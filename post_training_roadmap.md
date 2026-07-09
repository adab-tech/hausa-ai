# Hausa AI — Post-Training Roadmap

> [!IMPORTANT]
> **Superseded (2026-07-06).** The from-scratch VITS model this roadmap covers
> was retired after native-speaker evaluation. The production voice is now the
> **WAXAL–Piper grapheme-mode fine-tune** (`models/piper_hausa_waxal/`,
> 8 speakers). The v2 training run (2,693 utt / 6.03 h corpus) completed on
> Modal 2026-07-06 (app stopped cleanly, 0 tasks remaining); the final
> `model.onnx` / `model.onnx.json` was exported, swapped into
> `backend/services/vits_engine.py`, and verified end-to-end — 10 sample WAVs
> generated and reviewed. See `docs/waxal_piper_technical_report.md` for the
> full pipeline and `utils/run_training.ps1` for the current training
> entrypoint. Kept for historical reference.

Training on Modal is **complete**. Checkpoints live in Modal volume `hausa-ai-checkpoints` and locally under `models/vits/` (ONNX export done).

---

## Quick start (post-training)

```powershell
cd C:\Users\Adamu\hausa-ai\hausa-ai
pip install -r backend/requirements-inference.txt   # once
.\post_train.ps1
```

Or double-click `run_post_training.bat`.

---

## Phase 1: Model Evaluation & Validation ✅

| Step | Script | Output |
|---|---|---|
| Linguistic audit (hooks, tones, lexicon) | `sovereign_auditor.py` | Console score |
| VITS synthesis (hooks, tones, 3 speakers) | `test_custom_vits.py` | `output_tests/*.wav` |
| Plural/tone regression | `test_plurals_tone.py` | Console |

**Status:** Passing — benchmark WAVs regenerated in `output_tests/`.

---

## Phase 2: Model Optimization & Export ✅ (ONNX done)

| Asset | Path |
|---|---|
| ONNX model | `models/vits/best_model.onnx` (~130 MB) |
| Config | `models/vits/config.json` |
| PyTorch checkpoints (archive) | `models/waxal_hausa_vits_v1-June-05-2026_06+35AM-0000000/` |

**Pull latest from Modal (if needed):**

```bash
modal volume get hausa-ai-checkpoints waxal_hausa_vits_v1-June-05-2026_06+35AM-0000000/best_model.onnx models/vits/best_model.onnx
modal volume get hausa-ai-checkpoints waxal_hausa_vits_v1-June-05-2026_06+35AM-0000000/config.json models/vits/config.json
```

**Optional next:** INT8 quantization for faster CPU inference (current RTF ~0.5× on CPU — see `flywheel_optimizer.py`).

---

## Phase 3: Backend Integration ✅

Pipeline in `backend/routers/audio.py`:

`Raw text → orthography.normalize → apply_tonal_heuristics → VitsEngine.synthesize → PCM stream`

Fallback order: WAXAL sample match → **custom VITS** → Piper → WAXAL nearest sample.

Start backend:

```powershell
cd backend
pip install -r requirements.txt -r requirements-inference.txt
uvicorn main:app --reload --port 8000
```

---

## Phase 4: Frontend UI ✅

- **Murya** speaker dial (8 VITS speakers + Piper baseline)
- **Axiom Trace** panel (raw → normalized → tone-mapped)

Start frontend:

```powershell
npm install
npm run dev
```

Test live voice at `http://localhost:3000` with mic button.

---

## Recommended next steps (after validation)

1. **Listen** to `output_tests/` — confirm hooked letters and tone quality as a native speaker.
2. **Live voice smoke test** — backend + frontend, select Speaker 1–8, speak in Hausa.
3. **Quantize ONNX** (optional) — target RTF > 1.0 on CPU for real-time `/api/live`.
4. **Commit** `models/vits/best_model.onnx` via Git LFS when disk space allows (~15 GB free recommended).

---

## Post-Training Tasks / Next Steps (2026-07-06)

**Done this session:**
- v2 WAXAL–Piper training run completed on Modal; final model exported and
  swapped into `backend/services/vits_engine.py` as the active engine.
- 10 sample WAVs generated from the final model and reviewed.
- UI speaker dial renamed **Nexus → Murya**.
- Fabricated/unverified stats removed from docs (no invented MOS numbers,
  no invented epoch/step counts not pulled from source).
- `App.tsx` refactored (see git diff for scope).
- Several bugs fixed in the reliability pipeline and engine integration this
  session (see `docs/waxal_piper_technical_report.md` §4 for the taxonomy).

**Still open (genuinely not done — no numbers invented here):**
- **MOS evaluation** — the planned native-listener Mean Opinion Score study
  has not been run. No MOS numbers exist yet; any figure quoted elsewhere is
  a placeholder or aspirational target, not a result.
- **HF model card publishing** — `docs/hf_model_card.md` is drafted but the
  Hugging Face repo has not been confirmed as published/live; verify repo
  existence and upload status before citing a public URL.
- **Exact final epoch/step number for v2** — not yet pulled from
  `last.ckpt` in this session (Modal CLI was unavailable in the working
  shell; local disk also had only ~13 GB free). Pull via
  `modal volume get hausa-ai-checkpoints piper_hausa_waxal/last.ckpt` and
  inspect with `torch.load(..., map_location="cpu")["global_step"]` /
  `["epoch"]`, then delete the local copy — still an open action item.
- **Remaining deployment steps** — Fly.io (or equivalent) production deploy
  of the swapped-in model has not been confirmed complete; verify the live
  deployment serves the new ONNX artifact, not a stale cached one.
- **INT8 quantization** and **replication on a second language** remain
  future work, unchanged from §8 of the technical report.
