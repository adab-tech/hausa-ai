"""
Human-in-the-loop pronunciation corrections for TTS.

The trained voice speaks naturally; when it mis-articulates a word or phrase, a
native-speaker reviewer records the CORRECT pronunciation. Once approved, that
recording is used at synthesis time (highest priority, above the WAXAL sample
bank and the VITS model) AND accumulates as (text, audio) training data for the
next voice retrain — closing the loop toward a better base model.

This is the audio counterpart of the existing TEXT correction/feedback loop
(corrections_store.py) and mirrors its reviewer-approval model.

Storage: SQLite on the same persistent volume as the other stores
(FEEDBACK_DATA_DIR), one fresh connection per call via _get_conn (same
lifecycle rationale as analytics_store.py / admin_store.py). Correct for the
single-Fly-machine deployment; revisit before scaling out.

Audio is stored as raw PCM-16 LE mono at 24 kHz (the TTS pipeline's native
format) so a correction can be returned straight into the synthesis path with
no re-decode. Uploaded recordings (webm/ogg/wav/mp3…) are converted on ingest.

Row lifecycle:
  flag()            -> status 'pending', audio NULL   (a user says "this is wrong")
  add_correction()  -> status 'approved', audio set   (a reviewer records the fix)
  attach_audio()    -> record against an existing flag, -> 'approved'
  set_status()      -> approve / reject
"""

import io
import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("murya.pronunciation")

_DATA_DIR = Path(os.getenv("FEEDBACK_DATA_DIR", Path(__file__).resolve().parent / "data"))
_DB_PATH = _DATA_DIR / "pronunciation.db"

_TTS_SAMPLE_RATE = 24000
_MAX_TEXT = 400          # a correction targets a word or short phrase, not an essay
_MAX_NOTE = 500
_MAX_CID = 64
_MAX_AUDIO_BYTES = 4 * 1024 * 1024  # 4 MB of 24 kHz PCM ~= 87 s; plenty for a phrase

# Hooked Hausa letters -> plain ASCII for a case/diacritic-insensitive lookup
# key (same idea as dictionary_service._fold). The ORIGINAL text is preserved in
# display_text; only the match key is folded.
_FOLD = {"ɓ": "b", "ɗ": "d", "ƙ": "k", "ƴ": "y",
         "Ɓ": "b", "Ɗ": "d", "Ƙ": "k", "Ƴ": "y"}


def fold_key(text: str) -> str:
    """Normalize text to a lookup key: fold hooked letters, lowercase, collapse
    whitespace, strip surrounding punctuation/space. Empty string if nothing
    usable remains."""
    if not text:
        return ""
    folded = "".join(_FOLD.get(ch, ch) for ch in text)
    folded = folded.lower().strip()
    folded = " ".join(folded.split())
    return folded.strip(".,!?;:\"'()[]{} ")


# ---------------------------------------------------------------------------
# Audio ingest
# ---------------------------------------------------------------------------
def convert_upload_to_pcm24k(raw: bytes) -> bytes | None:
    """Decode an uploaded recording (any common format) to raw PCM-16 LE mono at
    24 kHz — the TTS pipeline's native format. Returns None on failure (never
    raises into the request path)."""
    if not raw:
        return None
    try:
        from pydub import AudioSegment
        try:  # match _load_mp3_as_pcm24k: point pydub at the bundled ffmpeg
            import imageio_ffmpeg
            AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
        seg = AudioSegment.from_file(io.BytesIO(raw))
        seg = seg.set_frame_rate(_TTS_SAMPLE_RATE).set_channels(1).set_sample_width(2)
        return seg.raw_data
    except Exception as exc:
        logger.error("Failed to decode uploaded correction audio: %s", exc)
        return None


# ---------------------------------------------------------------------------
# DB lifecycle
# ---------------------------------------------------------------------------
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
    """Create the corrections table + lookup index if missing."""
    with _get_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS pronunciations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text_key TEXT NOT NULL,
                display_text TEXT NOT NULL,
                speaker_id INTEGER,
                audio BLOB,
                status TEXT NOT NULL DEFAULT 'pending',
                submitted_by TEXT,
                note TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pron_lookup ON pronunciations(text_key, status)"
        )


def _cap(value, limit):
    if value is None:
        return None
    value = str(value).strip()
    return value[:limit] if value else None


