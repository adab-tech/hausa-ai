# Deployment

## Current state (updated: Fly.io is now the primary backend target)

Cloud Run pipeline still exists as a fallback (see below), but the active plan is:

- **Backend → Fly.io** (`fly.toml` in repo root, builds `backend/Dockerfile`).
- **Frontend → Vercel** (`vercel.json` in repo root).
- **Domain → `murya.ng`** (chosen over `.dev`/`hausa.ai` for cost + brand fit).

### To launch on Fly.io (run these yourself — first one needs your browser for OAuth)
```sh
flyctl auth login                       # interactive, opens browser — your account
flyctl volumes create hausa_ai_data --size 1 --region jnb   # persistent /app/data for feedback.jsonl + corrections.jsonl (jnb = Johannesburg, closest Fly region to West Africa)

# REQUIRED secrets (production won't boot without the first two — see Security below)
flyctl secrets set \
  REVIEWER_API_KEY="$(openssl rand -hex 24)" \
  ALLOWED_ORIGINS="https://murya.ng,https://www.murya.ng" \
  GEMINI_API_KEY=<your-gemini-key>
# ^ save the REVIEWER_API_KEY value somewhere safe — you (and anyone you delegate)
#   type it into the Corrections tab to approve model-affecting corrections.

flyctl deploy --remote-only   # build on Fly's builders, not your laptop
```
`--remote-only` matters here: the image bundles torch + the 73 MB model and is several GB — building it remotely avoids local Docker and local disk pressure entirely (your disk is near-full). It also means you don't need Docker installed locally.

`fly.toml` already sets `APP_ENV=production` and a `performance-2x` / 8GB machine (needed for the always-loaded Whisper/Piper/Ollama models — do not shrink this without testing, cold model loads will OOM on smaller machines).

If you don't have an Ollama-served model reachable from Fly, set `OLLAMA_HOST` to wherever you're running it, or rely on the Gemini fallback chain in `backend/routers/chat.py` (requires `GEMINI_API_KEY`).

### Security model (a public tool that learns from users)

The threat model here is specific: `murya.ng` is meant to be **open to real Hausa
speakers** (chat, TTS, and submitting feedback/corrections are public by design),
but the one action that changes the model — **approving a correction into the
system prompt** — must be locked down, or the learning loop becomes a poisoning
vector. So `backend/main.py::_validate_runtime_config` enforces, in production:

- **`REVIEWER_API_KEY` (required).** Gates `GET /api/corrections` and
  `POST /api/corrections/{id}/review` (via `X-Reviewer-Key`). Only you and your
  delegates know it; it is **never** shipped in the frontend bundle — it's typed
  into the Corrections tab at review time. Production refuses to boot without it.
- **`ALLOWED_ORIGINS` explicit (required).** Must not be `*`. Restricts CORS to
  your own frontend origins so other sites can't drive your backend from a
  browser. CORS `allow_headers` already includes `X-Reviewer-Key`.
- **`API_KEY` (optional).** Only for a *private/firewalled* deployment. Do **not**
  rely on it as a secret for the public app — a single-page frontend bundle would
  expose it. Public endpoints (chat/tts/feedback) stay open by design.
- **HTTPS** is forced by `fly.toml` (`force_https = true`).
- **Still open (not yet implemented):** request rate limiting on the public
  endpoints (recommended before heavy public traffic — e.g. slowapi, or Cloudflare
  in front); and per-private-mode frontend `X-API-Key` wiring (only needed if you
  choose `API_KEY` mode).

### Cloud Run (fallback, not currently used)
1. **CI** ([`.github/workflows/backend-ci.yml`](../.github/workflows/backend-ci.yml)) — lint, type-check, `pytest` with coverage. Runs on every push/PR to `main`.
2. **Deploy** ([`.github/workflows/deploy-cloud-run.yml`](../.github/workflows/deploy-cloud-run.yml)) — builds the same `backend/Dockerfile`, deploys to Cloud Run. Currently skipped (no `GCP_WIF_PROVIDER`/`GCP_SERVICE_ACCOUNT` secrets set) — leave it that way until/unless you want to switch back.
3. **Smoke test** ([`.github/workflows/post-deploy-smoke.yml`](../.github/workflows/post-deploy-smoke.yml)) — only fires after a successful Cloud Run deploy, so it's dormant too.

## Frontend (Vercel)

`vercel.json` auto-detects Vite, builds `dist/`. Set `VITE_BACKEND_URL` in Vercel's project env vars to your Fly.io app URL (e.g. `https://hausa-ai-backend.fly.dev`, or `https://murya.ng/api` once DNS is wired).

## Data / storage

**Feedback (`backend/data/feedback.jsonl`) → Supabase, when you outgrow the flat file.** You already have a Supabase account. Migrate `POST /api/feedback` to insert into a Postgres table instead of appending JSONL once you want real queries (trends over time, filtering by category) or a `community_corrections` table for the retraining feedback loop. The JSONL file works fine at current volume — no rush.

**WAXAL audio corpus** currently served from local disk (`backend/routers/waxal.py`). If it outgrows the container image, Supabase Storage or Cloudflare R2 (S3-compatible, no egress fees) are both reasonable homes.

**TTS model artifact.** `models/piper_hausa_waxal/model.onnx` (~73 MB) is **baked into the Docker image** (`backend/Dockerfile`), and `VITS_MODEL_DIR=/app/models/piper_hausa_waxal` points the engine at it. The model is **not git-tracked**, so:
- **Local `flyctl deploy`** (from your laptop) works — the file is in the build context. ✅
- **CI builds** (Cloud Run via GitHub Actions, which `git checkout`s) would fail the `COPY` — the model isn't in the repo. Fix before using CI: add it via **Git LFS** (`git lfs track "*.onnx"; git add models/piper_hausa_waxal/model.onnx`) or pull it into the build in the workflow. Not needed for the Fly path.

## DNS / domain

You have a Cloudflare account — put it in front of Vercel (frontend) as DNS, regardless of which registrar you buy the domain from (Namecheap, name.com, GoDaddy all work fine; Cloudflare doesn't need to be the registrar to manage DNS).
