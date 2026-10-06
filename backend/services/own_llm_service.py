"""
Self-hosted / any-vendor LLM provider over the OpenAI-compatible
/chat/completions protocol.

Why this exists: Murya's chat, document and live-voice chains were wired to
specific vendors (Cerebras, Groq, Gemini). Pointing Murya at its OWN model --
vLLM, llama.cpp's server, TGI, or any vendor speaking the same protocol -- is
now configuration, not code:

    MURYA_LLM_BASE_URL   e.g. http://gpu-box:8000/v1   (unset = provider off)
    MURYA_LLM_MODEL      the served model name          (required with the URL)
    MURYA_LLM_API_KEY    bearer token                   (optional; local servers
                                                         often need none)
    MURYA_LLM_TIMEOUT    seconds to wait on the stream  (default 60)

When enabled it is tried FIRST in every chain; the hosted providers stay behind
it as fallback. When MURYA_LLM_BASE_URL is unset, nothing here runs and the
existing chains behave exactly as before.

Built on httpx (already a dependency) rather than the `openai` SDK so adding a
sovereign provider adds no new package.

Design contract (same as the other services here): failures raise, never
silently no-op, so callers fall through to the next provider.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from typing import Any

import httpx

# Name used by the per-provider cooldown tracker in routers/chat.py.
PROVIDER_NAME = "Murya"


class OwnLLMError(RuntimeError):
    """Raised for a non-2xx reply. Carries `status_code` so the cooldown
    tracker (routers/chat._note_provider_failure) can recognise 402/403
    quota blocks and sets a cooldown instead of retrying every request.
    A 429 is exposed through the class name, which that tracker matches on."""

    def __init__(self, status_code: int, body: str, retry_after: str | None = None):
        super().__init__(f"own LLM HTTP {status_code}: {body[:200]}")
        self.status_code = status_code
        # The tracker reads err.response.headers["retry-after"] when present.
        self.response = _HeaderHolder({"retry-after": retry_after} if retry_after else {})


class RateLimitError(OwnLLMError):
    """HTTP 429. Named to match the SDKs' own class so the shared cooldown
    logic (which matches on the class NAME) treats it identically."""


class _HeaderHolder:
    def __init__(self, headers: dict[str, str]):
        self.headers = headers


def own_llm_enabled() -> bool:
    return bool(os.getenv("MURYA_LLM_BASE_URL", "").strip()) and bool(
        os.getenv("MURYA_LLM_MODEL", "").strip()
    )


def _config() -> tuple[str, str, dict[str, str], float]:
    base = os.getenv("MURYA_LLM_BASE_URL", "").strip().rstrip("/")
    model = os.getenv("MURYA_LLM_MODEL", "").strip()
    if not base or not model:
        raise RuntimeError("MURYA_LLM_BASE_URL / MURYA_LLM_MODEL not set in environment.")
    headers = {"Content-Type": "application/json"}
    key = os.getenv("MURYA_LLM_API_KEY", "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        timeout = float(os.getenv("MURYA_LLM_TIMEOUT", "60"))
    except ValueError:
        timeout = 60.0
    return f"{base}/chat/completions", model, headers, timeout


def _clean(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    # Same shape-stripping the Cerebras/Groq steps do: drop Ollama's
    # non-standard "images" key and any other extras.
    return [{"role": m["role"], "content": m["content"]} for m in messages]


def _raise_for_status(status: int, body: str, headers: httpx.Headers) -> None:
    if status < 400:
        return
    cls = RateLimitError if status == 429 else OwnLLMError
    raise cls(status, body, headers.get("retry-after"))


async def stream_own_llm(messages: list[dict[str, Any]]) -> AsyncGenerator[str, None]:
    """Stream text deltas from the configured OpenAI-compatible server."""
    url, model, headers, timeout = _config()
    payload = {"model": model, "messages": _clean(messages), "stream": True}

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5.0)) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            if resp.status_code >= 400:
                body = (await resp.aread()).decode("utf-8", "replace")
                _raise_for_status(resp.status_code, body, resp.headers)
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content")
                except (ValueError, KeyError, IndexError, TypeError):
                    continue  # keepalive / malformed frame -- skip, don't abort the reply
                if delta:
                    yield delta


async def complete_own_llm(messages: list[dict[str, Any]], max_tokens: int = 512) -> str:
    """One-shot (non-streaming) completion -- used by live voice, which needs
    the whole reply before synthesising speech."""
    url, model, headers, timeout = _config()
    payload = {
        "model": model,
        "messages": _clean(messages),
        "max_tokens": max_tokens,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5.0)) as client:
        resp = await client.post(url, headers=headers, json=payload)
    _raise_for_status(resp.status_code, resp.text, resp.headers)
    try:
        return (resp.json()["choices"][0]["message"]["content"] or "").strip()
    except (ValueError, KeyError, IndexError, TypeError) as err:
        raise OwnLLMError(resp.status_code, f"malformed completion: {err}") from err
