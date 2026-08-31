"""Tests for the MOS (Mean Opinion Score) listening-test store."""

import os
import tempfile

import pytest

# Point the store at a throwaway data dir BEFORE importing it.
os.environ.setdefault("FEEDBACK_DATA_DIR", tempfile.mkdtemp(prefix="mos_test_"))

import mos_store as store  # noqa: E402

_PCM = b"\x01\x00" * 2400  # 0.1 s of near-silent 24 kHz PCM-16 as stand-in audio


@pytest.fixture(autouse=True)
def _fresh_db():
    store._reset_for_tests()
    yield


def _seed_basic():
    """8 murya voices x 1 sentence + 1 ground-truth clip — enough to exercise
    session-building and aggregation without a real synthesis run."""
    for voice in ["F1", "F2", "F3", "F4", "M1", "M2", "M3", "M4"]:
        store.add_stimulus(f"murya_{voice}_s1", "murya", voice, "s1", "sannu", _PCM)
    store.add_stimulus("groundtruth_gt1", "ground_truth", "human", "gt1", "sannu", _PCM)


def test_build_session_mixes_conditions_and_is_bounded():
    _seed_basic()
    session = store.build_session()
    assert 1 <= len(session) <= store._SESSION_SIZE
    conditions = {c["condition"] for c in session}
    assert "murya" in conditions
    assert "ground_truth" in conditions
    # No audio in session metadata — fetched separately by clip_id.
    assert all("audio" not in c for c in session)


def test_build_session_empty_when_no_stimuli():
    assert store.build_session() == []


def test_get_audio_roundtrip():
    _seed_basic()
    assert store.get_audio("murya_F1_s1") == _PCM
    assert store.get_audio("does-not-exist") is None


def test_record_session_and_results():
    _seed_basic()
    answers = [
        store.RatingIn("murya_F1_s1", "murya", "F1", "s1", 4, "yes", replays=1),
        store.RatingIn("murya_M1_s1", "murya", "M1", "s1", 2, "no", replays=0),
        store.RatingIn("groundtruth_gt1", "ground_truth", "human", "gt1", 5, "yes"),
    ]
    n = store.record_session("sess-1", answers, region="Nigeria", native_speaker=True, submitted_by="cid-1")
    assert n == 3

    results = store.list_results()
    assert results["total_ratings"] == 3
    assert results["session_count"] == 1
    assert results["by_condition"]["murya"]["n"] == 2
    assert results["by_condition"]["murya"]["mean"] == 3.0
    assert results["by_condition"]["ground_truth"]["mean"] == 5.0
    assert results["by_voice"]["F1"]["mean"] == 4.0
    assert results["intelligibility"] == {"yes": 2, "partial": 0, "no": 1}


def test_record_session_empty_is_noop():
    assert store.record_session("sess-empty", [], region=None, native_speaker=False, submitted_by=None) == 0


def test_analysis_flags_insufficient_data_below_threshold():
    _seed_basic()
    answers = [store.RatingIn("murya_F1_s1", "murya", "F1", "s1", 4, "yes")]
    store.record_session("sess-1", answers, region=None, native_speaker=False, submitted_by=None)
    analysis = store.list_results()["analysis"]
    assert analysis["verdict"] == "insufficient_data"


def test_analysis_close_to_human_when_gap_small():
    _seed_basic()
    n = store._MIN_TRUSTWORTHY_N
    murya_answers = [store.RatingIn("murya_F1_s1", "murya", "F1", "s1", 4, "yes") for _ in range(n)]
    truth_answers = [store.RatingIn("groundtruth_gt1", "ground_truth", "human", "gt1", 4, "yes") for _ in range(n)]
    store.record_session("sess-1", murya_answers + truth_answers, region=None, native_speaker=True, submitted_by=None)
    analysis = store.list_results()["analysis"]
    assert analysis["verdict"] == "close_to_human"
    assert analysis["gap"] == 0.0


def test_analysis_meaningful_gap_when_large():
    _seed_basic()
    n = store._MIN_TRUSTWORTHY_N
    murya_answers = [store.RatingIn("murya_F1_s1", "murya", "F1", "s1", 2, "yes") for _ in range(n)]
    truth_answers = [store.RatingIn("groundtruth_gt1", "ground_truth", "human", "gt1", 5, "yes") for _ in range(n)]
    store.record_session("sess-1", murya_answers + truth_answers, region=None, native_speaker=True, submitted_by=None)
    analysis = store.list_results()["analysis"]
    assert analysis["verdict"] == "meaningful_gap"
    assert analysis["gap"] == 3.0


def test_analysis_flags_weak_voice():
    for voice in ["F1", "M1"]:
        store.add_stimulus(f"murya_{voice}_s1", "murya", voice, "s1", "sannu", _PCM)
    n = max(5, store._MIN_TRUSTWORTHY_N // 4)
    good = [store.RatingIn("murya_F1_s1", "murya", "F1", "s1", 5, "yes") for _ in range(n)]
    weak = [store.RatingIn("murya_M1_s1", "murya", "M1", "s1", 2, "yes") for _ in range(n)]
    store.record_session("sess-1", good + weak, region=None, native_speaker=True, submitted_by=None)
    analysis = store.list_results()["analysis"]
    assert any(w["voice"] == "M1" for w in analysis["weak_voices"])
    assert not any(w["voice"] == "F1" for w in analysis["weak_voices"])


def test_record_decision_snapshots_current_stats():
    _seed_basic()
    answers = [store.RatingIn("murya_F1_s1", "murya", "F1", "s1", 4, "yes")]
    store.record_session("sess-1", answers, region=None, native_speaker=True, submitted_by=None)

    did = store.record_decision("needs_more_data", "not enough data yet", admin="adamu")
    assert did

    decisions = store.list_decisions()
    assert len(decisions) == 1
    assert decisions[0]["verdict"] == "needs_more_data"
    assert decisions[0]["murya_mean_at_time"] == 4.0
    assert decisions[0]["admin"] == "adamu"

    # A later rating must NOT retroactively change what was decided.
    store.record_session("sess-2", [store.RatingIn("murya_F1_s1", "murya", "F1", "s1", 1, "yes")],
                         region=None, native_speaker=True, submitted_by=None)
    assert store.list_decisions()[0]["murya_mean_at_time"] == 4.0


def test_record_decision_rejects_invalid_verdict():
    with pytest.raises(ValueError):
        store.record_decision("maybe", None, admin="adamu")


def test_export_ratings_returns_raw_rows():
    _seed_basic()
    answers = [store.RatingIn("murya_F1_s1", "murya", "F1", "s1", 4, "yes")]
    store.record_session("sess-1", answers, region="Niger", native_speaker=True, submitted_by="cid-2")
    exported = store.export_ratings()
    assert len(exported) == 1
    assert exported[0]["clip_id"] == "murya_F1_s1"
    assert exported[0]["region"] == "Niger"
    assert exported[0]["native_speaker"] == 1
