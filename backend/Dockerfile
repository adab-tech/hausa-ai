# ==========================================
# Stage 1: Build the React/Vite Frontend
# ==========================================
FROM node:20-slim AS frontend-builder
WORKDIR /build

# Copy frontend package manifests first to leverage Docker cache
COPY package*.json ./
RUN npm ci

# Copy all required frontend source files
COPY tsconfig.json vite.config.ts index.html index.css index.tsx App.tsx types.ts ./
COPY components/ ./components/
COPY services/ ./services/
COPY utils/ ./utils/
COPY hausa_ai_banner.png ./hausa_ai_banner.png

# Build static assets (generates /build/dist)
RUN npm run build

# ==========================================
# Stage 2: Build the FastAPI Backend
# ==========================================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for faster-whisper and piper-tts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend source files
COPY backend/ ./

# Copy compiled frontend from Stage 1 into the backend container
COPY --from=frontend-builder /build/dist ./dist

# Expose port
EXPOSE 8000

# Run FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
