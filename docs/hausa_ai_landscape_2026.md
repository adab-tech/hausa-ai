# The State of Hausa AI/NLP — Landscape Survey (July 2026)

Compiled 2026-07-04 from Hugging Face Hub, arXiv/HF-papers, and GitHub, to
position the Hausa AI project (`docs/waxal_piper_technical_report.md`) at v2
completion. Companion to `manifesto.md`.

---

## 1. Hausa TTS — every open model on the Hub, and where we land

| Model | Author / Year | Base & data | Speakers | License | Notes |
|---|---|---|---|---|---|
| `facebook/mms-tts-hau` | Meta, 2023 | VITS, MMS (religious-text corpus) | 1 | **CC-BY-NC** | 26.9K downloads; judged unnatural by native audition (this project, 2026-07) |
| `Baghdad99/hausa_voice_tts`, `zeustek/jummai-hausa-tts`, `dammyogt/hausa-tts`, `Asakrg/hausa-text-to-speech-fine-tune` | individuals, 2023–25 | MMS re-uploads / light fine-tunes | 1 | CC-BY-NC | single-digit downloads each |
| BibleTTS Hausa (Coqui) | Meyer et al., 2022 (arXiv:2207.03546) | ~86 h studio single-speaker, Bible domain | 1 | CC-BY-SA | best pre-2026 quality; domain-limited; also OpenBibleTTS benchmark (2026, arXiv:2606.09553) |
| `FarmerlineML/main_hausa_TTS` | Farmerline (Ghana agtech), 2024 | VITS, gated proprietary dataset | 1 | CC-BY-4.0 | commercial org |
| `CLEAR-Global/TWB-Voice-Hausa-TTS-1.0` | CLEAR Global (NGO), 2025 | own TWB Voice corpus (gated) + synthetic-voice program | 1 | **CC-BY-NC** | most serious org effort; single voice |
| `mosesdaudu/hausa-tts-model-gambo-11h` | individual, 2025 | VITS, 11 h single speaker | 1 | unspecified | |
| Piper voices | rhasspy | — | — | — | **no Hausa voice exists** (`ha_NG-openbible` was named in configs but never published) |
| **WAXAL–Piper (this project)** | **A. D. Abubakar, 2026** | **Piper grapheme-mode, WAXAL (CC-BY), 6.03 h after corpus recovery** | **8** | **CC BY-NC-SA 4.0** | **only multi-speaker, only WAXAL-trained conversational Hausa TTS; native-speaker-built. Weights are non-commercial and share-alike; app code is MIT** |

**Findings:**
1. **Nobody had trained TTS on WAXAL-Hausa.** Despite `google/WaxalNLP`'s 243
   likes and 128K downloads, its only published fine-tunes are Naija-Pidgin
   SpeechT5 and Luganda/Acholi ASR. The Hausa TTS subset sat unused until this
   project.
2. **Every existing open Hausa TTS is single-speaker.** Ours is the first open
   multi-speaker (8-voice) Hausa model.
3. **License landscape:** Meta MMS and CLEAR Global are NC; BibleTTS is
   share-alike and Bible-domain. Murya's weights are CC BY-NC-SA 4.0, so
   non-commercial derivatives stay share-alike. Commercial use of the voice
   is a separate written license. The application code is MIT.
4. **Piper's ecosystem gap** (no Hausa, no espeak support) is exactly what our
   grapheme-alphabet method closes — and the method generalizes.

## 2. Hausa ASR — comparatively crowded

A 2022 wave of wav2vec2/XLS-R Common Voice fine-tunes (Akashpb13, Cdial, Mofe,
etc.); whisper fine-tunes (incl. `Baghdad99/saad-speech-recognition-hausa`);
Nigeria's NCAIR (`NCAIR1/Hausa-ASR`); and the field-changing **NaijaVoices**
dataset (2025, arXiv:2505.20564): 1,800 h across Hausa/Igbo/Yoruba, 5,000+
speakers, large WER gains. CLEAR Global released Hausa synthetic-voice ASR
data (arXiv:2507.17578): 250 h real + 250 h synthetic matching 500 h real.
*Implication for us:* ASR is not our fight; but NaijaVoices audio could feed a
future TTS v3, and stronger Hausa ASR would upgrade our whisper-based
segmentation aligner.

## 3. Hausa text/LLM — community-rich, model-poor

- **HausaNLP community** (survey: arXiv:2505.14311; NaijaNLP survey:
  arXiv:2502.19784): AfriSenti/NaijaSenti sentiment, HausaVG/HausaVQA
  multimodal, VOA NER/topics, SemEval 2025/2026 Hausa tasks (emotion,
  cultural QA), machine-generated-text detection (arXiv:2503.13101,
  AfroXLMR 99.2% acc).
