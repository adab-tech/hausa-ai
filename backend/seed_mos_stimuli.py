"""
One-time seed for the MOS listening test's stimulus pool (see mos_store.py).
Runs at startup, only when mos_stimuli is empty — synthesis is a few seconds
of CPU on 8 short sentences, cheap enough to just redo per-empty-DB rather
than shipping a pre-baked audio blob in the repo.

Sentences are real, already-vetted Hausa text pulled from elsewhere in this
project (utils/synth_custom_samples.py's dev synthesis set, and the landing
page's own demo copy) -- nothing invented for this. Ground-truth clips are
real WAXAL human recordings (data/mos_ground_truth/, CC-BY-SA-4.0, see
ATTRIBUTION in that directory), used as a naturalness ceiling to calibrate
against.

Deliberately does NOT include a low-quality-checkpoint anchor or a
competitor-model comparison the way the standalone research build
(the one-off Claude Artifact "Murya Listening Test") does -- that would mean
baking an extra ~77 MB eval checkpoint into the production image just for
this, for a comparison end users don't need. The full research-grade version
stays a separate, non-deployed tool; this one only answers "is the CURRENT
production voice good," which is what an admin needs before deciding what
feeds the next retrain.
"""

import logging
from pathlib import Path

import mos_store

logger = logging.getLogger("murya.mos.seed")

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MODEL_DIR_CONTAINER = Path("/app/models/piper_hausa_waxal")
_MODEL_DIR_REPO = _REPO_ROOT / "models" / "piper_hausa_waxal"

_GT_DIR_CONTAINER = Path("/app/mos_ground_truth")
_GT_DIR_REPO = _REPO_ROOT / "data" / "mos_ground_truth"

_VOICES = ["F1", "F2", "F3", "F4", "M1", "M2", "M3", "M4"]
_FRONTEND_BY_NAME = {"M1": 0, "M2": 1, "M3": 2, "M4": 3, "F1": 4, "F2": 5, "F3": 6, "F4": 7}

SENTENCES = [
    {"id": "s1", "text": "gobe za mu tafi kasuwa domin sayen abinci da kayan gona."},
    {"id": "s2", "text": "idan ruwan sama ya sauka, manoma za su yi murna sosai."},
    {"id": "s3", "text": "yara suna zuwa makaranta da safe don neman ilimi."},
    {"id": "s4", "text": "wannan labari ya faru ne shekaru da suka wuce a garinmu."},
    {"id": "s5", "text": "ina son yin aiki tukuru domin ci gaban al'ummata."},
    {"id": "s6", "text": "Gaskiya ta fi ƙarfin takobi, in ji magabata."},
    {"id": "s7", "text": "Sannu da zuwa, ina fatan kana lafiya."},
    {"id": "s8", "text": "Ga duniyar Hausa, ba nawa kaɗai ba ne."},
]

GROUND_TRUTH = [
    {"id": "gt0", "file": "gt0.wav", "text": "Busasshen reshen bishiya maciji ya nannade shi mai launin ruwan kasa da zane-zane."},
    {"id": "gt1", "file": "gt1.wav", "text": "Yau za a wuni da tsananin rana."},
]


def _resolve_model_dir() -> Path | None:
    if (_MODEL_DIR_CONTAINER / "model.onnx").exists():
        return _MODEL_DIR_CONTAINER
    if (_MODEL_DIR_REPO / "model.onnx").exists():
        return _MODEL_DIR_REPO
    return None


def _load_wav_as_pcm24k(path: Path) -> bytes | None:
    """Decode a known-format WAV file to mono PCM-16 LE at 24 kHz via
    libsndfile (soundfile) -- no ffmpeg/ffprobe subprocess needed for a
    format we already know exactly (see requirements.txt's soundfile entry
    for why this doesn't reuse pronunciation_store's pydub-based path)."""
    try:
        import numpy as np
        import soundfile as sf

        audio, sr = sf.read(str(path), dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != mos_store._SAMPLE_RATE:
            duration = audio.size / float(sr)
            n_out = int(round(duration * mos_store._SAMPLE_RATE))
            t_in = np.linspace(0.0, duration, num=audio.size, endpoint=False)
            t_out = np.linspace(0.0, duration, num=n_out, endpoint=False)
            audio = np.interp(t_out, t_in, audio).astype(np.float32)
        clipped = np.clip(audio, -1.0, 1.0)
        return (clipped * 32767).astype(np.int16).tobytes()
    except Exception as exc:
        logger.error("Failed to decode ground-truth WAV %s: %s", path, exc)
        return None


def _resolve_gt_dir() -> Path | None:
    if _GT_DIR_CONTAINER.exists():
        return _GT_DIR_CONTAINER
    if _GT_DIR_REPO.exists():
        return _GT_DIR_REPO
    return None


def seed_if_empty() -> None:
    if mos_store.stimuli_count() > 0:
        return

    model_dir = _resolve_model_dir()
    if model_dir is None:
        logger.warning("MOS seed skipped: no Piper model found for synthesis")
        return

    from services.vits_engine import VitsEngine

    engine = VitsEngine(model_dir=str(model_dir))
    if not engine.session:
        logger.warning("MOS seed skipped: VITS engine failed to initialize")
        return

    added = 0
    for sent in SENTENCES:
        for voice in _VOICES:
            pcm = engine.synthesize(sent["text"], speaker_id=_FRONTEND_BY_NAME[voice])
            if pcm is None:
                logger.warning("MOS seed: synthesis failed for %s/%s", voice, sent["id"])
                continue
            mos_store.add_stimulus(
                clip_id=f"murya_{voice}_{sent['id']}", condition="murya", voice=voice,
                sentence_id=sent["id"], text=sent["text"], audio_pcm=pcm,
                source="models/piper_hausa_waxal/model.onnx",
            )
            added += 1

    gt_dir = _resolve_gt_dir()
    if gt_dir is None:
        logger.warning("MOS seed: no ground-truth audio directory found, skipping that condition")
    else:
        for gt in GROUND_TRUTH:
            path = gt_dir / gt["file"]
            if not path.exists():
                logger.warning("MOS seed: missing ground-truth file %s", path)
                continue
            pcm = _load_wav_as_pcm24k(path)
            if pcm is None:
                logger.warning("MOS seed: failed to decode ground-truth file %s", path)
                continue
            mos_store.add_stimulus(
                clip_id=f"groundtruth_{gt['id']}", condition="ground_truth", voice="human",
                sentence_id=gt["id"], text=gt["text"], audio_pcm=pcm,
                source="adab-tech/WaxalNLP (hau_tts/test)",
            )
            added += 1

    logger.info("MOS stimuli seeded: %d clips", added)
