"""
Hausa <-> English dictionary lookup backed by three openly-usable/licensed
lexicons.

Sources (all auto-detected and merged into one index; each entry keeps its own
provenance):
  * Robinson (1914) — public domain — clean ENGLISH->Hausa direction.
    provenance "robinson_1914_vol2".
  * Wiktionary/Kaikki — CC-BY-SA — clean HAUSA->English direction.
    provenance "wiktionary_ha_ccbysa". See
    data/sources/wiktionary-hausa/ATTRIBUTION.md and utils/build_hausa_en_open.py.
  * Newman & Newman (1977) — in copyright, ingestion APPROVED directly by
    Prof. Paul Newman via email — clean HAUSA->English direction (natively
    HA-headword). provenance "newman_1977". Transcribed by page-image reading
    (the PDF's embedded OCR text layer is unreliable — see
    data/sources/newman-dictionary/ATTRIBUTION.md) and merged via
    utils/merge_newman_1977.py. The 2007 Newman edition is not yet ingested.

Purpose — let Murya define/translate words with a CITED source instead of
guessing. Every returned entry carries its provenance so the chat path can say
where a definition came from. Results are ranked so each source answers in the
direction it is authoritative for (clean answers before noisy reverse lookups).

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

# Fixed container location (the image bakes the lexicon here). Deliberately
# OUTSIDE /app/data: that path is the Fly persistent volume's mount point (see
# fly.toml [mounts]), which shadows anything baked into it at build time —
# confirmed live in production (2026-08-22) that dictionary_ready() was False
# because /app/data/robinson/... never existed at runtime, silently replaced
# by the empty/unrelated volume contents. Moved here so the baked-in lexicon
# actually survives past container start.
_CONTAINER_PATH = Path("/app/dictionaries/robinson/en_ha_pairs.jsonl")

# Repo-root fallback, resolved relative to THIS file so it works from any cwd.
# services/dictionary_service.py -> backend/ -> <repo-root>
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_REPO_PATH = _REPO_ROOT / "data" / "processed" / "robinson" / "en_ha_pairs.jsonl"

# Secondary, openly-licensed HAUSA->ENGLISH lexicon (Wiktionary via Kaikki,
# CC-BY-SA — see data/sources/wiktionary-hausa/ATTRIBUTION.md). It gives a clean
# HA->EN direction that Robinson (EN->HA, 1914) lacks. Loaded IN ADDITION to
# Robinson when present; both feed the same indexes, each entry keeping its own
# provenance.
_HA_EN_CONTAINER_PATH = Path("/app/dictionaries/hausa_en_open/ha_en_pairs.jsonl")
_HA_EN_REPO_PATH = _REPO_ROOT / "data" / "processed" / "hausa_en_open" / "ha_en_pairs.jsonl"

# Tertiary HAUSA->ENGLISH lexicon: Newman & Newman (1977), APPROVED directly by
# Prof. Paul Newman (see data/sources/newman-dictionary/ATTRIBUTION.md). Also
# additive — merged into the same indexes alongside Robinson and Wiktionary.
_NEWMAN_1977_CONTAINER_PATH = Path("/app/dictionaries/newman_1977/ha_en_pairs_merged.jsonl")
_NEWMAN_1977_REPO_PATH = _REPO_ROOT / "data" / "processed" / "newman_1977" / "ha_en_pairs_merged.jsonl"

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
    real headword or translation.

    Previously this also blanket-rejected every single alphabetic character,
    on the theory that a lone letter is usually a stray OCR/grammar-tag
    artifact. But that silently dropped real single-letter headwords too --
    e.g. Hausa "a" (a genuine preposition/particle, see LEXICAL_TONES in
    orthography.py) or English "a"/"I" -- so define("a") returned nothing
    even when the source lexicon genuinely defined it. The known
    single-letter grammar tags this was meant to catch (e.g. "v", "n" for
    verb/noun) are already covered by `_ABBREV_NOISE` above, so dropping the
    blanket single-character rule does not let that OCR noise back in."""
    v = value.strip().strip(".").lower()
    return (not v) or (v in _ABBREV_NOISE)


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


def _resolve_ha_en_path() -> Path | None:
    """Resolve the optional open HA->EN lexicon (container path, then repo copy).
    Returns None if neither exists — it is a strictly additive source, so its
    absence never disables the dictionary."""
    for candidate in (_HA_EN_CONTAINER_PATH, _HA_EN_REPO_PATH):
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def _resolve_newman_1977_path() -> Path | None:
    """Resolve the optional Newman 1977 HA->EN lexicon (container path, then
    repo copy). Returns None if neither exists — additive source, absence
    never disables the dictionary."""
    for candidate in (_NEWMAN_1977_CONTAINER_PATH, _NEWMAN_1977_REPO_PATH):
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def _load_file(path: Path) -> int:
    """Read one JSONL lexicon file into the shared indexes; return the number of
    entries indexed. Raises OSError on read failure (caller handles). Malformed
    lines and OCR/grammar-tag artifacts are skipped, not fatal."""
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
    return count


