import re

# Hooked character mappings for Standard Hausa orthography
# Supports lowercase and uppercase conversions
HOOKED_MAP = {
    # Lowercase
    r"b'": "ɓ",
    r"d'": "ɗ",
    r"k'": "ƙ",
    r"y'": "ƴ",
    r"'y": "ƴ",
    r"ts'": "ts",
    # Uppercase
    r"B'": "Ɓ",
    r"D'": "Ɗ",
    r"K'": "Ƙ",
    r"Y'": "Ƴ",
    r"'Y": "Ƴ",
    r"Ts'": "Ts",
    r"TS'": "TS"
}

# Eastern Arabic-Indic (U+0660-0669) and Persian/Urdu (U+06F0-06F9) digits ->
# ASCII 0-9. The LLM sometimes emits these in Hausa text (e.g. "Zaben ٢٠١٥"),
# which is wrong for Hausa (which uses Western digits) AND breaks TTS — those
# glyphs aren't in the voice's phoneme map, so the number would be dropped,
# and the ASCII-digit number speller wouldn't match them either.
_FOREIGN_DIGITS = {
    **{chr(0x0660 + i): str(i) for i in range(10)},  # ٠١٢٣٤٥٦٧٨٩
    **{chr(0x06F0 + i): str(i) for i in range(10)},  # ۰۱۲۳۴۵۶۷۸۹
}
_FOREIGN_DIGIT_RE = re.compile("[" + "".join(_FOREIGN_DIGITS) + "]")


def normalize_digits(text: str) -> str:
    """Convert Arabic-Indic / Persian digit glyphs to ASCII 0-9. Leaves all
    other text untouched."""
    if not text:
        return text
    return _FOREIGN_DIGIT_RE.sub(lambda m: _FOREIGN_DIGITS[m.group(0)], text)


