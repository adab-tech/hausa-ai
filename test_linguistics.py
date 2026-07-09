import sys
import os

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))
sys.stdout.reconfigure(encoding='utf-8')

from orthography import normalize_hausa_orthography, apply_tonal_heuristics
from routers.chat import get_vertex_token, _build_vertex_payload, ChatRequest, HistoryItem, stream_gcp_fallback
import asyncio

def test_orthography():
    print("--- Testing Orthography Normalization ---")
    inputs = [
        "d'an k'asa",
        "y'anci da daidaito",
        "b'aki da d'umi",
        "sannun barka da zuwa",
        "K'asar Hausa",
        "'yanci",
        "B'aure"
    ]
    for inp in inputs:
        out = normalize_hausa_orthography(inp)
        print(f"Input : {inp}")
        print(f"Output: {out}")
        print("-" * 20)

def test_tonal_mapping():
    print("\n--- Testing R-to-L Tonal Mapping Heuristics ---")
    inputs = [
        "Sannun ku da zuwa",
        "Barka da yamma ranka ya dade",
        "Kunya da girmamawa sune tushen mutunci"
    ]
    for inp in inputs:
        out = apply_tonal_heuristics(inp)
        print(f"Input : {inp}")
        print(f"Output: {out}")
        print("-" * 20)

async def test_gcp_fallback_connection():
    print("\n--- Testing GCP/Gemini Fallback connection ---")
    try:
        # Build mock request
        req = ChatRequest(
            text="Sannu! Bayyana mana dan takaitaccen tarihin birnin Kano.",
            history=[
                HistoryItem(role="user", text="Sannu"),
                HistoryItem(role="assistant", text="Ina kwana, ranka ya daɗe. Fatan kun tashi lafiya. Barka da zuwa.")
            ],
            vibe="Classic"
        )
        
        print("Streaming from GCP/Gemini Fallback...")
        full_response = ""
        async for chunk in stream_gcp_fallback(req):
            print(chunk, end="", flush=True)
            full_response += chunk
            
        print("\n\nStream finished successfully!")
        print(f"Word count: {len(full_response.split())}")
        
    except Exception as e:
        print(f"\nFallback connection failed (expected if offline/no key/no API access): {e}")

async def main():
    test_orthography()
    test_tonal_mapping()
    await test_gcp_fallback_connection()

if __name__ == "__main__":
    asyncio.run(main())
