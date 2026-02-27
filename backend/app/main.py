import wave
import asyncio
import json
import uvicorn
import time
import aiohttp
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

# Initialize Audio Processor
processor = AudioProcessor(
    browser_rate=BROWSER_RATE,
    target_rate=TARGET_RATE,
    vad_threshold=VAD_THRESHOLD
)

@app.get("/")
def home():
    return {"status": "LinguaStream Backend is Running (3-Stage Optimized)", "vad_loaded": True}

class OrderedAudioStreamer:
    """
    Ensures that audio chunks from parallel sentence processing
    are streamed to the WebSocket in correct order.
    """
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.next_index = 0
        self.active_queues = {} # index -> asyncio.Queue
        self.lock = asyncio.Lock()
        self._stream_task = asyncio.create_task(self._stream_loop())

    async def _stream_loop(self):
        """Background task that pulls from queues in order."""
        try:
            while True:
                # Wait for the next queue to exist
                while self.next_index not in self.active_queues:
                    await asyncio.sleep(0.05)
                
                queue = self.active_queues[self.next_index]
                print(f"📡 [Streamer] Now streaming sentence {self.next_index}")
                
                while True:
                    chunk = await queue.get()
                    if chunk is None: # Sentinel for end of sentence
                        break
                    await self.websocket.send_bytes(chunk)
                
                # Cleanup and move to next
                async with self.lock:
                    del self.active_queues[self.next_index]
                    self.next_index += 1
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"❌ [Streamer] Error: {e}")

    async def get_queue(self, index: int) -> asyncio.Queue:
        async with self.lock:
            if index not in self.active_queues:
                self.active_queues[index] = asyncio.Queue()
            return self.active_queues[index]
    
    def cancel(self):
        self._stream_task.cancel()

@app.websocket("/ws/stream")
async def audio_stream(websocket: WebSocket, lang: str = "hi-IN"):
    await websocket.accept()
    print(f"✅ Client Connected (Stream) | Target Lang: {lang}")

    # --- Initialize Services ---
    deepgram_service = DeepgramService()
    translator_service = SarvamTranslateService()
    tts_service = SarvamTTSService()
    
    # Shared HTTP session for all translation requests in this socket
    http_session = aiohttp.ClientSession()
    
    # Ordered Streamer
    audio_streamer = OrderedAudioStreamer(websocket)
    
    # Counter for preserving order
    sentence_counter = 0

    async def process_sentence(index: int, transcript_text: str):
        """
        Stage 2 (Translate) and Stage 3 (TTS) for a single sentence.
        Runs in parallel with other sentences.
        """
        queue = await audio_streamer.get_queue(index)
        try:
            # --- Stage 2: Translation (Sarvam) ---
            start_translate = time.time()
            target_text = await translator_service.translate(
                transcript_text, 
                target_lang=lang, 
                session=http_session
            )
            print(f"🔄 [S{index}] Translate took {time.time()-start_translate:.2f}s")

            if target_text:
                # Send Target transcript to UI
                try:
                    await websocket.send_json({
                        "type": "transcript",
                        "text": target_text,
                        "lang": lang,
                        "is_final": True
                    })
                except Exception:
                    pass

                # --- Stage 3: TTS (Sarvam) ---
                start_tts = time.time()
                first_byte_time = None
                
                async for audio_chunk in tts_service.text_to_speech_stream(target_text, target_lang=lang, session=http_session):
                    if first_byte_time is None:
                        first_byte_time = time.time()
                        print(f"⚡ [S{index}] First byte of TTS in {first_byte_time-start_tts:.2f}s")
                    
                    if audio_chunk:
                        await queue.put(audio_chunk)
                
                print(f"🗣️ [S{index}] TTS Gen Finished. Total time: {time.time()-start_tts:.2f}s")
                
        except Exception as e:
            print(f"⚠️ [S{index}] Error: {e}")
        finally:
            # Signal end of sentence audio
            await queue.put(None)

    async def on_transcript_received(transcript_text, is_final):
        nonlocal sentence_counter
        if is_final and transcript_text:
            print(f"🎤 [ASR] S{sentence_counter}: {transcript_text}")
            # Launch parallel task for this sentence
            asyncio.create_task(process_sentence(sentence_counter, transcript_text))
            sentence_counter += 1

    # --- Start Deepgram ---
    await deepgram_service.connect(on_transcript_callback=on_transcript_received)

    # Open WAV file for debug recording
    with wave.open(OUTPUT_FILE, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2) # 16-bit
        wav_file.setframerate(TARGET_RATE)

        try:
            while True:
                data = await websocket.receive_bytes()
                audio_resampled = processor.resample_chunk(data)
                wav_file.writeframes(audio_resampled.tobytes())
                await deepgram_service.send_audio(audio_resampled.tobytes())

        except WebSocketDisconnect:
            print(f"\n❌ Client Disconnected.")
        except Exception as e:
            print(f"\n⚠️ Error: {e}")
        finally:
            audio_streamer.cancel()
            await http_session.close()
            await deepgram_service.close()

@app.websocket("/ws/loopback")
async def loopback_stream(websocket: WebSocket):
    await websocket.accept()
    print("✅ Client Connected (Loopback)")
    try:
        while True:
            data = await websocket.receive_bytes()
            await websocket.send_bytes(data)
    except WebSocketDisconnect:
        print("❌ Loopback Client Disconnected")
    except Exception as e:
        print(f"⚠️ Loopback Error: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
