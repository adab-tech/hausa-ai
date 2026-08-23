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


@pytest.fixture(scope="session", autouse=True)
def _disable_rate_limiting():
    """The full suite fires far more than 20-30 requests/minute against the
    same fake client IP within one session-scoped `client` — without this,
    the rate limiter itself (not test logic) would start failing unrelated
    tests. test_rate_limiting.py re-enables it deliberately to verify the
    limiter actually works. ip_limiter (the per-IP ceiling added alongside
    the per-device limiter, see rate_limit.py) needs the same treatment for
    the same reason — every test request shares one fake client IP too."""
    import rate_limit

    rate_limit.limiter.enabled = False
    rate_limit.ip_limiter.enabled = False
    yield
    rate_limit.limiter.enabled = True
    rate_limit.ip_limiter.enabled = True


@pytest.fixture(scope="session")
async def client():
    """Async test client wired to the FastAPI app."""
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def admin_session(client, tmp_path, monkeypatch):
    """Isolate admin_store to a scratch SQLite file, seed a known test admin,
    and log the shared test `client` into a real session cookie. Request this
    fixture from any test that needs an authenticated admin; the client
    stays session-scoped, so this logs out again on teardown to avoid
    leaking an authenticated cookie into unrelated tests."""
    import admin_store

    monkeypatch.setattr(admin_store, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(admin_store, "_DB_PATH", tmp_path / "admin.db")
    admin_store.init_db()
    admin_store.create_admin("testadmin", "testpass123")

    resp = await client.post(
        "/api/admin/login", json={"username": "testadmin", "password": "testpass123"}
    )
    assert resp.status_code == 200, resp.text

    yield "testadmin"

    await client.post("/api/admin/logout")


@pytest.fixture(scope="session")
def mock_ollama_stream():
    """Return a callable that yields a single fake Ollama streaming chunk."""

    async def _stream(*_args, **_kwargs):
        yield {"message": {"content": "Sannu! "}}
        yield {"message": {"content": "Ranka ya dade."}}

    mock = AsyncMock()
    mock.chat = AsyncMock(side_effect=_stream)
    return mock
