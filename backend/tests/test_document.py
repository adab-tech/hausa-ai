"""Tests for /api/document (one-shot translate / summarize)."""

import json
from unittest.mock import patch

import pytest


def _iter_sse(content: bytes) -> list[dict]:
    events = []
    for line in content.decode().splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_document_rejects_bad_action(client):
    resp = await client.post("/api/document", json={"text": "hi", "action": "rewrite", "target": "ha"})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_document_rejects_bad_target(client):
    resp = await client.post("/api/document", json={"text": "hi", "action": "translate", "target": "fr"})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_document_rejects_empty_text(client):
    resp = await client.post("/api/document", json={"text": "", "action": "translate", "target": "en"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# System-prompt shaping
# ---------------------------------------------------------------------------
def test_translate_prompt_names_target_language():
    from routers.document import _system_prompt

    en = _system_prompt("translate", "en")
    ha = _system_prompt("translate", "ha")
    assert "English" in en and "translat" in en.lower()
    assert "Hausa" in ha and "ɓ" in ha  # hooked-letter orthography note for Hausa target


def test_summarize_prompt_is_summary():
    from routers.document import _system_prompt

    assert "summar" in _system_prompt("summarize", "ha").lower()


# ---------------------------------------------------------------------------
# Streaming (Cerebras mocked) — the translated/summarized text comes back
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_document_translate_streams_result(client):
    async def _fake_stream_cerebras(messages, *_a, **_k):
        # Assert the doc text reached the model as the user turn.
        assert any("Sannu duniya" in m["content"] for m in messages)
        for piece in ("Hello", " ", "world"):
            yield piece

    with patch("routers.chat.stream_cerebras", _fake_stream_cerebras):
        resp = await client.post(
            "/api/document",
            json={"text": "Sannu duniya", "action": "translate", "target": "en"},
        )
    assert resp.status_code == 200
    events = _iter_sse(resp.content)
    final = events[-1]
    assert final["isDone"] is True
    assert "Hello world" in final["text"]


@pytest.mark.anyio
async def test_document_reports_error_gracefully(client):
    async def _boom(*_a, **_k):
        raise RuntimeError("provider down")
        yield  # make it an async generator

    # document_endpoint now falls through Cerebras -> Ollama -> Gemini (same
    # chain as /api/chat); all three must fail to reach the final error path.
    with (
        patch("routers.chat.stream_cerebras", _boom),
        patch("routers.chat.stream_ollama", _boom),
        patch("routers.chat.stream_gemini_raw", _boom),
    ):
        resp = await client.post(
            "/api/document",
            json={"text": "wani rubutu", "action": "summarize", "target": "ha"},
        )
    assert resp.status_code == 200
    final = _iter_sse(resp.content)[-1]
    assert final["isDone"] is True
    assert "error" in final


async def test_document_falls_back_to_ollama_when_cerebras_fails(client):
    async def _boom(*_a, **_k):
        raise RuntimeError("cerebras down")
        yield  # make it an async generator

    async def _ollama_ok(*_a, **_k):
        for chunk in ("Taƙaice: ", "wannan labari ne."):
            yield chunk

    with (
        patch("routers.chat.stream_cerebras", _boom),
        patch("routers.chat.stream_ollama", _ollama_ok),
    ):
        resp = await client.post(
            "/api/document",
            json={"text": "wani rubutu", "action": "summarize", "target": "ha"},
        )
    assert resp.status_code == 200
    final = _iter_sse(resp.content)[-1]
    assert final["isDone"] is True
    assert "error" not in final
    assert "wannan labari ne" in final["text"]
