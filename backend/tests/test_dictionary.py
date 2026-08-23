"""Tests for GET /api/dictionary — the standalone dictionary search endpoint."""

import pytest


@pytest.mark.anyio
async def test_dictionary_search_returns_results_for_known_word(client):
    resp = await client.get("/api/dictionary", params={"q": "ruwa"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True
    assert body["query"] == "ruwa"
    assert len(body["results"]) > 0
    first = body["results"][0]
    assert set(first.keys()) == {"headword", "translation", "context", "direction", "source"}


@pytest.mark.anyio
async def test_dictionary_search_empty_for_unknown_word(client):
    resp = await client.get("/api/dictionary", params={"q": "zzzznonexistentword9999"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True
    assert body["results"] == []


@pytest.mark.anyio
async def test_dictionary_search_rejects_empty_query(client):
    resp = await client.get("/api/dictionary", params={"q": ""})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_dictionary_search_requires_query_param(client):
    resp = await client.get("/api/dictionary")
    assert resp.status_code == 422
