"""
Anonymous contributor identity — Level 1, no login wall.

A PII-free device token (a UUID the browser generates once and keeps in
localStorage) sent as the ``X-Contributor-Id`` header, or a ``contributor_id``
query param where a header isn't possible (the TTS ``<audio>`` element and the
live WebSocket). It identifies a *device*, not a person, and collects nothing.

Why it exists:
  - Fairer rate limiting. Carrier-grade NAT is the norm across the Sahel, so
    thousands of real users share one public IP; per-IP limits would let a
    few strangers exhaust a whole carrier's quota. Keying limits on the
    device token (when present) fixes that, falling back to IP otherwise.
  - Feedback/correction attribution. Knowing which anonymous device a
    correction came from lets the human-review queue dedupe and weight
    contributors — without a login or any personal data.

The token is validated as a UUID before use so a client can't inject
arbitrary or oversized rate-limit keys (unbounded distinct keys would be a
memory-exhaustion vector).
"""

import re

from fastapi import Request

# Accept any RFC-4122-shaped UUID (we don't require version 4 specifically —
# the point is a bounded, well-formed key, not cryptographic provenance).
_CID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def get_contributor_id(request: Request) -> str | None:
    """Return the validated anonymous contributor id for this request, or None.

    Prefers the ``X-Contributor-Id`` header; falls back to the
    ``contributor_id`` query param (used by the TTS/WebSocket surfaces that
    can't set headers). Returns None if absent or malformed.
    """
    cid = request.headers.get("X-Contributor-Id") or request.query_params.get("contributor_id")
    if cid and _CID_RE.match(cid):
        return cid.lower()
    return None
