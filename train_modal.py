import os
import modal

# Define the Modal App
app = modal.App("hausa-ai-tts-training")

# Persistent volume for model checkpoints
checkpoints_volume = modal.Volume.from_name("hausa-ai-checkpoints", create_if_missing=True)

# Build custom container image with Coqui-TTS and audio libraries
training_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "libsndfile1", "espeak-ng", "ffmpeg", "build-essential", "python3-dev")
    .pip_install(
        "coqui-tts==0.22.1",
        "torch==2.1.2",
        "torchaudio==2.1.2",
    )
    .add_local_dir(
        os.path.join(os.path.dirname(__file__), "waxal_hausa"),
        remote_path="/src/waxal_hausa"
    )
)

# Custom dataset formatter for the WAXAL Hausa dataset with duration and MAS length filtering
def waxal_formatter(root_path, meta_file, **kwargs):
    """
    Parses the staged tts_filelist.txt.
    Format of each line:
    audio/filename.mp3|normalized_plain_text|tone_marked_text
    """
    import torchaudio
    txt_file = os.path.join(root_path, meta_file)
    items = []
    skipped_long = 0
    skipped_short = 0
    skipped_error = 0
    total_checked = 0
    with open(txt_file, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) >= 3:
                rel_path = parts[0]       # e.g., "audio/Hausa_M4_001_0020.mp3"
                tone_text = parts[2]      # Use tone-marked text for accurate prosody
                
                # Extract speaker ID (e.g. "M4" or "F1") from filename
                filename = os.path.basename(rel_path)
                subparts = filename.split("_")
                speaker_id = subparts[1] if len(subparts) >= 3 else "default"
                
                full_audio_path = os.path.join(root_path, rel_path)
                total_checked += 1
                
                try:
                    info = torchaudio.info(full_audio_path)
                    duration = info.num_frames / info.sample_rate
                    
                    # 1. Filter out long files to prevent GPU OOM
                    if duration > 10.0:
                        skipped_long += 1
                        continue
                    
                    # 2. Filter out extremely short audio clips
                    if duration < 1.0:
                        skipped_short += 1
                        continue
                    
                    # 3. Filter out clips where audio spectrogram frames are too short relative to text length
                    # to prevent Monotonic Alignment Search (MAS) IndexError.
                    # hop_length is 256. Spectrogram length = info.num_frames // 256.
                    spectrogram_len = info.num_frames // 256
                    text_len = len(tone_text)
                    if spectrogram_len <= text_len + 25:
                        skipped_short += 1
                        continue
                        
                except Exception as e:
                    skipped_error += 1
                    if skipped_error <= 5:
                        print(f"[Warning] Failed to read {full_audio_path}: {e}")
                    continue
                
                items.append({
                    "text": tone_text,
                    "audio_file": full_audio_path,
                    "speaker_name": speaker_id,
                    "root_path": root_path
                })
    print(f"[waxal_formatter] Checked {total_checked} files. Kept {len(items)} files. Skipped {skipped_long} files (>10s), {skipped_short} files (too short/mismatch). Errors {skipped_error}.")
    return items



@app.function(
    image=training_image,
    gpu="A10G",           # Highly cost-effective serverless GPU (~$1.10/hour)
    timeout=72000,        # 20 hours timeout limit
    volumes={"/checkpoints": checkpoints_volume}
)
def train():
    print("[Modal Train] Starting VITS Multi-Speaker training setup...")
    
    from TTS.tts.configs.vits_config import VitsConfig
    from TTS.tts.datasets import load_tts_samples
    from TTS.tts.models.vits import Vits
    from trainer import Trainer, TrainerArgs
    
    # 2. Configure VITS model for Hausa phonology
    hausa_letters = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        "ɓɗƙƴƁƊƘƳ"
        "́̀"  # High and Low tone markers
    )
    
    from TTS.tts.configs.shared_configs import CharactersConfig, BaseAudioConfig

    characters_config = CharactersConfig(
        characters_class="TTS.tts.models.vits.VitsCharacters",
        characters=hausa_letters,
        punctuations=" .,!?;:-",
        pad="<PAD>",
        eos="<EOS>",
        bos="<BOS>",
        blank="<BLNK>",
    )

    audio_config = BaseAudioConfig(
        num_mels=80,
        fft_size=1024,
        hop_length=256,
        win_length=1024,
        sample_rate=24000,   # 24kHz target sample rate
        resample=True,
        preemphasis=0.97,
        ref_level_db=20,
        power=1.5,
        griffin_lim_iters=60,
    )

    config = VitsConfig(
        audio=audio_config,
        run_name="waxal_hausa_vits_v1",
        batch_size=8,
        eval_batch_size=4,
        mixed_precision=True,
        num_loader_workers=2,
        num_eval_loader_workers=2,
        run_eval=True,
        epochs=1000,
        text_cleaner="multilingual_cleaners",
        use_phonemes=False,      # Direct character sequence modeling
        characters=characters_config,
        use_speaker_embedding=True, # Enable multi-speaker mode
        lr_gen=2e-4,
        lr_disc=2e-4,
        save_step=1000,
        save_n_checkpoints=5,
        output_path="/checkpoints", # Persisted directly to Volume
    )

    restore_path = os.getenv("VITS_RESTORE_PATH", "").strip()
    if restore_path:
        config.restore_path = restore_path
        print(f"[Modal Train] Resuming from checkpoint: {restore_path}")
    
    from TTS.tts.configs.shared_configs import BaseDatasetConfig

    dataset_config = BaseDatasetConfig(
        formatter="waxal",
        dataset_name="waxal_hausa",
        path="/src/waxal_hausa",
        meta_file_train="tts_filelist.txt",
        meta_file_val="",
    )
    config.datasets = [dataset_config]
    
    # 3. Load samples & divide train/eval split
    print("[Modal Train] Loading and formatting dataset samples...")
    train_samples, eval_samples = load_tts_samples(
        config.datasets,
        eval_split=True,
        formatter=waxal_formatter,
        eval_split_max_size=16,
        eval_split_size=0.01,
    )
    print(f"[Modal Train] Loaded {len(train_samples)} training samples.")
    
    # 4. Initialize model and fit the trainer
    print("[Modal Train] Initializing VITS model...")
    model = Vits.init_from_config(config)
    
    print("[Modal Train] Starting model fitting...")
    trainer = Trainer(
        TrainerArgs(),
        config,
        output_path="/checkpoints",
        model=model,
        train_samples=train_samples,
        eval_samples=eval_samples,
    )
    trainer.fit()
    print("[Modal Train] Training completed successfully!")


@app.local_entrypoint()
def main():
    # Blocks until training finishes; checkpoints persist on Modal Volume.
    train.remote()
