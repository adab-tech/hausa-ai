# Murya — Roadmap: from good product to reference‑grade Hausa AI

_Honest status doc. Records what is built, what runs the system, how it learns,
and the milestones that would make Murya a reference‑grade Hausa language‑
technology system. Nothing here is claimed as done unless marked ✅._

Guiding principles: **sovereignty** (own the core models), **no fabrication**
(never invent Hausa words/proverbs/facts), **human‑in‑the‑loop** (the owner is
the approval gate), and **serious‑research rigor** (claims trace to sources; real
evaluation, not vibes).

---

## 1. Where Murya stands — the launchpad (built ✅)

- ✅ **Sovereign voice** — WAXAL‑Piper VITS, an 8‑speaker Hausa TTS fine‑tuned by a
  native speaker on Google's WAXAL corpus. Deployed, CPU‑real‑time.
- ✅ **Open dictionary** — Robinson (1914, public domain, EN→HA) + Wiktionary
  (CC‑BY‑SA, HA→EN), ranked by authoritative direction.
- ✅ **Community‑learning loop** — flag → record → **owner approval** → instant
  runtime override + exportable training corpus. Users *and* admins can record.
- ✅ **Product** — chat (Cerebras Gemma primary), live voice, admin panel
  (Text / Voice / Visitors), privacy‑preserving analytics, deployed on Fly.io +
  Vercel, loudness‑matched to the landing page, no scaffolding/fabrication leaks.

This is a strong **product**. It is not yet a reference‑grade **system**.

## 2. The brains — what actually runs Murya

| Role | Network | Sovereign? |
|---|---|---|
| Reasoning / chat | **Gemma‑4‑31B** (Cerebras; Ollama/Gemini fallback) | ❌ borrowed, general — **not** natively Hausa |
| Voice | **WAXAL‑Piper VITS** (`model.onnx`) | ✅ **ours**, fine‑tuned |
| Hearing (STT) | **Whisper** (faster‑whisper) | ❌ external |
| Images | FLUX.1‑schnell | ❌ external, non‑core |

The linguistic layer (orthography/hook normalization, Litvinova tone mapping) is
**rule‑based code, not a neural net**. Headline: **the voice is sovereign; the
mind is borrowed.** Closing that gap is milestone #1.

## 3. How Murya learns (decision, not aspiration)

- **Continuous learning = FREE and instant** via the runtime override: an
  approved correction serves the human recording for that exact text forever, at
  zero compute cost. This is the day‑to‑day "self‑learning."
- **Consolidation = the neural retrain**, which costs GPU time (Modal, real
  money). It generalizes corrections into the model weights and is run
  **occasionally and deliberately**, when enough corrections have accrued.
- **No free fully‑automatic retrain‑and‑deploy.** GPU retraining isn't free, and
  an unattended bad retrain reaching users contradicts the human gate. Decision:
  **keep the free override as continuous learning; retrain by choice, and the
  owner approves any new model before it ships.** (See `pronunciation-correction`
  loop + `utils/export_pronunciation_corpus.py` + the admin **Fitar da Koyo**
  button.)

## 4. Milestones to reference‑grade (not started ❌)

Ranked by impact on "AI + Hausa linguistics":

1. **Native Hausa LLM fine‑tune** ❌ — replace the borrowed mind. The single
   biggest authenticity win; directly fixes the fabrication class of bugs.
   _(Scoped in §5.)_
2. **Tone‑channel TTS** ❌ — feed tone (H/L) + vowel length into the voice for
   real rising/falling melody (montante/descendante), not an averaged contour.
   Depends on #3.
3. **Hausa G2P with tone + vowel length** ❌ — a grapheme‑to‑phoneme layer that
   marks Hausa's phonemic tone *and* length. The linguistic foundation #2 rests
   on; a publishable contribution in its own right.
4. **MOS evaluation study** ❌ — formal native‑listener mean‑opinion‑score study.
   The rigor that makes the work citable, not "sounds nice to us." Owed per the
   project's research standard.
5. **Word‑in‑sentence correction splicing** ❌ — apply approved corrections
   *inside* sentences (forced alignment + splice), not only exact phrases.

Doing **#1 + #2 + #3 + #4** yields: sovereign voice **and** sovereign mind,
tone‑accurate, community‑taught, and evaluated with real rigor — an assembly
nobody has completed for Hausa.

## 5. Milestone #1 — Native Hausa LLM (first scope)

**Goal:** a reasoning model that is authentically Hausa, so Hausa is native, not
translated — eliminating fabrication at the source.

**Data we already have / can get:**
- Robinson (1914) EN↔HA pairs (20k+, public domain) — already processed.
- Wiktionary HA→EN (CC‑BY‑SA) — already processed.
- Approved pronunciation corrections (text side) — growing, owner‑curated.
- Open Hausa text corpora to add (all to be licence‑checked, per the project
  standard): Hausa Wikipedia (CC‑BY‑SA), OSCAR/CC Hausa slice, Tatoeba HA,
  Bible/religious texts where licensing permits, and native‑speaker‑written
  prompts/answers (the highest‑value, smallest‑volume set).

**Approach (proposed, to confirm):**
- Base: an open, permissively‑licensed multilingual model with some Hausa
  exposure (candidates to benchmark: Gemma‑2/Aya‑Expanse/Llama‑3.x‑instruct).
- Method: **instruction fine‑tune (LoRA/QLoRA)** on a curated Hausa
  instruction set — cheaper, reversible, avoids catastrophic forgetting vs full
  FT. Always mix Hausa data with retained general data.
- Serve alongside/behind the current Cerebras path (fallback‑safe), A/B by ear
  before promoting.

**Compute / cost (rough, Modal):** a LoRA instruction‑tune of a 7–9B model is on
the order of low tens of GPU‑hours → typically tens of dollars per run, not
thousands. Iterative, not continuous. (Confirm against `docs/modal_stacks.md`.)

**Evaluation:** native‑speaker review of fluency + a no‑fabrication check
(does it invent words/proverbs?), plus a held‑out Hausa QA set. Gate on the
owner's ear before it serves users.

**Risks:** data licensing (hold the standard — no scraped copyrighted text);
catastrophic forgetting (mix corpora); over‑claiming (evaluate honestly).

---

_Next action: confirm the milestone‑#1 approach (base model + LoRA), then build a
data‑prep + training scaffold on Modal in stages. The voice pair (#3 → #2) is the
parallel track when ready._
