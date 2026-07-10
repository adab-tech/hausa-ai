"""Tests for the deterministic Hausa fallback templates in routers.fallback.

These templates fire as a last resort when both Ollama and Gemini fail.
They must never mix plural ("ku"/"kun"/"-ku"/"muku") address forms with
singular ("ka"/"ki") honorifics in the same response -- see the
[MANDATORY_SOCIAL_HIERARCHY] rule in SOVEREIGN_CONSTITUTION (chat.py).
"""

from routers.fallback import generate_fallback_response, get_time_of_day_greeting

# Plural markers that must never appear once a singular addressee form has
# been selected. Padded with spaces / hyphens to avoid false positives on
# substrings that happen to contain "ku" (e.g. "kuka", "kake").
PLURAL_MARKERS = ["kun ", " ku ", "kuna ", "muku", "nku", "nku'", "-ku"]


def _assert_no_plural_markers(text: str):
    lowered = text.lower()
    for marker in PLURAL_MARKERS:
        assert marker not in lowered, f"found plural marker {marker!r} in: {text}"


def test_greeting_masculine_has_no_plural_markers():
    greeting = get_time_of_day_greeting("masculine")
    assert "ranka ya daɗe" in greeting
    _assert_no_plural_markers(greeting)


def test_greeting_feminine_has_no_plural_markers():
    greeting = get_time_of_day_greeting("feminine")
    assert "ranki ya daɗe" in greeting
    _assert_no_plural_markers(greeting)


def test_greeting_unspecified_defaults_to_consistent_masculine():
    greeting = get_time_of_day_greeting("unspecified")
    assert "ranka ya daɗe" in greeting
    _assert_no_plural_markers(greeting)


def test_default_fallback_masculine_has_no_plural_markers():
    text = generate_fallback_response("Me kake yi?", addressee_gender="masculine")
    assert "ranka ya daɗe" in text
    _assert_no_plural_markers(text)


def test_default_fallback_feminine_has_no_plural_markers():
    text = generate_fallback_response("Me kike yi?", addressee_gender="feminine")
    assert "ranki ya daɗe" in text
    _assert_no_plural_markers(text)


def test_greeting_branch_has_no_plural_markers():
    text = generate_fallback_response("Sannu", addressee_gender="masculine")
    _assert_no_plural_markers(text)


def test_video_branch_has_no_plural_markers():
    text = generate_fallback_response("ka yi mini bidiyo", addressee_gender="feminine")
    assert "ranki ya daɗe" in text
    _assert_no_plural_markers(text)


def test_image_branch_has_no_plural_markers():
    text = generate_fallback_response("ka zana hoto", addressee_gender="masculine")
    _assert_no_plural_markers(text)


def test_cultural_branch_has_no_plural_markers():
    text = generate_fallback_response("faɗa mini game da al'ada", addressee_gender="masculine")
    _assert_no_plural_markers(text)


# Absence-of-plural-markers alone doesn't catch malformed word construction
# (e.g. "saƙon" + "anka" -> "saƙonanka", a doubled/garbled suffix that
# contains no plural marker at all but is still wrong). These assert the
# exact, correctly-formed singular possessive words appear, and that their
# previously-shipped malformed counterparts do not.
def test_default_fallback_uses_correctly_formed_possessives_masculine():
    text = generate_fallback_response("Me kake yi?", addressee_gender="masculine")
    assert "saƙonka" in text
    assert "umarninka" in text
    assert "saƙonanka" not in text
    assert "umarinanka" not in text


def test_default_fallback_uses_correctly_formed_possessives_feminine():
    text = generate_fallback_response("Me kike yi?", addressee_gender="feminine")
    assert "saƙonki" in text
    assert "umarninki" in text
    assert "saƙonanki" not in text
    assert "umarinanki" not in text


def test_greeting_branch_uses_correctly_formed_possessive():
    text = generate_fallback_response("Sannu", addressee_gender="masculine")
    assert "ayyukanka" in text
    assert "ayyukaanka" not in text


def test_video_branch_uses_correctly_formed_possessive():
    text = generate_fallback_response("ka yi mini bidiyo", addressee_gender="feminine")
    assert "umarninki" in text
    assert "umarinanki" not in text
