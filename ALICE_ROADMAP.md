✅❌ Alice Roadmap 2025–2026 (Checklist Edition)
Phase B — Robust Core (2025 H1)

B1 Local Fast Lane

✅ WebRTC/WebAudio pipeline (20 ms frames, jitter buffer 100 ms)

✅ Faster-Whisper streaming (partial <300 ms)

✅ gpt-oss 7B Q4_K_M (fast brain) with streaming tokens

✅ Piper TTS with streaming chunks, sub-500 ms

✅ Barge-in detection (cut <120 ms)

✅ Micro-acks (pre-recorded PCM)

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