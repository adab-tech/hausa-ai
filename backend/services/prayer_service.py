"""
Islamic prayer-time (Salla) computation — pure, local, offline.

Murya is a sovereign app: prayer times for religious observance must be
computed on-device with no network call and no third-party API. This module
implements the standard astronomical algorithm popularised by PrayTimes.org
(Hamid Zarrabi-Zadeh) — solar declination, the equation of time, and the
sun hour-angle for a given altitude — which is the same well-established set
of equations used by most reputable prayer-time software.

Method / conventions (all overridable):
  * Muslim World League: Fajr twilight angle 18 deg, Isha twilight angle 17 deg.
  * Asr: Shafi'i school (shadow factor 1). Hanafi would be factor 2.
  * Sunrise / sunset (Maghrib) at the standard 0.833 deg below the horizon
    (accounts for atmospheric refraction and the solar disc radius).

Honesty note: these are computed times. They are astronomically sound and
typically land within a few minutes of published tables, but small variance
between sources is normal (different refraction, elevation, and rounding
choices). The returned dict always names the calculation method so callers
can be transparent with users.

Stdlib only: math + datetime. No network, no dependencies.
"""

from __future__ import annotations

import math
from datetime import date

# --- Convention defaults (Muslim World League) -----------------------------

METHOD_NAME = "Muslim World League"
FAJR_ANGLE = 18.0
ISHA_ANGLE = 17.0
ASR_FACTOR_SHAFII = 1  # shadow length factor; Hanafi = 2
RISE_SET_ANGLE = 0.833  # sun altitude at sunrise/sunset (refraction + disc)

TIMEZONE_LABEL = "WAT (UTC+1)"
_WAT_OFFSET = 1.0  # Africa/Lagos, no DST

# --- Nigerian cities: (latitude, longitude) in degrees, East positive -------

_CITIES: dict[str, tuple[float, float]] = {
    "Kano": (12.00, 8.52),
    "Lagos": (6.45, 3.39),
    "Abuja": (9.06, 7.49),
    "Sokoto": (13.06, 5.24),
    "Kaduna": (10.52, 7.44),
    "Maiduguri": (11.83, 13.15),
    "Katsina": (12.99, 7.60),
    "Zaria": (11.09, 7.72),
    "Gusau": (12.16, 6.66),
    "Bauchi": (10.31, 9.84),
    "Ilorin": (8.50, 4.55),
    "Jos": (9.90, 8.89),
}


# --- Trig helpers in degrees ------------------------------------------------


def _sin(d: float) -> float:
    return math.sin(math.radians(d))


def _cos(d: float) -> float:
    return math.cos(math.radians(d))


def _tan(d: float) -> float:
    return math.tan(math.radians(d))


def _arcsin(x: float) -> float:
    return math.degrees(math.asin(x))


def _arccos(x: float) -> float:
    return math.degrees(math.acos(x))


def _arctan2(y: float, x: float) -> float:
    return math.degrees(math.atan2(y, x))


def _arccot(x: float) -> float:
    return math.degrees(math.atan2(1.0, x))


def _fix_angle(a: float) -> float:
    a = a % 360.0
    return a + 360.0 if a < 0 else a


def _fix_hour(h: float) -> float:
    h = h % 24.0
    return h + 24.0 if h < 0 else h


# --- Astronomy --------------------------------------------------------------


def _julian(year: int, month: int, day: int) -> float:
    """Julian day number for 0h UT of the given civil date."""
    if month <= 2:
        year -= 1
        month += 12
    a = math.floor(year / 100.0)
    b = 2 - a + math.floor(a / 4.0)
    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day
        + b
        - 1524.5
    )


def _sun_position(jd: float) -> tuple[float, float]:
    """Return (declination_deg, equation_of_time_hours) for Julian day ``jd``."""
    d = jd - 2451545.0  # days since J2000.0
    g = _fix_angle(357.529 + 0.98560028 * d)  # mean anomaly
    q = _fix_angle(280.459 + 0.98564736 * d)  # mean longitude
    ecl = _fix_angle(q + 1.915 * _sin(g) + 0.020 * _sin(2 * g))  # ecliptic long.
    obliquity = 23.439 - 0.00000036 * d
    declination = _arcsin(_sin(obliquity) * _sin(ecl))
    right_ascension = _arctan2(_cos(obliquity) * _sin(ecl), _cos(ecl)) / 15.0
    right_ascension = _fix_hour(right_ascension)
    eq_of_time = q / 15.0 - right_ascension
    return declination, eq_of_time


