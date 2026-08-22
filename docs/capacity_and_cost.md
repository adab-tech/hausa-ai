# Murya — Capacity & Cost (how far will it scale?)

_Rough engineering estimates grounded in the current production config. These
are planning figures, not benchmarks — real limits need load testing. The new
**Ziyara** analytics tab in the admin dashboard gives you actual visitors/day
to plan against._

> **Cost status (2026-08-22, revised — CORRECTION, was stale): NOT free
> anymore.** Cerebras ended the no-card free tier on **2026-08-17**. Every
> account now needs a verified payment method to unlock **$5 in free credit**,
> then pays PayGo. Confirmed live in production: with no payment method on
> file, every request returns `402 Payment Required` — this took the whole
> chat pipeline down for real users until caught and fixed (2026-08-22).
>
> **PayGo pricing for `gemma-4-31b`** (Preview tier — not yet Cerebras'
> officially-supported production tier, worth knowing separately from cost):
> **$0.99 / million input tokens, $1.49 / million output tokens.**
>
> Using this doc's own per-exchange figures below (~2,650 input + ~600 output
> tokens, roughly): **≈ $0.0035 per exchange** (~⅓ of a cent). At ~5
> exchanges/visitor:
>
> | Visitors/day | Cost/day | Cost/month |
> |---|---|---|
> | 100 | ~$1.75 | ~$52 |
> | 1,000 | ~$17.50 | ~$525 |
> | 10,000 | ~$175 | ~$5,250 |
>
> **The $5 free credit covers roughly ~1,400 exchanges total (a few hundred
> real conversations) — not a meaningful runway at "real humans using it"
> scale.** Treat Cerebras as a genuine, ongoing line-item cost from here on,
> the same way Fly hosting and Azure credit already are — not a free resource
> to plan around. Revisit this doc's context-length/burst-limit figures below
> too; those were measured under the old free tier and may differ under PayGo.

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

### Text chat — now COST-constrained, not rate-constrained
_The 720M-tokens/day and 500k-tokens/minute figures below described the old
no-card free tier (ended 2026-08-17) and are UNCONFIRMED under PayGo — Cerebras'
PayGo rate limits haven't been re-checked since the change. Do not plan capacity
against them until re-verified on the current billing dashboard._

The Fly box only proxies the token stream; generation is Cerebras'. Whatever the
current PayGo rate limits turn out to be, **the real constraint now is cost per
exchange** (~$0.0035, see below), not a free daily token ceiling — at real
traffic this becomes a genuine, ongoing bill, not a headroom question.
- ~~Daily ceiling ≈ 190,000–240,000 chat exchanges/day~~ (old free-tier math,
  no longer the binding constraint — cost is).
- ~~Burst ceiling ≈ 130–165 exchanges/minute~~ (same caveat — re-verify PayGo's
  actual per-minute limits before relying on this number).

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
_(Cost IS a real bottleneck now — see the status box up top — but it's a
billing/budget question, not a hard technical ceiling, so it isn't ranked
below. These are the limits that actually bite on the technical side.)_
1. **Cost per exchange (~$0.0035)** — no longer negligible. At real traffic
   (1,000+ visitors/day) this is a genuine ~$500+/month line item, not
   headroom. Treat it as a budget gate before pushing for more visitors.
2. **Voice on a single CPU box** — worst-scaling technically. Voice runs
   locally on 2 vCPUs (~1 comfortable concurrent session). Fix when voice
   grows: add Fly machines / a GPU voice worker.
3. **Single machine = single point of failure** — one machine down is a full
   outage. A second machine is the highest-value upgrade before real traffic.
4. **Cerebras per-minute burst** — old free-tier figure was 500k tokens/min
   (≈130–165 exchanges/min); PayGo's actual per-minute limit is unconfirmed.
   Re-check the dashboard before assuming this ceiling still holds.
5. **System-prompt size (~1,600 tokens)** — still a real per-exchange cost
   contributor now that tokens aren't free (≈$0.002 of the ~$0.0035/exchange).
   Worth trimming once cost, not just latency, is the thing being optimized.

## Recommended next steps as traffic grows
- **Now / low traffic**: current setup is fine. Watch the **Ziyara** tab for
  real visitors/day and the Cerebras dashboard for token burn.
- **~500+ visitors/day, or voice picking up**: enable Fly autoscaling / a
  second machine; consider a separate voice worker.
- **Cost control any time**: trim the system prompt and cache the static parts;
  cap history turns; keep the tools grounding tight.

_Last updated 2026-08-22 (cost-status correction). Revise as config or Cerebras plan changes._
