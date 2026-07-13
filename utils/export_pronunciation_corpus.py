"""
Export approved pronunciation corrections as a (text, audio) training corpus.

Closes the human-in-the-loop loop: reviewer recordings that fix the voice today
also become ground-truth training data, so the NEXT WAXAL/VITS retrain learns
the correct articulation and the runtime override eventually isn't needed.
Pairs with the tone-channel retrain milestone.

Output (LJSpeech-style, easy to fold into the existing training pipeline):
  data/processed/pronunciation_corpus/
    wavs/<id>.wav            24 kHz mono PCM-16
    metadata.csv             <id>|<text>|<speaker_id>

Run:  python utils/export_pronunciation_corpus.py
"""

import csv
import sys
import wave
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "backend"))

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Hausa hooked letters on Windows
except (AttributeError, ValueError):
    pass

_OUT = _REPO / "data" / "processed" / "pronunciation_corpus"
_WAVS = _OUT / "wavs"
_SAMPLE_RATE = 24000


def _write_wav(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_SAMPLE_RATE)
        w.writeframes(pcm)


def main() -> int:
    import pronunciation_store as store
    rows = store.export_approved()
    if not rows:
        print("[info] no approved corrections to export yet.")
        return 0

    _WAVS.mkdir(parents=True, exist_ok=True)
    meta_path = _OUT / "metadata.csv"
    with meta_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="|")
        for r in rows:
            wav_path = _WAVS / f"{r['id']}.wav"
            _write_wav(wav_path, r["audio"])
            writer.writerow([r["id"], r["text"], r["speaker_id"] if r["speaker_id"] is not None else ""])

    print(f"[ok] exported {len(rows)} approved corrections")
    print(f"[ok] wavs -> {_WAVS}")
    print(f"[ok] metadata -> {meta_path}")
    print("Fold these into the WAXAL training filelist for the next retrain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
