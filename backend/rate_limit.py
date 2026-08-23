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
    return f"cid:{cid}" if cid else get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)

# The hardening step this module's own docstring above already named as the
# right next move (found unaddressed in a 2026-08-23 security review): a
# genuine per-IP ceiling, stacked ALONGSIDE the per-device limiter above on
# specific high-risk endpoints -- not replacing it everywhere, which would
# actively hurt real users sharing a carrier-NAT IP. Two call sites, two very
# different appropriate ceilings:
#   - /api/admin/login: exactly one legitimate caller exists (the founder),
#     so there is zero CGNAT-fairness tradeoff here -- a strict per-IP cap
#     closes the token-rotation brute-force bypass with no downside.
#   - /api/generate-image, /api/generate-video: real end users DO share IPs
#     under CGNAT, so this ceiling is deliberately generous (several
#     multiples of the per-device limit) -- it exists purely to cap a
#     runaway rotating-token abuser burning paid Gemini quota, not to
#     constrain ordinary shared-IP traffic.
ip_limiter = Limiter(key_func=get_remote_address)
