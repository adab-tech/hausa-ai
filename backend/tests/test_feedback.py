"""Tests for /api/feedback and the human-validated corrections queue."""

import pytest

from routers import feedback as feedback_module
import corrections_store


@pytest.fixture(autouse=True)
def _isolated_feedback_file(tmp_path, monkeypatch):
    """Redirect feedback + corrections storage to scratch files for each test."""
    scratch = tmp_path / "feedback.jsonl"
    monkeypatch.setattr(feedback_module, "_FEEDBACK_FILE", scratch)
    monkeypatch.setattr(feedback_module, "_DATA_DIR", tmp_path)

    corrections_scratch = tmp_path / "corrections.jsonl"
    monkeypatch.setattr(corrections_store, "_CORRECTIONS_FILE", corrections_scratch)
    monkeypatch.setattr(corrections_store, "_DATA_DIR", tmp_path)
    return scratch


@pytest.mark.anyio
async def test_feedback_rejects_invalid_type(client):
    response = await client.post(
        "/api/feedback", json={"messageId": "1", "type": "sideways", "text": "hi"}
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_feedback_records_and_stats_reflect_it(client):
    stats_before = (await client.get("/api/feedback/stats")).json()

    resp = await client.post(
        "/api/feedback", json={"messageId": "1", "type": "up", "text": "Barka da yini"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "recorded"}

    resp2 = await client.post(
        "/api/feedback", json={"messageId": "2", "type": "down", "text": "Kuskure"}
    )
    assert resp2.status_code == 200

    stats_after = (await client.get("/api/feedback/stats")).json()
    assert stats_after["up"] == stats_before["up"] + 1
    assert stats_after["down"] == stats_before["down"] + 1
    assert stats_after["total"] == stats_before["total"] + 2


@pytest.mark.anyio
async def test_feedback_with_correction_creates_pending_entry(client):
    resp = await client.post(
        "/api/feedback",
        json={
            "messageId": "42",
            "type": "down",
            "text": "Babban birnin Nijeriya Legas ne.",
            "correction": "Babban birnin Nijeriya Abuja ne, ba Legas ba.",
        },
    )
    assert resp.status_code == 200

    pending = (await client.get("/api/corrections", params={"status": "pending"})).json()
    assert len(pending) == 1
    assert pending[0]["messageId"] == "42"
    assert pending[0]["correction"] == "Babban birnin Nijeriya Abuja ne, ba Legas ba."
    assert pending[0]["status"] == "pending"


@pytest.mark.anyio
async def test_feedback_without_correction_creates_no_pending_entry(client):
    await client.post(
        "/api/feedback", json={"messageId": "1", "type": "up", "text": "Barka da yini"}
    )
    pending = (await client.get("/api/corrections", params={"status": "pending"})).json()
    assert pending == []


@pytest.mark.anyio
async def test_correction_approval_flow(client):
    await client.post(
        "/api/feedback",
        json={
            "messageId": "7",
            "type": "down",
            "text": "Wrong answer",
            "correction": "The right answer",
        },
    )
    pending = (await client.get("/api/corrections", params={"status": "pending"})).json()
    correction_id = pending[0]["id"]

    resp = await client.post(f"/api/corrections/{correction_id}/review", json={"action": "approve"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    approved = (await client.get("/api/corrections", params={"status": "approved"})).json()
    assert len(approved) == 1

    prompt = corrections_store.get_approved_corrections_prompt()
    assert "The right answer" in prompt
    assert "Wrong answer" in prompt


@pytest.mark.anyio
async def test_review_nonexistent_correction_404s(client):
    resp = await client.post("/api/corrections/does-not-exist/review", json={"action": "approve"})
    assert resp.status_code == 404
