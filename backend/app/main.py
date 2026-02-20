import wave
import asyncio
import json
import uvicorn
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.audio.processor import AudioProcessor
from app.services.deepgram_client import DeepgramService
from app.services.sarvam_translate_client import SarvamTranslateService
from app.services.sarvam_tts_client import SarvamTTSService

app = FastAPI()

# --- Configuration ---
OUTPUT_FILE = "test_capture_speech_only.wav"
BROWSER_RATE = 44100
TARGET_RATE = 16000
VAD_THRESHOLD = 0.5

# Initialize Audio Processor (Keep VAD for local filtering if needed, or rely on Deepgram's VAD)
# We will still use it for Resampling.
processor = AudioProcessor(
    browser_rate=BROWSER_RATE,
    target_rate=TARGET_RATE,
    vad_threshold=VAD_THRESHOLD
)

@app.get("/")
def home():
    return {"status": "LinguaStream Backend is Running (3-Stage Pipeline)", "vad_loaded": True}

@app.websocket("/ws/stream")
async def audio_stream(websocket: WebSocket, lang: str = "hi-IN"):
    await websocket.accept()
    print(f"✅ Client Connected (Stream) | Target Lang: {lang}")

    # --- Initialize Services ---
    deepgram_service = DeepgramService()
    translator_service = SarvamTranslateService()
    tts_service = SarvamTTSService()

    # --- Pipeline Logic ---
    transcript_queue = asyncio.Queue()

    async def process_queue():
        while True:
            transcript_text = await transcript_queue.get()
            try:
                # --- Stage 2: Translation (Sarvam) ---
                print(f"🔄 [Translate] Translating to {lang}: '{transcript_text}'...")
                target_text = await translator_service.translate(transcript_text, target_lang=lang)

                if target_text:
                    print(f"🇮🇳 [Translate] Target ({lang}): {target_text}")

                    # Send Target transcript to UI
                    try:
                        await websocket.send_json({
                            "type": "transcript",
                            "text": target_text,
                            "lang": lang,
                            "is_final": True
                        })
                        print(f"📤 Sent {lang} transcript to UI: {target_text}")
                    except Exception as e:
                        print(f"⚠️ Failed to send {lang} transcript: {e}")

                    # --- Stage 3: TTS (Sarvam) ---
                    print(f"🗣️ [TTS] Generating Audio for: '{target_text}'...")

                    try:
                        chunk_count = 0
                        async for audio_chunk in tts_service.text_to_speech_stream(target_text, target_lang=lang):
                            if audio_chunk:
                                await websocket.send_bytes(audio_chunk)
                                chunk_count += 1

                        if chunk_count > 0:
                            print(f"📤 Sent {chunk_count} TTS audio chunks to UI")
                    except Exception as e:
                        print(f"⚠️ Failed to stream TTS audio: {e}")
            finally:
                transcript_queue.task_done()

    processing_task = asyncio.create_task(process_queue())

    async def on_transcript_received(transcript_text, is_final):
        """
        Callback when Deepgram returns a transcript (Stage 1).
        Triggers Stage 2 (Translation) and Stage 3 (TTS).
        """
        if not transcript_text:
            return

        print(f"🎤 [ASR] English: {transcript_text} (Final: {is_final})")

        # Only translate/dub if the sentence is final
        if is_final:
            await transcript_queue.put(transcript_text)

    # --- Start Deepgram ---
    await deepgram_service.connect(on_transcript_callback=on_transcript_received)

    # Open WAV file for debug recording
    with wave.open(OUTPUT_FILE, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2) # 16-bit
        wav_file.setframerate(TARGET_RATE)

        try:
            message_count = 0
            while True:
                # 1. Receive Raw Audio from Browser
                data = await websocket.receive_bytes()
                message_count += 1

                if message_count % 100 == 0:
                    print(f"📥 Received {message_count} audio chunks from client...")

                # 2. Resample (44.1k -> 16k)
                audio_resampled = processor.resample_chunk(data)

                # Write to local file (debug)
                wav_file.writeframes(audio_resampled.tobytes())

                # 3. Send to Deepgram (Stage 1 Input)
                await deepgram_service.send_audio(audio_resampled.tobytes())

        except WebSocketDisconnect:
            print(f"\n❌ Client Disconnected.")
        except Exception as e:
            print(f"\n⚠️ Error: {e}")
        finally:
            processing_task.cancel()
            await deepgram_service.close()

@app.websocket("/ws/loopback")
async def loopback_stream(websocket: WebSocket):
    await websocket.accept()
    print("✅ Client Connected (Loopback)")
    try:
        while True:
            data = await websocket.receive_bytes()
            # Immediately send back for latency testing
            await websocket.send_bytes(data)
    except WebSocketDisconnect:
        print("❌ Loopback Client Disconnected")
    except Exception as e:
        print(f"⚠️ Loopback Error: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
