"""Prepare the WAXAL Hausa TTS clips for MMS-TTS fine-tuning.

Reads waxal_hausa/tts_filelist.txt (audio/rel/path.mp3|plain_text|tone_text),
normalizes the plain text to the facebook/mms-tts-hau tokenizer vocabulary,
and writes a HF-datasets parquet file with embedded audio at
data/processed/waxal_mms/train.parquet plus a manifest.

The MMS-hau vocab is lowercase-only, has no punctuation besides ' and -,
no tone marks, and no p/v/q/x. Loanword letters are mapped to their
standard Hausa adaptations (p->f, v->b, q->k, x->s) and 'y-hook is
written as 'y, matching the Boko orthography MMS was trained on.

Usage (from repo root):
    python utils/prepare_waxal_mms.py
"""

from __future__ import annotations

import json
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILELIST = ROOT / "waxal_hausa" / "tts_filelist.txt"
OUT_DIR = ROOT / "data" / "processed" / "waxal_mms"

# facebook/mms-tts-hau vocab.json characters (tokens _ and the IPA stress
# mark are tokenizer-internal; '6' appears in the vocab but digits in our
# corpus are already spelled out, so it is not needed here).
MMS_HAU_CHARS = set("abcdefghijklmnorstuwyz") | set("āăūƙɓɗ'- ")

CHAR_MAP = {
    "ƴ": "'y",
    "Ƴ": "'y",
    "p": "f",
    "v": "b",
    "q": "k",
    "x": "s",
    "’": "'",
    "‘": "'",
    "`": "'",
    "–": "-",
    "—": "-",
    # Accent folding for foreign names (Côte d'Ivoire, Müller, ...)
    "é": "e", "è": "e", "ê": "e", "ë": "e",
    "á": "a", "à": "a", "â": "a", "ã": "a", "å": "a", "ä": "a",
    "í": "i", "ì": "i", "î": "i", "ï": "i",
    "ó": "o", "ò": "o", "ô": "o", "õ": "o", "ö": "o",
    "ú": "u", "ù": "u", "û": "u", "ü": "u",
    "ç": "c", "ñ": "n",
}

# Combining tone/length marks occasionally leak into the plain column.
STRIP_COMBINING = {"̀", "́", "̂", "̄"}


def normalize_for_mms(text: str, oov: Counter) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    out = []
    for ch in text:
        if ch in STRIP_COMBINING:
            continue
        ch = CHAR_MAP.get(ch, ch)
        for c in ch:
            if c in MMS_HAU_CHARS:
                out.append(c)
            elif c.isspace():
                out.append(" ")
            else:
                oov[c] += 1  # dropped (punctuation, digits, symbols)
    return " ".join("".join(out).split())


def main() -> None:
    from datasets import Audio, Dataset

    records = {"audio": [], "text": [], "speaker_id": [], "original_text": []}
    oov: Counter = Counter()
    skipped_missing = 0
    skipped_digits = 0

    with open(FILELIST, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) < 2:
                continue
            rel_path, plain_text = parts[0], parts[1]
            # Transcripts with digits (dates, units, currency) can't be
            # reliably matched to what the reader actually said — drop them.
            if any(c.isdigit() for c in plain_text):
                skipped_digits += 1
                continue
            audio_path = ROOT / "waxal_hausa" / rel_path
            if not audio_path.exists():
                skipped_missing += 1
                continue
            filename = audio_path.name
            subparts = filename.split("_")
            speaker_id = subparts[1] if len(subparts) >= 3 else "default"
            text = normalize_for_mms(plain_text, oov)
            if not text:
                continue
            records["audio"].append(str(audio_path))
            records["text"].append(text)
            records["speaker_id"].append(speaker_id)
            records["original_text"].append(plain_text)

    ds = Dataset.from_dict(records).cast_column("audio", Audio())

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = OUT_DIR / "train.parquet"
    ds.to_parquet(str(parquet_path))

    speakers = Counter(records["speaker_id"])
    manifest = {
        "source": "waxal_hausa (google/WaxalNLP, CC-BY-4.0 / CC-BY-SA-4.0)",
        "target_vocab": "facebook/mms-tts-hau (CC-BY-NC-4.0)",
        "clip_count": len(ds),
        "skipped_digit_transcripts": skipped_digits,
        "skipped_missing_audio": skipped_missing,
        "speakers": dict(sorted(speakers.items())),
        "dropped_oov_chars": {repr(k): v for k, v in oov.most_common()},
        "text_column": "text",
        "audio_column": "audio",
        "speaker_column": "speaker_id",
    }
    with open(OUT_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(ds)} clips -> {parquet_path}")
    print(f"Skipped {skipped_digits} clips with digits in transcript")
    print(f"Speakers: {dict(sorted(speakers.items()))}")
    print(f"Dropped OOV chars: {dict(oov.most_common(20))}")
    if skipped_missing:
        print(f"Skipped {skipped_missing} rows with missing audio")

    # Show a few normalization examples for eyeballing
    for i in range(0, min(len(ds), 3)):
        print(f"  RAW : {records['original_text'][i]}")
        print(f"  NORM: {records['text'][i]}")


if __name__ == "__main__":
    main()
