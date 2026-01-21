import wave
import torch
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from scipy.signal import resample
import uvicorn

app = FastAPI()

# --- Configuration ---
OUTPUT_FILE = "test_capture_speech_only.wav"
BROWSER_RATE = 44100
TARGET_RATE = 16000
VAD_THRESHOLD = 0.5  # Confidence level (0.0 - 1.0)

# --- 1. Load Silero VAD Model (On Startup) ---
print("⏳ Loading VAD Model...")
model, utils = torch.hub.load(
    repo_or_dir='snakers4/silero-vad',
    model='silero_vad',
    force_reload=False,
    trust_repo=True
)
(get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils
print("✅ VAD Model Loaded")

# --- Helper Functions ---
def process_audio_chunk(raw_bytes: bytes):
    """
    1. Convert bytes to Int16 Numpy array
    2. Resample to 16kHz
    """
    # Convert bytes to Int16
    audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)

    # Resample (44100 -> 16000)
    # Calculate number of samples in new rate
    num_samples = int(len(audio_int16) * TARGET_RATE / BROWSER_RATE)
    audio_resampled = resample(audio_int16, num_samples).astype(np.int16)

    return audio_resampled

@app.get("/")
def home():
    return {"status": "LinguaStream Backend is Running", "vad_loaded": True}

@app.websocket("/ws/stream")
async def audio_stream(websocket: WebSocket):
    await websocket.accept()
    print("✅ Client Connected")

    # Buffer for VAD processing (holds 16kHz int16 samples)
    vad_buffer = np.array([], dtype=np.int16)
    VAD_WINDOW_SIZE = 512  # Silero VAD requires exactly 512 samples at 16kHz

    # Open WAV file for recording "Speech Only"
    with wave.open(OUTPUT_FILE, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2) # 16-bit
        wav_file.setframerate(TARGET_RATE)

        try:
            while True:
                # 1. Receive Raw Audio
                data = await websocket.receive_bytes()

                # 2. Process (Resample)
                audio_int16 = process_audio_chunk(data)

                # 3. Add to Buffer
                vad_buffer = np.concatenate((vad_buffer, audio_int16))

                # 4. Process in chunks of 512
                while len(vad_buffer) >= VAD_WINDOW_SIZE:
                    # Extract chunk
                    chunk = vad_buffer[:VAD_WINDOW_SIZE]
                    vad_buffer = vad_buffer[VAD_WINDOW_SIZE:]

                    # Convert to Float32 for VAD (Normalize to -1.0 to 1.0)
                    audio_float32 = chunk.astype(np.float32) / 32768.0

                    # Convert numpy -> torch tensor
                    tensor = torch.from_numpy(audio_float32)

                    # Get speech confidence (0.0 to 1.0)
                    speech_prob = model(tensor, TARGET_RATE).item()

                    # The Gate Logic
                    if speech_prob > VAD_THRESHOLD:
                        # ✅ Speech Detected: Save it
                        wav_file.writeframes(chunk.tobytes())
                        print(f"🗣️ Speech Detected ({speech_prob:.2f})")
                    else:
                        # ❌ Music/Silence: Drop it
                        pass

        except WebSocketDisconnect:
            print(f"\n❌ Client Disconnected. Saved speech to {OUTPUT_FILE}")
        except Exception as e:
            print(f"\n⚠️ Error: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
