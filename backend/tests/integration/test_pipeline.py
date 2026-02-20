import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from app.services.sarvam_translate_client import SarvamTranslateService
from app.services.sarvam_tts_client import SarvamTTSService

async def test_services():
    print('Testing Services Pipeline...')
    
    translator = SarvamTranslateService()
    test_text = 'This application has an inbuilt compiler.'
    translated = await translator.translate(test_text, target_lang='te-IN')
    print(f'EN: {test_text}')
    print(f'TE: {translated}')
    
    tts = SarvamTTSService()
    try:
        chunks = 0
        async for chunk in tts.text_to_speech_stream(translated, target_lang='te-IN'):
            chunks += 1
            if chunks == 1:
                print('First audio chunk received!')
        print(f'Total audio chunks received: {chunks}')
    except Exception as e:
        print(f'TTS Error: {e}')

if __name__ == '__main__':
    asyncio.run(test_services())
