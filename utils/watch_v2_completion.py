"""Poll the Modal volume for v2 training completion or a genuine stall.

Uses Python's datetime (reliable cross-platform) instead of shell `date -d`,
which mis-parsed "Central Daylight Time" timestamps and produced a false
221-minute stall reading on 2026-07-05.

Prints one line per check; a match on "V2 COMPLETE" or "STALL" is the signal
to act on. Exits 0 on completion.
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

MODAL = str(__import__("pathlib").Path(__file__).resolve().parent.parent / ".venv/Scripts/modal.exe")
VOLUME = "hausa-ai-checkpoints"
PREFIX = "piper_hausa_waxal"
GRACE_SECONDS = 30 * 60
STALL_THRESHOLD_SECONDS = 60 * 60
POLL_SECONDS = 15 * 60

BASELINE_ONNX_PREFIX = "2026-07-04"  # pre-v2 export; anything newer = complete


def parse_ts(s: str) -> float:
    # e.g. "2026-07-05 18:20 Central Daylight Time" -> treat as naive local time
    s = s.replace(" Central Daylight Time", "").replace(" Central Standard Time", "")
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=timezone.utc).timestamp()  # consistent unit; only deltas matter


def main():
    start = time.time()
    while True:
        try:
            out = subprocess.run(
                [MODAL, "volume", "ls", VOLUME, PREFIX, "--json"],
                capture_output=True, text=True, timeout=90,
            )
            entries = json.loads(out.stdout)
        except Exception as e:  # noqa: BLE001
            print(f"[watch] could not read volume listing: {e}")
            time.sleep(POLL_SECONDS)
            continue

        onnx_ts = next((e["Created/Modified"] for e in entries if e["Filename"].endswith("model.onnx")), None)
        bak_ts = next((e["Created/Modified"] for e in entries if e["Filename"].endswith("latest_backup.ckpt")), None)

        if onnx_ts and BASELINE_ONNX_PREFIX not in onnx_ts:
            print(f"V2 COMPLETE: model.onnx re-exported at {onnx_ts}")
            sys.exit(0)

        if bak_ts:
            age = time.time() - parse_ts(bak_ts)
            elapsed = time.time() - start
            if elapsed > GRACE_SECONDS and age > STALL_THRESHOLD_SECONDS:
                print(f"STALL: latest_backup.ckpt is {age/60:.0f} min old (last sync: {bak_ts})")
            else:
                print(f"[watch] healthy — backup {age/60:.0f} min old (last sync: {bak_ts})")
        else:
            print("[watch] could not find latest_backup.ckpt in listing")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
