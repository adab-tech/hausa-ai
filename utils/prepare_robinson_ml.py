"""
Export Robinson dictionary JSONL into ML-friendly translation / lexicon datasets.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "data" / "sources" / "robinson-dictionary" / "robinson_en_ha.jsonl"
OUT_DIR = BASE / "data" / "processed" / "robinson"

# Rough Hausa token heuristic (hooked letters, common endings)
HAUSA_TOKEN = re.compile(r"\b[\wɓɗƙʼ\-]{2,}\b", re.UNICODE)
EN_STOP = {"see", "e", "g", "pi", "cf", "tr", "adj", "adv", "n", "v", "with", "the", "and", "or"}


def extract_hausa_candidates(gloss: str) -> list[str]:
    tokens = HAUSA_TOKEN.findall(gloss.lower())
    out = []
    for t in tokens:
        if t in EN_STOP or t.isdigit():
            continue
        if any(c in t for c in "ɓɗƙʼ") or t.endswith(("wa", "shi", "ce", "da", "na", "ka")):
            out.append(t)
        elif len(t) >= 3 and not t.endswith(("ing", "tion", "ness", "ment")):
            out.append(t)
    # dedupe preserve order
    seen = set()
    uniq = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq[:12]


def main() -> None:
    if not SRC.exists():
        print(f"Run extract_robinson_dictionary.py first. Missing {SRC}")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pairs_path = OUT_DIR / "en_ha_pairs.jsonl"
    lexicon_path = OUT_DIR / "lexicon_manifest.json"

    pair_count = 0
    with SRC.open(encoding="utf-8") as fin, pairs_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            row = json.loads(line)
            en = row["en"]
            gloss = row["gloss"]
            hausa = extract_hausa_candidates(gloss)
            if not hausa:
                continue
            for h in hausa[:3]:
                fout.write(
                    json.dumps(
                        {
                            "source_en": en,
                            "target_ha": h,
                            "context": gloss[:400],
                            "provenance": "robinson_1914_vol2",
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                pair_count += 1

    manifest = {
        "source": "robinson_1914_vol2",
        "pairs_file": str(pairs_path.relative_to(BASE)),
        "pair_count": pair_count,
        "attribution": "data/sources/robinson-dictionary/ATTRIBUTION.md",
        "suggested_use": ["translation fine-tuning", "lexical retrieval", "Hausa embedding warm-start"],
    }
    lexicon_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {pair_count} pair rows to {pairs_path}")
    print(f"Manifest: {lexicon_path}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
