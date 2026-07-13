from orthography import (
    hausa_cardinal,
    normalize_digits,
    normalize_hausa_orthography,
    prepare_text_for_tts,
    spell_out_hausa_numbers,
)


# ---------------------------------------------------------------------------
# Foreign-digit normalization — the LLM sometimes emits Arabic-Indic/Persian
# numerals in Hausa text; they must fold to Western digits (correct for Hausa,
# and required for the number to display and to be speakable by TTS).
# ---------------------------------------------------------------------------
def test_normalize_arabic_indic_digits():
    assert normalize_digits("Zaben ٢٠١٥") == "Zaben 2015"
    assert normalize_digits("٠١٢٣٤٥٦٧٨٩") == "0123456789"


def test_normalize_persian_digits():
    assert normalize_digits("۲۰۱۹") == "2019"


def test_normalize_digits_leaves_ascii_and_text_untouched():
    assert normalize_digits("Zaben 2015 (2019)") == "Zaben 2015 (2019)"
    assert normalize_digits("Barka da yamma") == "Barka da yamma"


def test_orthography_folds_foreign_digits():
    # The main normalizer folds digits too, so the reported bug string is fixed.
    assert normalize_hausa_orthography("Zaben ٢٠١٥") == "Zaben 2015"


def test_tts_prep_speaks_arabic_indic_year():
    # Foreign digits must survive into the number speller (else silent in TTS).
    out = prepare_text_for_tts("A shekara ta ٢٠١٥")
    assert "٢" not in out
    assert "dubu biyu da goma sha biyar" in out  # 2015

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


# ---------------------------------------------------------------------------
# prepare_text_for_tts — the full synthesis-input pipeline. Each case guards
# a real failure mode of the 42-symbol phoneme map (silent drops, word
# gluing, and '$'/'^'/'_' doubling as tokenizer control symbols).
# ---------------------------------------------------------------------------
def test_tts_prep_naira():
    assert prepare_text_for_tts("Kudin ya kai ₦500") == "Kudin ya kai naira ɗari biyar"


def test_tts_prep_dollar_never_reaches_tokenizer():
    # '$' is the phoneme map's EOS control symbol — it must be converted,
    # never passed through.
    out = prepare_text_for_tts("Farashin $20 ne")
    assert "$" not in out
    assert out == "Farashin dala ashirin ne"


def test_tts_prep_percent():
    assert prepare_text_for_tts("kashi 50% na mutane") == "kashi hamsin cikin ɗari na mutane"


def test_tts_prep_slash_gendered_alternatives():
    # 'maka/miki' must not glue into 'makamiki' once '/' is dropped.
    assert prepare_text_for_tts("zan taimaka maka/miki") == "zan taimaka maka ko miki"


def test_tts_prep_newlines_do_not_glue_words():
    out = prepare_text_for_tts("Babban taken\nabu na farko")
    assert "takenabu" not in out
    assert "taken abu" in out


def test_tts_prep_markdown_stripped_with_spacing():
    out = prepare_text_for_tts("**Muhimmi**: ga jerin abubuwa")
    assert "*" not in out
    assert out == "Muhimmi : ga jerin abubuwa" or out == "Muhimmi: ga jerin abubuwa"


def test_tts_prep_control_symbols_removed():
    out = prepare_text_for_tts("wannan _kalma_ da ^alama da $")
    for ch in ("_", "^", "$"):
        assert ch not in out


def test_tts_prep_combined_hooked_and_numbers():
    # Hooked-consonant normalization still runs inside the pipeline.
    assert prepare_text_for_tts("k'asa 2") == "ƙasa biyu"
