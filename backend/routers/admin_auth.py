"""
/api/admin/login, /api/admin/logout, /api/admin/me — real admin sessions.

Replaces the old pattern of typing REVIEWER_API_KEY into the frontend and
sending it as a raw X-Reviewer-Key header on every request. A login here
issues an HttpOnly, Secure session cookie instead — the credential never
touches JS, and corrections finally get a real "reviewed by" identity
(see admin_store.py, corrections_store.py).
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

import admin_audit_store
import admin_store
from auth import verify_admin_session
from rate_limit import ip_limiter, limiter

router = APIRouter()

_IS_PROD = os.getenv("APP_ENV", "development").strip().lower() == "production"


class LoginRequest(BaseModel):
    username: str = Field(..., max_length=100)
    password: str = Field(..., max_length=200)


def _set_session_cookie(response: Response, token: str) -> None:
    # Cross-site by design: the frontend (app.murya.ng) and this API
    # (hausa-ai-backend.fly.dev) are different registrable domains, so the
    # cookie must be SameSite=None (requires Secure) to be sent at all. In
    # dev (APP_ENV != production) both typically run over plain HTTP on the
    # same machine, where Secure/None cookies would be silently dropped by
    # the browser — fall back to Lax + non-Secure there.
    response.set_cookie(
        key=admin_store.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_IS_PROD,
        samesite="none" if _IS_PROD else "lax",
        max_age=12 * 3600,
        path="/",
    )


@router.post("/admin/login")
@limiter.limit("10/minute")
# Second, genuine per-IP ceiling -- the limiter above keys on a
# self-asserted, freely-rotatable X-Contributor-Id, so on its own it does
# NOT actually stop a scripted brute-force (a fresh random device id per
# attempt gets a fresh bucket every time). There's exactly one legitimate
# caller for this endpoint, so a strict IP-based cap has no fairness
# downside. See rate_limit.py's ip_limiter docstring.
@ip_limiter.limit("10/minute")
async def admin_login(request: Request, req: LoginRequest, response: Response):
    admin_id = admin_store.verify_login(req.username, req.password)
    if admin_id is None:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = admin_store.create_session(admin_id)
    _set_session_cookie(response, token)
    return {"username": req.username}


@router.post("/admin/logout")
async def admin_logout(request: Request, response: Response):
    token = request.cookies.get(admin_store.SESSION_COOKIE_NAME)
    if token:
        admin_store.delete_session(token)
    response.delete_cookie(admin_store.SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/admin/me")
async def admin_me(request: Request):
    token = request.cookies.get(admin_store.SESSION_COOKIE_NAME)
    username = admin_store.get_session_username(token) if token else None
    if username is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return {"username": username}


@router.get("/admin/audit-log")
async def audit_log(limit: int = 200, surface: str | None = None,
                    _admin: str = Depends(verify_admin_session)):
    """Unified, queryable trail of every admin action across corrections,
    pronunciation, and Q&A review (see admin_audit_store.py). Capped at 500
    rows per call regardless of the requested limit -- this is a review aid,
    not a bulk-export endpoint."""
    return {"items": admin_audit_store.list_recent(limit=min(max(limit, 1), 500), surface=surface)}
