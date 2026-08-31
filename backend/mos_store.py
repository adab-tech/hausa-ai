"""
MOS (Mean Opinion Score) listening test — the naturalness-eval counterpart of
the pronunciation-correction loop (pronunciation_store.py). Where that loop
fixes individual mispronounced words, this one answers a broader question
before any new voice checkpoint or correction batch feeds the next retrain:
does this actually sound better to real Hausa speakers?

Two conditions are served: 'murya' (the live production voice, all 8
speakers) and 'ground_truth' (real WAXAL human recordings, a naturalness
ceiling to calibrate against). A low-quality anchor and any competitor
comparison exist only in the standalone research build (see
scripts/seed_mos_stimuli.py's docstring) — not worth the image-size cost of
baking an extra checkpoint into the deployed container just for this.

Storage: SQLite on the same persistent volume as the other stores
(FEEDBACK_DATA_DIR), one fresh connection per call via _get_conn (same
lifecycle rationale as pronunciation_store.py / admin_store.py).

Stimuli are seeded ONCE, on first startup with an empty table (see
seed_if_empty in scripts/seed_mos_stimuli.py, called from main.py) — synthesis
is a few seconds of CPU, not worth repeating on every restart.

Listener sessions are anonymous (contributor id only, see contributor.py) and
never gate on login: this is deliberately zero-friction so real volunteers
actually finish it. Results (list_results/export_ratings) are admin-only.
"""

import logging
import os
import random
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("murya.mos")

_DATA_DIR = Path(os.getenv("FEEDBACK_DATA_DIR", Path(__file__).resolve().parent / "data"))
_DB_PATH = _DATA_DIR / "mos.db"

_SAMPLE_RATE = 24000
_SESSION_SIZE = 20
_GROUND_TRUTH_PER_SESSION = 3
_MAX_REGION = 64
_MAX_CID = 64


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
            """CREATE TABLE IF NOT EXISTS mos_stimuli (
                clip_id TEXT PRIMARY KEY,
                condition TEXT NOT NULL,
                voice TEXT NOT NULL,
                sentence_id TEXT NOT NULL,
                text TEXT NOT NULL,
                audio BLOB NOT NULL,
                source TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS mos_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                clip_id TEXT NOT NULL,
                condition TEXT NOT NULL,
                voice TEXT NOT NULL,
                sentence_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                intelligible TEXT NOT NULL,
                replays INTEGER NOT NULL DEFAULT 0,
                region TEXT,
                native_speaker INTEGER NOT NULL DEFAULT 0,
                submitted_by TEXT,
                created_at REAL NOT NULL
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mos_ratings_cond ON mos_ratings(condition)"
        )
        # A decision is the admin's explicit sign-off on a results snapshot —
        # nothing here EVER auto-approves data for training on its own; this
        # table exists so "the admin looked at this and made a call" is a
        # real, auditable record, not just an implication from a dashboard
        # someone glanced at.
        conn.execute(
            """CREATE TABLE IF NOT EXISTS mos_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                verdict TEXT NOT NULL,
                note TEXT,
                total_ratings_at_time INTEGER NOT NULL,
                murya_mean_at_time REAL,
                ground_truth_mean_at_time REAL,
                admin TEXT NOT NULL,
                created_at REAL NOT NULL
            )"""
        )


def stimuli_count() -> int:
    with _get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM mos_stimuli").fetchone()
    return row["c"] if row else 0


def add_stimulus(clip_id: str, condition: str, voice: str, sentence_id: str,
                 text: str, audio_pcm: bytes, source: str | None = None) -> None:
    with _get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO mos_stimuli
               (clip_id, condition, voice, sentence_id, text, audio, source)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (clip_id, condition, voice, sentence_id, text, sqlite3.Binary(audio_pcm), source),
        )


def get_audio(clip_id: str) -> bytes | None:
    with _get_conn() as conn:
        row = conn.execute("SELECT audio FROM mos_stimuli WHERE clip_id = ?", (clip_id,)).fetchone()
    return bytes(row["audio"]) if row and row["audio"] else None


def build_session() -> list[dict]:
    """A randomized, blind session: a few ground-truth anchors plus a spread
    of Murya voices/sentences, shuffled. Returns clip metadata WITHOUT audio
    (the frontend fetches each clip's audio separately by clip_id)."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT clip_id, condition, voice, sentence_id, text FROM mos_stimuli"
        ).fetchall()
    by_cond: dict[str, list[dict]] = {}
    for r in rows:
        by_cond.setdefault(r["condition"], []).append(dict(r))

    ground_truth = by_cond.get("ground_truth", [])
    murya = by_cond.get("murya", [])

    chosen = random.sample(ground_truth, min(_GROUND_TRUTH_PER_SESSION, len(ground_truth)))
    remaining = max(0, _SESSION_SIZE - len(chosen))
    chosen += random.sample(murya, min(remaining, len(murya)))
    random.shuffle(chosen)
    return chosen