def normalize_hausa_orthography(text: str) -> str:
    """
    Normalizes simplified or ASCII representation of Hausa hooked characters
    to standard Unicode representations. Handles uppercase and lowercase forms.
    Also folds any Arabic-Indic/Persian digits to ASCII (see normalize_digits).

    Examples:
      - 'doki' -> 'doki'
      - 'b\'aki' -> 'ɓaki'
      - 'd\'an' -> 'ɗan'
      - 'k\'asa' -> 'ƙasa'
      - 'y\'anci' or '\'yanci' -> 'ƴanci'
    """
    normalized = normalize_digits(text)

    # 1. First replace explicit quote representations (e.g. b', d', k', y', 'y)
    # Using word boundaries where appropriate or specific patterns.
    #
    # Case-preserving: these used to be split into a case-INSENSITIVE pass
    # (always producing the lowercase hooked letter) followed by a
    # case-sensitive uppercase-only pass -- but since the insensitive pass
    # ran first and matched BOTH cases, it consumed every occurrence before
    # the uppercase pass ever got a chance to run, silently lowercasing any
    # capitalized hooked-letter word (sentence-initial, proper nouns) that
    # should have kept its capital. `str.isupper()` ignores the apostrophe
    # (only cased characters count), so it correctly detects "B'" as
    # uppercase and "b'" as lowercase regardless of which side the
    # apostrophe sits on (matters for the y'/'y pair).
    def _hooked(lower: str, upper: str):
        def repl(m: re.Match) -> str:
            return upper if m.group(0).isupper() else lower
        return repl

    # All hooked-letter targets come from HOOKED_MAP so there is exactly one
    # source of truth for the mapping (previously this function re-implemented
    # the same letter mapping by hand, which could silently drift from
    # HOOKED_MAP over time).
    normalized = re.sub(r"\bb\'", _hooked(HOOKED_MAP["b'"], HOOKED_MAP["B'"]), normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bd\'", _hooked(HOOKED_MAP["d'"], HOOKED_MAP["D'"]), normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bk\'", _hooked(HOOKED_MAP["k'"], HOOKED_MAP["K'"]), normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\by\'|\'y", _hooked(HOOKED_MAP["y'"], HOOKED_MAP["Y'"]), normalized, flags=re.IGNORECASE)

    def _ts_repl(m: re.Match) -> str:
        letters = m.group(0)[:2]
        if letters.isupper():
            return HOOKED_MAP["TS'"]
        if letters[0].isupper():
            return HOOKED_MAP["Ts'"]
        return HOOKED_MAP["ts'"]

    normalized = re.sub(r"ts\'", _ts_repl, normalized, flags=re.IGNORECASE)

    # 2. Replace dangling post-consonant quotes (occurrences not caught above
    # because they don't sit at a word boundary, e.g. mid-word "gab'a").
    for key in ("b'", "d'", "k'", "y'", "'y", "B'", "D'", "K'", "Y'", "'Y"):
        normalized = normalized.replace(key, HOOKED_MAP[key])

    return normalized


# ---------------------------------------------------------------------------
# Hausa cardinal-number spelling (for TTS)
# ---------------------------------------------------------------------------
# The trained VITS voice's phoneme inventory is 42 symbols — a-z, punctuation,
# and the hooked consonants ɓɗƙƴ. It has NO digit glyphs, so any Arabic
# numeral in the model's reply is silently dropped by the tokenizer and
# produces no audio at all. Spell numbers out as Hausa words before synthesis
# so "2026" is actually spoken ("dubu biyu da ashirin da shida") instead of
# vanishing. Standard Hausa (Kananci/Fada) cardinals.
_HA_UNITS = ["", "ɗaya", "biyu", "uku", "huɗu", "biyar", "shida", "bakwai", "takwas", "tara"]
_HA_TENS = {
    1: "goma", 2: "ashirin", 3: "talatin", 4: "arba'in", 5: "hamsin",
    6: "sittin", 7: "saba'in", 8: "tamanin", 9: "casa'in",
}


def _ha_below_100(n: int) -> str:
    """0 <= n < 100 -> Hausa words."""
    if n < 10:
        return _HA_UNITS[n]
    if n < 20:
        r = n - 10
        return "goma" if r == 0 else f"goma sha {_HA_UNITS[r]}"
    t, r = divmod(n, 10)
    return _HA_TENS[t] if r == 0 else f"{_HA_TENS[t]} da {_HA_UNITS[r]}"


def _ha_below_1000(n: int) -> str:
    """0 <= n < 1000 -> Hausa words."""
    if n < 100:
        return _ha_below_100(n)
    h, r = divmod(n, 100)
    hundreds = "ɗari" if h == 1 else f"ɗari {_HA_UNITS[h]}"
    return hundreds if r == 0 else f"{hundreds} da {_ha_below_100(r)}"


def hausa_cardinal(n: int) -> str:
    """Non-negative integer -> Standard Hausa cardinal words.

    Handles units, tens, hundreds (ɗari), thousands (dubu) and millions
    (miliyan), joining groups with the connective 'da'. Numbers at/above a
    billion are read digit-by-digit (a giant single cardinal would be both
    unnatural and error-prone, and such runs are usually IDs/phone numbers).
    """
    if n == 0:
        return "sifili"
    if n >= 1_000_000_000:
        return " ".join(_HA_UNITS[int(d)] if d != "0" else "sifili" for d in str(n))

    parts: list[str] = []
    if n >= 1_000_000:
        m, n = divmod(n, 1_000_000)
        parts.append("miliyan" if m == 1 else f"miliyan {_ha_below_1000(m)}")
    if n >= 1000:
        th, n = divmod(n, 1000)
        parts.append("dubu" if th == 1 else f"dubu {_ha_below_1000(th)}")
    if n > 0:
        parts.append(_ha_below_1000(n))
    return " da ".join(parts)


def _spell_digits(digits: str) -> str:
    """Spell each digit individually as Hausa words. Used for tokens with a
    leading zero (phone numbers, codes) where parsing as an integer would
    silently drop the leading zero(s) or change how the number reads (e.g.
    '0500' is a code read digit-by-digit, not the cardinal 'five hundred')."""
    return " ".join(_HA_UNITS[int(d)] if d != "0" else "sifili" for d in digits)


def _spell_number_token(token: str) -> str:
    """Convert one matched numeric token (already comma-stripped) to Hausa
    words. Supports an optional decimal part read digit-by-digit after
    'digo' (point), e.g. '3.5' -> 'uku digo biyar'.

    A token with a leading zero (and more than one digit) is spelled out
    digit-by-digit rather than parsed with int() -- routing "08012345678"
    through int() silently drops the leading zero (becomes a 10-digit
    number, one digit short), and "0500" would be read as the cardinal
    "five hundred" instead of the intended digit-by-digit "zero five zero
    zero". Phone numbers and codes are the common real-world case."""
    if "." in token:
        int_part, _, frac_part = token.partition(".")
        if int_part and int_part.startswith("0") and len(int_part) > 1:
            int_words = _spell_digits(int_part)
        else:
            int_words = hausa_cardinal(int(int_part)) if int_part else "sifili"
        frac_words = _spell_digits(frac_part)
        return f"{int_words} digo {frac_words}".strip()
    if token.startswith("0") and len(token) > 1:
        return _spell_digits(token)
    return hausa_cardinal(int(token))


def spell_out_hausa_numbers(text: str) -> str:
    """Replace Arabic-numeral runs in `text` with spoken Hausa words.

    Intended for the TTS path only (display text keeps its digits). Commas
    used as thousands separators between digits are stripped first so
    '1,000' reads as one number; a comma not between digits is left alone.
    """
    # Drop thousands-separator commas (digit,digit) but keep list commas.
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)
    # Match integers or decimals (not identifiers like 'a1b').
    return re.sub(
        r"(?<![A-Za-z\d])\d+(?:\.\d+)?(?![A-Za-z\d])",
        lambda m: _spell_number_token(m.group(0)),
        text,
    )


