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
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Response, HTTPException
from routers.fallback import generate_fallback_response
import corrections_store

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
[IDENTITY]: Hausa AI (Murya).
[LINGUISTIC_CORE]: Standard Hausa (Fada).
[ROLE]: You are a live voice assistant. Respond naturally and conversationally in Hausa.
- Address the user ONLY in the grammatical singular. Never use plural pronouns or inflections of respect (e.g. do NOT use 'kun yini', 'muku', 'ayyukanku', 'kuka sani', 'ku', 'kun', 'su', 'sun'). Instead, use singular forms: 'ka yini' / 'ki yini', 'maka' / 'miki', 'ayyukanka' / 'ayyukanki', 'kake sani' / 'kaki sani', 'ka', 'ki'.
- Maintain a highly formal, courtly, and polite demeanor (Hausan Zaure) utilizing singular forms.
- Keep responses concise for voice delivery.
"""


def _voice_system_prompt() -> str:
    """_VOICE_SYSTEM plus any human-approved corrections, refreshed per call
    so newly-approved corrections take effect without a server restart."""
    return f"{_VOICE_SYSTEM}\n{corrections_store.get_approved_corrections_prompt()}"


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


# Map frontend speaker_id (0..7) to WAXAL speaker_id string (1..8)
# Frontend: 0..3 are Namiji (Male), 4..7 are Mace (Female)
# WAXAL: 1..4 are Female (F1-F4), 5..8 are Male (M1-M4)
SPEAKER_MAP = {
    0: "5",  # Namiji (Male) -> M1
    1: "6",  # Namiji (Male) -> M2
    2: "7",  # Namiji (Male) -> M3
    3: "8",  # Namiji (Male) -> M4
    4: "1",  # Mace (Female) -> F1
    5: "2",  # Mace (Female) -> F2
    6: "3",  # Mace (Female) -> F3
    7: "4",  # Mace (Female) -> F4
}


def _find_closest_waxal_sample(text: str, speaker_id_str: str) -> str | None:
    """Find the WAXAL sample text that matches input text closest for a speaker."""
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
    """Download baseline Piper model and config files from Hugging Face if missing."""
    import urllib.request
    
    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/ha/ha_NG/openbible/medium"
    
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
        pcm = vits.synthesize(text, speaker_id=speaker_id)
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
    messages = [{"role": "system", "content": _voice_system_prompt()}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": transcript})
    
    try:
        response = await client.chat(model=OLLAMA_MODEL, messages=cast(Any, messages))
        return response["message"]["content"].strip()
    except Exception as ollama_err:
        logger.warning("Ollama unavailable for voice (%s), switching to Gemini...", ollama_err)
        return await _llm_respond_gemini(transcript, history)


async def _llm_respond_gemini(transcript: str, history: list[dict]) -> str:
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
                    system_instruction=_voice_system_prompt(),
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
        system_instruction=_voice_system_prompt(),
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
async def tts_endpoint(text: str, speaker_id: int = 0):
    """
    Synthesize text into speech using the custom VITS model and return a WAV file.
    """
    try:
        pcm = await asyncio.get_event_loop().run_in_executor(
            None, _synthesize_speech, text, speaker_id
        )
        if not pcm:
            raise HTTPException(status_code=500, detail="TTS synthesis failed")
            
        # Wrap the raw PCM-16 bytes in a WAV container
        wav_bytes = _add_wav_header(pcm, sample_rate=24000)
        return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as e:
        logger.exception("TTS endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))


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
