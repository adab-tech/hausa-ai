"""Tests for the /health endpoint."""

import pytest


@pytest.mark.anyio
async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_health_payload(client):
    response = await client.get("/health")
    data = response.json()
    assert data["status"] == "sovereign"
    assert "version" in data
