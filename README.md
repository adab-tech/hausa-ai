<div align="center">
  <img width="1200" alt="Murya Banner" src="./hausa_ai_banner.png" />
</div>

# Murya — Sovereign Hausa AI

**Murya** (murya.ng) is an industry-grade, local-first computational linguistics and artificial intelligence stack designed specifically to capture the phonological, orthographic, and cultural nuances of the **Hausa language** — the first in a planned line of sovereign, native-speaker-built AI products from ADAB-TECH Labs. 

The system integrates a high-performance **FastAPI backend** running local neural models with a premium **TypeScript/React/Vite web client** to enable fully private text, image, and voice interaction without relying on third-party cloud services.

---

## 🚀 Architectural Blueprint & Sovereign Stack

| Capability | Local / Edge Stack (Sovereign) | Cloud / API Fallback |
| :--- | :--- | :--- |
| **Text Generation** | **Aya-Expanse 8B / Aya-23** via Ollama | **Vertex AI / Gemini 1.5** (Application Default Credentials fallback) |
| **Speech-to-Text (STT)** | **Faster-Whisper (base)** (Optimized mono 16kHz) | Local offline rule-based processor |
| **Text-to-Speech (TTS)** | **WAXAL-Piper 8-voice Hausa model** (grapheme-mode fine-tune, 73.5 MB ONNX, CPU real-time) | Legacy VITS / Piper baseline |
| **Image Generation** | **FLUX.1-schnell** (Diffusers) | Local offline fallback |
| **Linguistic Trace** | Right-to-Left Tonal Melody & Hook Normalizer | In-client **Axiom Trace** |

---

## 🎙️ The WAXAL–Piper Hausa voices (July 2026)

The app speaks with **8 native Hausa voices** (M1–M4, F1–F4) fine-tuned on
Google's [WAXAL](https://huggingface.co/datasets/google/WaxalNLP) corpus — to
our knowledge the **first WAXAL-trained TTS built by a native speaker of the
target language**. Highlights (full write-up:
[`docs/waxal_piper_technical_report.md`](docs/waxal_piper_technical_report.md)):

- **Grapheme-mode training** with a custom 42-symbol Hausa alphabet — espeak-ng
  has no Hausa voice, so the orthography itself (ɓ ɗ ƙ ƴ as first-class
  symbols) is the model input.
- **Corpus multiplication:** character-level forced alignment recovered 1,723
  sentence segments from long/digit-bearing clips, growing usable audio from
  2.83 h to **6.03 h** with no new recordings.
- **Native-speaker-in-the-loop evaluation** gated every decision: base-model
  selection (Meta MMS-Hausa auditioned and rejected), data certification, and
  the epoch budget (300 → 2,000, verified improving at each probe).
- Deployed model: `models/piper_hausa_waxal/model.onnx` (73.5 MB, 22.05 kHz,
  MIT-licensed pipeline; **cite Google WAXAL when publishing derivatives**).

Train / evaluate / segment with:

```bash
.\utils\run_training.ps1                      # preflight → Modal → log → diagnose
modal run finetune_piper_hausa_modal.py::evaluate   # audition any checkpoint
modal run --detach segment_waxal_modal.py     # corpus recovery pipeline
```

---

## 📚 Reference lexicon: Robinson (1914)

