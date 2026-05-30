#!/usr/bin/env bash
# utils/setup_training_env.sh
# Sets up VITS model training dependencies on an Ubuntu/Debian host (e.g. GitHub Codespaces or Azure GPU VM)

set -e

echo "=== Setting up HAUSA AI VITS Training Environment ==="

# 1. Install system audio and phonemizer dependencies
echo "Installing system packages (espeak-ng, libsndfile1, ffmpeg)..."
sudo apt-get update && sudo apt-get install -y \
  espeak-ng \
  libsndfile1 \
  ffmpeg \
  git \
  curl

# 2. Upgrade pip
echo "Upgrading pip..."
python3 -m pip install --upgrade pip

# 3. Install core PyTorch and Torchaudio (CUDA-enabled if GPU available)
if command -v nvidia-smi &>/dev/null; then
  echo "GPU detected. Installing CUDA-enabled PyTorch..."
  python3 -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
else
  echo "No GPU detected. Installing standard PyTorch..."
  python3 -m pip install torch torchaudio
fi

# 4. Install training and cloud dependencies
echo "Installing Coqui TTS, GCS, and Hugging Face datasets..."
python3 -m pip install \
  coqui-tts \
  google-cloud-storage \
  datasets \
  transformers \
  accelerate

# 5. Verify installations
echo "--- Verification ---"
python3 -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA Available:', torch.cuda.is_available())"
python3 -c "import TTS; print('Coqui TTS successfully imported!')"

echo ""
echo "=== Setup Complete ==="
echo "You are ready to sync your dataset and run training!"
echo "Step 1: Authenticate with GCP: gcloud auth login"
echo "Step 2: Sync audio: gsutil -m rsync -r gs://hausa-ai-waxal-studio-980910821-5b814/audio ./waxal_hausa/audio"
echo "Step 3: Run training script: python3 utils/train_vits_gcp.py"
