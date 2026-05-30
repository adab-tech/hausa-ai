import os
import sys
import json

# Ensure backend folder is in path for imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_path = os.path.join(BASE_DIR, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from orthography import normalize_hausa_orthography, apply_tonal_heuristics

def main():
    metadata_path = os.path.join(BASE_DIR, "waxal_hausa", "metadata.jsonl")
    output_jsonl_path = os.path.join(BASE_DIR, "waxal_hausa", "metadata_processed.jsonl")
    output_txt_path = os.path.join(BASE_DIR, "waxal_hausa", "tts_filelist.txt")

    if not os.path.exists(metadata_path):
        print(f"Error: {metadata_path} not found. Please pull the dataset first.")
        sys.exit(1)

    print("Loading raw WAXAL metadata and starting linguistic preprocessing...")
    
    processed_samples = []
    filelist_lines = []

    with open(metadata_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    total = len(lines)
    for idx, line in enumerate(lines):
        sample = json.loads(line)
        raw_text = sample.get("text", "")
        
        # 1. Normalize Hooked Orthography
        normalized_text = normalize_hausa_orthography(raw_text)
        
        # 2. Apply Right-to-Left Tonal Melody heuristics
        prosodic_text = apply_tonal_heuristics(normalized_text)
        
        # Create updated sample object
        processed_sample = {
            "id": sample.get("id"),
            "speaker_id": sample.get("speaker_id"),
            "gender": sample.get("gender"),
            "text_raw": raw_text,
            "text_normalized": normalized_text,
            "text_prosodic": prosodic_text,
            "audio_file": sample.get("audio_file")
        }
        processed_samples.append(processed_sample)

        # Standard TTS format: audio_path|normalized_text|prosodic_text
        audio_file = sample.get("audio_file")
        filelist_lines.append(f"{audio_file}|{normalized_text}|{prosodic_text}")

        if (idx + 1) % 100 == 0 or (idx + 1) == total:
            print(f"Processed {idx + 1}/{total} samples...")

    # Write processed JSONL metadata
    with open(output_jsonl_path, "w", encoding="utf-8") as f:
        for sample in processed_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    # Write standard TTS filelist
    with open(output_txt_path, "w", encoding="utf-8") as f:
        for line in filelist_lines:
            f.write(line + "\n")

    print(f"\nProcessing complete!")
    print(f"  - Processed metadata saved to: {output_jsonl_path}")
    print(f"  - Standard TTS filelist saved to: {output_txt_path}")

if __name__ == "__main__":
    # Ensure stdout works in UTF-8 on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
