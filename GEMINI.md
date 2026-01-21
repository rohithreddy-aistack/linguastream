# LinguaStream Project Context & Roadmap

## 1. Project Overview
**LinguaStream** is a cross-platform application designed to provide real-time, live translation of streaming audio (e.g., YouTube, Coursera) into Indian languages (Telugu, Hindi, Tamil, Kannada).

**Key Differentiator:** It handles "Code-Mixing" (Hinglish/Tanglish) natively using specialized AI models (**Sarvam AI**), ensuring technical terms remain in English while grammar and casual speech are translated.

## 2. Architecture: "The Audio Interceptor"

The system follows a **Thin Client / Fat Server** model to minimize browser resource usage and maximize Python's audio processing capabilities.

### **Frontend: Chrome/Brave Extension (Manifest V3)**
* **Role:** Audio Capture & UI Overlay.
* **Mechanism:**
    * **Background Script (`background.js`):** Orchestrates state (Rec/Stop) and manages the offscreen document lifecycle.
    * **Offscreen Document (`offscreen.html`):** Bypasses Manifest V3 limitations to access the `AudioContext` and `ScriptProcessorNode`.
    * **WebSocket Client (`offscreen.js`):** Streams raw PCM audio (Float32) to `127.0.0.1:8000`.
    * **Content Script (`content.js`):** Injects the subtitle overlay onto the `<video>` player (Phase 2).

### **Backend: Python Orchestrator (FastAPI)**
* **Role:** Signal Processing & AI Gateway.
* **Tech Stack:** FastAPI, Uvicorn, NumPy, SciPy, PyTorch (CPU).
* **Pipeline:**
    1.  **Ingest:** Receives audio stream via WebSocket (`ws://127.0.0.1:8000`).
    2.  **Resample:** Downsamples Browser Audio (44.1kHz/48kHz) to Model Audio (16kHz).
    3.  **VAD Gate:** Uses **Silero VAD** (Voice Activity Detection) to detect human speech.
        * *Music/Silence* -> **DROP** Packet (Saves API costs & prevents hallucinations).
        * *Speech* -> **PASS** Packet.
    4.  **Inference:** Forwards clean speech to **Sarvam AI** (Primary) or **Azure Speech SDK** (Fallback).
    5.  **Response:** Sends translated text/audio back to the frontend.

---

## 3. Current Status (Week 1 Complete - Stable)
* ✅ **Repository Setup:** Monorepo structure (`backend/`, `clients/extension`) established.
* ✅ **Audio Capture:** Extension successfully captures tab audio using `tabCapture` and `offscreen` API.
* ✅ **Connectivity:** WebSocket pipeline established between Chrome and Python (IPv4 `127.0.0.1` fix applied).
* ✅ **VAD Integration:** Silero VAD successfully filters out background music/silence in real-time (Buffering logic implemented).
* ✅ **Verification:** System successfully records a local `.wav` file containing only spoken segments from a YouTube video.

---

## 4. Comprehensive Directory Structure (Target State)
*Use this structure to maintain context of where new files belong.*

```text
linguastream/
├── .github/                       # CI/CD & Templates
│   ├── workflows/                 
│   │   ├── auto-test.yml          # (Planned) Unit tests on PR
│   │   └── deploy-backend.yml     # (Planned) Docker build/push
│   └── PULL_REQUEST_TEMPLATE.md   
├── assets/                        # Design assets
│   ├── diagrams/                  # Architecture flowcharts
│   └── branding/                  # Logos (icon16.png, icon48.png, etc.)
├── backend/                       # 🧠 THE BRAIN: Python Audio Orchestrator
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # ✅ Entry point & WebSocket router (VAD logic here)
│   │   ├── core/                  # Configurations
│   │   │   ├── __init__.py
│   │   │   └── config.py          # (Planned) Env var loader (API Keys)
│   │   ├── audio/                 # Audio Processing Logic
│   │   │   ├── __init__.py
│   │   │   ├── processor.py       # (Planned) Resampling & filtering logic
│   │   │   └── buffer.py          # (Planned) Jitter buffer & sync logic
│   │   └── services/              # External AI Integrations
│   │       ├── __init__.py
│   │       ├── sarvam_client.py   # (Planned) Sarvam AI WebSocket wrapper
│   │       └── azure_client.py    # (Planned) Azure Fallback wrapper
│   ├── tests/                     # Backend Tests
│   │   ├── __init__.py
│   │   ├── test_main.py           # ✅ Connection tests
│   │   └── test_audio.py          # (Planned) Resampling quality tests
│   ├── Dockerfile                 # (Planned) Container definition
│   ├── docker-compose.yml         # (Planned) Orchestration
│   ├── requirements.txt           # ✅ Python dependencies
│   └── .env                       # (Ignored) Secrets
├── clients/                       # 👂 THE EARS: Frontend Clients
│   ├── extension/                 # Chrome/Brave Extension
│   │   ├── manifest.json          # ✅ Manifest V3 Config
│   │   ├── src/
│   │   │   ├── background.js      # ✅ Extension Coordinator
│   │   │   ├── offscreen.html     # ✅ Audio Host Page
│   │   │   ├── offscreen.js       # ✅ Audio Capture Logic
│   │   │   ├── content.js         # (Planned) UI Overlay Injection
│   │   │   ├── popup.html         # ✅ Extension Menu UI
│   │   │   └── popup.js           # ✅ Extension Menu Logic
│   │   └── assets/                # Packed icons
│   └── mobile/                    # (Planned) Future Android/iOS Client
│       ├── pubspec.yaml           # (Placeholder) Flutter config
│       ├── android/
│       └── lib/
│           └── webview_bridge.dart # (Planned) Audio injection bridge
├── docs/                          # Project Documentation
│   ├── API_REFERENCE.md           # Internal WebSocket protocol
│   └── SETUP_GUIDE.md             # Dev environment setup
├── scripts/                       # Dev Tools
│   ├── start_dev.sh               # (Planned) One-click start script
│   └── latency_test.py            # (Planned) Lag measurement tool
├── GEMINI.md                      # ✅ This Project Context File
├── .gitignore                     # ✅ Git ignore rules
└── README.md                      # ✅ Project Landing Page
```

