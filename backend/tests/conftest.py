"""
Shared pytest fixtures for the backend test suite.

The test client is built against the FastAPI app defined in ``main.py``
with all heavy model loading mocked out so tests run offline and quickly.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

# Make sure the backend package root is importable when running tests directly.
sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_app():
    """Import the app after environment is set up."""
    # Prevent lazy-loaded heavy deps from being imported at collection time.
    from main import app  # noqa: PLC0415

    return app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def client():
    """Async test client wired to the FastAPI app."""
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
def mock_ollama_stream():
    """Return a callable that yields a single fake Ollama streaming chunk."""

    async def _stream(*_args, **_kwargs):
        yield {"message": {"content": "Sannu! "}}
        yield {"message": {"content": "Ranka ya dade."}}

    mock = AsyncMock()
    mock.chat = AsyncMock(side_effect=_stream)
    return mock
