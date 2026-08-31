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

SENTRY_DSN
    Optional. When set, backend errors and explicit capture_message() calls
    (e.g. the whole LLM provider chain failing on one request -- see
    routers/chat.py's fetch_stream) are reported to Sentry instead of only
    existing in docker logs someone has to think to grep. Leave unset to
    disable entirely (the default) -- no behavior change, no dependency on
    an external service for a purely self-hosted deployment.
"""

import os
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import sentry_sdk
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from auth import verify_api_key, verify_admin_session
from rate_limit import limiter
from routers import (admin_auth, analytics, audio, chat, dictionary, document,
                     feedback, image, mos, pronunciation, qa, waxal)
import admin_audit_store
import admin_store
import analytics_store
import mos_store
import pronunciation_store
import qa_store
import seed_mos_stimuli


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
        if not allowed_origins:
            # ALLOWED_ORIGINS="" (set but empty-after-strip) previously slipped
            # past this check silently -- it isn't "*" so the wildcard guard
            # above didn't catch it, and it went on to configure
            # allow_origins=[] below, blocking ALL cross-origin traffic while
            # /health still reported healthy. Fail fast instead.
            raise RuntimeError(
                "ALLOWED_ORIGINS is empty in production. Set explicit "
                "comma-separated trusted origins (or leave the variable "
                "entirely unset only in non-production environments)."
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
# Error tracking (optional -- see SENTRY_DSN in the module docstring)
# ---------------------------------------------------------------------------
_sentry_dsn = os.getenv("SENTRY_DSN", "").strip()
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        environment=os.getenv("APP_ENV", "development"),
        # Error tracking only -- no performance/trace sampling. This is a
        # single small self-hosted box; the free tier's event quota should
        # go to actual errors, not request traces.
        traces_sample_rate=0.0,
        # Self-hosted, privacy-conscious project (see rate_limit.py's own
        # reasoning about not over-collecting from users) -- don't attach
        # request IPs/cookies/headers to error reports by default.
        send_default_pii=False,
    )

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

    # Startup: create + seed the MOS listening-test DB (naturalness eval
    # gate before a voice/correction batch feeds the next retrain — see
    # mos_store.py / seed_mos_stimuli.py). Seeding is idempotent (no-op once
    # stimuli already exist) so this is cheap on every restart after the first.
    mos_store.init_db()
    seed_mos_stimuli.seed_if_empty()

    # Startup: create the community Q&A DB (native-written instruction data for
    # the LLM training mix — see qa_store.py / docs/murya_roadmap.md)
    qa_store.init_db()

    # Startup: create the unified admin audit-log DB (who approved/rejected/
    # deleted what, when, across corrections/pronunciation/Q&A review — see
    # admin_audit_store.py)
    admin_audit_store.init_db()

    # Startup: Pre-load STT and TTS models to avoid cold-start latency.
    #
    # This used to swallow ALL exceptions and only log a warning -- a broken
    # or missing VITS/Whisper/Piper model at boot left the process running
    # with /health reporting "sovereign" regardless, so the only way to
    # discover the deployment was actually broken was an end-user's TTS/STT
    # request failing. Track success/failure on app.state instead so /health
    # can distinguish degraded from healthy, while still NOT crashing the
    # process on a preload failure (a transient model-download hiccup at
    # boot shouldn't take the whole API down -- other endpoints, e.g. text
    # chat, work fine without these models).
    app.state.model_preload_ok = True
    app.state.model_preload_error = None
    import asyncio
    import logging
    loop = asyncio.get_event_loop()
    startup_logger = logging.getLogger("uvicorn.error")
    startup_logger.info("[Murya] Pre-loading speech models to prevent live cold-starts...")
    try:
        from routers.audio import _get_whisper, _get_vits, _get_piper

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
        app.state.model_preload_ok = False
        app.state.model_preload_error = str(startup_err)

    # Startup: pre-load the dictionary lexicon (Robinson 1914 + Wiktionary +
    # Newman 1977, ~30,700 entries total) off the event loop too. This used
    # to be lazily parsed in-line on whatever request first triggered it
    # (chat's "ma'anar kalmar" tool, or GET /api/dictionary) -- that one
    # unlucky request would block the event loop for the full parse.
    # dictionary_service already degrades gracefully on its own (
    # dictionary_ready() False, define() returns []) if this fails, so a
    # failure here is just logged, not tracked on app.state like the
    # TTS/STT models above -- text chat works fine without the dictionary.
    try:
        import services.dictionary_service as dictionary_service

        await loop.run_in_executor(None, dictionary_service.dictionary_ready)
        startup_logger.info(
            "[Murya] Pre-load: dictionary lexicon loaded (ready=%s).",
            dictionary_service.dictionary_ready(),
        )
    except Exception as dict_err:
        startup_logger.warning("[Murya] Dictionary pre-load warning: %s", dict_err)

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

# CORSMiddleware is added LAST, deliberately: Starlette's add_middleware()
# inserts each new middleware at the front of the stack (see
# starlette.applications.Starlette.add_middleware), so the middleware added
# LAST ends up OUTERMOST at request time. It used to be registered before
# the _security_headers middleware above, which meant _security_headers -- a
# plain function middleware registered afterward via the decorator, which
# also calls add_middleware under the hood -- ended up wrapping CORS instead
# of the other way around. Practically: any response produced by an inner
# layer (rate-limit rejections, the security-headers middleware itself
# erroring, etc.) could miss CORS headers, which browsers report as an
# opaque network failure rather than the real error. Adding CORS after every
# other app.add_middleware()/@app.middleware() call keeps it the outermost
# layer, so it wraps everything else in the stack.
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
# mos.router: /mos/session and /mos/audio/* are public, anonymous, rate-limited
# (a login wall would kill volunteer participation); /admin/mos/* self-gates
# via verify_admin_session. Same split as pronunciation.
app.include_router(mos.router, prefix="/api")

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
    # Existing shape ({"status": "sovereign", "version": ...}) is preserved
    # unconditionally for other callers -- "degraded"/"degraded_reason"/
    # "commit" are additive fields, so this doesn't change behavior for any
    # caller that only checks "status"/"version". "commit" is the git SHA
    # baked into the image at build time (Dockerfile's GIT_SHA build arg) --
    # a deploy pipeline diffs this against the commit it just pushed to
    # confirm the NEW code is actually running, not just that some process
    # answers on the port (see Dockerfile's comment on GIT_SHA for why this
    # exists: a stale, never-restarted container returns this exact same
    # payload otherwise, indistinguishable from a real deploy).
    payload = {
        "status": "sovereign",
        "version": "1.0.0",
        "commit": os.getenv("GIT_SHA", "unknown"),
    }
    if not getattr(app.state, "model_preload_ok", True):
        payload["degraded"] = True
        payload["degraded_reason"] = getattr(
            app.state, "model_preload_error", "model preload failed"
        )
    return payload


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
