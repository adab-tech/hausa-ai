"""
Build a clean HAUSA->ENGLISH lexicon from openly-licensed Wiktionary data.

Source: Kaikki.org machine-readable extraction of English Wiktionary's Hausa
entries (https://kaikki.org/dictionary/Hausa/). Wiktionary text is licensed
**CC-BY-SA 4.0** (+ GFDL) — free to reuse and redistribute with attribution and
share-alike. See data/sources/wiktionary-hausa/ATTRIBUTION.md.

Why this exists — the shipped lexicon (Robinson 1914) is public-domain and clean
in the ENGLISH->Hausa direction, but its reverse (HA->EN) lookup is rough. This
source is natively Hausa-headword -> English gloss, so it gives Murya a clean
HA->EN direction WITHOUT touching any copyrighted dictionary (Newman etc. remain
unlicensed / not ingested — see data/sources/newman-dictionary/ATTRIBUTION.md).

Output — one JSON object per line, matching backend/services/dictionary_service
schema so it drops straight into the existing loader:
  {"source_en": <english gloss>, "target_ha": <hausa headword>,
   "context": "<pos>", "provenance": "wiktionary_ha_ccbysa"}

Run:  python utils/build_hausa_en_open.py
"""

import json
import sys
from pathlib import Path

# Keep Hausa hooked letters (ƙ ɗ ɓ ƴ) from crashing a cp1252 Windows console.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "data" / "sources" / "wiktionary-hausa" / "kaikki-Hausa.jsonl"
_OUT_DIR = _REPO_ROOT / "data" / "processed" / "hausa_en_open"
_OUT = _OUT_DIR / "ha_en_pairs.jsonl"
_PROVENANCE = "wiktionary_ha_ccbysa"

# Skip glosses that are pure form-references, not real translations
# (Wiktionary "inflection of…", "plural of…", "alternative form of…" lines).
_FORM_REF_MARKERS = (
    "inflection of", "plural of", "singular of", "alternative form of",
    "alternative spelling of", "obsolete form of", "misspelling of",
    "romanization of", "feminine of", "masculine of",
)


def _clean_gloss(gloss: str) -> str:
    return " ".join((gloss or "").split()).strip()


def _is_form_ref(gloss: str) -> bool:
    low = gloss.lower()
    return any(low.startswith(m) or m in low for m in _FORM_REF_MARKERS)


def build() -> int:
    if not _SRC.is_file():
        print(f"[error] source not found: {_SRC}")
        print("        download it first:")
        print("        curl -sS https://kaikki.org/dictionary/Hausa/"
              "kaikki.org-dictionary-Hausa.jsonl -o " + str(_SRC))
        return 1

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    seen: set[tuple[str, str]] = set()
    rows_out = 0
    words_in = 0
    dropped_forms = 0

    with _SRC.open(encoding="utf-8") as fh, _OUT.open("w", encoding="utf-8") as out:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            word = (rec.get("word") or "").strip()
            if not word or rec.get("lang_code") not in (None, "ha"):
                # kaikki Hausa file is all Hausa, but stay defensive.
                pass
            if not word:
                continue
            words_in += 1
            pos = (rec.get("pos") or "").strip()
            for sense in rec.get("senses", []):
                for gloss in sense.get("glosses", []) or []:
                    g = _clean_gloss(gloss)
                    if not g:
                        continue
                    if _is_form_ref(g):
                        dropped_forms += 1
                        continue
                    # Skip self-references (gloss == headword, e.g. "sura->sura"):
                    # Wiktionary sometimes glosses a borrowing with its own form.
                    if g.strip().lower() == word.strip().lower():
                        dropped_forms += 1
                        continue
                    key = (word, g)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.write(json.dumps({
                        "source_en": g,
                        "target_ha": word,
                        "context": pos,
                        "provenance": _PROVENANCE,
                    }, ensure_ascii=False) + "\n")
                    rows_out += 1

    print(f"[ok] {words_in} Hausa headwords -> {rows_out} HA->EN pairs "
          f"({dropped_forms} form-reference glosses skipped)")
    print(f"[ok] wrote {_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
