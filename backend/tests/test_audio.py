"""Tests for the pure helper functions in routers.audio."""

import os
import struct
import threading
import time
import wave
from pathlib import Path

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
    """Text pulled verbatim from a real corpus entry should still match.

    Depends on the real WAXAL sample corpus (waxal_hausa/metadata*.jsonl at
    the repo root) genuinely being present on disk -- a large data
    directory, deliberately not committed to git, so this can never pass in
    a clean CI checkout no matter what gets pip-installed. Skips honestly
    there instead of failing red for a reason no dependency fix can
    address; still real, enforced coverage on any machine (a contributor's,
    the production deploy) that actually has the corpus."""
    metadata_dir = Path(__file__).resolve().parent.parent.parent / "waxal_hausa"
    if not any((metadata_dir / name).exists() for name in ("metadata_processed.jsonl", "metadata.jsonl")):
        pytest.skip("WAXAL corpus (waxal_hausa/metadata*.jsonl) not present in this environment")
    result = _find_closest_waxal_sample("Musulmi na zuwa Masallaci ran juma'a", "5")
    assert result is not None


# ---------------------------------------------------------------------------
# Regression: waxal metadata caching (Medium finding — the metadata file was
# re-parsed from scratch on every single TTS call).
# ---------------------------------------------------------------------------
def test_waxal_metadata_cache_reuses_parse_when_mtime_unchanged(tmp_path):
    from routers import audio

    path = tmp_path / "metadata.jsonl"
    path.write_text('{"speaker_id": "1", "text": "hello"}\n', encoding="utf-8")

    audio._waxal_metadata_cache.update({"path": None, "mtime": None, "entries": None})
    first = audio._load_waxal_metadata_cached(path)
    second = audio._load_waxal_metadata_cached(path)
    # Same list object back -- proves the second call hit the cache instead
    # of re-reading and re-parsing the file.
    assert first is second
    assert len(first) == 1


def test_waxal_metadata_cache_invalidates_on_mtime_change(tmp_path):
    from routers import audio

    path = tmp_path / "metadata.jsonl"
    path.write_text('{"speaker_id": "1", "text": "hello"}\n', encoding="utf-8")

    audio._waxal_metadata_cache.update({"path": None, "mtime": None, "entries": None})
    first = audio._load_waxal_metadata_cached(path)
    assert len(first) == 1

    path.write_text(
        '{"speaker_id": "1", "text": "hello"}\n{"speaker_id": "2", "text": "world"}\n',
        encoding="utf-8",
    )
    # Force a distinct mtime even on filesystems with coarse mtime resolution.
    new_time = path.stat().st_mtime + 1
    os.utime(path, (new_time, new_time))

    second = audio._load_waxal_metadata_cached(path)
    assert len(second) == 2
    assert second is not first


