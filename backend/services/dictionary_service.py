"""
Hausa <-> English dictionary lookup backed by the real Robinson (1914) lexicon.

Purpose — let Murya define/translate words with a CITED source instead of
guessing. Every returned entry carries its provenance
(e.g. "robinson_1914_vol2") so the chat path can say where a definition came
from.

Design contract — graceful degradation is mandatory:
  * If the lexicon file cannot be found or parsed, dictionary_ready() is False
    and define() returns [] without ever raising into the request path. The
    caller then behaves exactly as before (honest "I don't have that").
  * Loading is lazy and thread-safe: the file is read at most once, on first
    use, behind a lock. Subsequent calls hit an in-memory index.

Stdlib only (json, os, pathlib, threading, logging) — no new dependency.

Data shape — one JSON object per line:
  {"source_en": "abandon", "target_ha": "hari",
   "context": "tr. v. hari, har.", "provenance": "robinson_1914_vol2"}
English headwords may repeat (multiple Hausa senses).
"""

import json
import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger("murya.dictionary")

# Environment override for the lexicon path (highest priority).
_ENV_VAR = "DICTIONARY_PATH"

# Fixed container location (the image bakes the lexicon here).
_CONTAINER_PATH = Path("/app/data/robinson/en_ha_pairs.jsonl")

# Repo-root fallback, resolved relative to THIS file so it works from any cwd.
# services/dictionary_service.py -> backend/ -> <repo-root>
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_REPO_PATH = _REPO_ROOT / "data" / "processed" / "robinson" / "en_ha_pairs.jsonl"

# Diacritic folding: Hausa hooked letters -> plain ASCII, so "ƙasa" and "kasa"
# resolve to the same index key. The ORIGINAL spelling is always preserved in
# the returned entry — this only affects lookup keys.
_DIACRITIC_MAP = {
    "ɓ": "b",
    "ɗ": "d",
    "ƙ": "k",
    "ƴ": "y",
    "Ɓ": "b",
    "Ɗ": "d",
    "Ƙ": "k",
    "Ƴ": "y",
}

# ---------------------------------------------------------------------------
# Singleton state (guarded by _LOCK)
# ---------------------------------------------------------------------------
_LOCK = threading.Lock()
_LOADED = False
_READY = False
_EN_INDEX: dict[str, list[dict]] = {}  # english headword (folded) -> entries
_HA_INDEX: dict[str, list[dict]] = {}  # hausa word (folded) -> entries


def _fold(text: str) -> str:
    """Normalize a lookup key: strip, lowercase, and fold Hausa hooked letters
    to their plain ASCII equivalents. Used for KEYS only, never for stored
    values."""
    folded = "".join(_DIACRITIC_MAP.get(ch, ch) for ch in text)
    return folded.strip().lower()


def _resolve_path() -> Path | None:
    """Resolve the lexicon path.

    If DICTIONARY_PATH is set it is AUTHORITATIVE — the file it names is used,
    or the dictionary is unavailable if that file is missing. We do not
    silently fall back to a different lexicon when an explicit override was
    given (that would be surprising and could load stale data in tests/ops).

    With no override, try the baked-in container path, then the repo copy;
    return the first that exists, else None."""
    env_value = os.getenv(_ENV_VAR)
    if env_value:
        p = Path(env_value)
        try:
            return p if p.is_file() else None
        except OSError:
            return None
    for candidate in (_CONTAINER_PATH, _REPO_PATH):
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


# Grammatical abbreviations left in the Robinson OCR extraction as if they
# were words (e.g. context "intr. v. tarara." split so "intr"/"v"/"etc"
# became bogus target_ha values). Filtering them at index time keeps junk
# like water->"intr" out of definitions without touching the source data.
_ABBREV_NOISE = {
    "tr", "intr", "v", "n", "adj", "adv", "pl", "sing", "etc", "see", "cf",
    "conj", "prep", "pron", "int", "interj", "vol", "fig", "lit", "abbr",
    "id", "ibid", "eg", "ie", "esp", "usu", "var", "dial",
}


def _is_noise(value: str) -> bool:
    """True for OCR/grammatical-tag artifacts that should not be indexed as a
    real headword or translation."""
    v = value.strip().strip(".").lower()
    return (not v) or (v in _ABBREV_NOISE) or (len(v) == 1 and v.isalpha())


def _index_entry(key_field: str, index: dict[str, list[dict]], entry: dict) -> None:
    """Index `entry` under its folded key for `key_field`, skipping OCR-noise
    values and deduplicating identical entries under one key."""
    raw = entry.get(key_field)
    if not raw or not isinstance(raw, str) or _is_noise(raw):
        return
    key = _fold(raw)
    if not key:
        return
    bucket = index.setdefault(key, [])
    if entry not in bucket:
        bucket.append(entry)


