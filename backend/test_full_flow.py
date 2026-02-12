import asyncio
import numpy as np
import os
import sys

# Ensure backend is in path
sys.path.append(os.getcwd())

from app.audio.processor import AudioProcessor
from app.services.sarvam_client import SarvamClient
from app.audio.buffer import AudioSyncBuffer

async def test_flow():
    print("🚀 Starting Full Flow Test...")
    
    # 1. Test Audio Processor Init (VAD Load)
    print("⏳ Initializing AudioProcessor...")
    try:
        processor = AudioProcessor(
            browser_rate=44100,
            target_rate=16000,
            vad_threshold=0.5
        )
        print("✅ AudioProcessor initialized.")
    except Exception as e:
        print(f"❌ AudioProcessor Init Failed: {e}")
        return

    # 2. Test Sarvam Connection
    print("⏳ Connecting to Sarvam...")
    sarvam = SarvamClient()
    try:
        await sarvam.start()
        print("✅ Sarvam Connected.")
    except Exception as e:
        print(f"❌ Sarvam Connection Failed: {e}")
        return

    # 3. Test Audio Processing Loop
    print("⏳ Processing dummy audio...")
    sync = AudioSyncBuffer()
    sync.start()

    # Generate 1 second of dummy audio (silence + noise)
    # 44100 samples, Int16
    dummy_audio = np.random.randint(-1000, 1000, 44100, dtype=np.int16).tobytes()
    
    # Chunk it like the browser (4096 samples per chunk approx)
    chunk_size = 8192 # bytes (4096 * 2)
    
    try:
        for i in range(0, len(dummy_audio), chunk_size):
            chunk = dummy_audio[i:i+chunk_size]
            
            # Resample
            resampled = processor.resample_chunk(chunk)
            sync.record_samples(len(resampled))
            
            # VAD
            speech_chunks = processor.process_with_vad(resampled)
            print(f"   Chunk {i//chunk_size}: {len(speech_chunks)} speech segments found.")
            
            # Send to Sarvam (Simulated)
            for speech, prob in speech_chunks:
                print("      Sending speech chunk...")
                await sarvam.send_audio_chunk(speech.tobytes())
                print("      ✅ Chunk sent.")
        
        # Force a send to verify API
        print("⚡ Forcing a manual chunk send to verify API...")
        dummy_chunk = np.zeros(1024, dtype=np.int16).tobytes()
        await sarvam.send_audio_chunk(dummy_chunk)
        print("✅ Manual chunk accepted.")

        print("✅ Audio processing loop finished.")

    except Exception as e:
        print(f"❌ Processing Loop Failed: {e}")
    finally:
        await sarvam.close()
        print("✅ Cleanup done.")

if __name__ == "__main__":
    asyncio.run(test_flow())
