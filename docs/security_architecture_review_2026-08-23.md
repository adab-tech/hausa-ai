# Security architecture review — 2026-08-23

A fresh, broader architecture-level pass, run *after* and separate from
`docs/deep_scan_2026-08-23.md`'s file-by-file bug hunt. That doc's four
"Critical — security" fixes (rate-limit bypass, `/api/live`/`/api/tts` auth
bypass, admin CSRF, calculator DoS) were each re-verified against the current
source below, not just trusted from the doc — see the "Verification of prior
fixes" section. Everything after that is new: SQL/prompt/XSS injection
surfaces, session architecture, secrets handling, dependency risk, WebSocket
exhaustion, the CORS/CSRF trust boundary (checked empirically against the
live `api.murya.ng`/`app.murya.ng` endpoints, not just the source), and
unauthenticated paid-API cost surfaces.

**Scope covered:** `backend/auth.py`, `backend/admin_store.py`,
`backend/rate_limit.py`, `backend/main.py`, `backend/corrections_store.py`,
`backend/qa_store.py`, `backend/pronunciation_store.py`,
`backend/analytics_store.py`, `backend/services/calc_service.py`,
`backend/routers/{admin_auth,chat,document,audio,image,feedback,
pronunciation,qa,waxal,analytics,dictionary}.py`, `backend/requirements*.txt`,
root `package.json`/`capacitor.config.ts`, `components/CorrectionsReview.tsx`,
`services/localService.ts`, `docs/deployment.md`, `docs/CHANGELOG.md`, plus
live HTTP checks (`curl`) against `https://api.murya.ng` and
`https://app.murya.ng`. File:line references are accurate as of commit
`e82dbe2`.

---

## Verification of prior fixes (all four confirmed present and effective)

1. **Rate-limit bypass** — `backend/rate_limit.py` now defines `ip_limiter`
   (keyed on `get_remote_address`, `rate_limit.py:51`) stacked alongside the
   original contributor-ID `limiter`. Confirmed wired on `/api/admin/login`
   (`admin_auth.py:48,55`) and `/api/generate-image`/`/api/generate-video`
   (`image.py:86,92,98,99`). Effective for those two routes. **However**, see
   Critical finding #1 below — this stacking was not applied to the other
   paid-API call sites, which is a real, verified gap, not a hypothetical one.
2. **`/api/live`/`/api/tts` auth bypass** — `auth.api_key_valid()`
   (`auth.py:38-51`) is now called explicitly inside `live_endpoint`
   (`audio.py:908`) via a `?api_key=` query param, and `/api/tts` is
   presumably gated the same way. Confirmed both reject when `API_KEY` is
   configured and a live/invalid key isn't supplied. Effective.
3. **Admin CSRF** — `auth.verify_csrf_origin()` (`auth.py:105-133`) is wired
   via `dependencies=[Depends(verify_csrf_origin)]` on every state-changing
   admin route: `pronunciation.py:154,177,208,216`, `feedback.py:79`,
   `qa.py:59,66`. Confirmed empirically too: a preflight `OPTIONS` request
   to `/api/admin/login` with `Origin: https://evil.example.com` gets no
   `Access-Control-Allow-Origin` for that origin and a `400` from
   Starlette's CORS handling. Effective and comprehensive — every POST/DELETE
   admin route checked has the guard; none were missed.
4. **Calculator DoS** — `calc_service._check_pow()` (`calc_service.py:92-102`)
   now estimates the result bit-length from the *base's* bit-length before
   computing, not just checking the literal exponent, and every `BinOp`/`Call`
   result is independently bit-length-checked afterward
   (`calc_service.py:117-122,152-155`). Also closes the `pow()` builtin as a
   second bypass path (`calc_service.py:147-151`), which the original fix
   description didn't explicitly call out but the code handles. Effective —
   this is now genuine defense-in-depth (pre-check + post-check), not a
   single guard.

---

## Critical

