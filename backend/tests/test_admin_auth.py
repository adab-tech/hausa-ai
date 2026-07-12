"""Tests for /api/admin/login, /api/admin/logout, /api/admin/me."""

import pytest


@pytest.fixture
def isolated_admin_store(tmp_path, monkeypatch):
    """Fresh admin_store DB per test, no seeded admin (REVIEWER_API_KEY
    cleared so init_db doesn't auto-sync an 'adamu' account that would
    collide with tests creating their own)."""
    import admin_store

    monkeypatch.delenv("REVIEWER_API_KEY", raising=False)
    monkeypatch.setattr(admin_store, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(admin_store, "_DB_PATH", tmp_path / "admin.db")
    admin_store.init_db()
    return admin_store


def test_password_syncs_from_secret_on_init(tmp_path, monkeypatch):
    """The REVIEWER_API_KEY secret IS the admin password: init_db seeds it,
    and a changed secret updates the stored hash on the next init (so the
    owner changes their password by changing the secret + restarting)."""
    import admin_store

    monkeypatch.setattr(admin_store, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(admin_store, "_DB_PATH", tmp_path / "admin.db")
    monkeypatch.setattr(admin_store, "ADMIN_USERNAME", "adamu")

    # First boot with an initial secret seeds the account.
    monkeypatch.setenv("REVIEWER_API_KEY", "first-password")
    admin_store.init_db()
    assert admin_store.verify_login("adamu", "first-password") is not None

    # Owner changes the secret; next boot re-syncs the password.
    monkeypatch.setenv("REVIEWER_API_KEY", "second-password")
    admin_store.init_db()
    assert admin_store.verify_login("adamu", "second-password") is not None
    assert admin_store.verify_login("adamu", "first-password") is None


@pytest.mark.anyio
async def test_me_without_session_401s(client, isolated_admin_store):
    resp = await client.get("/api/admin/me")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_login_wrong_password_401s(client, isolated_admin_store):
    isolated_admin_store.create_admin("adamu", "correct-horse")
    resp = await client.post(
        "/api/admin/login", json={"username": "adamu", "password": "wrong"}
    )
    assert resp.status_code == 401
    # No session cookie should be set on a failed login.
    assert "murya_admin_session" not in resp.cookies


@pytest.mark.anyio
async def test_login_unknown_username_401s(client, isolated_admin_store):
    resp = await client.post(
        "/api/admin/login", json={"username": "nobody", "password": "whatever"}
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_login_success_then_me_then_logout(client, isolated_admin_store):
    isolated_admin_store.create_admin("adamu", "correct-horse")

    login_resp = await client.post(
        "/api/admin/login", json={"username": "adamu", "password": "correct-horse"}
    )
    assert login_resp.status_code == 200
    assert login_resp.json() == {"username": "adamu"}
    assert "murya_admin_session" in login_resp.cookies

    me_resp = await client.get("/api/admin/me")
    assert me_resp.status_code == 200
    assert me_resp.json() == {"username": "adamu"}

    logout_resp = await client.post("/api/admin/logout")
    assert logout_resp.status_code == 200

    me_after_logout = await client.get("/api/admin/me")
    assert me_after_logout.status_code == 401
