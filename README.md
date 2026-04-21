<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Hausa AI — Self-Hosted Open-Source AI Stack

Hausa AI is a full-stack app with a TypeScript/React/Vite frontend and a FastAPI backend that serves local/self-hosted AI capabilities.

## Architecture

- **Frontend:** TypeScript + React + Vite
- **Backend:** FastAPI (`backend/`)
  - `POST /api/chat`
  - `POST /api/generate-image`
  - `POST /api/generate-video`
  - `WS /api/live`
  - `GET /health`
- **Models/services:**
  - **Ollama** (default `aya-expanse:8b`)
  - **Diffusers** (default `black-forest-labs/FLUX.1-schnell`)
  - **Whisper** (speech-to-text)
  - **Piper** (text-to-speech)

Backend interactive API docs are available at `http://localhost:8000/docs`.

## Run options

### 1) Docker Compose (recommended)

```bash
docker compose up --build
```

Open:
- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`

### 2) GitHub Codespaces / devcontainer

1. Open the repo in Codespaces.
2. `.devcontainer/setup.sh` runs on create.
3. Start backend: `cd backend && uvicorn main:app --reload --port 8000`
4. Start frontend: `npm run dev`

### 3) Local development (split terminals)

```bash
# Terminal 1: Ollama
ollama serve
ollama pull aya-expanse:8b

# Terminal 2: Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 3: Frontend
cd ..
npm install
npm run dev
```

## Environment variables

Commonly used settings and defaults:

| Variable | Default | Used by |
|---|---|---|
| `VITE_BACKEND_URL` | `http://localhost:8000` | Frontend |
| `OLLAMA_HOST` | `http://ollama:11434` (Compose) | Backend |
| `OLLAMA_MODEL` | `aya-expanse:8b` | Backend/Ollama |
| `IMAGE_MODEL` | `black-forest-labs/FLUX.1-schnell` | Backend/Diffusers |
| `IMAGE_DEVICE` | `cpu` | Backend/Diffusers |
| `VIDEO_MODEL` | `damo-vilab/text-to-video-ms-1.7b` | Backend/Diffusers |
| `VIDEO_DEVICE` | `cpu` | Backend/Diffusers |
| `WHISPER_MODEL` | `base` | Backend/Whisper |
| `PIPER_MODELS_DIR` | `/models/piper` | Backend/Piper |
| `PIPER_MODEL` | `ha_NG-openbible-medium` | Backend/Piper |

## Model assets and large downloads

- `ollama pull <model>` downloads LLM weights into Ollama storage.
- Diffusers models are downloaded/cached on first use (Hugging Face cache).
- Piper voice files are downloaded to `PIPER_MODELS_DIR`.
- **Do not commit model weights or cache artifacts** to git.

## Troubleshooting

- Ensure required ports are free: `3000` (frontend), `8000` (backend), `11434` (Ollama).
- CPU mode works but image/video generation can be slow; prefer GPU (`IMAGE_DEVICE=cuda`, `VIDEO_DEVICE=cuda`) when available.
- Check backend health at `http://localhost:8000/health`.
- Use API docs at `http://localhost:8000/docs` to verify request/response formats.

## Deployment

- Cloud Run deployment (GitHub Actions + Workload Identity Federation): [docs/deploy-cloud-run.md](docs/deploy-cloud-run.md)

## Documentation map

See [docs/README.md](docs/README.md) for the docs index.
