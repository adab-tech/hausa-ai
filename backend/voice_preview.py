"""Authenticated Railway preview of Murya's existing Hausa ONNX engine."""

import hmac
import io
import os
from contextlib import asynccontextmanager
from threading import BoundedSemaphore
import wave

from fastapi import FastAPI, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from vits_engine import OUTPUT_SAMPLE_RATE, VitsEngine


ASABE = 6
TEST_PHRASE = "Sannu da zuwa."


@asynccontextmanager
async def lifespan(app: FastAPI):
    token = os.environ.get("MURYA_VOICE_PREVIEW_TOKEN", "")
    if len(token) < 32 or not token.isascii():
        raise RuntimeError("Set an ASCII preview token of at least 32 characters.")
    engine = VitsEngine()
    if not engine.synthesize(TEST_PHRASE, speaker_id=ASABE):
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
    if not payload.text.strip():
        raise HTTPException(status_code=422, detail="Text is required")
    slot = request.app.state.slot
    if not slot.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Voice preview is busy", headers={"Retry-After": "1"})
    try:
        pcm = request.app.state.engine.synthesize(payload.text, speaker_id=ASABE)
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