---

## 5. Detailed 8-Week Development Roadmap

### **Phase 1: Foundation & "The Pipeline" (Weeks 1-2)**

*Focus: Establishing the connection between the Browser and Python.*

* **Week 1: MVP Audio Capture & VAD (Completed)**
* [x] Setup Monorepo & Git Flow.
* [x] Implement `manifest.json` & `offscreen` audio capture.
* [x] Build FastAPI WebSocket Server.
* [x] Integrate Silero VAD to filter non-speech audio.
* [x] Verification: `.wav` file recording.


* **Week 2: Audio Resampling & Loopback Test (Current Focus)**
* [ ] **Backend:** Refactor `main.py` to move logic into `audio/processor.py` for cleaner architecture.
* [ ] **Backend:** Implement robust `scipy.signal.resample_poly` (44.1kHz -> 16kHz) to improve audio quality for the AI.
* [ ] **Feature:** Create a "Loopback" endpoint. (Browser Mic -> Python -> Browser Speakers). This is critical to *hear* the latency delay.
* [ ] **Frontend:** Update `popup.html` to show real-time connection status (Green/Red indicators) instead of just the browser badge.



### **Phase 2: Core Translation Engine (Weeks 3-4)**

*Focus: Integrating Sarvam AI and handling Indian languages.*

* **Week 3: Sarvam AI Integration**
* [ ] **Backend:** Create `services/sarvam_client.py`.
* [ ] **Protocol:** Implement the specific WebSocket handshake for Sarvam's `speech-to-text-translate` API.
* [ ] **Authentication:** Securely load API keys from `.env`.
* [ ] **Logic:** Handle Sarvam's "Partial" vs "Final" transcript events to reduce text flickering on the UI.


* **Week 4: The Visual Overlay (Subtitle Sync)**
* [ ] **Frontend:** Build `content.js` to inject a floating, draggable `<div>` over the YouTube video player.
* [ ] **Backend:** Send translated text *with timestamps* back to the extension.
* [ ] **Sync Logic:** Implement a "Jitter Buffer" in `buffer.py`. (Calculate the delay between "Speech Sent" and "Text Received" and delay the display to match).



### **Phase 3: Robustness & Audio Dubbing (Weeks 5-6)**

*Focus: Improving quality and adding the "Audio" mode.*

* **Week 5: Azure Fallback & Error Handling**
* [ ] **Backend:** Implement `services/azure_client.py` using the Azure Speech SDK.
* [ ] **Circuit Breaker:** Logic: If Sarvam WebSocket errors rate > 5% in 1 minute, auto-switch stream to Azure.
* [ ] **Security:** Implement `core/config.py` for secure key rotation and secret management.


* **Week 6: Audio Dubbing (TTS) Mode**
* [ ] **Backend:** Request Audio bytes (TTS) from Sarvam alongside text.
* [ ] **Frontend:** Implement "Audio Ducking" in `content.js`.
* [ ] **Logic:** When translated audio arrives, set `videoElement.volume = 0.2` via JavaScript.
* [ ] **Goal:** A "News Broadcast" style experience (Original low background, Translation loud foreground).



### **Phase 4: Optimization, Mobile & Launch (Weeks 7-8)**

*Focus: Performance tuning and packaging.*

* **Week 7: Performance & Mobile Architecture**
* [ ] **Benchmark:** Run `scripts/latency_test.py`. If processing > 200ms, rewrite `resample` in Rust (PyO3).
* [ ] **Mobile:** Initialize `clients/mobile` Flutter project.
* [ ] **Mobile Bridge:** Implement the Android `WebView` bridge to inject JavaScript for audio capture on mobile.


* **Week 8: Documentation & Release**
* [ ] **Docs:** Finalize `SETUP_GUIDE.md` and internal API docs.
* [ ] **Ops:** Create `Dockerfile` and `docker-compose.yml` for easy 1-click deployment.
* [ ] **Release:** Submit Extension to Chrome Web Store (Unlisted/Beta).
* [ ] **Release:** Tag v1.0 on GitHub.



## 6. Troubleshooting & Notes

* **SSL Error:** Python on macOS requires running `Install Certificates.command` to fix `torch.hub.load` errors.
* **IPv6 Issue:** Chrome Extensions must connect to `127.0.0.1`, not `localhost`.
* **Brave Browser:** Shields must be DOWN for the YouTube tab to allow audio capture.
* **VAD Buffer Error:** Silero VAD requires exactly 512 samples (at 16kHz). We implemented a buffer in `main.py` to ensure this exact chunk size is always passed to the model.
* **Tab Capture Error:** `getMediaStreamId` must be called in `background.js` without a specific `consumerTabId` to allow the offscreen document to consume the stream.
