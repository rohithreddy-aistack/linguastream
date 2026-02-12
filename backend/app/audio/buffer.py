import time
import asyncio
from collections import deque

class JitterBuffer:
    """
    A simple buffer to smooth out incoming results and optionally delay them
    to match audio latency.
    """
    def __init__(self, delay_ms=0):
        self.delay_ms = delay_ms
        self.queue = deque()
        self._running = True

    def push(self, data):
        """
        Push a new result into the buffer with its arrival timestamp.
        """
        self.queue.append({
            "received_at": time.time(),
            "data": data
        })

    def pop_ready(self):
        """
        Returns all items that have been in the buffer longer than delay_ms.
        """
        now = time.time()
        ready = []
        while self.queue:
            # Check if the first item in queue is ready
            if (now - self.queue[0]["received_at"]) * 1000 >= self.delay_ms:
                ready.append(self.queue.popleft()["data"])
            else:
                break
        return ready

class AudioSyncBuffer:
    """
    Tracks audio processing time vs transcript arrival time.
    """
    def __init__(self):
        self.start_time = None
        self.total_samples = 0
        self.sample_rate = 16000

    def start(self):
        self.start_time = time.time()

    def record_samples(self, count):
        self.total_samples += count

    def get_audio_time(self):
        """Returns current position in audio stream in seconds."""
        return self.total_samples / self.sample_rate

    def get_latency(self):
        """Returns the difference between real time and audio time."""
        if self.start_time is None:
            return 0
        elapsed_real = time.time() - self.start_time
        return elapsed_real - self.get_audio_time()
