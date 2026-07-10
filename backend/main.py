"""
Hausa AI — Self-Hosted Backend
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
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import verify_api_key
from routers import audio, chat, feedback, image, waxal


def _validate_runtime_config() -> None:
    """Fail fast on invalid or unsafe runtime configuration."""
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    api_key = os.getenv("API_KEY", "").strip()
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").strip()
    ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434").strip()

    parsed = urlparse(ollama_host)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(
            "Invalid OLLAMA_HOST. Expected a full http(s) URL, "
            f"got: {ollama_host!r}"
        )

    if app_env == "production":
        if allowed_origins == "*":
            raise RuntimeError(
                "ALLOWED_ORIGINS='*' is not allowed in production. "
                "Set explicit trusted origins."
            )
        # The reviewer gate is the security boundary that actually matters for a
        # PUBLIC deployment (a tool real Hausa speakers use freely): it controls
        # who may approve user-submitted corrections that get folded into the
        # model's system prompt. Left open, anyone could poison the model through
        # the corrections queue — so it is required in production.
        reviewer_key = os.getenv("REVIEWER_API_KEY", "").strip()
        if not reviewer_key:
            raise RuntimeError(
                "REVIEWER_API_KEY must be set when APP_ENV=production. It gates "
                "who can approve model-affecting corrections; without it the "
                "human-in-the-loop learning queue is open to poisoning."
            )
        # API_KEY is OPTIONAL. Set it only for a private/firewalled deployment —
        # in a public single-page app it cannot be a real secret (the frontend
        # bundle would expose it), so it must not be relied on as one. The
        # public endpoints (chat/tts/feedback) stay open by design; abuse is
        # bounded by restricted ALLOWED_ORIGINS and, when configured, rate limits.
        _ = api_key  # intentionally not required in production


_validate_runtime_config()

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

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Pre-load STT and TTS models to avoid cold-start latency
    import logging
    startup_logger = logging.getLogger("uvicorn.error")
    startup_logger.info("[Murya] Pre-loading speech models to prevent live cold-starts...")
    try:
        from routers.audio import _get_whisper, _get_vits, _get_piper
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Pre-load Whisper model in executor
        await loop.run_in_executor(None, _get_whisper)
        startup_logger.info("[Murya] Pre-load: Whisper STT model loaded successfully.")
        
        # Pre-load custom VITS ONNX model in executor
        await loop.run_in_executor(None, _get_vits)
        startup_logger.info("[Murya] Pre-load: Custom VITS ONNX model loaded successfully.")
        
        # Pre-load baseline Piper TTS in executor
        await loop.run_in_executor(None, _get_piper)
        startup_logger.info("[Murya] Pre-load: Baseline Piper TTS model loaded successfully.")
    except Exception as startup_err:
        startup_logger.warning("[Murya] Pre-load warning: %s", startup_err)
        
    yield

app = FastAPI(
    title="Murya — Sovereign Hausa AI Backend",
    description="Self-hosted replacement for Google Gemini APIs",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key", "X-Reviewer-Key"],
)

# ---------------------------------------------------------------------------
# Routers — all routes require the optional API key when configured
# ---------------------------------------------------------------------------
_auth = [Depends(verify_api_key)]

app.include_router(chat.router, prefix="/api", dependencies=_auth)
app.include_router(image.router, prefix="/api", dependencies=_auth)
app.include_router(audio.router, prefix="/api")
app.include_router(waxal.router, prefix="/api", dependencies=_auth)
app.include_router(feedback.router, prefix="/api", dependencies=_auth)


@app.get("/health")
async def health():
    return {"status": "sovereign", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Serve static frontend files (Single-Container Deployment)
# ---------------------------------------------------------------------------
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi import HTTPException

# Path to the compiled React build (dist folder)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DIST_DIR = os.path.join(_BASE_DIR, "dist")

if os.path.exists(_DIST_DIR):
    # Mount assets folder for bundle resources (JS/CSS/images)
    _assets_dir = os.path.join(_DIST_DIR, "assets")
    if os.path.exists(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")
    
    # Mount main banner at root level
    @app.get("/hausa_ai_banner.png")
    async def serve_banner():
        dist_banner = os.path.join(_DIST_DIR, "hausa_ai_banner.png")
        if os.path.exists(dist_banner):
            return FileResponse(dist_banner)
        workspace_banner = os.path.join(os.path.dirname(_BASE_DIR), "hausa_ai_banner.png")
        if os.path.exists(workspace_banner):
            return FileResponse(workspace_banner)
        raise HTTPException(status_code=404, detail="Banner not found")

    # Serve index.html for root and SPA routing fallbacks
    @app.get("/{fallback_path:path}")
    async def spa_fallback(fallback_path: str):
        if fallback_path.startswith("api/") or fallback_path == "health":
            raise HTTPException(status_code=404, detail="Not Found")
            
        index_file = os.path.join(_DIST_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend build missing")
else:
    # Dev mode: no compiled frontend is bundled with the backend, so the app is
    # served by the Vite dev server. Redirect the bare API root there instead of
    # returning a raw {"detail":"Not Found"} 404.
    _FRONTEND_DEV_URL = os.getenv("FRONTEND_DEV_URL", "http://localhost:3000")

    @app.get("/")
    async def _dev_root_redirect():
        return RedirectResponse(url=_FRONTEND_DEV_URL)
