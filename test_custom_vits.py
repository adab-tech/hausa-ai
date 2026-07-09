import sys
import os
import soundfile as sf
import numpy as np

# Ensure backend directory is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from services.vits_engine import VitsEngine
from orthography import normalize_hausa_orthography, apply_tonal_heuristics

def run_test():
    print("Initializing VitsEngine...")
    # Initialize engine pointing to the models/vits folder
    engine = VitsEngine(model_dir="models/vits")
    
    if not engine.initialize():
        print("Error: Failed to initialize VitsEngine!")
        return
        
    print("VitsEngine initialized successfully.")
    
    # Benchmark sentences covering:
    # 1. Hooked letters (ɗ, ɓ, ƙ, ƴ)
    # 2. Tonal markers (high/low pitch contours)
    # 3. Speaker IDs (e.g., Male/Female)
    test_cases = [
        # Text, speaker ID, output filename
        ("ɓurɓur ƙyaƙƴawa daɗi", 0, "test_speaker0_hooks.wav"),
        ("Sannu barka da yamma ranka ya daɗe.", 1, "test_speaker1_tone.wav"),
        ("Ɓarayi sun shigo gari da ƙarfi.", 5, "test_speaker5_male.wav"),
    ]
    
    os.makedirs("output_tests", exist_ok=True)
    
    for text, speaker_id, filename in test_cases:
        print(f"\n--- Testing synthesis ---")
        print(f"Raw Input: '{text}'")
        
        # 1. Orthographic hook normalization
        norm_text = normalize_hausa_orthography(text)
        print(f"Normalized: '{norm_text}'")
        
        # 2. Tonal melody mapping
        tonal_text = apply_tonal_heuristics(norm_text)
        print(f"Tonal Text: '{tonal_text}'")
        
        # 3. Synthesize
        print(f"Synthesizing for speaker {speaker_id}...")
        pcm_data = engine.synthesize(tonal_text, speaker_id=speaker_id)
        
        if pcm_data:
            out_path = os.path.join("output_tests", filename)
            # Save raw PCM-16 (mono, 24kHz) to WAV
            audio_samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
            sf.write(out_path, audio_samples, 24000)
            print(f"Saved synthesized audio to {out_path} (length: {len(pcm_data)} bytes)")
        else:
            print("Synthesis failed!")

if __name__ == "__main__":
    run_test()
