# Murya — Capacity & Cost (how far will it scale?)

_Rough engineering estimates grounded in the current production config. These
are planning figures, not benchmarks — real limits need load testing. The new
**Ziyara** analytics tab in the admin dashboard gives you actual visitors/day
to plan against._

> **Cost status (2026-07): free, and the allowance is huge.** Confirmed
> Cerebras limits for `gemma-4-31b` (our primary), at no cost:
>
> | | per minute | per day |
> |---|---|---|
> | Requests | 500 | 720,000 |
> | Tokens | 500,000 | **720,000,000** |
>
> Context length: **131,072 tokens** (so the ~1,600-token system prompt is
> trivial here — no need to trim it for Cerebras). A bigger `gpt-oss-120b`
> (Production tier) is also available with ~2× the limits (1,000 req/min,
> 1M tok/min, **2,000,000,000 tokens/day**) if ever needed.

## Current production shape
- **1× Fly.io machine**, `performance-2x` (2 vCPU, 8 GB), region `jnb`
  (Johannesburg), `min_machines_running = 1` (no redundancy, no autoscale yet).
- **LLM: Cerebras `gemma-4-31b`** (hosted API) is the fast primary — the heavy
  text generation runs on Cerebras, NOT on the Fly box. Local Ollama is a slow
  CPU fallback; Gemini/static behind that.
- **Voice: local on the box** — VITS (TTS) and Whisper (STT) run on the 2 vCPU
  CPU. This is the real bottleneck.
- **Rate limits**: chat 20/min·device, tts 20/min, feedback 30/min, image
  5/min, analytics 60/min; live-voice capped at 2 concurrent sessions per IP.

## The two very different ceilings

### Text chat — effectively unconstrained by Cerebras
The Fly box only proxies the token stream; generation is Cerebras'. With the
real limits above (720M tokens/day, 720k requests/day) and ~3k–3.8k tokens per
exchange:
- **Daily ceiling ≈ 190,000–240,000 chat exchanges/day** (token-limited; the
  720k requests/day is looser). At ~5 exchanges/visitor that's on the order of
  **~40,000 visitors/day** from Cerebras alone.
- **Burst ceiling ≈ 130–165 exchanges/minute** (500k tokens/min ÷ ~3k–3.8k;
  the 500 requests/min is looser). This is the real cap on *simultaneous*
  text users.
- In practice the single Fly box's async proxying and the per-minute burst,
  not the daily token budget, are what you'd hit first for text.

### Voice — scales poorly on one CPU box
Each spoken reply is a VITS synthesis (~1–3 s CPU) and each ~2 s of mic audio is
a Whisper transcription (~1–2 s CPU on the `small` model). On 2 shared vCPUs:
- **Estimate: ~1 comfortable concurrent voice session, a handful with
  queueing; on the order of a few hundred voice interactions/day** before
  latency degrades. Voice is the first thing that will feel slow under load.

## Tokens per exchange (the cost driver)
| Part | ~tokens |
|---|---|
| System prompt (constitution + date/time + blocks) | **~1,600** |
| Conversation history (up to 6 turns) | ~600–900 |
| Tool/search grounding (when triggered) | 0–500 |
| User message | ~50 |
| Model response | ~400–800 |
| **Total per exchange** | **~2,700–3,800** |

Rules of thumb (assume ~5 exchanges/visitor):
- **~15k–19k tokens per visitor.**
- **100 visitors/day → ~1.5–1.9 M tokens/day.**
- **1,000 visitors/day → ~15–19 M tokens/day.**

Check your Cerebras dashboard for the plan's included tokens/minute and /day and
price per million tokens to turn this into a naira/dollar figure.

## Bottlenecks, ranked
_(Tokens/cost are NOT here — 720M free tokens/day is far beyond current need.
These are the limits that actually bite, in order.)_
1. **Voice on a single CPU box** — worst-scaling by far. Text rides on Cerebras
   (~40k visitors/day headroom); voice runs locally on 2 vCPUs (~1 comfortable
   concurrent session). Fix when voice grows: add Fly machines / a GPU voice
   worker.
2. **Single machine = single point of failure** — one machine down is a full
   outage. A second machine is the highest-value upgrade before real traffic.
3. **Cerebras per-minute burst (500k tokens/min ≈ 130–165 exchanges/min)** —
   the daily budget is huge, but this caps *simultaneous* text users. Bump to
   `gpt-oss-120b` (1M tokens/min) if burst ever becomes the wall.
4. **System-prompt size (~1,600 tokens)** — negligible now (131k context, free
   tokens); only a minor latency/burst factor. Not worth trimming yet.

## Recommended next steps as traffic grows
- **Now / low traffic**: current setup is fine. Watch the **Ziyara** tab for
  real visitors/day and the Cerebras dashboard for token burn.
- **~500+ visitors/day, or voice picking up**: enable Fly autoscaling / a
  second machine; consider a separate voice worker.
- **Cost control any time**: trim the system prompt and cache the static parts;
  cap history turns; keep the tools grounding tight.

_Last updated 2026-07-12. Revise as config or Cerebras plan changes._
