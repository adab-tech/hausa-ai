import random
from datetime import datetime

HAUSA_PROVERBS = [
    "Zaman lafiya ya fi zama ɗan sarki.",
    "Kome nisan jifa ƙasa zai faɗo.",
    "Hargitsin duniya ba ya hana safiya wayewa.",
    "Gani ga wane ya isa tsoron Allah ga mai hankali.",
    "Domin ɗan gari shi ya san lungu-lungun gari."
]


def get_time_of_day_greeting(addressee_gender: str = "unspecified") -> str:
    """Return culturally appropriate time-of-day greeting in Hausa.

    Always uses the grammatical singular, gendered honorific — "ranka ya
    daɗe" (masculine) or "ranki ya daɗe" (feminine) — and singular verb/
    pronoun inflections throughout, never plural ("ku"/"kun") forms.
    """
    hour = datetime.now().hour
    is_feminine = addressee_gender == "feminine"
    honorific = "ranki ya daɗe" if is_feminine else "ranka ya daɗe"
    # "ka tashi" (masc.) vs "ki tashi" (fem.)
    you_rose = "ki tashi" if is_feminine else "ka tashi"
    # "kake cikin" (masc.) vs "kike cikin" (fem.)
    you_are_in = "kike cikin" if is_feminine else "kake cikin"
    # "ka yini" (masc.) vs "ki yini" (fem.)
    you_spent_day = "ki yini" if is_feminine else "ka yini"

    if 5 <= hour < 12:
        return f"Ina kwana, {honorific}. Fatan {you_rose} lafiya."
    elif 12 <= hour < 17:
        return f"Barka da yammaci, {honorific}. Fatan {you_are_in} ƙoshin lafiya da amincin Ubangiji."
    else:
        return f"Barka da yamma, {honorific}. Fatan {you_spent_day} cikin ƙoshin lafiya da kwanciyar hankali."


def generate_fallback_response(
    user_text: str, vibe: str = "Classic", addressee_gender: str = "unspecified"
) -> str:
    """
    Generate a culturally authentic, constitution-compliant Hausa response
    to serve as a fallback when Ollama is offline.

    The user is always addressed in the grammatical singular (never plural
    "ku"/"kun" forms), gendered to match ``addressee_gender`` when known
    ("masculine" -> ka/maka/ayyukanka/kake, "feminine" -> ki/miki/ayyukanki/
    kiki). When unspecified, masculine forms are used as the neutral default
    (this is a last-resort static fallback with no way to ask interactively),
    but the whole response always sticks to a single, consistent form.
    """
    text_lower = user_text.lower()
    greeting = get_time_of_day_greeting(addressee_gender)
    proverb = random.choice(HAUSA_PROVERBS)

    is_feminine = addressee_gender == "feminine"
    # Singular possessive/object suffixes and pronouns, gendered.
    ka_ki = "ki" if is_feminine else "ka"          # "kamar yadda ka/ki sani"
    maka_miki = "miki" if is_feminine else "maka"   # "muku" -> "maka"/"miki"
    # "-nku" -> "-nka"/"-nki", appended to a vowel-final stem: "saƙo" + "nka"
    # = "saƙonka", "umarni" + "nka" = "umarninka", "ayyuka" + "nka" =
    # "ayyukanka" (matches SOVEREIGN_CONSTITUTION's own "ayyukanka"/
    # "ayyukanki" example in chat.py). Do NOT use this after a stem that
    # already ends in "n" (e.g. "saƙon") — that would double the "n".
    nka_nki = "nki" if is_feminine else "nka"
    kake_kike = "kike" if is_feminine else "kake"   # "kuka" -> "kake"/"kike"

    # 1. Image Generation request
    if any(w in text_lower for w in ["image", "hoto", "draw", "zanen", "zane", "picture"]):
        prompt = "A beautiful and majestic Hausa cultural scene with gold-leaf borders and Arewa knots"
        if "horse" in text_lower or "doki" in text_lower:
            prompt = "A traditional Hausa Durbar festival horseman in royal attire, gold accents"
        elif "palace" in text_lower or "fada" in text_lower:
            prompt = "A majestic mud-walled Hausa Emir's palace, golden sunbeams shining"

        return (
            f"{greeting} Fasahar hotonmu na 'Murya' tana aiki a kan wannan umarni na zane na musamman. "
            f"Zamu ƙirƙiri hoton da {kake_kike} buƙata domin nuna kyawun al'adarmu da fasahar zane. "
            f"Kamar yadda aka sani, '{proverb}' [MANIFEST: IMAGE|{prompt}]"
        )

    # 2. Video Generation request
    if any(w in text_lower for w in ["video", "bidiyo", "motion", "motsi"]):
        prompt = "A sweeping cinematic view of ancient Kano walls and mud-brick architecture, golden hour"
        if "horse" in text_lower or "doki" in text_lower:
            prompt = "A galloping horse at the Durbar festival, dust kicking up, slow motion"

        return (
            f"{greeting} Sashen motsi na Murya yana shirin samar {maka_miki} da bidiyo na musamman domin bayyana kyawun umarni{nka_nki}. "
            f"Kamar yadda {ka_ki} sani, '{proverb}' [MANIFEST: VIDEO|{prompt}]"
        )

    # 3. Simple Greetings
    if any(w in text_lower for w in ["sannu", "barka", "hello", "hi"]):
        return (
            f"{greeting} Barka da haɗuwa a wannan cibiya ta fasaha. Muna {maka_miki} gaisuwa ta musamman da fatan alheri "
            f"da samun nasara a ayyuka{nka_nki} baki ɗaya. Kamar yadda {ka_ki} sani, '{proverb}'"
        )

    # 4. Cultural/Constitution discussion
    if any(w in text_lower for w in ["girmamawa", "kunya", "cultural", "al'ada", "constitution"]):
        return (
            f"{greeting} Dangane da tsarin mutunci da al'adunmu na Arewa, Murya yana aiki da matuƙar 'Kunya' da 'Girmamawa'. "
            f"Muna kiyaye hooked letters kamar (ɓ, ɗ, ƙ, 'y) da R-to-L tone mapping domin tabbatar da ingancin harshe. "
            f"Kamar yadda {ka_ki} sani, '{proverb}'"
        )

    # 5. Default Fallback
    return (
        f"{greeting} Na karɓi saƙo{nka_nki} mai fa'ida da zurfin tunani. Muna nan muna nazarin kowane sashe na umarni{nka_nki} "
        f"domin samar {maka_miki} da sakamako mai gamsarwa da ya dace da daraja. "
        f"Kamar yadda aka sani, '{proverb}'"
    )
