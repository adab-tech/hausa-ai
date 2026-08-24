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
# ^ REVIEWER_API_KEY is a one-time BOOTSTRAP credential: on first boot it seeds
#   a single admin account (username "adamu", password = this value) in
#   admin.db. Log in at /admin/login with it once, then treat the value as
#   burned — it plays no further role after the account exists. See
#   backend/admin_store.py.

flyctl deploy --remote-only   # build on Fly's builders, not your laptop
```
`--remote-only` matters here: the image bundles torch + the 73 MB model and is several GB — building it remotely avoids local Docker and local disk pressure entirely (your disk is near-full). It also means you don't need Docker installed locally.

`fly.toml` already sets `APP_ENV=production` and a `performance-2x` / 8GB machine (needed for the always-loaded Whisper/Piper/Ollama models — do not shrink this without testing, cold model loads will OOM on smaller machines).

**Ollama runs inside the same container** (`backend/start.sh`, installed in the
Dockerfile via `curl -fsSL https://ollama.com/install.sh | sh`) — it is NOT a
separate service. `OLLAMA_HOST=http://localhost:11434` in `fly.toml` only
works because `start.sh` boots `ollama serve` before `uvicorn`. The model
(`OLLAMA_MODEL`, default `aya-expanse:8b`) is pulled at container boot into
`OLLAMA_MODELS=/app/data/ollama-models` — the persistent volume — so only the
very first boot pays the multi-GB download cost; redeploys reuse the cached
model. FastAPI starts immediately without waiting for the pull to finish, so
`/health` passes fast; chat requests fall back to Gemini/the static template
(`backend/routers/fallback.py`) until the first pull completes.

**Known constraint, not yet load-tested:** an 8B model on CPU-only (no GPU on
this machine) sharing 8GB RAM with Whisper + Piper/VITS is genuinely tight.
Expect slow (possibly 15-40s+) chat replies, and watch for OOM under real
concurrent traffic (a live voice call runs STT + LLM + TTS at once). If this
turns out to be too slow/unstable, the options are: a smaller Ollama model
(faster/lighter, unverified for Hausa quality), a separate dedicated Fly
machine for Ollama, or re-enabling the Gemini fallback (requires
`GEMINI_API_KEY`, real per-token cost — was intentionally skipped for now).

### Security model (a public tool that learns from users)

The threat model here is specific: `murya.ng` is meant to be **open to real Hausa
speakers** (chat, TTS, and submitting feedback/corrections are public by design),
but the one action that changes the model — **approving a correction into the
system prompt** — must be locked down, or the learning loop becomes a poisoning
vector. So `backend/main.py::_validate_runtime_config` enforces, in production:

- **Real admin accounts + sessions (required).** `GET /api/corrections` and
  `POST /api/corrections/{id}/review` are gated by `verify_admin_session`
  (`backend/auth.py`), backed by `admin_store.py` — a SQLite table of admin
  accounts (bcrypt-hashed passwords) and sessions, on the same persistent
  volume as `feedback.jsonl`/`corrections.jsonl`. Login happens at
  `/admin/login`, which sets an HttpOnly, Secure session cookie; the
  credential never touches frontend JS, unlike the old shared
  `REVIEWER_API_KEY`-in-sessionStorage pattern this replaced. Approvals now
  carry a real `reviewedBy` identity in `corrections.jsonl`. To add a
  delegate reviewer today, call `admin_store.create_admin(username,
  password)` once (no UI for this yet — a fair next step if you delegate to
  more than one or two people).
- **`REVIEWER_API_KEY` (required at boot).** Bootstrap-only now — seeds the
  first admin account on first boot if none exist. Production still refuses
  to boot without it (otherwise there's no way to log in at all on a fresh
  deploy), but it's not checked on every request anymore.
