"""
Parse Robinson (1914) English–Hausa dictionary DJVU text into JSONL for ML and web lookup.

Source: Internet Archive item dictionaryofhaus02robiuoft
  https://archive.org/details/dictionaryofhaus02robiuoft
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SOURCE_DIR = BASE / "data" / "sources" / "robinson-dictionary"
DJVU_TXT = SOURCE_DIR / "dictionaryofhaus02robiuoft_djvu.txt"
OUT_JSONL = SOURCE_DIR / "robinson_en_ha.jsonl"
OUT_INDEX = SOURCE_DIR / "robinson_en_ha_index.json"

# Headword line: "abandon, tr. v." or "ache, n." or standalone "ache" before defs
ENTRY_RE = re.compile(
    r"^([A-Za-z][A-Za-z'\-]{1,48})(?:,\s*(.*))?$"
)
SKIP_PREFIXES = (
    "DICTIONARY",
    "VOLUME",
    "CHARLES",
    "ABBREVIATIONS",
    "Digitized",
    "http",
    "Cambridge",
    "June,",
)


def is_noise_line(line: str) -> bool:
    s = line.strip()
    if not s or len(s) < 2:
        return True
    if any(s.startswith(p) for p in SKIP_PREFIXES):
        return True
    if re.match(r"^\d+[\-\—]?\d*$", s):
        return True
    if re.match(r"^[=\.\s]+$", s):
        return True
    return False


def normalize_headword(word: str) -> str:
    return word.strip().lower()


def parse_entries(text: str) -> list[dict]:
    lines = text.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if re.match(r"^abandon,\s", line.strip(), re.I):
            start = i
            break

    entries: list[dict] = []
    current_head: str | None = None
    current_pos: str = ""
    buffer: list[str] = []

    def flush():
        nonlocal current_head, buffer, current_pos
        if not current_head or not buffer:
            buffer = []
            return
        body = " ".join(buffer)
        body = re.sub(r"\s+", " ", body).strip()
        if len(body) < 3:
            buffer = []
            return
        entries.append(
            {
                "en": current_head,
                "pos": current_pos or None,
                "gloss": body,
                "source": "robinson_1914_vol2",
            }
        )
        buffer = []

    for line in lines[start:]:
        raw = line.strip()
        if is_noise_line(raw):
            continue

        m = ENTRY_RE.match(raw)
        # New headword: short line, mostly letters, optional comma tail
        if m and ("," in raw or len(raw) < 55):
            head = normalize_headword(m.group(1))
            tail = (m.group(2) or "").strip()
            # Avoid false positives like "see" alone
            if head in {"see", "e", "g", "pi", "cf", "etc", "adv", "adj", "n", "v"}:
                if buffer:
                    buffer.append(raw)
                continue
            flush()
            current_head = head
            current_pos = tail
            if tail and not tail.startswith("see"):
                buffer.append(tail)
            continue

        if current_head:
            buffer.append(raw)

    flush()
    return entries


def build_search_index(entries: list[dict]) -> list[dict]:
    """Compact list for static web: en + gloss truncated."""
    index = []
    for e in entries:
        gloss = e["gloss"][:500]
        index.append({"en": e["en"], "g": gloss, "p": e.get("pos")})
    return index


def main() -> None:
    if not DJVU_TXT.exists():
        print(f"Missing {DJVU_TXT}. Download DJVU text from Archive.org first.")
        sys.exit(1)

    text = DJVU_TXT.read_text(encoding="utf-8", errors="replace")
    entries = parse_entries(text)
    print(f"Parsed {len(entries)} entries from Robinson Vol. II")

    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    index = build_search_index(entries)
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT_JSONL}")
    print(f"Wrote {OUT_INDEX} ({OUT_INDEX.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
