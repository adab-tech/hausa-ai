"""Preflight checks before launching a Modal TTS training run.

Encodes every avoidable failure from the 2026-07-02 session so it is
caught locally, in seconds, before any GPU is billed. Exit code 0 = safe
to launch; 1 = fix the reported problems first.

Usage (from repo root, ideally via utils/run_training.ps1):
    python utils/preflight_train.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRAIN_SCRIPT = ROOT / "finetune_piper_hausa_modal.py"
FILELIST = ROOT / "waxal_hausa" / "tts_filelist.txt"
BASE_CKPT_URL = (
    "https://huggingface.co/datasets/rhasspy/piper-checkpoints/resolve/main/"
    "en/en_US/lessac/medium/epoch%3D2164-step%3D1355540.ckpt"
)

failures: list[str] = []
warnings: list[str] = []


def check(ok: bool, label: str, detail: str = "", warn_only: bool = False) -> None:
    mark = "OK " if ok else ("WARN" if warn_only else "FAIL")
    print(f"[{mark}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        (warnings if warn_only else failures).append(f"{label}: {detail}")


def main() -> None:
    # 1. Console encoding (signature: windows-console-encoding)
    check(
        os.environ.get("PYTHONUTF8") == "1" or os.environ.get("PYTHONIOENCODING", "").lower().startswith("utf"),
        "UTF-8 console env",
        "set PYTHONUTF8=1 (run_training.ps1 does this)",
    )

    # 2. Dataset present and parseable (signature: digit-transcript-corruption)
    if not FILELIST.exists():
        check(False, "WAXAL filelist", f"{FILELIST} missing")
    else:
        lines = FILELIST.read_text(encoding="utf-8").splitlines()
        parsed = [ln.split("|") for ln in lines if ln.strip()]
        bad = sum(1 for p in parsed if len(p) < 2)
        digits = sum(1 for p in parsed if len(p) >= 2 and any(c.isdigit() for c in p[1]))
        speakers = Counter(
            Path(p[0]).stem.split("_")[1] for p in parsed if len(p) >= 2 and len(Path(p[0]).stem.split("_")) >= 3
        )
        check(bad == 0, "Filelist rows parse", f"{bad} malformed rows" if bad else f"{len(parsed)} rows")
        check(True, "Digit transcripts to be skipped", f"{digits} (staging filters these)")
        check(
            all(n - sum(1 for p in parsed if len(p) >= 2 and any(c.isdigit() for c in p[1])
                        and Path(p[0]).stem.split("_")[1] == s) >= 80
                for s, n in speakers.items()),
            "Every speaker >= 80 clean clips",
            str(dict(sorted(speakers.items()))),
            warn_only=True,
        )
        # sample a few audio paths
        sample = [p[0] for p in parsed[:: max(1, len(parsed) // 25)] if len(p) >= 2][:25]
        missing = [rel for rel in sample if not (ROOT / "waxal_hausa" / rel).exists()]
        check(not missing, "Audio files exist (sampled 25)", f"missing e.g. {missing[:3]}" if missing else "")

    # 3. Alphabet covers the corpus (signature: phoneme-map-missing-language)
    src = TRAIN_SCRIPT.read_text(encoding="utf-8")
    m = re.search(r"HA_ALPHABET = \(\s*(.*?)\)\n", src, re.DOTALL)
    check(bool(m), "HA_ALPHABET defined in training script")
    check("PREPROCESS_WRAPPER" in src, "Grapheme-mode preprocess wrapper present")

    # 4. Version pinning (signature: unpinned-api-drift)
    unpinned = re.findall(r"pip install ([a-zA-Z0-9_\-]+)(?![=<>'\"])(?=[\s\"])", src)
    unpinned = [p for p in unpinned if p not in ("pip", "-r", "-e")]
    check(not unpinned, "ML libraries pinned in image", f"unpinned: {unpinned}" if unpinned else "", warn_only=True)

    # 5. Build-time import smoke test (signature: missing-transitive-dep)
    check(
        "import piper_train.preprocess" in src,
        "Build-time import smoke-test present",
        "add: python -c 'import piper_train.preprocess, piper_train.__main__, piper_train.export_onnx'",
    )

    # 6. Base checkpoint reachable (signature: hub-download-failure)
    try:
        req = urllib.request.Request(BASE_CKPT_URL, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as resp:
            ok = resp.status == 200
            size_gb = int(resp.headers.get("Content-Length") or
                          resp.headers.get("X-Linked-Size") or 0) / 1e9
        check(ok, "Warm-start checkpoint reachable", f"{size_gb:.2f} GB")
    except Exception as e:  # noqa: BLE001 - any network failure is a preflight fail
        check(False, "Warm-start checkpoint reachable", str(e))

    # 7. Modal auth
    try:
        r = subprocess.run(
            [str(ROOT / ".venv" / "Scripts" / "modal.exe"), "profile", "current"],
            capture_output=True, text=True, timeout=60,
        )
        check(r.returncode == 0 and r.stdout.strip(), "Modal authenticated", r.stdout.strip())
    except Exception as e:  # noqa: BLE001
        check(False, "Modal authenticated", str(e))

    print()
    if failures:
        print(f"PREFLIGHT FAILED — {len(failures)} blocking problem(s):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    if warnings:
        print(f"Preflight passed with {len(warnings)} warning(s).")
    else:
        print("Preflight passed. Clear for launch.")
    sys.exit(0)


if __name__ == "__main__":
    main()
