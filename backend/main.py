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
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from auth import verify_api_key, verify_admin_session
from rate_limit import limiter
from routers import (admin_auth, analytics, audio, chat, dictionary, document,
                     feedback, image, pronunciation, qa, waxal)
import admin_store
import analytics_store
import pronunciation_store
import qa_store


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
        # Corrections review/approval is gated by real admin accounts + server-
        # side sessions now (admin_store.py, routers/admin_auth.py), not a
        # shared bearer key. REVIEWER_API_KEY's role is just to seed the first
        # admin account on first boot (see admin_store.init_db) — it must
        # still be set once so there's a way to log in at all; after that
        # first login it plays no further role in gating requests. Left
        # unset, there would be no admin account and no way to approve
        # corrections, but a fresh production deploy must have SOME path in.
        reviewer_key = os.getenv("REVIEWER_API_KEY", "").strip()
        if not reviewer_key:
            raise RuntimeError(
                "REVIEWER_API_KEY must be set when APP_ENV=production. It seeds "
                "the first admin account (see admin_store.py); without it "
                "there is no way to log in and approve model-affecting "
                "corrections."
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
    # Startup: create/seed the admin accounts + sessions DB (see admin_store.py)
    admin_store.init_db()

    # Startup: create the visitor-analytics DB (see analytics_store.py)
    analytics_store.init_db()

    # Startup: create the pronunciation-corrections DB (human-in-the-loop TTS
    # loop — see pronunciation_store.py)
    pronunciation_store.init_db()

    # Startup: create the community Q&A DB (native-written instruction data for
    # the LLM training mix — see qa_store.py / docs/murya_roadmap.md)
    qa_store.init_db()

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

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "DELETE"],
    # X-Contributor-Id carries the anonymous per-device token (see
    # contributor.py). It MUST be listed here or the browser's CORS preflight
    # blocks every cross-origin chat/feedback request from app.murya.ng.
    allow_headers=["Content-Type", "X-API-Key", "X-Reviewer-Key", "X-Contributor-Id"],
)


@app.middleware("http")
async def _security_headers(request, call_next):
    """Baseline response headers. Cheap, standard hardening — doesn't change
    behavior for any existing client, just tells browsers not to guess content
    types or let the app be framed by another origin."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response

# ---------------------------------------------------------------------------
# Routers — all routes require the optional API key when configured
# ---------------------------------------------------------------------------
_auth = [Depends(verify_api_key)]

app.include_router(chat.router, prefix="/api", dependencies=_auth)
app.include_router(image.router, prefix="/api", dependencies=_auth)
# audio.router deliberately does NOT get the router-level _auth here (found
# missing entirely in a 2026-08-23 security review, but a router-level
# Security(APIKeyHeader) dependency is incompatible with the WebSocket route
# on this same router -- FastAPI/Starlette can't supply the HTTP Request
# object APIKeyHeader.__call__ requires for a WebSocket handshake, and
# raises a TypeError before the connection even opens. A browser's native
# WebSocket API also cannot set custom headers at all, so header-based auth
# could never work for /api/live from the real frontend regardless. Instead:
# /api/tts (a normal HTTP GET, fetch()-able, header-settable) gets _auth
# directly on its own route decorator in routers/audio.py; /api/live gets
# its own WebSocket-native, query-param-based check inside live_endpoint.
app.include_router(audio.router, prefix="/api")
# waxal.router serves the training-corpus browser (NeuralReview admin panel)
# — real admin session required, not just the optional API key, since this
# is internal review tooling rather than a public product endpoint.
app.include_router(waxal.router, prefix="/api", dependencies=[Depends(verify_admin_session)])
app.include_router(feedback.router, prefix="/api", dependencies=_auth)
app.include_router(admin_auth.router, prefix="/api")
# analytics.router: the /analytics/visit beacon is PUBLIC by design (fired on
# every page load), so it is NOT placed behind the optional API-key _auth
# dependency; /admin/analytics self-gates via verify_admin_session.
app.include_router(analytics.router, prefix="/api")
# pronunciation.router: /pronunciation/flag is a public user report (rate-limited,
# contributor-id); the /admin/pronunciation/* endpoints self-gate via
# verify_admin_session. Same public/admin split as analytics, so no global _auth.
app.include_router(pronunciation.router, prefix="/api")
# qa.router: /qa/submit is a public native-speaker contribution (rate-limited);
# /admin/qa/* self-gate via verify_admin_session. Same split as pronunciation.
app.include_router(qa.router, prefix="/api")
# document.router: one-shot translate/summarize (public product endpoint,
# same optional-API-key posture as chat).
app.include_router(document.router, prefix="/api", dependencies=_auth)
# dictionary.router: GET /dictionary?q=... is a public, read-only lookup over
# the same lexicon chat's hidden tool trigger already uses — no reason to
# gate it behind the API key any more than chat itself is.
app.include_router(dictionary.router, prefix="/api", dependencies=_auth)
# research.router (deep-research start/poll via Tavily Research) is DISCONTINUED
# for now (2026-08-22) — routers/research.py and tavily_service.py's research
# helpers are left in place, unregistered, for an easy future re-enable.


@app.get("/health")
async def health():
    return {"status": "sovereign", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# This is an API-only server — the real frontend is app.murya.ng (Vercel),
# not anything bundled here. Redirect a bare visit to the root there instead
# of serving a stale lookalike copy or a raw {"detail":"Not Found"}. Locally,
# FRONTEND_DEV_URL isn't set, so this falls back to the Vite dev server.
# ---------------------------------------------------------------------------
from fastapi.responses import RedirectResponse

_FRONTEND_DEV_URL = os.getenv("FRONTEND_DEV_URL", "http://localhost:3000")


@app.get("/")
async def root_redirect():
    return RedirectResponse(url=_FRONTEND_DEV_URL)
