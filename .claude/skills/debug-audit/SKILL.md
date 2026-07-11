---
name: debug-audit
description: Comprehensive debugging audit of the Murya Hausa AI stack — backend, frontend, TTS pipeline, and live deployment. Use when asked to find and fix bugs, run a health/debug pass, audit the project for defects, or verify the whole stack end-to-end.
---

# Murya Debug Audit

A full-stack defect hunt for this repo. Work through the layers in order; fix what you find as you go (small fixes inline, big ones flagged first). Never claim a layer clean without running its checks.

## Layer 1 — Static & tests (fast, do first)

```bash
cd backend && python -m pytest tests/ -q --no-cov          # all must pass (93+ as of 2026-07)
npx tsc --noEmit 2>&1 | grep -v "^New folder"              # frontend typecheck ("New folder/" is untracked junk, ignore)
cd backend && python -m pip install ruff -q && python -m ruff check . --quiet
```

## Layer 2 — Known bug classes in THIS codebase

History shows defects cluster here — re-check each:

1. **Text-normalization gaps before TTS.** The trained VITS voice has a 42-symbol phoneme map (a–z, punctuation, ɓɗƙƴ). Anything outside it is *silently dropped*: digits were silent until `spell_out_hausa_numbers`, apostrophe-notation hooked consonants were mispronounced until normalization was added to `_synthesize_speech`. New risk surfaces: dates, times, currency (₦, $), abbreviations, English loanwords, emoji. Test by synthesizing text containing the suspect symbols and checking output size / listening.
2. **Fallback-chain ordering & timeouts** (`routers/chat.py`, `routers/audio.py`). Chain is Cerebras → Ollama (first-token timeout) → Gemini → static. A merely-*slow* tier must not hang the request — verify timeout paths, not just exception paths.
3. **Speaker/gender mapping.** WAXAL ids alternate gender (1=F1, 2=M1 … 8=M4). Frontend 0–3 = male, 4–7 = female. Any new mapping code must be tested against `waxal_hausa/metadata_processed.jsonl` filename prefixes, not assumed.
4. **CORS headers.** Any new custom request header MUST be added to `allow_headers` in `backend/main.py` or production silently breaks (dev same-origin hides it).
5. **Cache-key completeness** (`_get_cache_key` in chat.py). Every request field that changes the reply (gender, vibe, memoryPrompt…) must be in the key, or users get each other's replies.
6. **Per-device vs per-IP limits.** Rate limiting keys on `X-Contributor-Id` (see `backend/contributor.py`), falling back to IP. WebSocket `/live` has its own per-IP connection cap (slowapi doesn't cover WS).

## Layer 3 — Live production probes

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://hausa-ai-backend.fly.dev/health          # 200
curl -s -o /dev/null -w "%{http_code}\n" https://app.murya.ng                             # 200
curl -s -o /dev/null -w "%{http_code}\n" https://hausa-ai-backend.fly.dev/api/waxal/stats # 401 (admin-gated!)
# Chat must stream and finish fast (Cerebras primary ⇒ ~2s):
curl -s -m 20 -X POST https://hausa-ai-backend.fly.dev/api/chat -H "Content-Type: application/json" \
  -d '{"text":"Sannu"}' -o /dev/null -w "%{http_code} in %{time_total}s\n"
# TTS with numbers + hooked consonants must return substantial audio (>50KB):
curl -s -m 25 "https://hausa-ai-backend.fly.dev/api/tts?text=Mun%20sayi%20littattafai%2025%20a%20%C6%99asar%20Kano&speaker_id=0" -o /tmp/dbg.wav -w "%{http_code} %{size_download}\n"
```

Check Fly logs for silent errors: `flyctl logs -a hausa-ai-backend --no-tail | grep -iE "error|exception|failed|traceback"` (run via timeout, it can hang).

## Layer 4 — Browser runtime

Open https://app.murya.ng in the Browser pane. Then:
- `read_console_messages` with onlyErrors — zero errors expected on load and after sending one chat message.
- Send a real message; confirm streaming text renders, no layout jumps.
- `read_network_requests` — no failed requests; `/api/chat` carries `X-Contributor-Id`.
- Check `localStorage.murya_contributor_id` exists and is a UUID.

## Layer 5 — Report

Summarize: defects found (severity-ordered), what was fixed + commits, what was deferred and why. Never soften a finding; if production is broken say so first.

## Deploy note

Fixes are only real once deployed: `flyctl deploy -a hausa-ai-backend` (backend) / `npx vercel --prod` (frontend) — **always ask the user before deploying**, naming the command, target, and commit.
