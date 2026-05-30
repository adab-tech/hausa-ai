import os
import pytest
from httpx import AsyncClient

@pytest.mark.anyio
async def test_waxal_stats(client: AsyncClient):
    response = await client.get("/api/waxal/stats")
    assert response.status_code == 200
    data = response.json()
    
    # Check that general statistics are present
    assert "general" in data
    assert "total_samples" in data["general"]
    assert "total_speakers" in data["general"]
    assert "linguistic" in data
    assert "orthography" in data

@pytest.mark.anyio
async def test_waxal_samples_pagination(client: AsyncClient):
    response = await client.get("/api/waxal/samples?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    
    assert "samples" in data
    assert len(data["samples"]) <= 5
    assert "total_count" in data
    assert "total_pages" in data
    assert data["page"] == 1
    assert data["page_size"] == 5

@pytest.mark.anyio
async def test_waxal_samples_filtering(client: AsyncClient):
    # Filter by speaker
    response = await client.get("/api/waxal/samples?speaker_id=6")
    assert response.status_code == 200
    data = response.json()
    for s in data["samples"]:
        assert s["speaker_id"] == "6"

    # Filter by search query
    response = await client.get("/api/waxal/samples?query=kwallo")
    assert response.status_code == 200
    data = response.json()
    assert len(data["samples"]) > 0
    for s in data["samples"]:
        assert "kwallo" in s["text"].lower()

@pytest.mark.anyio
async def test_waxal_audio_not_found(client: AsyncClient):
    response = await client.get("/api/waxal/audio/nonexistent_file_12345.mp3")
    assert response.status_code == 404
