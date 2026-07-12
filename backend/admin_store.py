"""
Real admin authentication: accounts + server-side sessions, backed by SQLite
on the same persistent volume as corrections/feedback data. Replaces the
old REVIEWER_API_KEY-typed-into-sessionStorage pattern with a proper login:
bcrypt password hashes, HttpOnly session cookies, and a per-admin identity
so corrections finally carry a real "reviewed by" audit trail.

The REVIEWER_API_KEY secret IS the admin password (single-admin app). It is
synced to the ADMIN_USERNAME account (default "adamu") on EVERY boot — the
account is created if absent, or its stored hash is updated if the secret
changed. So the owner sets/changes their own password by changing the Fly
secret and restarting, with no DB surgery:
    flyctl secrets set REVIEWER_API_KEY="<new password>" -a hausa-ai-backend
Then log in at app.murya.ng/admin/login as ADMIN_USERNAME with that password.

A single Fly.io machine with a mounted persistent volume is the deployment
target today (see docs/deployment.md) — SQLite with a fresh connection per
call is safe under that model. This does not coordinate across multiple
machines/workers; don't scale out without revisiting this.
"""

import logging
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

import bcrypt

logger = logging.getLogger("murya.admin")

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


def init_db() -> None:
    """Create tables if missing, and keep the admin password in sync with the
    REVIEWER_API_KEY secret.

    Model: the Fly secret REVIEWER_API_KEY IS the admin password. On every
    boot, the ADMIN_USERNAME account is created (if absent) or its password is
    updated (if the secret changed). So the owner changes their password by
    changing the secret and restarting — no DB surgery needed:

        flyctl secrets set REVIEWER_API_KEY="<new password>" -a hausa-ai-backend

    If REVIEWER_API_KEY is unset, nothing is seeded (auth simply can't be used
    until it is)."""
    with _get_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at REAL NOT NULL
            )"""
        )
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

        existing = conn.execute(
            "SELECT id, password_hash FROM admins WHERE username = ? COLLATE NOCASE",
            (ADMIN_USERNAME,),
        ).fetchone()
        if existing is None:
            _create_admin_locked(conn, ADMIN_USERNAME, secret)
            action = "created"
        elif not bcrypt.checkpw(secret.encode("utf-8"), existing["password_hash"].encode("utf-8")):
            # Secret changed since last boot -> update the stored hash.
            new_hash = bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            conn.execute(
                "UPDATE admins SET password_hash = ? WHERE id = ?",
                (new_hash, existing["id"]),
            )
            action = "password-updated"
        else:
            action = "unchanged"
        # Diagnostic only — NEVER logs the password itself.
        all_usernames = [r["username"] for r in conn.execute("SELECT username FROM admins")]
        logger.info(
            "[admin] sync: username=%r action=%s reviewer_key_len=%d all_admins=%r",
            ADMIN_USERNAME, action, len(secret), all_usernames,
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


def create_session(admin_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = time.time()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (token, admin_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, admin_id, now, now + _SESSION_TTL_SECONDS),
        )
    return token


def get_session_username(token: str) -> str | None:
    """Return the admin's username if the session token is valid and not
    expired, else None. Expired sessions are lazily deleted on lookup."""
    now = time.time()
    with _get_conn() as conn:
        row = conn.execute(
            """SELECT admins.username AS username, sessions.expires_at AS expires_at
               FROM sessions JOIN admins ON sessions.admin_id = admins.id
               WHERE sessions.token = ?""",
            (token,),
        ).fetchone()
        if row is None:
            return None
        if row["expires_at"] < now:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None
    return row["username"]


def delete_session(token: str) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
