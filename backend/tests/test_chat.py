"""Tests for /api/chat."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iter_sse(content: bytes) -> list[dict]:
    """Parse SSE bytes into a list of payload dicts."""
    lines = content.decode().splitlines()
    events = []
    for line in lines:
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_chat_rejects_empty_text(client):
    """text field must not be empty."""
    response = await client.post("/api/chat", json={"text": ""})
    # FastAPI returns 422 for Pydantic validation errors.
    assert response.status_code == 422


@pytest.mark.anyio
async def test_chat_rejects_oversized_text(client):
    response = await client.post("/api/chat", json={"text": "a" * 5_000})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_chat_rejects_invalid_vibe(client):
    response = await client.post("/api/chat", json={"text": "hello", "vibe": "INVALID"})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_chat_rejects_bad_role_in_history(client):
    response = await client.post(
        "/api/chat",
        json={"text": "hello", "history": [{"role": "system", "text": "hi"}]},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Happy path — Ollama is mocked
# ---------------------------------------------------------------------------

async def _fake_ollama_chat(*_args, **_kwargs):
    async def _gen():
        yield {"message": {"content": "ƙ"}}
        yield {"message": {"content": "un san ku."}}

    return _gen()


@pytest.mark.anyio
async def test_chat_streams_sse(client):
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=_fake_ollama_chat)

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        response = await client.post(
            "/api/chat",
            json={"text": "Sannu"},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    events = _iter_sse(response.content)
    assert len(events) >= 1
    final = events[-1]
    assert final["isDone"] is True
    assert isinstance(final["verified"], bool)


@pytest.mark.anyio
async def test_chat_with_image_attachment(client):
    """Attachments are forwarded to Ollama as images."""
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=_fake_ollama_chat)

    # Minimal 1×1 white PNG, base64-encoded
    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        response = await client.post(
            "/api/chat",
            json={
                "text": "Describe this image",
                "attachments": [
                    {
                        "mimeType": "image/png",
                        "data": f"data:image/png;base64,{tiny_png_b64}",
                    }
                ],
            },
        )

    assert response.status_code == 200
    # Ensure Ollama was called with an images field
    call_kwargs = mock_client.chat.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
    user_msg = next(m for m in messages if m["role"] == "user")
    assert "images" in user_msg


@pytest.mark.anyio
async def test_chat_with_manifest_image_signal(client):
    """A MANIFEST: IMAGE tag in LLM reply triggers image generation."""

    from PIL import Image

    async def _chat_with_manifest(*_args, **_kwargs):
        async def _gen():
            yield {"message": {"content": "Wata duhun dare. [MANIFEST: IMAGE|moonlit Sahara]"}}

        return _gen()

    fake_img = Image.new("RGB", (8, 8), color=(50, 50, 50))
    fake_pipe_result = MagicMock()
    fake_pipe_result.images = [fake_img]
    fake_pipe = MagicMock(return_value=fake_pipe_result)

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=_chat_with_manifest)

    with (
        patch("routers.chat.ollama.AsyncClient", return_value=mock_client),
        patch("routers.image._get_image_pipeline", return_value=fake_pipe),
    ):
        response = await client.post("/api/chat", json={"text": "Describe the night"})

    assert response.status_code == 200
    events = _iter_sse(response.content)
    final = events[-1]
    assert final["isDone"] is True


@pytest.mark.anyio
async def test_chat_error_yields_done_event(client):
    """When Ollama raises, the endpoint must still emit isDone=true."""
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=Exception("ollama down"))

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        response = await client.post("/api/chat", json={"text": "Sannu"})

    assert response.status_code == 200
    events = _iter_sse(response.content)
    assert any(e.get("isDone") for e in events)


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_chat_with_api_key_set(client, monkeypatch):
    """If API_KEY env var is set, requests without it should be rejected."""
    import auth as auth_module

    monkeypatch.setattr(auth_module, "_CONFIGURED_KEY", "secret-test-key")

    response = await client.post("/api/chat", json={"text": "hello"})
    assert response.status_code == 401

    # With correct key it should proceed (Ollama will fail, but that's fine)
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=Exception("no ollama"))
    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        response2 = await client.post(
            "/api/chat",
            json={"text": "hello"},
            headers={"X-API-Key": "secret-test-key"},
        )
    # 200 SSE stream with error payload, not 401
    assert response2.status_code == 200

    monkeypatch.setattr(auth_module, "_CONFIGURED_KEY", None)
