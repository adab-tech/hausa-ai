"""Regression tests for the 2026-08-23 deep-scan CSRF finding: admin
pronunciation endpoints accept multipart/form-data (a CORS "simple" content
type -- no preflight) gated only by a SameSite=None session cookie, so a
malicious cross-site page's auto-submitting <form> could reach them with a
logged-in admin's cookie attached. auth.verify_csrf_origin checks
Origin/Referer by hand to close that gap; these tests cover both the unit
behavior of that check and its wiring onto the real routes."""

import io
import wave

import pytest

import auth
import pronunciation_store


@pytest.fixture
def _isolated_pronunciation_store(tmp_path, monkeypatch):
    """Fresh pronunciation_store DB per test -- without this, hitting the
    real POST /api/admin/pronunciation route would write into the actual
    production data directory when this file runs outside the full suite."""
    monkeypatch.setattr(pronunciation_store, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(pronunciation_store, "_DB_PATH", tmp_path / "pronunciation.db")
    pronunciation_store.init_db()


def _wav_bytes() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(b"\x00\x00" * 2400)  # 0.1s of silence
    return buf.getvalue()


class _FakeHeaders(dict):
    def get(self, key, default=None):
        return super().get(key.lower(), default)


class _FakeRequest:
    def __init__(self, headers: dict):
        self.headers = _FakeHeaders({k.lower(): v for k, v in headers.items()})


# ---------------------------------------------------------------------------
# Unit tests: verify_csrf_origin
# ---------------------------------------------------------------------------
@pytest.fixture
def _restricted_origins(monkeypatch):
    monkeypatch.setattr(auth, "_ALLOWED_ORIGINS_SET", {"https://app.murya.ng"})
    yield
    monkeypatch.setattr(auth, "_ALLOWED_ORIGINS_SET", None)


@pytest.mark.anyio
async def test_matching_origin_passes(_restricted_origins):
    await auth.verify_csrf_origin(_FakeRequest({"origin": "https://app.murya.ng"}))


@pytest.mark.anyio
async def test_foreign_origin_rejected(_restricted_origins):
    with pytest.raises(Exception) as exc_info:
        await auth.verify_csrf_origin(_FakeRequest({"origin": "https://evil.example"}))
    assert getattr(exc_info.value, "status_code", None) == 403


@pytest.mark.anyio
async def test_missing_origin_falls_back_to_referer(_restricted_origins):
    await auth.verify_csrf_origin(
        _FakeRequest({"referer": "https://app.murya.ng/admin/review"})
    )


@pytest.mark.anyio
async def test_missing_origin_and_referer_rejected(_restricted_origins):
    with pytest.raises(Exception) as exc_info:
        await auth.verify_csrf_origin(_FakeRequest({}))
    assert getattr(exc_info.value, "status_code", None) == 403


@pytest.mark.anyio
async def test_wildcard_config_is_a_no_op():
    # ALLOWED_ORIGINS='*' (open dev config) -- nothing trusted to check
    # against, so the guard must not block anything.
    assert auth._ALLOWED_ORIGINS_SET is None
    await auth.verify_csrf_origin(_FakeRequest({}))
    await auth.verify_csrf_origin(_FakeRequest({"origin": "https://anything.example"}))


# ---------------------------------------------------------------------------
# Wired onto the real admin pronunciation routes
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_cross_site_form_post_is_blocked(
    client, admin_session, _isolated_pronunciation_store, monkeypatch
):
    """Simulates the actual exploit: a real logged-in admin session cookie,
    but the request arrives with an Origin the deployment doesn't trust --
    exactly what a malicious cross-site <form> submission would send."""
    monkeypatch.setattr(auth, "_ALLOWED_ORIGINS_SET", {"https://app.murya.ng"})
    resp = await client.post(
        "/api/admin/pronunciation",
        data={"text": "gida"},
        files={"audio": ("x.wav", _wav_bytes(), "audio/wav")},
        headers={"Origin": "https://evil.example"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_same_site_form_post_still_works(
    client, admin_session, _isolated_pronunciation_store, monkeypatch
):
    monkeypatch.setattr(auth, "_ALLOWED_ORIGINS_SET", {"https://app.murya.ng"})
    # This dev box has no working ffmpeg for pydub's real decode path; that's
    # an environment gap unrelated to what this test is actually checking
    # (that a legitimate same-origin request still passes the CSRF guard),
    # so stub the decode step rather than depend on ffmpeg being present.
    monkeypatch.setattr(pronunciation_store, "convert_upload_to_pcm24k", lambda raw: b"\x00\x00" * 2400)
    resp = await client.post(
        "/api/admin/pronunciation",
        data={"text": "gida"},
        files={"audio": ("x.wav", _wav_bytes(), "audio/wav")},
        headers={"Origin": "https://app.murya.ng"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
