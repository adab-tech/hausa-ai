"""Tests for the helper / utility functions in routers.chat and auth."""

import pytest

from routers.chat import _calculate_cultural_confidence, _sanitize

# ---------------------------------------------------------------------------
# _sanitize helper
# ---------------------------------------------------------------------------

def test_sanitize_removes_manifest_tags():
    text = "Hello [MANIFEST: IMAGE|beautiful scene] world"
    assert _sanitize(text) == "Hello  world"


def test_sanitize_removes_special_chars():
    assert _sanitize("hello *world# $") == "hello world"


def test_sanitize_noop_on_clean_text():
    assert _sanitize("Sannu ranka ya dade") == "Sannu ranka ya dade"


# ---------------------------------------------------------------------------
# _calculate_cultural_confidence helper
# ---------------------------------------------------------------------------

def test_confidence_high_when_all_markers_present():
    text = "ɓarawo ɗan ƙauyen, kun ji 'yan birnin. Ranka ya dade."
    assert _calculate_cultural_confidence(text) is True


def test_confidence_low_for_generic_english():
    assert _calculate_cultural_confidence("Hello world, how are you?") is False


def test_confidence_partial_markers():
    # Has hooked letters (40 pts) but nothing else → below 70
    text = "ɓarawo ya tafi"
    assert _calculate_cultural_confidence(text) is False


# ---------------------------------------------------------------------------
# auth module
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_auth_passes_when_no_key_configured(client):
    """Health endpoint always passes (no API_KEY set in tests)."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_auth_rejects_wrong_key(client, monkeypatch):
    import auth as auth_module

    monkeypatch.setattr(auth_module, "_CONFIGURED_KEY", "correct-key")
    response = await client.get(
        "/health", headers={"X-API-Key": "wrong-key"}
    )
    # /health is not protected but other routes are; verify auth logic directly
    # by calling a protected route
    response = await client.post(
        "/api/chat",
        json={"text": "hello"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401
    monkeypatch.setattr(auth_module, "_CONFIGURED_KEY", None)
