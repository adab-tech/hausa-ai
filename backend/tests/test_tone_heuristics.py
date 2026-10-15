import unicodedata

import pytest
from orthography import LEXICAL_TONES, apply_tonal_heuristics


def _bare(text: str) -> str:
    """Text with all tone accents removed."""
    d = unicodedata.normalize("NFD", text)
    return unicodedata.normalize("NFC", "".join(c for c in d if c not in "̀́"))


def _marked(text: str) -> bool:
    return any(c in "̀́" for c in unicodedata.normalize("NFD", text))


@pytest.mark.parametrize("word", ["tambaya", "ɗefi", "fangali", "hankali", "zzzxqk", "wanzami"])
def test_unknown_words_are_left_unmarked(word):
    # Previously these received a tone pattern chosen by a heuristic that was no better than chance.
    assert apply_tonal_heuristics(word) == word


def test_unknown_words_keep_their_punctuation():
    assert apply_tonal_heuristics("Tambaya?") == "Tambaya?"
    assert apply_tonal_heuristics("(wanzami),") == "(wanzami),"


def test_words_in_the_lexicon_are_still_marked():
    assert "doki" in LEXICAL_TONES
    out = apply_tonal_heuristics("doki")
    assert _marked(out) and _bare(out) == "doki"


@pytest.mark.parametrize("word", ["kwanduna", "motoci", "gidaye", "dawakai"])
def test_plural_suffix_rules_are_still_applied(word):
    out = apply_tonal_heuristics(word)
    assert _marked(out) and _bare(out) == word


def test_a_sentence_marks_only_the_known_words():
    out = apply_tonal_heuristics("Doki tambaya")
    first, second = out.split(" ")
    assert _marked(first)
    assert second == "tambaya"


def test_empty_and_symbol_only_input():
    assert apply_tonal_heuristics("") == ""
    assert apply_tonal_heuristics("?!") == "?!"
