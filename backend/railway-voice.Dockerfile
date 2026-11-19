FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir 'fastapi>=0.115,<1' 'uvicorn>=0.30,<1' \
    'onnxruntime>=1.18,<2' 'numpy>=1.26,<3' 'unicodedata2>=16,<18' \
    'gyara @ https://github.com/adab-tech/gyara/archive/9d3b8afdfe22aa789f200c18559d73a875ce2bfa.zip'

ARG MURYA_MODEL_REVISION
RUN python -c 'import os,re,pathlib,urllib.request; revision=os.environ["MURYA_MODEL_REVISION"]; assert re.fullmatch("[0-9a-f]{40}", revision), "Use a Hugging Face commit SHA"; root=pathlib.Path("/app/model"); root.mkdir(); base=f"https://huggingface.co/adab-tech/murya-piper-hausa-tts/resolve/{revision}"; [urllib.request.urlretrieve(f"{base}/{name}", root / name) for name in ("model.onnx", "model.onnx.json")]'

COPY backend/services/vits_engine.py /app/vits_engine.py
COPY backend/voice_preview.py /app/voice_preview.py
ENV VITS_MODEL_DIR=/app/model VITS_LENGTH_SCALE=1.25 VITS_NOISE_W=0.3
RUN useradd --no-create-home --uid 10001 murya
USER murya
CMD ["sh", "-c", "exec uvicorn voice_preview:app --host 0.0.0.0 --port ${PORT:-8000}"]