def _load() -> None:
    """Read the lexicon once and build the English and Hausa indexes. Sets
    _READY True on success. Never raises — any failure logs at warning and
    leaves the dictionary unavailable."""
    global _LOADED, _READY
    _LOADED = True
    _EN_INDEX.clear()
    _HA_INDEX.clear()

    path = _resolve_path()
    if path is None:
        logger.warning(
            "Dictionary lexicon not found (checked %s, %s, %s); "
            "dictionary lookups disabled.",
            os.getenv(_ENV_VAR) or "<%s unset>" % _ENV_VAR,
            _CONTAINER_PATH,
            _REPO_PATH,
        )
        _READY = False
        return

    try:
        count = 0
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                entry = {
                    "source_en": row.get("source_en", ""),
                    "target_ha": row.get("target_ha", ""),
                    "context": row.get("context", ""),
                    "provenance": row.get("provenance", ""),
                }
                # Drop whole entries where either side is an OCR/grammar-tag
                # artifact (e.g. target_ha "intr"/"etc") — a bad extraction,
                # not a real translation pair.
                if _is_noise(entry["source_en"]) or _is_noise(entry["target_ha"]):
                    continue
                _index_entry("source_en", _EN_INDEX, entry)
                _index_entry("target_ha", _HA_INDEX, entry)
                count += 1
        _READY = True
        logger.info(
            "Dictionary loaded: %d entries from %s (%d EN keys, %d HA keys).",
            count,
            path,
            len(_EN_INDEX),
            len(_HA_INDEX),
        )
    except OSError as exc:
        logger.warning("Failed to read dictionary lexicon %s: %s", path, exc)
        _READY = False


def _ensure_loaded() -> None:
    """Lazily trigger a one-time, thread-safe load."""
    if _LOADED:
        return
    with _LOCK:
        if not _LOADED:
            _load()


def dictionary_ready() -> bool:
    """True iff the lexicon loaded successfully and lookups will work."""
    _ensure_loaded()
    return _READY


def _make_result(entry: dict, direction: str) -> dict:
    """Shape a stored entry into a caller-facing result for the given
    direction. headword/translation orient to the query direction while
    preserving original spellings."""
    if direction == "en->ha":
        headword = entry.get("source_en", "")
        translation = entry.get("target_ha", "")
    else:  # ha->en
        headword = entry.get("target_ha", "")
        translation = entry.get("source_en", "")
    return {
        "headword": headword,
        "translation": translation,
        "context": entry.get("context", ""),
        "provenance": entry.get("provenance", ""),
        "direction": direction,
    }


def define(term: str, max_results: int = 8) -> list[dict]:
    """Look `term` up in BOTH directions (English->Hausa and Hausa->English),
    case- and diacritic-insensitive.

    Returns a list of dicts:
      {"headword", "translation", "context", "provenance", "direction"}
    where direction is "en->ha" or "ha->en".

    Exact (folded) matches come first; if there are none in either direction,
    falls back to a startswith match. Result is capped at max_results. Returns
    [] for unknown terms or when the dictionary is unavailable — never raises.
    """
    _ensure_loaded()
    if not _READY or not isinstance(term, str):
        return []
    key = _fold(term)
    if not key:
        return []

    results: list[dict] = []
    seen: set[tuple] = set()

    def _collect(entries: list[dict], direction: str) -> None:
        for entry in entries:
            result = _make_result(entry, direction)
            fingerprint = (
                result["headword"],
                result["translation"],
                result["context"],
                result["provenance"],
                result["direction"],
            )
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            results.append(result)

    # Exact matches: English first, then Hausa.
    _collect(_EN_INDEX.get(key, []), "en->ha")
    _collect(_HA_INDEX.get(key, []), "ha->en")

    # Fall back to prefix matches only when nothing matched exactly.
    if not results:
        for index_key in sorted(_EN_INDEX):
            if index_key.startswith(key):
                _collect(_EN_INDEX[index_key], "en->ha")
        for index_key in sorted(_HA_INDEX):
            if index_key.startswith(key):
                _collect(_HA_INDEX[index_key], "ha->en")

    return results[:max_results]


def _reset_for_tests() -> None:
    """Reset the singleton so tests can point at a fresh fixture. Not part of
    the public API."""
    global _LOADED, _READY
    with _LOCK:
        _LOADED = False
        _READY = False
        _EN_INDEX.clear()
        _HA_INDEX.clear()