# ---------------------------------------------------------------------------
# Synthesis-time lookup (the hot path)
# ---------------------------------------------------------------------------
def lookup(text: str, speaker_id: int | None = None) -> bytes | None:
    """Return approved correction PCM (24 kHz mono PCM-16) for an EXACT folded
    match of `text`, or None. A voice-specific correction (matching speaker_id)
    wins over a voice-agnostic one; ties break to the most recently updated.
    Never raises — a correction lookup must never break synthesis."""
    key = fold_key(text)
    if not key:
        return None
    try:
        with _get_conn() as conn:
            row = conn.execute(
                """SELECT audio FROM pronunciations
                   WHERE text_key = ? AND status = 'approved' AND audio IS NOT NULL
                     AND (speaker_id IS ? OR speaker_id IS NULL)
                   ORDER BY (speaker_id IS ?) DESC, updated_at DESC
                   LIMIT 1""",
                (key, speaker_id, speaker_id),
            ).fetchone()
        if row and row["audio"]:
            return bytes(row["audio"])
    except Exception as exc:
        logger.error("pronunciation lookup failed for %r: %s", text, exc)
    return None


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------
def flag(text: str, speaker_id: int | None, submitted_by: str | None,
         note: str | None = None) -> int | None:
    """Record a user-reported mispronunciation (no audio yet) as a pending item
    for a reviewer to record against. Returns the new row id, or None if the
    text is empty."""
    key = fold_key(text)
    display = _cap(text, _MAX_TEXT)
    if not key or not display:
        return None
    now = time.time()
    with _get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO pronunciations
               (text_key, display_text, speaker_id, audio, status, submitted_by, note, created_at, updated_at)
               VALUES (?, ?, ?, NULL, 'pending', ?, ?, ?, ?)""",
            (key, display, speaker_id, _cap(submitted_by, _MAX_CID), _cap(note, _MAX_NOTE), now, now),
        )
        return cur.lastrowid


def add_correction(text: str, speaker_id: int | None, audio_pcm: bytes,
                   submitted_by: str | None = None, note: str | None = None,
                   status: str = "approved") -> int | None:
    """Store a reviewer's correction recording (already 24 kHz PCM) for `text`.
    Defaults to 'approved' — the reviewer is the authority. Returns row id."""
    key = fold_key(text)
    display = _cap(text, _MAX_TEXT)
    if not key or not display or not audio_pcm:
        return None
    if len(audio_pcm) > _MAX_AUDIO_BYTES:
        raise ValueError("correction audio too large")
    now = time.time()
    with _get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO pronunciations
               (text_key, display_text, speaker_id, audio, status, submitted_by, note, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (key, display, speaker_id, sqlite3.Binary(audio_pcm), status,
             _cap(submitted_by, _MAX_CID), _cap(note, _MAX_NOTE), now, now),
        )
        return cur.lastrowid


def attach_audio(row_id: int, audio_pcm: bytes) -> bool:
    """Attach a recording to an existing (usually flagged) row and approve it.
    Returns True if a row was updated."""
    if not audio_pcm:
        return False
    if len(audio_pcm) > _MAX_AUDIO_BYTES:
        raise ValueError("correction audio too large")
    with _get_conn() as conn:
        cur = conn.execute(
            "UPDATE pronunciations SET audio = ?, status = 'approved', updated_at = ? WHERE id = ?",
            (sqlite3.Binary(audio_pcm), time.time(), row_id),
        )
        return cur.rowcount > 0


def set_status(row_id: int, status: str) -> bool:
    if status not in ("pending", "approved", "rejected"):
        raise ValueError("invalid status")
    with _get_conn() as conn:
        cur = conn.execute(
            "UPDATE pronunciations SET status = ?, updated_at = ? WHERE id = ?",
            (status, time.time(), row_id),
        )
        return cur.rowcount > 0


def delete(row_id: int) -> bool:
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM pronunciations WHERE id = ?", (row_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Reads for the review dashboard
# ---------------------------------------------------------------------------
def _row_meta(row: sqlite3.Row) -> dict:
    """Row -> JSON-safe dict WITHOUT the audio blob (has_audio flag instead)."""
    return {
        "id": row["id"],
        "text": row["display_text"],
        "speaker_id": row["speaker_id"],
        "status": row["status"],
        "has_audio": row["audio"] is not None,
        "submitted_by": row["submitted_by"],
        "note": row["note"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_items(status: str | None = None, limit: int = 200) -> list[dict]:
    """List corrections (newest first) for the dashboard, without audio blobs.
    Optional status filter ('pending'|'approved'|'rejected')."""
    q = "SELECT * FROM pronunciations"
    params: tuple = ()
    if status in ("pending", "approved", "rejected"):
        q += " WHERE status = ?"
        params = (status,)
    q += " ORDER BY updated_at DESC LIMIT ?"
    params = params + (int(limit),)
    with _get_conn() as conn:
        return [_row_meta(r) for r in conn.execute(q, params).fetchall()]


def get_audio(row_id: int) -> bytes | None:
    """Raw 24 kHz PCM for a row (for playback in the review UI), or None."""
    with _get_conn() as conn:
        row = conn.execute("SELECT audio FROM pronunciations WHERE id = ?", (row_id,)).fetchone()
    return bytes(row["audio"]) if row and row["audio"] else None


def export_approved() -> list[dict]:
    """All approved corrections WITH audio, for building the retrain corpus.
    Each: {id, text, text_key, speaker_id, audio(pcm bytes)}."""
    out = []
    with _get_conn() as conn:
        for r in conn.execute(
            "SELECT * FROM pronunciations WHERE status = 'approved' AND audio IS NOT NULL"
        ).fetchall():
            out.append({
                "id": r["id"], "text": r["display_text"], "text_key": r["text_key"],
                "speaker_id": r["speaker_id"], "audio": bytes(r["audio"]),
            })
    return out


def counts() -> dict:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS c FROM pronunciations GROUP BY status"
        ).fetchall()
    by = {r["status"]: r["c"] for r in rows}
    return {"pending": by.get("pending", 0), "approved": by.get("approved", 0),
            "rejected": by.get("rejected", 0)}


def _reset_for_tests() -> None:
    with _get_conn() as conn:
        conn.execute("DROP TABLE IF EXISTS pronunciations")
    init_db()
