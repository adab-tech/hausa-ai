import os
import sys
import re

# Ensure backend folder is in path for imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(BASE_DIR, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Enforce UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from orthography import normalize_hausa_orthography, apply_tonal_heuristics, LEXICAL_TONES, segment_word_syllables

TEST_SENTENCES = [
    "Sannun ku da zuwa barka da yamma.",
    "Lafiyar yara da mutane tana da matuƙar muhimmanci a yau.",
    "b'aki da d'umi ne a cikin k'asar Hausa.",
    "d'an k'asa da mace sun ci abinci lafiyayye a gida.",
    "Baba ya tafi daji don ya gani ko da ruwa a kogi.",
    "yiwuwa gobe a samu iska mai d'umi da safe.",
    "Motsi ya fi laɓewa."
]

def run_linguistic_audit():
    print("=" * 60)
    print("      SOVEREIGN HAUSA LINGUISTIC AUDITOR (Axiom Trace)      ")
    print("=" * 60)
    
    total_words = 0
    dict_hits = 0
    simplified_hooks_found = 0
    hooks_corrected = 0
    
    # Simple regex to check for simplified hooked indicators
    hook_pattern = re.compile(r"\b[bdkyBDKY]'|'[yY]|\b[tT]s'")
    
    print("\n--- Detailed Sentence Audit Logs ---\n")
    
    for idx, sentence in enumerate(TEST_SENTENCES, 1):
        print(f"[{idx}] Raw Input:  \"{sentence}\"")
        
        # Track simplified hooks in the raw sentence
        hooks_in_raw = hook_pattern.findall(sentence)
        simplified_hooks_found += len(hooks_in_raw)
        
        # 1. Run Orthography Normalization
        normalized = normalize_hausa_orthography(sentence)
        print(f"    Normalized: \"{normalized}\"")
        
        # Verify normalization resolved the hooks
        hooks_in_norm = hook_pattern.findall(normalized)
        corrected_hooks = len(hooks_in_raw) - len(hooks_in_norm)
        hooks_corrected += corrected_hooks
        
        # 2. Run Tonal Melody Mapping
        prosodic = apply_tonal_heuristics(normalized)
        print(f"    Prosodic:   \"{prosodic}\"")
        
        # 3. Analyze word matches
        words = normalized.split()
        sentence_hits = 0
        word_details = []
        
        for word in words:
            # Strip punctuation
            clean_word = re.sub(r"[^\wƁƊƘƳɓɗƙƴ']", "", word).lower()
            if not clean_word:
                continue
                
            total_words += 1
            is_hit = clean_word in LEXICAL_TONES
            if is_hit:
                dict_hits += 1
                sentence_hits += 1
                
            # Get syllable segmentation for reporting
            syllables = segment_word_syllables(clean_word)
            syll_str = "-".join([s[0] for s in syllables])
            match_type = "DICT_MATCH" if is_hit else "SYLL_FALLBACK"
            word_details.append(f"{word}({syll_str}:{match_type})")
            
        hit_rate = (sentence_hits / len(words)) * 100 if words else 0
        print(f"    Segmentation & Match:")
        print(f"      {' | '.join(word_details)}")
        print(f"    Sentence Hit Rate: {hit_rate:.1f}%")
        print("-" * 50)
        
    # Summary Metrics Calculation
    overall_hit_rate = (dict_hits / total_words) * 100 if total_words else 0
    hook_correction_rate = (hooks_corrected / simplified_hooks_found) * 100 if simplified_hooks_found else 100
    
    # Calculate sovereign score
    sovereign_score = (overall_hit_rate * 0.4) + (hook_correction_rate * 0.6)
    
    print("\n" + "=" * 60)
    print("                    AUDIT SUMMARY REPORT                    ")
    print("=" * 60)
    print(f"Total Words Evaluated:         {total_words}")
    print(f"Lexical Dictionary Hits:       {dict_hits}")
    print(f"Dictionary Hit Rate (Prosody): {overall_hit_rate:.2f}%")
    print(f"Simplified Hooks Found:        {simplified_hooks_found}")
    print(f"Simplified Hooks Corrected:    {hooks_corrected}")
    print(f"Hook Correction Success Rate:  {hook_correction_rate:.2f}%")
    print("-" * 60)
    print(f"SOVEREIGN LINGUISTIC SCORE:   {sovereign_score:.2f} / 100.00")
    
    if sovereign_score >= 85.0:
        print("Status: LINGUISTIC PIPELINE COMPLIANT (EXCELLENT)")
    elif sovereign_score >= 70.0:
        print("Status: LINGUISTIC PIPELINE COMPLIANT (GOOD)")
    else:
        print("Status: LINGUISTIC PIPELINE WARNING (REQUIRES FURTHER DICTIONARY POPULATION)")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    run_linguistic_audit()
