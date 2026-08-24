"""Hausa grapheme-to-IPA phonetic transliteration via epitran ('hau-Latn').

Diagnostic-only today: feeds the [PROSODIC_TRACE] log line in
routers/chat.py so the accuracy of the hand-built tonal heuristic
(LEXICAL_TONES / apply_tonal_heuristics in orthography.py) can be
spot-checked against real segmental IPA, not just eyeballed. Verified live
inside a python:3.11-slim container (matching this project's production
base image) against real Hausa hooked-consonant words:
    ƙasa  -> kʼasa   (ejective velar correctly rendered)
    ɓarna -> ɓaɽna    (implosive preserved, tap/flap r correctly identified)
    ɗan   -> ɗan      (implosive alveolar preserved)
    lafiya-> laɸija   (bilabial fricative, correct y->j)

epitran's G2P is deterministic from ORTHOGRAPHY -- standard Hausa spelling
does not mark tone, so this can never produce tone marks; it is a
segmental (consonant/vowel) transliteration only. It does NOT solve tone
assignment, which stays exactly what it is today: LEXICAL_TONES's
hand-curated dictionary plus a heuristic fallback for words outside it.

epitran is a real dependency (requirements.txt) but this module must never
be the reason a chat/audio request fails -- every function here degrades
to None on any error (missing package, epitran's own internal failure on
an unexpected input) rather than raising.
"""

import logging

logger = logging.getLogger("murya.phonetics")

_epi = None
_epi_unavailable = False


def _get_epitran():
    global _epi, _epi_unavailable
    if _epi_unavailable:
        return None
    if _epi is None:
        try:
            import epitran
            _epi = epitran.Epitran("hau-Latn")
        except Exception as exc:
            # Cache the failure (same pattern as vits_engine.py's
            # _init_failed) so a missing/broken epitran install doesn't
            # retry the expensive import on every single request.
            logger.warning("epitran unavailable -- IPA transliteration disabled: %s", exc)
            _epi_unavailable = True
            return None
    return _epi


def to_ipa(text: str) -> str | None:
    """Transliterate Hausa text to IPA. None if epitran isn't available or
    transliteration fails for any reason -- diagnostic-only, must never
    break a real request."""
    if not text or not text.strip():
        return None
    epi = _get_epitran()
    if epi is None:
        return None
    try:
        return epi.transliterate(text)
    except Exception as exc:
        logger.warning("IPA transliteration failed: %s", exc)
        return None
