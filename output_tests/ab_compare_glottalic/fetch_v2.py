# -*- coding: utf-8 -*-
import os, urllib.request, urllib.parse

def p(s):
    print(str(s).encode('ascii','replace').decode('ascii'), flush=True)

OUT = os.path.dirname(os.path.abspath(__file__))
sentences = [
    "Ɗan Adam yana buƙatar haƙuri.",
    "ƴaƴa suna kwaɗayin abinci mai daɗi.",
    "Ka ɓoye wuƙa a cikin ɗaki.",
    "Maƙeri ya ƙera wuƙa da garma.",
    "Ubangida ya karɓi kuɗi daga ɗansa.",
]

# try both /api/tts and /tts
BASES = ["http://127.0.0.1:8000/api/tts", "http://127.0.0.1:8000/tts"]

def works(base):
    q = urllib.parse.urlencode({"text": "gwaji", "speaker_id": 0})
    try:
        with urllib.request.urlopen(base + "?" + q, timeout=60) as r:
            data = r.read()
        return data[:4] == b"RIFF"
    except Exception as e:
        p("probe %s failed: %s" % (base, e))
        return False

base = None
for b in BASES:
    if works(b):
        base = b
        break
if base is None:
    p("NO WORKING TTS ENDPOINT")
    raise SystemExit(1)
p("Using endpoint: %s" % base)

for i, text in enumerate(sentences, 1):
    q = urllib.parse.urlencode({"text": text, "speaker_id": 0})
    url = base + "?" + q
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            data = r.read()
    except Exception as e:
        p("s%d FAILED: %s" % (i, e))
        continue
    if data[:4] != b"RIFF":
        p("s%d NOT WAV (first bytes: %r len=%d)" % (i, data[:16], len(data)))
        continue
    out = os.path.join(OUT, "s%d_v2.wav" % i)
    with open(out, "wb") as f:
        f.write(data)
    p("wrote s%d_v2.wav  (%d bytes)" % (i, len(data)))

p("V2 DONE")
