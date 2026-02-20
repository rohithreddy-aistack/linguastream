import base64
import aiohttp
from app.core.config import settings

class SarvamTTSService:
    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        self.url = "https://api.sarvam.ai/text-to-speech"
        # 'ritu' is one of the available female voices for the bulbul:v3 model.
        # Other options include: aditya, priya, neha, rahul, pooja, rohan, etc.
        self.speaker = "ritu"

    async def text_to_speech_stream(self, text: str, target_lang: str = "hi-IN"):
        """
        Converts text to speech using Sarvam API and returns an async iterator of raw PCM audio chunks.
        """
        if not text or not text.strip():
            return

        payload = {
            "inputs": [text],
            "target_language_code": target_lang,
            "speaker": self.speaker,
            "pace": 1.2,
            "speech_sample_rate": 16000,
            "enable_preprocessing": True,
            "model": "bulbul:v3"
        }

        headers = {
            "Content-Type": "application/json",
            "api-subscription-key": self.api_key
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        audios = data.get("audios", [])
                        if audios:
                            # Sarvam returns base64 encoded audio strings
                            base64_audio = audios[0]
                            audio_bytes = base64.b64decode(base64_audio)

                            # Sarvam returns a WAV file format.
                            # The frontend/backend expects raw PCM 16-bit 16kHz data,
                            # so we strip the standard 44-byte WAV header.
                            pcm_data = audio_bytes[44:]

                            # Yield audio in chunks to simulate a stream and maintain compatibility
                            chunk_size = 4096
                            for i in range(0, len(pcm_data), chunk_size):
                                chunk = pcm_data[i:i+chunk_size]

                                # PCM 16-bit must be even-sized (2 bytes per sample)
                                if len(chunk) % 2 != 0:
                                    chunk += b"\x00"  # Pad with silence to make it even

                                yield chunk
                    else:
                        error_text = await response.text()
                        print(f"❌ Sarvam TTS Error {response.status}: {error_text}")
        except Exception as e:
            print(f"❌ Sarvam TTS Exception: {e}")
