"""
Real admin authentication: accounts + server-side sessions, backed by SQLite
on the same persistent volume as corrections/feedback data. Replaces the
old REVIEWER_API_KEY-typed-into-sessionStorage pattern with a proper login:
bcrypt password hashes, HttpOnly session cookies, and a per-admin identity
so corrections finally carry a real "reviewed by" audit trail.

Two ways to set the admin password, both supported at once:

1. REVIEWER_API_KEY (bootstrap / forced reset). Set the env var and
   restart -- init_db() syncs it to the ADMIN_USERNAME account (default
   "adamu"). No DB surgery, useful when locked out and server access is
   the only channel available:
       sudo sed -i 's/^REVIEWER_API_KEY=.*/REVIEWER_API_KEY=<new>/' murya.env
       sudo systemctl restart murya.service

2. Self-service (change_password(), see routers/admin_auth.py's
   POST /api/admin/change-password). Requires knowing the CURRENT
   password. This is the one real admins should use day to day.

These two must not fight each other: a self-service change must SURVIVE
the next redeploy even though REVIEWER_API_KEY didn't change (deploys are
frequent in this project). init_db() tracks a hash of the REVIEWER_API_KEY
value it last synced FROM (admins.synced_secret_hash) -- separate from
whether it still matches the CURRENT password_hash -- so it only re-syncs
when the secret itself actually changes, never just because a self-service
change made the two diverge.

A single machine with a mounted persistent volume is the deployment target
today (see docs/deployment.md) — SQLite with a fresh connection per call is
safe under that model. This does not coordinate across multiple
machines/workers; don't scale out without revisiting this.
"""

import hashlib
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

import bcrypt

_DATA_DIR = Path(os.getenv("FEEDBACK_DATA_DIR", Path(__file__).resolve().parent / "data"))
_DB_PATH = _DATA_DIR / "admin.db"

SESSION_COOKIE_NAME = "murya_admin_session"
_SESSION_TTL_SECONDS = 12 * 3600  # 12h absolute expiry


@contextmanager
def _get_conn():
    """sqlite3.Connection's own context manager only commits/rolls back on
    exit — it does NOT close the connection, which leaks a file handle per
    call. Wrap it so every caller gets both commit-on-success and a
    guaranteed close."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# The admin username (single-admin app). Override with ADMIN_USERNAME.
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "adamu").strip() or "adamu"


def _hash_secret(secret: str) -> str:
    """Change-detection only (not a password hash) -- used to tell whether
    REVIEWER_API_KEY itself has changed since the last sync, independent of
    whether it still matches the current (possibly self-service-changed)
    password_hash."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def init_db() -> None:
    """Create tables if missing, and keep the admin password in sync with the
    REVIEWER_API_KEY secret -- but ONLY when that secret has actually
    changed since the last time this ran, so a self-service password
    change (change_password(), below) isn't silently reverted on the next
    ordinary redeploy just because REVIEWER_API_KEY didn't move. See the
    module docstring for the full model.

    If REVIEWER_API_KEY is unset, nothing is seeded (auth simply can't be
    used until it is)."""
    with _get_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at REAL NOT NULL,
                synced_secret_hash TEXT
            )"""
        )
        # Migration for a database created before synced_secret_hash existed
        # (CREATE TABLE IF NOT EXISTS is a no-op on an already-existing
        # table, so the column above never gets added to it on its own).
        existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(admins)")}
        if "synced_secret_hash" not in existing_columns:
            conn.execute("ALTER TABLE admins ADD COLUMN synced_secret_hash TEXT")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                admin_id INTEGER NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                FOREIGN KEY (admin_id) REFERENCES admins(id)
            )"""
        )

        secret = os.getenv("REVIEWER_API_KEY", "").strip()
        if not secret:
            return
        secret_hash = _hash_secret(secret)

        existing = conn.execute(
            "SELECT id, password_hash, synced_secret_hash FROM admins WHERE username = ? COLLATE NOCASE",
            (ADMIN_USERNAME,),
        ).fetchone()
        if existing is None:
            _create_admin_locked(conn, ADMIN_USERNAME, secret)
            conn.execute(
                "UPDATE admins SET synced_secret_hash = ? WHERE username = ? COLLATE NOCASE",
                (secret_hash, ADMIN_USERNAME),
            )
            action = "created"
        elif existing["synced_secret_hash"] != secret_hash:
            # REVIEWER_API_KEY itself changed since the last sync (not just
            # "doesn't match the current password_hash" -- that would also
            # be true after a self-service change with no secret rotation
            # at all, which must NOT trigger this branch).
            new_hash = bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            conn.execute(
                "UPDATE admins SET password_hash = ?, synced_secret_hash = ? WHERE id = ?",
                (new_hash, secret_hash, existing["id"]),
            )
            action = "password-updated (REVIEWER_API_KEY changed)"
        else:
            action = "unchanged (self-service password changes, if any, are preserved)"
        # Diagnostic only — NEVER logs the password itself, only its LENGTH.
        # print() (not logger) so it reaches stdout: uvicorn doesn't wire up
        # arbitrary loggers, so a logger.info here was silently dropped.
        all_usernames = [r["username"] for r in conn.execute("SELECT username FROM admins")]
        print(
            f"[admin] sync: username={ADMIN_USERNAME!r} action={action} "
            f"reviewer_key_len={len(secret)} all_admins={all_usernames!r}",
            flush=True,
        )


