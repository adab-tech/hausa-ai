"""Segment long WAXAL Hausa clips into sentence-level training pieces.

The Piper training set uses only 1-20s clips (970 of 1,572). This recovers
the rest: the 340 clips >20s AND the 262 digit-containing clips, by
transcript-guided forced alignment:

  1. faster-whisper (GPU, word timestamps, language='ha') transcribes each clip
  2. whisper words are aligned to the ground-truth transcript (SequenceMatcher)
  3. audio is cut at sentence boundaries; only clean sentences survive
     (1-20s, no digits, >=50% word alignment coverage)

Outputs to the `hausa-ai-checkpoints` volume under waxal_segments/:
  audio/<clip>_sNN.wav   (22.05 kHz mono 16-bit)
  segments_filelist.txt  (audio/xxx.wav|text  — same format as tts_filelist)
  stats.json

The training script reads these directly from the volume (mounted at
/checkpoints), so no re-upload is needed.

Launch:
    modal run --detach segment_waxal_modal.py
"""

import json
import os
import re
import subprocess
import unicodedata

import modal

app = modal.App("hausa-waxal-segmentation")

checkpoints_volume = modal.Volume.from_name("hausa-ai-checkpoints", create_if_missing=True)

SAMPLE_RATE = 22050
MIN_SEG_SECONDS = 1.0
MAX_SEG_SECONDS = 20.0
MIN_COVERAGE = 0.5   # fraction of sentence words whisper must have matched
PAD_SECONDS = 0.05
OUT_DIR = "/checkpoints/waxal_segments"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install("faster-whisper==1.1.0", "soundfile", "numpy",
                 "requests", "huggingface_hub==0.25.2",
                 # CTranslate2 (faster-whisper backend) needs CUDA 12 runtime libs
                 "nvidia-cublas-cu12", "nvidia-cudnn-cu12==9.*")
    .env({"LD_LIBRARY_PATH":
          "/usr/local/lib/python3.11/site-packages/nvidia/cublas/lib:"
          "/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib"})
    # fail at build time if the stack can't import (playbook: missing-transitive-dep)
    .run_commands("python -c 'import faster_whisper, soundfile, requests'")
    .add_local_dir(
        os.path.join(os.path.dirname(__file__), "waxal_hausa"),
        remote_path="/src/waxal_hausa",
    )
)


def norm_word(w: str) -> str:
    """Normalize a word for alignment matching (not for training text).

    Whisper's Hausa output is phonetic, not orthographic — it writes plain
    k/b/d/y for the hooked letters and drops glottal marks. Fold both sides
    to the same reduced alphabet so character-level alignment can anchor.
    """
    w = unicodedata.normalize("NFD", w).casefold()
    w = "".join(c for c in w if not unicodedata.combining(c))
    w = w.translate(str.maketrans({"ƙ": "k", "ɓ": "b", "ɗ": "d", "ƴ": "y", "q": "k"}))
    return re.sub(r"[^a-z]", "", w)


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?;:])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


