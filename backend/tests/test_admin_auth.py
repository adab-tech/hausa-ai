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


def test_session_token_stored_hashed_not_plaintext(isolated_admin_store):
    """Regression test for a gap the 2026-08-23 follow-up security-
    architecture review found: sessions.token stored the raw
    secrets.token_urlsafe(32) value directly, matched by equality on lookup.
    Not exploitable through the app's own request surface (good entropy,
    HttpOnly cookie) but if admin.db is ever read through some OTHER channel
    (a misconfigured backup, a future path-traversal bug, an operator
    debugging via `sqlite3 admin.db`), a plaintext token there hijacks every
    currently-valid session with no further work. Hashing removes that."""
    import sqlite3

    isolated_admin_store.create_admin("adamu", "correct-horse")
    admin_id = isolated_admin_store.verify_login("adamu", "correct-horse")
    token = isolated_admin_store.create_session(admin_id)

    with sqlite3.connect(isolated_admin_store._DB_PATH) as conn:
        row = conn.execute("SELECT token FROM sessions").fetchone()

    assert row[0] != token, "raw session token must not be stored at rest"
    assert isolated_admin_store.get_session_username(token) == "adamu"
    assert isolated_admin_store.get_session_username(row[0]) is None, (
        "the stored (hashed) value itself must not work as a session token"
    )


def test_delete_session_removes_hashed_row(isolated_admin_store):
    isolated_admin_store.create_admin("adamu", "correct-horse")
    admin_id = isolated_admin_store.verify_login("adamu", "correct-horse")
    token = isolated_admin_store.create_session(admin_id)
    assert isolated_admin_store.get_session_username(token) == "adamu"
    isolated_admin_store.delete_session(token)
    assert isolated_admin_store.get_session_username(token) is None


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
