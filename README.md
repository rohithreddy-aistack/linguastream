# LinguaStream 🎙️🇮🇳

> **Real-time, cross-platform live translation for streaming content (YouTube/Coursera) into Indian languages.**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Backend](https://img.shields.io/badge/backend-FastAPI-green.svg)
![Frontend](https://img.shields.io/badge/extension-Chrome_Manifest_V3-orange.svg)
![Status](https://img.shields.io/badge/status-Alpha-red.svg)

## 📖 Overview
LinguaStream is a browser-based translation overlay that enables users to watch English educational content with real-time audio/text translations in **Telugu, Hindi, Tamil, and Kannada**.

Unlike standard captioning tools, LinguaStream uses a **"Thin Client" architecture** where audio capturing happens in the browser, but all heavy processing (resampling, buffering, AI inference) is offloaded to a local Python backend. This ensures minimal browser lag and allows us to leverage high-performance Python libraries for audio signal processing.

## 🏗️ Architecture
```mermaid
graph LR
    A[YouTube Tab] -- 1. Raw Audio (PCM) --> B(Chrome Extension)
    B -- 2. WebSocket Stream --> C{Python Backend}
    C -- 3. Resample & Buffer --> D[Sarvam AI / Azure]
    D -- 4. Translated Text/Audio --> C
    C -- 5. Sync & Push --> B
    B -- 6. Overlay on Video --> A
