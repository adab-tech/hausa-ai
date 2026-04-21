"""
Vertex Sovereign — Self-Hosted Backend
FastAPI app that replaces Google Gemini/Veo/Live APIs with open-source equivalents:
  • Text  : Ollama (Aya-23 8B / Llama 3.1 8B)
  • Image : Diffusers FLUX.1-schnell / Stable Diffusion
  • Audio : faster-whisper (STT) + Ollama (LLM) + Piper TTS
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chat, image, audio

app = FastAPI(
    title="Vertex Sovereign — Local AI Backend",
    description="Self-hosted replacement for Google Gemini APIs",
    version="1.0.0",
)

# Allow any origin (open self-hosted API — no cookie-based auth is used)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(image.router, prefix="/api")
app.include_router(audio.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "sovereign", "version": "1.0.0"}
