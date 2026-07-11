"""Tests for /api/chat."""

import json
from unittest.mock import AsyncMock, patch

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
    """A MANIFEST: IMAGE tag in the LLM reply surfaces a manifest field in the
    final SSE event — the frontend, not the chat endpoint, is what actually
    calls /api/generate-image afterward (see localService.ts's
    unifiedExchange), so there's no image pipeline to mock here."""

    async def _chat_with_manifest(*_args, **_kwargs):
        async def _gen():
            yield {"message": {"content": "Wata duhun dare. [MANIFEST: IMAGE|moonlit Sahara]"}}

        return _gen()

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=_chat_with_manifest)

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        response = await client.post("/api/chat", json={"text": "Describe the night"})

    assert response.status_code == 200
    events = _iter_sse(response.content)
    final = events[-1]
    assert final["isDone"] is True
    assert final["manifest"] == {"type": "IMAGE", "prompt": "moonlit Sahara"}


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


@pytest.mark.anyio
async def test_chat_uses_cerebras_as_primary(client, monkeypatch):
    """Cerebras is tried first — Ollama should never be invoked when it
    succeeds."""
    monkeypatch.setenv("CEREBRAS_API_KEY", "fake-key")

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=Exception("ollama should not be called"))

    async def _fake_stream_cerebras(*_args, **_kwargs):
        for piece in ("Sannu", ", ", "yaya kake?"):
            yield piece

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client), \
         patch("routers.chat.stream_cerebras", _fake_stream_cerebras):
        response = await client.post("/api/chat", json={"text": "Cerebras primary test"})

    assert response.status_code == 200
    events = _iter_sse(response.content)
    final = events[-1]
    assert final["isDone"] is True
    assert "Sannu" in final["text"]
    mock_client.chat.assert_not_called()


@pytest.mark.anyio
async def test_chat_falls_back_to_ollama_when_cerebras_down(client, monkeypatch):
    """When Cerebras fails (or has no key), the endpoint should fall through
    to Ollama next, before Gemini or the static fallback."""
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=_fake_ollama_chat)

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        response = await client.post("/api/chat", json={"text": "Ollama fallback test"})

    assert response.status_code == 200
    events = _iter_sse(response.content)
    final = events[-1]
    assert final["isDone"] is True
    mock_client.chat.assert_called()


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


@pytest.mark.anyio
async def test_chat_caching(client):
    """The second identical request should hit cache and stream from cache."""
    from routers.chat import _CHAT_CACHE
    _CHAT_CACHE.clear()

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=_fake_ollama_chat)

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        # First request (populates cache)
        response1 = await client.post(
            "/api/chat",
            json={"text": "Ku yini lafiya"},
        )
        assert response1.status_code == 200
        events1 = _iter_sse(response1.content)
        assert len(events1) > 0
        
        # Second request (hits cache)
        response2 = await client.post(
            "/api/chat",
            json={"text": "Ku yini lafiya"},
        )
        assert response2.status_code == 200
        events2 = _iter_sse(response2.content)
        assert len(events2) > 0
        # The content should match
        assert events1[-1]["text"] == events2[-1]["text"]
        # Since it was served from cache, Ollama should only have been called once
        assert mock_client.chat.call_count == 1


@pytest.mark.anyio
async def test_chat_cache_key_includes_addressee_gender(client):
    """Requests differing only in addresseeGender must NOT share a cache
    entry — the system prompt (and therefore the correct Hausa reply) is
    grammatically gendered per-request, so a collision would serve one
    user's masculine- or feminine-addressed reply to the other."""
    from routers.chat import _CHAT_CACHE
    _CHAT_CACHE.clear()

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=_fake_ollama_chat)

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        response1 = await client.post(
            "/api/chat",
            json={"text": "Yaya kake?", "addresseeGender": "masculine"},
        )
        assert response1.status_code == 200
        _iter_sse(response1.content)

        response2 = await client.post(
            "/api/chat",
            json={"text": "Yaya kake?", "addresseeGender": "feminine"},
        )
        assert response2.status_code == 200
        _iter_sse(response2.content)

    # Ollama must be invoked for both distinct-gender requests, not just once.
    assert mock_client.chat.call_count == 2


