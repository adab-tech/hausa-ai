"""
Privacy-preserving visitor analytics — counts and rough geography only.

Deliberately stores NO IP addresses and NO PII. Uniqueness is counted via the
existing anonymous per-device token (the ``X-Contributor-Id`` UUID the frontend
keeps in localStorage — see contributor.py / services/localService.ts), never
by IP. Geography is derived from the browser's IANA timezone string (e.g.
"Africa/Lagos") that the frontend sends in the beacon body — NOT from a GeoIP
lookup. This keeps the whole system dependency-free and non-identifying.

Backed by SQLite on the same persistent volume as admin.db (FEEDBACK_DATA_DIR),
following the connection/lifecycle pattern in admin_store.py: a fresh
connection per call, committed and closed via the _get_conn() context manager.
Correct for the single-Fly-machine deployment (see docs/deployment.md); revisit
before scaling out horizontally.
"""

import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

_DATA_DIR = Path(os.getenv("FEEDBACK_DATA_DIR", Path(__file__).resolve().parent / "data"))
_DB_PATH = _DATA_DIR / "analytics.db"

# Retention: how long a visit row is kept before it's eligible for pruning.
# Without this the visits table (one row per page load, from a PUBLIC,
# rate-limit-bypassable beacon -- see rate_limit.py's finding on
# X-Contributor-Id-keyed limits) grows forever. Configurable via env so an
# operator can tune it without a redeploy; 90 days is generous enough to
# cover the "all_time"/"last_7d" dashboard figures while still bounding
# growth.
_RETENTION_DAYS = int(os.getenv("ANALYTICS_RETENTION_DAYS", "90"))

# record_visit() is the busiest, most latency-sensitive path here (called on
# every page load), so pruning is NOT run on every single insert -- that
# would add a DELETE's cost to the hottest path for no benefit. Instead it's
# opportunistic and rate-limited to at most once per this interval, so
# cleanup still happens automatically under normal traffic without needing
# an admin to open the dashboard (summary() is comparatively rare/manual).
_PRUNE_INTERVAL_SECONDS = 6 * 3600
_prune_state_lock = threading.Lock()
_last_prune_ts = 0.0

# Stored-string caps — bound row size and reject junk/oversized client input.
_MAX_TZ = 64
_MAX_LANG = 16
_MAX_PATH = 128
_MAX_CID = 64

# ---------------------------------------------------------------------------
# Timezone -> country/region map.
#
# APPROXIMATION ONLY. A browser's IANA timezone is a coarse, self-reported
# geography signal — good enough to know roughly where visitors are, and
# intentionally far less precise (and less identifying) than a GeoIP lookup.
# Zones we don't recognise fall back to a per-continent "(other)" bucket, or
# "Unknown" when even the continent is missing/unparseable.
# ---------------------------------------------------------------------------
_TZ_COUNTRY = {
    "Africa/Lagos": "Nigeria",
    "Africa/Kano": "Nigeria",
    "Africa/Niamey": "Niger",
    "Africa/Accra": "Ghana",
    "Africa/Ndjamena": "Chad",
    "Africa/Douala": "Cameroon",
    "Africa/Bangui": "Central African Republic",
    "Europe/London": "United Kingdom",
    "America/New_York": "United States",
    "America/Chicago": "United States",
    "America/Los_Angeles": "United States",
    "America/Denver": "United States",
    "Asia/Riyadh": "Saudi Arabia",
    "Asia/Dubai": "UAE",
    "Europe/Paris": "France",
    "Europe/Berlin": "Germany",
    # Canada zones
    "America/Toronto": "Canada",
    "America/Vancouver": "Canada",
    "America/Edmonton": "Canada",
    "America/Winnipeg": "Canada",
    "America/Halifax": "Canada",
    "America/Montreal": "Canada",
}


def _country_from_timezone(tz: str | None) -> str:
    """Map an IANA timezone to a coarse country/region label (approximation)."""
    if not tz:
        return "Unknown"
    tz = tz.strip()
    if tz in _TZ_COUNTRY:
        return _TZ_COUNTRY[tz]
    # Fall back to the continent (first path segment) as a coarse bucket.
    region = tz.split("/", 1)[0].strip()
    if region in {"Africa", "Europe", "America", "Asia", "Australia", "Pacific", "Antarctica", "Indian", "Atlantic"}:
        return f"{region} (other)"
    return "Unknown"


@contextmanager
def _get_conn():
    """Fresh connection per call, committed on success and always closed —
    same rationale as admin_store._get_conn (sqlite3's own context manager
    commits but never closes, leaking a handle per call)."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the visits table + day index if missing."""
    with _get_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                day TEXT NOT NULL,
                contributor_id TEXT,
                timezone TEXT,
                country TEXT,
                lang TEXT,
                path TEXT
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_day ON visits(day)")


