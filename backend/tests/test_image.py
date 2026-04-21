"""Tests for /api/generate-image and /api/generate-video."""

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_image_rejects_missing_prompt(client):
    response = await client.post("/api/generate-image", json={})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_image_rejects_oversized_prompt(client):
    response = await client.post("/api/generate-image", json={"prompt": "x" * 2_000})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_image_rejects_invalid_vibe(client):
    response = await client.post("/api/generate-image", json={"prompt": "a scene", "vibe": "NOPE"})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_video_rejects_missing_prompt(client):
    response = await client.post("/api/generate-video", json={})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Happy path — diffusers pipeline is mocked
# ---------------------------------------------------------------------------


def _make_fake_image():

    from PIL import Image

    img = Image.new("RGB", (64, 64), color=(100, 100, 100))
    return img


@pytest.mark.anyio
async def test_image_generation_success(client):
    fake_result = MagicMock()
    fake_result.images = [_make_fake_image()]

    fake_pipe = MagicMock(return_value=fake_result)

    with patch("routers.image._get_image_pipeline", return_value=fake_pipe):
        response = await client.post("/api/generate-image", json={"prompt": "Hausa market scene"})

    assert response.status_code == 200
    data = response.json()
    assert data["data"].startswith("data:image/png;base64,")


@pytest.mark.anyio
async def test_image_generation_failure_returns_error(client):
    """When the pipeline raises, the endpoint must return an error payload (not 500)."""
    with patch(
        "routers.image._get_image_pipeline",
        side_effect=RuntimeError("CUDA OOM"),
    ):
        response = await client.post("/api/generate-image", json={"prompt": "test"})

    assert response.status_code == 200
    data = response.json()
    assert data["data"] is None
    assert "error" in data


# ---------------------------------------------------------------------------
# Video generation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_video_generation_success(client):
    import sys
    from types import ModuleType

    fake_frame = _make_fake_image()
    fake_output = MagicMock()
    fake_output.frames = [[fake_frame] * 4]
    fake_pipe = MagicMock(return_value=fake_output)

    def _fake_export(frames, path, fps=8):
        with open(path, "wb") as f:
            f.write(b"\x00\x00\x00\x18ftyp")  # fake MP4 header bytes

    # diffusers is not installed in the CI test environment, so stub the modules
    # that are imported lazily inside generate_video.
    fake_diffusers = ModuleType("diffusers")
    fake_diffusers_utils = ModuleType("diffusers.utils")
    fake_diffusers_utils.export_to_video = _fake_export
    fake_diffusers.utils = fake_diffusers_utils

    with (
        patch.dict(
            sys.modules,
            {"diffusers": fake_diffusers, "diffusers.utils": fake_diffusers_utils},
        ),
        patch("routers.image._get_video_pipeline", return_value=fake_pipe),
    ):
        response = await client.post("/api/generate-video", json={"prompt": "Hausa night market"})

    assert response.status_code == 200
    data = response.json()
    assert data["uri"].startswith("data:video/mp4;base64,")
    assert data["error"] is None


@pytest.mark.anyio
async def test_video_generation_failure_returns_error(client):
    with patch(
        "routers.image._get_video_pipeline",
        side_effect=RuntimeError("OOM"),
    ):
        response = await client.post("/api/generate-video", json={"prompt": "test"})

    assert response.status_code == 200
    data = response.json()
    assert data["uri"] is None
    assert "error" in data
