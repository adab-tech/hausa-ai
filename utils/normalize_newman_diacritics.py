"""
Normalize the two real phonetic diacritics in the Newman 1977 transcription
to one consistent Unicode representation each.

Background: the dictionary's own "GUIDE TO THE USE OF THE DICTIONARY" (PDF
page index 10) documents two marks not in standard Hausa orthography:
  (1) a cedilla under a vowel = short vowel (vs. unmarked = long)
  (2) a tilde over 'r' = trilled/rolled r (vs. unmarked = flap)
Both are real, deliberate, and were faithfully transcribed -- verified by
rendering the source PDF pages directly and reading the guide. The bug is
that different transcription batches (4 parallel chunks) approximated the
same two marks with DIFFERENT Unicode characters, since neither mark has a
clean precomposed form for all five vowels:
  - short vowel: precomposed ogonek (ą, ę) in some entries, precomposed
    dot-below (ạ, ẹ, ị, ọ, ụ) in others -- 480 entries combined.
  - trilled r: precomposed caron (ř) in some entries, base 'r' + combining
    tilde (U+0303) in others -- 331 entries combined.
This normalizes everything to: base vowel + combining cedilla (U+0327) for
the short-vowel mark, and 'r' + combining tilde (U+0303) for the trilled-r
mark (the majority existing choice, and what the guide's own wording --
"a tilde over the letter r" -- literally describes).

Run: python utils/normalize_newman_diacritics.py
"""

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

_DIR = Path(__file__).resolve().parent.parent / "data" / "processed" / "newman_1977"
_SOURCES = [
    "ha_en_pairs.jsonl",
    "ha_en_pairs_chunk1.jsonl",
    "ha_en_pairs_chunk2.jsonl",
    "ha_en_pairs_chunk3.jsonl",
    "ha_en_pairs_chunk4.jsonl",
]

_CEDILLA = "̧"
_TILDE = "̃"

# precomposed ogonek vowel -> base vowel (+ cedilla applied after)
_OGONEK_TO_BASE = {"ą": "a", "ę": "e", "į": "i", "ǫ": "o", "ų": "u",
                   "Ą": "A", "Ę": "E", "Į": "I", "Ǫ": "O", "Ų": "U"}
# precomposed dot-below vowel -> base vowel
_DOTBELOW_TO_BASE = {"ạ": "a", "ẹ": "e", "ị": "i", "ọ": "o", "ụ": "u",
                     "Ạ": "A", "Ẹ": "E", "Ị": "I", "Ọ": "O", "Ụ": "U"}


def normalize(text: str) -> str:
    out = []
    for ch in text:
        if ch in _OGONEK_TO_BASE:
            out.append(_OGONEK_TO_BASE[ch] + _CEDILLA)
        elif ch in _DOTBELOW_TO_BASE:
            out.append(_DOTBELOW_TO_BASE[ch] + _CEDILLA)
        elif ch == "ř":
            out.append("r" + _TILDE)
        elif ch == "Ř":
            out.append("R" + _TILDE)
        else:
            out.append(ch)
    return "".join(out)


def main() -> int:
    changed_total = 0
    for fname in _SOURCES:
        path = _DIR / fname
        rows = []
        changed = 0
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                new_ha = normalize(rec.get("target_ha", ""))
                new_ctx = normalize(rec.get("context", ""))
                if new_ha != rec.get("target_ha", "") or new_ctx != rec.get("context", ""):
                    changed += 1
                rec["target_ha"] = new_ha
                rec["context"] = new_ctx
                rows.append(rec)
        with path.open("w", encoding="utf-8") as f:
            for rec in rows:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[ok] {fname}: {changed}/{len(rows)} rows normalized")
        changed_total += changed
    print(f"[ok] {changed_total} total rows changed across {len(_SOURCES)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
