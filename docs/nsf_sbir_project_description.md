# NSF SBIR Phase I Project Description Draft

**Project Title:** SBIR Phase I: Sovereign Edge-Native Speech Synthesis for Low-Resource Tonal African Languages  
**Company:** ADAB Tech Inc.  
**Principal Investigator (PI):** Adamu Danjuma Abubakar  

---

## 1. Project Summary & Elevator Pitch

### The Problem
Over 80 million people in West Africa speak Hausa, yet existing speech technologies are virtually non-existent or fail to capture the language's fundamental phonetic and prosodic structures. Because Hausa is a tonal language with phonemic vowel lengths, flat synthesis models produce ambiguous, flat, or robotic speech. Furthermore, standard cloud-based text-to-speech (TTS) systems are unusable in West Africa due to high internet costs, erratic connectivity, and expensive API overhead.

### The Research Innovation
ADAB Tech proposes the development of a sovereign, linguistically-grounded, multi-speaker Text-to-Speech engine optimized for edge deployment. Our primary scientific innovation is the integration of a **Grapheme-to-Phoneme (G2P) hooked character parser** combined with **Litvinova's Right-to-Left Tonal Melody mapping** directly into the encoder of a Variational Inference with adversarial learning (VITS) architecture. By converting the resulting model to an INT8-quantized ONNX format, we enable real-time, high-fidelity conversational speech synthesis directly on low-resource CPU devices.

### Commercial Impact
This research will bridge the digital divide in West Africa, enabling local banks, healthcare providers, and educational groups to deploy offline-first voice assistants. It lowers the barrier of digital accessibility for semi-literate and illiterate demographics, representing a multi-billion dollar market expansion in the fastest-growing demographic region in the world.

---

## 2. Technical Discussion & Innovation

Traditional speech synthesis models treat low-resource languages as simplified ASCII subsets. For Hausa, this causes two critical failures:
1.  **Orthography Corruption:** Ignoring hooked letters (`ɓ`, `ɗ`, `ƙ`, `ƴ`) changes word definitions (e.g. *ɗan* "son of" vs. *dan* "for").
2.  **Tonal Flattening:** Ignoring High (H) and Low (L) pitch accents removes phonemic meaning. For example, *fada* can be *fádà* (palace) or *fádaá* (speaking/fighting).

```
Raw Text ─> [G2P Hook Normalizer] ─> [Syllable Segmenter] ─> [R-to-L Pitch Accent Mapper] ─> Vocab Tokenizer ─> VITS Encoder
```

### Computational Linguistics Pipeline
Our proprietary pipeline processes text prior to model encoding:
*   **Orthography Normalizer:** Reconstructs simplified input sequences (e.g., `d'`, `b'`) to proper Unicode hooked representations.
*   **Syllable Weight Parser:** Segments words into syllables, identifying syllable weight (Light CV vs. Heavy CVC/CVV).
*   **R-to-L Tonal Melody Mapper:** Employs a combination of a lexical dictionary and deterministic syllable weight rules to map tones from right to left, annotating target vowels with explicit pitch markers (`́` or `̀`).
*   **Edge Optimizer:** Applies dynamic range INT8 quantization to the trained ONNX graph, shrinking the model from ~1.2GB to ~250MB, making CPU execution feasible under 150ms.

---

## 3. Phase I Research Objectives

During the Phase I R&D cycle, ADAB Tech will focus on proving the technical feasibility of this linguistic-neural pipeline:

*   **Objective 1: Lexical Tone Dictionary Expansion (Target: >95% Accuracy)**
    *   *Task:* Expand the lexical tone dictionary to cover the top 1,500 conversational words.
    *   *Metric:* Achieve a dictionary hit rate of >90% on conversational speech benchmarks, measured by our local sovereign auditing suite.
*   **Objective 2: Multi-Speaker VITS Convergence & MOS Evaluation**
    *   *Task:* Train our multi-speaker model on the Google WAXAL corpus to 1,000 epochs.
    *   *Metric:* Conduct a double-blind Mean Opinion Score (MOS) test with 50 native speakers in Nigeria, targeting a MOS score of >4.0 (comparable to natural human speech).
*   **Objective 3: Edge-Optimization and RTF Benchmarking**
    *   *Task:* Quantize the trained VITS graph to INT8 ONNX format.
    *   *Metric:* Benchmarking on standard ARM Cortex-A CPU devices, targeting a Real-Time Factor (RTF) of >5.0x and synthesis latency of <120ms.

---

## 4. Commercial Opportunity & Market Validation

Our target commercial avenues include:
*   **Fintech & Financial Inclusion:** Integrating offline voice synthesis into POS terminals, mobile wallets, and banking IVRs to allow rural, non-literate merchants to receive voice transaction confirmations in native Hausa.
*   **Health & Public Services:** Partnering with international NGOs to deploy local-first, tablet-based medical and agricultural advisory systems that talk directly to users without internet dependencies.
*   **Education Tech:** Pre-installing natural Hausa voices on low-cost devices for literacy and vocational training programs in the Sahel region.
