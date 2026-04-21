"""
Vertex Sovereign — Self-Hosted Backend
FastAPI app that replaces Google Gemini/Veo/Live APIs with open-source equivalents:
  • Text  : Ollama (Aya-23 8B / Llama 3.1 8B)
  • Image : Diffusers FLUX.1-schnell / Stable Diffusion
  • Audio : faster-whisper (STT) + Ollama (LLM) + Piper TTS

Environment variables
---------------------
ALLOWED_ORIGINS
    Comma-separated list of permitted CORS origins.
    Default ``*`` (allow all) is fine for a fully local/self-hosted deployment.
    Example: ``http://localhost:3000,https://my-frontend.example.com``

API_KEY
    Optional shared secret.  When set, callers must supply the header
    ``X-API-Key: <value>`` on every request.  Leave unset to disable auth
    (suitable for a local, firewalled deployment).
"""

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import verify_api_key
from routers import audio, chat, image

# ---------------------------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------------------------
_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
if _raw_origins.strip() == "*":
    _allowed_origins: list[str] = ["*"]
    _allow_credentials = False  # credentials cannot be used with wildcard origin
else:
    _allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
    _allow_credentials = True

app = FastAPI(
    title="Vertex Sovereign — Local AI Backend",
    description="Self-hosted replacement for Google Gemini APIs",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# ---------------------------------------------------------------------------
# Routers — all routes require the optional API key when configured
# ---------------------------------------------------------------------------
_auth = [Depends(verify_api_key)]

app.include_router(chat.router, prefix="/api", dependencies=_auth)
app.include_router(image.router, prefix="/api", dependencies=_auth)
app.include_router(audio.router, prefix="/api", dependencies=_auth)


@app.get("/health")
async def health():
    return {"status": "sovereign", "version": "1.0.0"}
