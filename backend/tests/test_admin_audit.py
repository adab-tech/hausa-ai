"""Tests for the unified admin audit log (admin_audit_store.py) and the
GET /api/admin/audit-log endpoint that surfaces it. Added alongside the
admin-panel enhancement pass: pronunciation_store.py and qa_store.py record
a timestamp on approve/reject/delete but no admin identity at all, so there
was previously no way to answer "what has the admin account done recently"
across all three review surfaces. These tests cover the store in isolation
and its wiring into the corrections/pronunciation/Q&A review routes."""

import io
import wave

import pytest

import admin_audit_store
import corrections_store
import pronunciation_store
import qa_store


@pytest.fixture
def _isolated_audit_store(tmp_path, monkeypatch):
    monkeypatch.setattr(admin_audit_store, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(admin_audit_store, "_DB_PATH", tmp_path / "admin_audit.db")
    admin_audit_store.init_db()


@pytest.fixture
def _isolated_corrections_store(tmp_path, monkeypatch):
    monkeypatch.setattr(corrections_store, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(corrections_store, "_CORRECTIONS_FILE", tmp_path / "corrections.jsonl")


@pytest.fixture
def _isolated_pronunciation_store(tmp_path, monkeypatch):
    monkeypatch.setattr(pronunciation_store, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(pronunciation_store, "_DB_PATH", tmp_path / "pronunciation.db")
    pronunciation_store.init_db()


@pytest.fixture
def _isolated_qa_store(tmp_path, monkeypatch):
    monkeypatch.setattr(qa_store, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(qa_store, "_DB_PATH", tmp_path / "qa.db")
    qa_store.init_db()


def _wav_bytes() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(b"\x00\x00" * 2400)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Store unit tests
# ---------------------------------------------------------------------------
def test_log_and_list_recent(_isolated_audit_store):
    admin_audit_store.log("adamu", "approve", "qa", 7, detail="Yaya kake?")
    admin_audit_store.log("adamu", "delete", "pronunciation", 3)
    items = admin_audit_store.list_recent()
    assert len(items) == 2
    # Newest first.
    assert items[0]["action"] == "delete"
    assert items[0]["surface"] == "pronunciation"
    assert items[0]["target_id"] == "3"
    assert items[1]["detail"] == "Yaya kake?"


def test_list_recent_filters_by_surface(_isolated_audit_store):
    admin_audit_store.log("adamu", "approve", "qa", 1)
    admin_audit_store.log("adamu", "approve", "pronunciation", 2)
    qa_only = admin_audit_store.list_recent(surface="qa")
    assert len(qa_only) == 1
    assert qa_only[0]["surface"] == "qa"


def test_log_never_raises_on_db_failure(_isolated_audit_store, monkeypatch):
    """The whole point of log() swallowing errors: an audit-log write
    failing (e.g. disk full) must never take down the approve/reject/delete
    action it's recording."""
    def _boom(*a, **kw):
        raise sqlite3_error()

    def sqlite3_error():
        import sqlite3
        return sqlite3.OperationalError("disk full")

    import admin_audit_store as mod
    monkeypatch.setattr(mod, "_get_conn", lambda: (_ for _ in ()).throw(sqlite3_error()))
    # Must not raise.
    admin_audit_store.log("adamu", "approve", "qa", 1)


# ---------------------------------------------------------------------------
# Wired into the review routes
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_audit_log_endpoint_requires_admin_session(client, _isolated_audit_store):
    resp = await client.get("/api/admin/audit-log")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_qa_status_change_is_audited(
    client, admin_session, _isolated_audit_store, _isolated_qa_store
):
    row_id = qa_store.submit("Yaya ake cewa 'hello'?", "Sannu", None, "dev-1")
    resp = await client.post(f"/api/admin/qa/{row_id}/status", json={"status": "approved"})
    assert resp.status_code == 200

    log_resp = await client.get("/api/admin/audit-log")
    assert log_resp.status_code == 200
    items = log_resp.json()["items"]
    matching = [i for i in items if i["surface"] == "qa" and i["target_id"] == str(row_id)]
    assert len(matching) == 1
    assert matching[0]["action"] == "approved"
    assert matching[0]["admin"] == admin_session


@pytest.mark.anyio
async def test_qa_delete_is_audited(
    client, admin_session, _isolated_audit_store, _isolated_qa_store
):
    row_id = qa_store.submit("Q", "A", None, "dev-1")
    resp = await client.delete(f"/api/admin/qa/{row_id}")
    assert resp.status_code == 200

    log_resp = await client.get("/api/admin/audit-log")
    items = log_resp.json()["items"]
    matching = [i for i in items if i["surface"] == "qa" and i["action"] == "delete"]
    assert len(matching) == 1
    assert matching[0]["target_id"] == str(row_id)


@pytest.mark.anyio
async def test_pronunciation_status_change_is_audited(
    client, admin_session, _isolated_audit_store, _isolated_pronunciation_store
):
    row_id = pronunciation_store.add_correction(
        "gida", speaker_id=0, audio_pcm=b"\x01\x00" * 2400, submitted_by="reviewer:test"
    )
    resp = await client.post(
        f"/api/admin/pronunciation/{row_id}/status", json={"status": "approved"}
    )
    assert resp.status_code == 200

    log_resp = await client.get("/api/admin/audit-log")
    items = log_resp.json()["items"]
    matching = [i for i in items if i["surface"] == "pronunciation" and i["target_id"] == str(row_id)]
    assert len(matching) == 1
    assert matching[0]["action"] == "approved"


@pytest.mark.anyio
async def test_pronunciation_delete_is_audited(
    client, admin_session, _isolated_audit_store, _isolated_pronunciation_store
):
    row_id = pronunciation_store.flag("sallah", speaker_id=0, submitted_by="dev")
    resp = await client.delete(f"/api/admin/pronunciation/{row_id}")
    assert resp.status_code == 200

    log_resp = await client.get("/api/admin/audit-log")
    items = log_resp.json()["items"]
    matching = [i for i in items if i["surface"] == "pronunciation" and i["action"] == "delete"]
    assert len(matching) == 1


@pytest.mark.anyio
async def test_correction_review_is_audited(
    client, admin_session, _isolated_audit_store, _isolated_corrections_store
):
    entry = corrections_store.add_correction("msg-1", "wrong text", "right text", contributor_id="dev-1")
    resp = await client.post(
        f"/api/corrections/{entry['id']}/review", json={"action": "approve"}
    )
    assert resp.status_code == 200

    log_resp = await client.get("/api/admin/audit-log")
    items = log_resp.json()["items"]
    matching = [i for i in items if i["surface"] == "correction" and i["target_id"] == entry["id"]]
    assert len(matching) == 1
    assert matching[0]["action"] == "approve"
    assert matching[0]["detail"] == "right text"


@pytest.mark.anyio
async def test_audit_log_surface_filter(
    client, admin_session, _isolated_audit_store, _isolated_qa_store, _isolated_pronunciation_store
):
    qa_id = qa_store.submit("Q", "A", None, "dev-1")
    await client.post(f"/api/admin/qa/{qa_id}/status", json={"status": "approved"})
    pron_id = pronunciation_store.flag("sallah", speaker_id=0, submitted_by="dev")
    await client.delete(f"/api/admin/pronunciation/{pron_id}")

    resp = await client.get("/api/admin/audit-log?surface=qa")
    items = resp.json()["items"]
    assert all(i["surface"] == "qa" for i in items)
    assert len(items) == 1
