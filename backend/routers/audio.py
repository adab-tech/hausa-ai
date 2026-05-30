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
from contextlib import suppress
from pathlib import Path
from typing import Any, cast

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from routers.fallback import generate_fallback_response

router = APIRouter()
logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "aya-expanse:8b")
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

# Sovereign Constitution system instruction for voice sessions
_VOICE_SYSTEM = """
[IDENTITY]: Hausa AI (Nexus-7 Core).
[LINGUISTIC_CORE]: Standard Hausa (Fada).
[ROLE]: You are a live voice assistant. Respond naturally and conversationally in Hausa,
using appropriate honorifics and cultural warmth. Keep responses concise for voice delivery.
"""


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


def _download_piper_assets(model_path: Path, config_path: Path):
    """Download baseline Piper model and config files from Hugging Face if missing."""
    import urllib.request
    
    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/ha/ha_NG/openbible/medium"
    
    if not model_path.exists():
        logger.info("Downloading baseline Piper model from HF: %s.onnx...", PIPER_MODEL)
        url = f"{base_url}/{PIPER_MODEL}.onnx"
        try:
            urllib.request.urlretrieve(url, str(model_path))
            logger.info("Baseline Piper model downloaded successfully.")
        except Exception as e:
            logger.error("Failed to download baseline model ONNX: %s", e)
            
    if not config_path.exists():
        logger.info("Downloading baseline Piper config from HF: %s.onnx.json...", PIPER_MODEL)
        url = f"{base_url}/{PIPER_MODEL}.onnx.json"
        try:
            urllib.request.urlretrieve(url, str(config_path))
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


def _synthesize_speech(text: str, speaker_id: int = 0) -> bytes | None:
    """Run VITS/Piper TTS and return raw PCM-16 LE bytes at 24 kHz."""
    # Try custom VITS model first
    vits = _get_vits()
    if vits and vits.model_path.exists():
        pcm = vits.synthesize(text, speaker_id=speaker_id)
        if pcm:
            logger.info("Generated speech using custom VITS model (speaker %d)", speaker_id)
            return pcm
            
    # Fallback to baseline Piper model
    voice = _get_piper()
    if voice is None:
        return None
    # Piper writes WAV; we strip the 44-byte header and return raw PCM
    wav_buf = io.BytesIO()
    with voice.stream_to_file(text, wav_buf):
        pass
    wav_buf.seek(44)
    return wav_buf.read()


def _transcribe(pcm_bytes: bytes, sample_rate: int = 16000) -> str:
    """Run faster-whisper STT; returns transcript string."""
    model = _get_whisper()
    float_audio = _pcm_bytes_to_float32(pcm_bytes)
    # Write to temp WAV for whisper; always clean up afterward
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        _write_wav(tmp_path, float_audio, sample_rate)
        segments, _ = model.transcribe(tmp_path, language="ha")
        return " ".join(seg.text for seg in segments).strip()
    finally:
        if tmp_path:
            with suppress(OSError):
                os.unlink(tmp_path)


def _write_wav(path: str, audio: np.ndarray, sample_rate: int):
    """Write a minimal PCM WAV file."""
    pcm = _float32_to_pcm16_bytes(audio)
    with open(path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + len(pcm)))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
        f.write(b"data")
        f.write(struct.pack("<I", len(pcm)))
        f.write(pcm)


# ---------------------------------------------------------------------------
# LLM chat (non-streaming, for voice — we want the full response at once)
# ---------------------------------------------------------------------------
async def _llm_respond(transcript: str, history: list[dict]) -> str:
    import ollama

    client = ollama.AsyncClient(host=OLLAMA_HOST)
    messages = [{"role": "system", "content": _VOICE_SYSTEM}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": transcript})
    response = await client.chat(model=OLLAMA_MODEL, messages=cast(Any, messages))
    return response["message"]["content"].strip()


# ---------------------------------------------------------------------------
# WebSocket handler
# ---------------------------------------------------------------------------
@router.websocket("/live")
async def live_endpoint(ws: WebSocket, speaker_id: int = 0):
    await ws.accept()
    pcm_buffer = bytearray()
    conversation_history: list[dict] = []

    try:
        while True:
            # Receive binary PCM-16 audio frames from browser (16 kHz, mono)
            try:
                data = await asyncio.wait_for(ws.receive_bytes(), timeout=30.0)
            except TimeoutError:
                continue

            pcm_buffer.extend(data)

            # Process when we have ~2 s worth of audio
            if len(pcm_buffer) < CHUNK_SAMPLES * 2:  # 2 bytes per sample
                continue

            chunk = bytes(pcm_buffer)
            pcm_buffer.clear()

            # 1. STT
            try:
                transcript = await asyncio.get_event_loop().run_in_executor(
                    None, _transcribe, chunk
                )
            except Exception as exc:
                logger.exception("STT failed, using fallback transcript")
                transcript = "Sannu barka"
            
            if not transcript:
                continue

            await ws.send_text(json.dumps({"type": "user_transcript", "data": transcript}))

            # 2. LLM
            try:
                reply_text = await _llm_respond(transcript, conversation_history)
            except Exception as exc:
                logger.exception("LLM failed, using fallback response")
                reply_text = generate_fallback_response(transcript)

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