class RatingIn:
    __slots__ = ("clip_id", "condition", "voice", "sentence_id", "score", "intelligible", "replays")

    def __init__(self, clip_id, condition, voice, sentence_id, score, intelligible, replays=0):
        self.clip_id = clip_id
        self.condition = condition
        self.voice = voice
        self.sentence_id = sentence_id
        self.score = score
        self.intelligible = intelligible
        self.replays = replays


def record_session(session_id: str, answers: list[RatingIn], region: str | None,
                   native_speaker: bool, submitted_by: str | None) -> int:
    """Insert one listener's full set of answers. Returns the number of rows
    inserted (0 if `answers` was empty — a no-op, not an error)."""
    if not answers:
        return 0
    now = time.time()
    region = (region or "").strip()[:_MAX_REGION] or None
    submitted_by = (submitted_by or "").strip()[:_MAX_CID] or None
    session_id = (session_id or "").strip()[:_MAX_CID] or None
    with _get_conn() as conn:
        conn.executemany(
            """INSERT INTO mos_ratings
               (session_id, clip_id, condition, voice, sentence_id, score,
                intelligible, replays, region, native_speaker, submitted_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (session_id, a.clip_id, a.condition, a.voice, a.sentence_id, a.score,
                 a.intelligible, a.replays, region, 1 if native_speaker else 0, submitted_by, now)
                for a in answers
            ],
        )
    return len(answers)


def _mean_ci(scores: list[int]) -> dict:
    n = len(scores)
    if n == 0:
        return {"mean": None, "n": 0, "ci95": None}
    mean = sum(scores) / n
    if n < 2:
        return {"mean": round(mean, 3), "n": n, "ci95": None}
    variance = sum((s - mean) ** 2 for s in scores) / (n - 1)
    se = (variance ** 0.5) / (n ** 0.5)
    return {"mean": round(mean, 3), "n": n, "ci95": round(1.96 * se, 3)}


# Below this many ratings for a condition/voice, don't draw a conclusion from
# it — just say so. Standard MOS practice treats <20 as too few to trust.
_MIN_TRUSTWORTHY_N = 20


def _analysis(by_condition: dict, by_voice: dict, intel_counts: dict) -> dict:
    """A synthesized, plain-language read of the numbers below — the thing an
    admin actually wants before deciding what feeds the next retrain, not raw
    means they have to interpret themselves."""
    murya = by_condition.get("murya")
    truth = by_condition.get("ground_truth")

    headline: str
    verdict: str  # 'insufficient_data' | 'close_to_human' | 'meaningful_gap' | 'unknown'
    gap = None

    if not murya or murya["n"] == 0:
        headline = "No Murya ratings yet."
        verdict = "insufficient_data"
    elif not truth or truth["n"] == 0:
        headline = f"Murya: {murya['mean']:.2f}/5 (n={murya['n']}). No human-recording ratings yet to compare against."
        verdict = "insufficient_data"
    else:
        gap = round(truth["mean"] - murya["mean"], 2)
        low_n = murya["n"] < _MIN_TRUSTWORTHY_N or truth["n"] < _MIN_TRUSTWORTHY_N
        if low_n:
            headline = (f"Murya: {murya['mean']:.2f}/5 vs. human speech: {truth['mean']:.2f}/5 "
                        f"(gap {gap:.2f}) — but too few ratings yet (murya n={murya['n']}, "
                        f"human n={truth['n']}) to trust this number. Keep collecting.")
            verdict = "insufficient_data"
        elif gap <= 0.3:
            headline = (f"Murya: {murya['mean']:.2f}/5 vs. human speech: {truth['mean']:.2f}/5 "
                        f"— close to human naturalness (gap {gap:.2f}).")
            verdict = "close_to_human"
        else:
            headline = (f"Murya: {murya['mean']:.2f}/5 vs. human speech: {truth['mean']:.2f}/5 "
                        f"— a meaningful gap remains ({gap:.2f}).")
            verdict = "meaningful_gap"

    # Flag any voice scoring notably below Murya's own overall average — a
    # concrete "this voice needs attention" signal, not just a bare table.
    weak_voices = []
    overall = murya["mean"] if murya and murya["mean"] is not None else None
    if overall is not None:
        for voice, stats in by_voice.items():
            if stats["n"] >= max(5, _MIN_TRUSTWORTHY_N // 4) and stats["mean"] is not None and stats["mean"] <= overall - 0.4:
                weak_voices.append({"voice": voice, "mean": stats["mean"], "n": stats["n"]})
    weak_voices.sort(key=lambda w: w["mean"])

    total_intel = sum(intel_counts.values())
    intel_pct_full = round(100 * intel_counts.get("yes", 0) / total_intel, 1) if total_intel else None
    intel_flag = total_intel >= _MIN_TRUSTWORTHY_N and intel_pct_full is not None and intel_pct_full < 85

    return {
        "headline": headline,
        "verdict": verdict,
        "gap": gap,
        "weak_voices": weak_voices,
        "intelligibility_pct_full": intel_pct_full,
        "intelligibility_flag": intel_flag,
        "min_trustworthy_n": _MIN_TRUSTWORTHY_N,
    }


def list_results() -> dict:
    """Aggregated stats AND a synthesized analysis for the admin dashboard —
    mean/CI per condition, per Murya voice, intelligibility counts, plus a
    plain-language headline/verdict so this is a real eval screen, not just
    numbers to interpret by hand. Computed fresh on every call — ratings
    volume here is nowhere near large enough to need pre-aggregation."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT condition, voice, score, intelligible FROM mos_ratings"
        ).fetchall()

    by_cond: dict[str, list[int]] = {}
    by_voice: dict[str, list[int]] = {}
    intel_counts = {"yes": 0, "partial": 0, "no": 0}
    for r in rows:
        by_cond.setdefault(r["condition"], []).append(r["score"])
        if r["condition"] == "murya":
            by_voice.setdefault(r["voice"], []).append(r["score"])
        if r["intelligible"] in intel_counts:
            intel_counts[r["intelligible"]] += 1

    with _get_conn() as conn:
        session_count = conn.execute(
            "SELECT COUNT(DISTINCT session_id) AS c FROM mos_ratings WHERE session_id IS NOT NULL"
        ).fetchone()["c"]

    by_condition = {cond: _mean_ci(scores) for cond, scores in by_cond.items()}
    by_voice_stats = {voice: _mean_ci(scores) for voice, scores in by_voice.items()}

    return {
        "total_ratings": len(rows),
        "session_count": session_count,
        "by_condition": by_condition,
        "by_voice": by_voice_stats,
        "intelligibility": intel_counts,
        "analysis": _analysis(by_condition, by_voice_stats, intel_counts),
    }


