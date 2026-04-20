#!/usr/bin/env bash
# .devcontainer/setup.sh
# Run automatically by postCreateCommand in devcontainer.json

set -e

echo "=== Vertex Sovereign — Codespaces Setup ==="

# ── 1. Install Ollama ────────────────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
  echo "Installing Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
fi

# Start Ollama in the background
ollama serve &>/tmp/ollama.log &
sleep 5

# Pull the Hausa-capable model (change to llama3.1:8b if preferred)
OLLAMA_MODEL="${OLLAMA_MODEL:-aya-expanse:8b}"
echo "Pulling Ollama model: $OLLAMA_MODEL (this may take a few minutes)..."
ollama pull "$OLLAMA_MODEL"

# ── 2. Python backend deps ───────────────────────────────────────────────────
echo "Installing Python dependencies..."
pip install --quiet -r backend/requirements.txt

# ── 3. Node.js frontend deps ─────────────────────────────────────────────────
echo "Installing Node dependencies..."
npm install

# ── 4. Download Piper Hausa TTS voice ────────────────────────────────────────
PIPER_DIR="${PIPER_MODELS_DIR:-/models/piper}"
PIPER_MODEL="${PIPER_MODEL:-ha_NG-openbible-medium}"
mkdir -p "$PIPER_DIR"

if [ ! -f "$PIPER_DIR/${PIPER_MODEL}.onnx" ]; then
  echo "Downloading Piper Hausa TTS voice: $PIPER_MODEL..."
  BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/ha/NG/openbible/medium"
  curl -L --retry 3 -o "$PIPER_DIR/${PIPER_MODEL}.onnx"      "${BASE_URL}/${PIPER_MODEL}.onnx"
  curl -L --retry 3 -o "$PIPER_DIR/${PIPER_MODEL}.onnx.json" "${BASE_URL}/${PIPER_MODEL}.onnx.json"
  echo "Piper voice downloaded."
else
  echo "Piper voice already present."
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "To start the stack:"
echo "  Terminal 1: cd backend && uvicorn main:app --reload"
echo "  Terminal 2: npm run dev"
echo ""
echo "Or use Docker Compose: docker compose up --build"