def _create_admin_locked(conn: sqlite3.Connection, username: str, password: str) -> None:
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn.execute(
        "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
        (username, password_hash, time.time()),
    )


def create_admin(username: str, password: str) -> None:
    """Exposed for tests and future admin-management tooling."""
    with _get_conn() as conn:
        _create_admin_locked(conn, username, password)


def verify_login(username: str, password: str) -> int | None:
    """Return the admin id if username/password match, else None."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM admins WHERE username = ? COLLATE NOCASE",
            (username,),
        ).fetchone()
    if row is None:
        # Still run a hash comparison against a dummy value so a valid vs.
        # invalid username can't be distinguished by response timing.
        bcrypt.checkpw(b"", bcrypt.gensalt())
        return None
    if bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
        return row["id"]
    return None


def change_password(username: str, old_password: str, new_password: str) -> int | None:
    """Self-service password change (routers/admin_auth.py's
    POST /api/admin/change-password). Requires the CURRENT password even
    though the caller already has a valid session -- defense in depth: a
    hijacked session cookie alone (stolen from a shared machine, an XSS
    that never should happen but might, etc.) can't permanently take over
    the account without also knowing the current password. Returns None
    (not an exception) on a wrong old_password -- same "don't distinguish
    valid from invalid by raising" posture as verify_login. On success,
    returns the admin id so the caller can invalidate existing sessions
    (see delete_all_sessions_for_admin).

    Does NOT touch synced_secret_hash -- this deliberately decouples the
    stored password from REVIEWER_API_KEY going forward, so it survives
    the next ordinary redeploy. See init_db()'s docstring."""
    admin_id = verify_login(username, old_password)
    if admin_id is None:
        return None
    new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    with _get_conn() as conn:
        conn.execute("UPDATE admins SET password_hash = ? WHERE id = ?", (new_hash, admin_id))
    return admin_id


def delete_all_sessions_for_admin(admin_id: int) -> None:
    """Called after a successful password change -- standard practice is
    that changing your password logs you out everywhere, including the
    session that just made the change (the frontend re-prompts for a fresh
    login with the new password)."""
    with _get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE admin_id = ?", (admin_id,))


def _hash_token(token: str) -> str:
    """Sessions store this hash, never the raw token -- see create_session's
    docstring for why."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(admin_id: int) -> str:
    """Returns the raw session token (goes into the HttpOnly cookie). Only
    sha256(token) is persisted to sessions.token, not the raw value.

    The token already has good entropy (256 bits, secrets.token_urlsafe) and
    the cookie carrying it is HttpOnly, so this isn't exploitable through
    the app's own request surface -- the gap it closes is narrower: if
    admin.db is ever read through some OTHER channel (a misconfigured
    backup, a future path-traversal bug, an operator debugging via `sqlite3
    admin.db` and pasting output somewhere), a plaintext token there would
    make every currently-valid session immediately hijackable with no
    further work, for up to the full session TTL. Hashing means a DB read
    alone isn't enough. Found in the 2026-08-23 follow-up security-
    architecture review."""
    token = secrets.token_urlsafe(32)
    now = time.time()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (token, admin_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (_hash_token(token), admin_id, now, now + _SESSION_TTL_SECONDS),
        )
    return token


def get_session_username(token: str) -> str | None:
    """Return the admin's username if the session token is valid and not
    expired, else None. Expired sessions are lazily deleted on lookup."""
    token_hash = _hash_token(token)
    now = time.time()
    with _get_conn() as conn:
        row = conn.execute(
            """SELECT admins.username AS username, sessions.expires_at AS expires_at
               FROM sessions JOIN admins ON sessions.admin_id = admins.id
               WHERE sessions.token = ?""",
            (token_hash,),
        ).fetchone()
        if row is None:
            return None
        if row["expires_at"] < now:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token_hash,))
            return None
    return row["username"]


def delete_session(token: str) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (_hash_token(token),))
