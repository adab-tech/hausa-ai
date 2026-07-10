"""Tests for /api/generate-image and /api/generate-video."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

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
# Image generation tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_image_generation_success(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    
    tiny_png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    
    mock_img = MagicMock()
    mock_img.image.image_bytes = tiny_png_bytes
    
    mock_res = MagicMock()
    mock_res.generated_images = [mock_img]
    
    mock_client_instance = MagicMock()
    mock_client_instance.aio.models.generate_images = AsyncMock(return_value=mock_res)
    
    with patch("google.genai.Client", return_value=mock_client_instance):
        response = await client.post(
            "/api/generate-image",
            json={"prompt": "Hausa market scene", "vibe": "Classic"}
        )
        
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == f"data:image/png;base64,{base64.b64encode(tiny_png_bytes).decode()}"
    assert "error" not in data


@pytest.mark.anyio
async def test_image_generation_unavailable_returns_none(client, monkeypatch):
    """When the real backend fails, the endpoint must report failure honestly
    (data: None) rather than drawing a stand-in placeholder graphic — a fake
    image would mislead the user into thinking generation succeeded."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    mock_client_instance = MagicMock()
    mock_client_instance.aio.models.generate_images = AsyncMock(side_effect=Exception("API limit"))

    with patch("google.genai.Client", return_value=mock_client_instance):
        response = await client.post(
            "/api/generate-image",
            json={"prompt": "Hausa market scene", "vibe": "Classic"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["data"] is None
    assert "error" in data


# ---------------------------------------------------------------------------
# Video generation tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_video_generation_success(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    
    tiny_png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    
    mock_img = MagicMock()
    mock_img.image.image_bytes = tiny_png_bytes
    mock_res = MagicMock()
    mock_res.generated_images = [mock_img]
    mock_client_instance = MagicMock()
    mock_client_instance.aio.models.generate_images = AsyncMock(return_value=mock_res)
    
    with patch("google.genai.Client", return_value=mock_client_instance):
        response = await client.post(
            "/api/generate-video",
            json={"prompt": "Hausa night market"}
        )
        
    assert response.status_code == 200
    data = response.json()
    assert data["uri"].startswith("data:video/mp4;base64,")
    assert data["error"] is None


@pytest.mark.anyio
async def test_video_generation_failure_returns_error(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    
    with patch("imageio.get_writer", side_effect=RuntimeError("FFMPEG error")):
        response = await client.post(
            "/api/generate-video",
            json={"prompt": "test"}
        )
        
    assert response.status_code == 200
    data = response.json()
    assert data["uri"] is None
    assert "error" in data