- **Encoders dominate:** Davlan's mBERT/XLM-R Hausa adaptations (2022-era),
  AfroXLMR family.
- **No dedicated open Hausa LLM exists.** Coverage comes via multilingual
  models (Aya-Expanse — which our app already uses — AfroLM/AfriTeVa,
  Belebele evaluation). Regional precedent: Uganda's **Sunflower**
  (arXiv:2510.07203) built Qwen3-based models for Ugandan languages — the
  equivalent for Nigeria's big three does not yet exist.
- Instruction data exists but is translated/synthetic (`saillab/alpaca_hausa_taco`,
  `ChrisToukmaji/hausa_instruction_tuning`) — our **Robinson 1914 SFT track
  (20,628 curated EN–HA pairs)** plus the Sovereign Constitution persona is
  differentiated: lexicographically grounded, native-curated.

## 4. Where Adamsy's project stands at v2 (comparative claims)

Defensible as of 2026-07-04 (with "to our knowledge" hedging):

1. **First TTS trained on WAXAL-Hausa** — and first WAXAL model built by a
   native speaker of the target language.
2. **First open multi-speaker Hausa TTS** (8 voices vs. every rival's 1).
3. **Reference conversational Hausa TTS** — eight everyday-domain voices,
   with weights under CC BY-NC-SA 4.0.
4. **First grapheme-native Hausa pipeline** — orthography (ɓ ɗ ƙ ƴ) as model
   symbols; closes the espeak-ng gap for Hausa and, by recipe, for other
   unphonemized languages.
5. **Novel corpus-recovery result:** 2.83 h → 6.03 h from unchanged source
   audio via char-level alignment robust to phonetic ASR (whisper-Hausa word
   anchoring 2–24% → 81–91%).
6. **Only integrated sovereign Hausa stack** (TTS + STT + LLM persona +
   linguistic trace UI, offline, CPU) — competitors ship models; we ship a
   system.
7. With Robinson SFT: the only **lexicon-grounded** Hausa instruction dataset
   from a public-domain scholarly dictionary.

**Honest caveats:** BibleTTS single-speaker audio (86 h studio) likely still
exceeds our per-voice naturalness ceiling (ours: ~45 min/voice after
recovery); CLEAR Global and Farmerline have organizational data pipelines we
lack; NaijaVoices dwarfs WAXAL in hours (ASR-grade, multi-condition — not
studio TTS quality). Our differentiators are breadth (8 voices), license,
integration, method, and native authorship — not yet raw single-voice
naturalness vs. an 86-hour Bible voice.

**Native-speaker comparative audition of BibleTTS-Hausa source audio**
(A. D. Abubakar, 2026-07-04, 25-sample audit): recording quality judged
**ahead of Meta MMS's corpus but a bit below WAXAL's**; delivery **somewhat
fast**, with occasional **mid-sentence cut-offs** (traced to the corpus's
forced-alignment assembly — same artifact class our neighbor-aware edge
padding fixes); and although the reader is native, **the scripted,
read-aloud delivery is audible** — one can tell the speaker is reading from
script, vs. WAXAL's more natural delivery. Register is single-speaker, male,
scriptural. WAXAL's
comparative advantage is **ecological validity**: 8 speakers, gender-balanced,
real-world domains (colors, story excerpts, plants, family, current affairs)
vs. religious-register text. Implication: BibleTTS competes on per-voice
polish; WAXAL-trained models compete on voice diversity and everyday-domain
prosody — the axis end-users actually experience in conversational
applications. Orthographic note: BibleTTS transcripts use vowel-length
macrons (gāba) and apostrophe conventions ('ya'yan) that differ from WAXAL's
Boko-standard text — a normalization consideration for any future corpus
mixing.

## 5. Strategic implications

- **Publish fast:** the WAXAL-TTS slot is empty *today*; first-mover naming
  matters (`adab-tech/waxal-piper-hausa` or similar).
- **Benchmark placement:** OpenBibleTTS (2026) established a low-resource TTS
  benchmark culture — submitting/evaluating our model against it (and MMS-hau,
  BibleTTS) with MOS gives the paper its evaluation section.
- **Alliances:** HausaNLP community (surveys explicitly call for exactly this
  kind of work), Masakhane, NaijaVoices for v3 data.
- **The Sunflower gap:** a Nigeria-focused LLM (Hausa first) is an open,
  fundable niche — our Robinson SFT + persona work is a seed.