# Currency symbols -> Hausa words. Currency-first is natural Hausa word
# order ("naira dubu goma" = ten thousand naira), and the symbols usually
# precede the digits in written text, so a plain global replacement lands
# the word in the right place: '₦500' -> 'naira 500' -> 'naira ɗari biyar'.
_CURRENCY_WORDS = {
    "₦": " naira ",
    "$": " dala ",
    "€": " yuro ",
    "£": " fam ",
}

# English glosses in parentheses: the constitution/tutor asks the model to give
# a Hausa term with its English gloss on first mention — "ruwa (water)",
# "ilimin halittu (Biology)". The SCREEN should keep the gloss, but the VOICE is
# a Hausa voice and should speak ONLY the Hausa — not read the English aloud
# (and not mangle it). This strips a parenthetical from the SPOKEN text when its
# content looks like a short English gloss: plain ASCII letters, 1-3 words, and
# no Hausa hooked letters. Longer or hooked-letter parentheticals are Hausa
# asides and are kept.
_HOOKED = "ɓɗƙƴƁƊƘƳ"
_PAREN_RE = re.compile(r"\s*\(([^()]{1,40})\)")
_ASCII_GLOSS_RE = re.compile(r"[A-Za-z][A-Za-z /'-]*$")
# Common Hausa words that legitimately appear in parentheses as asides (ASCII,
# so charset can't tell them from an English gloss) — always keep these spoken.
_HAUSA_PAREN_KEEP = {
    "misali", "wato", "watau", "kamar", "kuma", "gani", "duba", "watakila",
    "wajen", "ma", "dss", "sauransu", "haka", "shi", "ita",
}


def strip_english_glosses_for_speech(text: str) -> str:
    """Remove short English-gloss parentheticals from TTS text so the Hausa
    voice speaks only the Hausa. Keeps Hausa asides (hooked letters, common
    Hausa words, or >3 words). Spoken-text only — the displayed reply keeps its
    parentheses."""
    def _repl(m: "re.Match[str]") -> str:
        inner = m.group(1).strip()
        if any(c in inner for c in _HOOKED):      # Hausa aside -> keep
            return m.group(0)
        words = inner.split()
        if len(words) > 3:                        # phrase -> likely Hausa -> keep
            return m.group(0)
        if any(w.lower().strip(".,") in _HAUSA_PAREN_KEEP for w in words):
            return m.group(0)                     # known Hausa word -> keep
        if _ASCII_GLOSS_RE.match(inner):          # short ASCII gloss -> drop
            return ""
        return m.group(0)
    return _PAREN_RE.sub(_repl, text)


