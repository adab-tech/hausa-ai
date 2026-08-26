"""
Publish the local Piper Hausa TTS model to adab-tech/murya-piper-hausa-tts on HF.

Run this after a retrain has been validated locally (native-speaker audition
per the model card's "Evaluation" section) — this script does not validate
audio quality itself, it just pushes files.

Requires HF_TOKEN in the environment (a write-scoped token; never hardcode it
here or commit it). Get one at https://huggingface.co/settings/tokens.

Run: python publish_tts_model_to_hf.py [--dry-run] [--commit-message "..."]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODEL_DIR = BASE / "models" / "piper_hausa_waxal"
REPO_ID = "adab-tech/murya-piper-hausa-tts"

FILES_TO_PUBLISH = ["model.onnx", "model.onnx.json"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate files and print the plan, but don't upload."
    )
    parser.add_argument(
        "--commit-message", default="Update TTS model", help="HF commit message for this push."
    )
    args = parser.parse_args()

    missing = [f for f in FILES_TO_PUBLISH if not (MODEL_DIR / f).exists()]
    if missing:
        print(f"Missing local model files in {MODEL_DIR}: {missing}")
        sys.exit(1)

    for f in FILES_TO_PUBLISH:
        size_mb = (MODEL_DIR / f).stat().st_size / 1_048_576
        print(f"  {f}  ({size_mb:.1f} MB)")

    if args.dry_run:
        print(f"\n[dry run] would push the above to {REPO_ID}")
        return

    token = os.getenv("HF_TOKEN")
    if not token:
        print("HF_TOKEN not set. Get a write-scoped token from "
              "https://huggingface.co/settings/tokens and set it as an env var.")
        sys.exit(1)

    from huggingface_hub import HfApi

    api = HfApi(token=token)
    for f in FILES_TO_PUBLISH:
        api.upload_file(
            path_or_fileobj=str(MODEL_DIR / f),
            path_in_repo=f,
            repo_id=REPO_ID,
            repo_type="model",
            commit_message=args.commit_message,
        )
        print(f"Pushed {f} -> {REPO_ID}")

    print(f"\nDone: https://huggingface.co/{REPO_ID}")


if __name__ == "__main__":
    main()
