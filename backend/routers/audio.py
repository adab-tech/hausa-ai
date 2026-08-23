"""
/api/live  — bidirectional voice WebSocket (replaces Google Live API).

Protocol (mirrors the original geminiService.ts connectLive usage):
  Client → Server:  binary PCM-16 frames at 16 kHz, mono
  Server → Client:  JSON  {"type": "audio", "data": "<base64-pcm24k>"}
                    JSON  {"type": "text",  "data": "<transcript>"}
                    JSON  {"type": "error", "data": "<message>"}

Pipeline:
  1. Accumulate ~2 s of incoming PCM (32 000 samples at 16 kHz)
  2. faster-whisper STT → Hausa transcript
  3. Ollama chat (same model as /api/chat) → response text
  4. Piper TTS → PCM at 24 kHz
  5. Send PCM chunks back as base64
"""

import asyncio
import base64
import io
import json
import logging
import os
import struct
import tempfile
import time
from contextlib import suppress
from pathlib import Path
from typing import Any, cast

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Response, HTTPException, Request

from rate_limit import limiter
from routers.fallback import generate_fallback_response
from services.cloudflare_stt_service import cloudflare_stt_enabled, transcribe_via_cloudflare
import corrections_store

router = APIRouter()
logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "aya-expanse:8b")
# See routers/chat.py's _OLLAMA_OPTIONS comment for why this is hardcoded
# rather than left to Ollama's own thread auto-detection.
_OLLAMA_OPTIONS = {"num_thread": int(os.getenv("OLLAMA_INFERENCE_THREADS", "2"))}

# Same rationale as routers/chat.py: a slow-but-not-erroring Ollama never
# trips the except-based fallback on its own, so bound how long voice
# chat waits before handing off to Cerebras.
_OLLAMA_VOICE_TIMEOUT = float(os.getenv("OLLAMA_FIRST_TOKEN_TIMEOUT", "12"))
PIPER_MODEL = os.getenv("PIPER_MODEL", "ha_NG-openbible-medium")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny/base/small/medium

# Resolve local models path first
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_LOCAL_DIR = _ROOT_DIR / "models" / "piper"

PIPER_MODELS_DIR = os.getenv("PIPER_MODELS_DIR")
if not PIPER_MODELS_DIR:
    # Ensure folder exists
    _DEFAULT_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    PIPER_MODELS_DIR = str(_DEFAULT_LOCAL_DIR)
else:
    # Ensure env-specified directory exists
    Path(PIPER_MODELS_DIR).mkdir(parents=True, exist_ok=True)

# How many 16 kHz PCM samples to accumulate before running STT (~2 s)
CHUNK_SAMPLES = 32_000

# Loudness normalization target for ALL served TTS. Raw model output has no
# normalization — RMS swings ~-11.5..-14.5 dBFS and peaks hit 0 dBFS
# (full-scale, clipping risk), so replies are uneven and "not loud". These
# unify every voice source to the landing-page sample level
# (landing/samples/*.wav: RMS ≈ -14 dBFS, peak ≈ -0.5 dBFS). Parsed once at
# module load, overridable per deploy without a code change.
TTS_TARGET_RMS_DBFS = float(os.getenv("TTS_TARGET_RMS_DBFS", "-14.0"))
TTS_PEAK_CEILING_DBFS = float(os.getenv("TTS_PEAK_CEILING_DBFS", "-0.5"))

# Sovereign Constitution system instruction for voice sessions
_VOICE_SYSTEM = """
[IDENTITY]: Murya, a sovereign Hausa AI.
[LINGUISTIC_CORE]: Standard Hausa (Fada).
[ROLE]: You are a live voice assistant. Respond naturally and conversationally in Hausa.
- Address the user ONLY in the grammatical singular. Never use plural pronouns or inflections of respect (e.g. do NOT use 'kun yini', 'muku', 'ayyukanku', 'kuka sani', 'ku', 'kun', 'su', 'sun').
- Hausa singular address is grammatically gendered — 'ka yini' vs 'ki yini', 'maka' vs 'miki', 'ka' vs 'ki'. Use ONLY the form matching the [ADDRESSEE_GENDER] value given below, consistently — never mix masculine and feminine forms.
- If [ADDRESSEE_GENDER] is 'unspecified', do NOT guess. Ask once, briefly, at the start of the call which form to use, then use it for the rest of the call.
- Maintain a highly formal, courtly, and polite demeanor (Hausan Zaure) utilizing singular forms.
- Keep responses concise for voice delivery.
[CODE_SWITCHING]: Scientific, technical and official terms and proper nouns (Biology, WhatsApp, API, course names) may stay in English — natural Hausa code-mixing, not a defect. Give an established Hausa term first when one exists, e.g. 'ilimin halittu (Biology)'; never invent awkward calques.
"""


