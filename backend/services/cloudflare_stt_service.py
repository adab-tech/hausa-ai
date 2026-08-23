"""
Cloudflare Workers AI — hosted Whisper speech-to-text, used as the PRIMARY
STT path when configured, with local faster-whisper as the automatic
fallback (see routers/audio.py's _transcribe).

Why this exists: local Whisper on the Fly box competes for the same limited
RAM/CPU as Ollama and Piper TTS — this is the exact resource pressure that's
been causing Ollama to fail its first-token timeout on effectively every
request (see routers/chat.py's stream_ollama docstring). Offloading STT to
Cloudflare's free tier (10,000 Neurons/day; Whisper costs ~46.63 neurons per
audio-minute, so this budget goes a long way for current traffic) relieves
that pressure without giving up STT entirely when unconfigured or on error.

Design contract — same graceful degradation as every other optional service
in this project (tavily_service.py, you_service.py):
  * With no CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID, cloudflare_stt_enabled()
    is False and transcribe_via_cloudflare() returns None without any network
    call. The caller then falls back to local Whisper exactly as before.
  * ANY error, timeout, or malformed response also yields None — this
    function NEVER raises into the request path.

Verified live against the real API (2026-08-23): confirmed base64 WAV input,
confirmed "ha" is accepted as a `language` hint (language_probability: 1.0).
"""

import base64
import logging
import os

import httpx

logger = logging.getLogger("murya.cloudflare_stt")

_MODEL = "@cf/openai/whisper-large-v3-turbo"
_TIMEOUT_SECONDS = 20.0


def _get_credentials() -> tuple[str, str] | None:
    token = os.getenv("CLOUDFLARE_API_TOKEN")
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    if not token or not account_id:
        return None
    return token, account_id


def cloudflare_stt_enabled() -> bool:
    """True iff both CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID are set."""
    return _get_credentials() is not None


async def transcribe_via_cloudflare(wav_bytes: bytes, language: str = "ha") -> str | None:
    """Transcribe `wav_bytes` (a complete WAV file) via Cloudflare Workers AI's
    hosted Whisper. Returns the transcript string, or None on missing
    credentials, timeout, or any error — never raises. An empty-but-successful
    transcription (silence) returns "" (falsy, same as the local-Whisper path),
    which the caller already treats as "no speech"."""
    creds = _get_credentials()
    if creds is None:
        return None
    token, account_id = creds

    endpoint = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{_MODEL}"
    payload = {
        "audio": base64.b64encode(wav_bytes).decode("ascii"),
        "language": language,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as err:  # noqa: BLE001 — must never propagate into request path
        logger.warning("Cloudflare STT failed (%s: %s)", type(err).__name__, err)
        return None

    if not data.get("success"):
        logger.warning("Cloudflare STT returned success=false: %s", data.get("errors"))
        return None

    text = (data.get("result") or {}).get("text") or ""
    return text.strip()
