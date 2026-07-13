"""Tests for the human-in-the-loop pronunciation correction loop."""

import os
import tempfile

import pytest

# Point the store at a throwaway data dir BEFORE importing it.
os.environ.setdefault("FEEDBACK_DATA_DIR", tempfile.mkdtemp(prefix="pron_test_"))

import pronunciation_store as store  # noqa: E402

_PCM = b"\x01\x00" * 2400  # 0.1 s of near-silent 24 kHz PCM-16 as stand-in audio


@pytest.fixture(autouse=True)
def _fresh_db():
    store._reset_for_tests()
    yield


def test_fold_key_normalizes():
    assert store.fold_key("  Ƙasa! ") == "kasa"
    assert store.fold_key("Ina Kwana") == "ina kwana"
    assert store.fold_key("ɓarna") == "barna"
    assert store.fold_key("") == ""


def test_flag_creates_pending_without_audio():
    rid = store.flag("kwamfuta", speaker_id=0, submitted_by="dev-1", note="wrong stress")
    assert rid
    items = store.list_items(status="pending")
    assert len(items) == 1
    assert items[0]["has_audio"] is False
    assert items[0]["status"] == "pending"
    # No audio yet -> lookup must not return anything.
    assert store.lookup("kwamfuta", 0) is None


def test_recording_lands_pending_until_approved():
    # Recording is NOT approving — nothing is served until the owner approves.
    rid = store.add_correction("kwamfuta", speaker_id=0, audio_pcm=_PCM, submitted_by="reviewer:adamu")
    assert rid
    assert store.list_items(status="pending")[0]["id"] == rid
    assert store.lookup("kwamfuta", 0) is None            # pending -> not served
    assert store.set_status(rid, "approved") is True
    assert store.lookup("kwamfuta", 0) == _PCM            # approved -> served
    # Case/diacritic/whitespace-insensitive.
    assert store.lookup("  KWAMFUTA ", 0) == _PCM
    assert store.lookup("wani-abu-dabam", 0) is None


def test_voice_specific_beats_agnostic():
    a = store.add_correction("gida", speaker_id=None, audio_pcm=b"\x02\x00" * 100)  # agnostic
    b = store.add_correction("gida", speaker_id=4, audio_pcm=_PCM)                  # voice 4
    store.set_status(a, "approved")
    store.set_status(b, "approved")
    assert store.lookup("gida", 4) == _PCM               # voice-specific wins
    assert store.lookup("gida", 1) == b"\x02\x00" * 100  # falls back to agnostic


def test_attach_audio_leaves_pending():
    rid = store.flag("sallah", speaker_id=0, submitted_by="dev")
    assert store.lookup("sallah", 0) is None
    assert store.attach_audio(rid, _PCM) is True
    assert store.lookup("sallah", 0) is None             # recorded but not yet approved
    assert store.set_status(rid, "approved") is True
    assert store.lookup("sallah", 0) == _PCM


def test_reject_removes_from_lookup():
    rid = store.add_correction("barka", speaker_id=0, audio_pcm=_PCM)
    store.set_status(rid, "approved")
    assert store.lookup("barka", 0) == _PCM
    assert store.set_status(rid, "rejected") is True
    assert store.lookup("barka", 0) is None


def test_export_approved_only():
    one = store.add_correction("one", speaker_id=0, audio_pcm=_PCM)
    store.set_status(one, "approved")
    store.add_correction("two", speaker_id=0, audio_pcm=_PCM)  # pending, never approved
    store.flag("three", speaker_id=0, submitted_by="dev")      # pending, no audio
    exported = store.export_approved()
    assert [e["text"] for e in exported] == ["one"]
    assert exported[0]["audio"] == _PCM


def test_counts_and_delete():
    rid_a = store.add_correction("a", speaker_id=0, audio_pcm=_PCM)
    store.set_status(rid_a, "approved")
    rid = store.flag("b", speaker_id=0, submitted_by="d")
    c = store.counts()
    assert c["approved"] == 1 and c["pending"] == 1
    assert store.delete(rid) is True
    assert store.counts()["pending"] == 0


def test_oversize_audio_rejected():
    big = b"\x00" * (store._MAX_AUDIO_BYTES + 2)
    with pytest.raises(ValueError):
        store.add_correction("huge", speaker_id=0, audio_pcm=big)
