"""Match a failed training log against known failure signatures.

Usage:
    python utils/diagnose_run.py <logfile> [logfile2 ...]
    python utils/diagnose_run.py --history logs/modal_runs/

Prints matched signatures with diagnosis + fix. With --history and a
directory, summarizes failure frequency across all logs — useful for
spotting recurring classes worth new prevention steps.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

SIGNATURES = json.loads(
    (Path(__file__).parent / "failure_signatures.json").read_text(encoding="utf-8")
)["signatures"]


def diagnose(text: str) -> list[dict]:
    hits = []
    for sig in SIGNATURES:
        if sig["pattern"].startswith("SILENT"):
            continue
        if re.search(sig["pattern"], text):
            hits.append(sig)
    return hits


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    history_mode = "--history" in args
    paths = []
    for a in args:
        if a == "--history":
            continue
        p = Path(a)
        paths.extend(sorted(p.glob("*.log")) + sorted(p.glob("*.output")) if p.is_dir() else [p])

    freq: Counter = Counter()
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"!! {path}: {e}")
            continue
        hits = diagnose(text)
        if not history_mode:
            print(f"\n=== {path.name} ===")
            if not hits:
                print("  No known signature matched. Read the traceback manually;")
                print("  if it's a new class, add it to utils/failure_signatures.json.")
            for sig in hits:
                print(f"  [{sig['id']}]")
                print(f"    diagnosis:  {sig['diagnosis']}")
                print(f"    fix:        {sig['fix']}")
        freq.update(sig["id"] for sig in hits)

    if history_mode:
        print("Failure class frequency across", len(paths), "logs:")
        for sig_id, n in freq.most_common():
            print(f"  {n:3d}  {sig_id}")
        if not freq:
            print("  (no known signatures matched)")


if __name__ == "__main__":
    main()
