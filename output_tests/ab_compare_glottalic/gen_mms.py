# -*- coding: utf-8 -*-
import os, torch, soundfile as sf
from transformers import VitsModel, AutoTokenizer

def p(s):
    print(str(s).encode('ascii','replace').decode('ascii'), flush=True)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)))
sentences = [
    "Ɗan Adam yana buƙatar haƙuri.",
    "ƴaƴa suna kwaɗayin abinci mai daɗi.",
    "Ka ɓoye wuƙa a cikin ɗaki.",
    "Maƙeri ya ƙera wuƙa da garma.",
    "Ubangida ya karɓi kuɗi daga ɗansa.",
]

p("Loading facebook/mms-tts-hau ...")
model = VitsModel.from_pretrained("facebook/mms-tts-hau")
tok = AutoTokenizer.from_pretrained("facebook/mms-tts-hau")
sr = model.config.sampling_rate
p("MMS sampling rate: %d" % sr)

for i, text in enumerate(sentences, 1):
    inputs = tok(text.lower(), return_tensors="pt")
    with torch.no_grad():
        wav = model(**inputs).waveform.squeeze().cpu().numpy()
    out_path = os.path.join(OUT, "s%d_mms.wav" % i)
    sf.write(out_path, wav, sr)
    p("wrote s%d_mms.wav  (%d samples)" % (i, len(wav)))

p("MMS DONE")
