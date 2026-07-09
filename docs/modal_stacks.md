# Known-good Modal dependency stacks (Hausa AI)

Verified 2026-07-02/03 through live runs. **Copy these wholesale when writing a
new Modal script — do not re-derive pip lists from memory.** Every stack must
end with a build-time import smoke-test so missing deps fail at build (seconds,
free) instead of mid-run (minutes, GPU dollars).

## Stack 1 — Piper VITS training (`finetune_piper_hausa_modal.py`)

Python 3.10 · apt: `git espeak-ng ffmpeg build-essential libsndfile1`

```
pip==23.3.2
numpy==1.24.4  cython>=0.29.0  piper-phonemize==1.1.0
librosa==0.10.1  onnx==1.15.0  onnxruntime==1.16.3
torch==1.13.1  pytorch-lightning==1.7.7  torchmetrics==0.11.4
huggingface_hub==0.25.2  requests          # hub 1.x needs httpx — avoid
six==1.17.0  tensorboard==2.11.2  protobuf==3.20.3
piper-tts==1.2.0 (--no-deps)
```

- Build monotonic_align: `cd piper/src/python && bash build_monotonic_align.sh`
- Smoke test: `python -c 'import piper_train.preprocess, piper_train.__main__, piper_train.export_onnx'`
- Gotchas: espeak-ng has NO Hausa — use grapheme mode with the HA_MAP wrapper.
  `--resume_from_single_speaker_checkpoint` resets the epoch counter to 0.

## Stack 2 — faster-whisper GPU (`segment_waxal_modal.py`)

Python 3.11 · apt: `ffmpeg`

```
faster-whisper==1.1.0  soundfile  numpy
requests  huggingface_hub==0.25.2
nvidia-cublas-cu12  nvidia-cudnn-cu12==9.*   # CTranslate2 CUDA runtime
```

- REQUIRED env (debian_slim ships no CUDA userspace libs):
  `LD_LIBRARY_PATH=/usr/local/lib/python3.11/site-packages/nvidia/cublas/lib:/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib`
- Smoke test: `python -c 'import faster_whisper, soundfile, requests'`
  (imports alone don't catch missing CUDA libs — keep a circuit breaker in the
  processing loop: N failures with zero successes → abort.)

## Rules distilled from the 2026-07-02/03 failure log

1. **Pin everything** to versions contemporary with the recipe repo
   (`unpinned-api-drift`).
2. **`--no-deps` demands an audit** — list the transitive deps yourself
   (`missing-transitive-dep`: httpx, six).
3. **Import smoke-test in every image build** — cheap, catches most classes.
4. **GPU libs are not import-visible** — pair the smoke test with a runtime
   circuit breaker (`missing-cuda-runtime-libs`).
5. **Launch through `utils/run_training.ps1`** (preflight → log → diagnose);
   match new failures against `utils/failure_signatures.json` and add classes.
