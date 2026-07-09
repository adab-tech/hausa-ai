"""Generate 15 baseline samples from the ORIGINAL facebook/mms-tts-hau model
for observation/comparison against the WAXAL-Piper v2 model.

Uses a varied sentence set (greetings, proverbs, everyday speech, numbers,
place names) with deliberate ƴ/ɗ/ƙ/ɓ probes to expose MMS orthographic
handling. Writes mms_orig_01.wav .. mms_orig_15.wav.
"""
import os
import numpy as np
import soundfile as sf
import torch
from transformers import VitsModel, AutoTokenizer

OUT_DIR = r"C:\Users\Adamu\Desktop\Hausa AI\output_tests\mms_base_preview"
os.makedirs(OUT_DIR, exist_ok=True)

SENTENCES = [
    "Sannu da aiki, yaya gajiya?",
    "Ranka ya daɗe, mun gode da ziyararka.",
    "Ina son in sayi doya da shinkafa a kasuwa.",
    "Ƴaƴan nan suna wasa a cikin gida.",
    "Ruwan sama yana zuba tun da safe.",
    "Malam Ibrahim ya tafi Kano jiya da yamma.",
    "Haƙuri maganin duniya ne, in ji masu hikima.",
    "Ka ɗauki littafin nan ka kai wa yaronka.",
    "Muna buƙatar ƙarin lokaci domin gama aiki.",
    "Ƴan Najeriya suna murnar samun 'yanci.",
    "Goma da biyar sun zama ashirin da biyar.",
    "Uwa tana dafa abinci a cikin ɗaki.",
    "Barka da sallah, Allah ya karɓa.",
    "Ɗalibai suna karatun addini a makaranta.",
    "Gari ya waye, lokacin fita zuwa gona ne.",
]

print("Loading facebook/mms-tts-hau ...")
model = VitsModel.from_pretrained("facebook/mms-tts-hau")
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-hau")
rate = model.config.sampling_rate
print("sampling_rate:", rate)

for i, text in enumerate(SENTENCES, 1):
    inputs = tokenizer(text.lower(), return_tensors="pt")
    with torch.no_grad():
        wav = model(**inputs).waveform.squeeze().cpu().numpy()
    out_path = os.path.join(OUT_DIR, f"mms_orig_{i:02d}.wav")
    sf.write(out_path, wav, rate)
    dur = len(wav) / rate
    # ASCII-safe status line (avoid Windows console encoding errors on hooks)
    print(f"[OK] mms_orig_{i:02d}.wav  {dur:.1f}s  <- {text.encode('ascii','replace').decode()}")

print("DONE")
