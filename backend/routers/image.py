"""
/api/generate-image  — image generation via Diffusers (FLUX.1-schnell or SD).
/api/generate-video  — video generation stub (returns null; swap in CogVideoX when available).

POST /api/generate-image
  { "prompt": "...", "vibe": "Classic" }
  -> { "data": "data:image/png;base64,..." }

POST /api/generate-video
  { "prompt": "..." }
  -> { "uri": null }   (stub — extend with CogVideoX when GPU VRAM allows)
"""

import base64
import io
import logging
import os
from functools import lru_cache

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model selection — default to FLUX.1-schnell (Apache 2.0, fast CPU/GPU)
# Set IMAGE_MODEL=stabilityai/stable-diffusion-2-1 for lighter VRAM usage
# ---------------------------------------------------------------------------
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
IMAGE_DEVICE = os.getenv("IMAGE_DEVICE", "cpu")  # "cuda" on GPU runners


@lru_cache(maxsize=1)
def _get_pipeline():
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


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------
class ImageRequest(BaseModel):
    prompt: str
    vibe: str = "Classic"


class VideoRequest(BaseModel):
    prompt: str


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
        pipe = _get_pipeline()
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
    Video generation stub.
    Swap this out for CogVideoX or Stable Video Diffusion when GPU VRAM allows.
    See: https://github.com/THUDM/CogVideo
    """
    return {"uri": None, "message": "Video generation requires CogVideoX. See backend/README.md."}
