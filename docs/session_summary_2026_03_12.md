# LinguaStream Architecture & R&D Session Summary
**Date:** March 12, 2026

## Objective
Investigate and integrate local/fast AI models into the real-time 3-Stage Dubbing Pipeline (ASR -> Translation -> TTS) to improve translation accuracy, specifically addressing the "Code-Mixing" semantic limitation where English technical quotes/proverbs were inappropriately translated into Indian languages.

---

## 1. Local ASR Exploration (Replacing Deepgram)
**Goal:** Test open-source local ASR models on Apple Silicon (M4) to potentially replace cloud-hosted Deepgram for better privacy/latency control.

### Model A: OpenAI Whisper (Base)
*   **Action:** Upgraded from `tiny` to `base` model.
*   **Issue:** Encountered `NaN logits` and tensor reshape crashes on MPS (Apple Metal Performance Shaders) when using `fp16=True`.
*   **Fix:** Added conditional logic to force `fp32` (disable `fp16`) specifically when running on MPS.
*   **Result:** The pipeline ran successfully, but the resulting textual translation produced by Sarvam was complete gibberish (severe hallucination/error propagation from the base ASR transcript).

### Model B: Moonshine (Base)
*   **Action:** Removed Whisper and implemented a completely customized `MoonshineService` integrating the `moonshine-base` model.
*   **Issue:** `AttributeError` caused by differing model architectures (`input_values` vs `input_features`).
*   **Fix:** Refactored the Hugging Face processor pipeline to pass audio chunks dynamically as continuous input values.
*   **Result:** Like Whisper, the ASR transcript quality from the fast continuous audio stream caused the next translation stage to output unusable gibberish.

**Decision:** Reverted the codebase to entirely use the **Deepgram Cloud API**. All local ASR service files (`whisper_service.py`, `moonshine_service.py`) and dependencies were uninstalled and removed from `/backend`.

---

## 2. Translation & Semantic Reasoning Investigation (Replacing Sarvam API)
**The Problem:** While the Sarvam API with `mode="code-mixed"` successfully translates Hinglish/Tanglish grammar, it acts as a traditional Sequence-to-Sequence (Seq2Seq) Neural Machine Translation model. It lacks semantic reasoning. When the presenter says *"All that glitters is not gold"*, Sarvam blindly translates the quote into Telugu instead of recognizing it as an English idiom meant to remain in English.

### Exploration A: Groq + Llama 3 (8B-Instant)
*   **Action:** Implemented a `GroqTranslateService` wrapping an ultra-low latency Llama-3 instructed to perform semantic reasoning (i.e. recognize English quotes and keep them in English while translating the surrounding text).
*   **Latency Profile:** Highly successful. Groq's dedicated LPU architecture achieved Time-To-First-Token (TTFT) ~15ms, maintaining the 1-second live stream integrity.
*   **Result:** The English idioms were successfully protected, but the user determined the actual quality of the generated Indian language (Telugu/Hindi) grammar from Llama 3 was horrible compared to Sarvam's hyper-specialized models.
*   **Codebase Decision:** The Groq implementation and `groq` pip package were removed and the server reverted.

### Exploration B: Google Cloud Translation API
*   **Action:** Designed the architecture for integrating `google-cloud-translate`.
*   **Result:** Abandoned prior to execution because Google Translate relies on the exact same traditional NMT architecture as Sarvam's API. It has no semantic LLM reasoning layer and thus possesses the exact same code-mixing shortfall.

### Exploration C: Custom Sarvam 30B Inference on Dedicated GPU
*   **Goal:** Use Sarvam's highly contextual 30 Billion parameter open-source LLM natively to do both flawless translation AND semantic quote retention.
*   **Discovery:** Sarvam 30B is not hosted on any serverless LPU providers (Together AI, Fireworks, Groq). To use it as an API, it requires renting a dedicated GPU instance (e.g. RunPod, Hugging Face Dedicated Endpoints) running `vLLM` on an A100 80GB configuration.
*   **Limitations:**
    *   **Cost:** ~$1.69 - $2.00 per hour dedicated cost.
    *   **Latency:** Generation speeds roughly 12-20ms per token, resulting in a 300ms-500ms Time-To-First-Token. This drastically harms the real-time continuous streaming feel compared to Groq.
*   **Decision:** The user paused development due to the cost and latency hurdles.

---

## Codebase Status at Session Pause
The `backend` is perfectly functional, stable, and completely cleaned containing only the original 3 Stage Architecture:
1.  **ASR:** `DeepgramService`
2.  **Translate:** `SarvamTranslateService` (with the known semantic idiom limitation)
3.  **TTS:** `SarvamTTSService`

*All experimental files, prompt logic, API flag toggles, and dependencies (transformers, einops, groq, openai-whisper) have been safely uninstalled and deleted from the repository.*
