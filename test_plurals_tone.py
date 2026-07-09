import sys
import os

# Ensure backend folder is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))
sys.stdout.reconfigure(encoding='utf-8')

from orthography import apply_tonal_heuristics, segment_word_syllables

def test_plural_tone_mapping():
    print("=" * 60)
    print("  VERIFYING HAUSA PLURAL MORPHO-PHONOLOGICAL TONE RULES  ")
    print("=" * 60)
    
    test_cases = [
        # (word, expected_suffix_rule_description, expected_melody)
        ("kwanduna", "Ends in -una (H-L-L)", "kwándùnà"),
        ("kasuna", "Ends in -una (H-L-L)", "kásùnà"),
        ("motoci", "Ends in -oci (H-L-H)", "mótòcí"),
        ("yatsotsi", "Ends in -otsi (H-L-H)", "yátsòtsí"),
        ("gidaye", "Ends in -aye (L-H-L)", "gìdáyè"),
        ("dawakai", "Ends in -ai preceded by consonant (L-H-H)", "dàwákái"),
        ("litattafai", "Ends in -ai preceded by consonant (L-H-H)", "lìtàttáfái")
    ]
    
    passed_all = True
    for word, desc, expected_prosodic in test_cases:
        syllables = segment_word_syllables(word)
        syll_str = "-".join([s[0] for s in syllables])
        output = apply_tonal_heuristics(word)
        
        print(f"Word     : {word} ({syll_str})")
        print(f"Rule     : {desc}")
        print(f"Output   : {output}")
        print(f"Expected : {expected_prosodic}")
        
        # Check if the output contains the expected tonal annotations
        # Removing any case differences or punctuation
        if output.strip().lower() == expected_prosodic.strip().lower():
            print("Status   : PASSED ✅")
        else:
            print("Status   : FAILED ❌")
            passed_all = False
        print("-" * 50)
        
    if passed_all:
        print("\nAll morpho-phonological plural rules verified successfully! 🎉")
        sys.exit(0)
    else:
        print("\nSome verification cases failed.")
        sys.exit(1)

if __name__ == "__main__":
    test_plural_tone_mapping()
