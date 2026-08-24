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


def test_self_service_password_change_survives_reinit_without_secret_change(tmp_path, monkeypatch):
    """The bug this whole mechanism exists to prevent: a real user reported
    being locked out after a self-service-style password change, because
    the OLD sync logic compared REVIEWER_API_KEY against the CURRENT
    password_hash on every boot -- once those two diverged (exactly what a
    self-service change does, on purpose), the very next ordinary redeploy
    silently reverted the password back to REVIEWER_API_KEY. This project
    redeploys the backend many times a day, so that window was tiny.
    synced_secret_hash decouples "did REVIEWER_API_KEY itself change" from
    "does it currently match the stored hash" -- a self-service change must
    survive any number of re-inits as long as the secret itself doesn't
    move."""
    import admin_store

    monkeypatch.setattr(admin_store, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(admin_store, "_DB_PATH", tmp_path / "admin.db")
    monkeypatch.setattr(admin_store, "ADMIN_USERNAME", "adamu")
    monkeypatch.setenv("REVIEWER_API_KEY", "bootstrap-secret")

    admin_store.init_db()
    assert admin_store.verify_login("adamu", "bootstrap-secret") is not None

    admin_id = admin_store.change_password("adamu", "bootstrap-secret", "my-own-chosen-password")
    assert admin_id is not None
    assert admin_store.verify_login("adamu", "my-own-chosen-password") is not None
    assert admin_store.verify_login("adamu", "bootstrap-secret") is None

    # Simulate several ordinary redeploys -- REVIEWER_API_KEY unchanged.
    for _ in range(3):
        admin_store.init_db()
    assert admin_store.verify_login("adamu", "my-own-chosen-password") is not None, (
        "self-service password must survive redeploys when REVIEWER_API_KEY didn't change"
    )

    # The operator can still force-reset via REVIEWER_API_KEY when actually
    # needed (e.g. genuinely locked out) -- changing the secret for real
    # must still take effect.
    monkeypatch.setenv("REVIEWER_API_KEY", "operator-forced-reset")
    admin_store.init_db()
    assert admin_store.verify_login("adamu", "operator-forced-reset") is not None
    assert admin_store.verify_login("adamu", "my-own-chosen-password") is None


def test_change_password_requires_correct_old_password(isolated_admin_store):
    isolated_admin_store.create_admin("adamu", "correct-horse")
    result = isolated_admin_store.change_password("adamu", "wrong-old-password", "new-strong-password")
    assert result is None
    # Password must be unchanged.
    assert isolated_admin_store.verify_login("adamu", "correct-horse") is not None
    assert isolated_admin_store.verify_login("adamu", "new-strong-password") is None


def test_change_password_success_updates_credential(isolated_admin_store):
    isolated_admin_store.create_admin("adamu", "correct-horse")
    admin_id = isolated_admin_store.change_password("adamu", "correct-horse", "new-strong-password")
    assert admin_id is not None
    assert isolated_admin_store.verify_login("adamu", "new-strong-password") is not None
    assert isolated_admin_store.verify_login("adamu", "correct-horse") is None


def test_delete_all_sessions_for_admin_kills_every_session(isolated_admin_store):
    isolated_admin_store.create_admin("adamu", "correct-horse")
    admin_id = isolated_admin_store.verify_login("adamu", "correct-horse")
    token_a = isolated_admin_store.create_session(admin_id)
    token_b = isolated_admin_store.create_session(admin_id)

    isolated_admin_store.delete_all_sessions_for_admin(admin_id)

    assert isolated_admin_store.get_session_username(token_a) is None
    assert isolated_admin_store.get_session_username(token_b) is None


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


@pytest.mark.anyio
async def test_change_password_endpoint_requires_login(client, isolated_admin_store):
    resp = await client.post(
        "/api/admin/change-password",
        json={"old_password": "whatever", "new_password": "a-new-strong-password"},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_change_password_endpoint_rejects_wrong_old_password(client, isolated_admin_store):
    isolated_admin_store.create_admin("adamu", "correct-horse")
    login_resp = await client.post(
        "/api/admin/login", json={"username": "adamu", "password": "correct-horse"}
    )
    assert login_resp.status_code == 200

    resp = await client.post(
        "/api/admin/change-password",
        json={"old_password": "not-the-real-password", "new_password": "a-new-strong-password"},
    )
    assert resp.status_code == 401

    # Session must still be alive -- a failed change shouldn't log anyone out.
    me_resp = await client.get("/api/admin/me")
    assert me_resp.status_code == 200

    await client.post("/api/admin/logout")


@pytest.mark.anyio
async def test_change_password_endpoint_rejects_short_new_password(client, isolated_admin_store):
    isolated_admin_store.create_admin("adamu", "correct-horse")
    login_resp = await client.post(
        "/api/admin/login", json={"username": "adamu", "password": "correct-horse"}
    )
    assert login_resp.status_code == 200

    resp = await client.post(
        "/api/admin/change-password",
        json={"old_password": "correct-horse", "new_password": "short"},
    )
    assert resp.status_code == 422

    await client.post("/api/admin/logout")


@pytest.mark.anyio
async def test_change_password_endpoint_success_logs_out_and_new_password_works(client, isolated_admin_store):
    isolated_admin_store.create_admin("adamu", "correct-horse")
    login_resp = await client.post(
        "/api/admin/login", json={"username": "adamu", "password": "correct-horse"}
    )
    assert login_resp.status_code == 200

    change_resp = await client.post(
        "/api/admin/change-password",
        json={"old_password": "correct-horse", "new_password": "a-new-strong-password"},
    )
    assert change_resp.status_code == 200
    assert change_resp.json() == {"ok": True}

    # The session that made the change is now dead -- standard "change
    # password logs you out everywhere" behavior.
    me_after_change = await client.get("/api/admin/me")
    assert me_after_change.status_code == 401

    # A fresh login with the OLD password must fail, and with the NEW
    # password must succeed.
    old_login = await client.post(
        "/api/admin/login", json={"username": "adamu", "password": "correct-horse"}
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/admin/login", json={"username": "adamu", "password": "a-new-strong-password"}
    )
    assert new_login.status_code == 200

    await client.post("/api/admin/logout")
