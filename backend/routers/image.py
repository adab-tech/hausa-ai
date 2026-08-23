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

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator

from rate_limit import ip_limiter, limiter

router = APIRouter()
logger = logging.getLogger(__name__)


def _reject_blank_prompt(v: str) -> str:
    """Shared prompt validator: a blank/whitespace-only prompt must be
    rejected at the request-parsing stage, before it ever reaches the
    billed Gemini Imagen call -- previously " " or "" passed straight
    through and paid for a generation of essentially nothing."""
    if not v.strip():
        raise ValueError("prompt must not be blank")
    return v


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------
class ImageRequest(BaseModel):
    prompt: str = Field(..., max_length=1_000)
    vibe: str = Field("Classic", pattern=r"^(Classic|Royal|Cyberpunk|Academic)$")

    _validate_prompt = field_validator("prompt")(_reject_blank_prompt)


class VideoRequest(BaseModel):
    prompt: str = Field(..., max_length=1_000)

    _validate_prompt = field_validator("prompt")(_reject_blank_prompt)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
async def _generate_image_impl(req: ImageRequest) -> dict:
    """Actual image-generation logic, callable directly (no HTTP request, no
    rate limit) — generate_video uses this as an internal step, distinct
    from a real client hitting POST /generate-image."""
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


@router.post("/generate-image")
@limiter.limit("5/minute")
# Genuine per-IP ceiling alongside the spoofable per-device limit above --
# see rate_limit.py's ip_limiter docstring. Generous (6x the per-device
# rate) since real users do share IPs under carrier NAT; this exists to cap
# a rotating-token abuser burning paid Gemini Imagen quota, not to
# constrain ordinary shared-IP traffic.
@ip_limiter.limit("30/minute")
async def generate_image(request: Request, req: ImageRequest):
    return await _generate_image_impl(req)


@router.post("/generate-video")
@limiter.limit("5/minute")
@ip_limiter.limit("30/minute")
async def generate_video(request: Request, req: VideoRequest):
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
        img_res = await _generate_image_impl(ImageRequest(prompt=req.prompt, vibe="Classic"))
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
            # Use imageio to write video. writer.close() must run even if a
            # frame write raises partway through the loop -- otherwise the
            # imageio/ffmpeg writer (a subprocess + open file handle) leaks
            # for the lifetime of the process instead of being released.
            writer = imageio.get_writer(tmp_path, fps=8, codec='libx264', format='FFMPEG')
            try:
                for frame in frames:
                    writer.append_data(frame)
            finally:
                writer.close()

            with open(tmp_path, "rb") as fh:
                mp4_bytes = fh.read()
        finally:
            with suppress(OSError):
                os.unlink(tmp_path)

        b64 = base64.b64encode(mp4_bytes).decode()
        return {"uri": f"data:video/mp4;base64,{b64}", "error": None}

    except Exception:
        logger.exception("Video generation failed")
        # Same posture as _generate_image_impl's sibling failure path: don't
        # leak raw exception text (stack internals, library error strings)
        # to the client -- a plain, honest message instead.
        return {"uri": None, "error": "Video generation is not available right now."}
