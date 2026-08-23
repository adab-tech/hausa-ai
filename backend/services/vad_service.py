"""
services/vad_service.py — Silero VAD (ONNX, pure numpy) streaming wrapper.

Model source: https://github.com/adab-tech/silero-vad (a clean fork of
snakers4/silero-vad, verified with
`gh api repos/adab-tech/silero-vad --jq '.parent.full_name'` -> "snakers4/silero-vad").
Weights fetched from that fork's src/silero_vad/data/silero_vad.onnx and
committed at models/silero_vad/silero_vad.onnx (see backend/Dockerfile for
how it's baked into the container, mirroring the models/piper_hausa_waxal/
convention).

Why this is hand-reimplemented instead of importing the fork's own
src/silero_vad/utils_vad.py (OnnxWrapper / VADIterator) verbatim: those
classes import torch purely to do tensor bookkeeping (concatenating the
context lookback, carrying recurrent state) around a single
onnxruntime.InferenceSession.run() call — the actual inference never uses
torch, only onnxruntime. This project has a deliberate no-torch policy (see
the comment block in backend/requirements.txt above the Pillow/imageio
entries: a local torch/diffusers pipeline was previously removed for
blowing out the Docker image past Fly's unpacked-size limit; faster-whisper
runs on CTranslate2 and Piper/the custom VITS engine are both already
onnxruntime-only specifically to avoid pulling torch back in). Adding torch
just to concatenate a couple of numpy arrays would undo that.

The tensor contract below (input/state/sr in; output/stateN out) was
confirmed two ways, not guessed: reading OnnxWrapper.__call__ and
_validate_input in the fork's utils_vad.py, AND independently loading the
committed ONNX graph with
`onnxruntime.InferenceSession(...).get_inputs()/.get_outputs()`, which
reported exactly:
    input  : [None, None]      float32   (batch, samples)
    state  : [2, None, 128]    float32   (recurrent state, carried between calls)
    sr     : []                int64     (scalar sample rate)
  ->
    output : [None, 1]         float32   (per-frame speech probability)
    stateN : [None, None, None] float32  (updated recurrent state)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Silero VAD's 16 kHz mode: 512-sample frames (32 ms), with a 64-sample
# lookback ("context") from the tail of the previous frame prepended to each
# call. This project only ever feeds it 16 kHz audio (Murya's mic pipeline
# resamples to 16 kHz client-side — see resampleLinear in App.tsx and
# _transcribe's sample_rate: int = 16000 in routers/audio.py), so the 8 kHz
# variant (256-sample frames, 32-sample context) is intentionally not
# supported here — one fewer branch to get wrong.
WINDOW_SIZE_SAMPLES = 512
FRAME_MS = WINDOW_SIZE_SAMPLES / 16_000 * 1000.0  # 32.0 ms per frame
_CONTEXT_SIZE = 64
_STATE_SHAPE = (2, 1, 128)  # (2, batch, hidden) — batch is always 1 here: one stream per WebSocket connection.
_SAMPLE_RATE = 16_000

_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_MODEL_PATH = _ROOT_DIR / "models" / "silero_vad" / "silero_vad.onnx"


def _resolve_model_path() -> Path:
    """VAD_MODEL_PATH lets deployment point explicitly at the baked-in model,
    mirroring VITS_MODEL_DIR in services/vits_engine.py — the container
    flattens the repo layout (backend/ -> /app), so the repo-relative
    auto-detection above would otherwise miss it."""
    env_path = os.getenv("VAD_MODEL_PATH", "").strip()
    if env_path:
        return Path(env_path)
    return _DEFAULT_MODEL_PATH


class SileroVAD:
    """One streaming VAD state machine over a shared onnxruntime session.

    Deliberately split from the session itself (see new_vad_stream() below):
    the ONNX graph/weights are the same for every caller and are expensive
    to reload, but the recurrent state + context lookback are per-audio-
    stream and MUST NOT be shared across concurrent WebSocket connections —
    each live_endpoint connection creates its own SileroVAD instance sharing
    one process-wide InferenceSession (onnxruntime sessions are safe for
    concurrent .run() calls since no mutable state lives on the session
    itself; everything mutable is passed in/out as numpy arrays here).
    """

    def __init__(self, session) -> None:
        self._session = session
        self._sr_input = np.array(_SAMPLE_RATE, dtype=np.int64)
        self.reset_states()

    def reset_states(self) -> None:
        """Zero the recurrent state and context lookback. Call this at the
        start of a fresh connection AND on every assistant_speaking
        false->true rising edge — carrying state/context across that
        boundary would let the model's internal notion of "recent audio"
        bleed leaked-echo or stale audio into the next real turn's
        probabilities, reintroducing the same class of bug the pcm_buffer
        clear() was fixed for."""
        self._state = np.zeros(_STATE_SHAPE, dtype=np.float32)
        self._context = np.zeros((1, _CONTEXT_SIZE), dtype=np.float32)

    def process_frame(self, frame: np.ndarray) -> float:
        """Run exactly one WINDOW_SIZE_SAMPLES (512) float32 frame at 16 kHz
        (values in [-1, 1]) through the model. Returns the speech
        probability in [0, 1] for that frame and advances the internal
        state/context for the next call."""
        frame = np.asarray(frame, dtype=np.float32).reshape(1, -1)
        if frame.shape[1] != WINDOW_SIZE_SAMPLES:
            raise ValueError(
                f"SileroVAD.process_frame expects exactly {WINDOW_SIZE_SAMPLES} "
                f"samples, got {frame.shape[1]}"
            )

        x = np.concatenate([self._context, frame], axis=1)
        outputs = self._session.run(
            None,
            {"input": x, "state": self._state, "sr": self._sr_input},
        )
        prob, state = outputs
        self._state = np.asarray(state, dtype=np.float32)
        # Matches OnnxWrapper.__call__: next call's context is the tail of
        # THIS call's (context+frame) concatenation, i.e. the last 64
        # samples of the frame just processed.
        self._context = x[:, -_CONTEXT_SIZE:]
        return float(np.asarray(prob).reshape(-1)[0])


_session = None
_session_load_failed = False


def _get_session():
    """Lazy singleton onnxruntime.InferenceSession, mirroring the
    _get_vits/_get_piper/_get_whisper pattern in routers/audio.py. Loaded
    once per process and shared read-only across every live connection."""
    global _session, _session_load_failed
    if _session is None and not _session_load_failed:
        try:
            import onnxruntime as ort

            path = _resolve_model_path()
            if not path.exists():
                raise FileNotFoundError(
                    f"Silero VAD ONNX model not found at {path}. Set VAD_MODEL_PATH "
                    "or place the model at models/silero_vad/silero_vad.onnx."
                )
            opts = ort.SessionOptions()
            # This model is tiny (~2 MB) and called once per 32 ms frame —
            # single-threaded avoids onnxruntime's thread-pool scheduling
            # overhead swamping the actual (sub-millisecond) inference time.
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 1
            _session = ort.InferenceSession(
                str(path), sess_options=opts, providers=["CPUExecutionProvider"]
            )
            logger.info("Loaded Silero VAD model from %s", path)
        except Exception as exc:
            logger.error(
                "Failed to load Silero VAD model — live voice will fall back "
                "to fixed-duration chunking for turn detection: %s", exc,
            )
            _session_load_failed = True
    return _session


def new_vad_stream() -> SileroVAD | None:
    """Create a fresh per-connection VAD stream. Returns None if the shared
    ONNX session could not be loaded (caller must fall back to the old
    fixed-duration chunking rather than crash the live session)."""
    session = _get_session()
    if session is None:
        return None
    return SileroVAD(session)