@pytest.mark.anyio
async def test_chat_with_attachments_not_cached(client):
    """Requests carrying image attachments must never be served from (or
    written to) the cache — the cache key doesn't cover attachment bytes, so
    caching could leak one user's image-derived reply to a different user
    who happens to send the same caption text."""
    from routers.chat import _CHAT_CACHE
    _CHAT_CACHE.clear()

    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=_fake_ollama_chat)

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        for _ in range(2):
            response = await client.post(
                "/api/chat",
                json={
                    "text": "Me kake gani a wannan hoto?",
                    "attachments": [
                        {"mimeType": "image/png", "data": f"data:image/png;base64,{tiny_png_b64}"}
                    ],
                },
            )
            assert response.status_code == 200
            _iter_sse(response.content)

    # Both requests should hit Ollama — neither served from cache.
    assert mock_client.chat.call_count == 2
    assert _CHAT_CACHE == {}


@pytest.mark.anyio
async def test_chat_time_sensitive_query_not_cached(client):
    """A time-sensitive question (news/today/prices…) must never be served
    from or written to the cache — a stale 'today's news' reply replayed an
    hour later is wrong, and a live-search-grounded answer is only valid at
    fetch time. Same predicate that gates whether live search runs."""
    from routers.chat import _CHAT_CACHE
    _CHAT_CACHE.clear()

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=_fake_ollama_chat)

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        for _ in range(2):
            response = await client.post(
                "/api/chat",
                json={"text": "Meye labari a Kano yau?"},
            )
            assert response.status_code == 200
            _iter_sse(response.content)

    # Both time-sensitive requests must reach the model; nothing cached.
    assert mock_client.chat.call_count == 2
    assert _CHAT_CACHE == {}


@pytest.mark.anyio
async def test_chat_warmup(client):
    """If the LLM takes > 2 seconds to respond, a warmup heartbeat is emitted."""
    import asyncio
    
    async def _slow_ollama_chat(*_args, **_kwargs):
        async def _gen():
            await asyncio.sleep(2.5)
            yield {"message": {"content": "Sannu."}}
        return _gen()

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=_slow_ollama_chat)

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        response = await client.post(
            "/api/chat",
            json={"text": "Barka da yamma"},
        )
    assert response.status_code == 200
    events = _iter_sse(response.content)
    warmups = [e for e in events if e.get("warmup") is True]
    assert len(warmups) > 0


# ---------------------------------------------------------------------------
# Sovereign Constitution content
# ---------------------------------------------------------------------------


def test_constitution_permits_code_switching():
    """The constitution must carry the [CODE_SWITCHING] section so English
    scientific/technical terms are not force-translated into awkward calques."""
    from routers.chat import SOVEREIGN_CONSTITUTION

    assert "[CODE_SWITCHING]" in SOVEREIGN_CONSTITUTION
    assert "ilimin halittu (Biology)" in SOVEREIGN_CONSTITUTION


def test_constitution_declares_capabilities():
    """The model must know its own real abilities so it answers 'me kake
    iyawa' truthfully instead of hallucinating (or forgetting) features."""
    from routers.chat import SOVEREIGN_CONSTITUTION

    assert "[CAPABILITIES]" in SOVEREIGN_CONSTITUTION


def test_current_time_context_has_utc_and_world_anchors():
    """The datetime block must carry the UTC anchor, Nigeria/WAT, and the
    precomputed world anchors (so world timezones are read, not miscomputed
    by the LLM). Proves it's live via the current year."""
    from datetime import datetime, timezone
    from routers.chat import _current_time_context

    ctx = _current_time_context()
    assert "[CURRENT_DATETIME]" in ctx
    assert "UTC" in ctx and "WAT" in ctx
    # World anchors precomputed server-side (the fix for the wrong-Tokyo bug).
    assert "Tokyo" in ctx and "Makka" in ctx
    assert str(datetime.now(timezone.utc).year) in ctx


