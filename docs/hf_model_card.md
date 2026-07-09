---
license: mit
language:
- ha
pipeline_tag: text-to-speech
tags:
- text-to-speech
- tts
- hausa
- piper
- vits
- multi-speaker
- african-languages
- low-resource
- sovereign-ai
datasets:
- google/WaxalNLP
library_name: piper
---

# WAXAL–Piper Hausa TTS (8-voice)

**Multi-speaker Hausa text-to-speech**, fine-tuned on Google's WAXAL corpus.
To our knowledge this is the **first TTS model trained on WAXAL-Hausa**, the
**first open multi-speaker Hausa voice model**, and the **first built by a
native speaker of the target language** with native evaluation embedded at
every decision point.

- **Voices:** 8 (M1–M4 male, F1–F4 female)
- **Sample rate:** 22.05 kHz
- **Format:** ONNX (~73.5 MB) — real-time on commodity **CPU**, no GPU or cloud required
- **Orthography-native:** trained in grapheme mode on a custom 42-symbol Hausa
  alphabet — the hooked consonants **ɓ ɗ ƙ ƴ** and glottal **'** are
  first-class model symbols and are never flattened.
- **License:** MIT (commercial use permitted). Please cite Google WAXAL (below).

Developed by **Adamu Danjuma Abubakar** (ADAB-TECH Labs) · [github.com/adab-tech](https://github.com/adab-tech)

---

## Usage

```python
# Requires: pip install piper-tts  (or use the ONNX directly with onnxruntime)
import wave
from piper import PiperVoice

voice = PiperVoice.load("model.onnx", config_path="model.onnx.json")

# Speaker index is NOT sorted-alphabetical — read speaker_id_map from
# model.onnx.json rather than assuming an order. Current map:
#   F2:0  M3:1  M2:2  F4:3  M4:4  F1:5  M1:6  F3:7
with wave.open("out.wav", "wb") as wav:
    voice.synthesize("sannu da zuwa, ina fatan kana lafiya.", wav, speaker_id=6)  # M1
```

**Text tip:** normalize input to Unicode NFD before synthesis. NFC composes
tone-marked vowels (e.g. `á`) into codepoints outside the training alphabet,
which drops the vowel; NFD keeps the base vowel. Lowercase input (the model is
trained casefolded). Digits should be spelled out.

---

## Training

- **Base / warm start:** [rhasspy/piper](https://github.com/rhasspy/piper)
  (VITS-family, MIT), warm-started from the public-domain `en_US-lessac-medium`
  checkpoint (acoustic init only — all voice identity comes from WAXAL).
- **Method:** grapheme-mode (`--phoneme-type text`) with an injected Hausa
  codepoint alphabet, because espeak-ng has no Hausa voice.
- **Data:** WAXAL Hausa TTS clips (8 speakers), filtered to 1–20 s, digit-free.
  A character-level forced-alignment segmentation pass (whisper-large-v3;
  robust to phonetic ASR output) recovered long/digit clips into clean
  sentence segments, growing usable audio from **2.83 h → 6.03 h**
  (2,693 utterances) from the same source recordings.
- **Evaluation:** native-speaker audition on fixed benchmark sentences,
  including minimal-pair orthography/tone tests, gating base-model selection,
  data certification, and epoch budget. A scored MOS (Mean Opinion Score)
  listening study is planned but not yet run — treat existing native-speaker
  audits as directional, not a substitute.
- **Status:** the v2 fine-tuning run is complete (Modal run stopped cleanly;
  final `model.onnx`/`model.onnx.json` exported 2026-07-06). Exact final
  epoch/step number has not yet been pulled from the checkpoint and is not
  stated here to avoid guessing.

Full methodology: see the project technical report.

---

## Intended use & limitations

**Intended for:** conversational and everyday-domain Hausa speech —
accessibility (voice-first access for low-literacy users), education, IVR,
offline/edge apps in bandwidth-constrained regions.

**Limitations:**
- Per-voice naturalness reflects ~45 min of audio per speaker; a single-speaker
  corpus with far more hours (e.g. BibleTTS) may sound smoother on one voice,
  but is single-speaker and single-register. This model's strengths are voice
  diversity, everyday-domain prosody, natural (non-scripted) delivery, and a
  permissive license.
- Trained on read speech; extreme expressivity/emotion is out of scope.
- Not validated for safety-critical or medical dictation without human review.

---

## Attribution & citation

Training data derives from **Google WAXAL** (`google/WaxalNLP`,
CC-BY-4.0 / CC-BY-SA-4.0). Please credit WAXAL and its speakers in any
derivative work.

```bibtex
@misc{abubakar2026waxalpiper,
  title  = {WAXAL--Piper Hausa TTS: Sovereign Multi-Speaker Speech Synthesis
            from a Small Corpus},
  author = {Abubakar, Adamu Danjuma},
  year   = {2026},
  note   = {ADAB-TECH Labs. Fine-tuned on the Google WAXAL corpus.},
  url    = {https://github.com/adab-tech}
}
```

*Motsi ya fi laɓewa.*
