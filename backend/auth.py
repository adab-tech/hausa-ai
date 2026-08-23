"""
Optional API-key authentication for the Hausa AI backend.

Set the ``API_KEY`` environment variable to a secret value to enable
authentication.  When set, every request must carry the header::

    X-API-Key: <your-key>

When ``API_KEY`` is not set (the default for a fully local deployment),
authentication is disabled and all requests are allowed through.
"""

import hmac
import os
from urllib.parse import urlparse

from fastapi import HTTPException, Request, Security, status
from fastapi.security.api_key import APIKeyHeader

import admin_store

_API_KEY_NAME = "X-API-Key"
_api_key_header = APIKeyHeader(name=_API_KEY_NAME, auto_error=False)

_CONFIGURED_KEY: str | None = os.getenv("API_KEY")


async def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency — enforce API key when one is configured."""
    if not api_key_valid(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Set the X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


def api_key_valid(candidate: str | None) -> bool:
    """Plain (non-dependency-injected) API key check, usable anywhere the
    key string has already been pulled from somewhere other than the
    X-API-Key header -- specifically for /api/live: a WebSocket route can't
    use Security(APIKeyHeader) as a router-level dependency (FastAPI can't
    supply the HTTP Request object APIKeyHeader.__call__ requires during a
    WebSocket handshake, and raises before the connection even opens), and
    a browser's native WebSocket API can't set custom headers at all
    regardless. True means access is allowed -- either no key is
    configured (open access, the self-hosted default) or the candidate
    matches."""
    if _CONFIGURED_KEY is None:
        return True
    return candidate is not None and hmac.compare_digest(candidate, _CONFIGURED_KEY)


_REVIEWER_KEY_NAME = "X-Reviewer-Key"
_reviewer_key_header = APIKeyHeader(name=_REVIEWER_KEY_NAME, auto_error=False)

_CONFIGURED_REVIEWER_KEY: str | None = os.getenv("REVIEWER_API_KEY")


async def verify_reviewer_key(reviewer_key: str | None = Security(_reviewer_key_header)) -> None:
    """Deprecated: superseded by verify_admin_session (real accounts + a
    session cookie instead of one shared secret). Kept only as a documented,
    unused fallback in case admin.db is ever lost and REVIEWER_API_KEY needs
    to re-seed a fresh bootstrap admin (see admin_store.init_db).
    """
    if _CONFIGURED_REVIEWER_KEY is None:
        # No reviewer key configured → open access (self-hosted/dev default).
        return
    if reviewer_key is None or not hmac.compare_digest(reviewer_key, _CONFIGURED_REVIEWER_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing reviewer key. Set the X-Reviewer-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


async def verify_admin_session(request: Request) -> str:
    """FastAPI dependency — gates correction review/approval endpoints.

    Real per-admin identity via a server-side session (SQLite-backed,
    HttpOnly cookie) instead of a single shared bearer secret — see
    admin_store.py and routers/admin_auth.py. Returns the authenticated
    admin's username (so callers can record who approved what); raises 401
    if there's no valid session. This is the gate that decides what the
    model actually learns from user corrections, so it must not be left
    open — see routers/feedback.py.
    """
    token = request.cookies.get(admin_store.SESSION_COOKIE_NAME)
    username = admin_store.get_session_username(token) if token else None
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin session required. Log in at /admin/login.",
        )
    return username


_ALLOWED_ORIGINS_RAW = os.getenv("ALLOWED_ORIGINS", "*").strip()
_ALLOWED_ORIGINS_SET: set[str] | None = (
    None if _ALLOWED_ORIGINS_RAW == "*"
    else {o.strip() for o in _ALLOWED_ORIGINS_RAW.split(",") if o.strip()}
)


async def verify_csrf_origin(request: Request) -> None:
    """CSRF guard for admin state-changing routes gated only by the session
    cookie. The cookie is SameSite=None by necessity (admin_store.py --
    app.murya.ng and the API domain differ, so SameSite=Lax/Strict would
    break every admin request), which means the browser attaches it to
    cross-site requests too. Routes that accept multipart/form-data (a CORS
    "simple" content type, e.g. the pronunciation admin recording endpoints)
    trigger no preflight, so CORS's allow_origins list is never even
    consulted for them -- a malicious page's auto-submitting <form> reaches
    the route with a valid session cookie attached. This checks Origin
    (falling back to Referer, since some browsers omit Origin on same-site
    navigations) against ALLOWED_ORIGINS by hand, closing exactly the gap
    CORS doesn't cover. No-op when ALLOWED_ORIGINS='*' (open dev config,
    nothing trusted to check against)."""
    if _ALLOWED_ORIGINS_SET is None:
        return
    origin = request.headers.get("origin")
    if not origin:
        referer = request.headers.get("referer")
        if referer:
            parsed = urlparse(referer)
            if parsed.scheme and parsed.netloc:
                origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in _ALLOWED_ORIGINS_SET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-site request blocked.",
        )
