import sys
import torch
import transformers.pytorch_utils
if not hasattr(transformers.pytorch_utils, "isin_mps_friendly"):
    def isin_mps_friendly(elements, test_elements):
        return torch.isin(elements, test_elements)
    transformers.pytorch_utils.isin_mps_friendly = isin_mps_friendly
    print("[PATCH] Successfully monkey-patched transformers.pytorch_utils.isin_mps_friendly")

from TTS.tts.datasets import register_formatter
import TTS.tts.datasets.dataset
import torchaudio

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
print("[PATCH] Successfully registered waxal_hausa formatter")

# Monkey-patch get_audio_size to bypass broken torchcodec library
def patched_get_audio_size(audiopath):
    import subprocess
    if not isinstance(audiopath, str):
        audiopath = str(audiopath)
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-select_streams", "a:0", 
        "-show_entries", "stream=duration,sample_rate", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        audiopath
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = res.stdout.strip().split()
        if len(lines) >= 2:
            sample_rate = int(lines[0])
            duration = float(lines[1])
            return int(sample_rate * duration)
    except Exception:
        pass
    return 160000

TTS.tts.datasets.dataset.get_audio_size = patched_get_audio_size
print("[PATCH] Successfully monkey-patched TTS.tts.datasets.dataset.get_audio_size to use ffprobe")

# Monkey-patch torchaudio.load to bypass broken torchcodec library
def patched_load(filepath, channels_first=True, **kwargs):
    import subprocess
    if not isinstance(filepath, str):
        filepath = str(filepath)
    cmd_probe = [
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate,channels",
        "-of", "default=noprint_wrappers=1:nokey=1", filepath
    ]
    res_probe = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
    lines = res_probe.stdout.strip().split()
    sample_rate = int(lines[0])
    channels = int(lines[1])
    
    cmd_conv = [
        "ffmpeg", "-v", "error", "-y", "-i", filepath,
        "-f", "f32le", "-acodec", "pcm_f32le", "-"
    ]
    res_conv = subprocess.run(cmd_conv, capture_output=True, check=True)
    raw_data = res_conv.stdout
    
    waveform = torch.frombuffer(raw_data, dtype=torch.float32).clone()
    waveform = waveform.reshape(-1, channels)
    if channels_first:
        waveform = waveform.t()
        
    return waveform, sample_rate

torchaudio.load = patched_load
print("[PATCH] Successfully monkey-patched torchaudio.load to use ffmpeg")

# Monkey-patch base_tts to correctly compute embedding size when add_blank is True
import TTS.tts.models.base_tts
original_set_model_args = TTS.tts.models.base_tts.BaseTTS._set_model_args

def patched_set_model_args(self, config):
    original_set_model_args(self, config)
    if config.add_blank and hasattr(self, 'tokenizer') and self.tokenizer is not None:
        num_chars = self.tokenizer.characters.num_chars + 1
        self.config.model_args.num_chars = num_chars
        self.config.num_chars = num_chars
        self.args.num_chars = num_chars
        print(f"[PATCH] Adjusted num_chars to {num_chars} because add_blank is True")

TTS.tts.models.base_tts.BaseTTS._set_model_args = patched_set_model_args
print("[PATCH] Successfully monkey-patched BaseTTS._set_model_args to handle add_blank")

# Monkey-patch load_config in train_tts to resolve characters deserialization issues
import TTS.bin.train_tts
from TTS.tts.configs.shared_configs import CharactersConfig, BaseDatasetConfig

original_load_config = TTS.bin.train_tts.load_config

def patched_load_config(config_path):
    config = original_load_config(config_path)
    
    hausa_characters = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        "ɓɗƙƴƁƊƘƳ"
        "́̀"
    )
    hausa_punctuations = " .,!?;:-"
    
    config.characters = CharactersConfig(
        characters=hausa_characters,
        punctuations=hausa_punctuations
    )
    
    config.datasets = [
        BaseDatasetConfig(
            formatter="waxal_hausa",
            dataset_name="waxal",
            path=config.datasets[0].path if config.datasets else "waxal_hausa",
            meta_file_train="tts_filelist.txt"
        )
    ]
    
    print("[PATCH] Successfully intercepted config load and patched characters/datasets configs")
    return config

TTS.bin.train_tts.load_config = patched_load_config

from TTS.bin.train_tts import main
if __name__ == "__main__":
    main()
