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
