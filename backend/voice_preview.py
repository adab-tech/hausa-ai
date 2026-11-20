"""Authenticated Railway service for Murya's Hausa chat and ONNX speech engine."""

import hmac
import os
import re
from contextlib import asynccontextmanager
from threading import BoundedSemaphore
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from gyara import normalize_digits, prepare_for_speech
from pydantic import BaseModel, Field
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

import admin_audit_store
import admin_store
import pronunciation_store
from rate_limit import limiter
from routers import admin_auth, chat, pronunciation
from vits_engine import OUTPUT_SAMPLE_RATE, VitsEngine


ASABE = 6
GARBA = 0
REVIEW_VOLUME = "/app/review-data"
TEST_PHRASE = "An gina birnin a ƙarni na 14."
_ORDINAL_SUFFIX = r"(?:i[eè]mes?|[eè]mes?|er|re|e|st|nd|rd|th|[ºªᵉ])"
_CENTURY_ORDINAL = re.compile(
    rf"\b[kƙ]arni(?:\s+na)?\s+([0-9]+){_ORDINAL_SUFFIX}?(?!\w)"
    rf"|\b([0-9]+){_ORDINAL_SUFFIX}\s+(?:si[èe]cle|century)\b",
    re.IGNORECASE,
)


def prepare_preview_text(text: str) -> str:
    """Restore century ordinals before applying Murya's shared speech rules."""
    text = _CENTURY_ORDINAL.sub(
        lambda match: f"ƙarni na {match[1] or match[2]}", normalize_digits(text)
    )
    return prepare_for_speech(text)


@asynccontextmanager
async def lifespan(app: FastAPI):
    token = os.environ.get("MURYA_RAILWAY_TOKEN", "")
    if len(token) < 32 or not token.isascii():
        raise RuntimeError("Set an ASCII relay token of at least 32 characters.")
    engine = VitsEngine()
    for speaker_id in (ASABE, GARBA):
        if not engine.synthesize(prepare_preview_text(TEST_PHRASE), speaker_id=speaker_id):
            raise RuntimeError(f"Murya speech model did not pass synthesis for speaker {speaker_id}.")
    app.state.token = token.encode("ascii")
    app.state.engine = engine
    app.state.slot = BoundedSemaphore(1)
    app.state.review_ready = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH") == REVIEW_VOLUME
    if app.state.review_ready:
        pronunciation_store.init_db()
        admin_store.init_db()
        admin_audit_store.init_db()
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def verify_relay(request: Request, authorization: str = Header(default="")):
    expected = b"Bearer " + request.app.state.token
    if not hmac.compare_digest(authorization.encode("utf-8"), expected):
        raise HTTPException(status_code=401, detail="Invalid or missing relay credentials")


def require_review_storage(request: Request):
    if not request.app.state.review_ready:
        raise HTTPException(status_code=503, detail="Pronunciation review storage is unavailable")


def require_chat_provider():
    if not os.environ.get("GROQ_API_KEY", "").strip():
        raise HTTPException(status_code=503, detail="Chat provider is not configured")


review_dependencies = [Depends(verify_relay), Depends(require_review_storage)]
app.include_router(pronunciation.router, prefix="/api", dependencies=review_dependencies)
app.include_router(admin_auth.router, prefix="/api", dependencies=review_dependencies)
app.include_router(chat.router, prefix="/api", dependencies=[*review_dependencies, Depends(require_chat_provider)])


class VoiceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    speaker_id: Literal[0, 6] = ASABE


@app.get("/health")
def health(request: Request):
    return {
        "status": "ok", "voice": "asabe", "voices": ["asabe", "garba"],
        "pronunciation_storage": request.app.state.review_ready,
        "chat_configured": bool(os.environ.get("GROQ_API_KEY", "").strip()),
    }


@app.post("/relay/speech", dependencies=review_dependencies)
def speech(payload: VoiceRequest, request: Request):
    pcm, spoken_text = None, None
    if request.app.state.review_ready:
        pcm, spoken_text = pronunciation_store.resolve(payload.text, payload.speaker_id)
    if pcm:
        return speech_response(pcm)
    text = prepare_preview_text(spoken_text or payload.text)
    if not text:
        raise HTTPException(status_code=422, detail="Text is required")
    slot = request.app.state.slot
    if not slot.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Voice service is busy", headers={"Retry-After": "1"})
    try:
        pcm = request.app.state.engine.synthesize(text, speaker_id=payload.speaker_id)
        if not pcm:
            raise HTTPException(status_code=422, detail="Unable to synthesize speech from this text")
        return speech_response(pcm)
    finally:
        slot.release()


def speech_response(pcm: bytes) -> Response:
    return Response(
        pronunciation_store.pcm_to_wav(pcm, sample_rate=OUTPUT_SAMPLE_RATE),
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )
