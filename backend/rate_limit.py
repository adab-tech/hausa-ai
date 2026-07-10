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

limiter = Limiter(key_func=get_remote_address)
