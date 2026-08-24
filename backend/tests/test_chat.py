"""Tests for /api/chat."""

import json
import sys
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
async def test_chat_falls_back_to_groq_when_cerebras_down(client, monkeypatch):
    """When Cerebras fails (or has no key), the endpoint should try Groq
    next — before Ollama, which has never once succeeded in production
    under current RAM pressure, so trying it first would waste its timeout
    on every request."""
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=Exception("ollama should not be called"))

    async def _fake_stream_groq(*_args, **_kwargs):
        for piece in ("Sannu", ", ", "daga Groq"):
            yield piece

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client), \
         patch("routers.chat.stream_groq", _fake_stream_groq):
        response = await client.post("/api/chat", json={"text": "Groq fallback test"})

    assert response.status_code == 200
    events = _iter_sse(response.content)
    final = events[-1]
    assert final["isDone"] is True
    assert "daga Groq" in final["text"]
    mock_client.chat.assert_not_called()


@pytest.mark.anyio
async def test_chat_falls_back_to_ollama_when_cerebras_and_groq_down(client, monkeypatch):
    """When both Cerebras and Groq fail (or have no key), the endpoint
    should fall through to Ollama next, before Gemini or the static
    fallback."""
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=_fake_ollama_chat)

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        response = await client.post("/api/chat", json={"text": "Ollama fallback test"})

    assert response.status_code == 200
    events = _iter_sse(response.content)
    final = events[-1]
    assert final["isDone"] is True
    mock_client.chat.assert_called()


@pytest.mark.anyio
async def test_chat_does_not_concatenate_providers_on_mid_stream_failure(client, monkeypatch):
    """Regression test for a real bug found in a 2026-08-23 review: if a
    provider yields some real content and THEN fails partway through (a
    network blip, quota cutoff mid-generation), the old code fell through
    to the next provider and glued its entirely separate, fresh answer onto
    the first provider's partial text -- producing an incoherent reply,
    then caching that garbled result and replaying it to a different user
    later. Once a provider has produced ANY content, a later failure must
    end the stream with just that partial content -- never switch providers
    mid-answer."""
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)

    async def _fake_stream_cerebras(*_args, **_kwargs):
        yield "Barka "
        yield "da zuwa"
        raise RuntimeError("connection dropped mid-generation")

    groq_call_count = 0

    async def _fake_stream_groq(*_args, **_kwargs):
        # Must NEVER be reached -- Cerebras already produced real content.
        nonlocal groq_call_count
        groq_call_count += 1
        yield "an entirely different Groq answer"

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=Exception("ollama should not be called"))

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client), \
         patch("routers.chat.stream_cerebras", _fake_stream_cerebras), \
         patch("routers.chat.stream_groq", _fake_stream_groq):
        response = await client.post("/api/chat", json={"text": "concatenation regression test"})

    assert response.status_code == 200
    events = _iter_sse(response.content)
    final = events[-1]
    assert final["isDone"] is True
    assert final["text"] == "Barka da zuwa"
    assert "Groq" not in final["text"]
    assert groq_call_count == 0
    mock_client.chat.assert_not_called()


@pytest.mark.anyio
async def test_chat_falls_through_when_provider_yields_nothing(client, monkeypatch):
    """Regression test for the related empty-success gap: a provider whose
    stream completes with ZERO chunks and no exception (e.g. Ollama hitting
    StopAsyncIteration on the very first chunk, or any provider returning a
    genuinely empty completion) used to look exactly like a successful,
    complete reply and skip the rest of the fallback chain. Must be treated
    the same as a failure and continue to the next provider."""
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)

    async def _empty_stream_cerebras(*_args, **_kwargs):
        return
        yield  # pragma: no cover -- makes this an async generator, never reached

    async def _fake_stream_groq(*_args, **_kwargs):
        yield "Sannu daga Groq"

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=Exception("ollama should not be called"))

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client), \
         patch("routers.chat.stream_cerebras", _empty_stream_cerebras), \
         patch("routers.chat.stream_groq", _fake_stream_groq):
        response = await client.post("/api/chat", json={"text": "empty-success regression test"})

    assert response.status_code == 200
    events = _iter_sse(response.content)
    final = events[-1]
    assert final["isDone"] is True
    assert "Sannu daga Groq" in final["text"]
    mock_client.chat.assert_not_called()


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


def test_constitution_greets_only_on_first_turn():
    """Regression guard: a real user reported Murya re-greeting ('Barka da
    ...') on every single reply, even mid-conversation with prior turns
    already in history -- unnatural, and it buries the actual answer under
    a formal Gaisuwa every time. The constitution mandates the Gaisuwa
    greeting whenever 'Barka'/'Sannun' is used, but must also say that
    belongs on the FIRST reply only, not every turn."""
    from routers.chat import SOVEREIGN_CONSTITUTION

    assert "first reply" in SOVEREIGN_CONSTITUTION.lower()
    assert "do NOT greet again" in SOVEREIGN_CONSTITUTION


