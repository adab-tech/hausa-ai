import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class VitsEngine:
    """
    Sovereign VITS ONNX Inference Engine for Hausa TTS.
    
    This service loads the custom trained VITS model exported to ONNX format
    and runs local inference without external API dependencies.
    """
    def __init__(self, model_dir: Optional[str] = None):
        self.root_dir = Path(__file__).resolve().parent.parent.parent
        self.model_dir = Path(model_dir) if model_dir else self.root_dir / "models" / "vits"
        self.model_path = self.model_dir / "best_model.onnx"
        self.config_path = self.model_dir / "config.json"
        
        self.session = None
        self.config = {}
        self.characters = []
        self.char_to_id = {}
        
        # Try to initialize the session if the model exists
        if self.model_path.exists():
            self.initialize()
            
    def initialize(self) -> bool:
        """Initialize the ONNX Runtime session and load model configuration."""
        try:
            import onnxruntime as ort
            import json
            
            logger.info("Initializing Sovereign VITS ONNX model from: %s", self.model_path)
            
            # Load config.json to get vocabs and hyperparameters
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    
            # Set up character vocabulary mappings
            # VITS character mapping (default fallback if config doesn't have it)
            self.characters = self.config.get("characters", {}).get("characters", [
                "_", "~", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
                "n", "o", "p", "r", "s", "t", "u", "v", "w", "y", "z", "ɗ", "ɓ", "ƙ", "ƴ",
                "á", "à", "é", "è", "í", "ì", "ó", "ò", "ú", "ù", " ", "!", "?", ".", ",", "-"
            ])
            self.char_to_id = {char: idx for idx, char in enumerate(self.characters)}
            
            # Load the ONNX model
            self.session = ort.InferenceSession(str(self.model_path), providers=["CPUExecutionProvider"])
            logger.info("Sovereign VITS Engine initialized successfully.")
            return True
        except Exception as e:
            logger.error("Failed to initialize VITS ONNX Engine: %s", e)
            return False

    def text_to_sequence(self, text: str) -> list[int]:
        """Convert normalized text to a sequence of character token IDs."""
        sequence = []
        for char in text.lower():
            if char in self.char_to_id:
                sequence.append(self.char_to_id[char])
            else:
                # Discard characters not in vocab
                continue
        return sequence

    def synthesize(self, text: str, speaker_id: int = 0) -> Optional[bytes]:
        """
        Synthesize speech from Hausa text using the custom VITS ONNX model.
        
        Returns:
            bytes: Raw PCM-16 audio data, or None if the engine is not initialized.
        """
        if not self.session:
            if self.model_path.exists():
                if not self.initialize():
                    return None
            else:
                return None
                
        try:
            import numpy as np
            
            # 1. Convert text to token sequence
            sequence = self.text_to_sequence(text)
            if not sequence:
                return None
                
            # Add blank tokens between characters if required by VITS config (add_blank = True)
            if self.config.get("add_blank", True):
                blank_id = self.char_to_id.get("_", 0)
                sequence_with_blanks = [blank_id]
                for item in sequence:
                    sequence_with_blanks.append(item)
                    sequence_with_blanks.append(blank_id)
                sequence = sequence_with_blanks
                
            x = np.array([sequence], dtype=np.int64)
            x_lengths = np.array([x.shape[1]], dtype=np.int64)
            sid = np.array([speaker_id], dtype=np.int64)
            
            # Hyperparameters for VITS generator
            noise_scale = np.array([0.667], dtype=np.float32)
            length_scale = np.array([1.0], dtype=np.float32)
            noise_scale_w = np.array([0.8], dtype=np.float32)
            
            # 2. Run ONNX Session
            inputs = {
                "input": x,
                "input_lengths": x_lengths,
                "sid": sid,
                "noise_scale": noise_scale,
                "length_scale": length_scale,
                "noise_scale_w": noise_scale_w
            }
            
            outputs = self.session.run(None, inputs)
            audio = outputs[0]  # Shape: (1, 1, audio_samples) or (1, audio_samples)
            
            # 3. Convert float32 audio array to raw PCM-16 LE bytes
            audio = audio.squeeze()
            clipped = np.clip(audio, -1.0, 1.0)
            pcm16 = (clipped * 32767).astype(np.int16).tobytes()
            
            return pcm16
        except Exception as e:
            logger.error("VITS Synthesis execution failed: %s", e)
            return None
