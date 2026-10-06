"""Fine-tune a Piper (MIT) voice on the WAXAL Hausa clips — all 8 speakers.

Warm-starts from the public-domain en_US-lessac-medium checkpoint (acoustic
initialization only; the WAXAL fine-tune replaces the voice) and trains a
single multi-speaker Hausa model matching the Murya speaker dial. Piper's
code is MIT and WAXAL is CC-BY-4.0 / CC-BY-SA-4.0. The published weights are
CC BY-NC-SA 4.0: non-commercial and share-alike. Commercial use of the voice
needs a separate written license. The application code stays MIT.

Launch:

    modal run finetune_piper_hausa_modal.py --extra-epochs 300

Outputs land in the `hausa-ai-checkpoints` volume under piper_hausa_waxal/:
final .ckpt, exported model.onnx + model.onnx.json, and sample WAVs per
speaker. Pull with:

    modal volume get hausa-ai-checkpoints piper_hausa_waxal models/piper_hausa_waxal

Long bake / resume: --resume-ckpt continues the epoch counter, so
--extra-epochs is then the TOTAL target (e.g. resume a 300-epoch ckpt with
--extra-epochs 2000 to train 1700 more). Fresh warm-starts begin at 0.
A backup checkpoint syncs to the volume every 15 min (latest_backup.ckpt).
"""

import os
import shutil
import subprocess

import modal

app = modal.App("hausa-piper-finetuning")

checkpoints_volume = modal.Volume.from_name("hausa-ai-checkpoints", create_if_missing=True)

PIPER = "/root/piper"
SAMPLE_RATE = 22050
BASE_CKPT_REPO = "rhasspy/piper-checkpoints"
BASE_CKPT_FILE = "en/en_US/lessac/medium/epoch=2164-step=1355540.ckpt"
BASE_EPOCH = 2164  # epoch counter stored inside the lessac checkpoint

# espeak-ng has no Hausa voice, so we train on graphemes (piper's "text"
# phoneme type). Hausa's Boko orthography is phonemic, and this keeps the
# hooked letters as first-class symbols instead of collapsing them.
# Layout follows piper-phonemize's Ukrainian codepoints map:
# _ (pad)=0, ^ (bos)=1, $ (eos)=2, then space/punctuation/letters.
HA_ALPHABET = (
    ["_", "^", "$", " ", "!", "'", ",", "-", ".", ":", ";", "?"]
    + list("abcdefghijklmnorstuwyz")
    + ["ɓ", "ɗ", "ƙ", "ƴ"]
    + list("pqvx")  # rare loanword letters (names, borrowings)
)
HA_MAP = {ch: [i] for i, ch in enumerate(HA_ALPHABET)}

# Wrapper that injects the Hausa map into piper_train.preprocess.
# phonemize_codepoints() is language-independent (casefolded codepoints);
# only the id lookup and the config's phoneme_id_map need the "ha" entry.
PREPROCESS_WRAPPER = '''
import json, sys

HA_MAP = json.loads(sys.argv[1])

import piper_phonemize
import piper_train.preprocess as pp

_orig_map = piper_phonemize.get_codepoints_map

def get_codepoints_map():
    maps = dict(_orig_map())
    maps["ha"] = HA_MAP
    return maps

def phoneme_ids_codepoints(language, phonemes, missing_phonemes=None):
    assert language == "ha", language
    # Mirrors piper-phonemize phonemes_to_ids with interspersed pad:
    # ^ _ p1 _ p2 _ ... $
    ids = [1, 0]
    for ph in phonemes:
        mapped = HA_MAP.get(ph)
        if mapped is None:
            if missing_phonemes is not None:
                missing_phonemes[ph] = missing_phonemes.get(ph, 0) + 1
            continue
        ids.extend(mapped)
        ids.append(0)
    ids.append(2)
    return ids

pp.get_codepoints_map = get_codepoints_map
pp.phoneme_ids_codepoints = phoneme_ids_codepoints

sys.argv = ["preprocess.py"] + sys.argv[2:]
pp.main()
'''

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "espeak-ng", "ffmpeg", "build-essential", "libsndfile1")
    .run_commands(
        f"git clone https://github.com/rhasspy/piper.git {PIPER}",
        # Piper training stack is from the lightning 1.x / torch 1.13 era
        "pip install pip==23.3.2",
        "pip install numpy==1.24.4 'cython>=0.29.0' piper-phonemize==1.1.0 "
        "librosa==0.10.1 onnx==1.15.0 onnxruntime==1.16.3",
        "pip install torch==1.13.1 pytorch-lightning==1.7.7 torchmetrics==0.11.4",
        f"pip install -e {PIPER}/src/python --no-deps",
        f"cd {PIPER}/src/python && bash build_monotonic_align.sh",
        # hub 0.x is requests-based (1.x needs httpx); piper-tts without deps
        # so it can't disturb the pinned torch/onnxruntime stack
        "pip install 'huggingface_hub==0.25.2' requests && pip install piper-tts==1.2.0 --no-deps",
        # lightning 1.7-era logging deps missed by the --no-deps installs
        "pip install six==1.17.0 tensorboard==2.11.2 protobuf==3.20.3",
        # fail at build time if anything in the training stack can't import
        "python -c 'import piper_train.preprocess, piper_train.__main__, piper_train.export_onnx'",
    )
    .add_local_dir(
        os.path.join(os.path.dirname(__file__), "waxal_hausa"),
        remote_path="/src/waxal_hausa",
    )
)


