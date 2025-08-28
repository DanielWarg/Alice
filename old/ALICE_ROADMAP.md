✅❌ Alice Roadmap 2025–2026 (Checklist Edition)
Phase B — Robust Core (2025 H1)

B1 Voice Adapter Architecture (**NEW THIN SLICE APPROACH**)

### **🎙️ Thin Slice Voice Pipeline (Mål: "Prata med Alice idag")**

**🚀 Phase 1: OpenAI Realtime Thin Slice**
⬜ Arkitektur: Mic → VAD → ASR+TTS (OpenAI Realtime WebSocket) → Agent → Playback
⬜ VoiceAdapter interface med feature flags (VOICE_PROVIDER=openai|local)
⬜ Instrumenterad latens: asr_partial_latency, asr_final_latency, llm_latency, tts_ttfa, e2e_roundtrip
⬜ UX states i UI: "Lyssnar" (VAD on), "Tänker" (agent), "Svarar" (audio stream)

**🔌 Phase 2: Adapterkontrakt & Isolering**
⬜ Voice adapter interface:
  - ASR.start({onPartial, onFinal, onError}), ASR.stop()
  - TTS.speak({text|ssml, voiceId, onStart, onChunk, onEnd, onError}), TTS.cancel()
⬜ Providers implementerade:
  - OpenAIRealtimeAdapter (aktiv)
  - WhisperAdapter (stub för framtid)
  - PiperAdapter (stub för framtid)
⬜ Env/feature flags: VOICE_PROVIDER, VOICE_VAD=on/off, VOICE_LOG_METRICS=on

**📊 Phase 3: Shadow Mode & Mätning**
⬜ Kör OpenAI Realtime live + shadow Whisper lokalt (mäta WER/fel)
⬜ Daglig rapport: median/p95 latens, felkoder, avbrott, VAD-fel, fallback-rate
⬜ Datadrivna val för när vi ska byta till lokal pipeline

**🔒 Phase 4: Säkerhet & Etik**
⬜ Banner "Syntetiskt tal" för TTS
⬜ Samtycke före eventuell röstkloning
⬜ Logga bara nödvändiga metrikfält (ej råaudio som standard)
⬜ Förbered digitalt vattenmärke när leverantör stödjer

**🎯 Acceptanskriterier för Thin Slice**
⬜ "Hej Alice, vad är vädret?" → svar med strömmad röst
⬜ e2e roundtrip ≤1200ms p50, ≤2500ms p95 (M4 + bra nätverk)
⬜ Felhantering: WS-reconnect, mic-varningar, TTS timeout → textfallback
⬜ Metrics i logg + KPI-rapport via Shadow Mode endpoint

**📁 Arkiverad Implementation (v1)**
✅ Komplett lokal voice pipeline (faster-whisper + gpt-oss + Piper) arkiverad
✅ ASR/LLM/TTS streaming adapters implementerade och testade
✅ WebSocket binary transport + session management
✅ Performance metrics och comprehensive testing suite
📦 Arkiv: `archive/voice_pipeline_v1_20250827/` för framtida användning

B2 Tool Lane & Memory

**🎯 Orchestrator Integration (Before Tool Expansion)**
⬜ State machine per session with turn management
⬜ Event bus for inter-component routing (STT/LLM/TTS/Tools)
⬜ Router with cloud auto-degrade (TTFA >600ms → lock 5min)
⬜ Privacy gate: Safe Summary enforcement before TTS/cloud
⬜ Planner: Intent detection → tool selection with JSON schema
⬜ Performance metrics: P50/P95 SLO telemetry collection
⬜ Barge-in propagation: Cancel LLM/TTS/tools <120ms
⬜ Self-tests: latency/barge-in/privacy/offline validation

✅ Local tools (Gmail, Calendar, Files, Home) stubs

✅ Privacy filter → Safe Summary (no PII)

✅ SQLite episodic memory + sqlite-vec embeddings

⬜ Retention controls (Forget Now/Today/All)

⬜ UI badges ("Cloud used", "All local", "What was spoken?")

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