# ---------------------------------------------------------------------------
# Tutor (learning) mode — mode="tutor" turns Murya into Malamin Hausa.
# ---------------------------------------------------------------------------
def test_tutor_mode_injects_teaching_persona():
    from routers.chat import _build_messages, ChatRequest

    msgs = _build_messages(ChatRequest(text="Koya min Hausa", mode="tutor"))
    system = next(m for m in msgs if m["role"] == "system")["content"]
    assert "[LEARNING_MODE" in system and "MALAMIN HAUSA" in system


def test_assistant_mode_has_no_tutor_persona():
    from routers.chat import _build_messages, ChatRequest

    msgs = _build_messages(ChatRequest(text="Sannu"))  # default mode="assistant"
    system = next(m for m in msgs if m["role"] == "system")["content"]
    assert "[LEARNING_MODE" not in system


def test_cache_key_separates_tutor_from_assistant():
    """Same text in tutor vs assistant mode must not collide in the cache."""
    from routers.chat import _get_cache_key, ChatRequest

    a = _get_cache_key(ChatRequest(text="Koya min", mode="assistant"))
    t = _get_cache_key(ChatRequest(text="Koya min", mode="tutor"))
    assert a != t


@pytest.mark.anyio
async def test_chat_rejects_invalid_mode(client):
    """mode is constrained to assistant|tutor; anything else is a 422."""
    resp = await client.post("/api/chat", json={"text": "hi", "mode": "hacker"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Local knowledge tools — calculator / prayer / dictionary grounding
# ---------------------------------------------------------------------------
def test_tools_context_calculator():
    """An arithmetic question yields an exact CALCULATION grounding block."""
    from routers.chat import _tools_context

    ctx = _tools_context("Menene 45 * 12?")
    assert ctx is not None and "CALCULATION" in ctx and "540" in ctx


def test_tools_context_percentage_of():
    """Percent-of ('15% na 2000' = 300) is handled in Hausa and English."""
    from routers.chat import _tools_context

    ctx = _tools_context("Menene 15% na 2000?")
    assert ctx is not None and "300" in ctx


def test_tools_context_prayer():
    """A Salla question yields a PRAYER TIMES block for the named city."""
    from routers.chat import _tools_context

    ctx = _tools_context("Menene lokutan salla a Kano?")
    assert ctx is not None and "PRAYER TIMES" in ctx and "Kano" in ctx


def test_tools_context_none_for_plain_chat():
    """Ordinary conversation triggers no tool grounding."""
    from routers.chat import _tools_context

    assert _tools_context("Barka da yamma, yaya gida?") is None


def test_define_re_skips_kalmar_filler_word():
    """'ma'anar kalmar X' ('the meaning of the WORD X') must extract X, not
    the filler word 'kalmar' ('word') itself -- a real bug found live in
    production: the dictionary tool was searching for the literal word
    "kalmar" (which has no entry) instead of the actual target term, so
    real dictionary-grounded answers silently never fired for this very
    common phrasing."""
    from routers.chat import _DEFINE_RE

    assert _DEFINE_RE.search("me ma'anar kalmar ƙasa?").group(1) == "ƙasa"
    assert _DEFINE_RE.search("ma'anar ƙasa").group(1) == "ƙasa"
    assert _DEFINE_RE.search("what does the word ƙasa mean").group(1) == "ƙasa"
    assert _DEFINE_RE.search("what does ƙasa mean").group(1) == "ƙasa"
    assert _DEFINE_RE.search("define the term aboki").group(1) == "aboki"


def test_tools_context_dictionary_lookup():
    """A 'ma'anar kalmar X' question yields a DICTIONARY block citing a real
    source for a word actually in the loaded lexicon."""
    from routers.chat import _tools_context
    from services import dictionary_service

    if not dictionary_service.dictionary_ready():
        pytest.skip("dictionary lexicon not available in this environment")

    ctx = _tools_context("me ma'anar kalmar ruwa?")
    assert ctx is not None and "DICTIONARY 'ruwa'" in ctx


@pytest.mark.anyio
async def test_calculator_grounding_reaches_model(client):
    """The exact calculation must land in the system prompt the model sees."""
    from routers.chat import _CHAT_CACHE
    _CHAT_CACHE.clear()

    captured = {}

    async def _capture(*args, **kwargs):
        captured["messages"] = kwargs.get("messages") or (args[0] if args else None)
        async def _gen():
            yield {"message": {"content": "Amsar ita ce 540."}}
        return _gen()

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=_capture)
    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client):
        await client.post("/api/chat", json={"text": "menene 45 * 12?"})

    system_msg = next(m for m in captured["messages"] if m["role"] == "system")
    assert "CALCULATION" in system_msg["content"] and "540" in system_msg["content"]


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


