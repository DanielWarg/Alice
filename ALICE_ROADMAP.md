✅❌ Alice Roadmap 2025–2026 (Checklist Edition)
Phase B — Robust Core (2025 H1)

B1 Local Fast Lane (**REIMPLEMENTING WITH NEW ARCHITECTURE**)

### **🎙️ New Streaming Voice Pipeline (Sub-500ms Target)**

**📁 Infrastructure & Transport**
✅ Scaffold WebSocket/DataChannel server + binary audio frames
✅ Client mic capture → 20ms frames with VAD (WebRTC-VAD aggressiveness=2)
✅ Jitter buffer (100ms) & playback with cross-fade (80ms)
✅ Audio ducking (-18dB when TTS active) and echo cancellation

**🎯 ASR Streaming (faster-whisper)**
⬜ faster-whisper adapter with streaming configuration
⬜ Partial transcription ≤200ms, final on silence ≥250ms
⬜ chunk_ms=200, stabilize_ms=250, beam_size=1, no_speech_threshold=0.6
⬜ Event emission: `partial(text)`, `final(text)` with timestamps

**🧠 LLM Streaming (gpt-oss 7B)**
⬜ gpt-oss 7B Q4_K_M streaming adapter 
⬜ First token emission ≤300ms target
⬜ max_new_tokens=40, temperature=0.2, top_p=0.9, stream=true
⬜ System prompt: "Spoken style, ≤2 sentences, concise"

**🔊 TTS Streaming (Piper)**
⬜ Pre-warmed Piper model (synthesize 100ms silence on boot)
⬜ Stream 40-80ms PCM chunks, first chunk ≤150ms
⬜ Phrase splitter: 10-25 words or minor punctuation triggers
⬜ Cancel with 80-120ms smooth ramp-down (no clicks)

**⚡ Barge-in System**
⬜ Client VAD detection during playback → `barge_in` signal
⬜ Server cancels TTS with smooth fadeout <120ms
⬜ Measure and log `barge_in_cut_ms` for performance tracking
⬜ Resume-safe: spurious barge-in doesn't resume old TTS

**🎵 Micro-acks & Responsiveness**
⬜ Pre-baked PCM acks ("Mm?" ~180ms) on first partial (≥2 words)
⬜ Auto cross-fade out when first Piper chunk arrives
⬜ Perceived responsiveness without waiting for full LLM response

**🧭 Router & Privacy Architecture**
⬜ Intelligent routing: `local_fast` (default) vs `cloud_complex` (opt-in)
⬜ Heuristics: PII/tools/long-tokens → route appropriately
⬜ Safe-Summary privacy gate: 1-2 sentences, ≤300 chars, no PII
⬜ Timeout guard: cloud TTFA >600ms twice → lock cloud 5 min

**📊 Telemetry & Diagnostics**
⬜ Real-time NDJSON metrics: first_partial_ms, ttft_ms, tts_first_chunk_ms
⬜ total_latency_ms, barge_in_cut_ms, privacy_leak_attempts tracking
⬜ `/diagnostics` UI panel showing p50/p95 performance live
⬜ Self-test integration with latency/barge-in/privacy validation

**🧪 Comprehensive Testing Suite**
⬜ 50 short utterances p95 ≤500ms latency validation
⬜ 20 barge-in tests <120ms cut, no audible clicks
⬜ 0 privacy leaks in synthetic tool prompts with PII
⬜ Full offline `local_fast` operation without network
⬜ Loopback echo prevention (energy <-12dB with AEC+ducking)

B2 Tool Lane & Memory

✅ Local tools (Gmail, Calendar, Files, Home) stubs

✅ Privacy filter → Safe Summary (no PII)

✅ SQLite episodic memory + sqlite-vec embeddings

⬜ Retention controls (Forget Now/Today/All)

⬜ UI badges (“Cloud used”, “All local”, “What was spoken?”)

B3 Self-Tests & Packaging

✅ start_alice.sh autonom self-test runner (quick/full/ci)

✅ Self-test blocks boot on fail, logs artifacts (NDJSON/JUnit)

✅ Deterministic installs (npm ci, pip hashes, PID files)

⬜ Electron app packaging with auto-update & signing

⬜ Model Manager (manifest, checksums, resumable downloads)

Phase C — Cutting Edge Expansion (2025 H2)

C1 Cloud “Complex Lane” (optional)

⬜ Responses API integration for reasoning + tools

⬜ Reasoning summaries visible in UI/logs

⬜ Background tasks with safe_summary outputs

⬜ Network-guard blocks no_cloud payloads

C2 MCP Standardization

⬜ Wrap Calendar, Email, Files, Home as MCP servers

⬜ Engine MCP client integration

C3 Vision Lane

⬜ RTSP ingest → WebRTC for network cameras

⬜ YOLOv10-S/N (Metal) real-time detection

⬜ SAM-2 for segmentation/tracking bursts

⬜ Zone rules → Engine events

⬜ Ephemeral re-ID, auto-forget

C4 Persona / Media

⬜ HeyGen Streaming Avatar integration (safe_summary only)

⬜ LiveKit transport (optional showcase path)

Phase D — Self-Learning “Pattern LLM” (2025 H2–2026 H1)

D1 Pattern LLM v0 (shadow mode)

⬜ Tiny local LLM (50–200M params, 4-bit) scorer

⬜ Event featurizer → compact tokens

⬜ Outputs: P(next_action), P(accept), etc.

⬜ Bandit layer (LinUCB/TS) integration

⬜ Shadow mode logging (no suggestions shown)

D2 Pattern LLM v1 (online learning)

⬜ On-device LoRA/adapters or calibrated heads

⬜ Throttled online updates

⬜ Intervention budget (max 3/day, accept-rate ≥30%)

⬜ User controls: Off / Learn / Forget week / Forget all

D3 RL-Light (assist-only)

⬜ Offline RL (IQL/CQL small) from logs

⬜ Conservative assist-only policies (propose, not execute)

⬜ Safety bounds, rollback on low reward

Phase E — Portability & Multi-Shell (2026 H1)

⬜ Desktop (Electron v1, later Tauri)

⬜ Mobile (React Native shell)

⬜ Web (PWA shell)

⬜ Shared Engine API (HTTP/WS, Talk socket)

⬜ Export/Import encrypted ZIP for memory + Pattern LLM state

Cross-Cutting

✅ Safe Summary-only to external voice/cloud

✅ Network-guard for no_cloud payloads

✅ Secrets in OS keyring; metrics-only logs

⬜ Observability panel (latency charts, leak counter, p95 SLOs)

⬜ Auto-update pipeline for app + models

Next actionable steps

⬜ Retention controls in memory (Forget Now/Today/All).

⬜ Electron packaging + auto-update for Alice desktop.

⬜ Model Manager (manifest + resumable downloads).