def clean_text(text: str) -> str:
    """Normalize to the HA_ALPHABET symbol set (casefolded graphemes)."""
    import unicodedata

    text = unicodedata.normalize("NFC", text).casefold()
    subs = {"’": "'", "‘": "'", "`": "'", "–": "-", "—": "-", "\xa0": " ", "​": ""}
    for a, b in subs.items():
        text = text.replace(a, b)
    kept = set(HA_ALPHABET)
    out = "".join(c if c in kept else (" " if c.isspace() else "") for c in text)
    return " ".join(out.split())


MIN_CLIP_SECONDS = 1.0
# Corpus stats (soundfile, clean clips): median 12.8s, p90 49.7s, max 132s.
# 20s keeps 970 clips / 2.83h; the >20s tail is what OOMs the GPU.
MAX_CLIP_SECONDS = 20.0


def clip_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return -1.0


def stage_ljspeech_dataset(dst: str) -> dict:
    """waxal filelist -> LJSpeech-style dir: wav/<id>.wav + metadata.csv (id|speaker|text)."""
    wav_dir = os.path.join(dst, "wav")
    os.makedirs(wav_dir, exist_ok=True)
    kept, skipped_digits, skipped_duration, speakers = 0, 0, 0, set()
    lines_out = []
    with open("/src/waxal_hausa/tts_filelist.txt", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) < 2:
                continue
            rel_path, text = parts[0], parts[1]
            # Digit transcripts (dates, units) don't match what was read
            # aloud — check BEFORE clean_text, which strips digits.
            if any(c.isdigit() for c in text):
                skipped_digits += 1
                continue
            text = clean_text(text)
            if not text:
                continue
            src = os.path.join("/src/waxal_hausa", rel_path)
            if not os.path.exists(src):
                continue
            duration = clip_duration(src)
            if not (MIN_CLIP_SECONDS <= duration <= MAX_CLIP_SECONDS):
                skipped_duration += 1
                continue
            clip_id = os.path.splitext(os.path.basename(rel_path))[0]
            speaker = clip_id.split("_")[1] if len(clip_id.split("_")) >= 3 else "default"
            wav_path = os.path.join(wav_dir, f"{clip_id}.wav")
            subprocess.run(
                ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src,
                 "-ar", str(SAMPLE_RATE), "-ac", "1", "-sample_fmt", "s16", wav_path],
                check=True,
            )
            lines_out.append(f"{clip_id}|{speaker}|{text}")
            speakers.add(speaker)
            kept += 1
    # Include sentence segments recovered from long/digit clips, if the
    # segmentation run (segment_waxal_modal.py) has populated the volume.
    seg_dir = "/checkpoints/waxal_segments"
    seg_filelist = os.path.join(seg_dir, "segments_filelist.txt")
    segments_added = 0
    if os.path.exists(seg_filelist):
        with open(seg_filelist, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) < 2:
                    continue
                rel_path, text = parts[0], parts[1]
                text = clean_text(text)
                if not text:
                    continue
                src = os.path.join(seg_dir, rel_path)
                if not os.path.exists(src):
                    continue
                clip_id = os.path.splitext(os.path.basename(rel_path))[0]
                speaker = clip_id.split("_")[1] if len(clip_id.split("_")) >= 3 else "default"
                shutil.copy(src, os.path.join(wav_dir, f"{clip_id}.wav"))
                lines_out.append(f"{clip_id}|{speaker}|{text}")
                speakers.add(speaker)
                segments_added += 1
                kept += 1

    with open(os.path.join(dst, "metadata.csv"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out) + "\n")
    return {
        "kept": kept,
        "skipped_digits": skipped_digits,
        "skipped_duration": skipped_duration,
        "segments_added": segments_added,
        "speakers": sorted(speakers),
    }


