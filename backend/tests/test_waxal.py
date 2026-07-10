import pytest
from unittest.mock import patch
from httpx import AsyncClient

# Mock WAXAL metadata so tests run successfully without requiring the full 2GB corpus in CI
MOCK_METADATA = [
    {"speaker_id": "6", "gender": "Male", "text": "Kwallo yana da daɗi."},
    {"speaker_id": "2", "gender": "Female", "text": "Sannu ku da zuwa."},
    {"speaker_id": "6", "gender": "Male", "text": "Muna son kwallo sosai."},
]

@pytest.fixture(autouse=True)
def mock_waxal_metadata():
    with patch("routers.waxal._load_metadata", return_value=MOCK_METADATA):
        yield

@pytest.mark.anyio
async def test_waxal_stats_requires_admin_session(client: AsyncClient):
    """The dataset browser is internal review tooling, not a public
    endpoint — must reject requests without a valid admin session."""
    response = await client.get("/api/waxal/stats")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_waxal_stats(client: AsyncClient, admin_session):
    response = await client.get("/api/waxal/stats")
    assert response.status_code == 200
    data = response.json()
    
    # Check that general statistics are present
    assert "general" in data
    assert data["general"]["total_samples"] == 3
    assert data["general"]["total_speakers"] == 2
    assert "linguistic" in data
    assert "orthography" in data

@pytest.mark.anyio
async def test_waxal_samples_pagination(client: AsyncClient, admin_session):
    response = await client.get("/api/waxal/samples?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    
    assert "samples" in data
    assert len(data["samples"]) == 3
    assert "total_count" in data
    assert "total_pages" in data
    assert data["page"] == 1
    assert data["page_size"] == 5

@pytest.mark.anyio
async def test_waxal_samples_filtering(client: AsyncClient, admin_session):
    # Filter by speaker
    response = await client.get("/api/waxal/samples?speaker_id=6")
    assert response.status_code == 200
    data = response.json()
    assert len(data["samples"]) == 2
    for s in data["samples"]:
        assert s["speaker_id"] == "6"

    # Filter by search query
    response = await client.get("/api/waxal/samples?query=kwallo")
    assert response.status_code == 200
    data = response.json()
    assert len(data["samples"]) == 2
    for s in data["samples"]:
        assert "kwallo" in s["text"].lower()

@pytest.mark.anyio
async def test_waxal_audio_not_found(client: AsyncClient, admin_session):
    response = await client.get("/api/waxal/audio/nonexistent_file_12345.mp3")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_waxal_tts_match(client: AsyncClient, admin_session):
    response = await client.get("/api/waxal/tts?text=kwallo")
    assert response.status_code == 200
    data = response.json()
    assert "sample" in data
    assert "similarity" in data
    assert "audio_url" in data
    assert "kwallo" in data["sample"]["text"].lower()


@pytest.mark.anyio
async def test_waxal_tts_fallback(client: AsyncClient, admin_session):
    response = await client.get("/api/waxal/tts?text=unrecognizedpattern")
    assert response.status_code == 200
    data = response.json()
    assert "sample" in data
    assert "similarity" in data
    assert "audio_url" in data

