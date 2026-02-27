import base64
import aiohttp
import asyncio
from typing import AsyncIterator
from app.core.config import settings

class SarvamTTSService:
    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        self.url = "https://api.sarvam.ai/text-to-speech"
        self.speaker = "ritu"

    async def text_to_speech_stream(self, text: str, target_lang: str = "hi-IN", session: aiohttp.ClientSession = None) -> AsyncIterator[bytes]:
        """
        Converts text to speech using Sarvam REST API (bulbul:v3).
        Accepts an external session for better performance.
        """
        if not text or not text.strip():
            return

        payload = {
            "inputs": [text],
            "target_language_code": target_lang,
            "speaker": self.speaker,
            "pace": 1.2,
            "speech_sample_rate": 24000, # Using 24kHz for quality
            "enable_preprocessing": True,
            "model": "bulbul:v3"
        }

        headers = {
            "Content-Type": "application/json",
            "api-subscription-key": self.api_key
        }

        # Use provided session or create a temporary one
        async def fetch(s):
            try:
                async with s.post(self.url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        audios = data.get("audios", [])
                        if audios:
                            # Sarvam returns base64 encoded audio strings
                            base64_audio = audios[0]
                            audio_bytes = base64.b64decode(base64_audio)

                            # bulbul:v3 returns a WAV file.
                            # We strip the 44-byte header to get raw PCM.
                            pcm_data = audio_bytes[44:]
                            return pcm_data
                    else:
                        error_text = await response.text()
                        print(f"❌ Sarvam TTS Error {response.status}: {error_text}")
            except Exception as e:
                print(f"❌ Sarvam TTS Exception: {e}")
            return None

        if session:
            pcm_data = await fetch(session)
        else:
            async with aiohttp.ClientSession() as new_session:
                pcm_data = await fetch(new_session)

        if pcm_data:
            # Yield in smaller chunks to mimic streaming interface
            chunk_size = 4096
            for i in range(0, len(pcm_data), chunk_size):
                chunk = pcm_data[i:i+chunk_size]
                if len(chunk) % 2 != 0:
                    chunk += b"\x00"
                yield chunk
