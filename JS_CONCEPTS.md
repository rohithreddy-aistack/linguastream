# JavaScript Concepts & Development Insights

This document outlines the core JavaScript concepts utilized in the **LinguaStream** Chrome Extension, along with specific challenges encountered and the debugging strategies employed during development.

---

## 1. Key Concepts

### A. Chrome Extension Architecture (Manifest V3)
The project adheres to **Manifest V3**, which enforces strict separation of concerns and security policies.

*   **Service Workers (`background.js`):** Acts as the central event coordinator. Since it runs in a worker environment (no DOM access), it cannot directly capture audio or manipulate the webpage. It manages the application state (`isRecording`) and routes messages between the Popup and Offscreen document.
*   **Offscreen Documents (`offscreen.html` / `offscreen.js`):** A workaround for Manifest V3 limitations. Since Service Workers cannot access `navigator.mediaDevices`, we spawn a hidden HTML document to handle the `AudioContext` and WebSocket connections.
*   **Content Scripts (`content.js`):** Runs in the context of the web page (e.g., YouTube). It is responsible for injecting the subtitle overlay and manipulating the DOM elements (like `<video>`) to implement "Audio Ducking".
*   **Message Passing:** Asynchronous communication between these isolated contexts using `chrome.runtime.sendMessage` and `chrome.runtime.onMessage`.

### B. Web Audio API
Used extensively for real-time audio processing in `offscreen.js`.

*   **AudioContext:** The primary container for audio graph processing. We use two separate contexts:
    *   **Capture Context (44.1kHz):** Matches the browser's native tab capture rate to avoid artifacts.
    *   **Playback Context (16kHz):** Explicitly set to match the output sample rate of the TTS engine (ElevenLabs) to ensure correct pitch and speed.
*   **ScriptProcessorNode:** Used to access raw PCM data from the audio stream. While deprecated in favor of `AudioWorklet`, it provides a simpler implementation for buffer access in this MVP.
*   **AudioBuffer & SourceNodes:** Used to schedule and play back the binary audio chunks received from the backend.

### C. Binary Data & Typed Arrays
*   **PCM Data Manipulation:** Raw audio from the browser comes as `Float32Array` (values -1.0 to 1.0). The backend expects 16-bit integers (`Int16Array`).
*   **ArrayBuffer:** The WebSocket `binaryType` is set to `arraybuffer` to handle the raw audio bytes efficiently without string serialization overhead.

### D. WebSockets
*   **Real-Time Streaming:** Establishes a persistent full-duplex connection to the Python FastAPI backend.
*   **Event-Driven Architecture:** Relies heavily on `onopen`, `onmessage`, `onerror`, and `onclose` to manage the stream lifecycle and handle incoming TTS chunks or transcript text.

---

## 2. Challenges & Issues

### Issue 1: "navigator.mediaDevices is undefined"
*   **Context:** Attempting to call `getUserMedia` inside `background.js`.
*   **Cause:** Manifest V3 Service Workers do not have access to the `window` object or DOM APIs, including MediaDevices.
*   **Resolution:** Implemented the `chrome.offscreen` API. The background script checks for an existing offscreen document or creates one, then passes the `streamId` to it to handle the actual audio capture.

### Issue 2: Audio Playback Speed & Pitch (Chipmunk Effect)
*   **Context:** The TTS audio returned from the backend sounded high-pitched and too fast.
*   **Cause:** Sample Rate Mismatch. The browser's `AudioContext` defaults to the system rate (usually 44.1kHz or 48kHz), but the AI model generates audio at 16kHz. Playing 16k samples at a 44.1k rate compresses the waveform, causing the "chipmunk" effect.
*   **Resolution:** Created a dedicated `playbackContext` in `offscreen.js` explicitly initialized with `sampleRate: 16000`.

### Issue 3: Stuttering Audio (Gapless Playback)
*   **Context:** Audio chunks from the TTS stream played with noticeable gaps or overlaps between them.
*   **Cause:** `source.start(0)` plays audio immediately upon receipt. Network jitter caused buffers to arrive at irregular intervals.
*   **Resolution:** Implemented a scheduling system using `nextStartTime`.
    ```javascript
    // Logic in offscreen.js
    if (nextStartTime < currentTime) nextStartTime = currentTime;
    source.start(nextStartTime);
    nextStartTime += audioBuffer.duration;
    ```
    This queues chunks back-to-back in the audio hardware buffer.

### Issue 4: WebSocket State Management
*   **Context:** Errors like "WebSocket is already in CLOSING or CLOSED state" when stopping recording.
*   **Cause:** Asynchronous cleanup routines trying to send data after the socket connection was manually terminated.
*   **Resolution:** Added rigorous checks for `socket.readyState === WebSocket.OPEN` inside the `onaudioprocess` loop and proper cleanup in the `stopCapture` function.

---

## 3. Debugging Strategies

### A. The "Loopback" Test
To isolate whether audio corruption was happening in the Browser->Python upload or Python->Browser download:
1.  Created a boolean flag `isLoopback`.
2.  Backend simply echoes the received bytes back without processing.
3.  If the loopback audio is clear, the capture/playback logic is correct, and the issue lies with the AI models.

### B. Console Logging Layers
Since logs appear in different places for extensions:
*   **Popup Logs:** Right-click Extension icon -> Inspect.
*   **Background Logs:** Extensions Management Page -> "Inspect views: service worker".
*   **Offscreen/Content Logs:** These are trickier. We used `chrome.runtime.sendMessage` to forward critical logs from the offscreen document to the background script console, or opened the offscreen HTML file in a standard tab during dev to see its console.

### C. Visualizing Audio Data
*   **Amplitude Checks:** Logged the `Math.max(...chunk)` of the PCM data to ensure the microphone wasn't muted (receiving all zeros) or clipping (hitting 1.0 continuously).
*   **Hex/Binary Inspection:** Used `console.log` on the `Int16Array` to verify that byte conversion was producing expected integer ranges (-32768 to 32767).