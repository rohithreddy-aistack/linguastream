import asyncio
import os
import websockets

api_key = os.environ.get("SARVAM_API_KEY")
print("Key length:", len(api_key))

async def test():
    uri = "wss://api.sarvam.ai/speech-to-text-translate"
    try:
        async with websockets.connect(uri, additional_headers={"api-subscription-key": api_key}) as websocket:
            print("Connected!")
            await websocket.close()
    except Exception as e:
        print("Error:", type(e), e)

asyncio.run(test())
