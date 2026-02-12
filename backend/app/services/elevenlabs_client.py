from elevenlabs import AsyncElevenLabs
from app.core.config import settings
import asyncio

class ElevenLabsService:
    def __init__(self):
        self.client = AsyncElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
        # 'Viraj' - Optimized for Indian accents and languages like Hindi
        self.voice_id = "FmBhnvP58BK0vz65OOj7" 

    async def text_to_speech_stream(self, text: str):
        """
        Converts text to speech and returns an async iterator of audio chunks.
        """
        if not text:
            return

        try:
            # Using eleven_multilingual_v2 for much better pronunciation of Indian languages
            audio_iterator = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id="eleven_multilingual_v2",
                output_format="pcm_16000"
            )
            
            remainder = b""
            async for chunk in audio_iterator:
                if remainder:
                    chunk = remainder + chunk
                    remainder = b""
                
                # PCM 16-bit must be even-sized (2 bytes per sample)
                if len(chunk) % 2 != 0:
                    remainder = chunk[-1:]
                    chunk = chunk[:-1]
                
                if chunk:
                    yield chunk
            
            if remainder:
                # This should rarely happen with TTS streams, but for safety:
                yield remainder + b"\x00" # Pad with silence to make it even

        except Exception as e:
            print(f"❌ ElevenLabs TTS Error: {e}")
