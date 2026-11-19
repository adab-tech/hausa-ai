FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir 'fastapi>=0.115,<1' 'uvicorn>=0.30,<1' \
    'onnxruntime>=1.18,<2' 'numpy>=1.26,<3' 'unicodedata2>=16,<18' \
    'bcrypt>=4,<6' 'slowapi>=0.1.9,<1' 'python-multipart>=0.0.20,<1' \
    'pydub>=0.25,<1' \
    'gyara @ https://github.com/adab-tech/gyara/archive/9d3b8afdfe22aa789f200c18559d73a875ce2bfa.zip'

ARG MURYA_MODEL_REVISION
RUN python -c 'import os,re,pathlib,urllib.request; revision=os.environ["MURYA_MODEL_REVISION"]; assert re.fullmatch("[0-9a-f]{40}", revision), "Use a Hugging Face commit SHA"; root=pathlib.Path("/app/model"); root.mkdir(); base=f"https://huggingface.co/adab-tech/murya-piper-hausa-tts/resolve/{revision}"; [urllib.request.urlretrieve(f"{base}/{name}", root / name) for name in ("model.onnx", "model.onnx.json")]'

COPY backend/services/vits_engine.py /app/vits_engine.py
COPY backend/voice_preview.py backend/start_voice_preview.py backend/admin_store.py backend/admin_audit_store.py backend/auth.py backend/contributor.py backend/pronunciation_store.py backend/rate_limit.py /app/
COPY backend/routers/admin_auth.py backend/routers/pronunciation.py /app/routers/
ENV VITS_MODEL_DIR=/app/model VITS_LENGTH_SCALE=1.25 VITS_NOISE_W=0.3 APP_ENV=production FEEDBACK_DATA_DIR=/app/review-data/db
RUN groupadd --gid 10001 murya && useradd --no-create-home --uid 10001 --gid 10001 murya
CMD ["python", "/app/start_voice_preview.py"]