def prepare_text_for_tts(text: str) -> str:
    """Full text-normalization pipeline for speech synthesis.

    The trained voice's phoneme map is 42 symbols; everything else is
    silently skipped by the tokenizer, which has two failure modes worth
    engineering around:
      - meaning loss: ₦/%/digits vanish ("₦500" said as just "ɗari biyar");
      - word gluing: dropped separators (newline, '/') concatenate the
        words around them ("maka/miki" -> "makamiki", mispronounced).
    Worse, '$', '^' and '_' ARE in the map — as the EOS/BOS/pad control
    symbols — so a literal dollar sign in LLM output injects an
    end-of-sequence token mid-speech.

    Order matters: hooked consonants first (they may precede numbers),
    currency before number spelling (so the amount is still digits when the
    currency word is placed), percent before number spelling for the same
    reason, then numbers, then separator repair, then whitespace collapse.
    """
    text = normalize_hausa_orthography(text)

    # Speak only the Hausa: drop short English-gloss parentheticals before the
    # rest of the pipeline (the screen still shows them).
    text = strip_english_glosses_for_speech(text)

    # Currency symbols -> Hausa words (also removes '$' before it can be
    # read as the tokenizer's EOS control symbol).
    for sym, word in _CURRENCY_WORDS.items():
        text = text.replace(sym, word)

    # '50%' / '50 %' -> '50 cikin ɗari' ("in a hundred" — standard Hausa
    # percentage phrasing; text that already says 'kashi 50%' becomes the
    # canonical 'kashi 50 cikin ɗari'). A '%' not after a digit is just
    # dropped later, which is fine.
    text = re.sub(r"(?<=\d)\s*%", " cikin ɗari", text)

    text = spell_out_hausa_numbers(text)

    # Separators the phoneme map would drop, gluing adjacent words:
    # 'maka/miki' -> 'maka ko miki' ("or" — this app's own replies use the
    # slash constantly for gendered alternatives); '@' -> ' a ' (as read
    # aloud in addresses); newlines/tabs become spaces via \s+ below.
    text = re.sub(r"(?<=\w)/(?=\w)", " ko ", text)
    text = text.replace("@", " a ")

    # Markdown/formatting and control symbols -> space (NOT deleted — a
    # deleted separator glues words). Keep the apostrophe: it's meaningful
    # Hausa orthography (a'a, ɗan'uwa).
    text = re.sub(r"[*#_^~|<>\[\]{}()\"“”„]", " ", text)

    return re.sub(r"\s+", " ", text).strip()


def segment_word_syllables(word: str) -> list[tuple[str, str]]:
    """
    Segments a Hausa word into a list of (syllable_text, weight) tuples.
    Weights are either 'light' (CV) or 'heavy' (CVV, CVC).
    """
    # Remove punctuation for syllable counting
    clean_word = re.sub(r"[^\wƁƊƘƳɓɗƙƴ']", "", word)
    if not clean_word:
        return []
        
    lower_word = clean_word.lower()
    tokens = []
    i = 0
    while i < len(lower_word):
        # Match digraphs (longest first)
        digraph_match = re.match(r"^(ts|sh|ch|gy|ky|ƙy|fy|gw|kw|ƙw|hw)", lower_word[i:])
        if digraph_match:
            tokens.append((clean_word[i:i+digraph_match.end()], "C"))
            i += digraph_match.end()
            continue
            
        # Match single consonants (including hooked letters and glottal stop)
        c_match = re.match(r"^[ɓɗƙƴbdfghjklmnrstwyz']", lower_word[i:])
        if c_match:
            tokens.append((clean_word[i:i+1], "C"))
            i += 1
            continue
            
        # Match long vowels and diphthongs
        v_long_match = re.match(r"^(aa|ee|ii|oo|uu|ai|au)", lower_word[i:])
        if v_long_match:
            tokens.append((clean_word[i:i+2], "V_long"))
            i += 2
            continue
            
        # Match short vowels
        v_match = re.match(r"^[aeiou]", lower_word[i:])
        if v_match:
            tokens.append((clean_word[i:i+1], "V_short"))
            i += 1
            continue
            
        # Fallback for other characters
        tokens.append((clean_word[i:i+1], "C"))
        i += 1

    # Group tokens into syllables: CV(C) structure
    syllables = []
    num_tokens = len(tokens)
    j = 0
    while j < num_tokens:
        c_val = ""
        v_val = ""
        v_type = "V_short"
        coda_val = ""
        
        # 1. Consonant
        if j < num_tokens and tokens[j][1] == "C":
            c_val = tokens[j][0]
            j += 1
            
        # 2. Vowel
        if j < num_tokens and tokens[j][1] in ("V_short", "V_long"):
            v_val = tokens[j][0]
            v_type = tokens[j][1]
            j += 1
            
        # 3. Coda consonant (belongs to this syllable if followed by another C, or at word end)
        if j < num_tokens and tokens[j][1] == "C":
            is_coda = False
            if j == num_tokens - 1:
                is_coda = True
            elif j + 1 < num_tokens and tokens[j+1][1] == "C":
                is_coda = True
                
            if is_coda:
                coda_val = tokens[j][0]
                j += 1
                
        syllable_text = c_val + v_val + coda_val
        weight = "heavy" if (v_type == "V_long" or coda_val != "") else "light"
        if syllable_text:
            syllables.append((syllable_text, weight))
            
    return syllables

