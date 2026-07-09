"""
Build instruction-tuning JSONL from Robinson EN→HA lexicon pairs.
Output: data/processed/robinson/sft_train.jsonl (chat messages format)
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PAIRS = BASE / "data" / "processed" / "robinson" / "en_ha_pairs.jsonl"
OUT = BASE / "data" / "processed" / "robinson" / "sft_train.jsonl"
MANIFEST = BASE / "data" / "processed" / "robinson" / "sft_manifest.json"

SYSTEM = (
    "Kai Hausa AI ne. Ka amsa da Hausa mai daraja, da ɓ, ɗ, ƙ, ƴ, "
    "kuma ka yi amfani da darajar girmamawa (Ku/Kun)."
)


def pair_to_messages(en: str, ha: str, context: str) -> dict:
    user = f"Fassara wannan kalmar Turanci zuwa Hausa: {en}"
    if context and context != en:
        user += f"\n(Samun: {context[:200]})"
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": ha},
        ]
    }


def main() -> None:
    if not PAIRS.exists():
        print(f"Missing {PAIRS}. Run: python utils/prepare_robinson_ml.py")
        sys.exit(1)

    rows = []
    with PAIRS.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            en = row.get("source_en", "").strip()
            ha = row.get("target_ha", "").strip()
            if len(en) < 2 or len(ha) < 2:
                continue
            rows.append(pair_to_messages(en, ha, row.get("context", "")))

    random.seed(42)
    random.shuffle(rows)
    split = int(len(rows) * 0.95)
    train_rows = rows[:split]
    eval_rows = rows[split:]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for row in train_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    eval_path = OUT.parent / "sft_eval.jsonl"
    with eval_path.open("w", encoding="utf-8") as f:
        for row in eval_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "train_file": str(OUT.relative_to(BASE)),
        "eval_file": str(eval_path.relative_to(BASE)),
        "train_count": len(train_rows),
        "eval_count": len(eval_rows),
        "format": "chat_messages",
        "base_model_suggestion": "Qwen/Qwen2.5-7B-Instruct",
        "ollama_target": "hausa-robinson-sft",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {len(train_rows)} train + {len(eval_rows)} eval rows")
    print(f"Train: {OUT}")
    print(f"Eval:  {eval_path}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
