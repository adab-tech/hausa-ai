#!/bin/sh
# Boots Ollama (the local LLM behind /api/chat and /api/live) alongside
# FastAPI in the same container. OLLAMA_MODELS points at the persistent
# volume (/app/data) so the pulled model survives redeploys/restarts —
# only the very first boot pays the download cost.
set -e

export OLLAMA_MODELS="${OLLAMA_MODELS:-/app/data/ollama-models}"
mkdir -p "$OLLAMA_MODELS"

echo "[start.sh] Starting Ollama server..."
ollama serve &

# Pull the model in the background so FastAPI's health check isn't gated on
# a multi-GB download completing. Chat requests fall back to the static
# template (see routers/fallback.py) until this finishes on first boot.
(
  MODEL="${OLLAMA_MODEL:-aya-expanse:8b}"
  for i in $(seq 1 30); do
    if curl -fsS http://localhost:11434/api/version >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
  if ! ollama list 2>/dev/null | grep -q "$(echo "$MODEL" | cut -d: -f1)"; then
    echo "[start.sh] Pulling Ollama model $MODEL (first boot only)..."
    ollama pull "$MODEL" || echo "[start.sh] WARNING: model pull failed — chat will use the Gemini/static fallback until this succeeds."
  else
    echo "[start.sh] Model $MODEL already present on the persistent volume."
  fi
) &

echo "[start.sh] Starting FastAPI..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
