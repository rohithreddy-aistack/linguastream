import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.deepgram_client import DeepgramService
from app.services.sarvam_translate_client import SarvamTranslateService
from app.services.elevenlabs_client import ElevenLabsService

async def test_services():
    print("🚀 Testing Services Pipeline...")

    # 1. Test Sarvam Translation
    print("\n--- Testing Sarvam Translate ---")
    sarvam = SarvamTranslateService()
    test_text = "Hello, how are you today?"
    translated = await sarvam.translate(test_text, target_lang="hi-IN")
    if translated:
        print(f"✅ Sarvam: '{test_text}' -> '{translated}'")
    else:
        print("❌ Sarvam Translation Failed (Check API Key)")

    # 2. Test ElevenLabs TTS
    if translated:
        print("\n--- Testing ElevenLabs TTS ---")
        eleven = ElevenLabsService()
        audio_bytes = await eleven.text_to_speech(translated)
        if audio_bytes:
            print(f"✅ ElevenLabs: Generated {len(audio_bytes)} bytes of audio")
            # Save to file for verification
            with open("test_tts_output.pcm", "wb") as f:
                f.write(audio_bytes)
            print("💾 Saved to test_tts_output.pcm")
        else:
            print("❌ ElevenLabs TTS Failed (Check API Key/Voice ID)")

    # 3. Test Deepgram Connection
    print("\n--- Testing Deepgram Connection ---")
    deepgram = DeepgramService()

    async def on_transcript(text, is_final):
        print(f"🎤 Deepgram Transcript: {text} (Final: {is_final})")

    try:
        # This will wait for connection
        await asyncio.wait_for(deepgram.connect(on_transcript), timeout=10.0)
        if deepgram.is_connected:
            print("✅ Deepgram Connected")
            await deepgram.close()
            print("✅ Deepgram Closed")
        else:
            print("❌ Deepgram Connection Failed")
    except Exception as e:
        print(f"❌ Deepgram Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_services())
