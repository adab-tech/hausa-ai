# MOS listening test — TTS naturalness eval

The naturalness-eval counterpart of the pronunciation-correction loop
(`docs/murya_roadmap.md`). Where that loop fixes individual mispronounced
words, this one answers a broader question before any new voice checkpoint
or correction batch feeds the next retrain: **does this actually sound
better to real Hausa speakers?**

## What it is

A blind, randomized Mean Opinion Score (MOS) study, standard TTS-evaluation
methodology (ITU-T P.800-style: a 1–5 naturalness scale, a real-human-speech
anchor to calibrate against), reachable two ways:

1. **Public listening page** — `app.murya.ng/listen` ([components/MosListen.tsx](../components/MosListen.tsx)).
   Anonymous, no login. A listener hears ~20 unlabeled clips (a mix of the
   production Murya voice and real WAXAL human recordings), rates naturalness
   (1–5) and intelligibility ("could you understand every word?") per clip,
   and submits at the end. Session data lands in `backend/mos.db`.
2. **In-app nudge** — [components/MosPrompt.tsx](../components/MosPrompt.tsx). A
   one-time, dismissible banner pointing existing chat users at `/listen`,
   shown only after they've actually heard the voice a couple of times in
   that session (never on first load, never repeated once seen/dismissed —
   tracked via a `localStorage` flag).

## What's in the stimulus pool

Seeded once at backend startup if `mos_stimuli` is empty
([backend/seed_mos_stimuli.py](../backend/seed_mos_stimuli.py)):

- **64 Murya clips** — 8 real, already-vetted Hausa sentences (pulled from
  `utils/synth_custom_samples.py`'s dev synthesis set and the landing page's
  own demo copy — nothing invented for this) × all 8 production voices,
  synthesized fresh from the exact deployed model
  (`models/piper_hausa_waxal/model.onnx`).
- **2 ground-truth clips** — real human WAXAL recordings
  ([data/mos_ground_truth/](../data/mos_ground_truth/), CC-BY-4.0/CC-BY-SA-4.0,
  baked into the Docker image), the naturalness ceiling every session is
  calibrated against.

Deliberately does **not** include a low-quality-checkpoint anchor or a
competitor-model comparison the way the one-off standalone research build
(a Claude Artifact, not deployed) does — that would mean baking an extra
~77 MB undertrained checkpoint into the production image for a comparison
end users don't need. This deployed version only answers "is the CURRENT
production voice good," which is what an admin needs before a retrain
decision.

## Admin: the actual eval gate

`app.murya.ng/admin` → **Kimanta Murya** tab
([components/MosReview.tsx](../components/MosReview.tsx)), reading
`GET /api/admin/mos/results`:

- A synthesized headline, not just raw numbers — e.g. *"Murya: 4.94/5 vs.
  human speech: 5.00/5 (gap 0.06) — but too few ratings yet... to trust this
  number. Keep collecting."* Below a floor of 20 ratings per condition
  (`mos_store._MIN_TRUSTWORTHY_N`), the verdict is always `insufficient_data`
  regardless of how good the raw mean looks.
- Per-voice breakdown, with any voice scoring ≥0.4 below Murya's own overall
  mean flagged as needing attention.
- An intelligibility flag if fewer than 85% of listeners understood every
  word (once there's enough data to say so).
- **Raw CSV export** (`GET /api/admin/mos/export`) for real statistics
  (proper confidence intervals, significance tests) beyond the dashboard's
  quick normal-approximation numbers.

### The decision record — final authority stays explicit

Nothing about this tool ships anything to training by itself. The dashboard
has three buttons — **Approve for training**, **Needs more data**,
**Reject** — each recording an explicit, timestamped, auditable decision
(`mos_store.mos_decisions`, surfaced in the existing unified admin audit log)
that snapshots the exact numbers it was made against, so a later flood of
new ratings can never quietly rewrite what was actually decided and why.
This mirrors the pronunciation loop's own rule: recording a correction is
not approving it; approving a correction doesn't retrain the model by
itself. A human decision is always the last step before anything from this
tool influences an actual retrain.

## Distribution

Two channels, deliberately not a landing-page CTA (general product traffic
is the wrong audience for a study that depends on careful native-speaker
judgment):

1. **Direct, targeted outreach** — recruited native-speaker volunteers (e.g.
   the HausaNLP community, personal contacts) sent the `/listen` link
   directly.
2. **The in-app nudge** (`MosPrompt.tsx`) — existing `app.murya.ng` users who
   already care about the product, a better-qualified pool than cold
   landing-page traffic.

## Operating it

- Nothing to run manually — the stimulus pool self-seeds on first backend
  startup with an empty `mos_stimuli` table (subsequent restarts are a
  no-op check, not a re-synthesis).
- To add more sentences or voices to the pool: edit `SENTENCES` in
  `backend/seed_mos_stimuli.py`, then clear `mos_stimuli` (or the whole
  `mos.db`) so it reseeds — existing ratings in `mos_ratings` are keyed by
  `clip_id` and are unaffected by a stimuli reseed unless a clip_id is
  reused with different content.
- To pull raw data for offline analysis: log in as admin, **Kimanta
  Murya** → **Fitar (Export CSV)**.
