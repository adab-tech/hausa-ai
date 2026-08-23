# ==========================================
# Build the FastAPI Backend
# ==========================================
# API-only image — the real frontend is app.murya.ng, deployed separately
# on Vercel. This used to also build and bundle the React frontend for a
# single-container deploy, but that made api.murya.ng serve a second, stale
# copy of the app at "/", confusingly indistinguishable from the real one.
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for faster-whisper and piper-tts.
# zstd is required by Ollama's own install.sh to extract its release archive.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    zstd \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama — serves the local LLM behind /api/chat and /api/live.
# The model itself is NOT baked into the image (that would make every
# rebuild re-ship several GB); it's pulled at container boot into the
# persistent volume instead — see start.sh.
RUN curl -fsSL https://ollama.com/install.sh | sh

# Copy backend requirements and install dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend source files
COPY backend/ ./

# Bake in the trained WAXAL-Piper v2 TTS model (only the two files the engine
# needs at runtime; the rest of models/piper_hausa_waxal/ is eval audio). Without
# this the container has no voice model and TTS 500s. VITS_MODEL_DIR points the
# engine straight at it (the container flattens backend/ -> /app, so repo-relative
# auto-detection would miss it). NOTE: model.onnx (~73 MB) is not git-tracked, so
# a CI build (git checkout) needs it via Git LFS; a local `flyctl deploy` already
# has it in the build context.
COPY models/piper_hausa_waxal/model.onnx models/piper_hausa_waxal/model.onnx.json /app/models/piper_hausa_waxal/
ENV VITS_MODEL_DIR=/app/models/piper_hausa_waxal

# Bake in all THREE dictionary sources so the dictionary/translation tool works
# in the container. dictionary_service auto-detects these container paths and
# loads them together: Robinson (1914, public domain) for clean EN->HA, the
# open Wiktionary/Kaikki lexicon (CC-BY-SA) for clean HA->EN, and Newman &
# Newman (1977, ingestion approved directly by Prof. Paul Newman) also for
# clean HA->EN. We do NOT set DICTIONARY_PATH here — that env var is an
# authoritative single-file override that would suppress the secondary/
# tertiary sources; the auto-detected paths load all three.
#
# Deliberately under /app/dictionaries, NOT /app/data: the Fly persistent
# volume mounts at /app/data (see fly.toml [mounts]) and silently shadows
# anything baked into that path at build time. Confirmed live in production
# (2026-08-22) that all three sources were failing to load for exactly this
# reason — dictionary_ready() was False, /app/data/robinson/... never existed
# at runtime. Keep this path out of the volume's mount point.
COPY data/processed/robinson/en_ha_pairs.jsonl /app/dictionaries/robinson/en_ha_pairs.jsonl
COPY data/processed/hausa_en_open/ha_en_pairs.jsonl /app/dictionaries/hausa_en_open/ha_en_pairs.jsonl
COPY data/processed/newman_1977/ha_en_pairs_merged.jsonl /app/dictionaries/newman_1977/ha_en_pairs_merged.jsonl

RUN chmod +x /app/start.sh

# Expose port
EXPOSE 8000 8080

# Boots Ollama + FastAPI together — see start.sh
CMD ["/app/start.sh"]