@app.function(
    image=image,
    gpu="A10G",
    timeout=86400,  # 24 h ceiling — long bakes are budget-approved
    volumes={"/checkpoints": checkpoints_volume},
)
def finetune(extra_epochs: int = 300, batch_size: int = 12, resume_ckpt: str = ""):
    out_dir = "/checkpoints/piper_hausa_waxal"
    os.makedirs(out_dir, exist_ok=True)
    # Reduce fragmentation headroom needed on the 22 GB A10G
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"

    # 1. Stage dataset (mp3 -> 22.05 kHz mono wav)
    print("[piper] Staging LJSpeech-format dataset...")
    stats = stage_ljspeech_dataset("/tmp/ds")
    print(f"[piper] Staged {stats['kept']} clips ({stats['segments_added']} from "
          f"recovered segments), speakers {stats['speakers']}, "
          f"skipped {stats['skipped_digits']} digit transcripts, "
          f"{stats['skipped_duration']} out-of-range durations")

    # 2. Preprocess with grapheme ("text") phonemes + injected Hausa map
    print("[piper] Preprocessing (grapheme mode, Hausa alphabet)...")
    import json as _json
    wrapper_path = "/tmp/preprocess_ha.py"
    with open(wrapper_path, "w", encoding="utf-8") as f:
        f.write(PREPROCESS_WRAPPER)
    subprocess.run(
        ["python", wrapper_path, _json.dumps(HA_MAP, ensure_ascii=False),
         "--language", "ha",
         "--input-dir", "/tmp/ds",
         "--output-dir", "/tmp/train",
         "--dataset-format", "ljspeech",
         "--phoneme-type", "text",
         "--text-casing", "casefold",
         "--sample-rate", str(SAMPLE_RATE),
         "--max-workers", "8"],
        cwd=f"{PIPER}/src/python",
        check=True,
    )
    with open("/tmp/train/config.json", encoding="utf-8") as f:
        cfg = _json.load(f)
    print(f"[piper] num_symbols={cfg['num_symbols']} speakers={cfg['num_speakers']} "
          f"map_size={len(cfg['phoneme_id_map'])}")

    # 3. Base checkpoint: fresh lessac (single->multi speaker) or resume our own
    #
    # If Modal silently reschedules this container (preemption), the function
    # re-runs with THIS SAME static resume_ckpt argument -- it has no way to
    # know a newer latest_backup.ckpt now exists on the volume. Detected
    # 2026-07-04: a restart resumed from a ~150-epoch-stale argument despite
    # the 15-min backup thread having reached further (failure signature:
    # auto-restart-uses-stale-resume-path). Always compare embedded epoch
    # counts and pick the freshest checkpoint automatically.
    def _ckpt_epoch(path: str) -> int:
        # NOTE: no pathlib PosixPath/WindowsPath aliasing here — this runs in
        # the Linux container, where aliasing PosixPath breaks torch.load
        # entirely (verified 2026-07-05: it scored BOTH resume candidates -1,
        # letting a Git-Bash-mangled path win the tie and crash training).
        # The alias is only needed when reading these ckpts on Windows.
        try:
            import torch
            if not os.path.exists(path):
                print(f"[piper] Resume candidate does not exist: {path}")
                return -1
            return int(torch.load(path, map_location="cpu", weights_only=False).get("epoch", -1))
        except Exception as e:  # noqa: BLE001 - a bad/missing ckpt just loses this comparison
            print(f"[piper] Could not read epoch from {path}: {e}")
            return -1

    if resume_ckpt:
        candidates = [resume_ckpt]
        backup_path = "/checkpoints/piper_hausa_waxal/latest_backup.ckpt"
        if os.path.exists(backup_path) and os.path.abspath(backup_path) != os.path.abspath(resume_ckpt):
            candidates.append(backup_path)
        scored = [(c, _ckpt_epoch(c)) for c in candidates]
        for c, e in scored:
            print(f"[piper] Candidate resume checkpoint {c}: epoch={e}")
        best, best_epoch = max(scored, key=lambda ce: ce[1])
        if best_epoch < 0:
            raise RuntimeError(
                f"No readable resume checkpoint among candidates: {scored}. "
                "Refusing to train from a broken/mangled path."
            )
        base = best
        resume_flag = "--resume_from_checkpoint"
        print(f"[piper] Resuming from freshest checkpoint: {base} (epoch {best_epoch})")
    else:
        from huggingface_hub import hf_hub_download
        base = hf_hub_download(repo_id=BASE_CKPT_REPO, filename=BASE_CKPT_FILE, repo_type="dataset")
        resume_flag = "--resume_from_single_speaker_checkpoint"
        print(f"[piper] Warm-starting from {BASE_CKPT_FILE}")

    # 4. Train
    # NOTE: --resume_from_single_speaker_checkpoint loads weights only and
    # RESETS the epoch counter to 0 (verified 2026-07-02), so max_epochs is
    # the actual number of fine-tuning epochs — not BASE_EPOCH + extra.
    max_epochs = extra_epochs
    print(f"[piper] Training {max_epochs} epochs (counter starts at 0)...")

    # Safety net: copy the newest checkpoint to the volume every 15 min so a
    # timeout/crash can't lose the run (lightning writes to container-local /tmp).
    import threading

    def _sync_newest_ckpt():
        ckpts = []
        for root, _dirs, files in os.walk("/tmp/train/lightning_logs"):
            ckpts += [os.path.join(root, f) for f in files if f.endswith(".ckpt")]
        if not ckpts:
            return
        newest = max(ckpts, key=os.path.getmtime)
        dst = os.path.join(out_dir, "latest_backup.ckpt")
        tmp = dst + ".tmp"
        shutil.copy(newest, tmp)
        os.replace(tmp, dst)
        checkpoints_volume.commit()
        print(f"[piper] Synced backup checkpoint {os.path.basename(newest)} to volume")

    stop_sync = threading.Event()

    def _sync_loop():
        while not stop_sync.wait(900):
            try:
                _sync_newest_ckpt()
            except Exception as e:  # noqa: BLE001 - backup must never kill training
                print(f"[piper] checkpoint sync failed (non-fatal): {e}")

    threading.Thread(target=_sync_loop, daemon=True).start()
    subprocess.run(
        ["python", "-m", "piper_train",
         "--dataset-dir", "/tmp/train",
         "--accelerator", "gpu",
         "--devices", "1",
         "--batch-size", str(batch_size),
         "--validation-split", "0.02",
         "--num-test-examples", "2",
         "--max_epochs", str(max_epochs),
         resume_flag, base,
         "--checkpoint-epochs", "25",
         "--precision", "32",
         "--quality", "medium"],
        cwd=f"{PIPER}/src/python",
        check=True,
    )
    stop_sync.set()

    # 5. Collect newest checkpoint, export ONNX
    ckpt_dir = "/tmp/train/lightning_logs"
    ckpts = []
    for root, _dirs, files in os.walk(ckpt_dir):
        ckpts += [os.path.join(root, f) for f in files if f.endswith(".ckpt")]
    last_ckpt = max(ckpts, key=os.path.getmtime)
    print(f"[piper] Exporting {last_ckpt}")
    shutil.copy(last_ckpt, os.path.join(out_dir, "last.ckpt"))
    subprocess.run(
        ["python", "-m", "piper_train.export_onnx", last_ckpt, os.path.join(out_dir, "model.onnx")],
        cwd=f"{PIPER}/src/python",
        check=True,
    )
    shutil.copy("/tmp/train/config.json", os.path.join(out_dir, "model.onnx.json"))
    checkpoints_volume.commit()

    # 6. Benchmark WAVs (3 sentences x all speakers)
    print("[piper] Generating sample WAVs...")
    samples_dir = os.path.join(out_dir, "samples")
    os.makedirs(samples_dir, exist_ok=True)
    # lowercase: grapheme map is casefolded, inference text should match
    sentences = [
        ("sannu", "sannu da zuwa, ina fatan kana lafiya."),
        ("hausa", "hausa harshe ne mai arziki da tarihi."),
        ("gaskiya", "gaskiya ta fi ƙarfin takobi, in ji magabata."),
        # "danjuma" with plain d (not ɗ) — per Adamu Danjuma Abubakar
        ("danjuma", "sannu, ni ne adamu danjuma abubakar."),
    ]
    # Label samples by the model's OWN speaker_id_map (Piper shuffles indices
    # during preprocessing) — NOT the sorted speaker list. Assuming sorted order
    # mislabels the WAVs: e.g. `piper -s 7` is whatever name maps to index 7 in
    # speaker_id_map, which is not sorted[7]. (This bug produced eval files named
    # M4_*.wav that were actually a female voice.)
    import json as _json
    with open(os.path.join(out_dir, "model.onnx.json"), "r", encoding="utf-8") as _f:
        _spk_map = _json.load(_f).get("speaker_id_map", {})
    if not _spk_map:
        _spk_map = {(stats["speakers"][0] if stats["speakers"] else "spk0"): 0}
    for spk_name, spk_idx in _spk_map.items():
        for name, text in sentences:
            wav_out = os.path.join(samples_dir, f"{spk_name}_{name}.wav")
            r = subprocess.run(
                ["piper", "-m", os.path.join(out_dir, "model.onnx"),
                 "-c", os.path.join(out_dir, "model.onnx.json"),
                 "-s", str(spk_idx), "-f", wav_out],
                input=text.encode("utf-8"),
            )
            if r.returncode != 0:
                print(f"[piper] sample generation failed for {spk_name}/{name} (non-fatal)")
    checkpoints_volume.commit()
    print(f"[piper] Done. Model + samples in volume at {out_dir}")


