import time
import asyncio
from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.extensions.types.sockets import ListenV1ResultsEvent
from app.core.config import settings

class DeepgramService:
    def __init__(self):
        self.deepgram = AsyncDeepgramClient(api_key=settings.DEEPGRAM_API_KEY)
        self.connection = None
        self.is_connected = False
        self.on_transcript_callback = None
        self._run_task = None
        self._connected_event = asyncio.Event()

    async def connect(self, on_transcript_callback):
        """
        Connects to Deepgram Live Transcription API by starting a background task.
        """
        self.on_transcript_callback = on_transcript_callback
        self._connected_event.clear()
        self._run_task = asyncio.create_task(self._run_loop())

        print("⏳ Connecting to Deepgram...")
        # Wait for connection to be established (or fail)
        await self._connected_event.wait()

    async def _run_loop(self):
        try:
            # Note: connect returns an async context manager
            async with self.deepgram.listen.v1.connect(
                model="nova-2",
                language="en-US",
                smart_format=True,
                encoding="linear16",
                channels="1",
                sample_rate="16000",
                interim_results="true",
                vad_events="true",
                endpointing="300"
            ) as connection:
                self.connection = connection
                self.is_connected = True
                self._connected_event.set()
                print("✅ Connected to Deepgram (ASR)")

                # Iterate over the connection to receive messages
                # This is the "pump" that makes the SDK process incoming data
                accumulated_transcript = ""
                accumulation_start_time = None

                async for message in connection:
                    if isinstance(message, ListenV1ResultsEvent):
                        if not message.channel.alternatives:
                            continue

                        transcript = message.channel.alternatives[0].transcript
                        is_final = message.is_final
                        speech_final = message.speech_final

                        if is_final and transcript:
                            accumulated_transcript += transcript + " "
                            if accumulation_start_time is None:
                                accumulation_start_time = time.time()

                        word_count = len(accumulated_transcript.split())
                        time_elapsed = time.time() - accumulation_start_time if accumulation_start_time else 0

                        # Thresholds for sending the chunk early to avoid long delays
                        # If a speaker is talking fast, we force a dispatch after 6 words or 1.5 seconds
                        force_dispatch = False
                        if word_count >= 6 or time_elapsed >= 1.5:
                            force_dispatch = True

                        if (speech_final or force_dispatch) and accumulated_transcript.strip():
                            if self.on_transcript_callback:
                                # Call the callback directly (same event loop)
                                await self.on_transcript_callback(accumulated_transcript.strip(), True)
                            accumulated_transcript = ""
                            accumulation_start_time = None

        except Exception as e:
            print(f"❌ Deepgram Connection Error: {e}")
            self._connected_event.set()
        finally:
            self.is_connected = False
            self.connection = None
            print("🚫 Deepgram Connection Closed")

    async def send_audio(self, audio_bytes: bytes):
        """
        Sends raw PCM audio to Deepgram.
        """
        if self.connection and self.is_connected:
            try:
                # In this SDK version, send_media is used for binary data
                await self.connection.send_media(audio_bytes)
            except Exception as e:
                print(f"⚠️ Error sending audio to Deepgram: {e}")

    async def close(self):
        """
        Closes the connection.
        """
        self._stop_event = asyncio.Event()
        self._stop_event.set()
        if self._run_task:
            # Give it a moment to clean up
            try:
                await asyncio.wait_for(self._run_task, timeout=2.0)
            except asyncio.TimeoutError:
                self._run_task.cancel()
            self._run_task = None
