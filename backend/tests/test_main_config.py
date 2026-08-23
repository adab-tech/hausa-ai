"""Tests for main.py's startup config validation and middleware wiring."""

import pytest
from starlette.middleware.cors import CORSMiddleware

import main


# ---------------------------------------------------------------------------
# Regression: ALLOWED_ORIGINS="" (set but empty-after-strip) used to pass
# startup validation in production and silently configure allow_origins=[],
# blocking ALL cross-origin traffic while /health still reported healthy.
# ---------------------------------------------------------------------------
def test_validate_runtime_config_rejects_empty_allowed_origins_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "")
    monkeypatch.setenv("REVIEWER_API_KEY", "some-key")
    with pytest.raises(RuntimeError, match="ALLOWED_ORIGINS"):
        main._validate_runtime_config()


def test_validate_runtime_config_rejects_whitespace_only_allowed_origins(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "   ")
    monkeypatch.setenv("REVIEWER_API_KEY", "some-key")
    with pytest.raises(RuntimeError, match="ALLOWED_ORIGINS"):
        main._validate_runtime_config()


def test_validate_runtime_config_rejects_wildcard_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")
    monkeypatch.setenv("REVIEWER_API_KEY", "some-key")
    with pytest.raises(RuntimeError, match="ALLOWED_ORIGINS"):
        main._validate_runtime_config()


def test_validate_runtime_config_accepts_explicit_origins_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.murya.ng")
    monkeypatch.setenv("REVIEWER_API_KEY", "some-key")
    main._validate_runtime_config()  # should not raise


def test_validate_runtime_config_allows_empty_origins_outside_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ALLOWED_ORIGINS", "")
    main._validate_runtime_config()  # should not raise outside production


# ---------------------------------------------------------------------------
# Regression: CORSMiddleware must be the outermost middleware so a response
# produced by any inner layer (rate limiting, the security-headers
# middleware, etc.) still gets CORS headers. Starlette's add_middleware()
# inserts each new registration at the FRONT of app.user_middleware, so the
# outermost middleware at request time is user_middleware[0].
# ---------------------------------------------------------------------------
def test_cors_middleware_is_outermost():
    assert main.app.user_middleware[0].cls is CORSMiddleware


# ---------------------------------------------------------------------------
# Regression: startup model preload used to swallow all exceptions with only
# a log warning, leaving /health reporting healthy even when the TTS/STT
# models never loaded. /health should now reflect a failed preload.
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_health_reports_degraded_when_preload_failed(client):
    main.app.state.model_preload_ok = False
    main.app.state.model_preload_error = "boom: model file missing"
    try:
        response = await client.get("/health")
        data = response.json()
        assert response.status_code == 200
        # Existing contract preserved: status/version unchanged.
        assert data["status"] == "sovereign"
        assert "version" in data
        assert data["degraded"] is True
        assert "boom" in data["degraded_reason"]
    finally:
        main.app.state.model_preload_ok = True
        main.app.state.model_preload_error = None


@pytest.mark.anyio
async def test_health_healthy_when_preload_ok(client):
    main.app.state.model_preload_ok = True
    main.app.state.model_preload_error = None
    response = await client.get("/health")
    data = response.json()
    assert data["status"] == "sovereign"
    assert "degraded" not in data


# ---------------------------------------------------------------------------
# Regression: dictionary_service._load() used to parse ~30,700 entries
# in-line on whatever request first triggered it, blocking the event loop
# for that request. It's now pre-loaded at startup via run_in_executor,
# matching the existing Whisper/VITS/Piper preload pattern.
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_lifespan_preloads_dictionary_off_the_event_loop(monkeypatch):
    import services.dictionary_service as dictionary_service

    dictionary_service._reset_for_tests()
    assert dictionary_service._LOADED is False

    # Isolate/no-op the unrelated startup steps so this test only exercises
    # the dictionary preload path.
    monkeypatch.setattr(main.admin_store, "init_db", lambda: None)
    monkeypatch.setattr(main.analytics_store, "init_db", lambda: None)
    monkeypatch.setattr(main.pronunciation_store, "init_db", lambda: None)
    monkeypatch.setattr(main.qa_store, "init_db", lambda: None)
    import routers.audio as audio_module
    monkeypatch.setattr(audio_module, "_get_whisper", lambda: None)
    monkeypatch.setattr(audio_module, "_get_vits", lambda: None)
    monkeypatch.setattr(audio_module, "_get_piper", lambda: None)

    async with main.lifespan(main.app):
        pass

    # Loading was actually triggered by the lifespan (not left for the first
    # real request to pay for).
    assert dictionary_service._LOADED is True