def test_current_time_context_tokyo_is_exact():
    """The Tokyo line must match a fresh zoneinfo computation to the hour —
    guards against regressing to LLM-computed (wrong) offsets."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from routers.chat import _current_time_context

    ctx = _current_time_context()
    tokyo_now = datetime.now(ZoneInfo("Asia/Tokyo"))
    # The exact "HH:MM" for Tokyo must appear in the block.
    assert f"{tokyo_now:%H:%M}" in ctx


@pytest.mark.anyio
async def test_time_context_injected_into_system_prompt(client):
    """Every chat request's system message must carry the live datetime block
    so date/time questions are answerable on the primary path."""
    from routers.chat import _CHAT_CACHE
    _CHAT_CACHE.clear()

    captured = {}

    async def _capture_ollama(*args, **kwargs):
        captured["messages"] = kwargs.get("messages") or (args[0] if args else None)
        async def _gen():
            yield {"message": {"content": "Sannu."}}
        return _gen()

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=_capture_ollama)
    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        await client.post("/api/chat", json={"text": "Karfe nawa ne a Kano?"})

    system_msg = next(m for m in captured["messages"] if m["role"] == "system")
    assert "[CURRENT_DATETIME]" in system_msg["content"]


# ---------------------------------------------------------------------------
# Live web search grounding
# ---------------------------------------------------------------------------


def test_needs_live_search_flags_time_sensitive():
    """Present-day / current-events queries (Hausa + English) are flagged."""
    from routers.chat import _needs_live_search

    assert _needs_live_search("Meye labari a Kano yau?") is True
    assert _needs_live_search("what is the price of fuel today") is True
    assert _needs_live_search("Sakamakon zabe na 2027") is True  # 4-digit recent year


def test_needs_live_search_ignores_historical():
    """Historical questions with no time cue are NOT flagged."""
    from routers.chat import _needs_live_search

    assert _needs_live_search("Wane ne Usman dan Fodio?") is False
    assert _needs_live_search("Ka gaya mini tarihin garin Kano") is False


@pytest.mark.anyio
async def test_chat_injects_search_grounding(client, monkeypatch):
    """With a Tavily key set and a time-sensitive query, the fresh search
    results are injected into the system message the model receives."""
    from routers.chat import _CHAT_CACHE
    _CHAT_CACHE.clear()
    monkeypatch.setenv("TAVILY_API_KEY", "fake-tavily-key")
    monkeypatch.setenv("CEREBRAS_API_KEY", "fake-key")

    async def _fake_web_search(query, max_results=4):
        return [
            {
                "title": "Kano Daily",
                "url": "https://example.com/kano",
                "content": "GROUNDED_FACT_TOKEN happened in Kano today.",
            }
        ]

    captured = {}

    async def _fake_stream_cerebras(messages, *_args, **_kwargs):
        captured["messages"] = messages
        yield "An amsa."

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=Exception("ollama not used"))

    with patch("routers.chat.web_search", _fake_web_search), \
         patch("routers.chat.stream_cerebras", _fake_stream_cerebras), \
         patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        response = await client.post("/api/chat", json={"text": "Meye labari a Kano yau?"})

    assert response.status_code == 200
    system_msg = next(m for m in captured["messages"] if m["role"] == "system")
    assert "GROUNDED_FACT_TOKEN" in system_msg["content"]
    assert "[REAL_TIME_RESULTS]" in system_msg["content"]
    # The no-access block must have been replaced.
    assert "[REAL_TIME_LIMITS]" not in system_msg["content"]


@pytest.mark.anyio
async def test_chat_no_search_without_key(client, monkeypatch):
    """With no Tavily key, behavior is unchanged: the honest no-live-access
    block is present and web_search is never invoked."""
    from routers.chat import _CHAT_CACHE
    _CHAT_CACHE.clear()
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_SEARCH_API_KEY", raising=False)
    monkeypatch.setenv("CEREBRAS_API_KEY", "fake-key")

    search_called = {"hit": False}

    async def _fake_web_search(query, max_results=4):
        search_called["hit"] = True
        return []

    captured = {}

    async def _fake_stream_cerebras(messages, *_args, **_kwargs):
        captured["messages"] = messages
        yield "An amsa."

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=Exception("ollama not used"))

    with patch("routers.chat.web_search", _fake_web_search), \
         patch("routers.chat.stream_cerebras", _fake_stream_cerebras), \
         patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        response = await client.post("/api/chat", json={"text": "Meye labari a Kano yau?"})

    assert response.status_code == 200
    assert search_called["hit"] is False
    system_msg = next(m for m in captured["messages"] if m["role"] == "system")
    assert "[REAL_TIME_LIMITS]" in system_msg["content"]
    assert "[REAL_TIME_RESULTS]" not in system_msg["content"]

