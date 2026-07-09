import json
from pathlib import Path

# Load config.json
config_path = Path("models/vits/config.json")
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

char_config = config["characters"]
pad = char_config["pad"]
bos = char_config["bos"]
eos = char_config["eos"]
blank = char_config["blank"]
characters = char_config["characters"]
punctuations = char_config["punctuations"]

# In Coqui-TTS, VitsCharacters builds the list as follows:
# pad, bos, eos, blank, then unique characters, then punctuations.
# If is_sorted is True, characters and punctuations are sorted.

char_list = [pad, bos, eos, blank]

# Characters
unique_chars = list(set(characters))
if char_config.get("is_sorted", True):
    unique_chars.sort()
char_list.extend(unique_chars)

# Punctuations
unique_puncs = list(set(punctuations))
if char_config.get("is_sorted", True):
    unique_puncs.sort()
char_list.extend(unique_puncs)

print(f"Num chars compiled: {len(char_list)}")
print("Character List:")
print(json.dumps(char_list, ensure_ascii=False))