The project archives **Charles H. Robinson’s** *Dictionary of the Hausa Language*, Vol. II (English–Hausa, Cambridge, 1914), digitized by the [Internet Archive](https://archive.org/details/dictionaryofhaus02robiuoft) (University of Toronto Robarts Library).

| Asset | Path |
| :--- | :--- |
| PDF + OCR + attribution | `data/sources/robinson-dictionary/` |
| Parsed JSONL / search index | `robinson_en_ha.jsonl`, `robinson_en_ha_index.json` |
| ML pair export | `data/processed/robinson/en_ha_pairs.jsonl` |

```bash
python utils/extract_robinson_dictionary.py
python utils/prepare_robinson_ml.py
```

Always cite Robinson and the Archive item when publishing derivatives (see `data/sources/robinson-dictionary/ATTRIBUTION.md`).

---

## 🎯 Core Linguistic sovereign features

Hausa is a tonal language with complex orthographic characters neglected by standard commercial LLMs. Hausa AI implements a pure-Python native linguistic pipeline:

### 1. Orthographic Hook Normalization
Standardizes raw ASCII input and corrects missing diacritics to proper Unicode equivalents:
*   `b'` / `B'` ➔ **ɓ** / **Ɓ** (bilabial implosive)
*   `d'` / `D'` ➔ **ɗ** / **Ɗ** (alveolar implosive)
*   `k'` / `K'` ➔ **ƙ** / **Ƙ** (velar ejective)
*   `'y` / `Y'` ➔ **ƴ** / **Ƴ** (palatalized glottal stop)
*   `ts'` / `Ts'` ➔ **ts** / **Ts** (alveolar ejective)

### 2. Litvinova Right-to-Left Tonal Melody Mapping
Since tone is unmarked in standard Hausa orthography, the system analyzes word syllable weights:
1.  **Syllable Segmentation**: Splits text into light (CV) and heavy (CVV, CVC) syllables.
2.  **R-to-L Mapping**: Assigns high (`́`) and low (`̀`) pitch contours backwards from the end of each word.
3.  **Synthesis Injection**: Feeds prosodic markers directly into the custom VITS generator for natural pronunciation.

### 3. Cultural Protocols (Kunya & Girmamawa)
System prompts enforce strict cultural alignment:
*   **Plural of Respect**: Enforces addressing users respectfully (*Ku*, *Su*, *Kun*, *Sun*).
*   **Honorific Greetings**: Mandatory inclusion of respect markers (*Ranka ya daɗe* / *Ranki ya daɗe*).
*   **Kunya (Modesty)**: Automatically uses metaphors for sensitive topics.

---

## 🎙️ Live Bidirectional Voice Engine (`/api/live`)

The stack features a real-time WebSocket connection for voice conversation, replacing cloud live streaming with an offline pipeline:
1.  **Ingestion**: Client streams raw 16kHz mono PCM-16 audio over WebSockets.
2.  **Transcription**: Accumulates ~2 seconds of audio frames and transcribes using **Faster-Whisper**.
3.  **Cognition**: Processes the transcript through the LLM pipeline (Ollama with fallback to Vertex AI).
4.  **Linguistic Trace**: Annotates the text response using R-to-L tonal heuristics.
5.  **Synthesis**: Feeds the tone-mapped text into the custom **VITS ONNX model** (or baseline Piper TTS).
6.  **Streaming**: Streams 24kHz PCM-16 audio chunks back to the client for zero-latency voice feedback.

---

## 🛠️ Root Diagnostic & Optimization Utilities

We maintain root scripts to benchmark and audit the sovereign pipeline:

*   **[`sovereign_auditor.py`](file:///C:/Users/Adamu/Desktop/HAUSA%20AI/sovereign_auditor.py)**: Performs an automated linguistic audit over test sentences. It calculates word syllable splits, dictionary matching efficiency, orthography correction success rates, and outputs a final **Sovereign Linguistic Score**.
*   **[`flywheel_optimizer.py`](file:///C:/Users/Adamu/Desktop/HAUSA%20AI/flywheel_optimizer.py)**: Runs latency benchmarks. It measures the execution speed of orthography-to-tone processing and calculates the Real-Time Factor (RTF) of the VITS ONNX model to verify inference efficiency on edge CPU/GPU.

---

## 📊 WAXAL Dataset Diagnostics (`/api/waxal/*`)

The backend contains a dedicated dataset inspector at [**`backend/routers/waxal.py`**](file:///C:/Users/Adamu/Desktop/HAUSA%20AI/backend/routers/waxal.py) to audit and query the local training corpus:
*   **Dataset Stats (`GET /api/waxal/stats`)**: Generates real-time statistics including speaker gender distribution, average/min/max sentence word count, vocabulary type-to-token ratio (TTR), and exact counts of Unicode vs. simplified ASCII hooked letters in the transcriptions.
*   **Interactive Search (`GET /api/waxal/samples`)**: Provides paginated, searchable access to the 1,970 samples, filterable by speaker ID, gender, or transcription content.
*   **Audio Streaming (`GET /api/waxal/audio/{filename}`)**: Serves target staged WAXAL audio recordings directly to check pronunciation nuances.

---

## 🏋️ Model Training & HPC Scaling Workflows

We train our custom **VITS multi-speaker models** using Google's high-fidelity **WAXAL Hausa dataset** (1,970 samples). Due to compute constraints, we support two distinct workflows:

### Option A: Google Colab (T4 GPU Environment)
For low-barrier model training:
1.  See the full guide in [**`docs/colab_resuming_guide.md`**](file:///C:/Users/Adamu/Desktop/HAUSA%20AI/docs/colab_resuming_guide.md).
2.  Run [**`utils/prepare_colab_env.py`**](file:///C:/Users/Adamu/Desktop/HAUSA%20AI/utils/prepare_colab_env.py) in your notebook to download manifests, dataset manifests, and resume checkpoints in parallel using 16 threads directly from GCS (`gs://hausa-ai-waxal-studio-980910821-5b814/`).
3.  Execute training:
    ```bash
    python -m TTS.bin.train_tts --config_path waxal_hausa/config.json
    ```

### Option B: University HPC Cluster (Slurm-Managed GPUs)
For high-throughput, private training on supercomputers:
1.  Set up environment: `bash utils/setup_training_env.sh`
2.  Authenticate GCS and download the WAXAL dataset:
    ```bash
    gcloud auth application-default login
    python utils/download_dataset.py
    ```
3.  Submit Slurm training script: `sbatch utils/train_vits.slurm`

---

## 🎓 Academic Strategy & Active Proposals

To support the funding and computational requirements of the project, we have drafted institutional proposals:
1.  **University of Alabama (UA) HPC Allocation**: Proposal to secure dedicated GPU partitions on `hpc.ua.edu` and the Center for Data ([**`docs/project_proposal_hpc_ua.md`**](file:///C:/Users/Adamu/Desktop/HAUSA%20AI/docs/project_proposal_hpc_ua.md)).
2.  **University of Ilorin (Unilorin) Affiliation**: Institutional collaboration draft to establish research affiliation in Nigeria, enabling eligibility for **AI4D Africa** and **Lacuna Fund** research grants ([**`docs/unilorin_ua_ai4d_pitch.md`**](file:///C:/Users/Adamu/Desktop/HAUSA%20AI/docs/unilorin_ua_ai4d_pitch.md)).
3.  **NSF-NEH DLI-DEL Grant**: Collaborative funding strategy under the Documenting Endangered Languages initiative.
4.  **WAXAL Corpus Reference**: Direct access to the core white paper [**`docs/waxal_white_paper.pdf`**](file:///C:/Users/Adamu/Desktop/HAUSA%20AI/docs/waxal_white_paper.pdf) documenting the high-fidelity multi-speaker training corpus.

---

## 💻 Local Development Setup

### 1. Environment Configurations
Configure your root `.env` (or copy `.env.example` if available):
```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=aya-expanse:8b
IMAGE_MODEL=black-forest-labs/FLUX.1-schnell
IMAGE_DEVICE=cpu
VIDEO_MODEL=damo-vilab/text-to-video-ms-1.7b
VIDEO_DEVICE=cpu
WHISPER_MODEL=base
PIPER_MODELS_DIR=models/piper
PIPER_MODEL=ha_NG-openbible-medium
VITE_BACKEND_URL=http://localhost:8000
```

### 2. Multi-Terminal Execution
*   **Terminal 1: Start local LLM (Ollama)**
    ```bash
    ollama serve
    ollama pull aya-expanse:8b
    ```
*   **Terminal 2: Start FastAPI Backend**
    ```bash
    cd backend
    python -m pip install -r requirements.txt
    python -m uvicorn main:app --reload --port 8000
    ```
*   **Terminal 3: Start Vite Frontend**
    ```bash
    npm install
    npm run dev
    ```
    Open `http://localhost:3000` to interact with the application.

---

## 🧪 Testing Suite

We maintain unit test suites for all backend core features:
```bash
cd backend
python -m pytest
```
*Current test metrics: **39/39 passed successfully, 66.12% code coverage**.*