# Map common Hausa lexical items to their standard tone melodies
LEXICAL_TONES = {
    # Greetings & Courtesy
    "sannu": ["H", "L"],
    "sannun": ["H", "L"],
    "barka": ["H", "H"],
    "barkan": ["H", "H"],
    "lafiya": ["H", "H", "L"],
    "lafiyayye": ["H", "H", "L", "H"],
    "madalla": ["L", "H", "L"],
    "godiya": ["L", "H", "L"],
    "gode": ["H", "H"],
    
    # Pronouns & Particles
    "na": ["L"],
    "naa": ["H"],
    "ni": ["H"],
    "kai": ["H"],
    "ke": ["H"],
    "shi": ["H"],
    "ita": ["H", "L"],
    "mu": ["H"],
    "ku": ["H"],
    "su": ["H"],
    "mun": ["H"],
    "kun": ["H"],
    "sun": ["H"],
    "ya": ["L"],
    "ta": ["L"],
    "kuma": ["H", "L"],
    "don": ["H"],
    "da": ["L"],
    "a": ["L"],
    "ne": ["H"],
    "ce": ["H"],
    "ko": ["H"],
    "mai": ["H"],
    "fi": ["H"],
    
    # Time & Question Words
    "yanzu": ["H", "L"],
    "yau": ["H"],
    "gobe": ["H", "L"],
    "dare": ["L", "H"],
    "rana": ["H", "L"],
    "safe": ["L", "H"],
    "yaushe": ["H", "L"],
    "ina": ["L", "H"],
    "yaya": ["H", "L"],
    "mene": ["H", "L"],
    "menene": ["H", "L", "L"],
    
    # Numbers
    "ɗan": ["H"],
    "ɗaya": ["L", "H"],
    "biyu": ["H", "L"],
    "uku": ["H", "L"],
    "hudu": ["H", "L"],
    "biyar": ["L", "H"],
    "shida": ["H", "L"],
    "bakwai": ["H", "H"],
    "takwas": ["L", "H"],
    "tara": ["H", "L"],
    "goma": ["H", "L"],
    "dari": ["H", "L"],
    "dubu": ["H", "L"],
    
    # Core Nouns
    "doki": ["H", "L"],
    "ƙasa": ["L", "H"],
    "ƙasar": ["L", "H"],
    "girma": ["H", "L"],
    "kunya": ["H", "L"],
    "al'ada": ["L", "H", "L"],
    "mutunci": ["L", "H", "L"],
    "yaro": ["H", "L"],
    "yara": ["H", "L"],
    "mace": ["H", "L"],
    "namiji": ["L", "H", "L"],
    "mutum": ["L", "H"],
    "mutane": ["H", "H", "L"],
    "abinci": ["L", "H", "L"],
    "ruwa": ["L", "H"],
    "wuta": ["L", "H"],
    "gida": ["L", "H"],
    "hanya": ["H", "L"],
    "aiki": ["H", "L"],
    "baba": ["H", "L"],
    "mama": ["H", "L"],
    "daji": ["H", "L"],
    "kogi": ["H", "L"],
    "tsauni": ["H", "L"],
    "iska": ["L", "H"],
    "ƙwai": ["H"],
    "hausa": ["H", "H"],
    "lafiyar": ["L", "L", "H"],
    "matuƙar": ["L", "H", "L"],
    "muhimmanci": ["L", "H", "H", "L"],
    "fada": ["H", "L"],      # palace
    "fadaa": ["L", "H"],     # fighting/speaking
    
    # Core Verbs
    "yi": ["H"],
    "yiwuwa": ["L", "H", "L"],
    "samu": ["H", "L"],
    "tafi": ["H", "L"],
    "zo": ["H"],
    "ci": ["H"],
    "sha": ["H"],
    "gani": ["H", "L"],
    "ji": ["H"],
    "laɓewa": ["L", "L", "H"],
    "cikin": ["L", "H"],
    "ɗumi": ["H", "L"]
}

