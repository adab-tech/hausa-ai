from orthography import (
    hausa_cardinal,
    normalize_hausa_orthography,
    spell_out_hausa_numbers,
)

def test_normalize_hausa_orthography():
    # Test cases for hooked letters b', d', k', 'y
    assert normalize_hausa_orthography("b'aki") == "ɓaki"
    assert normalize_hausa_orthography("d'an gari") == "ɗan gari"
    assert normalize_hausa_orthography("k'asa") == "ƙasa"
    assert normalize_hausa_orthography("'yanci") == "ƴanci"
    assert normalize_hausa_orthography("y'anci") == "ƴanci"

    # Test standard text remains untouched
    assert normalize_hausa_orthography("Barka da zuwa") == "Barka da zuwa"


# ---------------------------------------------------------------------------
# Hausa cardinal number spelling — the TTS phoneme map has no digit glyphs,
# so numerals must be spelled out or they produce no audio at all.
# ---------------------------------------------------------------------------
def test_hausa_cardinal_units_and_teens():
    assert hausa_cardinal(0) == "sifili"
    assert hausa_cardinal(1) == "ɗaya"
    assert hausa_cardinal(5) == "biyar"
    assert hausa_cardinal(10) == "goma"
    assert hausa_cardinal(11) == "goma sha ɗaya"
    assert hausa_cardinal(15) == "goma sha biyar"


def test_hausa_cardinal_tens_and_hundreds():
    assert hausa_cardinal(20) == "ashirin"
    assert hausa_cardinal(21) == "ashirin da ɗaya"
    assert hausa_cardinal(99) == "casa'in da tara"
    assert hausa_cardinal(100) == "ɗari"
    assert hausa_cardinal(125) == "ɗari da ashirin da biyar"
    assert hausa_cardinal(200) == "ɗari biyu"


def test_hausa_cardinal_thousands():
    assert hausa_cardinal(1000) == "dubu"
    assert hausa_cardinal(2000) == "dubu biyu"
    # Two thousand and twenty-six
    assert hausa_cardinal(2026) == "dubu biyu da ashirin da shida"
    # One thousand eight hundred and four (Sokoto Caliphate, 1804)
    assert hausa_cardinal(1804) == "dubu da ɗari takwas da huɗu"


def test_spell_out_in_sentence():
    # Digits inside a sentence become spoken words; other text is untouched.
    assert spell_out_hausa_numbers("shekara ta 2026") == "shekara ta dubu biyu da ashirin da shida"
    # Thousands separator is handled.
    assert spell_out_hausa_numbers("1,500 naira") == "dubu da ɗari biyar naira"
    # Decimal read digit-by-digit after 'digo' (point).
    assert spell_out_hausa_numbers("3.5 dola") == "uku digo biyar dola"


def test_spell_out_leaves_plain_text_untouched():
    assert spell_out_hausa_numbers("Barka da zuwa") == "Barka da zuwa"