@app.function(
    image=image,
    gpu="A10G",
    timeout=14400,
    volumes={"/checkpoints": checkpoints_volume},
)
def segment(sample: int = 0, min_coverage: float = MIN_COVERAGE):
    import numpy as np
    import soundfile as sf
    from difflib import SequenceMatcher
    from faster_whisper import WhisperModel

    audio_out = os.path.join(OUT_DIR, "audio")
    os.makedirs(audio_out, exist_ok=True)

    # 1. Select clips excluded from the direct training set
    targets = []
    with open("/src/waxal_hausa/tts_filelist.txt", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) < 2:
                continue
            rel_path, text = parts[0], parts[1]
            src = os.path.join("/src/waxal_hausa", rel_path)
            if not os.path.exists(src):
                continue
            has_digits = any(c.isdigit() for c in text)
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", src],
                capture_output=True, text=True,
            )
            try:
                duration = float(r.stdout.strip())
            except ValueError:
                continue
            if duration > MAX_SEG_SECONDS or has_digits:
                targets.append((src, text, duration))

    if sample:
        targets = targets[:sample]
    total_in_h = sum(d for _, _, d in targets) / 3600
    print(f"[segment] {len(targets)} clips to segment ({total_in_h:.2f} h of audio), "
          f"min_coverage={min_coverage}")

    print("[segment] Loading faster-whisper large-v3...")
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")

    filelist_lines = []
    stats = {"clips": len(targets), "segments": 0, "kept_seconds": 0.0,
             "skipped_short": 0, "skipped_long": 0, "skipped_digits": 0,
             "skipped_low_coverage": 0, "failed_clips": 0}

    for n, (src, text, duration) in enumerate(targets):
        clip_id = os.path.splitext(os.path.basename(src))[0]
        try:
            # Decode once at target rate for cutting
            wav_tmp = "/tmp/full.wav"
            subprocess.run(
                ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src,
                 "-ar", str(SAMPLE_RATE), "-ac", "1", "-sample_fmt", "s16", wav_tmp],
                check=True,
            )
            audio, _sr = sf.read(wav_tmp, dtype="int16")

            # 2. Whisper word timestamps
            segments_iter, _info = model.transcribe(
                src, language="ha", word_timestamps=True, beam_size=5,
            )
            hyp_words = []
            for seg in segments_iter:
                for w in seg.words or []:
                    hyp_words.append((norm_word(w.word), w.start, w.end))
            hyp_norm = [w[0] for w in hyp_words]

            # 3. Map transcript words -> whisper timestamps
            sentences = split_sentences(text)
            ref_words, ref_sentence_of = [], []
            for si, s in enumerate(sentences):
                for w in re.findall(r"\S+", s):
                    nw = norm_word(w)
                    if nw:
                        ref_words.append(nw)
                        ref_sentence_of.append(si)

            # Character-level alignment: whisper merges/mangles words, so
            # word-identity matching fails (~10% coverage), but the character
            # stream still aligns well. Each ref word inherits the timestamp
            # of the hyp word its characters mostly landed in.
            def char_stream(words):
                chars, owner = [], []
                for wi, w in enumerate(words):
                    for c in w:
                        chars.append(c)
                        owner.append(wi)
                return chars, owner

            ref_chars, ref_owner = char_stream(ref_words)
            hyp_chars, hyp_owner = char_stream(hyp_norm)
            matcher = SequenceMatcher(None, ref_chars, hyp_chars, autojunk=False)
            from collections import defaultdict
            overlap: dict = defaultdict(lambda: defaultdict(int))
            for block in matcher.get_matching_blocks():
                for k in range(block.size):
                    overlap[ref_owner[block.a + k]][hyp_owner[block.b + k]] += 1

            ref_to_time = {}
            for ri, hyp_hits in overlap.items():
                matched_chars = sum(hyp_hits.values())
                if matched_chars < max(2, len(ref_words[ri]) // 2):
                    continue  # too few characters anchored to trust
                hi = max(hyp_hits, key=hyp_hits.get)
                ref_to_time[ri] = (hyp_words[hi][1], hyp_words[hi][2])

            match_ratio = len(ref_to_time) / max(1, len(ref_words))
            if sample or n < 3:
                print(f"[segment][debug] {clip_id}: dur={duration:.0f}s "
                      f"ref_words={len(ref_words)} hyp_words={len(hyp_norm)} "
                      f"matched={len(ref_to_time)} ({match_ratio:.0%}) "
                      f"sentences={len(sentences)}")
                if match_ratio < 0.3:
                    print(f"[segment][debug]   ref: {' '.join(ref_words[:15])}")
                    print(f"[segment][debug]   hyp: {' '.join(hyp_norm[:15])}")

            # 4. Compute per-sentence raw anchors first, then cut with
            # neighbor-aware boundaries: whisper often fails to match a
            # sentence's first/last words, so extend each cut toward its
            # neighbors' anchors (bounded) to recapture unmatched edges.
            anchors = {}
            for si in range(len(sentences)):
                idxs = [i for i, s_of in enumerate(ref_sentence_of) if s_of == si]
                matched = [ref_to_time[i] for i in idxs if i in ref_to_time]
                if idxs and matched:
                    anchors[si] = (matched[0][0], matched[-1][1], len(matched) / len(idxs))

            # Edge policy (per Adamsy): include 0.2-0.5s of natural silence
            # at each edge so segments breathe; allow up to 1.0s to also
            # recapture words whisper failed to match at the boundary.
            # Neighboring segments split the inter-sentence gap at midpoint.
            PAD_MIN, PAD_MAX_SLACK = 0.2, 1.0

            for si, sentence in enumerate(sentences):
                if si not in anchors:
                    idxs = [i for i, s_of in enumerate(ref_sentence_of) if s_of == si]
                    if idxs:
                        stats["skipped_low_coverage"] += 1
                    continue
                if any(c.isdigit() for c in sentence):
                    stats["skipped_digits"] += 1
                    continue
                raw_start, raw_end, coverage = anchors[si]
                if coverage < min_coverage:
                    stats["skipped_low_coverage"] += 1
                    continue
                prev_end = max((anchors[sj][1] for sj in anchors if sj < si), default=None)
                next_start = min((anchors[sj][0] for sj in anchors if sj > si), default=None)

                mid_before = (prev_end + raw_start) / 2 if prev_end is not None else raw_start - 0.35
                t0 = min(raw_start - PAD_MIN, max(mid_before, raw_start - PAD_MAX_SLACK))
                t0 = max(0.0, t0)

                mid_after = (raw_end + next_start) / 2 if next_start is not None else raw_end + 0.35
                t1 = max(raw_end + PAD_MIN, min(mid_after, raw_end + PAD_MAX_SLACK))
                t1 = min(duration, t1)
                seg_dur = t1 - t0
                if seg_dur < MIN_SEG_SECONDS:
                    stats["skipped_short"] += 1
                    continue
                if seg_dur > MAX_SEG_SECONDS:
                    stats["skipped_long"] += 1
                    continue
                seg_audio = audio[int(t0 * SAMPLE_RATE):int(t1 * SAMPLE_RATE)]
                seg_name = f"{clip_id}_s{si:02d}.wav"
                sf.write(os.path.join(audio_out, seg_name), seg_audio, SAMPLE_RATE)
                filelist_lines.append(f"audio/{seg_name}|{sentence}")
                stats["segments"] += 1
                stats["kept_seconds"] += seg_dur
        except Exception as e:  # noqa: BLE001 - one bad clip must not kill the batch
            stats["failed_clips"] += 1
            print(f"[segment] FAILED {clip_id}: {e}")
            # Circuit breaker: all-failures-no-successes means the environment
            # is broken, not the data — abort instead of burning the batch.
            if stats["failed_clips"] >= 15 and stats["segments"] == 0:
                raise RuntimeError(
                    f"{stats['failed_clips']} consecutive failures with zero segments — "
                    f"environment problem, aborting. Last error: {e}"
                ) from e

        if (n + 1) % 50 == 0 or (n + 1) == len(targets):
            print(f"[segment] {n + 1}/{len(targets)} clips, {stats['segments']} segments, "
                  f"{stats['kept_seconds'] / 3600:.2f} h recovered | skips: "
                  f"cov={stats['skipped_low_coverage']} long={stats['skipped_long']} "
                  f"short={stats['skipped_short']} digits={stats['skipped_digits']} "
                  f"failed={stats['failed_clips']}")
            # Incremental output so a dead run still leaves usable artifacts
            with open(os.path.join(OUT_DIR, "segments_filelist.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(filelist_lines) + "\n")
            with open(os.path.join(OUT_DIR, "stats.json"), "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
            checkpoints_volume.commit()

    with open(os.path.join(OUT_DIR, "segments_filelist.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(filelist_lines) + "\n")
    with open(os.path.join(OUT_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    checkpoints_volume.commit()

    print(f"[segment] DONE: {stats['segments']} segments, "
          f"{stats['kept_seconds'] / 3600:.2f} h recovered from {total_in_h:.2f} h")
    print(f"[segment] Stats: {stats}")


@app.local_entrypoint()
def main(sample: int = 0, min_coverage: float = MIN_COVERAGE):
    call = segment.spawn(sample=sample, min_coverage=min_coverage)
    print(f"[segment] Spawned detached segmentation call: {call.object_id}")
    call.get()
