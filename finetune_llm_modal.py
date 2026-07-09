"""
Fine-tune a Hausa lexicon/translation adapter on Robinson SFT data via Modal GPU.
Uses LoRA on Qwen2.5-7B-Instruct; checkpoints saved to Modal volume hausa-ai-llm-checkpoints.
"""
from __future__ import annotations

import os
import modal

app = modal.App("hausa-ai-llm-finetune")
llm_volume = modal.Volume.from_name("hausa-ai-llm-checkpoints", create_if_missing=True)

BASE = os.path.dirname(__file__)
SFT_DIR = os.path.join(BASE, "data", "processed", "robinson")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.2.2",
        "transformers==4.46.3",
        "datasets==3.1.0",
        "peft==0.13.2",
        "trl==0.12.1",
        "accelerate==1.2.1",
        "bitsandbytes==0.44.1",
        "sentencepiece",
    )
    .add_local_dir(SFT_DIR, remote_path="/src/sft")
)

MODEL_ID = os.getenv("SFT_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
MAX_SAMPLES = int(os.getenv("SFT_MAX_SAMPLES", "4096"))


@app.function(
    image=image,
    gpu="A10G",
    timeout=14400,
    volumes={"/checkpoints": llm_volume},
)
def finetune():
    import json
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTTrainer, SFTConfig

    train_path = "/src/sft/sft_train.jsonl"
    rows = []
    with open(train_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= MAX_SAMPLES:
                break
            rows.append(json.loads(line))

    def format_chat(example):
        msgs = example["messages"]
        text = ""
        for m in msgs:
            text += f"<|{m['role']}|>\n{m['content']}\n"
        text += "<|end|>\n"
        return {"text": text}

    ds = Dataset.from_list(rows).map(format_chat)

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype="float16",
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb,
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)
    lora = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)

    out_dir = "/checkpoints/hausa-robinson-lora"
    args = SFTConfig(
        output_dir=out_dir,
        num_train_epochs=1,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        logging_steps=25,
        save_steps=500,
        max_seq_length=512,
        dataset_text_field="text",
        bf16=True,
        report_to=[],
    )
    trainer = SFTTrainer(model=model, train_dataset=ds, processing_class=tokenizer, args=args)
    trainer.train()
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    print(f"[LLM Finetune] Saved LoRA adapter to {out_dir}")


@app.local_entrypoint()
def main():
    finetune.remote()