def _voice_time_context() -> str:
    """Compact current-date/time line for voice replies (kept short for voice
    delivery). Nigeria + Makka precomputed exactly via zoneinfo; server is
    UTC. Falls back to fixed WAT (UTC+1) if tzdata is unavailable."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now_utc = datetime.now(ZoneInfo("UTC"))
    try:
        wat = now_utc.astimezone(ZoneInfo("Africa/Lagos"))
        makka = now_utc.astimezone(ZoneInfo("Asia/Riyadh"))
        return (
            f"[CURRENT_DATETIME]: Nigeria (WAT) now = {wat:%A, %d %B %Y, %H:%M}; "
            f"Makka = {makka:%H:%M}. You know the current date/time — answer directly "
            f"in Hausa; for other places compute from these."
        )
    except Exception:
        from datetime import timedelta
        wat = now_utc + timedelta(hours=1)
        return (
            f"[CURRENT_DATETIME]: Nigeria (WAT, UTC+1) now = {wat:%A, %d %B %Y, %H:%M}. "
            f"You know the current date/time — answer directly in Hausa."
        )


def _voice_system_prompt(addressee_gender: str = "unspecified") -> str:
    """_VOICE_SYSTEM plus current date/time and any human-approved corrections,
    refreshed per call so newly-approved corrections take effect without a
    server restart."""
    return f"{_VOICE_SYSTEM}\n{_voice_time_context()}\n[ADDRESSEE_GENDER]: {addressee_gender}\n{corrections_store.get_approved_corrections_prompt()}"


# ---------------------------------------------------------------------------
# Lazy singletons
# ---------------------------------------------------------------------------
_whisper_model = None
_piper_voice = None
_vits_engine = None


def _get_vits():
    global _vits_engine
    if _vits_engine is None:
        try:
            from services.vits_engine import VitsEngine
            _vits_engine = VitsEngine()
        except Exception as e:
            logger.error("Failed to load VITS Engine service: %s", e)
    return _vits_engine


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        logger.info("Loading Whisper model: %s", WHISPER_MODEL)
        _whisper_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _whisper_model


# Map frontend speaker_id (0..7) to WAXAL speaker_id string (1..8).
# Frontend: 0..3 are Namiji (Male), 4..7 are Mace (Female).
# WAXAL numeric ids ALTERNATE gender (verified against
# waxal_hausa/metadata_processed.jsonl's audio_file prefixes):
# 1=F1, 2=M1, 3=F2, 4=M2, 5=F3, 6=M3, 7=F4, 8=M4 — NOT grouped as
# 1-4=female/5-8=male. Getting this wrong silently serves a
# wrong-gender recording for half of all speaker selections.
SPEAKER_MAP = {
    0: "2",  # Namiji (Male) -> M1
    1: "4",  # Namiji (Male) -> M2
    2: "6",  # Namiji (Male) -> M3
    3: "8",  # Namiji (Male) -> M4
    4: "1",  # Mace (Female) -> F1
    5: "3",  # Mace (Female) -> F2
    6: "5",  # Mace (Female) -> F3
    7: "7",  # Mace (Female) -> F4
}


# Minimum Jaccard word-overlap for a WAXAL recording to stand in for live
# TTS. This path plays back a real pre-recorded human sentence verbatim —
# without a high bar, it always returns *some* file (even a near-zero-overlap
# one) and silently says the wrong words instead of the requested text,
# while also preempting the trained VITS model from ever running. Only
# near-exact known prompts should take this shortcut.
_MIN_WAXAL_MATCH_SCORE = 0.6


def _find_closest_waxal_sample(text: str, speaker_id_str: str) -> str | None:
    """Find a WAXAL sample whose text closely matches the input for a given
    speaker, or None if nothing meets _MIN_WAXAL_MATCH_SCORE."""
    metadata_path = Path(__file__).resolve().parent.parent.parent / "waxal_hausa" / "metadata_processed.jsonl"
    if not metadata_path.exists():
        metadata_path = Path(__file__).resolve().parent.parent.parent / "waxal_hausa" / "metadata.jsonl"

    if not metadata_path.exists():
        return None

    best_file = None
    best_score = -1.0

    import json
    import re

    words_input = set(re.findall(r'\w+', text.lower()))
    if not words_input:
        return None

    with open(metadata_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                s = json.loads(line)
                if str(s.get("speaker_id")) != speaker_id_str:
                    continue
                s_text = s.get("text_normalized", s.get("text", ""))
                words_s = set(re.findall(r'\w+', s_text.lower()))
                if not words_s:
                    continue
                # Jaccard similarity
                score = len(words_input.intersection(words_s)) / len(words_input.union(words_s))
                if score > best_score:
                    best_score = score
                    best_file = s.get("audio_file")
            except Exception:
                continue

    if best_score < _MIN_WAXAL_MATCH_SCORE:
        return None
                
    return best_file


def _load_mp3_as_pcm24k(mp3_path: Path) -> bytes | None:
    """Load an MP3 file and resample it to 24000 Hz, mono, PCM 16-bit."""
    try:
        from pydub import AudioSegment
        # Configure pydub to find ffmpeg if it's installed via imageio-ffmpeg
        try:
            import imageio_ffmpeg
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            AudioSegment.converter = ffmpeg_bin
        except Exception:
            pass
            
        audio = AudioSegment.from_mp3(str(mp3_path))
        audio = audio.set_frame_rate(24000).set_channels(1).set_sample_width(2)
        return audio.raw_data
    except Exception as e:
        logger.error("Failed to resample MP3 with pydub: %s", e)
        return None


def _download_piper_assets(model_path: Path, config_path: Path):
    """Download the baseline Piper model/config from Hugging Face if missing.

    Previously pointed at rhasspy/piper-voices' "ha_NG-openbible-medium"
    voice, which 404'd on every deploy — that repo has no "ha" (Hausa)
    language at all, and never did. There is no third-party Hausa Piper
    voice to fall back to. Instead this now re-downloads OUR OWN trained
    WAXAL model from adab-tech/murya-piper-hausa-tts on the Hub — the same
    model baked into the Docker image at build time — so this path is a
    genuine self-healing fallback (e.g. if the persistent volume's copy is
    ever missing or corrupted) rather than a dead link to a voice that was
    never Hausa-specific to begin with.
    """
    import urllib.request

    base_url = "https://huggingface.co/adab-tech/murya-piper-hausa-tts/resolve/main"

    if not model_path.exists():
        logger.info("Downloading baseline Hausa Piper model from HF: adab-tech/murya-piper-hausa-tts...")
        try:
            urllib.request.urlretrieve(f"{base_url}/model.onnx", str(model_path))
            logger.info("Baseline Piper model downloaded successfully.")
        except Exception as e:
            logger.error("Failed to download baseline model ONNX: %s", e)

    if not config_path.exists():
        logger.info("Downloading baseline Hausa Piper config from HF: adab-tech/murya-piper-hausa-tts...")
        try:
            urllib.request.urlretrieve(f"{base_url}/model.onnx.json", str(config_path))
            logger.info("Baseline Piper config downloaded successfully.")
        except Exception as e:
            logger.error("Failed to download baseline model config JSON: %s", e)


def _get_piper():
    global _piper_voice
    if _piper_voice is None:
        try:
            from piper import PiperVoice

            model_path = Path(PIPER_MODELS_DIR) / f"{PIPER_MODEL}.onnx"
            config_path = Path(PIPER_MODELS_DIR) / f"{PIPER_MODEL}.onnx.json"
            
            # Auto-download if files are missing
            _download_piper_assets(model_path, config_path)

            if model_path.exists() and config_path.exists():
                logger.info("Loading Piper voice: %s", PIPER_MODEL)
                _piper_voice = PiperVoice.load(str(model_path), config_path=str(config_path))
            else:
                logger.warning(
                    "Piper model not found at %s — TTS disabled. "
                    "Download from https://huggingface.co/rhasspy/piper-voices",
                    model_path,
                )
        except ImportError:
            logger.warning("piper-tts not installed — TTS disabled")
    return _piper_voice


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------
def _pcm_bytes_to_float32(raw: bytes) -> np.ndarray:
    """Convert raw PCM-16 LE bytes to float32 numpy array."""
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return samples


def _float32_to_pcm16_bytes(arr: np.ndarray) -> bytes:
    """Convert float32 numpy array to raw PCM-16 LE bytes."""
    clipped = np.clip(arr, -1.0, 1.0)
    return (clipped * 32767).astype(np.int16).tobytes()


def _normalize_loudness(
    pcm: bytes,
    target_rms_dbfs: float = TTS_TARGET_RMS_DBFS,
    peak_ceiling_dbfs: float = TTS_PEAK_CEILING_DBFS,
) -> bytes:
    """Normalize 16-bit mono PCM to a unified loudness (landing-sample level).

    Applies RMS gain toward target_rms_dbfs, then peak-limits so nothing
    exceeds peak_ceiling_dbfs (the ceiling wins over the RMS target — no
    clipping). Silent input is returned unchanged (never divide by ~0).
    """
    audio = _pcm_bytes_to_float32(pcm)
    if audio.size == 0:
        return pcm

    current_rms = float(np.sqrt(np.mean(audio ** 2)))
    # Effectively silent — leave untouched rather than amplifying noise/NaN.
    if current_rms < 1e-4:
        return pcm

    target_rms_linear = 10 ** (target_rms_dbfs / 20.0)
    audio = audio * (target_rms_linear / current_rms)

    # Peak-limit: prevent clipping; takes priority over the RMS target.
    ceiling_linear = 10 ** (peak_ceiling_dbfs / 20.0)
    peak = float(np.max(np.abs(audio)))
    if peak > ceiling_linear:
        audio = audio * (ceiling_linear / peak)

    # Final safety clip, then re-encode (also handles [-1,1] clamp).
    audio = np.clip(audio, -1.0, 1.0)
    return _float32_to_pcm16_bytes(audio)


def _synthesize_speech(
    text: str,
    speaker_id: int = 0,
    length_scale: float | None = None,
    noise_scale: float | None = None,
    noise_w: float | None = None,
) -> bytes | None:
    """Run VITS/Piper TTS and return raw PCM-16 LE bytes at 24 kHz, loudness-
    normalized so every synthesis path comes out at the landing-sample level.

    Delegates to _synthesize_speech_raw for the actual synthesis, then
    normalizes the single non-None return exactly once (None passes through
    untouched)."""
    pcm = _synthesize_speech_raw(
        text, speaker_id,
        length_scale=length_scale, noise_scale=noise_scale, noise_w=noise_w,
    )
    if pcm:
        return _normalize_loudness(pcm)
    return pcm


def _synthesize_speech_raw(
    text: str,
    speaker_id: int = 0,
    length_scale: float | None = None,
    noise_scale: float | None = None,
    noise_w: float | None = None,
) -> bytes | None:
    """Run VITS/Piper TTS and return raw PCM-16 LE bytes at 24 kHz."""
    # 0. Human pronunciation corrections have the HIGHEST priority. If a native
    #    reviewer has recorded and approved the correct way to say this exact
    #    text, use that recording instead of synthesizing (see
    #    pronunciation_store.py — the human-in-the-loop TTS loop). Keyed on the
    #    RAW request text (what the user flagged), before TTS normalization.
    try:
        import pronunciation_store
        correction = pronunciation_store.lookup(text, speaker_id)
        if correction:
            logger.info("Speech served from approved pronunciation correction (speaker %s)", speaker_id)
            return correction
    except Exception as exc:
        logger.error("Pronunciation correction lookup failed: %s", exc)

    # Full TTS text-normalization pipeline (hooked consonants, numbers,
    # currency ₦/$/€/£, percent, markdown/control symbols, separator
    # repair — see orthography.prepare_text_for_tts for the failure modes
    # each stage prevents). Done here (not just by callers) so every
    # synthesis path — /api/tts, live WebSocket, future callers — gets it.
    from orthography import prepare_text_for_tts
    text = prepare_text_for_tts(text)

    # 1. Try WAXAL voice bank if speaker_id is explicitly selected
    if speaker_id is not None:
        try:
            spk_str = SPEAKER_MAP.get(speaker_id)
            if spk_str:
                audio_file = _find_closest_waxal_sample(text, spk_str)
                if audio_file:
                    audio_path = Path(__file__).resolve().parent.parent.parent / "waxal_hausa" / audio_file
                    if audio_path.exists():
                        pcm = _load_mp3_as_pcm24k(audio_path)
                        if pcm:
                            logger.info("Generated speech using WAXAL sample %s (speaker %s)", audio_file, spk_str)
                            return pcm
        except Exception as e:
            logger.error("Failed to load WAXAL sample for synthesis: %s", e)

    # 2. Try custom VITS model first
    vits = _get_vits()
    if vits and vits.model_path.exists():
        # Single-pass synthesis — let the trained model speak the whole passage
        # naturally, with its OWN prosody and punctuation pauses. We do not split
        # sentences or impose uniform pauses/levels (that fought the model and
        # trembled/broke). Pace is the measured global length_scale; that's it.
        pcm = vits.synthesize(
            text, speaker_id=speaker_id,
            length_scale=length_scale, noise_scale=noise_scale, noise_w=noise_w,
        )
        if pcm:
            logger.info("Generated speech using custom VITS model (speaker %d)", speaker_id)
            return pcm
            
    # 3. Fallback to baseline Piper model
    voice = _get_piper()
    if voice is None:
        # 4. Fallback to any closest WAXAL sample as final resort
        try:
            spk_str = SPEAKER_MAP.get(speaker_id or 0, "5")
            audio_file = _find_closest_waxal_sample(text, spk_str)
            if audio_file:
                audio_path = Path(__file__).resolve().parent.parent.parent / "waxal_hausa" / audio_file
                if audio_path.exists():
                    pcm = _load_mp3_as_pcm24k(audio_path)
                    if pcm:
                        logger.info("Generated speech using WAXAL fallback sample %s", audio_file)
                        return pcm
        except Exception as e:
            logger.error("Failed to load WAXAL fallback sample: %s", e)
        return None
        
    # Piper writes WAV; strip the 44-byte header, then resample to the
    # 24 kHz contract every caller assumes. Our published Hausa voice is
    # 22 050 Hz native — returning its PCM unresampled made clients play
    # it at 24 kHz: ~9% too fast and audibly pitched up.
    wav_buf = io.BytesIO()
    with voice.stream_to_file(text, wav_buf):
        pass
    wav_buf.seek(44)
    pcm = wav_buf.read()

    native_rate = int(getattr(getattr(voice, "config", None), "sample_rate", 22050) or 22050)
    if pcm and native_rate != 24000:
        audio_f = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
        duration = audio_f.size / float(native_rate)
        n_out = int(round(duration * 24000))
        t_in = np.linspace(0.0, duration, num=audio_f.size, endpoint=False)
        t_out = np.linspace(0.0, duration, num=n_out, endpoint=False)
        pcm = np.interp(t_out, t_in, audio_f).astype(np.int16).tobytes()
    return pcm


# Minimum RMS (of float32 audio in [-1, 1]) for a chunk to be treated as
# speech. Whisper HALLUCINATES text on silence/noise-only input — it will
# happily invent a Hausa greeting from an empty room — and each invented
# "user turn" makes the assistant answer speech nobody said, locking the
# live session into talking to itself. Gate cheaply on energy before ever
# running STT.
_SPEECH_RMS_THRESHOLD = float(os.getenv("MIC_RMS_THRESHOLD", "0.01"))

# Safety valve for the assistant_speaking server-side echo backstop (see
# live_endpoint below): if the client never sends the "false" control
# message -- a JS exception, a dropped control frame, a tab going into deep
# background throttling -- this guarantees the session doesn't go
# permanently deaf. No real TTS reply + tail should ever run this long.
_ASSISTANT_SPEAKING_MAX_S = float(os.getenv("ASSISTANT_SPEAKING_MAX_S", "15.0"))


async def _transcribe(pcm_bytes: bytes, sample_rate: int = 16000) -> str:
    """Transcribe pcm_bytes to Hausa text. Tries Cloudflare Workers AI's
    hosted Whisper first when configured -- offloads STT off this box
    entirely, relieving the RAM/CPU pressure shared with Ollama/Piper that's
    been causing Ollama's failures (see stream_ollama's docstring in
    routers/chat.py) -- falling back to local faster-whisper otherwise or on
    any Cloudflare failure. Returns '' for non-speech either way."""
    float_audio = _pcm_bytes_to_float32(pcm_bytes)

    # 1. Energy gate: skip silence/background noise without running STT at all.
    rms = float(np.sqrt(np.mean(float_audio**2))) if float_audio.size else 0.0
    if rms < _SPEECH_RMS_THRESHOLD:
        return ""

    if cloudflare_stt_enabled():
        text = await transcribe_via_cloudflare(_wav_bytes(float_audio, sample_rate))
        if text is not None:
            # Sanity floor: one or two characters is noise, not Hausa.
            return text if len(text) > 2 else ""
        logger.warning("Cloudflare STT unavailable, falling back to local Whisper.")

    # Local faster-whisper is CPU-bound/blocking -- run off the event loop.
    return await asyncio.get_event_loop().run_in_executor(
        None, _transcribe_local, float_audio, sample_rate
    )


def _transcribe_local(float_audio: np.ndarray, sample_rate: int) -> str:
    """Run local faster-whisper STT; returns transcript string ('' for
    non-speech). Fallback path when Cloudflare STT is unconfigured or fails."""
    model = _get_whisper()
    # Write to temp WAV for whisper; always clean up afterward
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        with open(tmp_path, "wb") as f:
            f.write(_wav_bytes(float_audio, sample_rate))
        # vad_filter: Silero VAD inside faster-whisper strips non-speech
        # spans, the main defense against hallucinated transcripts.
        segments, _ = model.transcribe(tmp_path, language="ha", vad_filter=True)
        text = " ".join(seg.text for seg in segments).strip()
        # Sanity floor: one or two characters is noise, not Hausa.
        return text if len(text) > 2 else ""
    finally:
        if tmp_path:
            with suppress(OSError):
                os.unlink(tmp_path)


def _wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """Build a minimal PCM WAV file in memory."""
    pcm = _float32_to_pcm16_bytes(audio)
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + len(pcm)))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", len(pcm)))
    buf.write(pcm)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# LLM chat (non-streaming, for voice — we want the full response at once)
# ---------------------------------------------------------------------------
async def _llm_respond(transcript: str, history: list[dict], addressee_gender: str = "unspecified") -> str:
    # Cerebras is the fast, hosted primary — local Ollama on this box is
    # slow enough that trying it first before Cerebras just adds latency.
    try:
        return await _llm_respond_cerebras(transcript, history, addressee_gender)
    except Exception as cerebras_err:
        logger.warning("Cerebras unavailable for voice (%s), switching to Groq...", cerebras_err)

    # Groq before Ollama: real bug found 2026-08-23 -- this voice chain never
    # had a Groq step at all (unlike /api/chat and /api/document, fixed
    # earlier the same day), so with Cerebras down every live-voice turn was
    # paying Ollama's full timeout (never once succeeds under current RAM
    # pressure) before falling to Gemini's thin free quota or the static
    # fallback -- a real, separate reason live voice could feel broken.
    try:
        return await _llm_respond_groq(transcript, history, addressee_gender)
    except Exception as groq_err:
        logger.warning("Groq unavailable for voice (%s), switching to Ollama...", groq_err)

    import ollama

    client = ollama.AsyncClient(host=OLLAMA_HOST)
    messages = [{"role": "system", "content": _voice_system_prompt(addressee_gender)}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": transcript})

    try:
        response = await asyncio.wait_for(
            client.chat(model=OLLAMA_MODEL, messages=cast(Any, messages), options=_OLLAMA_OPTIONS),
            timeout=_OLLAMA_VOICE_TIMEOUT,
        )
        return response["message"]["content"].strip()
    except Exception as ollama_err:
        logger.warning("Ollama unavailable for voice (%s), switching to Gemini...", ollama_err)
        return await _llm_respond_gemini(transcript, history, addressee_gender)


async def _llm_respond_groq(transcript: str, history: list[dict], addressee_gender: str = "unspecified") -> str:
    """Fallback: use Groq (OpenAI-compatible, real free tier) for voice LLM
    responses. Same model/contract as stream_groq in routers/chat.py."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set — cannot use Groq fallback for voice.")

    from groq import AsyncGroq

    client = AsyncGroq(api_key=api_key)
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    messages = [{"role": "system", "content": _voice_system_prompt(addressee_gender)}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": transcript})

    response = await client.chat.completions.create(
        model=model,
        messages=cast(Any, messages),
    )
    return response.choices[0].message.content.strip()


async def _llm_respond_cerebras(transcript: str, history: list[dict], addressee_gender: str = "unspecified") -> str:
    """Fallback: use the Cerebras Cloud SDK (OpenAI-compatible) for voice LLM responses."""
    import os
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        raise RuntimeError("CEREBRAS_API_KEY not set — cannot use Cerebras fallback for voice.")

    from cerebras.cloud.sdk import AsyncCerebras

    client = AsyncCerebras(api_key=api_key)
    model = os.getenv("CEREBRAS_MODEL", "gemma-4-31b")

    messages = [{"role": "system", "content": _voice_system_prompt(addressee_gender)}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": transcript})

    response = await client.chat.completions.create(
        model=model,
        messages=cast(Any, messages),
    )
    return response.choices[0].message.content.strip()


async def _llm_respond_gemini(transcript: str, history: list[dict], addressee_gender: str = "unspecified") -> str:
    """Fallback: use Gemini SDK for voice LLM responses."""
    import os
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set — cannot use Gemini fallback for voice.")
    
    gemini_model = os.getenv("VERTEX_MODEL", "gemini-2.5-flash")
    
    # Build history in the new SDK format
    gemini_history = []
    for msg in history[-6:]:
        role = "user" if msg.get("role") == "user" else "model"
        gemini_history.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
    
    loop = asyncio.get_event_loop()
    
    # Try new google.genai SDK first
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        def _sync_send_new():
            contents = gemini_history + [{"role": "user", "parts": [{"text": transcript}]}]
            response = client.models.generate_content(
                model=gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=_voice_system_prompt(addressee_gender),
                    temperature=0.4,
                    max_output_tokens=512,
                )
            )
            return response.text.strip() if response.text else ""

        return await loop.run_in_executor(None, _sync_send_new)

    except ImportError:
        pass
    except Exception as e:
        logger.warning("google.genai voice error: %s, falling back...", e)

    # Fallback to deprecated google.generativeai
    import google.generativeai as genai_old
    genai_old.configure(api_key=api_key)
    model = genai_old.GenerativeModel(
        model_name=gemini_model,
        system_instruction=_voice_system_prompt(addressee_gender),
        generation_config={"temperature": 0.4, "max_output_tokens": 512}
    )
    old_history = [{"role": h["role"], "parts": [{"text": h["parts"][0]["text"]}]} for h in gemini_history]
    chat = model.start_chat(history=old_history)

    def _sync_send_old():
        response = chat.send_message(transcript)
        return response.text.strip()
    
    return await loop.run_in_executor(None, _sync_send_old)


def _add_wav_header(pcm_bytes: bytes, sample_rate: int = 24000) -> bytes:
    """Helper to wrap raw PCM-16 bytes into a WAV container."""
    header = io.BytesIO()
    header.write(b"RIFF")
    header.write(struct.pack("<I", 36 + len(pcm_bytes)))
    header.write(b"WAVE")
    header.write(b"fmt ")
    header.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    header.write(b"data")
    header.write(struct.pack("<I", len(pcm_bytes)))
    header.write(pcm_bytes)
    return header.getvalue()


@router.get("/tts")
@limiter.limit("20/minute")
async def tts_endpoint(
    request: Request,
    text: str,
    speaker_id: int = 0,
    length_scale: float | None = None,
    noise_scale: float | None = None,
    noise_w: float | None = None,
):
    """
    Synthesize text into speech using the custom VITS model and return a WAV file.

    length_scale/noise_scale/noise_w are optional per-request overrides for
    A/B testing pacing and clarity (e.g. ?length_scale=1.15 for slower,
    more deliberate speech) without redeploying — see services/vits_engine.py.
    """
    try:
        pcm = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _synthesize_speech(
                text, speaker_id,
                length_scale=length_scale, noise_scale=noise_scale, noise_w=noise_w,
            ),
        )
        if not pcm:
            raise HTTPException(status_code=500, detail="TTS synthesis failed")
            
        # Wrap the raw PCM-16 bytes in a WAV container
        wav_bytes = _add_wav_header(pcm, sample_rate=24000)
        return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as e:
        logger.exception("TTS endpoint failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ---------------------------------------------------------------------------
# WebSocket handler
# ---------------------------------------------------------------------------
# slowapi's rate limiter doesn't cover WebSockets, and each connection runs
# a CPU-heavy STT+LLM+TTS pipeline per ~2s audio chunk — without a cap,
# nothing stops one client from flooding the (single, CPU-only) Fly machine
# with concurrent live sessions. In-memory/per-process, matching the rest
# of this app's single-machine deployment model (see rate_limit.py).
_MAX_LIVE_CONNECTIONS_PER_IP = int(os.getenv("MAX_LIVE_CONNECTIONS_PER_IP", "2"))
_live_connections_by_ip: dict[str, int] = {}


@router.websocket("/live")
async def live_endpoint(ws: WebSocket, speaker_id: int = 0, addressee_gender: str = "unspecified"):
    if addressee_gender not in ("masculine", "feminine", "unspecified"):
        addressee_gender = "unspecified"

    client_ip = ws.client.host if ws.client else "unknown"
    if _live_connections_by_ip.get(client_ip, 0) >= _MAX_LIVE_CONNECTIONS_PER_IP:
        await ws.close(code=1008, reason="Too many concurrent live sessions from this address.")
        return

    await ws.accept()
    _live_connections_by_ip[client_ip] = _live_connections_by_ip.get(client_ip, 0) + 1
    pcm_buffer = bytearray()
    conversation_history: list[dict] = []

    # Server-side echo backstop ("the app is listening to itself" bug): the
    # client's half-duplex mic gate (App.tsx toggleLiveVoice) is the primary
    # defense against the assistant transcribing its own TTS, but it's
    # timing-based client audio-buffer bookkeeping — a scheduling race at
    # the start of playback, or echoCancellation simply not doing its job
    # on a laptop's built-in speakers, can leak a bit of the assistant's own
    # voice into the mic stream. Once that reaches STT, the RMS/VAD gates
    # below are no help: leaked TTS is real, energetic, VAD-passing speech,
    # indistinguishable from genuine user speech by those signals alone.
    # So the client also tells us explicitly, via a small JSON control
    # message, when its own reply is scheduled to be audible
    # (setAssistantSpeaking in services/localService.ts), and we drop any
    # audio bytes that arrive while that's true — independent of whatever
    # the client's own gate did or didn't catch.
    assistant_speaking = False
    assistant_speaking_since: float | None = None

    try:
        while True:
            # Receive a raw ASGI websocket message rather than
            # ws.receive_bytes() so this loop can also accept the
            # assistant_speaking JSON control frame (a text message) on the
            # same connection without raising.
            try:
                message = await asyncio.wait_for(ws.receive(), timeout=30.0)
            except TimeoutError:
                continue

            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(message.get("code", 1000), message.get("reason"))

            text = message.get("text")
            if text is not None:
                try:
                    control = json.loads(text)
                except ValueError:
                    continue
                if isinstance(control, dict) and control.get("type") == "assistant_speaking":
                    speaking = bool(control.get("value"))
                    assistant_speaking = speaking
                    assistant_speaking_since = time.monotonic() if speaking else None
                continue

            data = message.get("bytes")
            if not data:
                continue

            if assistant_speaking:
                # Safety valve: don't trust a stuck flag forever in case the
                # client failed to send the "false" follow-up.
                if assistant_speaking_since is not None and (
                    time.monotonic() - assistant_speaking_since > _ASSISTANT_SPEAKING_MAX_S
                ):
                    assistant_speaking = False
                    assistant_speaking_since = None
                else:
                    # Drop it outright rather than buffering it — a leaked
                    # fragment must not survive to be merged into the next
                    # legitimate ~2s chunk once the flag clears.
                    continue

            pcm_buffer.extend(data)

            # Process when we have ~2 s worth of audio
            if len(pcm_buffer) < CHUNK_SAMPLES * 2:  # 2 bytes per sample
                continue

            chunk = bytes(pcm_buffer)
            pcm_buffer.clear()

            # 1. STT. On failure, SKIP the turn — never substitute an
            # invented transcript. The old fallback ("Sannu barka") made
            # the assistant answer speech the user never said, which (with
            # the client's half-duplex mic gate active during playback)
            # locked live sessions into a self-talk loop the real user
            # couldn't interrupt.
            try:
                transcript = await _transcribe(chunk)
            except Exception:
                logger.exception("STT failed; skipping this audio chunk")
                continue

            if not transcript:
                continue

            await ws.send_text(json.dumps({"type": "user_transcript", "data": transcript}))

            # 2. LLM
            try:
                reply_text = await _llm_respond(transcript, conversation_history, addressee_gender)
            except Exception as exc:
                logger.exception("LLM failed, using fallback response")
                reply_text = generate_fallback_response(transcript, addressee_gender=addressee_gender)

            conversation_history.append({"role": "user", "content": transcript})
            conversation_history.append({"role": "assistant", "content": reply_text})

            # Always send text reply so the UI can display it
            from orthography import normalize_hausa_orthography, apply_tonal_heuristics
            normalized = normalize_hausa_orthography(reply_text)
            tone_mapped = apply_tonal_heuristics(reply_text)
            await ws.send_text(json.dumps({
                "type": "text",
                "data": reply_text,
                "normalized": normalized,
                "tone_mapped": tone_mapped
            }))

            # 3. TTS → send PCM back if available
            try:
                pcm_out = await asyncio.get_event_loop().run_in_executor(
                    None, _synthesize_speech, reply_text, speaker_id
                )
                if pcm_out:
                    b64 = base64.b64encode(pcm_out).decode()
                    await ws.send_text(json.dumps({"type": "audio", "data": b64}))
            except Exception as exc:
                logger.exception("TTS failed")

    except WebSocketDisconnect:
        logger.info("Live session disconnected")
    except Exception as exc:
        logger.exception("Live session error: %s", exc)
        with suppress(Exception):
            await ws.send_text(json.dumps({"type": "error", "data": str(exc)}))
    finally:
        remaining = _live_connections_by_ip.get(client_ip, 1) - 1
        if remaining <= 0:
            _live_connections_by_ip.pop(client_ip, None)
        else:
            _live_connections_by_ip[client_ip] = remaining
