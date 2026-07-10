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
