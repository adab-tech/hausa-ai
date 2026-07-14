"""
Build a Hausa instruction fine-tuning dataset — the FREE, safe first step of
Milestone #1 (a native Hausa LLM). No training here, no compute cost: this only
turns licence-clean lexical sources into instruction/response pairs, each row
carrying its provenance and licence.

Sources (licence-checked — the serious-research standard forbids scraped
copyrighted text; Newman etc. are NOT used):
  * Robinson (1914) EN->HA — PUBLIC DOMAIN
    data/processed/robinson/en_ha_pairs.jsonl  {source_en, target_ha}
  * Wiktionary HA->EN via Kaikki — CC-BY-SA 4.0
    data/processed/hausa_en_open/ha_en_pairs.jsonl  {source_en(gloss), target_ha(word)}

Instructions are phrased IN HAUSA so the model learns Hausa instruction-following,
not just English. Output (Alpaca-style, convertible to chat):
  {"instruction", "input", "output", "source", "license"}

Run:  python utils/build_hausa_instruction_dataset.py
Later: add licence-checked open Hausa corpora (Hausa Wikipedia CC-BY-SA, OSCAR
slice, native-written prompts) as extra rows — see the TODO at the bottom.
"""

import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

_REPO = Path(__file__).resolve().parent.parent
_ROBINSON = _REPO / "data" / "processed" / "robinson" / "en_ha_pairs.jsonl"
_WIKTIONARY = _REPO / "data" / "processed" / "hausa_en_open" / "ha_en_pairs.jsonl"
_OUT_DIR = _REPO / "data" / "processed" / "hausa_instruction"
_OUT = _OUT_DIR / "instructions.jsonl"
_MANIFEST = _OUT_DIR / "manifest.json"

# OCR/grammar-tag artifacts to skip (mirrors dictionary_service._is_noise).
_NOISE = {
    "tr", "intr", "v", "n", "adj", "adv", "pl", "sing", "etc", "see", "cf",
    "conj", "prep", "pron", "int", "interj", "vol", "fig", "lit", "abbr",
    "id", "ibid", "eg", "ie", "esp", "usu", "var", "dial",
}


def _clean(s: str) -> str:
    return " ".join((s or "").split()).strip()


def _is_noise(v: str) -> bool:
    v = (v or "").strip().strip(".").lower()
    return (not v) or (v in _NOISE) or (len(v) == 1 and v.isalpha()) or bool(re.fullmatch(r"[\W_]+", v))


def _emit(rows, instruction, output, source, license_):
    instruction, output = _clean(instruction), _clean(output)
    if instruction and output:
        rows.append({"instruction": instruction, "input": "", "output": output,
                     "source": source, "license": license_})


def build() -> int:
    rows: list[dict] = []
    seen: set[tuple] = set()
    stats = {"robinson_en_ha": 0, "wiktionary_ha_en": 0}

    # Robinson EN->HA (public domain): translate + how-to-say tasks.
    if _ROBINSON.is_file():
        for line in _ROBINSON.open(encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            en, ha = _clean(r.get("source_en", "")), _clean(r.get("target_ha", ""))
            if _is_noise(en) or _is_noise(ha):
                continue
            key = ("r", en.lower(), ha.lower())
            if key in seen:
                continue
            seen.add(key)
            _emit(rows, f"Fassara wannan kalma ta Turanci zuwa Hausa: {en}", ha,
                  "robinson_1914_vol2", "public-domain")
            _emit(rows, f"Yaya ake cewa '{en}' da harshen Hausa?", ha,
                  "robinson_1914_vol2", "public-domain")
            stats["robinson_en_ha"] += 1

    # Wiktionary HA->EN (CC-BY-SA): translate-to-English + define-in-English.
    if _WIKTIONARY.is_file():
        for line in _WIKTIONARY.open(encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            gloss, word = _clean(r.get("source_en", "")), _clean(r.get("target_ha", ""))
            if _is_noise(gloss) or _is_noise(word):
                continue
            key = ("w", word.lower(), gloss.lower())
            if key in seen:
                continue
            seen.add(key)
            _emit(rows, f"Menene ma'anar kalmar Hausa '{word}' a Turanci?", gloss,
                  "wiktionary_ha_ccbysa", "CC-BY-SA-4.0")
            _emit(rows, f"Fassara wannan kalma ta Hausa zuwa Turanci: {word}", gloss,
                  "wiktionary_ha_ccbysa", "CC-BY-SA-4.0")
            stats["wiktionary_ha_en"] += 1

    # Community Q&A (native-written, owner-approved) — the highest-value source.
    # Drop the admin "Fitar da Koyo" export here as community_qa.jsonl to include it.
    community = _OUT_DIR / "community_qa.jsonl"
    if community.is_file():
        for line in community.open(encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            instr, out = _clean(r.get("instruction", "")), _clean(r.get("output", ""))
            if instr and out:
                rows.append({"instruction": instr, "input": _clean(r.get("input", "")),
                             "output": out, "source": "community_qa",
                             "license": r.get("license", "owner-approved-contribution")})
        stats["community_qa"] = sum(1 for x in rows if x["source"] == "community_qa")

    if not rows:
        print("[error] no source lexicons found — run the dictionary builders first.")
        return 1

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    with _OUT.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "total_examples": len(rows),
        "unique_source_entries": stats,
        "sources": [
            {"name": "Robinson 1914 Vol.II (EN->HA)", "license": "public-domain",
             "tag": "robinson_1914_vol2"},
            {"name": "Wiktionary Hausa via Kaikki (HA->EN)", "license": "CC-BY-SA-4.0",
             "tag": "wiktionary_ha_ccbysa"},
        ],
        "format": "alpaca: {instruction, input, output, source, license}",
        "note": "Instruction-tuning seed for the native Hausa LLM (Milestone #1). "
                "Licence-clean only; no copyrighted (e.g. Newman) text. Extend with "
                "licence-checked open Hausa corpora before training.",
    }
    _MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] {len(rows)} instruction examples -> {_OUT}")
    print(f"[ok] source entries: {stats}")
    print(f"[ok] manifest -> {_MANIFEST}")
    return 0


# TODO (next, before training): add licence-checked open Hausa corpora as extra
# rows — Hausa Wikipedia (CC-BY-SA), an OSCAR/CC Hausa slice, Tatoeba HA, and
# (highest value) native-speaker-written instruction/answer pairs. Keep the
# per-row source+license fields so the training mix is fully auditable.

if __name__ == "__main__":
    raise SystemExit(build())
