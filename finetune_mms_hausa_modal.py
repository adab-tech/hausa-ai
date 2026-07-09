"""Fine-tune facebook/mms-tts-hau on the WAXAL Hausa clips (per speaker).

Uses the ylacombe/finetune-hf-vits recipe: the MMS VITS generator is
re-united with its training discriminator, then fine-tuned on ~200 clips
of a single WAXAL speaker. Run the dataset prep first:

    python utils/prepare_waxal_mms.py

Then launch (one speaker per run, default M4 — most clean clips):

    modal run finetune_mms_hausa_modal.py --speaker M4 --epochs 200

Outputs land in the `hausa-ai-checkpoints` Modal volume under
mms_hau_waxal_<speaker>/ (HF-format model + sample WAVs). Pull with:

    modal volume get hausa-ai-checkpoints mms_hau_waxal_M4 models/mms_hau_waxal_M4

License note: the fine-tuned model inherits CC-BY-NC-4.0 from MMS and
must credit Meta MMS + Google WAXAL when published.
"""

import json
import os
import subprocess

import modal

app = modal.App("hausa-mms-finetuning")

checkpoints_volume = modal.Volume.from_name("hausa-ai-checkpoints", create_if_missing=True)

REPO = "/root/finetune-hf-vits"
DATA_DIR = "/data/waxal_mms"
BASE_CKPT = "/checkpoints/mms-hau-base-with-disc"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "libsndfile1", "ffmpeg", "build-essential", "python3-dev")
    .run_commands(
        f"git clone https://github.com/ylacombe/finetune-hf-vits.git {REPO}",
        f"pip install -r {REPO}/requirements.txt",
        # The recipe repo (2024) predates current transformers/datasets APIs
        # (e.g. VitsConfig.pad_token_id was removed) — pin a compatible era.
        "pip install 'transformers==4.46.3' 'datasets==3.6.0' 'accelerate==1.2.1' "
        "'torch==2.5.1' 'torchaudio==2.5.1' soundfile",
        f"cd {REPO}/monotonic_align && mkdir -p monotonic_align && python setup.py build_ext --inplace",
    )
    .add_local_file(
        os.path.join(os.path.dirname(__file__), "data", "processed", "waxal_mms", "train.parquet"),
        remote_path=f"{DATA_DIR}/train.parquet",
    )
)


@app.function(
    image=image,
    gpu="A10G",
    timeout=14400,  # 4 h is plenty for ~200 clips x 200 epochs
    volumes={"/checkpoints": checkpoints_volume},
)
def finetune(speaker: str = "M4", epochs: int = 200, batch_size: int = 16, learning_rate: float = 2e-5):
    output_dir = f"/checkpoints/mms_hau_waxal_{speaker}"

    # 1. One-time: rebuild the MMS-hau checkpoint with its discriminator
    if not os.path.exists(os.path.join(BASE_CKPT, "config.json")):
        print("[finetune] Converting facebook/mms-tts-hau + discriminator...")
        subprocess.run(
            [
                "python", "convert_original_discriminator_checkpoint.py",
                "--language_code", "hau",
                "--pytorch_dump_folder_path", BASE_CKPT,
            ],
            cwd=REPO,
            check=True,
        )
        checkpoints_volume.commit()
    else:
        print(f"[finetune] Reusing converted base checkpoint at {BASE_CKPT}")

    # 2. Training config (mirrors training_config_examples/finetune_mms.json)
    config = {
        "project_name": f"mms_hausa_waxal_{speaker}",
        "push_to_hub": False,
        "report_to": [],
        "overwrite_output_dir": True,
        "output_dir": output_dir,
        "dataset_name": DATA_DIR,
        "audio_column_name": "audio",
        "text_column_name": "text",
        "train_split_name": "train",
        "eval_split_name": "train",
        "speaker_id_column_name": "speaker_id",
        "override_speaker_embeddings": True,
        "filter_on_speaker_id": speaker,
        "full_generation_sample_text": "sannu da zuwa ina fatan kana lafiya",
        "max_duration_in_seconds": 15,
        "min_duration_in_seconds": 1.0,
        "max_tokens_length": 500,
        "model_name_or_path": BASE_CKPT,
        "preprocessing_num_workers": 4,
        "do_train": True,
        "num_train_epochs": epochs,
        "gradient_accumulation_steps": 1,
        "gradient_checkpointing": False,
        "per_device_train_batch_size": batch_size,
        "learning_rate": learning_rate,
        "adam_beta1": 0.8,
        "adam_beta2": 0.99,
        "warmup_ratio": 0.01,
        "group_by_length": False,
        "do_eval": True,
        "eval_steps": 50,
        "per_device_eval_batch_size": batch_size,
        "max_eval_samples": 25,
        "do_step_schedule_per_epoch": True,
        "weight_disc": 3,
        "weight_fmaps": 1,
        "weight_gen": 1,
        "weight_kl": 1.5,
        "weight_duration": 1,
        "weight_mel": 35,
        "fp16": True,
        "seed": 456,
    }
    config_path = "/root/finetune_config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    # 3. Train
    print(f"[finetune] Fine-tuning speaker {speaker} for {epochs} epochs...")
    subprocess.run(
        ["accelerate", "launch", "run_vits_finetuning.py", config_path],
        cwd=REPO,
        check=True,
    )
    checkpoints_volume.commit()

    # 4. Synthesize benchmark sentences with the fine-tuned model
    print("[finetune] Generating sample WAVs...")
    import scipy.io.wavfile
    import torch
    from transformers import VitsModel, VitsTokenizer

    model = VitsModel.from_pretrained(output_dir)
    tokenizer = VitsTokenizer.from_pretrained(output_dir)
    samples_dir = os.path.join(output_dir, "samples")
    os.makedirs(samples_dir, exist_ok=True)
    sentences = [
        "sannu da zuwa ina fatan kana lafiya",
        "hausa harshe ne mai arziki da tarihi",
        "ilimi gishirin duniya ne kowa ya nemi ya samu",
    ]
    for i, sentence in enumerate(sentences):
        inputs = tokenizer(sentence, return_tensors="pt")
        with torch.no_grad():
            waveform = model(**inputs).waveform[0].cpu().numpy()
        scipy.io.wavfile.write(
            os.path.join(samples_dir, f"sample_{i}.wav"),
            rate=model.config.sampling_rate,
            data=waveform,
        )
    checkpoints_volume.commit()
    print(f"[finetune] Done. Model + samples in volume at {output_dir}")


@app.local_entrypoint()
def main(speaker: str = "M4", epochs: int = 200):
    finetune.remote(speaker=speaker, epochs=epochs)