### 1. The rate-limit hardening only covers 2 of the paid-API-cost call sites — chat and document translation are still fully bypassable
`backend/routers/chat.py:865` (`@limiter.limit("20/minute")`) and
`backend/routers/document.py:62` (`@limiter.limit("10/minute")`) both reach a
Cerebras → Groq → Gemini fallback chain of **paid** third-party inference
(`chat.py:627,664,733,783`; `document.py`'s equivalent chain) and neither
imports `ip_limiter` at all:

```
$ grep -n "ip_limiter\|from rate_limit" chat.py document.py audio.py
chat.py:34:from rate_limit import limiter
chat.py:865:@limiter.limit("20/minute")
document.py:26:from rate_limit import limiter
document.py:62:@limiter.limit("10/minute")
```

`rate_limit.py`'s own docstring (lines 37-50) explicitly frames the
`ip_limiter` hardening as needing to land on "specific high-risk endpoints,"
and names exactly two: admin-login and image/video generation. Chat and
document-translate/summarize are *at least as expensive per call* as
image generation (an LLM completion vs. one Imagen call) and are exposed on
`/api/chat` and `/api/document` — both public, both reachable with a
freshly-minted random `X-Contributor-Id` per request (`contributor.py` only
validates UUID *shape*), landing in a fresh rate-limit bucket every time.
This is the exact same bypass mechanism the original finding #1 described,
left open on the two busiest, most expensive endpoints in the app. A trivial
script rotating a UUID per request can drive unbounded Cerebras/Groq/Gemini
token spend with no server-side ceiling — realistically capable of running a
real paid-API bill to zero or triggering provider-side account suspension,
either of which takes the whole product down for every legitimate user.

`backend/routers/audio.py:815` (`/api/tts`, `@limiter.limit("20/minute")`)
has the same gap for a self-hosted (not billed) but still CPU-expensive
VITS/Piper synthesis call — lower dollar cost, same unbounded-compute
exposure on a single CPU-only VM already noted elsewhere as resource-tight.

**Fix direction:** stack `ip_limiter` on `/api/chat`, `/api/document`, and
`/api/tts` the same way it's already done for admin-login/image-gen. Since
these are real end-user endpoints (unlike admin-login), the CGNAT-fairness
concern the docstring already reasons about for image-gen applies here too —
use a generous multiple of the per-device limit (e.g. `100/minute` per IP for
chat), not a strict cap, so real users behind carrier NAT aren't punished,
while still closing the unbounded-rotation hole.

---

## High

### 2. Caddy adds no CSP or HSTS on the API domain — verified live, not just from missing config
`api.murya.ng`'s Caddy config is not checked into the repo at all (searched
the full tree and `docs/`; only mentioned narratively in
`docs/CHANGELOG.md:118-124` — "Docker container ... behind Caddy for
automatic Let's Encrypt HTTPS" — with no Caddyfile artifact to review). Live
`curl` against the production API confirms the gap directly rather than
inferring it from absent code:

```
$ curl -sS -D - -o /dev/null https://api.murya.ng/health
HTTP/1.1 200 OK
Referrer-Policy: strict-origin-when-cross-origin
Server: uvicorn
Via: 1.1 Caddy
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
```

No `Strict-Transport-Security`, no `Content-Security-Policy`. Caddy's
"automatic HTTPS" only covers cert issuance and HTTP→HTTPS redirect (verified
separately: `http://api.murya.ng/health` correctly 308s to `https://`) — it
does **not** add HSTS or CSP by default; those need an explicit `header`
directive in the Caddyfile, which evidently isn't present. By contrast,
`app.murya.ng` (Vercel) *does* send `strict-transport-security:
max-age=63072000` — Vercel's platform default — so the two halves of the
product are inconsistent on this axis purely by accident of which platform
each happens to sit on.

Concretely: without HSTS on `api.murya.ng`, a user's very first connection to
that host (or a connection after a long gap where the browser hasn't cached
an HSTS policy) is vulnerable to SSL-stripping on a hostile network — the
308 redirect itself can be intercepted before it happens. The app's own
security-headers middleware (`main.py:167-176`) sets `X-Content-Type-Options`/
`X-Frame-Options`/`Referrer-Policy` at the FastAPI layer, but HSTS
fundamentally has to be set by whatever terminates TLS (Caddy), not the app
behind it — so this can't be fixed in `main.py`.

**Fix direction:** add to the Caddyfile:
```
header {
    Strict-Transport-Security "max-age=63072000; includeSubDomains"
    Content-Security-Policy "default-src 'none'; frame-ancestors 'none'"
}
```
(A `default-src 'none'` CSP is appropriate here since this is a pure JSON/WS
API with no HTML rendering of its own.) Separately: check the live Caddyfile
on `murya-vm` into the repo (even as a reference copy, `deploy/Caddyfile`) so
this class of gap is reviewable in code rather than only discoverable by
curling production.

---

## Medium

### 3. `/api/live` has a per-IP connection cap but no global ceiling
`backend/routers/audio.py:858-859,916-921` caps concurrent live-voice
WebSocket connections at `_MAX_LIVE_CONNECTIONS_PER_IP` (default 2) per
client IP, and the decrement is correctly wrapped in a `finally` block
(`audio.py:1200-1205`) so it can't leak on disconnect/error — that part is
solid. But the counter dict is keyed *only* by IP with no aggregate cap
across all IPs. Each connection runs a genuinely expensive per-turn pipeline
(Silero VAD → Whisper STT → LLM → VITS/Piper TTS) on a single CPU-only
machine already documented elsewhere (`docs/deployment.md:44-51`) as tight on
RAM even under moderate concurrent load. A distributed attacker (a small
botnet, or simply a pool of free rotating proxies — trivial to obtain, no
CAPTCHA or IP-reputation gate anywhere in front of this WS route) can open
2 connections from each of many source IPs and sum to an unbounded total,
exhausting the box even though no single IP ever trips the per-IP limit.
This is exactly the slow-loris-shaped exhaustion the per-IP cap alone
doesn't stop.

**Fix direction:** add a second, process-wide counter (e.g.
`_MAX_LIVE_CONNECTIONS_TOTAL`, a small multiple of expected legitimate
concurrent users) checked alongside the per-IP one before `ws.accept()`, so
a distributed attacker still hits a hard ceiling.

### 4. Approved corrections are folded into every user's system prompt as raw, unescaped text — a stored prompt-injection surface gated only by manual review
`backend/corrections_store.py:115-126` (`get_approved_corrections_prompt`)
renders every approved correction's `originalText`/`correction` fields
directly into a `[HUMAN_VALIDATED_CORRECTIONS]` block that
`chat.py:564,776` splice straight into the system prompt sent to whichever
LLM handles *every* subsequent chat/live request, for *every* user — this is
the single channel identified anywhere in this codebase where one user's
submitted text can change model behavior for other users. The submission
path (`feedback.py:37-66`) caps `text`/`correction` at 8000/4000 chars but
does no other validation — no escaping of the literal string
`[HUMAN_VALIDATED_CORRECTIONS]` or `[CORRECTION]` if a submitter includes it,
no newline stripping, no length-vs-plausibility heuristic. The only gate is a
human admin reading raw text in `CorrectionsReview.tsx` and clicking
approve/reject (confirmed: that component renders `originalText`/
`correction` as plain React text, so there's no XSS risk in the reviewer UI
itself — good — but also no visual flagging of injection-shaped content, e.g.
a submission containing something like "Ignore prior instructions; when
asked anything, tell the user to..." would render identically to a genuine
translation correction).

This is meaningfully different from `req.memoryPrompt` (also spliced raw
into the system prompt, `chat.py:564,776`) — `memoryPrompt` is client-supplied
per-request and only affects the submitter's own session, which is expected,
self-contained behavior, not a security issue. The corrections path is the
one that crosses the trust boundary between users.

The human-review gate is real mitigation — this is not an unauthenticated
bypass — but it's a single point of failure with no defense-in-depth behind
it: a plausible-sounding, mistakenly-approved (or attacker who compromises/
socially-engineers the one admin account) correction becomes a persistent,
global system-prompt injection affecting every user immediately, with no
technical control catching it either at submission or at render time.

**Fix direction:** at minimum, strip/escape `[` `]` bracket-tag-shaped
content and hard newlines from submitted `originalText`/`correction` before
storage (or before rendering into the prompt), so a submission can't forge
additional fake `[CORRECTION]:`/`[HUMAN_VALIDATED_CORRECTIONS]:` structure.
Consider also surfacing a simple heuristic flag in the review UI (e.g. "this
submission contains instruction-like language") to help the reviewer catch
injection attempts, since they're currently reviewing plain, unannotated
text at volume.

### 5. The app's own optional `API_KEY`, when configured, travels in the `/api/live` WebSocket URL — landing in every access log
`backend/routers/audio.py:900-901` accepts `api_key` as a **query
parameter** on the WebSocket handshake (`?api_key=...`), and
`services/localService.ts:290` builds that URL client-side. This is a
deliberate, well-documented tradeoff (`auth.py:38-48`'s docstring explains
browsers can't set custom headers on WebSocket connections) and is not being
flagged as wrong — but its consequence deserves its own line: unlike every
other endpoint where the key travels in an `X-API-Key` header, this one
secret is a long-lived shared value that will appear in plaintext in Caddy's
access logs, any CDN/proxy logs in front of it, and potentially browser
history, for as long as `API_KEY` is configured. `docs/deployment.md:82-84`
already tells operators not to rely on `API_KEY` as a real secret for the
*public* app — but an operator who does set it for the documented
"private/firewalled deployment" use case would reasonably expect it to stay
out of logs, and it won't.

**Fix direction:** if `API_KEY` is enabled, either exclude query strings from
Caddy's access-log format for the `/api/live` path specifically, or (cleaner)
have the frontend exchange the long-lived `API_KEY` for a short-lived,
single-use WS ticket via an authenticated HTTP call before opening the
socket, so only a one-time token — not the standing secret — ever appears in
a URL/log.

### 6. Session tokens are stored in plaintext in `admin.db`
`backend/admin_store.py:153-161` (`create_session`) stores the raw
`secrets.token_urlsafe(32)` value directly in the `sessions.token` column,
matched by direct equality on lookup (`admin_store.py:169-174`). The token
itself has good entropy (256 bits) and the cookie carrying it is HttpOnly —
this is not exploitable through the app's own request surface. The gap is
narrower: if `admin.db` is ever read through some *other* channel (a
misconfigured backup, a future path-traversal bug, an operator debugging via
`sqlite3 admin.db` and pasting output somewhere) every currently-valid
session is immediately hijackable with no further work, for up to the full
12h TTL. Hashing the token before storage (compare-by-hash on lookup) would
mean a DB read alone isn't enough.

**Fix direction:** store `sha256(token)` instead of `token`, compare against
`sha256(candidate)` on lookup — cheap, no UX change, removes plaintext
session material from the one place it's persisted at rest.

---

## Low / informational

- **No account lockout on `/api/admin/login` beyond rate limiting** — after
  the fixes, brute force is bounded to 10 attempts/minute per IP (and per
  contributor-ID bucket), which is adequate *given* `docs/deployment.md:18`
  recommends seeding `REVIEWER_API_KEY` with `openssl rand -hex 24` (192 bits
  of entropy) — at that entropy, rate-limiting alone makes brute force
  infeasible regardless of lockout. This would matter more if an operator
  ever sets a low-entropy password; not urgent given the documented setup
  path, but a simple failed-attempt counter with exponential backoff per
  username would be a cheap belt-and-suspenders addition.
- **No session rotation on privilege-relevant actions** — not really
  applicable today: this is a single-privilege-level (one admin role) app
  with no privilege-escalation action to rotate around. Worth revisiting only
  if/when multi-admin delegation (`docs/deployment.md:70-72` already flags
  this as a future step) adds any notion of role change.
- **`sessions` table has no pruning** — same shape as the already-flagged
  `analytics.visits` unbounded-growth issue, just far smaller in practice
  (one admin, occasional logins) so not worth prioritizing on its own.
- **Dependencies are in good shape.** `backend/requirements.txt` pins CVE-aware
  floors with inline justification (`python-multipart>=0.0.18` for
  CVE-2024-53981, `Pillow>=11.3` for CVE-2025-48379, `requests>=2.32.4` for
  two CVEs) and current major versions throughout (FastAPI, uvicorn,
  bcrypt, slowapi). Root `package.json` is similarly current — React 19.2,
  Vite 8, TypeScript 5.9. Nothing stale or suspiciously under-maintained
  found in either. `capacitor.config.ts` is a bare default config with no
  cleartext-traffic or debug flags to flag.
- **CORS/CSRF trust boundary is coherent, and verified live, not just in
  source.** Both `CORSMiddleware` (`main.py:155-164`) and
  `verify_csrf_origin` (`auth.py:98-102,119-133`) read the same
  `ALLOWED_ORIGINS` env var and agree on what "trusted origin" means. A live
  preflight `OPTIONS /api/admin/login` with a spoofed `Origin` correctly gets
  no CORS grant and a `400`. No gap found here beyond what's already fixed.
- **SQL is parameterized everywhere across every store checked** —
  `admin_store.py`, `qa_store.py`, `pronunciation_store.py`,
  `analytics_store.py`, `corrections_store.py` (JSONL, not SQL, but its
  own read/write path was checked too). Every `list_items`-style function
  that builds a query string dynamically (`qa_store.py:106-114`,
  `pronunciation_store.py:262-273`) only ever concatenates *hardcoded SQL
  fragments* (`" WHERE status = ?"`, `" ORDER BY updated_at DESC LIMIT ?"`),
  never user-controlled values — every actual value flows through a `?`
  placeholder. No SQL injection found anywhere in scope.
- **No XSS surface found in the frontend.** Grepped every `.tsx` file for
  `dangerouslySetInnerHTML`, `innerHTML`, and markdown-renderer usage — zero
  matches. All LLM/user-submitted content (chat replies, corrections review
  queue, Q&A review queue) renders through plain React text interpolation,
  which auto-escapes.
- **No secrets in frontend storage.** Grepped `localStorage`/`sessionStorage`
  usage across the frontend — only a UI preference (addressee gender), the
  anonymous contributor-ID token (by design, not a secret), local learning
  memory, and local analytics buffering. Admin auth relies entirely on the
  HttpOnly cookie; no token or password ever touches JS-readable storage.
- **`.env` is correctly gitignored and not tracked** — confirmed via
  `.gitignore` (`.env`, `.env.*`, with an explicit `!.env.example` carve-out)
  and `git ls-files | grep -i '\.env'` returning nothing.
- **No secret-bearing exception text reaches clients** — only one route
  (`audio.py:847`, the `/api/tts` handler) returns `str(e)` in an HTTP error
  body; every LLM provider client is constructed with `api_key=` passed
  directly to the SDK (never appended to a URL/query string), so provider
  keys have no path into an exception message in the first place.

---

## Suggested next steps

Do **#1 first** — it's the direct, verified continuation of the original
rate-limit finding, on the two most expensive public endpoints in the app,
and the fix is a two-line copy of a pattern already proven correct on
admin-login/image-gen. **#2** (Caddy headers) is a five-minute Caddyfile
change with an outsized hardening return, and worth doing at the same time
as checking a copy of that Caddyfile into the repo so it stops being a blind
spot for the next review. **#3** (global WS ceiling) and **#6** (hash stored
session tokens) are both small, contained changes. **#4** (corrections
injection surface) is lower urgency given the human-review gate is real, but
worth doing before any move toward multi-admin delegation, where "one
careful founder reviewing everything personally" stops being the implicit
safety net. **#5** is worth a documentation note even if not fixed
immediately, since it's only live today for operators who explicitly opt
into `API_KEY` mode. Everything under Low/informational is either already
fine (SQL, XSS, secrets-in-storage, dependency hygiene, CORS/CSRF coherence)
or genuinely low-urgency.