- **`ALLOWED_ORIGINS` explicit (required).** Must not be `*`. Restricts CORS to
  your own frontend origins so other sites can't drive your backend from a
  browser — this also matters for the session cookie, which is `SameSite=None`
  in production (the frontend and backend are on different domains) and
  therefore relies on `allow_credentials=True` + an explicit origin list.
- **`API_KEY` (optional).** Only for a *private/firewalled* deployment. Do **not**
  rely on it as a secret for the public app — a single-page frontend bundle would
  expose it. Public endpoints (chat/tts/feedback) stay open by design.
  `/api/live` (a WebSocket) can't use the `X-API-Key` header every other
  endpoint uses — browsers can't set custom headers on a WebSocket handshake
  at all — so a query param is the only place *something* can travel. Fixed
  2026-08-23 (`docs/security_architecture_review_2026-08-23.md` finding #5):
  rather than the standing key itself, the frontend calls
  `POST /api/live/ticket` (header-authenticated, same as every other
  endpoint) and gets back a random, single-use, 30-second ticket
  (`auth.issue_live_ticket`/`consume_live_ticket`) — `?ticket=<ticket>`
  is what actually appears in the WS URL/access logs, and it's already
  worthless a few seconds (or one connection) after being issued. No-op
  when `API_KEY` isn't configured — the public default deployment never
  calls the ticket endpoint at all, so this adds zero latency to the common
  case. A private deployment enables the flow by setting `VITE_API_KEY` at
  frontend build time (matching the value of the backend's `API_KEY`).
- **HTTPS** is forced by Caddy's automatic HTTPS (production) / `fly.toml`'s
  `force_https = true` (if ever redeployed to Fly). Caddy also sends HSTS
  and a strict CSP on the API domain (`deploy/Caddyfile`, a reference copy
  of the live config on the VM) — added 2026-08-23 after a live `curl`
  check found both missing.
- **Rate limiting** on public endpoints via slowapi (`backend/rate_limit.py`),
  in-memory/per-process — correct for the current single-machine deployment,
  not multi-instance safe. Two stacked limiters: `limiter`, keyed on the
  anonymous per-device `X-Contributor-Id` token (falls back to IP) —
  deliberately NOT per-IP-only, since carrier-grade NAT across the Sahel
  means many real users share one public IP; and `ip_limiter`, a second,
  genuinely per-IP (`get_remote_address`) ceiling stacked alongside it on
  every endpoint that reaches a paid third-party API or otherwise-expensive
  compute (chat, document translate/summarize, TTS, image/video generation,
  admin login) — set to a generous multiple of the per-device limit
  everywhere except admin-login (one legitimate caller, so a strict cap has
  no fairness cost) specifically to close the "rotate a fresh device token
  every request" bypass the single device-keyed limiter alone can't stop.
  Chat 20/min per-device + 100/min per-IP, document 10/min + 50/min, TTS
  20/min + 100/min, image/video generation 5/min + 30/min, feedback 30/min
  (no IP ceiling — free, not a cost/abuse vector), admin login 10/min +
  10/min (brute-force protection, strict on both).
- **Live-voice connection caps** (`backend/routers/audio.py`): per-IP (2
  concurrent, `MAX_LIVE_CONNECTIONS_PER_IP`) and process-wide (40 concurrent,
  `MAX_LIVE_CONNECTIONS_TOTAL`) — the per-IP cap alone doesn't stop a
  distributed attacker opening a couple of connections from each of many
  source IPs, since each `/api/live` connection runs a genuinely expensive
  Whisper+LLM+VITS pipeline on the single CPU-only VM.
- **Still open (not yet implemented):** `/api/live`'s private-mode auth is
  wired end to end (`VITE_API_KEY` → ticket exchange, see above), but the
  equivalent `X-API-Key` header wiring for `/api/chat`/`/api/document`/
  `/api/tts` in private mode is not — those calls don't currently send
  `VITE_API_KEY` at all, so a private deployment would need to add that
  itself for now. Also still open: an admin UI for creating/removing
  delegate reviewer accounts (currently a one-off Python call).

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
