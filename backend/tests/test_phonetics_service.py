"""Tests for services/phonetics_service.py (Hausa -> IPA via epitran).

epitran is a real dependency (requirements.txt) but has C-extension
sub-dependencies (editdistance, via panphon) with no prebuilt wheel for
every local dev platform/Python combination -- this project's own Windows
dev environment can't build it locally (confirmed: MSVC Build Tools
required), while the production python:3.11-slim image installs it fine
from a prebuilt manylinux wheel. So: the graceful-degradation tests below
run everywhere and are the real regression coverage; the golden-value
transliteration test is skipped wherever epitran isn't actually
importable, and is the test that matters wherever it IS (CI on a platform
with the wheel, production, or a contributor's Linux/macOS machine)."""

import pytest

from services import phonetics_service


@pytest.fixture(autouse=True)
def _reset_epitran_state():
    """Each test gets a clean slate -- the module caches both the epitran
    instance and an 'unavailable' flag at module level."""
    phonetics_service._epi = None
    phonetics_service._epi_unavailable = False
    yield
    phonetics_service._epi = None
    phonetics_service._epi_unavailable = False


def test_empty_text_returns_none_without_touching_epitran(monkeypatch):
    calls = []
    monkeypatch.setattr(phonetics_service, "_get_epitran", lambda: calls.append(1) or None)
    assert phonetics_service.to_ipa("") is None
    assert phonetics_service.to_ipa("   ") is None
    assert calls == []  # never even tried to load epitran for empty input


def test_returns_none_gracefully_when_epitran_unavailable():
    """The real situation on this project's own Windows dev box today --
    must degrade to None, never raise, so a chat request's prosodic-trace
    logging can't be the thing that breaks the request."""
    phonetics_service._epi_unavailable = True
    assert phonetics_service.to_ipa("sannu") is None


def test_unavailable_flag_short_circuits_before_any_import_attempt():
    """Same pattern as vits_engine.py's _init_failed -- once epitran is
    known unavailable, _get_epitran must return immediately without
    attempting the (expensive, exception-raising) import again."""
    phonetics_service._epi_unavailable = True
    assert phonetics_service._get_epitran() is None
    assert phonetics_service._get_epitran() is None  # still short-circuits
    assert phonetics_service._epi is None  # never got as far as assigning it


def test_loaded_instance_is_reused_across_calls(monkeypatch):
    """Once epitran loads successfully, don't re-instantiate Epitran('hau-
    Latn') on every request -- same client-reuse pattern already used for
    the Cerebras/Groq/Gemini SDK clients in routers/chat.py."""
    created = []

    class _FakeEpiInstance:
        pass

    class _FakeEpitranModule:
        class Epitran:
            def __init__(self, code):
                created.append(code)

    monkeypatch.setitem(__import__("sys").modules, "epitran", _FakeEpitranModule())

    first = phonetics_service._get_epitran()
    second = phonetics_service._get_epitran()

    assert first is second
    assert created == ["hau-Latn"]


def test_transliteration_failure_returns_none_not_raise(monkeypatch):
    class _FakeEpi:
        def transliterate(self, text):
            raise RuntimeError("simulated epitran internal error")

    monkeypatch.setattr(phonetics_service, "_get_epitran", lambda: _FakeEpi())
    assert phonetics_service.to_ipa("sannu") is None


# ---------------------------------------------------------------------------
# Golden-value transliteration test -- skipped (not the whole module, just
# this one test) wherever epitran and its editdistance/panphon
# sub-dependencies can't actually be imported. Values verified live
# 2026-08-24 inside a python:3.11-slim container (matching this project's
# production Docker base image exactly) before this integration was added.
# ---------------------------------------------------------------------------
def test_real_hausa_transliteration_matches_verified_output():
    pytest.importorskip("epitran", reason="epitran not installed in this environment")
    phonetics_service._epi = None
    phonetics_service._epi_unavailable = False

    cases = {
        "sannu": "sannu",
        "barka": "baɽka",
        "ɓarna": "ɓaɽna",
        "ɗan": "ɗan",
        "ƙasa": "kʼasa",
        "lafiya": "laɸija",
    }
    for word, expected_ipa in cases.items():
        assert phonetics_service.to_ipa(word) == expected_ipa