def test_needs_live_search_flags_who_is_questions():
    """Real bug found live 2026-08-23: 'Wanene shugaban Najeriya?' ('Who is
    the president of Nigeria?') never triggered live search at all -- no
    'yanzu'/'yau' in that exact phrasing -- so the model answered from stale
    training data with no honesty guard. This is the same class of bug
    already caught once for a Ghana question that happened to include
    'a yanzu'. Covers the Hausa question-word variants, not just the one
    that happened to slip through."""
    from routers.chat import _needs_live_search

    assert _needs_live_search("Wanene shugaban Najeriya?") is True
    assert _needs_live_search("Wa ne shugaban kasar Ghana?") is True
    assert _needs_live_search("Wace ce firaministar Burtaniya?") is True
    assert _needs_live_search("Su wanene 'yan wasan Najeriya a gasar?") is True
    assert _needs_live_search("Who is the president of France?") is True


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


# ---------------------------------------------------------------------------
# Regression: each provider used to instantiate a fresh SDK client on EVERY
# streaming call (a connection-pool leak under sustained traffic). Clients
# are now cached at module level and reused across calls.
# ---------------------------------------------------------------------------
def test_ollama_client_is_reused_across_calls(monkeypatch):
    from routers import chat as chat_module

    created = []

    class _FakeAsyncClient:
        def __init__(self, host=None):
            created.append(host)

    monkeypatch.setattr(chat_module.ollama, "AsyncClient", _FakeAsyncClient)
    chat_module._ollama_client = None

    first = chat_module._get_ollama_client()
    second = chat_module._get_ollama_client()

    assert first is second
    assert len(created) == 1  # constructor called exactly once, not per call


def test_cerebras_client_is_reused_across_calls(monkeypatch):
    from routers import chat as chat_module

    created = []

    class _FakeAsyncCerebras:
        def __init__(self, api_key=None):
            created.append(api_key)

    # The `cerebras` package isn't installed in this dev/test environment at
    # all (stream_cerebras's real path is only exercised in production, or
    # bypassed entirely by higher-level tests that patch stream_cerebras
    # itself) -- fake the module in sys.modules so `from cerebras.cloud.sdk
    # import AsyncCerebras` inside _get_cerebras_client resolves to it.
    monkeypatch.setitem(
        sys.modules, "cerebras.cloud.sdk",
        type("_FakeSdkModule", (), {"AsyncCerebras": _FakeAsyncCerebras})(),
    )
    chat_module._cerebras_client = None

    first = chat_module._get_cerebras_client("key-a")
    second = chat_module._get_cerebras_client("key-a")

    assert first is second
    assert len(created) == 1


def test_gemini_client_is_reused_across_stream_gemini_raw_and_stream_gemini(monkeypatch):
    from routers import chat as chat_module

    created = []

    class _FakeGenaiClient:
        def __init__(self, api_key=None):
            created.append(api_key)

    monkeypatch.setattr("google.genai.Client", _FakeGenaiClient)
    chat_module._gemini_client = None

    first = chat_module._get_gemini_client("gem-key")
    second = chat_module._get_gemini_client("gem-key")

    assert first is second
    assert len(created) == 1


# ---------------------------------------------------------------------------
# Regression: found live 2026-08-24 -- Cerebras 402'd, Groq hit its real
# rate limit, Ollama timed out, and Gemini had no key, all on one request.
# That specific request couldn't be saved, but EVERY subsequent request
# still retried Cerebras/Groq from scratch and paid full latency to hit the
# exact same 402/429 again. A per-provider cooldown skips a known-blocked
# provider instead of re-trying it every request; a short, narrowly-scoped
# tenacity retry recovers a genuinely transient (not rate-limit) connection
# failure without re-yielding duplicate content.
# ---------------------------------------------------------------------------
class _FakeRateLimitError(Exception):
    """Stands in for groq.RateLimitError / cerebras.cloud.sdk.RateLimitError
    -- matched by class NAME in chat.py, not isinstance, since the real
    classes differ per SDK."""
    __name__ = "RateLimitError"

    def __init__(self, message, status_code=429, headers=None):
        super().__init__(message)
        self.status_code = status_code

        class _Resp:
            pass

        self.response = _Resp()
        self.response.headers = headers or {}


_FakeRateLimitError.__name__ = "RateLimitError"


class _FakeQuotaError(Exception):
    __name__ = "APIStatusError"

    def __init__(self, message, status_code=402):
        super().__init__(message)
        self.status_code = status_code


