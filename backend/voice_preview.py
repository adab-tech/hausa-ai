"""Authenticated Railway preview of Murya's existing Hausa ONNX engine."""

import hmac
import io
import os
import re
from contextlib import asynccontextmanager
from threading import BoundedSemaphore
import wave

from fastapi import FastAPI, Header, HTTPException, Request, Response
from gyara import normalize_digits, prepare_for_speech
from pydantic import BaseModel, Field

from vits_engine import OUTPUT_SAMPLE_RATE, VitsEngine


ASABE = 6
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
    token = os.environ.get("MURYA_VOICE_PREVIEW_TOKEN", "")
    if len(token) < 32 or not token.isascii():
        raise RuntimeError("Set an ASCII preview token of at least 32 characters.")
    engine = VitsEngine()
    if not engine.synthesize(prepare_preview_text(TEST_PHRASE), speaker_id=ASABE):
        raise RuntimeError("Murya speech model did not pass initial synthesis.")
    app.state.token = token.encode("ascii")
    app.state.engine = engine
    app.state.slot = BoundedSemaphore(1)
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


class VoiceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=300)


@app.get("/health")
def health():
    return {"status": "ok", "voice": "asabe"}


@app.post("/preview/speech")
def speech(payload: VoiceRequest, request: Request, authorization: str = Header(default="")):
    expected = b"Bearer " + request.app.state.token
    if not hmac.compare_digest(authorization.encode("utf-8"), expected):
        raise HTTPException(status_code=401, detail="Invalid or missing preview credentials")
    text = prepare_preview_text(payload.text)
    if not text:
        raise HTTPException(status_code=422, detail="Text is required")
    slot = request.app.state.slot
    if not slot.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Voice preview is busy", headers={"Retry-After": "1"})
    try:
        pcm = request.app.state.engine.synthesize(text, speaker_id=ASABE)
        if not pcm:
            raise HTTPException(status_code=422, detail="Unable to synthesize speech from this text")
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(OUTPUT_SAMPLE_RATE)
            wav.writeframes(pcm)
        return Response(output.getvalue(), media_type="audio/wav", headers={"Cache-Control": "no-store"})
    finally:
        slot.release()
