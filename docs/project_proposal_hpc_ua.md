# Project Proposal: Sovereign Speech Synthesis and Cultural Alignment for Low-Resource Languages

**Target Institution:** University of Alabama High Performance Computing (hpc.ua.edu) & The Planned Center for Data  
**Proposer:** Adamu Abubakar (Lead Developer & Computational Linguist, adab-tech)  
**Project Title:** *Sovereign Voices: High-Fidelity Speech Synthesis and Culturally Grounded NLP for the Hausa Language*

---

## 1. Executive Summary

This proposal outlines a research project to develop a high-fidelity, culturally aligned speech synthesis (Text-to-Speech) and conversational AI pipeline for the **Hausa language**—a low-resource language spoken by over 80 million people in West Africa. 

While commercial AI systems (e.g., Google, OpenAI) fail to capture the phonetic nuances (such as phonemic vowel length, hooked consonants `ɓ, ɗ, ƙ, ƴ`, and tone melodies) of Hausa, this project introduces a linguistically grounded framework. We propose training a multi-speaker **VITS (Variational Inference with adversarial learning)** TTS model on the 13-hour WAXAL corpus, integrated with custom orthographic normalization and Right-to-Left tonal melody mappings. 

By leveraging the advanced GPU acceleration of the **University of Alabama HPC cluster (hpc.ua.edu)**, we aim to demonstrate how academic high-performance computing can serve as a catalyst for sovereign language preservation and low-resource NLP. This project aligns directly with the UA **Center for Data's** mission to leverage advanced data analytics, high-performance architectures, and machine learning to solve complex global and societal challenges.

---

## 2. Background and Significance

### The Linguistic Gap in Modern NLP
Most commercial NLP and speech models are designed around high-resource, non-tonal Western languages. Low-resource, tonal languages like Hausa are poorly served:
1.  **Orthography Ignorance:** Hooked letters (`ɓ`, `ɗ`, `ƙ`, `ƴ`/`y̰`) are frequently normalized to basic ASCII characters (`b`, `d`, `k`, `y`), completely altering word meaning (e.g., *fada* [palace] vs. *faɗa* [fighting/speaking]).
2.  **Tonal Neglect:** Hausa utilizes high, low, and falling tones that carry both lexical and grammatical weight. Default TTS models sound highly robotic because they lack a model for Hausa's prosodic structure.
3.  **Cultural Disconnect:** Conversational interfaces fail to adhere to West African socio-linguistic protocols, such as the *Plural of Respect* (addressing users as *Ku*/*Su*) and cultural courtesy protocols (*Kunya* and *Girmamawa*).

### The Scientific Opportunity
By formalizing phonetic and prosodic rules—specifically **Litvinova's Right-to-Left Tonal Melody Mapping**—into neural speech training, we can build a voice engine that achieves human-like prosodic naturalness. 

---

## 3. Technical Approach and Methodology

We propose a hybrid local-cloud pipeline divided into three core stages:

```
[Text Input] ──> [Orthography Normalization] ──> [R-to-L Tone Annotation (IPA)] 
                                                                │
[High-Fidelity Audio Output] <── [VITS Multi-Speaker TTS] <─────┘
```

### Stage 1: Linguistic Pre-processing & Normalization
*   **Grapheme-to-Phoneme (G2P):** We map standard Hausa text to the International Phonetic Alphabet (IPA) utilizing the `Epitran` G2P converter.
*   **Prosodic Annotation:** Syllables are segmented and annotated with tone registers (`H` and `L`) using a rule-based algorithm implementing R-to-L melody mappings.
*   **Orthographic Hardening:** Hooked consonants are programmatically validated and normalized to Unicode block standards.

### Stage 2: Neural Speech Synthesis (VITS)
*   **Model Architecture:** We employ the VITS (Variational Inference with adversarial learning) model, which generates raw audio waveforms directly from text in an end-to-end, fully differentiable manner.
*   **Multi-Speaker Setup:** The model will learn speaker embeddings from the 8-speaker (4 Male, 4 Female) WAXAL corpus to enable controllable, high-fidelity voice cloning.
*   **Training Configuration:** We target 1,000 to 4,000 epochs (~300,000 steps) of training on a single CUDA-enabled GPU (Tesla T4, L4, or A100).

### Stage 3: Culturally Grounded Conversational AI
*   The speech engine will connect to an **Aya-23 8B** or **Llama 3.1** model hosted locally or via API, utilizing system instructions that enforce cultural courtesy rules.

---

## 4. Computational Requirements on hpc.ua.edu

Deep neural TTS models require high-performance parallel computing. The university's HPC cluster is the ideal environment to run this work:

1.  **GPU Accelerators:** We request access to **1x NVIDIA GPU** (Tesla T4, L4, or A100) on the cluster for the neural network training. A single model run takes approximately 30 to 60 hours of GPU time.
2.  **Multiprocessing CPU Allocation:** We require **4 CPU cores** and **32 GB RAM** per training task to manage parallel dataset loading, audio resampling, and real-time validation logging.
3.  **Storage footprint:**
    *   **WAXAL Dataset**: ~2 GB (audio and text manifests).
    *   **Checkpoints and Model Weights**: ~20 GB (saving checkpoints every 2,000 steps for verification).

---

## 5. Alignment with the UA Center for Data

This project directly aligns with the upcoming **Center for Data's** strategic goals:

*   **Advanced Data Processing:** Developing automated workflows to process, validate, and clean massive multilingual audio corpora.
*   **Interdisciplinary Science:** Bridging the gap between High-Performance Computing (HPC), Artificial Intelligence, and African Linguistics.
*   **Societal Impact:** Building technology that preserves low-resource languages, prevents linguistic marginalization in the digital age, and provides accessible voice interfaces for literacy-limited populations.

---

## 6. Expected Outcomes and Deliverables

1.  **Academic Publications:** Submissions to NLP and speech conferences (e.g., Interspeech, ACL, AfricaNLP).
2.  **Open-Source Contributions:** Releasing the custom Hausa tone-mapping tokenizer, G2P mappings, and VITS model weights to the research community.
3.  **Software Toolkit:** A production-ready API (FastAPI backend + React frontend) capable of running speech-to-text, LLM, and high-fidelity text-to-speech completely local-first.

---

## 7. Immediate Next Steps

If granted access to hpc.ua.edu:
1.  **Clone code and prepare directories:** Install virtual environments and transfer the project code.
2.  **Download GCS Staged Data:** Run the dataset downloader (`download_dataset.py`) to fetch files from GCS.
3.  **Submit Training Job:** Launch VITS training using the pre-configured Slurm job submission script (`train_vits.slurm`).
