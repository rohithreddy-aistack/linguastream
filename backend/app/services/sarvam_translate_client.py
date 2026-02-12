import aiohttp
import json
from app.core.config import settings

class SarvamTranslateService:
    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        self.url = "https://api.sarvam.ai/translate" # Verify exact endpoint

    async def translate(self, text: str, source_lang: str = "en-IN", target_lang: str = "hi-IN") -> str:
        """
        Translates text from source to target language.
        """
        if not text or not text.strip():
            return ""

        payload = {
            "input": text,
            "source_language_code": source_lang,
            "target_language_code": target_lang,
            "speaker_gender": "Male", # Optional
            "mode": "formal", # Optional
            "model": "mayura:v1" # Or whatever the latest translate model is
        }
        
        headers = {
            "Content-Type": "application/json",
            "api-subscription-key": self.api_key
        }

        async with aiohttp.ClientSession() as session:
            try:
                # Correct endpoint from documentation
                async with session.post("https://api.sarvam.ai/translate", json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("translated_text", "")
                    else:
                        error_text = await response.text()
                        print(f"❌ Sarvam Translate Error {response.status}: {error_text}")
                        return ""
            except Exception as e:
                print(f"❌ Translation Request Failed: {e}")
                return ""
