"""Tests for services/vad_service.py — the pure numpy + onnxruntime Silero
VAD wrapper used by /api/live's turn detection (routers/audio.py).

These tests run against the REAL committed ONNX model
(models/silero_vad/silero_vad.onnx) when it's present in the working tree,
so they exercise actual inference, not a mock — the whole point is to prove
the tensor plumbing (input/state/sr in, output/stateN out; 512-sample
frames + 64-sample context; state shape (2, batch, 128)) is correct against
the real graph. The model file is intentionally NOT git-tracked (see
.gitignore's models//*.onnx rules, matching the pre-existing Piper
convention) — a checkout that's missing it (e.g. CI without the model
restored via LFS or a build step) skips these tests with a clear reason
rather than failing or silently faking a result.

Per the task brief: silence must read as near-zero probability (a strong,
reliable assertion). A synthetic "speech-like" signal is NOT asserted to
score as confident speech — Silero is a trained model and there's no cheap
way to synthesize something it confidently calls speech, so that test only
proves the plumbing: correct output shape, valid probability range, no
crash. Real speech/silence discrimination is exercised behaviorally by the
live_endpoint integration tests in test_audio.py, which mock the VAD
decision directly instead of relying on a synthetic signal fooling the
model.
"""

import numpy as np
import pytest

from services.vad_service import (
    FRAME_MS,
    WINDOW_SIZE_SAMPLES,
    SileroVAD,
    new_vad_stream,
)

pytestmark = pytest.mark.skipif(
    new_vad_stream() is None,
    reason=(
        "Silero VAD model not available at models/silero_vad/silero_vad.onnx "
        "(or VAD_MODEL_PATH) in this checkout -- the .onnx file is "
        "intentionally not git-tracked, matching the pre-existing Piper "
        "model convention. Fetch it per backend/services/vad_service.py's "
        "module docstring to run these tests."
    ),
)


def _silence_frame() -> np.ndarray:
    return np.zeros(WINDOW_SIZE_SAMPLES, dtype=np.float32)


def _noise_frame(seed: int = 0, amplitude: float = 0.4) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (rng.standard_normal(WINDOW_SIZE_SAMPLES) * amplitude).astype(np.float32)


# ---------------------------------------------------------------------------
# Frame size / window constants
# ---------------------------------------------------------------------------


def test_window_size_is_512_samples_at_16khz():
    """Silero's 16 kHz mode expects exactly 512-sample (32ms) frames --
    routers/audio.py's sub-chunking loop depends on this exact value."""
    assert WINDOW_SIZE_SAMPLES == 512
    assert FRAME_MS == pytest.approx(32.0)


# ---------------------------------------------------------------------------
# Silence -> near-zero probability (strong, reliable assertion)
# ---------------------------------------------------------------------------


def test_process_frame_silence_is_near_zero_probability():
    """Real digital silence must read as a very low speech probability --
    this is the actual gate that decides whether a live call ever reaches
    trailing-silence turn completion."""
    vad = new_vad_stream()
    assert vad is not None

    probs = [vad.process_frame(_silence_frame()) for _ in range(10)]
    assert all(0.0 <= p <= 1.0 for p in probs)
    # Give the recurrent state a couple of frames to settle, then require
    # sustained near-zero probability.
    assert max(probs[2:]) < 0.15


def test_process_frame_silence_probability_does_not_climb_over_time():
    """Feeding many consecutive silent frames must not cause the recurrent
    state to drift the probability upward -- a real symptom a state-
    bookkeeping bug (e.g. never actually updating self._state) could produce
    without necessarily crashing."""
    vad = new_vad_stream()
    assert vad is not None

    probs = [vad.process_frame(_silence_frame()) for _ in range(60)]
    # Later frames should be at least as quiet as the very first one, not
    # trending toward "speech".
    assert np.mean(probs[-10:]) <= np.mean(probs[:10]) + 0.05


# ---------------------------------------------------------------------------
# Plumbing on a non-trivial signal: shapes, ranges, no crash. NOT asserted
# to be classified as confident speech (see module docstring).
# ---------------------------------------------------------------------------


def test_process_frame_handles_noisy_signal_without_crashing():
    vad = new_vad_stream()
    assert vad is not None

    for i in range(20):
        prob = vad.process_frame(_noise_frame(seed=i))
        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0


def test_process_frame_rejects_wrong_frame_size():
    vad = new_vad_stream()
    assert vad is not None

    with pytest.raises(ValueError):
        vad.process_frame(np.zeros(256, dtype=np.float32))
    with pytest.raises(ValueError):
        vad.process_frame(np.zeros(1024, dtype=np.float32))


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


def test_reset_states_zeroes_recurrent_state_and_context():
    vad = new_vad_stream()
    assert vad is not None

    # Drive some real audio through so state/context are non-trivial.
    for i in range(5):
        vad.process_frame(_noise_frame(seed=i))
    assert np.any(vad._state != 0.0) or np.any(vad._context != 0.0)

    vad.reset_states()
    assert np.all(vad._state == 0.0)
    assert np.all(vad._context == 0.0)


def test_two_streams_share_session_but_not_state():
    """Two connections created via new_vad_stream() must not corrupt each
    other's recurrent state -- this is the whole reason SileroVAD is split
    from the shared onnxruntime session (see vad_service.py's SileroVAD
    docstring): concurrent /api/live connections must stay independent."""
    vad_a = new_vad_stream()
    vad_b = new_vad_stream()
    assert vad_a is not None and vad_b is not None
    assert vad_a is not vad_b

    # Drive stream A hard; stream B, untouched, must still read near-silent
    # on a fresh silent frame.
    for i in range(10):
        vad_a.process_frame(_noise_frame(seed=i, amplitude=0.8))

    prob_b = vad_b.process_frame(_silence_frame())
    assert prob_b < 0.2


def test_new_vad_stream_returns_fresh_instance_each_call():
    vad_a = new_vad_stream()
    vad_b = new_vad_stream()
    assert isinstance(vad_a, SileroVAD)
    assert isinstance(vad_b, SileroVAD)
    assert vad_a is not vad_b