_VALID_VERDICTS = ("approved_for_training", "needs_more_data", "rejected")


def record_decision(verdict: str, note: str | None, admin: str) -> int:
    """The admin's explicit sign-off on the CURRENT results snapshot. Snapshots
    the murya/ground_truth means at decision time (not just a live pointer)
    so a later change in the data can never quietly rewrite what was actually
    decided and why."""
    if verdict not in _VALID_VERDICTS:
        raise ValueError(f"invalid verdict: {verdict!r}")
    results = list_results()
    murya = results["by_condition"].get("murya", {})
    truth = results["by_condition"].get("ground_truth", {})
    now = time.time()
    with _get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO mos_decisions
               (verdict, note, total_ratings_at_time, murya_mean_at_time,
                ground_truth_mean_at_time, admin, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (verdict, (note or "").strip()[:500] or None, results["total_ratings"],
             murya.get("mean"), truth.get("mean"), admin, now),
        )
        return cur.lastrowid


def list_decisions(limit: int = 50) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM mos_decisions ORDER BY created_at DESC LIMIT ?", (int(limit),)
        ).fetchall()
    return [dict(r) for r in rows]


def export_ratings() -> list[dict]:
    """Every raw rating row, for offline analysis (real CIs, significance
    tests) beyond what the dashboard's quick normal-approximation gives."""
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT session_id, clip_id, condition, voice, sentence_id, score,
                      intelligible, replays, region, native_speaker, submitted_by, created_at
               FROM mos_ratings ORDER BY created_at"""
        ).fetchall()
    return [dict(r) for r in rows]


def _reset_for_tests() -> None:
    with _get_conn() as conn:
        conn.execute("DROP TABLE IF EXISTS mos_stimuli")
        conn.execute("DROP TABLE IF EXISTS mos_ratings")
        conn.execute("DROP TABLE IF EXISTS mos_decisions")
    init_db()
