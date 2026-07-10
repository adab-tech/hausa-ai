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
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set in environment.")
        return {"data": None, "error": "GEMINI_API_KEY not set in environment."}

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        # Using the async client to prevent blocking the event loop
        response = await client.aio.models.generate_images(
            model='imagen-3.0-fast-generate-001',
            prompt=full_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio="1:1"
            )
        )
        img_bytes = response.generated_images[0].image.image_bytes
        b64 = base64.b64encode(img_bytes).decode()
        return {"data": f"data:image/png;base64,{b64}"}

    except Exception as e:
        logger.warning("google.genai image generation failed: %s", e)
        # Honest failure: no drawn stand-in graphic. A placeholder card that
        # merely echoes the prompt back as text isn't a picture and misleads
        # the user into thinking generation succeeded — better to say plainly
        # that image generation isn't available right now.
        return {"data": None, "error": "Image generation is not available right now."}


@router.post("/generate-video")
async def generate_video(req: VideoRequest):
    """
    Video generation using the Imagen static output + Ken Burns pan/zoom animation.
    This creates an instant, lightweight MP4 without local GPU requirements.
    """
    try:
        import numpy as np
        from PIL import Image
        import imageio

        # 1. A real base image is required — without one, panning/zooming a
        # drawn placeholder produces a fake "video" that isn't actually video
        # generation. Fail honestly instead.
        img_res = await generate_image(ImageRequest(prompt=req.prompt, vibe="Classic"))
        if not (img_res and img_res.get("data") and "base64," in img_res["data"]):
            return {"uri": None, "error": "Video generation is not available right now."}

        b64_data = img_res["data"].split("base64,")[1]
        base_img = Image.open(io.BytesIO(base64.b64decode(b64_data)))
        base_img = base_img.resize((256, 256))
        
        # 2. Create 16 frames with a smooth panning/zooming effect (Ken Burns effect)
        frames = []
        num_frames = 16
        for i in range(num_frames):
            # Calculate zoom factor (e.g. from 1.0 to 1.15)
            zoom = 1.0 + (i / (num_frames - 1)) * 0.15
            new_size = (int(256 * zoom), int(256 * zoom))
            resized = base_img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Crop to center 256x256
            left = (resized.width - 256) // 2
            top = (resized.height - 256) // 2
            cropped = resized.crop((left, top, left + 256, top + 256))
            
            # Convert to numpy array
            frames.append(np.array(cropped))
            
        # 3. Write frames to temporary MP4 using imageio
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
        os.close(tmp_fd)
        try:
            # Use imageio to write video
            writer = imageio.get_writer(tmp_path, fps=8, codec='libx264', format='FFMPEG')
            for frame in frames:
                writer.append_data(frame)
            writer.close()
            
            with open(tmp_path, "rb") as fh:
                mp4_bytes = fh.read()
        finally:
            with suppress(OSError):
                os.unlink(tmp_path)
                
        b64 = base64.b64encode(mp4_bytes).decode()
        return {"uri": f"data:video/mp4;base64,{b64}", "error": None}
        
    except Exception as e:
        logger.exception("Video generation failed")
        return {"uri": None, "error": f"Video generation failed: {str(e)}"}
