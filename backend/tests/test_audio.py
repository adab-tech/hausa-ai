"""Tests for the pure helper functions in routers.audio."""

import struct
import wave

import numpy as np
import pytest

from routers.audio import (
    _float32_to_pcm16_bytes,
    _pcm_bytes_to_float32,
    _synthesize_speech,
    _write_wav,
)


# ---------------------------------------------------------------------------
# PCM conversion round-trip
# ---------------------------------------------------------------------------

def test_pcm_bytes_to_float32_shape():
    """16-bit stereo sample converts to float32 with correct length."""
    raw = struct.pack("<4h", 0, 16384, -16384, 32767)
    result = _pcm_bytes_to_float32(raw)
    assert result.dtype == np.float32
    assert len(result) == 4


def test_pcm_bytes_to_float32_values():
    """Zero sample stays zero; max int16 maps to ~1.0."""
    raw = struct.pack("<h", 0)
    assert _pcm_bytes_to_float32(raw)[0] == pytest.approx(0.0)

    raw_max = struct.pack("<h", 32767)
    assert _pcm_bytes_to_float32(raw_max)[0] == pytest.approx(32767 / 32768.0)


def test_float32_to_pcm16_bytes_clipping():
    """Values outside [-1, 1] are clipped before conversion."""
    arr = np.array([2.0, -2.0], dtype=np.float32)
    result = _float32_to_pcm16_bytes(arr)
    samples = struct.unpack("<2h", result)
    assert samples[0] == 32767
    assert samples[1] == -32767


def test_pcm_round_trip():
    """float32 → PCM16 → float32 round-trip is lossless within int16 precision."""
    original = np.array([0.0, 0.5, -0.5, 0.999], dtype=np.float32)
    pcm = _float32_to_pcm16_bytes(original)
    recovered = _pcm_bytes_to_float32(pcm)
    # int16 quantisation step is 1/32767 ≈ 3.05e-5; use a 2× margin
    np.testing.assert_allclose(original, recovered, atol=2.0 / 32767)


# ---------------------------------------------------------------------------
# _write_wav
# ---------------------------------------------------------------------------

def test_write_wav_creates_valid_riff(tmp_path):
    """_write_wav writes a RIFF WAV file readable by the stdlib wave module."""
    path = str(tmp_path / "test.wav")
    audio = np.zeros(16000, dtype=np.float32)
    _write_wav(path, audio, sample_rate=16000)

    with wave.open(path, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        assert wf.getnframes() == 16000


def test_write_wav_non_zero_audio(tmp_path):
    """Non-zero audio is written correctly."""
    path = str(tmp_path / "sine.wav")
    t = np.linspace(0, 1, 8000, dtype=np.float32)
    audio = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
    _write_wav(path, audio, sample_rate=8000)

    with wave.open(path, "rb") as wf:
        assert wf.getnframes() == 8000


# ---------------------------------------------------------------------------
# _synthesize_speech — Piper not installed → returns None gracefully
# ---------------------------------------------------------------------------

def test_synthesize_speech_returns_none_when_piper_unavailable():
    """When Piper is not installed / models not present, TTS returns None."""
    result = _synthesize_speech("Sannu ranka ya dade.")
    # In CI, Piper models are not present — must not raise, must return None.
    assert result is None
