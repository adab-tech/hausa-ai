"""Tests for cloudflare_stt_service / search_service / you_service's "never
raises" contract.

Regression: all three modules called `.get(...)` on the parsed JSON response
OUTSIDE the try/except that produced it. A non-dict JSON body (a bare
`null`, or a JSON array) makes `resp.json()` return `None`/`list` instead of
a dict, and `.get(...)` on either raises AttributeError straight into the
request path -- contradicting each module's own documented "never raises"
contract. Each module must now degrade to its documented empty-result value
(None or []) instead.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import services.cloudflare_stt_service as cloudflare_stt_service
import services.search_service as search_service
import services.you_service as you_service


def _fake_client_returning(json_body):
    """Build a fake httpx.AsyncClient (as an async context manager) whose
    .post() returns a response with the given (already-parsed) JSON body."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value=json_body)

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# ---------------------------------------------------------------------------
# cloudflare_stt_service
# ---------------------------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.parametrize("bad_body", [None, [], ["unexpected", "array"]])
async def test_cloudflare_stt_non_dict_json_returns_none_not_raise(monkeypatch, bad_body):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acct")
    with patch("httpx.AsyncClient", return_value=_fake_client_returning(bad_body)):
        result = await cloudflare_stt_service.transcribe_via_cloudflare(b"fake-wav-bytes")
    assert result is None


# ---------------------------------------------------------------------------
# search_service (Tavily)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.parametrize("bad_body", [None, [], [{"title": "x"}]])
async def test_tavily_search_non_dict_json_returns_empty_list_not_raise(monkeypatch, bad_body):
    monkeypatch.setenv("TAVILY_API_KEY", "tok")
    with patch("httpx.AsyncClient", return_value=_fake_client_returning(bad_body)):
        result = await search_service.web_search("zaben Najeriya")
    assert result == []


# ---------------------------------------------------------------------------
# you_service (You.com)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.parametrize("bad_body", [None, [], [{"answer": "x"}]])
async def test_you_search_non_dict_json_returns_empty_list_not_raise(monkeypatch, bad_body):
    monkeypatch.setenv("YOU_API_KEY", "tok")
    with patch("httpx.AsyncClient", return_value=_fake_client_returning(bad_body)):
        result = await you_service.web_search_you("zaben Najeriya")
    assert result == []


# ---------------------------------------------------------------------------
# Sanity checks: the normal, well-formed dict-body path still works after
# adding the isinstance guard (guards against an overly-broad fix).
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_cloudflare_stt_still_works_for_normal_dict_response(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acct")
    body = {"success": True, "result": {"text": " sannu "}}
    with patch("httpx.AsyncClient", return_value=_fake_client_returning(body)):
        result = await cloudflare_stt_service.transcribe_via_cloudflare(b"fake-wav-bytes")
    assert result == "sannu"


@pytest.mark.anyio
async def test_tavily_search_still_works_for_normal_dict_response(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tok")
    body = {"answer": "Test answer", "results": [{"title": "T", "url": "u", "content": "c"}]}
    with patch("httpx.AsyncClient", return_value=_fake_client_returning(body)):
        result = await search_service.web_search("query")
    assert result[0]["title"] == "Tavily summary"
    assert result[1]["title"] == "T"
