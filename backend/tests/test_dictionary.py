"""Tests for services.dictionary_service — the Robinson (1914) lexicon lookup.

These tests use a tiny temp .jsonl fixture (via DICTIONARY_PATH) and reset the
module singleton before each case, so they never depend on the full ~3 MB
lexicon being present.
"""

import json

import pytest

from services import dictionary_service


@pytest.fixture
def lexicon(tmp_path, monkeypatch):
    """Write a tiny fixture lexicon, point DICTIONARY_PATH at it, and reset the
    singleton. Returns the path."""
    rows = [
        {
            "source_en": "abandon",
            "target_ha": "hari",
            "context": "tr. v. hari, har.",
            "provenance": "robinson_1914_vol2",
        },
        {
            "source_en": "abandon",
            "target_ha": "har",
            "context": "tr. v. hari, har.",
            "provenance": "robinson_1914_vol2",
        },
        {
            "source_en": "ground",
            "target_ha": "ƙasa",
            "context": "n. the earth, land.",
            "provenance": "robinson_1914_vol1",
        },
        {
            "source_en": "abbreviate",
            "target_ha": "taƙaita",
            "context": "tr. v. shorten.",
            "provenance": "robinson_1914_vol2",
        },
    ]
    path = tmp_path / "en_ha_pairs.jsonl"
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DICTIONARY_PATH", str(path))
    dictionary_service._reset_for_tests()
    yield path
    dictionary_service._reset_for_tests()


def test_english_to_hausa_lookup(lexicon):
    results = dictionary_service.define("abandon")
    en_ha = [r for r in results if r["direction"] == "en->ha"]
    assert en_ha, "expected at least one en->ha result"
    translations = {r["translation"] for r in en_ha}
    assert "hari" in translations
    assert "har" in translations
    for r in en_ha:
        assert r["headword"] == "abandon"
        assert r["provenance"] == "robinson_1914_vol2"


def test_hausa_to_english_reverse_lookup(lexicon):
    results = dictionary_service.define("taƙaita")
    ha_en = [r for r in results if r["direction"] == "ha->en"]
    assert ha_en
    assert ha_en[0]["headword"] == "taƙaita"
    assert ha_en[0]["translation"] == "abbreviate"
    assert ha_en[0]["provenance"] == "robinson_1914_vol2"


def test_case_insensitive(lexicon):
    lower = dictionary_service.define("abandon")
    upper = dictionary_service.define("ABANDON")
    assert upper == lower
    assert upper


def test_diacritic_folded_hausa_lookup(lexicon):
    """"kasa" (plain ASCII) must find the entry stored as "ƙasa"."""
    results = dictionary_service.define("kasa")
    ha_en = [r for r in results if r["direction"] == "ha->en"]
    assert ha_en
    # Original spelling preserved in the returned entry.
    assert ha_en[0]["headword"] == "ƙasa"
    assert ha_en[0]["translation"] == "ground"


def test_unknown_term_returns_empty(lexicon):
    assert dictionary_service.define("zzxqnonsense") == []


def test_provenance_carried_through(lexicon):
    results = dictionary_service.define("ground")
    assert results
    assert all(r["provenance"] == "robinson_1914_vol1" for r in results)


def test_dictionary_ready_true_when_loaded(lexicon):
    assert dictionary_service.dictionary_ready() is True


def test_dictionary_unavailable_when_path_missing(tmp_path, monkeypatch):
    missing = tmp_path / "does_not_exist.jsonl"
    monkeypatch.setenv("DICTIONARY_PATH", str(missing))
    dictionary_service._reset_for_tests()
    try:
        assert dictionary_service.dictionary_ready() is False
        assert dictionary_service.define("abandon") == []
    finally:
        dictionary_service._reset_for_tests()


def test_prefix_fallback_when_no_exact_match(lexicon):
    # "abbrev" has no exact entry but "abbreviate" starts with it.
    results = dictionary_service.define("abbrev")
    assert any(r["headword"] == "abbreviate" for r in results)