def _cap(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return value[:limit]


def _utc_day(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def prune_old_visits(retention_days: int | None = None) -> int:
    """Delete visit rows older than `retention_days` (default
    ANALYTICS_RETENTION_DAYS / 90). Returns the number of rows deleted.
    Safe to call anytime; a no-op on an empty/fresh table."""
    days = _RETENTION_DAYS if retention_days is None else retention_days
    cutoff_day = _utc_day(time.time() - days * 86400)
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM visits WHERE day < ?", (cutoff_day,))
        return cur.rowcount


def _maybe_prune_old_visits() -> None:
    """Opportunistically run prune_old_visits(), rate-limited to at most
    once per _PRUNE_INTERVAL_SECONDS so record_visit (called on every page
    load) doesn't pay a DELETE's cost on every single insert."""
    global _last_prune_ts
    now = time.time()
    with _prune_state_lock:
        if now - _last_prune_ts < _PRUNE_INTERVAL_SECONDS:
            return
        _last_prune_ts = now
    prune_old_visits()


def record_visit(
    contributor_id: str | None,
    timezone: str | None,
    lang: str | None,
    path: str | None,
) -> None:
    """Insert one visit row. Never raises — analytics must never break the
    client beacon. Derives the UTC day and a coarse country from the
    timezone, and caps all stored string lengths."""
    try:
        ts = time.time()
        cid = _cap(contributor_id, _MAX_CID)
        tz = _cap(timezone, _MAX_TZ)
        lang_v = _cap(lang, _MAX_LANG)
        path_v = _cap(path, _MAX_PATH)
        country = _country_from_timezone(tz)
        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO visits
                   (ts, day, contributor_id, timezone, country, lang, path)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (ts, _utc_day(ts), cid, tz, country, lang_v, path_v),
            )
        # Best-effort, rate-limited retention cleanup -- must never break or
        # slow down the public beacon this function serves.
        _maybe_prune_old_visits()
    except Exception:
        # Swallow everything — a failed analytics write must not surface to
        # the user or interrupt the request.
        pass


def summary(days: int = 14) -> dict:
    """Aggregate stored visits into the admin dashboard shape.

    Returns:
        {
          "total_visits": int,
          "unique_devices": {"today": int, "last_7d": int, "all_time": int},
          "daily": [{"day", "visits", "unique"}, ...],  # last `days`, oldest->newest, zero-filled
          "by_country": [{"country", "visits"}, ...],    # desc, top 15
          "by_language": [{"lang", "visits"}, ...],       # desc, top 8
        }
    All time boundaries are computed in UTC. Empty DB -> zeros / empty lists.
    """
    now = time.time()
    today = _utc_day(now)
    day_7_ago = _utc_day(now - 7 * 86400)
    n = max(1, int(days))
    window_start_day = _utc_day(now - (n - 1) * 86400)

    with _get_conn() as conn:
        total_visits = conn.execute("SELECT COUNT(*) AS c FROM visits").fetchone()["c"]

        unique_today = conn.execute(
            "SELECT COUNT(DISTINCT contributor_id) AS c FROM visits "
            "WHERE day = ? AND contributor_id IS NOT NULL",
            (today,),
        ).fetchone()["c"]
        unique_7d = conn.execute(
            "SELECT COUNT(DISTINCT contributor_id) AS c FROM visits "
            "WHERE day >= ? AND contributor_id IS NOT NULL",
            (day_7_ago,),
        ).fetchone()["c"]
        unique_all = conn.execute(
            "SELECT COUNT(DISTINCT contributor_id) AS c FROM visits "
            "WHERE contributor_id IS NOT NULL"
        ).fetchone()["c"]

        # Per-day visits + uniques for the requested window. Filtered by the
        # window's start day IN THE QUERY (not fetched for the whole table's
        # history and then sliced down in Python below) -- the old version
        # scanned and grouped every row ever inserted on every summary()
        # call regardless of `days`, getting slower over time with no way
        # to reverse it short of a code change.
        daily_rows = conn.execute(
            """SELECT day,
                      COUNT(*) AS visits,
                      COUNT(DISTINCT contributor_id) AS unique_devices
               FROM visits
               WHERE day >= ?
               GROUP BY day""",
            (window_start_day,),
        ).fetchall()
        daily_map = {
            r["day"]: {"visits": r["visits"], "unique": r["unique_devices"]}
            for r in daily_rows
        }

        country_rows = conn.execute(
            """SELECT country, COUNT(*) AS visits
               FROM visits
               GROUP BY country
               ORDER BY visits DESC, country ASC
               LIMIT 15"""
        ).fetchall()

        lang_rows = conn.execute(
            """SELECT lang, COUNT(*) AS visits
               FROM visits
               WHERE lang IS NOT NULL
               GROUP BY lang
               ORDER BY visits DESC, lang ASC
               LIMIT 8"""
        ).fetchall()

    # Zero-fill the last `days` days, oldest -> newest (n computed above,
    # shared with the SQL window filter).
    daily = []
    for i in range(n - 1, -1, -1):
        d = _utc_day(now - i * 86400)
        entry = daily_map.get(d, {"visits": 0, "unique": 0})
        daily.append({"day": d, "visits": entry["visits"], "unique": entry["unique"]})

    return {
        "total_visits": total_visits,
        "unique_devices": {
            "today": unique_today,
            "last_7d": unique_7d,
            "all_time": unique_all,
        },
        "daily": daily,
        "by_country": [
            {"country": r["country"] or "Unknown", "visits": r["visits"]}
            for r in country_rows
        ],
        "by_language": [
            {"lang": r["lang"], "visits": r["visits"]} for r in lang_rows
        ],
    }


def _reset_for_tests() -> None:
    """Drop and recreate the visits table — convenience for isolated tests."""
    with _get_conn() as conn:
        conn.execute("DROP TABLE IF EXISTS visits")
    init_db()
