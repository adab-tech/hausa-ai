"""
Merge the Newman 1977 dictionary transcription chunks into one corpus file.

Source: 5 JSONL files under data/processed/newman_1977/ (the page-16 proof
batch + 4 parallel-agent chunks covering the rest of the A-Z dictionary body,
pages 16-156 — see data/sources/newman-dictionary/ATTRIBUTION.md for the full
transcription methodology and provenance).

This script:
  1. Concatenates all ha_en_pairs*.jsonl files.
  2. Drops exact-duplicate (target_ha, source_en, context) rows — chunk
     boundaries occasionally produced a page re-transcribed by two agents.
  3. Validates every row against the dictionary_service schema (non-empty
     source_en/target_ha, provenance == "newman_1977").
  4. Writes the deduped result to ha_en_pairs_merged.jsonl and prints a
     summary (row count, page coverage, any validation failures).

Run: python utils/merge_newman_1977.py
"""

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

_DIR = Path(__file__).resolve().parent.parent / "data" / "processed" / "newman_1977"
_OUT = _DIR / "ha_en_pairs_merged.jsonl"
_SOURCES = [
    "ha_en_pairs.jsonl",
    "ha_en_pairs_chunk1.jsonl",
    "ha_en_pairs_chunk2.jsonl",
    "ha_en_pairs_chunk3.jsonl",
    "ha_en_pairs_chunk4.jsonl",
]


def merge() -> int:
    seen: set[tuple[str, str, str]] = set()
    rows: list[dict] = []
    bad = 0
    dupes = 0

    for fname in _SOURCES:
        path = _DIR / fname
        if not path.is_file():
            print(f"[error] missing source: {path}")
            return 1
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    bad += 1
                    continue
                source_en = (rec.get("source_en") or "").strip()
                target_ha = (rec.get("target_ha") or "").strip()
                if not source_en or not target_ha:
                    bad += 1
                    continue
                if rec.get("provenance") != "newman_1977":
                    bad += 1
                    continue
                key = (target_ha, source_en, rec.get("context", ""))
                if key in seen:
                    dupes += 1
                    continue
                seen.add(key)
                out_row = {
                    "source_en": source_en,
                    "target_ha": target_ha,
                    "context": rec.get("context", ""),
                    "provenance": "newman_1977",
                }
                # Optional audit-trail field: carries forward a reviewer's note
                # (e.g. "printed as X but semantically questionable") without
                # altering the transcribed value itself. Not read by
                # dictionary_service — bookkeeping only.
                note = rec.get("note")
                if note:
                    out_row["note"] = note
                rows.append(out_row)

    pages = sorted({r for r in (json.loads(l).get("page") for l in
                                 (line for fname in _SOURCES
                                  for line in (_DIR / fname).open(encoding="utf-8"))
                                 if l.strip())
                     if r is not None})

    with _OUT.open("w", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"[ok] {len(rows)} merged entries -> {_OUT}")
    print(f"[ok] {dupes} exact duplicates dropped, {bad} invalid rows dropped")
    print(f"[ok] page range: {min(pages)}-{max(pages)} ({len(pages)} distinct pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(merge())
