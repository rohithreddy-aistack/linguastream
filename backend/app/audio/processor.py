import torch
import numpy as np
import math
from scipy.signal import resample_poly

class AudioProcessor:
    def __init__(self, browser_rate=44100, target_rate=16000, vad_threshold=0.5):
        self.browser_rate = browser_rate
        self.target_rate = target_rate
        self.vad_threshold = vad_threshold
        self.vad_window_size = 512  # Silero VAD requires exactly 512 samples at 16kHz
        
        # Calculate resampling factors
        gcd = math.gcd(self.browser_rate, self.target_rate)
        self.up = self.target_rate // gcd
        self.down = self.browser_rate // gcd
        
        print(f"🔄 Resampling: {self.browser_rate}Hz -> {self.target_rate}Hz (Factor: {self.up}/{self.down})")

        print("⏳ Loading VAD Model...")
        self.model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            trust_repo=True
        )
        self.vad_iterator = utils[3] # VADIterator not used here but could be useful later
        print("✅ VAD Model Loaded")
        
        self.vad_buffer = np.array([], dtype=np.int16)

    def resample_chunk(self, raw_bytes: bytes) -> np.ndarray:
        """
        Convert bytes to Int16 Numpy array and resample to target rate.
        """
        # Convert bytes to Int16
        audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)

        # Resample using polyphase filtering
        audio_resampled = resample_poly(audio_int16, self.up, self.down).astype(np.int16)

        return audio_resampled

    def process_with_vad(self, audio_int16: np.ndarray):
        """
        Add audio to buffer and return speech chunks.
        """
        self.vad_buffer = np.concatenate((self.vad_buffer, audio_int16))
        
        speech_chunks = []
        
        while len(self.vad_buffer) >= self.vad_window_size:
            # Extract chunk
            chunk = self.vad_buffer[:self.vad_window_size]
            self.vad_buffer = self.vad_buffer[self.vad_window_size:]

            # Convert to Float32 for VAD (Normalize to -1.0 to 1.0)
            audio_float32 = chunk.astype(np.float32) / 32768.0

            # Convert numpy -> torch tensor
            tensor = torch.from_numpy(audio_float32)

            # Get speech confidence
            speech_prob = self.model(tensor, self.target_rate).item()

            if speech_prob > self.vad_threshold:
                speech_chunks.append((chunk, speech_prob))
                
        return speech_chunks
