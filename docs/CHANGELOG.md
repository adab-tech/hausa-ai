# Changelog — Murya (Sovereign Hausa AI)

All notable changes to the backend and frontend. Newest first. Dates are the
day the change went live in production (Fly.io backend / Vercel `app.murya.ng`).

## 2026-07-12 (latest)

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
