# Changelog — Murya (Sovereign Hausa AI)

All notable changes to the backend and frontend. Newest first. Dates are the
day the change went live in production (backend on the self-hosted Azure VM
as of 2026-08-22 / Vercel `app.murya.ng`).

## 2026-08-31 (latest)

### Added — MOS listening test (TTS naturalness eval)
- New human-in-the-loop eval gate before a voice checkpoint or correction
  batch feeds the next retrain, mirroring the pronunciation-correction
  loop's storage/auth patterns exactly. Full writeup:
  `docs/mos_listening_test.md`.
- Backend: `backend/mos_store.py` (SQLite: stimuli, ratings, and an explicit
  `mos_decisions` table for the admin's auditable sign-off),
  `backend/routers/mos.py` (public session/audio/submit, admin
  results/export/decision), `backend/seed_mos_stimuli.py` (self-seeds 64
  Murya clips across all 8 production voices + 2 real WAXAL human
  recordings as ground truth, baked into the Docker image at
  `data/mos_ground_truth/`).
- Frontend: public `app.murya.ng/listen` ([components/MosListen.tsx](../components/MosListen.tsx)),
  a new **Kimanta Murya** admin dashboard tab
  ([components/MosReview.tsx](../components/MosReview.tsx)) with a synthesized
  headline verdict (not just raw numbers) and the three-way decision record,
  and a one-time in-app nudge toward the test after a couple of TTS plays
  ([components/MosPrompt.tsx](../components/MosPrompt.tsx)).
- New backend dependency: `soundfile` (decodes the known-format ground-truth
  WAV files directly via libsndfile — already installed system-wide — no
  ffmpeg/ffprobe subprocess needed for a format already known exactly).
- Verified end-to-end for real: a full 20-clip session run through the
  actual browser against the actual backend, real audio played, real
  submission landed in SQLite, real aggregation returned. Full backend
  suite: 336 passed, 1 skipped.

### Fixed — rate limiter could crash a request instead of returning a normal response
- `backend/rate_limit.py`'s `ip_limiter` used slowapi's bare
  `get_remote_address`, and the (separate) primary `limiter`'s IP fallback
  path did too — found while testing the MOS feature, when `/api/admin/login`
  (the only route stacking both limiters, and the only login path into the
  admin dashboard) failed with an opaque, unlogged connection error from a
  client whose request never populated `request.client`. Added
  `_safe_get_remote_address`, used by both limiters, so a missing
  `request.client` falls back to a fixed key instead of ever raising.
  Regression tests in `backend/tests/test_rate_limiting.py`.

## 2026-08-23

### Fixed — Live voice: self-echo and the wrong-transcription bug behind it
- **Root cause found in three layers, not one.** Reported live: "the app is
  listening to itself." Layer 1 — the client already muted the mic during TTS
  playback, but the server had no matching awareness, so any leaked audio got
  transcribed as a real user turn. Added an explicit `assistant_speaking`
  control message the server uses to drop audio outright while the reply is
  playing, with a 15s safety valve (`ASSISTANT_SPEAKING_MAX_S`) in case the
  message itself is lost. `backend/routers/audio.py` (`live_endpoint`),
  `services/localService.ts` (`setAssistantSpeaking`), `App.tsx`.
- Layer 2 — the fix above still left a gap: a partial pre-reply audio
  fragment sat frozen through the whole muted window, then got glued onto
  the front of the next post-reply chunk once unmuted. One Whisper call
  transcribing part-stale, part-fresh audio in a single buffer — the exact
  shape of "wrong transcriptions of what was said before." Fixed by clearing
  `pcm_buffer` on the mute rising edge, not just gating new bytes.
- Layer 3 (code review) — a deep review of the whole VAD rebuild (below)
  found the same class of bug one level deeper: `pre_roll` was spliced into
  a new turn but never cleared, so a rapid retrigger (continuous speech past
  `MAX_TURN_SECONDS`) could still stitch stale audio onto a fresh turn.
  Fixed by clearing `pre_roll` the instant it's consumed at trigger time.
  Also found and fixed: the `assistant_speaking` safety valve only
  re-evaluated itself when new audio bytes arrived, so a client that also
  stopped sending bytes entirely (a stalled `AudioContext`) would never
  self-heal — moved the check to run on every loop tick.
- Regression tests for all three layers in `backend/tests/test_audio.py`,
  including one proven to fail without the fix and pass with it
  (temporarily reverted the fix, reran, confirmed the failure, restored).
  Full suite: 209 passed.

### Added — Real VAD-based turn detection on `/api/live`
- Replaced the fixed ~2-second chunking that transcribed audio the instant a
  timer elapsed — regardless of whether the user had actually finished a
  sentence — with silence-triggered, variable-length turn detection using
  Silero VAD (the founder's own fork, `github.com/adab-tech/silero-vad`).
  Reimplemented the streaming inference loop in plain numpy + onnxruntime
  rather than pulling in the reference wrapper's torch dependency — this
  backend has a deliberate, documented history of staying off torch/
  transformers/diffusers to keep the image lean (`faster-whisper` runs on
  CTranslate2 for the same reason). `backend/services/vad_service.py` (new),
  `models/silero_vad/silero_vad.onnx` (~2 MB, gitignored like the Piper
  model, vendored directly onto the Azure VM to match how that one's
  already handled there).
- Tuning: 0.5/0.35 speech/silence hysteresis thresholds (avoids flapping on
  borderline-probability frames), 700ms trailing silence to close a turn
  (upper end of the 600–700ms range production voice agents typically use —
  chosen deliberately generous since the reported failure mode was being
  cut off mid-thought, not latency), 250ms minimum confirmed speech to
  count as a real utterance (discards coughs/mic bumps), 300ms pre-roll
  lookback spliced onto every triggered turn so VAD's onset lag stops
  clipping the first syllable, 25s forced-cut safety cap. All six constants
  env-overridable without a redeploy (`VAD_SPEECH_THRESHOLD`,
  `VAD_SILENCE_THRESHOLD`, `VAD_TRAILING_SILENCE_MS`, `VAD_MIN_SPEECH_MS`,
  `VAD_PRE_ROLL_MS`, `MAX_TURN_SECONDS`).
- Falls back to the old fixed-chunking path with a logged warning if the
  VAD model fails to load, rather than going silent.

### Added — Whisper `initial_prompt` hinting for Hausa STT
- Both STT paths (Cloudflare's hosted `whisper-large-v3-turbo` and local
  `faster-whisper`) now prime the decoder with a natural, correctly-spelled
  Hausa sentence carrying all four hooked consonants (ɗ ɓ ƙ ƴ) —
  `_HAUSA_WHISPER_PROMPT` in `backend/routers/audio.py`
  (env-overridable via `WHISPER_INITIAL_PROMPT`). Verified `initial_prompt`
  is a real documented input field on Cloudflare's model before writing any
  code, and verified live against the real API post-deploy. Also added
  `vad_filter: true` to the Cloudflare payload for parity with the local
  path, which wasn't getting it before. `backend/services/cloudflare_stt_service.py`.
- **Known limitation, not fixed by this:** Whisper has no tonal modeling at
  all, and Hausa is tonal. Prompt-hinting improves vocabulary/orthography
  recognition; it cannot close that gap. Real fix needs fine-tuning an ASR
  model on an annotated Hausa speech corpus — tracked as a named future
  goal, not solved here.

### Changed — Client-facing UI simplification, round 2
- Removed the live-scrolling transcript display from the live-voice call
  panel (`components/LiveCallPanel.tsx`) — conversation still lands in main
  chat history via `setMessages`, but the in-call overlay is audio-first
  now, no live text. Rationale: model correctly understanding what was said
  matters more than displaying a perfect live transcript.
- Removed the "Linguistic Scan" label and the English jargon parentheticals
  — `(Deep Thinking)`, `(Linguistic Analysis)`, `(Proverb Engine)`,
  `Litvinova's Tonal Laws`, a raw `sakan 20-25` estimate — from all 8
  rotating thinking-state phrases in `components/MessageItem.tsx`
  (`AXIOM_PHRASES`). Found only after an initial pass mistakenly checked
  for the wrong string (the already-removed trace panel) instead of this.
- Reverted the auto light theme (`prefers-color-scheme`-driven) added
  earlier the same day — read as too washed-out/blurry on an actual
  light-OS device. Murya is single-theme dark again; the CSS variable
  architecture bug found while building the light theme (Tailwind's
  `@theme` maps its `--color-dyn-*` tokens to `var(--bg-primary)` once, at
  `:root` — any override scoped to a nested element never reaches the
  Tailwind utilities that actually paint the UI, since custom-property
  inheritance passes down the already-resolved value) is documented in
  `index.css` for whenever this is revisited.
- "Fasahar Hausa" header mark: two iterations. First shipped as text + a
  separate octagon/diamond SVG icon; corrected per direct feedback to drop
  the icon entirely and mint the *text itself* — a corner-cut ("stamped
  seal") clip-path badge directly on the uppercase tracked-out type, no
  icon. `App.tsx`.
- Moved the Saurara (listen) button from the left to the right side of the
  message footer, next to the thumbs up/down controls; dropped the
  all-caps/`font-black`/`tracking-wider` "block lettering" treatment on it
  and the linguistic-trace toggle in favor of plain sentence case.
  `components/MessageItem.tsx`.

## 2026-08-22

### Infrastructure — Backend moved off Fly.io onto a self-hosted Azure VM
- Fly.io's billing lock (overdue invoices) stopped new deploys mid-session.
  Stood up `murya-vm` (Standard_B2as_v2, Canada Central): Docker container
  `murya-backend` behind Caddy for automatic Let's Encrypt HTTPS, systemd
  service `murya.service`. Deploy is manual SSH: `git pull` from repo root
  (Dockerfile COPY paths are repo-root-relative) → `docker build -f
  backend/Dockerfile -t murya-backend:latest .` → `systemctl restart
  murya.service`. Chose unproxied (grey-cloud) Cloudflare DNS + Caddy's own
  cert issuance over fighting Cloudflare origin-port proxying after hitting
  a 521 with default proxied DNS.
- `api.murya.ng` replaced the ad-hoc `api-backup.murya.ng` name everywhere
  user-facing: DNS record added, Caddy site block extended, Vercel's
  `VITE_BACKEND_URL` repointed and rebuilt — confirmed by grepping the live
  production JS bundle for the old name and finding zero occurrences.
  `api-backup.murya.ng` is still alive (same server) but referenced nowhere
  in the shipped app; not yet torn down.
- The backend Docker image used to also build and bundle a full frontend
  copy (`COPY --from=frontend-builder /build/dist ./dist`), served at `/`
  as a leftover from an earlier single-container setup — meant `api.murya.ng`
  showed a second, stale copy of the app. Removed the frontend-build stage
  from `backend/Dockerfile` entirely; the backend now redirects a bare `/`
  visit to the real `app.murya.ng` (`FRONTEND_DEV_URL` env var, defaults to
  `http://localhost:3000` for local dev) and otherwise answers as a pure API.

### Fixed — Critical: dictionary sources never loaded in production
- Fly's persistent volume mounted at `/app/data` and silently shadowed
  everything baked into that path at build time — `dictionary_service`'s
  `dictionary_ready()` had been `False` in every prior production deploy.
  Moved all three dictionary sources to `/app/dictionaries` (outside the
  volume mount) in both `backend/Dockerfile` and
  `backend/services/dictionary_service.py`.
- `/api/document` (Fassara & Takaitawa) had zero fallback chain — only ever
  called Cerebras, so it went fully dark whenever Cerebras was down.
  Rewrote to loop through the same provider chain as chat.
  `backend/routers/document.py`.
- Added Groq (`openai/gpt-oss-120b` — corrected after the first choice,
  `llama-3.3-70b-versatile`, turned out to no longer exist) as a real, free
  fallback step ahead of the proven-dead Ollama step, independently in all
  three places that had their own copy of the fallback chain:
  `routers/chat.py` (`stream_groq`), `routers/document.py`, and
  `routers/audio.py` (`_llm_respond_groq`, live voice).
- `_needs_live_search()` never triggered on Hausa "who is" questions
  ("Wanene shugaban Najeriya?") — a real hallucination-risk gap, not just a
  missed feature. Added `wanene`, `wa ne`, `wace ce`, `su wanene`, `su wane
  ne` (Hausa) and `who is`, `who are the` (English) to `_LIVE_SEARCH_CUES`.
- Dictionary lookup regex captured "kalmar" (Hausa for "word") itself as
  the search term for phrasings like "ma'anar kalmar ƙasa" instead of the
  actual target word. Fixed with an optional filler-word group in
  `_DEFINE_RE`.
- Live-voice STT offloaded to Cloudflare Workers AI
  (`@cf/openai/whisper-large-v3-turbo`) as the primary path, relieving the
  RAM/CPU pressure shared with Ollama/Piper on the box — local
  `faster-whisper` remains the automatic fallback on any Cloudflare
  failure or when unconfigured. `backend/services/cloudflare_stt_service.py`.

### Added — Newman (1977) dictionary corpus wired in as a third HA→EN source
- Merged into `dictionary_service` alongside Robinson (1914, public domain)
  and Wiktionary (CC-BY-SA), ranked ahead of Wiktionary for HA→EN. Bringing
  the combined corpus to 30,708 entries. Ingestion approved directly by
  Prof. Paul Newman via email (2026-08-21/22). One entry (*màbàrci*, p. 98)
  flagged reviewer-questioned; the flag carries through the merge.
- Made the dictionary a standalone feature instead of only reachable via a
  hidden chat-message trigger: `GET /api/dictionary?q=` (public,
  rate-limited 30/min, `backend/routers/dictionary.py`), full-screen
  **Ƙamus** search modal (`components/DictionarySearch.tsx`) wired into the
  sidebar. ("Ƙamus" with the hooked ƙ — corrected from an initial "Kamus.")

### Changed — Client-facing product simplification
- Voice selection limited to two featured voices for now — the rest held
  back as a real reason to sign in later, not a technical constraint.
  After listening through all 8 WAXAL samples: **Malama Asabe** (voice 6)
  is the new default, **Malam Garba** (voice 0) second.
  `components/Sidebar.tsx` (`FEATURED_VOICES`), `App.tsx`.
- Retired the "Sovereign Vibe / Protocol" picker (Classic/Royal/Cyberpunk/
  Academic) entirely from the client UI, including the header mode badge —
  English-named theme switching doesn't fit a Hausa-first product. Classic
  and Royal blended into the one permanent look (`index.css` `:root`/
  `.vibe-classic`); the full vibe system (CSS + `SovereignVibe` type) stays
  defined for `AdminPanel.tsx` (already hardcodes `vibe-classic`
  independently) or a future context where naming a mode is useful.
- Removed the client-facing linguistic-trace toggle (the per-message
  normalization/tone breakdown panel) and the Model Tier / Autonomy Level /
  raw server-hostname stats from the sidebar footer — none of it serves an
  end user. `MessageItem.tsx`'s `allowTrace` prop still exists (defaults
  false, unused by `App.tsx` now) so the panel can be wired into an
  admin/research view later without rebuilding it.
- Fixed a real, separate bug found while removing the above: the sidebar
  `<aside>` had no scroll container (`overflow-y: visible`, fixed
  `top-0`/`bottom-0`), so on any viewport shorter than its content,
  everything below "Learning Mode" — Ƙamus, White Paper, Clear Chat — was
  clipped and unclickable. Added `overflow-y-auto`.
- Landing page (`landing/index.html`): CTA moved into a sticky top-right
  header, duplicate bottom CTA removed, LinkedIn (vanity URL
  `linkedin.com/company/murya-voice`) and real GitHub SVG icons added to
  the footer credit line, "ADAB-TECH" renamed to "Adab Tech."

## 2026-08-21 — resumed active work this day (Friday)

### Added — free scheduled uptime monitor
- Backend/app/landing + TTS pipeline smoke check on a schedule.

### Newman (1977) dictionary — APPROVED
- Prof. Paul Newman approved ingestion directly via email; he also flagged
  a better-fit 2020/2022 BUK bidirectional edition worth recording for a
  possible future re-ingestion. Actual ingestion into `dictionary_service`
  landed the next day (see 2026-08-22 above).

### Tried and reverted — deep-research feature
- Built out a full research pipeline in one evening: Tavily
  Extract/Crawl/Map/Research SDK integration, a Hausa Wikipedia corpus
  builder scaled to 95 real articles (1.66M chars, with a Talk-namespace
  filter fix), You.com as a second search-grounding fallback behind
  Tavily, a fix for stale answers winning over fresh ones (Tavily
  `advanced` search depth), and a `DeepResearch` UI wired into the
  sidebar. Discontinued the following morning (2026-08-22 05:40) in the
  same pass that fixed the chat fallback-chain bugs it had surfaced — kept
  the underlying fallback-chain fixes, dropped the feature itself.
  `docs/capacity_and_cost.md` corrected at the time to reflect Cerebras'
  end of free tier.

---

## 2026-07-13

### Added — Clean Hausa→English dictionary (open-licensed) + source credits
- The dictionary/translation tool now loads a second, openly-licensed lexicon
  alongside Robinson (1914): **Hausa Wiktionary** entries (CC-BY-SA 4.0) via
  Kaikki.org — 2,187 headwords → 2,580 HA→EN pairs. This fixes the long-standing
  rough **Hausa→English** direction: results are ranked so each source answers in
  the direction it's authoritative for (e.g. `ruwa` → *water*, `ƙasa` →
  *soil, earth*, `yaro` → *boy, child* — no more Robinson reverse-lookup noise).
  `data/sources/wiktionary-hausa/`, `utils/build_hausa_en_open.py`,
  `backend/services/dictionary_service.py` (dual-source loader + quality ranking).
- **Paul Newman & Roxana Ma Newman** credited for their foundational Hausa
  lexicography (Modern Hausa–English Dictionary, 1977; A Hausa–English Dictionary,
  Yale 2007). These are **in copyright and deliberately NOT ingested** — a full
  attribution + not-licensed status is recorded in
  `data/sources/newman-dictionary/ATTRIBUTION.md`, with a ready-to-send licensing
  request in `docs/newman_permission_requests.md`. Credit is given; ingestion
  waits on a licence.

## 2026-07-12 (earlier)

### Added — Document Translate & Summarize (Fassara & Takaitawa)
- A **Fassara & Takaitawa** tool (sidebar) for one-shot translate/summarize of
  pasted text up to ~30,000 chars, on the free Cerebras path (131k context).
  Four actions: translate → English / → Hausa, summarize in Hausa / English;
  streamed result + copy. `POST /api/document {text, action, target}`
  (`routers/document.py`), `DocumentTool` modal, `streamDocument()` service.
  Live-verified both translation directions + Hausa summarization. Step 2 of
  the feature roadmap.

### Added — Hausa Tutor Mode (Malamin Hausa)
- A **Learning Mode** that turns Murya into a patient Hausa teacher: teaches the
  Hausa language (for diaspora/kids/new speakers) or explains any subject in
  simple Hausa. Method: one idea at a time, example + practice question, each
  word given with English gloss + example sentence (hooked letters intact),
  encouragement, and a nudge to tap **Saurara** to hear pronunciation. It
  inherits every existing capability (dictionary, calculator, gendered address,
  TTS) automatically. `mode` field on `POST /api/chat` (`assistant`|`tutor`);
  **Yanayin Koyo / Learning** switch in the sidebar. Cache key includes `mode`.
  First of the planned feature roadmap (see below). Live-verified.

## 2026-07-12 (later)

### Added — Admin visitor analytics (Ziyara)
- Privacy-preserving analytics in the admin dashboard: total visits, unique
  devices (today / 7d / all-time), a 14-day daily-visits chart, geography **by
  browser timezone** (no IP stored, no geoip dependency), and browser-language
  breakdown. `backend/analytics_store.py`, `backend/routers/analytics.py`
  (`POST /api/analytics/visit` public beacon + admin-gated
  `GET /api/admin/analytics`), and the **Ziyara** tab in `NeuralReview`.
  Uniqueness uses the existing anonymous `X-Contributor-Id` device token.
- `docs/capacity_and_cost.md` — capacity/token estimates (text scales via
  Cerebras; voice is the CPU-bound limiter on the single box; ~2.7k–3.8k tokens
  per exchange; the ~1,600-token system prompt is the main cost lever).

## 2026-07-12

### Added — LLM tools & knowledge
- **Calculator**: exact arithmetic (safe AST evaluator, never `eval`), including
  percent-of ("15% na 2000" = 300). `backend/services/calc_service.py`.
- **Prayer times (Salla)**: pure-offline astronomical computation (PrayTimes.org
  method, Muslim World League 18°/17°) for 12 Nigerian cities or any lat/long.
  `backend/services/prayer_service.py`.
- **Dictionary / translation**: Hausa⇄English from the Robinson (1914) lexicon
  (20,628 pairs), diacritic-folded lookup, provenance cited, OCR-noise filtered.
  EN→HA is clean; HA→EN reverse is rougher (1914-source limitation — planned fix:
  Paul Newman's *A Hausa-English Dictionary*). `backend/services/dictionary_service.py`.
- **Live web search**: Tavily-backed grounding for time-sensitive questions on the
  primary (Cerebras) path; honest "no live access" when no key is set.
  `backend/services/search_service.py`. Requires the `TAVILY_API_KEY` secret.
- **Date/time awareness**: exact current date/time for Nigeria (WAT) plus Makka,
  London, New York, Dubai, Tokyo (DST-accurate via `zoneinfo`/`tzdata`); other
  places computed from UTC.
- **Capability self-knowledge & translation** blocks added to the Sovereign
  Constitution so the model describes what it can actually do and translates
  cleanly on request.

### Fixed
- **Foreign numerals**: the model sometimes emitted Arabic-Indic / Persian digits
  (٢٠١٥) in Hausa text; these now fold to Western digits (2015) in both the
  display path and TTS. `orthography.normalize_digits`.
- **Admin password**: `REVIEWER_API_KEY` is now the admin password, synced to the
  `adamu` account on every boot (create-or-update) — change it via
  `flyctl secrets set REVIEWER_API_KEY=...` + restart, no DB surgery. Username
  lookups are case-insensitive.
- **Live voice**: cross-device capture fixed (client resamples mic to 16 kHz from
  the real hardware rate — Safari/WebView were sending 48 kHz mislabeled as 16 k);
  echo/self-talk stopped (VAD + energy gate + no fabricated transcripts + mic
  half-duplex gating); iOS AudioContext resume handling.
- **TTS**: unified loudness normalization to the landing-page level (−14 dBFS RMS,
  −0.5 dBFS peak ceiling); hooked-consonant and currency/percent/separator
  normalization; 22 kHz→24 kHz resample on the Piper fallback; steadier pacing
  (`VITS_NOISE_W=0.3`, `VITS_LENGTH_SCALE=1.1`).
- **Model routing**: Cerebras `gemma-4-31b` is the fast primary; Ollama (first-token
  timeout) → Gemini → static fallback chain.

### Security
- Leaked Gemini key purged from git history; dataset browser (`/api/waxal/*`) gated
  behind admin auth; per-IP live-WebSocket connection cap; dependency CVE floors
  raised (python-multipart, Pillow, requests); npm audit clean.

### Housekeeping
- Anonymous per-device contributor id (`X-Contributor-Id`) for fair rate-limiting
  and feedback attribution — no login wall.
- Project skills added: `.claude/skills/debug-audit`, `.claude/skills/premium-polish`.

---

_Convention: add a new dated section at the top for each production update. Keep
entries grouped under Added / Fixed / Security / Housekeeping._
