"""
Shared slowapi rate limiter. In-memory, per-process — correct for the
current deployment (a single Fly.io machine, min_machines_running = 1 in
fly.toml; see docs/deployment.md) but does NOT coordinate across multiple
machines/workers. Revisit with a shared backend (e.g. Redis) before scaling
out horizontally.

`enabled` defaults on; the test suite turns it off (see tests/conftest.py)
since hundreds of requests fire against the same fake client IP within a
single pytest session and would otherwise trip the limits themselves.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from contributor import get_contributor_id

# Fallback key when the ASGI transport never populated request.client (some
# proxy paths don't) -- slowapi's own get_remote_address does request.client.host
# unguarded, which throws AttributeError on None and crashes the request with
# an opaque, unlogged connection error instead of a normal response. Found on
# admin_login: the ONLY login path into the admin dashboard, so a proxy
# misconfiguration that leaves request.client unset would lock the owner out
# with no error message to debug from. A single shared fallback key here is
# fine -- worst case a burst of such requests share one rate-limit bucket,
# which is strictly safer than crashing every one of them.
_NO_CLIENT_KEY = "no-client-info"


def _safe_get_remote_address(request) -> str:
    if request.client is None:
        return _NO_CLIENT_KEY
    return get_remote_address(request)


def _rate_limit_key(request) -> str:
    """Key limits on the anonymous per-device contributor token when present,
    falling back to the client IP.

    Rationale: carrier-grade NAT across the Sahel means many real users share
    one public IP, so per-IP limits are unfair (a few strangers can exhaust a
    whole carrier's quota). Keying on the device token spreads the budget per
    device instead. The trade-off is that a determined abuser could rotate
    tokens to get fresh buckets — acceptable at this stage; the next hardening
    step, if token-rotation abuse ever appears, is a per-IP hard ceiling
    applied alongside this (a second limiter), not replacing it.
    """
    cid = get_contributor_id(request)
    return f"cid:{cid}" if cid else _safe_get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)

# The hardening step this module's own docstring above already named as the
# right next move (found unaddressed in a 2026-08-23 security review): a
# genuine per-IP ceiling, stacked ALONGSIDE the per-device limiter above on
# specific high-risk endpoints -- not replacing it everywhere, which would
# actively hurt real users sharing a carrier-NAT IP. Call sites, each with an
# appropriate ceiling:
#   - /api/admin/login: exactly one legitimate caller exists (the founder),
#     so there is zero CGNAT-fairness tradeoff here -- a strict per-IP cap
#     closes the token-rotation brute-force bypass with no downside.
#   - /api/generate-image, /api/generate-video: real end users DO share IPs
#     under CGNAT, so this ceiling is deliberately generous (several
#     multiples of the per-device limit) -- it exists purely to cap a
#     runaway rotating-token abuser burning paid Gemini quota, not to
#     constrain ordinary shared-IP traffic.
#   - /api/chat, /api/document: a follow-up security-architecture review
#     (2026-08-23) found these were missed in the original pass -- they hit
#     the exact same paid Cerebras/Groq/Gemini fallback chain as the routes
#     above, so a rotating-token script had unbounded free calls against
#     paid quota on the app's two busiest endpoints. Same generous-multiple
#     reasoning as image/video: real chatting groups can share one IP.
#   - /api/tts: same review, same gap -- not a paid-API cost like the above,
#     but CPU/model-inference cost on the one shared VM, which a rotating-
#     token script could still burn unbounded.
ip_limiter = Limiter(key_func=_safe_get_remote_address)