# ---------------------------------------------------------------------------
# Regression: Piper model download had no concurrency lock -- two
# simultaneous first-TTS-requests after a fresh deploy could both write to
# the same model file path at once. Verify _get_piper's download path is now
# serialized (never two threads inside _download_piper_assets at once).
# ---------------------------------------------------------------------------
def test_get_piper_serializes_concurrent_download_attempts(monkeypatch):
    from routers import audio

    monkeypatch.setattr(audio, "_piper_voice", None)
    state = {"active": 0, "max_active": 0}
    state_lock = threading.Lock()

    def fake_download(model_path, config_path):
        with state_lock:
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
        time.sleep(0.05)  # widen the window so a race would actually show up
        with state_lock:
            state["active"] -= 1

    monkeypatch.setattr(audio, "_download_piper_assets", fake_download)

    threads = [threading.Thread(target=audio._get_piper) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert state["max_active"] == 1


# ---------------------------------------------------------------------------
# Regression: piper-tts 1.3+ dropped voice.stream_to_file() (the pre-1.3 API)
# in favor of voice.synthesize_wav(text, wave.Wave_write). requirements.txt
# pins ~=1.2.0 (what the Linux production container resolves), but that pin
# is literally uninstallable on Windows (its piper-phonemize dependency
# never shipped Windows wheels), so local dev lands on 1.4.x -- and hitting
# the removed stream_to_file crashed every local TTS call with
# "'PiperVoice' object has no attribute 'stream_to_file'". Verify
# _piper_write_wav handles both API shapes correctly, independent of
# whichever piper-tts version actually happens to be installed here.
# ---------------------------------------------------------------------------
def test_piper_write_wav_uses_old_stream_to_file_api_when_present():
    from contextlib import contextmanager

    from routers import audio

    calls = []

    class FakeOldVoice:
        @contextmanager
        def stream_to_file(self, text, wav_file):
            calls.append((text, wav_file))
            yield

    buf = io.BytesIO()
    audio._piper_write_wav(FakeOldVoice(), "sannu", buf)
    assert calls == [("sannu", buf)]


def test_piper_write_wav_falls_back_to_new_synthesize_wav_api():
    from routers import audio

    calls = []

    class FakeNewVoice:
        def synthesize_wav(self, text, wav_file):
            calls.append(text)
            # Write a minimal valid frame so wave.open's context manager
            # exit (which finalizes the header) doesn't blow up.
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(b"\x00\x00")

    buf = io.BytesIO()
    audio._piper_write_wav(FakeNewVoice(), "sannu", buf)
    assert calls == ["sannu"]
    # A real WAV header was written (RIFF/WAVE magic bytes), proving this
    # path produces a file the rest of _synthesize_speech_raw can parse
    # (it seeks past byte 44 and reads raw PCM after).
    assert buf.getvalue()[:4] == b"RIFF"
    assert buf.getvalue()[8:12] == b"WAVE"


# ---------------------------------------------------------------------------
# /api/live -- VAD-driven turn detection helpers.
#
# live_endpoint no longer chunks on a fixed ~2s timer; it feeds every
# incoming frame through a Silero VAD stream (services/vad_service.py) and
# only calls STT once sustained trailing silence confirms the user is done
# talking (see routers.audio's _TurnState / VAD_* constants). These tests
# replace the VAD stream with a deterministic fake that returns a scripted
# sequence of speech probabilities, so turn boundaries are exact and the
# tests don't depend on real audio actually reading as "speech" to Silero.
# ---------------------------------------------------------------------------

from routers.audio import FRAME_MS, VAD_MIN_SPEECH_MS, VAD_PRE_ROLL_MS, VAD_TRAILING_SILENCE_MS, _FRAME_BYTES

# Number of consecutive frames needed to clear each threshold, derived from
# the real tuning constants rather than hardcoded, so these tests track the
# production constants automatically if they're ever retuned.
_SPEECH_FRAMES = int(VAD_MIN_SPEECH_MS // FRAME_MS) + 1
_SILENCE_FRAMES = int(VAD_TRAILING_SILENCE_MS // FRAME_MS) + 1


class _ScriptedFakeVAD:
    """Deterministic stand-in for services.vad_service.SileroVAD:
    process_frame() returns probabilities from a fixed script (looping the
    last value once exhausted) instead of running real inference, so tests
    can drive the live_endpoint turn-detection state machine to an exact,
    reproducible boundary."""

    def __init__(self, probs):
        self._probs = list(probs)
        self._i = 0
        self.reset_calls = 0
        self.frames_seen = []

    def process_frame(self, frame):
        self.frames_seen.append(bytes(np.asarray(frame, dtype=np.float32).tobytes()))
        prob = self._probs[min(self._i, len(self._probs) - 1)]
        self._i += 1
        return prob

    def reset_states(self):
        self.reset_calls += 1


def _frame(byte: bytes) -> bytes:
    """One full 512-sample (1024-byte) PCM-16 frame filled with `byte`."""
    return byte * (_FRAME_BYTES // len(byte))


def _speech_then_silence_script(n_speech=None, n_silence=None):
    """A probability script that clears VAD_SPEECH_THRESHOLD for n_speech
    frames (enough to pass VAD_MIN_SPEECH_MS) then drops below
    VAD_SILENCE_THRESHOLD for n_silence frames (enough to clear
    VAD_TRAILING_SILENCE_MS and complete the turn)."""
    n_speech = n_speech if n_speech is not None else _SPEECH_FRAMES
    n_silence = n_silence if n_silence is not None else _SILENCE_FRAMES
    return [0.9] * n_speech + [0.05] * n_silence


# ---------------------------------------------------------------------------
# Core VAD turn-detection behavior
# ---------------------------------------------------------------------------


def test_live_endpoint_completes_turn_on_trailing_silence():
    """A speech run followed by enough trailing silence must trigger exactly
    one STT call, with the accumulated speech bytes (not the trailing
    silence) handed to it."""
    import json as _json
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from main import app

    fake_vad = _ScriptedFakeVAD(_speech_then_silence_script())
    speech_bytes = _frame(b"\x22\x22") * _SPEECH_FRAMES
    silence_bytes = _frame(b"\x00\x00") * _SILENCE_FRAMES

    seen_chunks = []

    async def fake_transcribe(pcm_bytes, sample_rate=16000):
        seen_chunks.append(bytes(pcm_bytes))
        return "sannu"

    with patch("routers.audio.new_vad_stream", return_value=fake_vad), \
         patch("routers.audio._transcribe", side_effect=fake_transcribe) as mock_transcribe, \
         patch("routers.audio._llm_respond", AsyncMock(return_value="Sannu, yaya dai?")), \
         patch("routers.audio._synthesize_speech", return_value=None):
        with TestClient(app).websocket_connect("/api/live") as ws:
            ws.send_bytes(speech_bytes + silence_bytes)

            msg = _json.loads(ws.receive_text())
            assert msg["type"] == "user_transcript"
            assert msg["data"] == "sannu"

            reply = _json.loads(ws.receive_text())
            assert reply["type"] == "text"
            assert reply["data"] == "Sannu, yaya dai?"

    mock_transcribe.assert_called_once()
    # The trailing (confirmed-silent) tail is trimmed before STT -- only the
    # speech portion should have been handed over.
    assert seen_chunks == [speech_bytes]


def test_live_endpoint_does_not_transcribe_before_trailing_silence_completes():
    """Mid-utterance: speech followed by silence that's SHORT of
    VAD_TRAILING_SILENCE_MS must not trigger STT yet -- a natural pause
    (breath, searching for a word) must not fragment one sentence into
    multiple turns."""
    import asyncio
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from main import app

    short_silence_frames = max(1, _SILENCE_FRAMES - 5)
    fake_vad = _ScriptedFakeVAD(_speech_then_silence_script(n_silence=short_silence_frames))
    speech_bytes = _frame(b"\x22\x22") * _SPEECH_FRAMES
    silence_bytes = _frame(b"\x00\x00") * short_silence_frames

    with patch("routers.audio.new_vad_stream", return_value=fake_vad), \
         patch("routers.audio._transcribe", AsyncMock(return_value="sannu")) as mock_transcribe, \
         patch("routers.audio._llm_respond", AsyncMock(return_value="Sannu")), \
         patch("routers.audio._synthesize_speech", return_value=None):
        with TestClient(app).websocket_connect("/api/live") as ws:
            ws.send_bytes(speech_bytes + silence_bytes)
            # Nothing should arrive -- give the (synchronous, in-process)
            # handling a moment, then assert STT was never reached.
            import time as _time
            _time.sleep(0.1)

    mock_transcribe.assert_not_called()


def test_live_endpoint_discards_short_noise_blip_without_transcribing():
    """A speech run shorter than VAD_MIN_SPEECH_MS (a cough, a mic bump)
    followed by trailing silence must be discarded, not sent to STT."""
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from main import app

    n_speech = max(1, _SPEECH_FRAMES - 5)  # short of the minimum
    fake_vad = _ScriptedFakeVAD(_speech_then_silence_script(n_speech=n_speech))
    blip_bytes = _frame(b"\x22\x22") * n_speech
    silence_bytes = _frame(b"\x00\x00") * _SILENCE_FRAMES

    with patch("routers.audio.new_vad_stream", return_value=fake_vad), \
         patch("routers.audio._transcribe", AsyncMock(return_value="sannu")) as mock_transcribe, \
         patch("routers.audio._llm_respond", AsyncMock(return_value="Sannu")), \
         patch("routers.audio._synthesize_speech", return_value=None):
        with TestClient(app).websocket_connect("/api/live") as ws:
            ws.send_bytes(blip_bytes + silence_bytes)
            import time as _time
            _time.sleep(0.1)

    mock_transcribe.assert_not_called()


def test_live_endpoint_forced_cut_at_max_turn_length(monkeypatch):
    """Continuous speech that never pauses must still eventually reach STT
    -- the MAX_TURN_SECONDS safety valve forces a cut rather than buffering
    forever."""
    import json as _json
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from main import app
    from routers import audio as audio_router

    # Force the safety valve to trip almost immediately instead of the real
    # ~25s, so the test stays fast. Exactly 2 frames: frame 1 triggers the
    # turn (the "not triggered yet" branch never checks the forced-cut
    # clock), frame 2 is the first check once triggered -- with the clock
    # forced to 0.0 that check fires immediately. Sending more continuous-
    # speech frames after that would just trip the (now hair-trigger) forced
    # cut repeatedly and call _handle_turn more than once, which isn't what
    # this test is verifying.
    fake_vad = _ScriptedFakeVAD([0.9] * 2)
    speech_bytes = _frame(b"\x22\x22") * 2
    monkeypatch.setattr(audio_router, "MAX_TURN_SECONDS", 0.0)

    with patch("routers.audio.new_vad_stream", return_value=fake_vad), \
         patch("routers.audio._transcribe", AsyncMock(return_value="sannu")) as mock_transcribe, \
         patch("routers.audio._llm_respond", AsyncMock(return_value="Sannu")), \
         patch("routers.audio._synthesize_speech", return_value=None):
        with TestClient(app).websocket_connect("/api/live") as ws:
            ws.send_bytes(speech_bytes)
            msg = _json.loads(ws.receive_text())
            assert msg["type"] == "user_transcript"

    mock_transcribe.assert_called_once()


def test_live_endpoint_does_not_splice_stale_pre_roll_into_rapid_retrigger(monkeypatch):
    """Regression test for a real bug found in code review: pre_roll is only
    refilled while NOT triggered, so if a turn ends and speech resumes with
    ~zero gap (most realistically: continuous talking past MAX_TURN_SECONDS,
    where reset_turn() deliberately preserves pre_roll across the boundary),
    the next turn would splice pre_roll frozen from BEFORE the turn that
    just ended onto its front -- stale audio corrupting a fresh transcript.
    pre_roll must be cleared the moment it's consumed at trigger time."""
    import json as _json
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from main import app
    from routers import audio as audio_router

    pre_roll_frames = int(VAD_PRE_ROLL_MS // FRAME_MS) + 2
    stale_marker = _frame(b"\xAA\xAA") * pre_roll_frames  # fills pre_roll before turn 1
    # Turn 1 needs exactly 2 speech frames once triggered: frame 1 triggers
    # (the "not triggered yet" branch never checks forced_cut), frame 2 is
    # the first check once triggered -- with MAX_TURN_SECONDS forced to 0.0
    # that check fires immediately, force-cutting turn 1 right away.
    turn1_speech = _frame(b"\x33\x33") * 2
    turn2_speech = _frame(b"\x22\x22") * 3  # continuous speech straight after the forced cut

    # Script: enough low-probability frames to fill pre_roll with the stale
    # marker, then continuous high-probability speech for both turn 1 (which
    # gets force-cut almost immediately) and turn 2 (retriggering with no
    # silence gap in between).
    fake_vad = _ScriptedFakeVAD([0.05] * pre_roll_frames + [0.9] * 10)
    monkeypatch.setattr(audio_router, "MAX_TURN_SECONDS", 0.0)

    seen_chunks = []

    async def fake_transcribe(pcm_bytes, sample_rate=16000):
        seen_chunks.append(bytes(pcm_bytes))
        return "sannu"

    with patch("routers.audio.new_vad_stream", return_value=fake_vad), \
         patch("routers.audio._transcribe", side_effect=fake_transcribe) as mock_transcribe, \
         patch("routers.audio._llm_respond", AsyncMock(return_value="Sannu")), \
         patch("routers.audio._synthesize_speech", return_value=None):
        with TestClient(app).websocket_connect("/api/live") as ws:
            ws.send_bytes(stale_marker)  # fills pre_roll, no turn yet
            ws.send_bytes(turn1_speech)  # triggers turn 1, then force-cuts on frame 2's check
            msg1 = _json.loads(ws.receive_text())
            assert msg1["type"] == "user_transcript"
            reply1 = _json.loads(ws.receive_text())
            assert reply1["type"] == "text"
            ws.send_bytes(turn2_speech)  # turn 2: continuous speech, zero silence gap since turn 1 ended
            msg2 = _json.loads(ws.receive_text())
            assert msg2["type"] == "user_transcript"

    assert mock_transcribe.call_count == 2
    turn2_bytes = seen_chunks[1]
    assert b"\xAA\xAA" not in turn2_bytes, (
        "turn 2 must not contain the stale pre_roll marker recorded before turn 1 started"
    )


def test_live_endpoint_falls_back_to_fixed_chunking_when_vad_unavailable():
    """If the Silero VAD model fails to load (new_vad_stream() returns
    None), the connection must degrade to the old fixed ~2s chunking rather
    than going deaf -- a real, working fallback, not a crash."""
    import json as _json
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from main import app
    from routers.audio import CHUNK_SAMPLES

    chunk = b"\x22\x22" * CHUNK_SAMPLES

    with patch("routers.audio.new_vad_stream", return_value=None), \
         patch("routers.audio._transcribe", AsyncMock(return_value="sannu")) as mock_transcribe, \
         patch("routers.audio._llm_respond", AsyncMock(return_value="Sannu")), \
         patch("routers.audio._synthesize_speech", return_value=None):
        with TestClient(app).websocket_connect("/api/live") as ws:
            ws.send_bytes(chunk)
            msg = _json.loads(ws.receive_text())
            assert msg["type"] == "user_transcript"

    mock_transcribe.assert_called_once()


def test_live_endpoint_rejects_wrong_or_missing_ticket_when_configured(monkeypatch):
    """Regression test for a real gap found in a 2026-08-23 security review:
    /api/live had no API_KEY enforcement at all, unlike every other product
    endpoint. Since a Security(APIKeyHeader) router-level dependency doesn't
    work on a WebSocket route (confirmed empirically -- FastAPI can't supply
    the Request object it needs for a WS handshake), the check is a plain
    query-param comparison done manually inside live_endpoint before
    ws.accept(). A follow-up review found the first fix (a raw ?api_key=
    query param) leaked the standing secret into every access log -- this
    now checks the ticket-exchange replacement instead (auth.
    consume_live_ticket): no ticket, an unknown ticket, and an already-used
    ticket must all be rejected the same as a wrong key was before."""
    import auth
    from starlette.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect as ClientWSDisconnect

    from main import app

    monkeypatch.setattr(auth, "_CONFIGURED_KEY", "the-real-secret")

    # No ticket at all.
    with pytest.raises(ClientWSDisconnect):
        with TestClient(app).websocket_connect("/api/live"):
            pass

    # Unknown/forged ticket.
    with pytest.raises(ClientWSDisconnect):
        with TestClient(app).websocket_connect("/api/live?ticket=not-a-real-ticket"):
            pass

    # A real ticket, but already spent (consume_live_ticket is single-use).
    ticket = auth.issue_live_ticket()
    assert auth.consume_live_ticket(ticket) is True
    with pytest.raises(ClientWSDisconnect):
        with TestClient(app).websocket_connect(f"/api/live?ticket={ticket}"):
            pass


def test_live_endpoint_allows_connection_with_valid_ticket(monkeypatch):
    """The other half of the regression test above: a freshly issued ticket
    must still connect normally, not just reject bad ones."""
    import json as _json
    from unittest.mock import AsyncMock, patch

    import auth
    from starlette.testclient import TestClient

    from main import app
    from routers.audio import CHUNK_SAMPLES

    monkeypatch.setattr(auth, "_CONFIGURED_KEY", "the-real-secret")
    ticket = auth.issue_live_ticket()
    chunk = b"\x22\x22" * CHUNK_SAMPLES

    with patch("routers.audio.new_vad_stream", return_value=None), \
         patch("routers.audio._transcribe", AsyncMock(return_value="sannu")), \
         patch("routers.audio._llm_respond", AsyncMock(return_value="Sannu")), \
         patch("routers.audio._synthesize_speech", return_value=None):
        with TestClient(app).websocket_connect(f"/api/live?ticket={ticket}") as ws:
            ws.send_bytes(chunk)
            msg = _json.loads(ws.receive_text())
            assert msg["type"] == "user_transcript"


def test_live_endpoint_open_without_ticket_when_no_api_key_configured():
    """No API_KEY configured (the public default) must stay fully open with
    NO ticket required at all -- the ticket exchange must not add an extra
    round trip to every live-voice session in the common case where there's
    no secret to protect."""
    import json as _json
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from main import app
    from routers.audio import CHUNK_SAMPLES

    chunk = b"\x22\x22" * CHUNK_SAMPLES
    with patch("routers.audio.new_vad_stream", return_value=None), \
         patch("routers.audio._transcribe", AsyncMock(return_value="sannu")), \
         patch("routers.audio._llm_respond", AsyncMock(return_value="Sannu")), \
         patch("routers.audio._synthesize_speech", return_value=None):
        with TestClient(app).websocket_connect("/api/live") as ws:
            ws.send_bytes(chunk)
            msg = _json.loads(ws.receive_text())
            assert msg["type"] == "user_transcript"


@pytest.mark.anyio
async def test_live_ticket_endpoint_requires_api_key_when_configured(client, monkeypatch):
    """POST /api/live/ticket is a normal header-authenticated HTTP call
    (unlike the WebSocket itself) -- verify_api_key gates it the same as
    every other endpoint."""
    import auth

    monkeypatch.setattr(auth, "_CONFIGURED_KEY", "the-real-secret")

    resp = await client.post("/api/live/ticket")
    assert resp.status_code == 401

    resp2 = await client.post("/api/live/ticket", headers={"X-API-Key": "the-real-secret"})
    assert resp2.status_code == 200
    assert "ticket" in resp2.json()


def test_live_endpoint_rejects_beyond_global_connection_ceiling(monkeypatch):
    """Regression test for a gap the 2026-08-23 follow-up security-
    architecture review found: the per-IP connection cap alone doesn't stop
    a DISTRIBUTED attacker -- opening a couple of connections from each of
    many source IPs sums to an unbounded total even though no single IP
    ever trips the per-IP limit. A process-wide ceiling
    (_MAX_LIVE_CONNECTIONS_TOTAL) must reject a new connection once the
    total is at capacity, regardless of which IP it comes from."""
    from unittest.mock import patch

    import routers.audio as audio_module
    from starlette.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect as ClientWSDisconnect

    from main import app

    monkeypatch.setattr(audio_module, "_MAX_LIVE_CONNECTIONS_TOTAL", 1)
    monkeypatch.setattr(audio_module, "_MAX_LIVE_CONNECTIONS_PER_IP", 99)
    monkeypatch.setattr(audio_module, "_live_connections_by_ip", {})
    monkeypatch.setattr(audio_module, "_live_connections_total", 0)

    with patch("routers.audio.new_vad_stream", return_value=None):
        with TestClient(app).websocket_connect("/api/live") as first:
            # First connection succeeds and holds the one available slot.
            assert audio_module._live_connections_total == 1
            with pytest.raises(ClientWSDisconnect):
                with TestClient(app).websocket_connect("/api/live"):
                    pass
        # After the first connection closes, the slot is freed again.
        assert audio_module._live_connections_total == 0


# ---------------------------------------------------------------------------
# /api/live -- server-side echo backstop ("the app is listening to itself"
# bug, 2026-08-22). The client's half-duplex mic gate (App.tsx
# toggleLiveVoice) is timing-based and can leak a bit of the assistant's own
# TTS into the mic stream; VAD alone can't tell that apart from real speech.
# So the client also sends an explicit
# {"type": "assistant_speaking", "value": true/false} control frame, and the
# server must drop any binary audio it receives while that flag is true --
# entirely independent of whatever the client-side gate did or didn't catch.
# ---------------------------------------------------------------------------


def test_live_endpoint_drops_audio_while_assistant_speaking():
    """Binary audio received between assistant_speaking:true and :false must
    never reach the VAD / be buffered -- only audio sent while unmuted
    should trigger a transcription."""
    import json as _json
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from main import app

    fake_vad = _ScriptedFakeVAD(_speech_then_silence_script())
    muted_bytes = _frame(b"\x11\x11") * (_SPEECH_FRAMES + _SILENCE_FRAMES)  # sent while assistant_speaking=true
    real_bytes = _frame(b"\x22\x22") * _SPEECH_FRAMES + _frame(b"\x00\x00") * _SILENCE_FRAMES  # sent while unmuted

    seen_chunks = []

    async def fake_transcribe(pcm_bytes, sample_rate=16000):
        seen_chunks.append(bytes(pcm_bytes))
        return "sannu"

    with patch("routers.audio.new_vad_stream", return_value=fake_vad), \
         patch("routers.audio._transcribe", side_effect=fake_transcribe) as mock_transcribe, \
         patch("routers.audio._llm_respond", AsyncMock(return_value="Sannu, yaya dai?")), \
         patch("routers.audio._synthesize_speech", return_value=None):
        with TestClient(app).websocket_connect("/api/live") as ws:
            # Muted: flag the assistant as speaking, then send audio that
            # WOULD complete a full turn if it reached the VAD. If dropped
            # correctly, this must never even reach process_frame().
            ws.send_text(_json.dumps({"type": "assistant_speaking", "value": True}))
            ws.send_bytes(muted_bytes)

            # Unmute, then send a real utterance -- this one must go through
            # the whole STT -> LLM -> text-reply pipeline.
            ws.send_text(_json.dumps({"type": "assistant_speaking", "value": False}))
            ws.send_bytes(real_bytes)

            msg = _json.loads(ws.receive_text())
            assert msg["type"] == "user_transcript"
            assert msg["data"] == "sannu"

            reply = _json.loads(ws.receive_text())
            assert reply["type"] == "text"
            assert reply["data"] == "Sannu, yaya dai?"

    # STT must have run exactly once, and only on the utterance sent while
    # unmuted -- the muted bytes must never have reached the VAD at all.
    mock_transcribe.assert_called_once()
    assert len(fake_vad.frames_seen) == _SPEECH_FRAMES + _SILENCE_FRAMES
    assert seen_chunks == [_frame(b"\x22\x22") * _SPEECH_FRAMES]


def test_live_endpoint_clears_stale_partial_buffer_on_assistant_speaking_rising_edge():
    """Regression test for the real production bug behind 'still listening
    to itself' / 'wrong transcriptions of what was said before': a partial,
    not-yet-triggered fragment (sub-frame remainder, pre-roll lookback, or a
    part-way-through-a-turn buffer) must NOT survive a mute cycle and get
    stitched onto the front of the next post-reply utterance.

    Sequence: some partial pre-speech audio arrives (backlog recorded while
    the server was busy with the previous turn's STT/LLM/TTS) ->
    assistant_speaking:true (must fully reset turn state AND the VAD's own
    recurrent state) -> muted echo bytes (dropped) ->
    assistant_speaking:false -> a full fresh utterance. STT must see ONLY
    the fresh utterance, never the stale fragment prepended to it."""
    import json as _json
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from main import app

    # Partial pre-reply backlog: a few frames of speech-probability audio
    # that never got far enough to trigger a turn on its own.
    fake_vad = _ScriptedFakeVAD([0.9, 0.9] + _speech_then_silence_script())
    stale_fragment = _frame(b"\x33\x33") * 2  # backlog, sent before muting
    muted_bytes = _frame(b"\x11\x11") * (_SPEECH_FRAMES + _SILENCE_FRAMES)  # leaked echo, sent while muted
    real_bytes = _frame(b"\x22\x22") * _SPEECH_FRAMES + _frame(b"\x00\x00") * _SILENCE_FRAMES  # fresh post-reply speech

    seen_chunks = []

    async def fake_transcribe(pcm_bytes, sample_rate=16000):
        seen_chunks.append(bytes(pcm_bytes))
        return "sannu"

    with patch("routers.audio.new_vad_stream", return_value=fake_vad), \
         patch("routers.audio._transcribe", side_effect=fake_transcribe) as mock_transcribe, \
         patch("routers.audio._llm_respond", AsyncMock(return_value="Sannu, yaya dai?")), \
         patch("routers.audio._synthesize_speech", return_value=None):
        with TestClient(app).websocket_connect("/api/live") as ws:
            # Partial backlog arrives first -- read as speech-probability
            # but far too short to complete a turn, stays buffered/triggered.
            ws.send_bytes(stale_fragment)

            # Assistant starts speaking: this rising edge must discard the
            # stale fragment above AND reset the VAD's recurrent state.
            ws.send_text(_json.dumps({"type": "assistant_speaking", "value": True}))
            ws.send_bytes(muted_bytes)

            ws.send_text(_json.dumps({"type": "assistant_speaking", "value": False}))
            ws.send_bytes(real_bytes)

            msg = _json.loads(ws.receive_text())
            assert msg["type"] == "user_transcript"
            assert msg["data"] == "sannu"

    # STT must have run exactly once, on exactly the fresh utterance -- NOT
    # on stale_fragment + real_bytes (which is what the pre-fix bug would
    # have produced at the raw-buffer layer).
    mock_transcribe.assert_called_once()
    assert seen_chunks == [_frame(b"\x22\x22") * _SPEECH_FRAMES]
    # The VAD's own reset_states() must have been called on the rising edge
    # -- not just the raw byte buffers cleared.
    assert fake_vad.reset_calls >= 1


def test_live_endpoint_assistant_speaking_flag_has_a_safety_timeout(monkeypatch):
    """If the client never sends assistant_speaking:false (crash, dropped
    frame, backgrounded tab), the server must not stay deaf forever."""
    import json as _json
    from unittest.mock import AsyncMock, patch

    from starlette.testclient import TestClient

    from main import app
    from routers import audio as audio_router

    # Force the safety valve to trip almost immediately instead of waiting
    # the real 15s, so the test stays fast.
    monkeypatch.setattr(audio_router, "_ASSISTANT_SPEAKING_MAX_S", 0.0)

    fake_vad = _ScriptedFakeVAD(_speech_then_silence_script())
    turn_bytes = _frame(b"\x22\x22") * _SPEECH_FRAMES + _frame(b"\x00\x00") * _SILENCE_FRAMES

    with patch("routers.audio.new_vad_stream", return_value=fake_vad), \
         patch("routers.audio._transcribe", AsyncMock(return_value="sannu")) as mock_transcribe, \
         patch("routers.audio._llm_respond", AsyncMock(return_value="Sannu, yaya dai?")), \
         patch("routers.audio._synthesize_speech", return_value=None):
        with TestClient(app).websocket_connect("/api/live") as ws:
            ws.send_text(_json.dumps({"type": "assistant_speaking", "value": True}))
            # With max age forced to 0.0, this audio is already "stale" by
            # the time it's checked, so it must be let through rather than
            # dropped forever.
            ws.send_bytes(turn_bytes)

            msg = _json.loads(ws.receive_text())
            assert msg["type"] == "user_transcript"

    mock_transcribe.assert_called_once()

