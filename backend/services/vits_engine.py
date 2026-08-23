import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Frontend Murya dial: 0..3 = Namiji (M1..M4), 4..7 = Mace (F1..F4)
FRONTEND_TO_WAXAL_SPEAKER = {
    0: "M1", 1: "M2", 2: "M3", 3: "M4",
    4: "F1", 5: "F2", 6: "F3", 7: "F4",
}

OUTPUT_SAMPLE_RATE = 24000  # audio router wraps PCM in a 24 kHz WAV header


class VitsEngine:
    """
    Sovereign VITS ONNX Inference Engine for Hausa TTS.

    Supports two model formats:
    - Piper (preferred): models/piper_hausa_waxal/model.onnx + model.onnx.json
      — the WAXAL multi-speaker voice fine-tuned 2026-07 (grapheme phonemes,
      42-symbol Hausa alphabet, 8 speakers, 22.05 kHz).
    - Legacy Coqui VITS: models/vits/best_model.onnx + config.json.

    Output is always raw PCM-16 LE at 24 kHz (resampled if needed).
    """

    def __init__(self, model_dir: Optional[str] = None):
        self.root_dir = Path(__file__).resolve().parent.parent.parent
        piper_dir = self.root_dir / "models" / "piper_hausa_waxal"
        legacy_dir = self.root_dir / "models" / "vits"

        # VITS_MODEL_DIR lets deployment point explicitly at the baked-in model,
        # since the container flattens the repo layout (backend/ -> /app) and the
        # repo-relative auto-detection below would otherwise miss it.
        env_dir = os.getenv("VITS_MODEL_DIR", "").strip()
        if model_dir:
            self.model_dir = Path(model_dir)
        elif env_dir:
            self.model_dir = Path(env_dir)
        elif (piper_dir / "model.onnx").exists():
            self.model_dir = piper_dir
        else:
            self.model_dir = legacy_dir

        if (self.model_dir / "model.onnx").exists():
            self.format = "piper"
            self.model_path = self.model_dir / "model.onnx"
            self.config_path = self.model_dir / "model.onnx.json"
        else:
            self.format = "coqui"
            self.model_path = self.model_dir / "best_model.onnx"
            self.config_path = self.model_dir / "config.json"

        self.session = None
        self.config = {}
        self.characters = []
        self.char_to_id = {}
        self.phoneme_id_map = {}
        self.speaker_id_map = {}
        self.native_sample_rate = OUTPUT_SAMPLE_RATE
        # Set once initialize() fails, so synthesize() can fail fast instead
        # of re-attempting the full (expensive) ONNX session init on every
        # single request while the model is broken.
        self._init_failed = False

        if self.model_path.exists():
            self.initialize()

    def initialize(self) -> bool:
        """Initialize the ONNX Runtime session and load model configuration."""
        try:
            import onnxruntime as ort
            import json

            logger.info("Initializing Sovereign VITS ONNX model (%s format) from: %s",
                        self.format, self.model_path)

            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)

            if self.format == "piper":
                # Piper config: phoneme_id_map maps each symbol -> [id, ...]
                self.phoneme_id_map = self.config.get("phoneme_id_map", {})
                self.speaker_id_map = self.config.get("speaker_id_map", {})
                self.native_sample_rate = (
                    self.config.get("audio", {}).get("sample_rate", 22050)
                )
            else:
                self._init_coqui_vocab()

            self.session = ort.InferenceSession(str(self.model_path), providers=["CPUExecutionProvider"])
            self.input_names = [i.name for i in self.session.get_inputs()]
            logger.info("Sovereign VITS Engine initialized (%s, %d Hz native, inputs: %s)",
                        self.format, self.native_sample_rate, self.input_names)
            self._init_failed = False
            return True
        except Exception as e:
            logger.error("Failed to initialize VITS ONNX Engine: %s", e)
            self._init_failed = True
            return False

    def _init_coqui_vocab(self):
        """Reconstruct vocabulary mapping exactly as Coqui-TTS's VitsCharacters does."""
        if "characters" in self.config:
            char_config = self.config["characters"]
            pad = char_config.get("pad", "<PAD>")
            bos = char_config.get("bos", "<BOS>")
            eos = char_config.get("eos", "<EOS>")
            blank = char_config.get("blank", "<BLNK>")
            characters = char_config.get("characters", "")
            punctuations = char_config.get("punctuations", "")

            self.characters = [pad, bos, eos, blank]
            unique_chars = list(set(characters))
            if char_config.get("is_sorted", True):
                unique_chars.sort()
            self.characters.extend(unique_chars)
            unique_puncs = list(set(punctuations))
            if char_config.get("is_sorted", True):
                unique_puncs.sort()
            self.characters.extend(unique_puncs)
        else:
            self.characters = [
                "_", "~", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
                "n", "o", "p", "r", "s", "t", "u", "v", "w", "y", "z", "ɗ", "ɓ", "ƙ", "ƴ",
                "á", "à", "é", "è", "í", "ì", "ó", "ò", "ú", "ù", " ", "!", "?", ".", ",", "-"
            ]
        self.char_to_id = {char: idx for idx, char in enumerate(self.characters)}

    # ------------------------------------------------------------------
    # Tokenization
    # ------------------------------------------------------------------
    def text_to_sequence(self, text: str) -> list[int]:
        """Legacy Coqui path: convert text to character token IDs."""
        sequence = []
        for char in text:
            if char in self.char_to_id:
                sequence.append(self.char_to_id[char])
            elif char.lower() in self.char_to_id:
                sequence.append(self.char_to_id[char.lower()])
            else:
                continue
        return sequence

    def _piper_text_to_ids(self, text: str) -> list[int]:
        """Piper grapheme path: casefolded chars -> ids via phoneme_id_map,
        interspersed with pad, wrapped in bos/eos (^ _ c1 c2 _ ... $).

        NFD (not NFC) so tone-marked vowels decompose into base vowel +
        combining mark — the mark is skipped but the vowel survives. NFC
        would compose 'a'+acute into 'á', which is not in the map, and the
        whole vowel would vanish. Hooked letters (ɓ ɗ ƙ ƴ) have no
        decomposition and pass through unchanged."""
        import unicodedata

        text = unicodedata.normalize("NFD", text).casefold()
        for a, b in {"’": "'", "‘": "'", "`": "'", "–": "-", "—": "-", "\xa0": " "}.items():
            text = text.replace(a, b)

        pad = self.phoneme_id_map.get("_", [0])
        bos = self.phoneme_id_map.get("^", [1])
        eos = self.phoneme_id_map.get("$", [2])

        ids: list[int] = list(bos) + list(pad)
        for ch in text:
            mapped = self.phoneme_id_map.get(ch)
            if mapped is None:
                continue  # tone marks / unknown symbols are simply skipped
            ids.extend(mapped)
            ids.extend(pad)
        ids.extend(eos)
        return ids

    def _resolve_speaker(self, speaker_id: int) -> int:
        """Map frontend Murya dial index (0..7) to the model's speaker id."""
        if self.format != "piper" or not self.speaker_id_map:
            return speaker_id
        name = FRONTEND_TO_WAXAL_SPEAKER.get(speaker_id)
        if name is not None and name in self.speaker_id_map:
            return int(self.speaker_id_map[name])
        return max(0, min(speaker_id, len(self.speaker_id_map) - 1))

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------
    def synthesize(
        self,
        text: str,
        speaker_id: int = 0,
        length_scale: Optional[float] = None,
        noise_scale: Optional[float] = None,
        noise_w: Optional[float] = None,
    ) -> Optional[bytes]:
        """
        Synthesize speech from Hausa text using the custom ONNX model.

        length_scale/noise_scale/noise_w, when given, override the
        VITS_LENGTH_SCALE/VITS_NOISE_SCALE/VITS_NOISE_W env vars (which in
        turn override the model config's own defaults) — lets pacing/clarity
        be A/B tested per-request via /api/tts query params.

        Returns:
            bytes: Raw PCM-16 audio data at 24 kHz, or None if unavailable.
        """
        if not self.session:
            # Previously this re-attempted the full ONNX session init (a real
            # cost -- loading the model file, parsing config) on EVERY call
            # after the first failure, instead of remembering the model is
            # broken. Fail fast once initialize() has already failed once.
            if self._init_failed:
                return None
            if self.model_path.exists():
                if not self.initialize():
                    return None
            else:
                return None

        try:
            import numpy as np

            # 1. Convert text to token sequence
            if self.format == "piper":
                sequence = self._piper_text_to_ids(text)
                if len(sequence) <= 3:  # only bos/pad/eos -> nothing to say
                    return None
            else:
                sequence = self.text_to_sequence(text)
                if not sequence:
                    return None
                if self.config.get("add_blank", True):
                    blank_id = self.char_to_id.get("_", 0)
                    sequence_with_blanks = [blank_id]
                    for item in sequence:
                        sequence_with_blanks.append(item)
                        sequence_with_blanks.append(blank_id)
                    sequence = sequence_with_blanks

            x = np.array([sequence], dtype=np.int64)
            x_lengths = np.array([x.shape[1]], dtype=np.int64)

            # 2. Inference params (piper config carries its own defaults).
            # Env vars let pacing/clarity be tuned (e.g. to fix rushed
            # speech) without touching the baked-in model config or
            # redeploying code — just set the Fly secret/env and restart.
            # length_scale > 1.0 = slower; noise_scale/noise_w lower =
            # less stochastic variation (can read as more "even" pacing).
            inference = self.config.get("inference", {})
            if noise_scale is None:
                noise_scale = float(os.getenv("VITS_NOISE_SCALE", inference.get("noise_scale", 0.667)))
            if length_scale is None:
                length_scale = float(os.getenv("VITS_LENGTH_SCALE", inference.get("length_scale", 1.0)))
            if noise_w is None:
                noise_w = float(os.getenv("VITS_NOISE_W", inference.get("noise_w", 0.8)))

            inputs = {}
            if "input" in self.input_names:
                inputs["input"] = x
            if "input_lengths" in self.input_names:
                inputs["input_lengths"] = x_lengths
            if "scales" in self.input_names:
                inputs["scales"] = np.array([noise_scale, length_scale, noise_w], dtype=np.float32)
            else:
                if "noise_scale" in self.input_names:
                    inputs["noise_scale"] = np.array([noise_scale], dtype=np.float32)
                if "length_scale" in self.input_names:
                    inputs["length_scale"] = np.array([length_scale], dtype=np.float32)
                if "noise_scale_w" in self.input_names:
                    inputs["noise_scale_w"] = np.array([noise_w], dtype=np.float32)
            if "sid" in self.input_names:
                inputs["sid"] = np.array([self._resolve_speaker(speaker_id)], dtype=np.int64)

            outputs = self.session.run(None, inputs)
            audio = np.asarray(outputs[0]).squeeze().astype(np.float32)

            # 3. Resample to the router's 24 kHz contract if needed
            if self.native_sample_rate != OUTPUT_SAMPLE_RATE and audio.size > 1:
                duration = audio.size / float(self.native_sample_rate)
                n_out = int(round(duration * OUTPUT_SAMPLE_RATE))
                t_in = np.linspace(0.0, duration, num=audio.size, endpoint=False)
                t_out = np.linspace(0.0, duration, num=n_out, endpoint=False)
                audio = np.interp(t_out, t_in, audio).astype(np.float32)

            clipped = np.clip(audio, -1.0, 1.0)
            pcm16 = (clipped * 32767).astype(np.int16).tobytes()
            return pcm16
        except Exception as e:
            logger.error("VITS Synthesis execution failed: %s", e)
            return None