def apply_tonal_heuristics(text: str) -> str:
    """
    Implements Litvinova's Right-to-Left (R-to-L) Tonal Melody Mapping.
    Segments each word into syllables and assigns a pitch accent melody
    from right to left.
    
    Returns a representation of the text annotated with high (H) and low (L) tone markers
    suitable for prosodic diagnostics in the Axiom Trace.
    """
    words = text.split()
    processed_words = []
    
    for word in words:
        # Strip punctuation for processing
        word_clean = re.sub(r"[^\wƁƊƘƳɓɗƙƴ']", "", word)
        punc_left = re.match(r"^[^\wƁƊƘƳɓɗƙƴ']*", word).group(0)
        punc_right = re.search(r"[^\wƁƊƘƳɓɗƙƴ']*$", word).group(0)
        
        if not word_clean:
            processed_words.append(word)
            continue
            
        syllables = segment_word_syllables(word_clean)
        if not syllables:
            processed_words.append(word)
            continue
            
        # Select tone melody based on word or deterministic hash
        word_lower = word_clean.lower()
        if word_lower in LEXICAL_TONES:
            melody = LEXICAL_TONES[word_lower]
        else:
            # Check morpho-phonological rules for Hausa plural suffixes
            if word_lower.endswith("una"):  # Suffix -una (e.g. kwanduna, kasuna)
                melody = ["H", "L", "L"]
            elif word_lower.endswith("oshi") or word_lower.endswith("oshe"):  # Suffix -oshi / -oshe (e.g. akwashi)
                melody = ["H", "L", "H"]
            elif word_lower.endswith("aye") or word_lower.endswith("ayi"):  # Suffix -aye / -ayi (e.g. gidaye, wajaje)
                melody = ["L", "H", "L"]
            elif word_lower.endswith("oci") or word_lower.endswith("otsi"):  # Suffix -oci / -otsi (e.g. motoci, yatsotsi)
                melody = ["H", "L", "H"]
            elif re.search(r"[bdfghjklmnrstwyzɓɗƙƴ']ai$", word_lower):  # Suffix -ai preceded by consonant (e.g. dawakai, litattafai)
                melody = ["L", "H", "H"]
            else:
                # Fallback: assign melody based on syllable count and ending
                # If word ends in heavy syllable, often uses L-H or H-L
                if syllables[-1][1] == "heavy":
                    melody = ["L", "H"]
                else:
                    # Simple deterministic mapping using word hash
                    melodies = [["H", "L"], ["L", "H"], ["H", "H"]]
                    idx = sum(ord(char) for char in word_lower) % len(melodies)
                    melody = melodies[idx]
                
        # Perform Right-to-Left tone mapping
        tones = []
        melody_idx = len(melody) - 1
        for i in range(len(syllables) - 1, -1, -1):
            if melody_idx >= 0:
                tones.append(melody[melody_idx])
                if melody_idx > 0:
                    melody_idx -= 1
            else:
                # Spread the leftmost tone
                tones.append(melody[0])
        tones.reverse()
        
        # Format the word with tone tags
        formatted_syllables = []
        for (syll_text, weight), tone in zip(syllables, tones):
            # Annotate syllables with tone markers (e.g. ´ for high, ` for low)
            tone_symbol = "́" if tone == "H" else "̀"
            # Try to place the tone mark on the first vowel of the syllable
            vowel_match = re.search(r"[aeiouAEIOU]", syll_text)
            if vowel_match:
                v_idx = vowel_match.start()
                syll_annotated = syll_text[:v_idx+1] + tone_symbol + syll_text[v_idx+1:]
            else:
                syll_annotated = syll_text + f"({tone})"
            formatted_syllables.append(syll_annotated)
            
        processed_words.append(punc_left + "".join(formatted_syllables) + punc_right)
        
    return " ".join(processed_words)
