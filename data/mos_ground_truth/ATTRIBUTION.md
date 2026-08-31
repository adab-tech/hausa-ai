# MOS listening-test ground-truth clips

## Source & credit

Two real human Hausa recordings, pulled from the **WAXAL** multilingual
African-language speech corpus, `hau_tts/test` split.

- Upstream dataset: https://hf.co/datasets/google/WaxalNLP (Google)
- Mirror used to fetch these two clips: https://hf.co/datasets/adab-tech/WaxalNLP
- Files here: `gt0.wav` ("Busasshen reshen bishiya maciji ya nannade shi mai
  launin ruwan kasa da zane-zane."), `gt1.wav` ("Yau za a wuni da tsananin
  rana.") — converted from the dataset's source MP3 to 48 kHz PCM WAV,
  content otherwise unmodified.

## Licence — CC-BY-4.0 / CC-BY-SA-4.0 (WAXAL corpus)

Free to use, redistribute, and include in a served product with attribution.

## Usage in this project

Serves as the **naturalness ceiling** ("ground_truth" condition) in the MOS
(Mean Opinion Score) listening test — see `backend/mos_store.py` and
`backend/seed_mos_stimuli.py`. Baked into the backend Docker image and served
publicly at `/api/mos/audio/{clip_id}` alongside synthesized Murya clips, so
listeners can rate real human speech blind against the TTS voice.
