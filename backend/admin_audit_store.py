"""
Unified admin audit log — who did what, when, to which item, across every
review surface (text corrections, pronunciation corrections, community Q&A).

Before this module, each review surface tracked its own reviewer identity
inconsistently: corrections_store.py stores reviewedBy/reviewedAt per entry,
but pronunciation_store.py and qa_store.py's set_status()/delete() record
only a timestamp, with no admin identity at all. That's fine for "what is
the current state of this one item" but useless for "what has the admin
account actually done recently" — the question this module answers. This is
a single-admin app (see admin_store.py), so this isn't about attributing
blame between reviewers; it's a safety net: if something unexpected shows up
in the training data, the owner can look at the log and see exactly which
action put it there and when, instead of guessing.

Storage: SQLite on the same persistent volume as the other stores
(FEEDBACK_DATA_DIR), one fresh connection per call via _get_conn — same
lifecycle rationale as pronunciation_store.py / admin_store.py. Correct for
the single-Fly-machine deployment; revisit before scaling out.

log() never raises into the caller: an audit-log write failing (e.g. a full
disk) must not block the actual approve/reject/delete action it's recording,
so failures are logged and swallowed rather than propagated.
"""

import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("murya.admin_audit")

_DATA_DIR = Path(os.getenv("FEEDBACK_DATA_DIR", Path(__file__).resolve().parent / "data"))
_DB_PATH = _DATA_DIR / "admin_audit.db"

_MAX_DETAIL = 300


@contextmanager
def _get_conn():
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the audit_log table + a lookup index if missing."""
    with _get_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin TEXT NOT NULL,
                action TEXT NOT NULL,
                surface TEXT NOT NULL,
                target_id TEXT,
                detail TEXT,
                created_at REAL NOT NULL
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC)"
        )


def log(admin: str, action: str, surface: str, target_id=None, detail: str | None = None) -> None:
    """Record one admin action. Never raises -- see module docstring."""
    try:
        clipped_detail = None
        if detail:
            detail = str(detail).strip()
            clipped_detail = detail[:_MAX_DETAIL] if detail else None
        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO audit_log (admin, action, surface, target_id, detail, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (admin, action, surface, str(target_id) if target_id is not None else None,
                 clipped_detail, time.time()),
            )
    except Exception as exc:
        logger.error("Failed to record audit log entry (admin=%r action=%r surface=%r): %s",
                     admin, action, surface, exc)


def _row(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "admin": r["admin"],
        "action": r["action"],
        "surface": r["surface"],
        "target_id": r["target_id"],
        "detail": r["detail"],
        "created_at": r["created_at"],
    }


def list_recent(limit: int = 200, surface: str | None = None) -> list[dict]:
    """Most recent actions first. Optional surface filter
    ('correction'|'pronunciation'|'qa')."""
    q = "SELECT * FROM audit_log"
    params: tuple = ()
    if surface:
        q += " WHERE surface = ?"
        params = (surface,)
    q += " ORDER BY created_at DESC LIMIT ?"
    params = params + (int(limit),)
    with _get_conn() as conn:
        return [_row(r) for r in conn.execute(q, params).fetchall()]


def _reset_for_tests() -> None:
    with _get_conn() as conn:
        conn.execute("DROP TABLE IF EXISTS audit_log")
    init_db()
