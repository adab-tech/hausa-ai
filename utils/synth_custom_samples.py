"""Quick local synthesis of custom Hausa sentences using an already-downloaded
Piper ONNX checkpoint, without spinning up another Modal GPU run.

Usage:
    python utils/synth_custom_samples.py <model_dir> <out_dir>
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from services.vits_engine import VitsEngine, FRONTEND_TO_WAXAL_SPEAKER  # noqa: E402

SENTENCES = [
    ("gida", "gobe za mu tafi kasuwa domin sayen abinci da kayan gona."),
    ("ruwa", "idan ruwan sama ya sauka, manoma za su yi murna sosai."),
    ("makaranta", "yara suna zuwa makaranta da safe don neman ilimi."),
    ("labari", "wannan labari ya faru ne shekaru da suka wuce a garinmu."),
    ("aiki", "ina son yin aiki tukuru domin ci gaban al'ummata."),
]

SPEAKERS = ["F1", "F2", "F3", "F4", "M1", "M2", "M3", "M4"]


def main():
    model_dir = sys.argv[1] if len(sys.argv) > 1 else str(
        ROOT / "models/piper_hausa_waxal/eval_v2_epoch2249/eval_v2_epoch2249"
    )
    out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else str(ROOT / "models/piper_hausa_waxal/quick_listen_v2_custom"))
    out_dir.mkdir(parents=True, exist_ok=True)

    engine = VitsEngine(model_dir=model_dir)
    if not engine.session:
        print("Engine failed to initialize"); return

    # Sample a spread of speakers, one new sentence each, no repeats of prior text
    picks = [
        ("F1", SENTENCES[0]), ("M3", SENTENCES[1]), ("F4", SENTENCES[2]),
        ("M1", SENTENCES[3]), ("F2", SENTENCES[4]), ("M4", SENTENCES[0]),
        ("F3", SENTENCES[1]), ("M2", SENTENCES[2]),
    ]
    sheet = ["CUSTOM CONTENT — v2 epoch 2249, new sentences not in the fixed benchmark set:", ""]
    for spk, (tag, text) in picks:
        frontend_idx = [k for k, v in FRONTEND_TO_WAXAL_SPEAKER.items() if v == spk][0]
        pcm = engine.synthesize(text, speaker_id=frontend_idx)
        if pcm is None:
            print(f"FAILED {spk}_{tag}")
            continue
        import wave
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
