# Vertex Sovereign — Self-Hosted Backend

FastAPI backend that replaces all Google Gemini API calls with open-source equivalents:

| Capability | Original (Google) | Self-hosted |
|---|---|---|
| Text generation | Gemini 3 Pro | **Aya-Expanse 8B** via Ollama |
| Image generation | Gemini 3 Pro Image | **FLUX.1-schnell** via Diffusers |
| Live audio (voice) | Gemini 2.5 Flash Native Audio | **Whisper + Ollama + Piper TTS** |
| Video generation | Veo 3.1 | Stub (see below) |

---

## Quick Start

### Option A — Docker Compose (recommended)

```bash
docker compose up --build
```

This starts Ollama, pulls the Hausa model, and launches the backend and frontend.  
Open `http://localhost:3000`.

### Option B — GitHub Codespaces

1. Open the repo in Codespaces with a **4-core GPU** machine type.
2. The `postCreateCommand` runs `.devcontainer/setup.sh` automatically.
3. Start the backend: `cd backend && uvicorn main:app --reload`
4. Start the frontend: `npm run dev`

### Option C — Local development

```bash
# Start Ollama
ollama serve &
ollama pull aya-expanse:8b

# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd ..
npm install
npm run dev
```

---

## Configuration

All settings are via environment variables:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `aya-expanse:8b` | LLM model name |
| `IMAGE_MODEL` | `black-forest-labs/FLUX.1-schnell` | Diffusers model |
| `IMAGE_DEVICE` | `cpu` | `cpu` or `cuda` |
| `WHISPER_MODEL` | `base` | `tiny`/`base`/`small`/`medium` |
| `PIPER_MODELS_DIR` | `/models/piper` | Directory for Piper ONNX voice files |
| `PIPER_MODEL` | `ha_NG-openbible-medium` | Piper voice name |
| `VITE_BACKEND_URL` | `http://localhost:8000` | Frontend → backend URL |

---

## Model Recommendations

### Text (Hausa-capable LLMs)

| Model | VRAM | License | Notes |
|---|---|---|---|
| **aya-expanse:8b** (default) | 8 GB | Apache 2.0 | Best Hausa coverage; purpose-built for low-resource languages |
| `llama3.1:8b` | 8 GB | Meta Community | Strong multilingual |
| `qwen2.5:7b` | 6 GB | Apache 2.0 | Excellent on low-resource languages |
| `mistral:7b` | 6 GB | Apache 2.0 | Good general multilingual |

To change: `OLLAMA_MODEL=llama3.1:8b docker compose up`

### Image

| Model | VRAM | License | Notes |
|---|---|---|---|
| **FLUX.1-schnell** (default) | 14 GB / slow on CPU | Apache 2.0 | Best quality |
| `stabilityai/stable-diffusion-2-1` | 8 GB | CreativeML Open RAIL | Good quality |
| `runwayml/stable-diffusion-v1-5` | 4 GB | CreativeML Open RAIL | Lightest |

To change: `IMAGE_MODEL=runwayml/stable-diffusion-v1-5 docker compose up`

### Voice (Hausa TTS)

Download the Piper Hausa voice model:

```bash
mkdir -p /models/piper
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/ha/NG/openbible/medium"
curl -L -o /models/piper/ha_NG-openbible-medium.onnx      "$BASE/ha_NG-openbible-medium.onnx"
curl -L -o /models/piper/ha_NG-openbible-medium.onnx.json "$BASE/ha_NG-openbible-medium.onnx.json"
```

---

## Video Generation (Roadmap)

Video generation is currently stubbed (`/api/generate-video` returns `{"uri": null}`).

To enable it, replace the stub in `routers/image.py` with:

- **[CogVideoX-5B](https://github.com/THUDM/CogVideo)** — Apache 2.0, text-to-video, requires ~24 GB VRAM
- **[Stable Video Diffusion](https://huggingface.co/stabilityai/stable-video-diffusion-img2vid)** — image-to-video

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/chat` | POST | Streaming SSE text generation |
| `/api/generate-image` | POST | Image generation (base64 PNG) |
| `/api/generate-video` | POST | Video generation (stub) |
| `/api/live` | WS | Bidirectional voice (STT + LLM + TTS) |
| `/health` | GET | Health check |

Interactive docs: `http://localhost:8000/docs`