def _load() -> None:
    """Read the lexicon(s) once and build the English and Hausa indexes. Sets
    _READY True if at least one source loaded. Never raises — any failure logs
    at warning and leaves the dictionary unavailable.

    Sources:
      * Primary: Robinson (1914), or the DICTIONARY_PATH override (authoritative
        — when set, ONLY that file is loaded).
      * Secondary (additive, only when no override): the open HA->EN lexicon,
        merged into the same indexes if present.
    """
    global _LOADED, _READY
    _LOADED = True
    _EN_INDEX.clear()
    _HA_INDEX.clear()

    override = bool(os.getenv(_ENV_VAR))
    total = 0
    loaded_any = False

    # Primary source.
    primary = _resolve_path()
    if primary is None:
        logger.warning(
            "Primary dictionary lexicon not found (checked %s, %s, %s).",
            os.getenv(_ENV_VAR) or "<%s unset>" % _ENV_VAR,
            _CONTAINER_PATH,
            _REPO_PATH,
        )
    else:
        try:
            n = _load_file(primary)
            total += n
            loaded_any = True
            logger.info("Dictionary source loaded: %d entries from %s.", n, primary)
        except OSError as exc:
            logger.warning("Failed to read dictionary lexicon %s: %s", primary, exc)

    # Secondary open HA->EN source — additive, skipped when an override pins a
    # single authoritative file.
    if not override:
        ha_en = _resolve_ha_en_path()
        if ha_en is not None:
            try:
                n = _load_file(ha_en)
                total += n
                loaded_any = True
                logger.info("Dictionary source loaded: %d entries from %s.", n, ha_en)
            except OSError as exc:
                logger.warning("Failed to read HA->EN lexicon %s: %s", ha_en, exc)

    # Tertiary Newman 1977 HA->EN source — additive, same override-skip rule.
    if not override:
        newman = _resolve_newman_1977_path()
        if newman is not None:
            try:
                n = _load_file(newman)
                total += n
                loaded_any = True
                logger.info("Dictionary source loaded: %d entries from %s.", n, newman)
            except OSError as exc:
                logger.warning("Failed to read Newman 1977 lexicon %s: %s", newman, exc)

    _READY = loaded_any
    if loaded_any:
        logger.info(
            "Dictionary ready: %d total entries (%d EN keys, %d HA keys).",
            total, len(_EN_INDEX), len(_HA_INDEX),
        )
    else:
        logger.warning("No dictionary sources loaded; lookups disabled.")


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


# Each source is trustworthy in the direction it was compiled for; the reverse
# lookup is noisier. Robinson (1914) is an English->Hausa dictionary, so its
# EN->HA direction is clean and its HA->EN reverse is rough. Wiktionary and
# Newman (1977) are both natively Hausa-headword, so their HA->EN direction is
# clean. Ranking results by "am I being used in my native direction?" floats
# the clean answer to the top (e.g. Hausa "ruwa" -> "water" before Robinson's
# garbled reverse entries).
_NATIVE_DIRECTION = {
    "robinson": "en->ha",
    "wiktionary": "ha->en",
    "newman": "ha->en",
}

# Tiebreak among sources that are equally "in their native direction": prefer
# Newman (1977) first, then Wiktionary — Newman is the more authoritative,
# scholarly source (see data/sources/newman-dictionary/ATTRIBUTION.md), but
# both are clean HA->EN and either beats an unranked/noisy provenance.
_TIEBREAK_ORDER = ("newman", "wiktionary")


def _quality_rank(result: dict) -> tuple[int, int]:
    """Sort key (lower = better). Primary: is the source queried in its
    authoritative direction? 0 = yes (cleanest), 1 = unknown provenance,
    2 = noisier reverse direction. Secondary tiebreak: among clean HA->EN
    sources, prefer Newman then Wiktionary, so a Hausa headword that also
    appears as a garbled Robinson "English" entry still resolves to the
    clean, most-authoritative gloss."""
    provenance = result.get("provenance", "")
    direction = result.get("direction", "")
    tiebreak = next(
        (i for i, marker in enumerate(_TIEBREAK_ORDER) if marker in provenance),
        len(_TIEBREAK_ORDER),
    )
    for marker, native in _NATIVE_DIRECTION.items():
        if marker in provenance:
            return (0 if direction == native else 2, tiebreak)
    return (1, tiebreak)


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

    # Exact matches from both indexes, then rank so each source appears in its
    # authoritative direction first (clean answers before noisy reverse ones).
    _collect(_EN_INDEX.get(key, []), "en->ha")
    _collect(_HA_INDEX.get(key, []), "ha->en")
    results.sort(key=_quality_rank)  # stable: preserves order within a rank

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
