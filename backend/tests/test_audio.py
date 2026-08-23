"""Tests for the pure helper functions in routers.audio."""

import struct
import wave

import numpy as np
import pytest

import io

from routers.audio import (
    SPEAKER_MAP,
    _find_closest_waxal_sample,
    _float32_to_pcm16_bytes,
    _normalize_loudness,
    _pcm_bytes_to_float32,
    _synthesize_speech,
    _wav_bytes,
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
# _wav_bytes
# ---------------------------------------------------------------------------


def test_wav_bytes_creates_valid_riff():
    """_wav_bytes builds a RIFF WAV readable by the stdlib wave module."""
    audio = np.zeros(16000, dtype=np.float32)
    data = _wav_bytes(audio, sample_rate=16000)

    with wave.open(io.BytesIO(data), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        assert wf.getnframes() == 16000


def test_wav_bytes_non_zero_audio():
    """Non-zero audio is encoded correctly."""
    t = np.linspace(0, 1, 8000, dtype=np.float32)
    audio = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
    data = _wav_bytes(audio, sample_rate=8000)

    with wave.open(io.BytesIO(data), "rb") as wf:
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


@pytest.mark.anyio
async def test_transcribe_silence_returns_empty_without_running_whisper():
    """Silence must be energy-gated BEFORE Whisper runs: Whisper hallucinates
    text on non-speech input, and every hallucinated 'user turn' made the
    live voice session answer speech nobody said (self-talk loop). Must also
    never reach Cloudflare STT for the same reason."""
    from unittest.mock import patch
    from routers.audio import _transcribe

    silent_chunk = b"\x00\x00" * 32_000  # 2s of pure silence @16 kHz PCM-16
    with patch("routers.audio._get_whisper") as mock_whisper, \
         patch("routers.audio.cloudflare_stt_enabled", return_value=True), \
         patch("routers.audio.transcribe_via_cloudflare") as mock_cf:
        result = await _transcribe(silent_chunk)
    assert result == ""
    mock_whisper.assert_not_called()
    mock_cf.assert_not_called()


@pytest.mark.anyio
async def test_transcribe_prefers_cloudflare_when_enabled():
    """When Cloudflare STT is configured, it's tried first -- local Whisper
    must not be touched. This is the whole point of the offload: relieve
    local RAM/CPU pressure shared with Ollama/Piper."""
    from unittest.mock import AsyncMock, patch
    from routers.audio import _transcribe

    # A loud enough chunk to pass the energy gate.
    loud_chunk = (b"\x00\x7f" * 32_000)  # non-zero PCM-16 samples
    with patch("routers.audio._get_whisper") as mock_whisper, \
         patch("routers.audio.cloudflare_stt_enabled", return_value=True), \
         patch("routers.audio.transcribe_via_cloudflare", AsyncMock(return_value="sannu")):
        result = await _transcribe(loud_chunk)
    assert result == "sannu"
    mock_whisper.assert_not_called()


@pytest.mark.anyio
async def test_transcribe_falls_back_to_local_when_cloudflare_fails():
    """When Cloudflare STT is configured but returns None (any failure), the
    local faster-whisper path is used -- STT must never go silent just
    because the remote provider had a bad moment."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from routers.audio import _transcribe

    loud_chunk = (b"\x00\x7f" * 32_000)
    fake_segment = MagicMock(text="sannu")
    with patch("routers.audio._get_whisper") as mock_whisper, \
         patch("routers.audio.cloudflare_stt_enabled", return_value=True), \
         patch("routers.audio.transcribe_via_cloudflare", AsyncMock(return_value=None)):
        mock_whisper.return_value.transcribe.return_value = ([fake_segment], None)
        result = await _transcribe(loud_chunk)
    assert result == "sannu"
    mock_whisper.assert_called()


# ---------------------------------------------------------------------------
# _llm_respond — the live-voice fallback chain. Real bug found 2026-08-23:
# this chain never had a Groq step at all (unlike /api/chat and
# /api/document), so with Cerebras down every voice turn paid Ollama's full
# timeout before falling to Gemini's thin quota or the static fallback.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_llm_respond_falls_back_to_groq_when_cerebras_down(monkeypatch):
    from unittest.mock import AsyncMock, patch
    from routers.audio import _llm_respond

    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")

    mock_ollama_client = AsyncMock()
    mock_ollama_client.chat = AsyncMock(side_effect=Exception("ollama should not be called"))

    # _llm_respond imports `ollama` LOCALLY (function-scoped, not module-level
    # in routers.audio), so the patch target is the real ollama package
    # itself -- routers.audio.ollama.AsyncClient doesn't exist as an
    # attribute until the function actually runs its local import.
    with patch("routers.audio._llm_respond_groq", AsyncMock(return_value="sannu daga Groq")), \
         patch("ollama.AsyncClient", return_value=mock_ollama_client):
        result = await _llm_respond("Sannu", [])

    assert result == "sannu daga Groq"
    mock_ollama_client.chat.assert_not_called()


@pytest.mark.anyio
async def test_llm_respond_falls_back_to_ollama_when_cerebras_and_groq_down(monkeypatch):
    from unittest.mock import AsyncMock, patch
    from routers.audio import _llm_respond

    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    mock_ollama_client = AsyncMock()
    mock_ollama_client.chat = AsyncMock(return_value={"message": {"content": "sannu daga Ollama"}})

    with patch("ollama.AsyncClient", return_value=mock_ollama_client):
        result = await _llm_respond("Sannu", [])

    assert result == "sannu daga Ollama"
    mock_ollama_client.chat.assert_called()


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


# ---------------------------------------------------------------------------
# /api/live -- server-side echo backstop ("the app is listening to itself"
# bug, 2026-08-22). The client's half-duplex mic gate (App.tsx
# toggleLiveVoice) is timing-based and can leak a bit of the assistant's own
# TTS into the mic stream; the RMS/VAD gates can't tell that apart from real
# speech. So the client also sends an explicit
# {"type": "assistant_speaking", "value": true/false} control frame, and the
# server must drop any binary audio it receives while that flag is true --
# entirely independent of whatever the client-side gate did or didn't catch.
# ---------------------------------------------------------------------------


def test_live_endpoint_drops_audio_while_assistant_speaking():
    """Binary audio received between assistant_speaking:true and :false must
    never reach STT / be buffered -- only audio sent while unmuted should
    trigger a transcription."""
    import json as _json
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from main import app
    from routers.audio import CHUNK_SAMPLES

    muted_chunk = b"\x11\x11" * CHUNK_SAMPLES  # sent while assistant_speaking=true
    real_chunk = b"\x22\x22" * CHUNK_SAMPLES  # sent while unmuted

    seen_chunks = []

    async def fake_transcribe(pcm_bytes, sample_rate=16000):
        seen_chunks.append(bytes(pcm_bytes))
        return "sannu"

    with patch("routers.audio._transcribe", side_effect=fake_transcribe) as mock_transcribe, \
         patch("routers.audio._llm_respond", AsyncMock(return_value="Sannu, yaya dai?")), \
         patch("routers.audio._synthesize_speech", return_value=None):
        with TestClient(app).websocket_connect("/api/live") as ws:
            # Muted: flag the assistant as speaking, then send a full
            # 2-second chunk. If dropped correctly, this must not trigger
            # STT at all, so nothing should arrive on the socket yet.
            ws.send_text(_json.dumps({"type": "assistant_speaking", "value": True}))
            ws.send_bytes(muted_chunk)

            # Unmute, then send a second full chunk -- this one must go
            # through the whole STT -> LLM -> text-reply pipeline.
            ws.send_text(_json.dumps({"type": "assistant_speaking", "value": False}))
            ws.send_bytes(real_chunk)

            msg = _json.loads(ws.receive_text())
            assert msg["type"] == "user_transcript"
            assert msg["data"] == "sannu"

            reply = _json.loads(ws.receive_text())
            assert reply["type"] == "text"
            assert reply["data"] == "Sannu, yaya dai?"

    # STT must have run exactly once, and only on the chunk sent while
    # unmuted -- the muted chunk's bytes must never have been buffered/seen.
    mock_transcribe.assert_called_once()
    assert seen_chunks == [real_chunk]


def test_live_endpoint_clears_stale_partial_buffer_on_assistant_speaking_rising_edge():
    """Regression test for the real production bug behind 'still listening
    to itself' / 'wrong transcriptions of what was said before': a partial
    (<2s) pre-reply fragment left in pcm_buffer must NOT survive a mute
    cycle and get stitched onto the front of the next post-reply chunk.

    Sequence: some partial audio arrives (backlog recorded while the
    server was busy with the previous turn's STT/LLM/TTS, never reached
    the 2s threshold) -> assistant_speaking:true -> muted echo bytes
    (dropped) -> assistant_speaking:false -> a full fresh chunk. STT must
    see ONLY the fresh chunk, never the stale fragment prepended to it."""
    import json as _json
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from main import app
    from routers.audio import CHUNK_SAMPLES

    # Partial pre-reply backlog: well under the 2s threshold on its own.
    stale_fragment = b"\x33\x33" * (CHUNK_SAMPLES // 4)
    muted_chunk = b"\x11\x11" * CHUNK_SAMPLES  # leaked echo, sent while muted
    real_chunk = b"\x22\x22" * CHUNK_SAMPLES  # fresh post-reply speech

    seen_chunks = []

    async def fake_transcribe(pcm_bytes, sample_rate=16000):
        seen_chunks.append(bytes(pcm_bytes))
        return "sannu"

    with patch("routers.audio._transcribe", side_effect=fake_transcribe) as mock_transcribe, \
         patch("routers.audio._llm_respond", AsyncMock(return_value="Sannu, yaya dai?")), \
         patch("routers.audio._synthesize_speech", return_value=None):
        with TestClient(app).websocket_connect("/api/live") as ws:
            # Partial backlog arrives first -- below threshold, stays buffered.
            ws.send_bytes(stale_fragment)

            # Assistant starts speaking: this rising edge must discard the
            # stale fragment above.
            ws.send_text(_json.dumps({"type": "assistant_speaking", "value": True}))
            ws.send_bytes(muted_chunk)

            ws.send_text(_json.dumps({"type": "assistant_speaking", "value": False}))
            ws.send_bytes(real_chunk)

            msg = _json.loads(ws.receive_text())
            assert msg["type"] == "user_transcript"
            assert msg["data"] == "sannu"

    # STT must have run exactly once, on exactly real_chunk -- NOT on
    # stale_fragment + real_chunk (which is what the pre-fix code produced).
    mock_transcribe.assert_called_once()
    assert seen_chunks == [real_chunk]


def test_live_endpoint_assistant_speaking_flag_has_a_safety_timeout(monkeypatch):
    """If the client never sends assistant_speaking:false (crash, dropped
    frame, backgrounded tab), the server must not stay deaf forever."""
    import json as _json
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from main import app
    from routers import audio as audio_router
    from routers.audio import CHUNK_SAMPLES

    # Force the safety valve to trip almost immediately instead of waiting
    # the real 15s, so the test stays fast.
    monkeypatch.setattr(audio_router, "_ASSISTANT_SPEAKING_MAX_S", 0.0)

    chunk = b"\x22\x22" * CHUNK_SAMPLES

    with patch("routers.audio._transcribe", AsyncMock(return_value="sannu")) as mock_transcribe, \
         patch("routers.audio._llm_respond", AsyncMock(return_value="Sannu, yaya dai?")), \
         patch("routers.audio._synthesize_speech", return_value=None):
        with TestClient(app).websocket_connect("/api/live") as ws:
            ws.send_text(_json.dumps({"type": "assistant_speaking", "value": True}))
            # With max age forced to 0.0, this chunk is already "stale" by
            # the time it's checked, so it must be let through rather than
            # dropped forever.
            ws.send_bytes(chunk)

            msg = _json.loads(ws.receive_text())
            assert msg["type"] == "user_transcript"

    mock_transcribe.assert_called_once()

