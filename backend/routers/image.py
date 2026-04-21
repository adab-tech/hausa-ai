"""
/api/generate-image  — image generation via Diffusers (FLUX.1-schnell or SD).
/api/generate-video  — text-to-video generation via Diffusers (ModelScope T2V).

POST /api/generate-image
  { "prompt": "...", "vibe": "Classic" }
  -> { "data": "data:image/png;base64,..." }

POST /api/generate-video
  { "prompt": "..." }
  -> { "uri": "data:video/mp4;base64,..." }
"""

import base64
import io
import logging
import os
import tempfile
from contextlib import suppress
from functools import lru_cache

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Image model selection — default to FLUX.1-schnell (Apache 2.0, fast CPU/GPU)
# ---------------------------------------------------------------------------
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
IMAGE_DEVICE = os.getenv("IMAGE_DEVICE", "cpu")  # "cuda" on GPU runners

# ---------------------------------------------------------------------------
# Video model selection — default to ModelScope T2V 1.7B (Apache 2.0)
# Override: VIDEO_MODEL=<hf-model-id> VIDEO_DEVICE=cuda
# VIDEO_DEVICE falls back to IMAGE_DEVICE at call-time, not at import-time.
# ---------------------------------------------------------------------------
VIDEO_MODEL = os.getenv("VIDEO_MODEL", "damo-vilab/text-to-video-ms-1.7b")
VIDEO_DEVICE = os.getenv("VIDEO_DEVICE", "cpu")


@lru_cache(maxsize=1)
def _get_image_pipeline():
    """Lazy-load the diffusion pipeline once and cache it."""
    import torch
    from diffusers import AutoPipelineForText2Image

    dtype = torch.float16 if IMAGE_DEVICE != "cpu" else torch.float32

    logger.info("Loading image pipeline: %s on %s", IMAGE_MODEL, IMAGE_DEVICE)
    pipe = AutoPipelineForText2Image.from_pretrained(
        IMAGE_MODEL,
        torch_dtype=dtype,
    )
    pipe = pipe.to(IMAGE_DEVICE)
    return pipe


@lru_cache(maxsize=1)
def _get_video_pipeline():
    """Lazy-load the text-to-video pipeline once and cache it."""
    import torch
    from diffusers import TextToVideoSDPipeline

    dtype = torch.float16 if VIDEO_DEVICE != "cpu" else torch.float32

    logger.info("Loading video pipeline: %s on %s", VIDEO_MODEL, VIDEO_DEVICE)
    pipe = TextToVideoSDPipeline.from_pretrained(VIDEO_MODEL, torch_dtype=dtype)
    pipe = pipe.to(VIDEO_DEVICE)
    return pipe


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------
class ImageRequest(BaseModel):
    prompt: str = Field(..., max_length=1_000)
    vibe: str = Field("Classic", pattern=r"^(Classic|Royal|Cyberpunk|Academic)$")


class VideoRequest(BaseModel):
    prompt: str = Field(..., max_length=1_000)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/generate-image")
async def generate_image(req: ImageRequest):
    full_prompt = (
        f"A majestic Hausa cultural scene in {req.vibe} style: {req.prompt}. "
        "Dignified, scholarly, authentic, 8k."
    )
    try:
        pipe = _get_image_pipeline()
        result = pipe(full_prompt, num_inference_steps=4, guidance_scale=0.0)
        img = result.images[0]
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {"data": f"data:image/png;base64,{b64}"}
    except Exception:
        logger.exception("Image generation failed")
        return {"data": None, "error": "Image generation failed. Check backend logs."}


@router.post("/generate-video")
async def generate_video(req: VideoRequest):
    """
    Text-to-video generation using the ModelScope TextToVideoSD pipeline.

    Default model: damo-vilab/text-to-video-ms-1.7b (Apache 2.0, ~3.5 GB download).
    Override via VIDEO_MODEL env var (e.g. a CogVideoX or SVD model).
    VIDEO_DEVICE defaults to IMAGE_DEVICE (cpu or cuda).

    Note: CPU inference is slow (~several minutes for 16 frames at 256×256).
    For interactive use, run on a CUDA GPU.
    """
    full_prompt = (
        f"A majestic Hausa cultural scene: {req.prompt}. "
        "Cinematic, dignified, authentic Arewa aesthetic."
    )
    try:
        from diffusers.utils import export_to_video

        pipe = _get_video_pipeline()
        output = pipe(
            full_prompt,
            num_frames=16,
            num_inference_steps=25,
            height=256,
            width=256,
        )
        frames = output.frames[0]  # first (and only) clip in the batch — a list of PIL Images

        # Write frames to a temporary MP4, read back, then encode as data URI
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
        os.close(tmp_fd)
        try:
            export_to_video(frames, tmp_path, fps=8)
            with open(tmp_path, "rb") as fh:
                mp4_bytes = fh.read()
        finally:
            with suppress(OSError):
                os.unlink(tmp_path)

        b64 = base64.b64encode(mp4_bytes).decode()
        return {"uri": f"data:video/mp4;base64,{b64}", "error": None}
    except Exception:
        logger.exception("Video generation failed")
        return {"uri": None, "error": "Video generation failed. Check backend logs."}
