import random
from datetime import datetime

HAUSA_PROVERBS = [
    "Zaman lafiya ya fi zama ɗan sarki.",
    "Kome nisan jifa ƙasa zai faɗo.",
    "Hargitsin duniya ba ya hana safiya wayewa.",
    "Gani ga wane ya isa tsoron Allah ga mai hankali.",
    "Domin ɗan gari shi ya san lungu-lungun gari."
]

def get_time_of_day_greeting() -> str:
    """Return culturally appropriate time-of-day greeting in Hausa."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Ina kwana, ranka ya daɗe. Fatan kun tashi lafiya."
    elif 12 <= hour < 17:
        return "Barka da yammaci, ranka ya daɗe. Fatan kuna cikin ƙoshin lafiya da amincin Ubangiji."
    else:
        return "Barka da yamma, ranka ya daɗe. Fatan kun yini cikin ƙoshin lafiya da kwanciyar hankali."

def generate_fallback_response(user_text: str, vibe: str = "Classic") -> str:
    """
    Generate a culturally authentic, constitution-compliant Hausa response
    to serve as a fallback when Ollama is offline.
    """
    text_lower = user_text.lower()
    greeting = get_time_of_day_greeting()
    proverb = random.choice(HAUSA_PROVERBS)
    
    # 1. Image Generation request
    if any(w in text_lower for w in ["image", "hoto", "draw", "zanen", "zane", "picture"]):
        prompt = "A beautiful and majestic Hausa cultural scene with gold-leaf borders and Arewa knots"
        if "horse" in text_lower or "doki" in text_lower:
            prompt = "A traditional Hausa Durbar festival horseman in royal attire, gold accents"
        elif "palace" in text_lower or "fada" in text_lower:
            prompt = "A majestic mud-walled Hausa Emir's palace, golden sunbeams shining"
        
        return (
            f"{greeting} Fasahar hotonmu na 'Murya-7' tana aiki a kan wannan umarni na zane na musamman. "
            f"Zamu ƙirƙiri hoton da kuke buƙata domin nuna kyawun al'adarmu da fasahar zane. "
            f"Kamar yadda aka sani, '{proverb}' [MANIFEST: IMAGE|{prompt}]"
        )
        
    # 2. Video Generation request
    if any(w in text_lower for w in ["video", "bidiyo", "motion", "motsi"]):
        prompt = "A sweeping cinematic view of ancient Kano walls and mud-brick architecture, golden hour"
        if "horse" in text_lower or "doki" in text_lower:
            prompt = "A galloping horse at the Durbar festival, dust kicking up, slow motion"
            
        return (
            f"{greeting} Sashen motsi na Murya-7 yana shirin samar muku da bidiyo na musamman domin bayyana kyawun umarninku. "
            f"Kamar yadda kuka sani, '{proverb}' [MANIFEST: VIDEO|{prompt}]"
        )

    # 3. Simple Greetings
    if any(w in text_lower for w in ["sannu", "barka", "hello", "hi"]):
        return (
            f"{greeting} Barka da haɗuwa a wannan cibiya ta fasaha. Muna muku gaisuwa ta musamman da fatan alheri "
            f"da samun nasara a ayyukanku baki ɗaya. Kamar yadda kuka sani, '{proverb}'"
        )
        
    # 4. Cultural/Constitution discussion
    if any(w in text_lower for w in ["girmamawa", "kunya", "cultural", "al'ada", "constitution"]):
        return (
            f"{greeting} Dangane da tsarin mutunci da al'adunmu na Arewa, Murya-7 yana aiki da matuƙar 'Kunya' da 'Girmamawa'. "
            f"Muna kiyaye hooked letters kamar (ɓ, ɗ, ƙ, 'y) da R-to-L tone mapping domin tabbatar da ingancin harshe. "
            f"Kamar yadda kuka sani, '{proverb}'"
        )

    # 5. Default Fallback
    return (
        f"{greeting} Na karɓi saƙonku mai fa'ida da zurfin tunani. Muna nan muna nazarin kowane sashe na umarninku "
        f"domin samar muku da sakamako mai gamsarwa da ya dace da daraja. "
        f"Kamar yadda aka sani, '{proverb}'"
    )
