"""
Community Hausa Q&A contributions — native-written instruction data for the
Milestone-#1 LLM training mix (see docs/murya_roadmap.md).

Native speakers submit a Hausa question + its Hausa answer; the owner approves;
approved pairs export as instruction/response rows to fold into the fine-tune.
This is the highest-value data source (real conversational Hausa, not dictionary
pairs), gathered through the same human-in-the-loop gate as pronunciation
corrections — nothing enters the training mix without approval.

SQLite on the persistent volume (FEEDBACK_DATA_DIR), same lifecycle as the other
stores. Text-only (no audio), so it is lighter than pronunciation_store.
"""

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

_DATA_DIR = Path(os.getenv("FEEDBACK_DATA_DIR", Path(__file__).resolve().parent / "data"))
_DB_PATH = _DATA_DIR / "qa.db"

_MAX_Q = 1000
_MAX_A = 4000
_MAX_TOPIC = 80
_MAX_CID = 64


def _cap(v, n):
    if v is None:
        return None
    v = str(v).strip()
    return v[:n] if v else None


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
    with _get_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS qa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                topic TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                submitted_by TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qa_status ON qa(status)")


def submit(question: str, answer: str, topic: str | None,
           submitted_by: str | None) -> int | None:
    """Record a community Q&A pair as PENDING (owner approves before it's used).
    Returns row id, or None if question/answer is empty."""
    q, a = _cap(question, _MAX_Q), _cap(answer, _MAX_A)
    if not q or not a:
        return None
    now = time.time()
    with _get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO qa (question, answer, topic, status, submitted_by, created_at, updated_at)
               VALUES (?, ?, ?, 'pending', ?, ?, ?)""",
            (q, a, _cap(topic, _MAX_TOPIC), _cap(submitted_by, _MAX_CID), now, now),
        )
        return cur.lastrowid


def set_status(row_id: int, status: str) -> bool:
    if status not in ("pending", "approved", "rejected"):
        raise ValueError("invalid status")
    with _get_conn() as conn:
        cur = conn.execute(
            "UPDATE qa SET status = ?, updated_at = ? WHERE id = ?",
            (status, time.time(), row_id),
        )
        return cur.rowcount > 0


def delete(row_id: int) -> bool:
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM qa WHERE id = ?", (row_id,))
        return cur.rowcount > 0


def _row(r: sqlite3.Row) -> dict:
    return {"id": r["id"], "question": r["question"], "answer": r["answer"],
            "topic": r["topic"], "status": r["status"], "submitted_by": r["submitted_by"],
            "created_at": r["created_at"], "updated_at": r["updated_at"]}


def list_items(status: str | None = None, limit: int = 300) -> list[dict]:
    q = "SELECT * FROM qa"
    params: tuple = ()
    if status in ("pending", "approved", "rejected"):
        q += " WHERE status = ?"
        params = (status,)
    q += " ORDER BY updated_at DESC LIMIT ?"
    with _get_conn() as conn:
        return [_row(r) for r in conn.execute(q, params + (int(limit),)).fetchall()]


def counts() -> dict:
    with _get_conn() as conn:
        rows = conn.execute("SELECT status, COUNT(*) AS c FROM qa GROUP BY status").fetchall()
    by = {r["status"]: r["c"] for r in rows}
    return {"pending": by.get("pending", 0), "approved": by.get("approved", 0),
            "rejected": by.get("rejected", 0)}


def export_approved() -> list[dict]:
    """Approved pairs as instruction rows for the training mix."""
    out = []
    with _get_conn() as conn:
        for r in conn.execute(
            "SELECT * FROM qa WHERE status = 'approved' ORDER BY id"
        ).fetchall():
            out.append({
                "instruction": r["question"], "input": "", "output": r["answer"],
                "source": "community_qa", "license": "owner-approved-contribution",
                "topic": r["topic"],
            })
    return out


def _reset_for_tests() -> None:
    with _get_conn() as conn:
        conn.execute("DROP TABLE IF EXISTS qa")
    init_db()
