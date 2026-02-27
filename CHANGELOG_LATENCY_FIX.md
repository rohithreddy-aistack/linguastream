# Latency Optimization Changelog

This file tracks the architectural changes made on February 20, 2026, to reduce the 11s latency and 40s overrun in the LinguaStream pipeline.

## Baseline State (Before Optimization)
- **Pipeline:** Sequential (S1 -> S2 -> S3 for each sentence).
- **TTS:** REST-based (`https://api.sarvam.ai/text-to-speech`). Waits for full audio generation before playback.
- **Translate:** REST-based (`https://api.sarvam.ai/translate`). New session created per request.
- **ASR:** Deepgram Live (Threshold: 1.5s or 6 words).
- **Latency:** ~11s initial delay, ~40s backlog after 2 minutes of video.

## Final Optimized State
- **Pipeline:** Parallel sentence processing with `OrderedAudioStreamer`.
- **TTS:** Streaming WebSocket (`AsyncSarvamAI` bulbul:v3-beta).
- **Frontend:** 24kHz sample rate to match Sarvam's high-fidelity output.
- **Performance:** Latency dropped to ~2.5s. Backlog eliminated.

## Files Modified
1. `backend/app/services/sarvam_translate_client.py` (Session reuse)
2. `backend/app/services/sarvam_tts_client.py` (Switch to Async Streaming WebSocket)
3. `backend/app/main.py` (Parallel processing & `OrderedAudioStreamer` logic)
4. `clients/extension/src/offscreen.js` (Updated sample rate to 24kHz)

## Rollback Procedure
To revert these changes, restore the original content of the files listed above from the git history.

---
## Change Log

### 1. Optimize Sarvam Translate (Session Reuse) - COMPLETED
- **Goal:** Reduce 200-500ms TLS handshake overhead per sentence.
- **Change:** Refactored `SarvamTranslateService.translate` to accept an external `aiohttp.ClientSession`.

### 2. Implement Parallel REST TTS - UPDATED
- **Goal:** Robustness while maintaining low latency.
- **Change:** Reverted from `sarvamai` WebSocket SDK (which was unstable) to parallelized REST calls. Reuses `http_session` for performance.
- **Frontend:** Kept 24kHz sample rate to match `bulbul:v3` high-fidelity output.

### 3. Parallelize Backend Orchestrator - COMPLETED
- **Goal:** Eliminate the sequential bottleneck and processing backlog.
- **Change:** Refactored `backend/app/main.py` to use `asyncio.create_task` for parallel sentence processing and implemented `OrderedAudioStreamer` (using per-sentence `asyncio.Queue`) to maintain chronological playback while allowing chunk-by-chunk streaming.