_FakeQuotaError.__name__ = "APIStatusError"


class _FakeConnectionError(Exception):
    __name__ = "APIConnectionError"


_FakeConnectionError.__name__ = "APIConnectionError"


@pytest.fixture(autouse=True)
def _reset_provider_cooldowns():
    from routers import chat as chat_module
    chat_module._provider_cooldowns.clear()
    yield
    chat_module._provider_cooldowns.clear()


def test_provider_available_by_default():
    from routers.chat import _provider_available
    assert _provider_available("Groq") is True


def test_rate_limit_error_sets_cooldown_from_message_text():
    from routers.chat import _note_provider_failure, _provider_available

    err = _FakeRateLimitError(
        "Rate limit reached ... Please try again in 25.3575s. Need more tokens?"
    )
    _note_provider_failure("Groq", err)
    assert _provider_available("Groq") is False


def test_rate_limit_error_prefers_retry_after_header_over_message_text():
    from routers.chat import _extract_retry_after

    err = _FakeRateLimitError(
        "Please try again in 25.3575s.", headers={"retry-after": "5"}
    )
    assert _extract_retry_after(err) == 5.0


def test_quota_error_sets_longer_default_cooldown_when_no_retry_after():
    from routers.chat import (
        _QUOTA_COOLDOWN_SECONDS,
        _note_provider_failure,
        _provider_cooldowns,
    )
    import time as time_module

    err = _FakeQuotaError("Payment required to access this resource.", status_code=402)
    before = time_module.monotonic()
    _note_provider_failure("Cerebras", err)
    # No retry-after available for a 402 -> falls back to the long quota
    # cooldown, not the short generic default.
    assert _provider_cooldowns["Cerebras"] - before == pytest.approx(
        _QUOTA_COOLDOWN_SECONDS, abs=1.0
    )


def test_plain_connection_error_does_not_set_a_cooldown():
    """A transient connection blip is retried once (see the tenacity tests
    below), not cooled down -- the provider is probably fine on the very
    next request."""
    from routers.chat import _note_provider_failure, _provider_available

    _note_provider_failure("Groq", _FakeConnectionError("connection reset"))
    assert _provider_available("Groq") is True


@pytest.mark.anyio
async def test_fetch_stream_skips_provider_in_cooldown_without_calling_it(client, monkeypatch):
    """End-to-end: once Groq is in cooldown, /api/chat must not invoke it at
    all for a subsequent request -- straight through to the next provider."""
    from routers import chat as chat_module

    chat_module._provider_cooldowns["Groq"] = chat_module.time.monotonic() + 60

    groq_called = False

    async def _fake_stream_groq(*_args, **_kwargs):
        nonlocal groq_called
        groq_called = True
        yield "should never run"

    async def _fake_stream_cerebras(*_args, **_kwargs):
        raise RuntimeError("Cerebras down for this test")
        yield  # pragma: no cover -- unreachable; makes this an async generator function

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=_fake_ollama_chat)

    with patch("routers.chat.ollama.AsyncClient", return_value=mock_client), \
         patch("routers.chat.stream_cerebras", _fake_stream_cerebras), \
         patch("routers.chat.stream_groq", _fake_stream_groq):
        response = await client.post("/api/chat", json={"text": "cooldown skip test"})

    assert response.status_code == 200
    assert groq_called is False


@pytest.mark.anyio
async def test_create_stream_retries_once_on_transient_connection_error():
    """The narrowly-scoped tenacity retry: a connection error on the
    stream-establishing call recovers on one fast retry."""
    from routers.chat import _create_stream

    attempts = []

    class _FakeClient:
        class chat:
            class completions:
                @staticmethod
                async def create(**kwargs):
                    attempts.append(kwargs)
                    if len(attempts) == 1:
                        raise _FakeConnectionError("dropped mid-handshake")
                    return "the-real-stream"

    result = await _create_stream(_FakeClient(), model="m", messages=[], stream=True)
    assert result == "the-real-stream"
    assert len(attempts) == 2


@pytest.mark.anyio
async def test_create_stream_does_not_retry_rate_limit_errors():
    """Retrying a rate-limit error would just wait and hit the same limit
    again -- must fail immediately so the caller can fail over and set a
    cooldown instead."""
    from routers.chat import _create_stream

    attempts = []

    class _FakeClient:
        class chat:
            class completions:
                @staticmethod
                async def create(**kwargs):
                    attempts.append(kwargs)
                    raise _FakeRateLimitError("rate limited")

    with pytest.raises(_FakeRateLimitError):
        await _create_stream(_FakeClient(), model="m", messages=[], stream=True)
    assert len(attempts) == 1

