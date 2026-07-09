import os
import sys
import time
from pathlib import Path

# Ensure backend folder is in path for imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(BASE_DIR, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Enforce UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from orthography import normalize_hausa_orthography, apply_tonal_heuristics
from services.vits_engine import VitsEngine

def run_benchmarks():
    print("=" * 60)
    print("         HAUSA AI VITS PIPELINE & MODEL OPTIMIZER           ")
    print("=" * 60)
    
    # 1. Test Linguistic Pipeline Latency
    print("\n--- [1] Linguistic Pre-processing Latency Test ---")
    test_text = "Lafiyar yara da mutane tana da matuƙar muhimmanci a yau a ƙasar Hausa."
    print(f"Sample Text: \"{test_text}\"")
    
    start_time = time.perf_counter()
    iterations = 1000
    for _ in range(iterations):
        norm = normalize_hausa_orthography(test_text)
        _ = apply_tonal_heuristics(norm)
    end_time = time.perf_counter()
    
    total_time = (end_time - start_time) * 1000  # ms
    avg_time = total_time / iterations
    print(f"Executed {iterations} pre-processing iterations.")
    print(f"Total Time:   {total_time:.2f} ms")
    print(f"Average Latency per Sentence: {avg_time:.4f} ms")
    
    # 2. Check ONNX Model presence
    print("\n--- [2] Sovereign VITS ONNX Check ---")
    engine = VitsEngine()
    model_path = engine.model_path
    config_path = engine.config_path
    
    print(f"Expected Model Path:  {model_path}")
    print(f"Expected Config Path: {config_path}")
    
    if model_path.exists():
        print("Status: CUSTOM ONNX MODEL DETECTED (LOCAL)")
        print("Running dry-run ONNX inference latency benchmark...")
        
        # Verify characters
        print(f"Vocabulary characters: {len(engine.characters)}")
        
        # Benchmark 10 syntheses
        latencies = []
        synthesized_pcm_size = 0
        
        for i in range(1, 11):
            s_start = time.perf_counter()
            pcm = engine.synthesize("Sannun ku da zuwa barka da yamma.", speaker_id=0)
            s_end = time.perf_counter()
            
            if pcm:
                latency = (s_end - s_start) * 1000
                latencies.append(latency)
                synthesized_pcm_size = len(pcm)
                
        if latencies:
            avg_lat = sum(latencies) / len(latencies)
            min_lat = min(latencies)
            max_lat = max(latencies)
            # Estimate audio duration (assuming 24000 Hz, 16-bit mono = 48000 bytes/sec)
            duration_sec = synthesized_pcm_size / 48000
            rtf = duration_sec / (avg_lat / 1000)
            
            print(f"ONNX Model Benchmark Results (10 Runs):")
            print(f"  Average Latency: {avg_lat:.2f} ms")
            print(f"  Min Latency:     {min_lat:.2f} ms")
            print(f"  Max Latency:     {max_lat:.2f} ms")
            print(f"  Audio Duration:  {duration_sec:.2f} seconds")
            print(f"  Real-Time Factor (RTF): {rtf:.2f}x (synthesis is {rtf:.1f}x faster than real-time)")
            
            if avg_lat < 150.0:
                print("Status: PERFORMANCE OPTIMAL (LATENCY < 150ms)")
            else:
                print("Status: PERFORMANCE WARNING (CONSIDER INT8 QUANTIZATION OR RUNNING ON GPU)")
        else:
            print("Error: Synthesis failed. Check ONNX runtime logs.")
    else:
        print("Status: CUSTOM ONNX MODEL NOT DETECTED LOCALLY")
        print("\n> [!NOTE]")
        print("> To download the trained VITS model from your GCP VM, run:")
        print("> gcloud compute scp Adamu@hausa-ai-train-vm:/home/Adamu/checkpoints/best_model.onnx models/vits/best_model.onnx --zone=us-central1-a")
        print("> gcloud compute scp Adamu@hausa-ai-train-vm:/home/Adamu/checkpoints/config.json models/vits/config.json --zone=us-central1-a")
        print("\n> If model training is in progress, download the current checkpoint to test local synthesis.")
        
    print("\n" + "=" * 60 + "\n")

if __name__ == "__main__":
    run_benchmarks()
