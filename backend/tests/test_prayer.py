"""Tests for the local prayer-time (Salla) computation.

These validate ASTRONOMICAL correctness (ordering, solar-noon sanity, and
self-consistency) rather than matching one published timetable to the minute —
different sources use different twilight angles, refraction, and safety
margins, so a few minutes of variance is expected and honest.
"""

from datetime import date

import pytest

from services import prayer_service as ps

_ORDER = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]


def _to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def test_kano_times_are_valid_and_ordered():
    r = ps.prayer_times("Kano", date(2026, 7, 11))
    assert r is not None
    times = r["times"]
    # All six present and valid HH:MM.
    for key in _ORDER:
        hh, mm = times[key].split(":")
        assert 0 <= int(hh) < 24 and 0 <= int(mm) < 60
    # Strictly increasing through the day.
    minutes = [_to_minutes(times[k]) for k in _ORDER]
    assert minutes == sorted(minutes)
    assert len(set(minutes)) == len(minutes)


def test_kano_dhuhr_near_solar_noon():
    """Dhuhr is the solar transit; for Kano (long 8.52 E, WAT) that is ~12:31.
    Guards against longitude/timezone/equation-of-time sign errors."""
    r = ps.prayer_times("Kano", date(2026, 7, 11))
    dhuhr = _to_minutes(r["times"]["dhuhr"])
    assert _to_minutes("12:20") <= dhuhr <= _to_minutes("12:45")


def test_kano_sunrise_sunset_symmetric_about_noon():
    """Sunrise and sunset are symmetric around solar noon — a strong check on
    the hour-angle math."""
    r = ps.prayer_times("Kano", date(2026, 7, 11))
    t = r["times"]
    noon = _to_minutes(t["dhuhr"])
    morning_gap = noon - _to_minutes(t["sunrise"])
    evening_gap = _to_minutes(t["maghrib"]) - noon
    # Within ~5 minutes of each other (Maghrib carries a small refraction margin).
    assert abs(morning_gap - evening_gap) <= 6


def test_method_and_metadata_present():
    r = ps.prayer_times("Kano", date(2026, 7, 11))
    assert r["method"] == "Muslim World League"
    assert r["city"] == "Kano"
    assert r["date"] == "2026-07-11"
    assert "WAT" in r["timezone"]


def test_unknown_city_returns_none():
    assert ps.prayer_times("Atlantis", date(2026, 7, 11)) is None


def test_explicit_coordinates_work():
    """Any location is supported via explicit lat/long (Mecca here)."""
    r = ps.prayer_times("Makka", date(2026, 7, 11), latitude=21.42, longitude=39.83)
    assert r is not None
    minutes = [_to_minutes(r["times"][k]) for k in _ORDER]
    assert minutes == sorted(minutes)


def test_list_cities_and_ready():
    cities = ps.list_cities()
    assert "Kano" in cities and "Sokoto" in cities and "Lagos" in cities
    assert ps.prayer_ready() is True


def test_hanafi_asr_is_later_than_shafii():
    """Hanafi Asr (shadow factor 2) must fall later than Shafi'i (factor 1) —
    sanity on the asr_factor parameter."""
    shafii = ps.prayer_times("Kano", date(2026, 7, 11), asr_factor=1)
    hanafi = ps.prayer_times("Kano", date(2026, 7, 11), asr_factor=2)
    assert _to_minutes(hanafi["times"]["asr"]) > _to_minutes(shafii["times"]["asr"])
