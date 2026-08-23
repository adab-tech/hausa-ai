"""Verifies the slowapi rate limiter is actually wired up, not just present
in the decorator source. Disabled globally for the rest of the suite (see
conftest.py's autouse _disable_rate_limiting) since normal test traffic
would otherwise trip these same limits."""

import pytest


@pytest.fixture
def _rate_limiting_enabled():
    import rate_limit

    rate_limit.limiter.enabled = True
    yield
    rate_limit.limiter.enabled = False


@pytest.mark.anyio
async def test_admin_login_rate_limited_after_repeated_attempts(
    client, _rate_limiting_enabled, tmp_path, monkeypatch
):
    """admin/login is limited to 10/minute — hammer it well past that with
    bad credentials and confirm slowapi actually returns 429, not just 401s
    forever."""
    import admin_store

    monkeypatch.setattr(admin_store, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(admin_store, "_DB_PATH", tmp_path / "admin.db")
    admin_store.init_db()

    statuses = []
    for _ in range(15):
        resp = await client.post(
            "/api/admin/login", json={"username": "nobody", "password": "wrong"}
        )
        statuses.append(resp.status_code)

    assert 429 in statuses, f"Expected a 429 among {statuses} — rate limit did not trigger"


@pytest.fixture
def _ip_rate_limiting_enabled():
    import rate_limit

    rate_limit.ip_limiter.enabled = True
    yield
    rate_limit.ip_limiter.enabled = False


@pytest.mark.anyio
async def test_admin_login_ip_ceiling_survives_contributor_id_rotation(
    client, _ip_rate_limiting_enabled, tmp_path, monkeypatch
):
    """Regression test for the real bypass found in a 2026-08-23 security
    review: the primary limiter above keys on a self-asserted, freely-
    rotatable X-Contributor-Id header, so a scripted attacker sending a
    fresh random device id on every request never reuses a bucket and the
    10/minute cap never engages. Simulates exactly that attack -- a brand
    new UUID-shaped id per request -- and confirms the SEPARATE per-IP
    ceiling (rate_limit.ip_limiter) still trips a 429, since every request
    in this test genuinely comes from the same client IP regardless of
    which device id it claims."""
    import uuid

    import admin_store

    monkeypatch.setattr(admin_store, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(admin_store, "_DB_PATH", tmp_path / "admin.db")
    admin_store.init_db()

    statuses = []
    for _ in range(15):
        resp = await client.post(
            "/api/admin/login",
            json={"username": "nobody", "password": "wrong"},
            headers={"X-Contributor-Id": str(uuid.uuid4())},
        )
        statuses.append(resp.status_code)

    assert 429 in statuses, (
        f"Expected a 429 among {statuses} — rotating X-Contributor-Id must not "
        "bypass the per-IP ceiling"
    )
