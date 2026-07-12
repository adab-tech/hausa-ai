"""
/api/analytics/visit  — PUBLIC visitor beacon (numbers + rough geography).
/api/admin/analytics  — ADMIN-gated summary for the dashboard.

Privacy: no IP addresses, no PII. Uniqueness is counted via the anonymous
per-device token in the X-Contributor-Id header (see contributor.py), and
geography is derived from the browser's IANA timezone string sent in the
beacon body — never from IP. See analytics_store.py for the storage model.

The visit beacon is PUBLIC by design (it must fire from every page load, so
it is not placed behind the optional API-key dependency). The admin summary
self-gates via verify_admin_session.
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

import analytics_store
from auth import verify_admin_session
from contributor import get_contributor_id
from rate_limit import limiter

router = APIRouter()


class VisitBeacon(BaseModel):
    timezone: str | None = Field(None, max_length=64)
    lang: str | None = Field(None, max_length=16)
    path: str | None = Field(None, max_length=128)


@router.post("/analytics/visit")
@limiter.limit("60/minute")
async def record_visit(request: Request, beacon: VisitBeacon):
    """Public beacon. Must never error the client — any failure still returns
    ok so a broken analytics write can't degrade the user's experience."""
    try:
        analytics_store.record_visit(
            contributor_id=get_contributor_id(request),
            timezone=beacon.timezone,
            lang=beacon.lang,
            path=beacon.path,
        )
    except Exception:
        pass
    return {"ok": True}


@router.get("/admin/analytics")
async def admin_analytics(_admin: str = Depends(verify_admin_session)):
    """Admin-gated visitor-analytics summary for the dashboard."""
    return analytics_store.summary()