@app.function(
    image=image,
    gpu="A10G",
    timeout=1800,
    volumes={"/checkpoints": checkpoints_volume},
)
def evaluate(ckpt: str = "/checkpoints/piper_hausa_waxal/latest_backup.ckpt",
             out_name: str = "eval_current"):
    """Export a mid-training checkpoint and synthesize audition WAVs from it.

    Usage:  modal run finetune_piper_hausa_modal.py::evaluate
    Output: volume piper_hausa_waxal/<out_name>/  (onnx + WAVs, pull and listen)
    """
    import shutil as _shutil

    out_dir = f"/checkpoints/piper_hausa_waxal/{out_name}"
    os.makedirs(out_dir, exist_ok=True)

    # The exporter needs the training config next to it; regenerate quickly
    # from the same staging + preprocess path used in training.
    print("[eval] Staging + preprocessing for config regeneration...")
    stats = stage_ljspeech_dataset("/tmp/ds")
    import json as _json
    wrapper_path = "/tmp/preprocess_ha.py"
    with open(wrapper_path, "w", encoding="utf-8") as f:
        f.write(PREPROCESS_WRAPPER)
    subprocess.run(
        ["python", wrapper_path, _json.dumps(HA_MAP, ensure_ascii=False),
         "--language", "ha", "--input-dir", "/tmp/ds", "--output-dir", "/tmp/train",
         "--dataset-format", "ljspeech", "--phoneme-type", "text",
         "--text-casing", "casefold", "--sample-rate", str(SAMPLE_RATE),
         "--max-workers", "8"],
        cwd=f"{PIPER}/src/python", check=True,
    )

    print(f"[eval] Exporting {ckpt}...")
    subprocess.run(
        ["python", "-m", "piper_train.export_onnx", ckpt, os.path.join(out_dir, "model.onnx")],
        cwd=f"{PIPER}/src/python", check=True,
    )
    _shutil.copy("/tmp/train/config.json", os.path.join(out_dir, "model.onnx.json"))

    print("[eval] Generating audition WAVs...")
    sentences = [
        ("sannu", "sannu da zuwa, ina fatan kana lafiya."),
        ("hausa", "hausa harshe ne mai arziki da tarihi."),
        ("gaskiya", "gaskiya ta fi ƙarfin takobi, in ji magabata."),
        ("danjuma", "sannu, ni ne adamu danjuma abubakar."),
    ]
    # Label by the model's real speaker_id_map, not sorted order (see the
    # matching note in finetune()'s benchmark block — sorted[idx] != piper -s idx).
    import json as _json
    with open(os.path.join(out_dir, "model.onnx.json"), "r", encoding="utf-8") as _f:
        _spk_map = _json.load(_f).get("speaker_id_map", {})
    if not _spk_map:
        _spk_map = {(stats["speakers"][0] if stats["speakers"] else "spk0"): 0}
    for spk_name, spk_idx in _spk_map.items():
        for name, text in sentences:
            wav_out = os.path.join(out_dir, f"{spk_name}_{name}.wav")
            subprocess.run(
                ["piper", "-m", os.path.join(out_dir, "model.onnx"),
                 "-c", os.path.join(out_dir, "model.onnx.json"),
                 "-s", str(spk_idx), "-f", wav_out],
                input=text.encode("utf-8"),
            )
    checkpoints_volume.commit()
    print(f"[eval] Done — WAVs in volume at piper_hausa_waxal/{out_name}/")


@app.local_entrypoint()
def main(extra_epochs: int = 300, batch_size: int = 12, resume_ckpt: str = ""):
    # .spawn() + `modal run --detach` survives local disconnects (laptop
    # sleep); a blocking .remote() can be canceled when the caller drops.
    call = finetune.spawn(extra_epochs=extra_epochs, batch_size=batch_size, resume_ckpt=resume_ckpt)
    print(f"[piper] Spawned detached training call: {call.object_id}")
    print("[piper] Safe to sleep/disconnect — training finishes server-side.")
    # Stream progress while the client stays connected (harmless if it drops)
    call.get()
