"""Tests for the pure helper functions in routers.audio."""

import struct
import wave

import numpy as np
import pytest

from routers.audio import (
    SPEAKER_MAP,
    _find_closest_waxal_sample,
    _float32_to_pcm16_bytes,
    _normalize_loudness,
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
# _normalize_loudness — every served TTS output is unified to the
# landing-page sample loudness (RMS ≈ -14 dBFS, peak ≤ -0.5 dBFS) so replies
# are consistently loud and never clip.
# ---------------------------------------------------------------------------


def _rms_dbfs(pcm: bytes) -> float:
    audio = _pcm_bytes_to_float32(pcm)
    rms = float(np.sqrt(np.mean(audio ** 2)))
    return 20 * np.log10(rms)


def _peak(pcm: bytes) -> float:
    return float(np.max(np.abs(_pcm_bytes_to_float32(pcm))))


def test_normalize_quiet_audio_boosted_to_target():
    """A quiet sine (amp 0.05, ~-29 dBFS) is amplified UP to ~-14 dBFS RMS."""
    t = np.linspace(0, 1, 24000, endpoint=False, dtype=np.float32)
    quiet = (np.sin(2 * np.pi * 220 * t) * 0.05).astype(np.float32)
    pcm = _float32_to_pcm16_bytes(quiet)

    out = _normalize_loudness(pcm)
    # Within ~1.5 dB of the -14 dBFS target.
    assert abs(_rms_dbfs(out) - (-14.0)) <= 1.5


def test_normalize_hot_audio_never_clips():
    """A full-scale sine (amp 1.0) ends peak-limited at/below the ceiling."""
    t = np.linspace(0, 1, 24000, endpoint=False, dtype=np.float32)
    hot = np.sin(2 * np.pi * 220 * t).astype(np.float32)
    pcm = _float32_to_pcm16_bytes(hot)

    out = _normalize_loudness(pcm)
    # ceiling is -0.5 dBFS ≈ 0.944 linear; allow a hair of int16 rounding.
    assert _peak(out) <= 0.945


def test_normalize_silence_unchanged():
    """All-zero PCM is returned unchanged — no divide-by-zero, no NaN/crash."""
    silence = _float32_to_pcm16_bytes(np.zeros(24000, dtype=np.float32))
    out = _normalize_loudness(silence)
    assert out == silence
    assert not np.any(np.isnan(_pcm_bytes_to_float32(out)))


def test_normalize_preserves_sample_count():
    """Round-trip preserves the number of PCM samples (same byte length)."""
    t = np.linspace(0, 1, 18000, endpoint=False, dtype=np.float32)
    audio = (np.sin(2 * np.pi * 300 * t) * 0.3).astype(np.float32)
    pcm = _float32_to_pcm16_bytes(audio)
    out = _normalize_loudness(pcm)
    assert len(out) == len(pcm)


# ---------------------------------------------------------------------------
# _synthesize_speech — Piper not installed → returns None gracefully
# ---------------------------------------------------------------------------


def test_transcribe_silence_returns_empty_without_running_whisper():
    """Silence must be energy-gated BEFORE Whisper runs: Whisper hallucinates
    text on non-speech input, and every hallucinated 'user turn' made the
    live voice session answer speech nobody said (self-talk loop)."""
    from unittest.mock import patch
    from routers.audio import _transcribe

    silent_chunk = b"\x00\x00" * 32_000  # 2s of pure silence @16 kHz PCM-16
    with patch("routers.audio._get_whisper") as mock_whisper:
        result = _transcribe(silent_chunk)
    assert result == ""
    mock_whisper.assert_not_called()


def test_synthesize_speech_returns_none_when_piper_unavailable():
    """When Piper and VITS are not installed / models not present, TTS returns None."""
    from unittest.mock import patch
    with patch("routers.audio._get_vits", return_value=None), \
         patch("routers.audio._get_piper", return_value=None), \
         patch("routers.audio._find_closest_waxal_sample", return_value=None):
        result = _synthesize_speech("Sannu ranka ya dade.")
        assert result is None


# ---------------------------------------------------------------------------
# SPEAKER_MAP — frontend speaker_id -> WAXAL numeric id must match the
# actual gender-alternating scheme in waxal_hausa/metadata_processed.jsonl
# (1=F1, 2=M1, 3=F2, 4=M2, 5=F3, 6=M3, 7=F4, 8=M4), not a grouped
# 1-4=female/5-8=male scheme. Getting this wrong serves a wrong-gender
# recording for the requested voice.
# ---------------------------------------------------------------------------


def test_speaker_map_namiji_ids_are_even_waxal_ids():
    """Frontend 0..3 (Namiji/Male) must map to the even WAXAL ids (M1..M4)."""
    assert [SPEAKER_MAP[i] for i in (0, 1, 2, 3)] == ["2", "4", "6", "8"]


def test_speaker_map_mace_ids_are_odd_waxal_ids():
    """Frontend 4..7 (Mace/Female) must map to the odd WAXAL ids (F1..F4)."""
    assert [SPEAKER_MAP[i] for i in (4, 5, 6, 7)] == ["1", "3", "5", "7"]


# ---------------------------------------------------------------------------
# _find_closest_waxal_sample — must not return a low-relevance match.
# Exercised against the real repo metadata: a match is a stand-in for a
# verbatim human recording, so a low-overlap "closest" candidate must be
# rejected rather than silently played back saying the wrong words.
# ---------------------------------------------------------------------------


def test_waxal_match_returns_none_for_unrelated_text():
    """Text with no real counterpart in the corpus must return None, not
    the least-bad (but still wrong) candidate."""
    result = _find_closest_waxal_sample(
        "Fasahar sadarwa ta zamani na taimaka wa al'ummar Hausawa wajen adana al'adunmu.",
        "5",
    )
    assert result is None


def test_waxal_match_returns_file_for_near_exact_text():
    """Text pulled verbatim from a real corpus entry should still match."""
    result = _find_closest_waxal_sample("Musulmi na zuwa Masallaci ran juma'a", "5")
    assert result is not None

