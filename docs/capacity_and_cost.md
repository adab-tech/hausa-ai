# Murya — Capacity & Cost (how far will it scale?)

_Rough engineering estimates grounded in the current production config. These
are planning figures, not benchmarks — real limits need load testing. The new
**Ziyara** analytics tab in the admin dashboard gives you actual visitors/day
to plan against._

> **Cost status (2026-07): not a constraint.** The current Cerebras tier covers
> more than enough tokens/day for present traffic at no cost. So token *volume*
> and *price* are NOT the ceiling right now — the operative limits are the
> single CPU box (voice) and the lack of a second machine (see Bottlenecks).
> One thing to still check on the Cerebras plan: the **per-minute** rate limits
> (requests/min, tokens/min) — those cap simultaneous/burst users even when the
> daily token allowance is generous.

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

### Text chat — scales well (offloaded to Cerebras)
The Fly box only proxies the token stream; generation is Cerebras'. So text is
I/O-bound and light on the box. The limiter is **Cerebras throughput / your
plan's token quota**, not the machine.
- **Estimate: a few thousand → ~10k+ text chat exchanges/day** on the current
  single box, bounded mainly by the Cerebras tier. Concurrency of hundreds of
  simultaneous text streams is plausible before the box strains.

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
_(Tokens/cost are NOT here — the Cerebras tier covers them for free at this
stage. These are the limits that actually bite.)_
1. **Voice on a single CPU box** — worst-scaling. Fix when voice traffic grows:
   add Fly machines (autoscale) or move TTS/STT to a dedicated (ideally GPU)
   worker.
2. **Single machine = single point of failure** — one machine down is a full
   outage. Add a second machine before real traffic.
3. **Cerebras per-minute rate limits** — even on a generous/free daily
   allowance, requests/min and tokens/min cap how many users can be served
   *simultaneously*. Check the plan's burst limits.
4. **System-prompt size (~1,600 tokens every request)** — not a cost issue
   while tokens are free, but it does add latency and eat into per-minute token
   limits; trimming/caching it helps burst capacity.

## Recommended next steps as traffic grows
- **Now / low traffic**: current setup is fine. Watch the **Ziyara** tab for
  real visitors/day and the Cerebras dashboard for token burn.
- **~500+ visitors/day, or voice picking up**: enable Fly autoscaling / a
  second machine; consider a separate voice worker.
- **Cost control any time**: trim the system prompt and cache the static parts;
  cap history turns; keep the tools grounding tight.

_Last updated 2026-07-12. Revise as config or Cerebras plan changes._