def _mid_day(jd: float, t: float) -> float:
    """Local solar-noon time (hours) for the day-fraction guess ``t``."""
    _, eq = _sun_position(jd + t)
    return _fix_hour(12.0 - eq)


def _sun_angle_time(
    jd: float, lat: float, angle: float, t: float, direction: str
) -> float:
    """Time (hours) when the sun sits ``angle`` degrees below the horizon.

    ``direction`` is 'morning' (before noon) or 'evening' (after noon).
    """
    decl, _ = _sun_position(jd + t)
    noon = _mid_day(jd, t)
    numerator = -_sin(angle) - _sin(decl) * _sin(lat)
    denominator = _cos(decl) * _cos(lat)
    hour_angle = _arccos(numerator / denominator) / 15.0
    return noon + (-hour_angle if direction == "morning" else hour_angle)


def _asr_time(jd: float, lat: float, factor: float, t: float) -> float:
    """Time (hours) of Asr for the given shadow-length ``factor``."""
    decl, _ = _sun_position(jd + t)
    # Sun altitude at which an object's shadow equals ``factor`` * its height,
    # plus the shadow already present at noon.
    angle = -_arccot(factor + _tan(abs(lat - decl)))
    return _sun_angle_time(jd, lat, angle, t, "evening")


# --- Public API -------------------------------------------------------------


def list_cities() -> list[str]:
    """Names of the built-in Nigerian cities, alphabetically."""
    return sorted(_CITIES)


def prayer_ready() -> bool:
    """Always True — computation is pure and local, no key or network needed."""
    return True


def _to_hhmm(hours: float) -> str:
    """Round a fractional-hour value to the nearest minute as 'HH:MM' (24h)."""
    total_minutes = int(round(hours * 60.0)) % (24 * 60)
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def prayer_times(
    city: str = "Kano",
    on_date: date | None = None,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    fajr_angle: float = FAJR_ANGLE,
    isha_angle: float = ISHA_ANGLE,
    asr_factor: float = ASR_FACTOR_SHAFII,
) -> dict | None:
    """Five daily prayer times plus sunrise for a Nigerian city (or coords).

    Returns a dict with city, ISO date, method, timezone, and a ``times`` map
    ({fajr, sunrise, dhuhr, asr, maghrib, isha}) of "HH:MM" strings in WAT.
    Unknown city (with no explicit lat/long) returns None. Never raises to
    callers — any internal error also yields None.
    """
    try:
        if latitude is not None and longitude is not None:
            lat, lng = float(latitude), float(longitude)
            city_name = city
        else:
            match = _CITIES.get(city)
            if match is None:
                return None
            lat, lng = match
            city_name = city

        day = on_date or date.today()

        # Fold longitude into the Julian day so the day-fractions below track
        # local clock time; the final offset adds the timezone and longitude
        # correction (timezone - lng/15).
        jd = _julian(day.year, day.month, day.day) - lng / (15.0 * 24.0)
        tz_adjust = _WAT_OFFSET - lng / 15.0

        fajr = _sun_angle_time(jd, lat, fajr_angle, 5.0 / 24.0, "morning")
        sunrise = _sun_angle_time(jd, lat, RISE_SET_ANGLE, 6.0 / 24.0, "morning")
        dhuhr = _mid_day(jd, 12.0 / 24.0)
        asr = _asr_time(jd, lat, asr_factor, 13.0 / 24.0)
        maghrib = _sun_angle_time(jd, lat, RISE_SET_ANGLE, 18.0 / 24.0, "evening")
        isha = _sun_angle_time(jd, lat, isha_angle, 18.0 / 24.0, "evening")

        times = {
            "fajr": fajr,
            "sunrise": sunrise,
            "dhuhr": dhuhr,
            "asr": asr,
            "maghrib": maghrib,
            "isha": isha,
        }

        return {
            "city": city_name,
            "date": day.isoformat(),
            "method": METHOD_NAME,
            "timezone": TIMEZONE_LABEL,
            "times": {k: _to_hhmm(v + tz_adjust) for k, v in times.items()},
        }
    except Exception:
        return None
