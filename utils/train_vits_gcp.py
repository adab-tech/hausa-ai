"""
WAXAL Hausa TTS Training Orchestration Script
==============================================
This script sets up a multi-speaker VITS (Variational Inference with adversarial learning) 
training pipeline using the Coqui TTS framework, specifically optimized for the staged 
WAXAL Hausa TTS dataset and our custom prosodic tone mappings.

Prerequisites on the GPU VM:
----------------------------
1. Install CUDA-enabled PyTorch
2. Install TTS:
   $ pip install coqui-tts
3. Install Google Cloud Storage client:
   $ pip install google-cloud-storage
"""

import os
import sys
import argparse
from pathlib import Path

# Monkey-patch transformers to satisfy older coqui-tts imports on python 3.12
try:
    import torch
    import transformers.pytorch_utils
    if not hasattr(transformers.pytorch_utils, "isin_mps_friendly"):
        def isin_mps_friendly(elements, test_elements):
            return torch.isin(elements, test_elements)
        transformers.pytorch_utils.isin_mps_friendly = isin_mps_friendly
        print("[PATCH] Successfully monkey-patched transformers.pytorch_utils.isin_mps_friendly")
except ImportError:
    pass


def setup_training_config(bucket_name, local_data_dir):
    try:
        from TTS.tts.configs.vits_config import VitsConfig
        from TTS.tts.models.vits import Vits
        from TTS.utils.audio import AudioProcessor
        from TTS.tts.datasets import load_tts_samples, register_formatter
        from TTS.tts.configs.shared_configs import BaseDatasetConfig, CharactersConfig
    except ImportError:
        print("Error: 'coqui-tts' is not installed. Please install it with 'pip install coqui-tts' on your GPU instance.")
        return None

    # Define paths
    local_data_path = Path(local_data_dir)
    filelist_path = local_data_path / "tts_filelist.txt"
    
    if not filelist_path.exists():
        print(f"Error: Manifest file {filelist_path} not found. Please sync it from GCS first.")
        return None

    # Custom character set for Hausa including hooked letters and tone markers
    # Standard Latin + Hooked (ɓ, ɗ, ƙ, ƴ) + Accents (́, ̀)
    hausa_characters = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        "ɓɗƙƴƁƊƘƳ"
        "́̀"  # High and Low tone markers
    )
    hausa_punctuations = " .,!?;:-"

    # Define custom formatter
    def waxal_hausa_formatter(root_path, meta_file, **kwargs):
        import os
        txt_file = os.path.join(root_path, meta_file)
        items = []
        with open(txt_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                cols = line.split("|")
                wav_file = os.path.join(root_path, cols[0])
                parts = os.path.basename(cols[0]).split("_")
                if len(parts) >= 2:
                    speaker_name = parts[1] # e.g. "M4", "F1", etc.
                else:
                    speaker_name = "default"
                text = cols[2]
                items.append({
                    "text": text,
                    "audio_file": wav_file,
                    "speaker_name": speaker_name,
                    "root_path": root_path
                })
        return items

    register_formatter("waxal_hausa", waxal_hausa_formatter)

    characters_config = CharactersConfig(
        characters=hausa_characters,
        punctuations=hausa_punctuations
    )
    dataset_config = BaseDatasetConfig(
        formatter="waxal_hausa",
        dataset_name="waxal",
        path=local_data_dir,
        meta_file_train="tts_filelist.txt"
    )

    print("Configuring VITS Multi-Speaker TTS model for Hausa...")
    
    config = VitsConfig(
        audio=dict(
            num_mels=80,
            fft_size=1024,
            hop_length=256,
            win_length=1024,
            sample_rate=24000,  # WAXAL high-fidelity sample rate
            resample=True,
            preemphasis=0.97,
            ref_level_db=20,
            power=1.5,
            griffin_lim_iters=60,
        ),
        run_name="waxal_hausa_vits_v1",
        batch_size=32,
        eval_batch_size=16,
        num_loader_workers=4,
        num_eval_loader_workers=4,
        run_eval=True,
        test_delay_epochs=-1,
        epochs=1000,  # High number for quality convergence
        text_cleaner="multilingual_cleaners",
        use_phonemes=False,  # Train directly on tone-mapped characters for native contour accuracy
        phoneme_language="ha",
        characters=characters_config,
        datasets=[dataset_config],
        # Multi-speaker setup (WAXAL has 8 speakers: 4 Male, 4 Female)
        use_speaker_embedding=True,
        # Optimizer settings
        lr_gen=2e-4,
        lr_disc=2e-4,
        kl_loss_alpha=1.0,
        # Save checkpoints directly
        save_step=2000,
        save_n_checkpoints=5,
        output_path=str(local_data_path / "checkpoints"),
    )

    return config

def download_data_from_gcs(bucket_name, dest_dir):
    """Download manifests and files from GCS to local scratch directory on the GPU instance."""
    try:
        from google.cloud import storage
    except ImportError:
        print("google-cloud-storage not installed. Skipping automatic GCS download. Assumes GCS FUSE or pre-downloaded data.")
        return

    print(f"Connecting to GCS Bucket: {bucket_name}...")
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    os.makedirs(dest_dir, exist_ok=True)
    os.makedirs(os.path.join(dest_dir, "audio"), exist_ok=True)

    # 1. Download manifests
    for filename in ["metadata_processed.jsonl", "tts_filelist.txt"]:
        blob = bucket.blob(filename)
        dest_path = os.path.join(dest_dir, filename)
        if not os.path.exists(dest_path):
            print(f"Downloading {filename}...")
            blob.download_to_filename(dest_path)

    print("Staging complete. Ensure audio files are mounted via gcsfuse or copied locally.")

def main():
    parser = argparse.ArgumentParser(description="Kick start training of the WAXAL Hausa TTS model on a GPU instance.")
    parser.add_argument("--bucket", type=str, default="hausa-ai-waxal-studio-980910821-5b814", help="GCS bucket name")
    parser.add_argument("--data-dir", type=str, default="waxal_hausa", help="Local directory for dataset")
    args = parser.parse_args()

    print("====================================================")
    print("      WAXAL HAUSA TTS MODEL TRAINING PREPARATION    ")
    print("====================================================\n")

    # Step 1: Stage manifests from GCS
    download_data_from_gcs(args.bucket, args.data_dir)

    # Step 2: Initialize Config
    config = setup_training_config(args.bucket, args.data_dir)
    
    if config:
        print("\nModel configuration generated successfully!")
        print(f"Ready to train VITS multi-speaker model on WAXAL Hausa data.")
        print(f"Output directory: {config.output_path}")
        print("\nTo start training on your GPU instance, execute:")
        print("---------------------------------------------")
        print(f"python -m TTS.bin.train_tts --config_path {args.data_dir}/config.json")
        
        # Save config.json
        config_path = os.path.join(args.data_dir, "config.json")
        config.save_json(config_path)
        print(f"\nConfiguration saved to: {config_path}")

if __name__ == "__main__":
    main()
