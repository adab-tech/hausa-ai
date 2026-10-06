# Murya — Sovereignty Plan: host it and build it ourselves

_Goal: Murya runs on infrastructure we choose and on models we trained, with no
single vendor (cloud, model API or dev tool) able to switch it off._

Status legend: ✅ done · 🟡 started · ❌ not started. Prices and licences below
are **unverified planning figures** — check each before committing money.

## 1. Where the dependencies actually are

Murya has **no runtime dependency on Claude/Anthropic**: nothing in `backend/`,
`services/` or the frontend calls an Anthropic API. (`.claude/` holds dev-tool
config only; the build ignores it.) The real dependencies:

| Area | Today | Lock-in |
|---|---|---|
| Hosting | One Azure VM (`murya-vm`), Docker + Caddy + systemd | Operational only — no Azure SDKs in code |
| Chat / document / voice LLM | Cerebras `gemma-4-31b` → Groq → Ollama → Gemini | Paid API; model not Hausa-native |
| Speech-to-text | Cloudflare Workers AI Whisper (local faster-whisper fallback) | Free tier |
| TTS, VAD, dictionary | Local (WAXAL-Piper, Silero, Robinson/Wiktionary/Newman) | ✅ already ours |
| Images | Gemini Imagen | Paid API, non-core |
| Search | Tavily / You.com | Optional |
| Training compute | Modal (scripts are Modal-specific) | Convenience, replaceable |
| State | SQLite files on one VM | Single point of failure |

## 2. What "from scratch" means here

Pretraining an LLM from random weights needs billions of clean tokens; our
Hausa corpus is megabytes (`data/processed/`). The credible route to *our own
weights*: permissively-licensed open base → **continued pretraining** on a large
licensed Hausa corpus → **instruction tuning** → serve it ourselves. The voice
already follows this recipe (WAXAL-Piper).

## 3. Phases

### Phase 1 — Portability (weeks 1–2)
- ✅ **Provider seam for a self-hosted model.** `services/own_llm_service.py`
  speaks the OpenAI-compatible protocol (vLLM, llama.cpp server, TGI, any
  vendor). Set `MURYA_LLM_BASE_URL` + `MURYA_LLM_MODEL` (+ optional
  `MURYA_LLM_API_KEY`) and it becomes the **first** step in `/api/chat`,
  `/api/document` and live voice; Cerebras/Groq/Ollama/Gemini become fallback.
  Unset = chain unchanged.
- ✅ **Host-independent deploy script.** `deploy/murya-deploy.sh` reads
  `/etc/murya/deploy.env` instead of hardcoding user/path/URL.
- ❌ **Move off Azure.** Provision any VPS/bare-metal (Lagos or Johannesburg
  for latency to users; EU hosts are cheaper), copy the SQLite data dir, point
  DNS (Cloudflare) at it.
- ❌ **Fix the build-from-clean gap.** `model.onnx` (~73 MB) and
  `silero_vad.onnx` are not in git (`backend/Dockerfile` notes this). Publish
  them as release assets or Git LFS so a fresh server can build without a
  hand-copied file.
- ❌ **Verify `.github/workflows/deploy-cloud-run.yml`** — possible second GCP
  coupling; not reviewed.
- ❌ **Backups.** Nightly encrypted copy of the data dir to storage we control.
- ❌ **Provider-agnostic training scripts** (plain Docker/`torchrun`; Modal as one
  launcher). Today's `finetune_*_modal.py` only run on Modal.
- ❌ **Collapse the three duplicated provider chains** (`chat.py`,
  `document.py`, `audio.py`) into one. Deferred deliberately: the existing tests
  patch the per-provider functions by name, so it deserves its own change.

### Phase 2 — Data and evaluation (weeks 2–8)
- ❌ Licensed corpus pipeline (record licence + source per document). Candidates
  to check: Common Voice / WAXAL text, MADLAD / OSCAR / CC-100 Hausa slices,
  Masakhane datasets, Wikipedia, news archives where licensing allows.
- ❌ Native-speaker prompt/answer set (smallest, highest value).
- ❌ Held-out Hausa QA + no-fabrication evaluation set we own. Without it we
  cannot tell whether a new model beats the hosted one.
- ❌ Benchmark candidate bases **on Hausa** before choosing.

### Phase 3 — Our model (months 2–4)
- ❌ Continued pretraining + instruction tune (LoRA experiments first). Choose
  the base on licence + measured Hausa quality. Note
  `docs/murya_roadmap.md` lists Gemma/Aya/Llama while
  `finetune_llm_modal.py` trains Qwen2.5-7B — reconcile. Verify licences:
  Aya Expanse is, to my recollection, non-commercial (would block a
  commercial product); Qwen2.5-7B is, to my recollection, Apache-2.0.
- ❌ Own STT: fine-tune Whisper/MMS on Hausa (`finetune_mms_hausa_modal.py`
  exists).
- ❌ Release gate: evaluation set **and** the owner's ear (existing principle).

### Phase 4 — Serve it ourselves (month 4+)
- ❌ GPU box running vLLM/llama.cpp behind the Phase 1 seam; hosted APIs stay
  as burst/fallback, then are retired one by one.
- ❌ Decide images (drop, or self-host FLUX) and search (optional, or SearXNG).

## 4. Decisions still open
1. **Base model** (licence + Hausa quality).
2. **Own hardware vs rented bare-metal GPU.** Rent first; owning in-country adds
   power/import/cooling problems.
3. **Funding.** A 24/7 GPU likely costs more than Cerebras PayGo until traffic is
   well past ~1,000 visitors/day (see `capacity_and_cost.md`); the model/STT
   training itself is rough low-thousands of dollars. Both fit
   `startup_and_funding_roadmap.md`.

## 5. Switching on a self-hosted model

```bash
# On the GPU box (example)
vllm serve <your-model> --port 8000 --api-key <token>

# On the Murya backend (env)
MURYA_LLM_BASE_URL=http://<gpu-box>:8000/v1
MURYA_LLM_MODEL=<your-model>
MURYA_LLM_API_KEY=<token>
```

Remove the three variables to return to the hosted chain. Put the GPU box on a
private network (WireGuard/VPC) — do not expose an unauthenticated inference
port to the internet.
