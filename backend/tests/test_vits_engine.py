"""Tests for services/vits_engine.py's init-failure caching."""

from unittest.mock import patch

from services.vits_engine import VitsEngine


def _broken_engine(tmp_path):
    """A VitsEngine whose model file exists (so synthesize() would normally
    attempt to initialize) but whose ONNX session construction always fails,
    simulating a broken/corrupted model on disk."""
    (tmp_path / "best_model.onnx").write_bytes(b"not a real onnx model")
    return VitsEngine(model_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# Regression: synthesize() used to re-attempt the full (expensive) ONNX
# session init on every call after the first failure, instead of caching the
# failure and failing fast. initialize() itself is left un-mocked (only the
# ONNX session construction is patched to fail) so this exercises the real
# _init_failed bookkeeping, not a mocked shortcut.
# ---------------------------------------------------------------------------
def test_synthesize_does_not_reinitialize_after_first_failure(tmp_path):
    engine = _broken_engine(tmp_path)
    assert engine.model_path.exists()
    # __init__ already attempted (and failed) initialize() once, since the
    # model file exists but is invalid -- this itself is the FIRST failed
    # attempt, so _init_failed is already cached True before synthesize() is
    # ever called.
    assert engine._init_failed is True

    with patch("onnxruntime.InferenceSession", side_effect=RuntimeError("boom")), \
         patch.object(engine, "initialize", wraps=engine.initialize) as spy_init:
        assert engine.synthesize("sannu") is None
        assert engine.synthesize("sannu") is None
        assert engine.synthesize("sannu") is None
        # None of these calls should have re-attempted the expensive init --
        # the cached _init_failed flag must short-circuit every one of them.
        assert spy_init.call_count == 0

    assert engine._init_failed is True


def test_synthesize_attempts_init_exactly_once_then_caches_the_failure(tmp_path):
    # No model file at construction time -- __init__ does NOT call
    # initialize() itself, so _init_failed starts False and the first
    # synthesize() call is the one that discovers the model is broken.
    engine = VitsEngine(model_dir=str(tmp_path))
    assert engine._init_failed is False
    (tmp_path / "best_model.onnx").write_bytes(b"not a real onnx model")
    # VitsEngine resolves model_path once at construction time; point it at
    # the file we just created.
    engine.model_path = tmp_path / "best_model.onnx"

    with patch.object(engine, "initialize", wraps=engine.initialize) as spy_init:
        assert engine.synthesize("sannu") is None
        assert engine._init_failed is True
        assert engine.synthesize("sannu") is None
        assert engine.synthesize("sannu") is None
        # Real ONNX parsing of the bogus file fails on its own -- only the
        # first call should have paid that cost.
        assert spy_init.call_count == 1


def test_init_failed_flag_set_on_initialize_failure(tmp_path):
    engine = _broken_engine(tmp_path)
    with patch("onnxruntime.InferenceSession", side_effect=RuntimeError("boom")):
        ok = engine.initialize()
    assert ok is False
    assert engine._init_failed is True


def test_init_failed_flag_cleared_on_successful_reinitialize(tmp_path):
    engine = _broken_engine(tmp_path)
    engine._init_failed = True  # simulate a prior failure
    with patch("onnxruntime.InferenceSession") as mock_session_cls:
        mock_session_cls.return_value.get_inputs.return_value = []
        ok = engine.initialize()
    assert ok is True
    assert engine._init_failed is False
