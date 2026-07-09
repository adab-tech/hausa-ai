"""Synthesize sentences specifically stress-testing Hausa's hooked letters
(ɓ ɗ ƙ ƴ) using an already-downloaded Piper ONNX checkpoint.

Usage:
    python utils/synth_hooked_letters.py <model_dir> <out_dir>
"""
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from services.vits_engine import VitsEngine, FRONTEND_TO_WAXAL_SPEAKER  # noqa: E402

# Each sentence foregrounds specific hooked letters (tagged in the filename).
PICKS = [
    ("F1", "dan_bace_kauye", "ɗan yaro ya ɓace a cikin ƙauyen jiya da dare."),
    ("M1", "aiki_tukuru_gona", "manoma suna aiki tuƙuru domin ƙara amfanin gonaki."),
    ("F2", "yan_mata_kofa", "ƴan mata suna wasa kusa da ƙofar makaranta."),
    ("M2", "boye_gaskiya", "kada ka ɓoye gaskiya domin tsoron mutane."),
    ("F3", "dauki_littafi", "ɗauki wannan littafi ka kai wa malami a ɗakin karatu."),
    ("M3", "kauna_hakuri", "ƙauna da haƙuri su ne asalin zaman lafiya."),
    ("F4", "barayi_kauye", "ɓarayi sun ɓata dukiyar talakawa a ƙauyen nan."),
    ("M4", "yan_kasa_hakki", "ƴan ƙasar nan suna son a girmama haƙƙinsu."),
]


def main():
    model_dir = sys.argv[1] if len(sys.argv) > 1 else str(
        ROOT / "models/piper_hausa_waxal/eval_v2_epoch2249/eval_v2_epoch2249"
    )
    out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else str(ROOT / "models/piper_hausa_waxal/quick_listen_v2_hooked"))
    out_dir.mkdir(parents=True, exist_ok=True)

    engine = VitsEngine(model_dir=model_dir)
    if not engine.session:
        print("Engine failed to initialize"); return

    sheet = ["HOOKED-LETTER STRESS TEST — v2 epoch 2249 (ɓ ɗ ƙ ƴ):", ""]
    for spk, tag, text in PICKS:
        frontend_idx = [k for k, v in FRONTEND_TO_WAXAL_SPEAKER.items() if v == spk][0]
        pcm = engine.synthesize(text, speaker_id=frontend_idx)
        if pcm is None:
            print(f"FAILED {spk}_{tag}")
            continue
        wav_path = out_dir / f"{spk}_{tag}.wav"
        with wave.open(str(wav_path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm)
        sheet.append(f"{spk}_{tag}.wav")
        sheet.append(f"  -> {text}")
        sheet.append("")
        print(f"wrote {wav_path}")

    (out_dir / "EVAL_SHEET.txt").write_text("\n".join(sheet), encoding="utf-8")


if __name__ == "__main__":
    main()
