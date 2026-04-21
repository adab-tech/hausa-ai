"""
Optional API-key authentication for the Vertex Sovereign backend.

Set the ``API_KEY`` environment variable to a secret value to enable
authentication.  When set, every request must carry the header::

    X-API-Key: <your-key>

When ``API_KEY`` is not set (the default for a fully local deployment),
authentication is disabled and all requests are allowed through.
"""

import os

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

_API_KEY_NAME = "X-API-Key"
_api_key_header = APIKeyHeader(name=_API_KEY_NAME, auto_error=False)

_CONFIGURED_KEY: str | None = os.getenv("API_KEY")


async def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency — enforce API key when one is configured."""
    if _CONFIGURED_KEY is None:
        # No key configured → open access (self-hosted default).
        return
    if api_key != _CONFIGURED_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Set the X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
