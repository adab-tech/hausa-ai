"""Tests for the privacy-preserving visitor-analytics store and endpoints.

The DB is isolated to a per-test tmp_path via monkeypatch (same style as the
admin_store fixtures) so nothing touches the real analytics.db.
"""

import time

import pytest


@pytest.fixture
def isolated_analytics_store(tmp_path, monkeypatch):
    """Fresh analytics_store DB per test, isolated to tmp_path."""
    import analytics_store

    monkeypatch.setattr(analytics_store, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(analytics_store, "_DB_PATH", tmp_path / "analytics.db")
    analytics_store.init_db()
    return analytics_store


# ---------------------------------------------------------------------------
# Store-level tests
# ---------------------------------------------------------------------------
def test_record_visit_maps_timezone_to_country(isolated_analytics_store):
    store = isolated_analytics_store
    store.record_visit("dev-1", "Africa/Lagos", "ha", "/")
    summary = store.summary()

    countries = {c["country"]: c["visits"] for c in summary["by_country"]}
    assert countries.get("Nigeria") == 1
    assert summary["total_visits"] == 1


def test_same_contributor_counts_one_unique_two_visits(isolated_analytics_store):
    store = isolated_analytics_store
    store.record_visit("same-device", "Africa/Lagos", "ha", "/")
    store.record_visit("same-device", "Africa/Lagos", "ha", "/chat")
    summary = store.summary()

    assert summary["total_visits"] == 2
    assert summary["unique_devices"]["all_time"] == 1
    assert summary["unique_devices"]["today"] == 1


def test_unknown_and_none_timezone_never_crash(isolated_analytics_store):
    store = isolated_analytics_store
    store.record_visit("dev-a", None, "en", "/")
    store.record_visit("dev-b", "Mars/Olympus_Mons", "en", "/")
    summary = store.summary()

    countries = {c["country"]: c["visits"] for c in summary["by_country"]}
    # None -> Unknown; an unrecognised non-continent zone -> Unknown too.
    assert countries.get("Unknown") == 2
    assert summary["total_visits"] == 2


def test_continent_fallback_bucket(isolated_analytics_store):
    store = isolated_analytics_store
    store.record_visit("dev-c", "Africa/Timbuktu", "ha", "/")
    summary = store.summary()
    countries = {c["country"] for c in summary["by_country"]}
    assert "Africa (other)" in countries


def test_summary_empty_db(isolated_analytics_store):
    store = isolated_analytics_store
    summary = store.summary(days=14)

    assert summary["total_visits"] == 0
    assert summary["unique_devices"] == {"today": 0, "last_7d": 0, "all_time": 0}
    assert summary["by_country"] == []
    assert summary["by_language"] == []
    # daily is zero-filled to `days` entries, oldest -> newest.
    assert len(summary["daily"]) == 14
    assert all(d["visits"] == 0 and d["unique"] == 0 for d in summary["daily"])
    assert summary["daily"][0]["day"] <= summary["daily"][-1]["day"]


def _insert_raw_visit(store, days_ago: int, contributor_id: str = "old-dev") -> None:
    """Insert a visit row directly, backdated by `days_ago` -- bypasses
    record_visit()'s use of time.time() so retention/window tests can place
    rows precisely in the past."""
    ts = time.time() - days_ago * 86400
    day = store._utc_day(ts)
    with store._get_conn() as conn:
        conn.execute(
            """INSERT INTO visits (ts, day, contributor_id, timezone, country, lang, path)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ts, day, contributor_id, "Africa/Lagos", "Nigeria", "ha", "/"),
        )


# ---------------------------------------------------------------------------
# Regression: #13 -- the visits table had no retention/pruning logic, and
# summary()'s daily aggregate scanned the WHOLE table regardless of the
# requested date window.
# ---------------------------------------------------------------------------
def test_prune_old_visits_deletes_rows_past_retention(isolated_analytics_store):
    store = isolated_analytics_store
    _insert_raw_visit(store, days_ago=200, contributor_id="ancient")
    _insert_raw_visit(store, days_ago=1, contributor_id="recent")

    deleted = store.prune_old_visits(retention_days=90)

    assert deleted == 1
    summary = store.summary(days=365)
    assert summary["total_visits"] == 1  # only the recent row survives


def test_prune_old_visits_keeps_rows_within_retention(isolated_analytics_store):
    store = isolated_analytics_store
    _insert_raw_visit(store, days_ago=10, contributor_id="within-window")

    deleted = store.prune_old_visits(retention_days=90)

    assert deleted == 0
    assert store.summary(days=30)["total_visits"] == 1


def test_maybe_prune_is_rate_limited(isolated_analytics_store, monkeypatch):
    """record_visit's opportunistic prune must not run a DELETE on every
    single call -- the busiest, most public path in this module -- only at
    most once per _PRUNE_INTERVAL_SECONDS."""
    store = isolated_analytics_store
    _insert_raw_visit(store, days_ago=200, contributor_id="ancient")

    calls = {"n": 0}
    real_prune = store.prune_old_visits

    def _counting_prune(*a, **kw):
        calls["n"] += 1
        return real_prune(*a, **kw)

    monkeypatch.setattr(store, "prune_old_visits", _counting_prune)
    monkeypatch.setattr(store, "_last_prune_ts", time.time())  # just pruned

    store.record_visit("d1", "Africa/Lagos", "ha", "/")
    store.record_visit("d2", "Africa/Lagos", "ha", "/")

    assert calls["n"] == 0  # still within the rate-limit interval

    monkeypatch.setattr(store, "_last_prune_ts", 0.0)  # force it due
    store.record_visit("d3", "Africa/Lagos", "ha", "/")

    assert calls["n"] == 1


def test_summary_daily_window_excludes_visits_outside_requested_days(isolated_analytics_store):
    """A visit far outside the requested `days` window must not appear in
    the zero-filled `daily` series, even though it still counts toward the
    all-time total_visits figure."""
    store = isolated_analytics_store
    _insert_raw_visit(store, days_ago=60, contributor_id="outside-window")
    _insert_raw_visit(store, days_ago=1, contributor_id="inside-window")

    summary = store.summary(days=7)

    assert summary["total_visits"] == 2  # all-time count unaffected
    assert sum(d["visits"] for d in summary["daily"]) == 1  # only the recent one
    assert len(summary["daily"]) == 7


def test_by_language_aggregates(isolated_analytics_store):
    store = isolated_analytics_store
    store.record_visit("d1", "Africa/Lagos", "ha", "/")
    store.record_visit("d2", "Africa/Lagos", "ha", "/")
    store.record_visit("d3", "Europe/London", "en", "/")
    summary = store.summary()

    langs = {row["lang"]: row["visits"] for row in summary["by_language"]}
    assert langs.get("ha") == 2
    assert langs.get("en") == 1


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_visit_beacon_public_and_records(client, isolated_analytics_store):
    store = isolated_analytics_store
    resp = await client.post(
        "/api/analytics/visit",
        json={"timezone": "Africa/Lagos", "lang": "ha", "path": "/"},
        headers={"X-Contributor-Id": "11111111-1111-1111-1111-111111111111"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    summary = store.summary()
    assert summary["total_visits"] == 1
    assert summary["unique_devices"]["all_time"] == 1
    countries = {c["country"] for c in summary["by_country"]}
    assert "Nigeria" in countries


@pytest.mark.anyio
async def test_visit_beacon_ok_with_empty_body(client, isolated_analytics_store):
    resp = await client.post("/api/analytics/visit", json={})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@pytest.mark.anyio
async def test_admin_analytics_requires_session(client, isolated_analytics_store):
    resp = await client.get("/api/admin/analytics")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_admin_analytics_with_session(client, admin_session, isolated_analytics_store):
    resp = await client.get("/api/admin/analytics")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {
        "total_visits",
        "unique_devices",
        "daily",
        "by_country",
        "by_language",
    }
    assert set(body["unique_devices"].keys()) == {"today", "last_7d", "all_time"}
    assert isinstance(body["daily"], list)
