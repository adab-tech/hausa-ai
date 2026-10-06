"""Tests for the self-hosted / OpenAI-compatible provider
(services/own_llm_service.py) and its position in the chat / document chains."""

import json
from unittest.mock import patch

import httpx
import pytest

from services import own_llm_service as own


def _sse(*deltas: str, done: bool = True) -> bytes:
    frames = [
        f"data: {json.dumps({'choices': [{'delta': {'content': d}}]})}\n\n" for d in deltas
    ]
    if done:
        frames.append("data: [DONE]\n\n")
    return "".join(frames).encode()


def _mock_client(handler):
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    return patch.object(own.httpx, "AsyncClient", factory)


@pytest.fixture
def own_env(monkeypatch):
    monkeypatch.setenv("MURYA_LLM_BASE_URL", "http://gpu-box:8000/v1/")
    monkeypatch.setenv("MURYA_LLM_MODEL", "murya-ha-8b")
    monkeypatch.delenv("MURYA_LLM_API_KEY", raising=False)


def test_disabled_without_config(monkeypatch):
    monkeypatch.delenv("MURYA_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("MURYA_LLM_MODEL", raising=False)
    assert own.own_llm_enabled() is False


def test_needs_both_url_and_model(monkeypatch):
    monkeypatch.setenv("MURYA_LLM_BASE_URL", "http://x/v1")
    monkeypatch.delenv("MURYA_LLM_MODEL", raising=False)
    assert own.own_llm_enabled() is False


@pytest.mark.anyio
async def test_stream_yields_deltas_and_sends_clean_payload(own_env, monkeypatch):
    monkeypatch.setenv("MURYA_LLM_API_KEY", "sekret")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=_sse("Sannu", " da zuwa"))

    messages = [{"role": "user", "content": "Sannu", "images": ["xx"]}]
    with _mock_client(handler):
        out = [d async for d in own.stream_own_llm(messages)]

    assert out == ["Sannu", " da zuwa"]
    assert seen["url"] == "http://gpu-box:8000/v1/chat/completions"
    assert seen["auth"] == "Bearer sekret"
    assert seen["body"]["model"] == "murya-ha-8b"
    assert seen["body"]["stream"] is True
    assert seen["body"]["messages"] == [{"role": "user", "content": "Sannu"}]  # no "images"


@pytest.mark.anyio
async def test_stream_skips_malformed_frames(own_env):
    body = b"data: not-json\n\n" + _sse("ok")

    with _mock_client(lambda r: httpx.Response(200, content=body)):
        out = [d async for d in own.stream_own_llm([{"role": "user", "content": "x"}])]

    assert out == ["ok"]


@pytest.mark.anyio
async def test_stream_429_maps_to_rate_limit_error(own_env):
    handler = lambda r: httpx.Response(429, text="slow down", headers={"retry-after": "7"})  # noqa: E731

    with _mock_client(handler):
        with pytest.raises(own.RateLimitError) as exc:
            _ = [d async for d in own.stream_own_llm([{"role": "user", "content": "x"}])]

    # The shared cooldown tracker matches on the class NAME and reads retry-after.
    from routers.chat import _extract_retry_after, _note_provider_failure, _provider_available

    assert type(exc.value).__name__ == "RateLimitError"
    assert _extract_retry_after(exc.value) == 7.0
    _note_provider_failure("OwnLLMTest", exc.value)
    assert _provider_available("OwnLLMTest") is False


@pytest.mark.anyio
async def test_stream_402_is_a_quota_block(own_env):
    with _mock_client(lambda r: httpx.Response(402, text="pay up")):
        with pytest.raises(own.OwnLLMError) as exc:
            _ = [d async for d in own.stream_own_llm([{"role": "user", "content": "x"}])]
    assert exc.value.status_code == 402


@pytest.mark.anyio
async def test_complete_returns_stripped_text(own_env):
    payload = {"choices": [{"message": {"content": "  Barka  "}}]}
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=payload)

    with _mock_client(handler):
        text = await own.complete_own_llm([{"role": "user", "content": "x"}], max_tokens=99)

    assert text == "Barka"
    assert seen["body"]["max_tokens"] == 99
    assert seen["body"]["stream"] is False


@pytest.mark.anyio
async def test_complete_malformed_raises(own_env):
    with _mock_client(lambda r: httpx.Response(200, json={"oops": 1})):
        with pytest.raises(own.OwnLLMError):
            await own.complete_own_llm([{"role": "user", "content": "x"}])


# ---------------------------------------------------------------------------
# Chain integration
# ---------------------------------------------------------------------------


def _sse_texts(content: bytes) -> list[dict]:
    return [
        json.loads(line[6:]) for line in content.decode().splitlines() if line.startswith("data: ")
    ]


@pytest.mark.anyio
async def test_chat_prefers_own_llm_when_configured(client, own_env):
    async def _own(_messages):
        yield "Daga "
        yield "samfurinmu"

    async def _boom(*_a, **_k):
        raise AssertionError("hosted provider must not be called when own LLM answers")
        yield  # pragma: no cover

    with (
        patch("routers.chat.stream_own_llm", _own),
        patch("routers.chat.stream_cerebras", _boom),
        patch("routers.chat.stream_groq", _boom),
    ):
        response = await client.post("/api/chat", json={"text": "unique-own-llm-prompt-1"})

    final = _sse_texts(response.content)[-1]
    assert final["isDone"] is True
    assert "samfurinmu" in final["text"]


@pytest.mark.anyio
async def test_chat_falls_back_to_cerebras_when_own_llm_down(client, own_env):
    async def _own_down(_messages):
        raise own.OwnLLMError(503, "gpu box offline")
        yield  # pragma: no cover

    async def _cerebras(*_a, **_k):
        yield "Cerebras ya amsa"

    with (
        patch("routers.chat.stream_own_llm", _own_down),
        patch("routers.chat.stream_cerebras", _cerebras),
    ):
        response = await client.post("/api/chat", json={"text": "unique-own-llm-prompt-2"})

    final = _sse_texts(response.content)[-1]
    assert "Cerebras ya amsa" in final["text"]


@pytest.mark.anyio
async def test_chat_chain_unchanged_when_not_configured(client, monkeypatch):
    monkeypatch.delenv("MURYA_LLM_BASE_URL", raising=False)

    async def _own(_messages):
        raise AssertionError("own LLM must not be consulted when unconfigured")
        yield  # pragma: no cover

    async def _cerebras(*_a, **_k):
        yield "hosted"

    with (
        patch("routers.chat.stream_own_llm", _own),
        patch("routers.chat.stream_cerebras", _cerebras),
    ):
        response = await client.post("/api/chat", json={"text": "unique-own-llm-prompt-3"})

    assert "hosted" in _sse_texts(response.content)[-1]["text"]
