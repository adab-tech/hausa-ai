# CLAUDE.md: Murya (Hausa AI, murya.ng)

Murya is ADAB-TECH's open-source Hausa AI stack, built by a native Hausa speaker.
Live at murya.ng (landing) and app.murya.ng (app). Code on GitHub, voice model on Hugging Face.

Read this whole file before editing anything.

## Stack at a glance

- **Frontend** (repo root): React + TypeScript + Vite; Capacitor for Android (`android/`). Components in `components/`, client services in `services/`, hooks in `hooks/`.
- **Backend** (`backend/`): FastAPI. Routers in `backend/routers/`, services in `backend/services/`, tests in `backend/tests/`.
- **Landing page**: `landing/` (deployed separately to Cloudflare Pages).
- **Text generation**: Aya-Expanse 8B via Ollama (Vertex AI/Gemini fallback).
- **Speech recognition**: Faster-Whisper.
- **TTS**: WAXAL-Piper Hausa model, 8 speakers (M1–M4, F1–F4), 73.5 MB ONNX at 22.05 kHz. Runs in the browser via ONNX Runtime Web/WASM, with server streaming as fallback. `backend/services/vits_engine.py` resamples to a 24 kHz PCM contract.
- **Hausa text normalisation**: lives in the shared `gyara` package (github.com/adab-tech/gyara), pinned by commit SHA in `backend/requirements.txt` and CI. Fix orthography bugs in gyara, not here; `backend/orthography.py` only re-exports it plus syllable/tone heuristics.
- **Training**: Modal scripts at the repo root (`finetune_piper_hausa_modal.py`, `finetune_mms_hausa_modal.py`, `segment_waxal_modal.py`, `train_modal.py`). Full write-up: `docs/waxal_piper_technical_report.md`.

## Hard performance rules

- TTS must stay real-time on CPU, and time to first audio must stay under 110 ms.
- Report inference timing before and after any change to inference, chunking or export.

## Voices

- Only two voices are public: **Malama Asabe** and **Malam Garba**. Always use these honorific forms.
- Frontend speaker IDs map to model speakers in `FRONTEND_TO_WAXAL_SPEAKER` (`backend/services/vits_engine.py`): 0–3 = M1–M4, 4–7 = F1–F4.
- **Malama Asabe = frontend 6 (F3), the default. Malam Garba = frontend 0 (M1).** See `App.tsx`, `components/Sidebar.tsx`, `backend/voice_preview.py`.
- Never expose the other six speakers in the UI, API, docs or examples.
- Piper shuffles indices: when labelling checkpoint output, use the model's own `speaker_id_map`, never sorted order.

## Hausa text rules (most important section)

The hooked consonants and the glottal stop are model symbols. Corrupting them silently breaks the voice.

- Never replace ɓ ɗ ƙ ƴ with b d k y, and never strip them.
- NFC normalisation is fine (the pipeline uses it). Never apply NFKD/NFD or "remove accents" helpers.
- Never "fix" Hausa spelling, and never add tone or vowel-length marks to input text.
- Read and write text files as UTF-8 explicitly (`encoding="utf-8"`); this repo is also used on Windows.

  | Lower | Code point | Upper | Code point |
  |---|---|---|---|
  | ɓ | U+0253 | Ɓ | U+0181 |
  | ɗ | U+0257 | Ɗ | U+018A |
  | ƙ | U+0199 | Ƙ | U+0198 |
  | ƴ | U+01B4 | Ƴ | U+01B3 |

- **Glottal stop: the model symbol is the ASCII apostrophe `'` (U+0027).** `clean_text()` in `finetune_piper_hausa_modal.py` maps curly quotes and backticks to it. The modifier letter `ʼ` (U+02BC) is not in the map and gets dropped there; it appears only in IPA output from `backend/services/phonetics_service.py` (e.g. ƙ → kʼ). Keep those two layers separate.

## Two symbol sets, do not mix them

- **Piper model (live):** 42 symbols, `HA_ALPHABET` in `finetune_piper_hausa_modal.py` (pad/bos/eos, space, punctuation, a–z core letters, ɓ ɗ ƙ ƴ, rare p q v x). Changing order or contents invalidates the trained checkpoint.
- **MMS-TTS (`facebook/mms-tts-hau`) work:** its own lowercase vocabulary, handled in `utils/prepare_waxal_mms.py`. MMS weights are CC BY-NC 4.0.
- Never edit, reorder or extend either symbol set without asking first.

## Commands

Frontend (repo root):
```bash
npm ci
npm run dev          # Vite dev server
npm run typecheck
npm run lint
npm run test         # Vitest
npm run test:e2e     # Playwright
npm run build
```

Backend (`backend/`):
```bash
pip install -r requirements.txt -r requirements-dev.txt
uvicorn main:app --reload
pytest -v            # CI requires coverage >= 60%
ruff check . && ruff format --check . && mypy .
```

Full stack: `docker compose up --build` (Ollama + backend + frontend, http://localhost:3000).

Training and evaluation (Modal):
```bash
.\utils\run_training.ps1                            # preflight -> Modal -> log -> diagnose
modal run finetune_piper_hausa_modal.py::evaluate   # audition a checkpoint
modal run --detach segment_waxal_modal.py           # corpus recovery
```

Hooked-letter smoke test (synthesises sentences stressing ɓ ɗ ƙ ƴ):
```bash
python utils/synth_hooked_letters.py <model_dir> <out_dir>
```

## Working rules for Claude

- Run the matching CI checks (frontend: typecheck, lint, test, build; backend: ruff, mypy, pytest) before calling a change done.
- After any change to text processing, inference or export, run the hooked-letter smoke test and report the output paths so a native speaker can listen. Passing unit tests is not enough for TTS.
- Ask before: changing symbol sets, retraining or overwriting checkpoints, changing the ONNX export, changing the public voice list, bumping the gyara SHA, editing deploy workflows, or deleting data or audio.
- Never commit model weights, raw audio, datasets, `.env` files or keys. Weights go to Hugging Face, not Git.
- Licensing: application code is MIT; the WAXAL-Piper weights are CC BY-NC-SA 4.0 (commercial voice use needs a written licence from hi@murya.ng). Never describe the weights as MIT, and never change licence terms in README, docs, metadata or the model card without asking.
- Claims: do not add new "first", "only" or "best" claims anywhere. The MOS listening study (app.murya.ng/listen) is still collecting ratings: never publish or invent a naturalness score.
- Repo skills: `.claude/skills/debug-audit` (full-stack bug pass) and `.claude/skills/premium-polish` (UI polish pass).
