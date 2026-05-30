import json
import os
import re
import sys
from collections import Counter

# Set stdout to UTF-8 to prevent encoding errors on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def analyze():
    metadata_path = "waxal_hausa/metadata.jsonl"
    if not os.path.exists(metadata_path):
        print(f"Error: {metadata_path} not found.")
        return

    samples = []
    with open(metadata_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    total_samples = len(samples)
    print(f"=== General Dataset Statistics ===")
    print(f"Total samples: {total_samples}")

    # Speakers and Genders
    speakers = {}
    gender_counts = Counter()
    sample_gender_counts = Counter()

    for s in samples:
        spk = s.get("speaker_id", "unknown")
        gender = s.get("gender", "unknown")
        if spk not in speakers:
            speakers[spk] = gender
            gender_counts[gender] += 1
        sample_gender_counts[gender] += 1

    total_speakers = len(speakers)
    print(f"Total unique speakers: {total_speakers}")
    print("\nSpeakers by Gender:")
    for g, count in gender_counts.items():
        print(f"  - {g}: {count} speakers")
        
    print("\nSamples by Gender:")
    for g, count in sample_gender_counts.items():
        percentage = (count / total_samples) * 100
        print(f"  - {g}: {count} samples ({percentage:.2f}%)")

    # Samples per speaker
    spk_sample_counts = Counter(s.get("speaker_id", "unknown") for s in samples)
    print("\nSamples per Speaker:")
    for spk, count in sorted(spk_sample_counts.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]):
        gender = speakers.get(spk, "unknown")
        print(f"  - Speaker {spk} ({gender}): {count} samples")

    # Text analysis
    print(f"\n=== Linguistic & Text Statistics ===")
    all_words = []
    sentence_lengths = []
    
    # Track representations of hooked characters
    unicode_hooks = {
        "ɗ": 0, "ɗ".upper(): 0,
        "ɓ": 0, "ɓ".upper(): 0,
        "ƙ": 0, "ƙ".upper(): 0,
        "ƴ": 0, "ƴ".upper(): 0,
        "ɗ": 0, "Ɗ": 0, "ɓ": 0, "Ɓ": 0, "ƙ": 0, "Ƙ": 0, "ƴ": 0, "Ƴ": 0,
    }
    
    # Regex to find ASCII hooked representations: e.g. d', k', 'y, b' (using single quote ' or curly apostrophe ’)
    ascii_patterns = {
        "d' / d’": re.compile(r"[dD]['\u2019]"),
        "k' / k’": re.compile(r"[kK]['\u2019]"),
        "b' / b’": re.compile(r"[bB]['\u2019]"),
        "'y / ’y": re.compile(r"['\u2019][yY]"),
    }
    
    ascii_hook_counts = Counter()

    for s in samples:
        text = s.get("text", "")
        # Split text into words (removing punctuation except hooked-letter markers)
        # For word count, we can just split by whitespace
        words = text.split()
        sentence_lengths.append(len(words))
        all_words.extend(words)
        
        # Count Unicode hooks
        for char in text:
            if char in unicode_hooks:
                unicode_hooks[char] += 1
                
        # Count ASCII hooks
        for key, pattern in ascii_patterns.items():
            matches = len(pattern.findall(text))
            if matches > 0:
                ascii_hook_counts[key] += matches

    total_words = len(all_words)
    vocab = set(w.lower().strip(".,;:!?\"'()[]{}«»") for w in all_words)
    unique_words = len(vocab)
    
    print(f"Total word tokens: {total_words}")
    print(f"Unique vocabulary size: {unique_words}")
    print(f"Average sentence length: {sum(sentence_lengths)/total_samples:.2f} words")
    print(f"Min sentence length: {min(sentence_lengths)} words")
    print(f"Max sentence length: {max(sentence_lengths)} words")

    print("\n=== Orthography / Hooked Letter Analysis ===")
    print("Unicode Hooked Letters found in raw corpus:")
    print(f"  - ɗ / Ɗ (implosive d): {unicode_hooks.get('ɗ', 0) + unicode_hooks.get('Ɗ', 0)}")
    print(f"  - ɓ / Ɓ (implosive b): {unicode_hooks.get('ɓ', 0) + unicode_hooks.get('Ɓ', 0)}")
    print(f"  - ƙ / Ƙ (ejective k): {unicode_hooks.get('ƙ', 0) + unicode_hooks.get('Ƙ', 0)}")
    print(f"  - ƴ / Ƴ (glottalized y): {unicode_hooks.get('ƴ', 0) + unicode_hooks.get('Ƴ', 0)}")

    print("\nASCII/Apostrophe Hooked Letters found in raw corpus:")
    for k, v in ascii_hook_counts.items():
        print(f"  - {k}: {v}")

    # Vocabulary diversity metrics (Type-Token Ratio)
    ttr = unique_words / total_words if total_words > 0 else 0
    print(f"\nType-Token Ratio (Vocabulary Diversity): {ttr:.4f}")

if __name__ == "__main__":
    analyze()
