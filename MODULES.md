# 📦 Alice Deployment Architecture Guide
*Portable Application Suite Structure*

## 🏗️ Project Structure Overview

```
Alice Production Suite/
├── 📱  apps/            # Platform-specific applications
│   ├── desktop/        # Electron/Tauri desktop apps
│   ├── mobile/         # React Native mobile apps
│   └── web/            # Next.js PWA web app
├── 🏗️  core/            # UI-agnostic Alice Engine
│   ├── engine/         # Core AI processing
│   ├── voice/          # Talk-socket voice system
│   └── api/            # WebSocket/HTTP interface
├── 🔗  shared/          # Cross-platform components
│   ├── ui/             # Component library
│   ├── types/          # TypeScript definitions
│   └── utils/          # Common utilities
├── 📚  docs/            # Deployment documentation
├── 🐳  deploy/          # CI/CD and deployment scripts
└── 📋  Configuration   # Root config and documentation
```

---

## 🏗️ Alice Engine (`/core/`)

**UI-Agnostic Core:** Headless processing engine with WebSocket/HTTP API

### 🧠 Core AI Components
- **`llm/`** - LLM abstraction layer (Ollama, OpenAI, Harmony)
  - `manager.py` - LLM request routing and management
  - `harmony.py` - Swedish AI prompt system
  - `ollama.py` - Local model integration
  - `openai.py` - Cloud API fallback

### 🤖 Agent System
- **`core/`** - Agent orchestration and planning system
  - `agent_executor.py` - Task execution engine
  - `agent_planner.py` - Multi-step task planning
  - `agent_orchestrator.py` - Agent coordination
  - `tool_registry.py` - Available tools management

- **`agents/`** - Agent implementations
  - `bridge.py` - Alice AI bridge for external communication

### 🎙️ Voice Pipeline (Clean Slate Implementation)
- **`voice/`** - Sub-500ms streaming voice pipeline (NEW)
  - **`server/`** - WebSocket/DataChannel voice server
    - `transport.ts` - Binary audio frame transport
    - `pipeline.ts` - ASR → LLM → TTS orchestration
    - **`adapters/`** - Streaming component adapters
      - `asr_faster_whisper.ts` - Partial transcription ≤200ms
      - `llm_gpt_oss_7b.ts` - First token ≤300ms streaming
      - `tts_piper.ts` - Pre-warmed streaming chunks ≤150ms
    - `privacy_gate.ts` - Safe-Summary PII filtering
    - `telemetry.ts` - Real-time NDJSON metrics
  - **`client/`** - Browser voice client
    - `voice_client.ts` - VAD + mic capture + playback
    - `jitter_buffer.ts` - 100ms buffering with cross-fade
    - `barge_detector.ts` - Smart interruption handling
  - **`router/`** - Intelligent routing
    - `local_fast.ts` - Default on-device pipeline
    - `cloud_complex.ts` - Optional cloud routing

### 🗄️ Data & Memory
- **`data/`** - Databases and cached files
  - `alice.db` - Main SQLite database
  - `ambient.db` - Ambient memory storage
  - `tts_cache/` - Cached TTS audio files

### 🔧 Support Systems  
- **`services/`** - Backend services
  - `ambient_memory.py` - Memory management
  - `probe_api.py` - System health monitoring
  - `reflection.py` - AI self-reflection system

---

## 📱 Applications Layer (`/apps/`)

### 🖥️ Desktop Applications (`apps/desktop/`)
**Framework:** Electron/Tauri with OS integration

- **OS Keyring Integration** - Secure credential storage
- **Native File System** - Local document processing
- **System Notifications** - Desktop alerts
- **Menu Bar Access** - Quick controls
- **Auto-updater** - Background application updates

### 📱 Mobile Applications (`apps/mobile/`)
**Framework:** React Native iOS/Android

- **Native Audio** - Device-optimized voice processing
- **Background Processing** - Ambient memory collection
- **Push Notifications** - System-level alerts
- **Biometric Auth** - Touch/Face ID security
- **Offline Mode** - Local AI processing

### 🌐 Web Application (`apps/web/`)
**Framework:** Next.js PWA with modern browser features

### 📱 Core Application
- **`app/`** - Next.js app router pages
  - `page.jsx` - Main chat interface
  - `layout.js` - Global app layout
  - `globals.css` - Global styles

### 🎨 Components
- **`components/`** - React components
  - `VoiceBox.tsx` - Voice interface component
  - `CalendarWidget.tsx` - Calendar integration
  - `B3AmbientVoiceHUD.tsx` - Voice status display
  - `AudioVisualizer.tsx` - Real-time audio visualization

### 🔊 Voice Client (Clean Implementation)
- **`lib/`** - New voice client utilities
  - `stream_client.ts` - WebSocket binary streaming
  - `audio_processor.ts` - VAD + echo cancellation
  - `playback_manager.ts` - Jitter buffer + cross-fade

---

## 🔗 Shared Components (`/shared/`)

### 🎨 UI Library (`shared/ui/`)
**Cross-Platform Design System**
- Component library that works across desktop/mobile/web
- Unified styling and theming system
- Responsive design patterns
- Accessibility-first components

### 📝 Type Definitions (`shared/types/`)
**TypeScript Interface Definitions**
- API interfaces for Alice Engine communication
- Voice system types and configurations
- Platform-specific type extensions
- Shared data models

### ⚙️ Common Utilities (`shared/utils/`)
**Cross-Platform Helper Functions**
- Configuration management
- Encryption and security utilities
- Data validation functions
- Platform detection and adaptation

---

## 📚 Deployment Documentation (`/docs/`)

### 📖 Core Documentation
- **`README.md`** - Main project documentation
- **`API.md`** - Complete API reference
- **`DEVELOPMENT.md`** - Development setup guide
- **`TROUBLESHOOTING.md`** - Common issues and fixes

### 🏗️ Architecture & Design
- **`ALICE_SYSTEM_OVERVIEW.md`** - High-level system architecture
- **`VOICE_HYBRID_ARCHITECTURE.md`** - Voice pipeline design
- **`PRIVACY_MODEL.md`** - Privacy and data handling

### 🗄️ Archives
- **`archive/`** - Historical documentation
  - Implementation plans (B3, B4)
  - Status reports and analysis

---

## 🧪 Tests Module (`/tests/`)

### ✅ Test Categories
- **`final_validation/`** - End-to-end system tests
- **`harmony_e2e_test.py`** - AI system integration tests
- **`test_b3_e2e.py`** - Voice system tests (B3 generation)

---

## 🐳 Deployment Infrastructure (`/deploy/`)

### 📊 Monitoring
- **`docker-compose.yml`** - Complete stack deployment
- **`grafana/`** - Metrics visualization configuration  
- **`prometheus/`** - Metrics collection configuration

---

## 🔧 Tools & Utilities

### 🛠️ Development Tools
- **`tools/`** - Development utilities and debugging scripts
- **`simple_monitor.py`** - System monitoring script
- **`alice_monitor.py`** - Comprehensive system monitoring

### 📋 Voice Pipeline Tests
- **`tests/voice/`** - New streaming pipeline tests
  - `latency_validation.ts` - Sub-500ms performance testing
  - `barge_in_tests.ts` - Interruption response testing
  - `privacy_tests.ts` - PII leak prevention validation

---

## 🚀 Deployment Status

### ✅ Production Ready Architecture
- **Alice Engine Core** - UI-agnostic processing engine
- **Talk-socket System** - Voice I/O abstraction layer
- **OS Keyring Integration** - Secure credential management
- **Cross-platform UI** - Shared component library
- **WebSocket/HTTP API** - Stable communication layer

### 🔧 Implementation Ready
- **Desktop Framework** - Electron/Tauri architecture complete
- **Mobile Framework** - React Native structure defined
- **PWA Foundation** - Web app deployment ready
- **Security Model** - Privacy-first design implemented
- **Build Pipeline** - CI/CD deployment workflows

### 📋 Migration Complete
- **Development to Production** - Architecture shift completed
- **Portable Structure** - apps/core/shared organization
- **Documentation Updated** - All guides reflect new structure
- **Deployment Ready** - Production infrastructure prepared

---

## 🎙️ **Voice Pipeline Architecture Specification**

### **🎯 Objective**
Implement an **on-device, streaming voice pipeline** with **sub-500ms** total latency using **faster-whisper** → **gpt-oss 7B** → **Piper TTS** with barge-in support.

### **⚡ Performance Targets (SLOs)**
- `first_partial_ms` ≤ **300ms** - Time to first partial transcription
- `ttft_ms` ≤ **300ms** - Time to first LLM token
- `tts_first_chunk_ms` ≤ **150ms** - Time to first TTS audio chunk
- `total_latency_ms` p95 ≤ **500ms** - End-to-end for short turns (1-8 words)
- `barge_in_cut_ms` < **120ms** - Interruption response time

### **🔄 Data Flow (local_fast path)**
```
Mic (20ms frames, AEC/NS/AGC)
  → VAD (aggressiveness=2, min-voiced=2 frames)  
  → STT (faster-whisper, partial ≤200ms, final on silence ≥250ms)
  → LLM (gpt-oss 7B Q4_K_M, stream, first token ≤300ms)
  → Phrase splitter (10-25 words, immediate TTS feed)
  → Piper TTS (pre-warmed, stream 40-80ms PCM chunks, first ≤150ms)
  → Jitter buffer (client 100ms) → Playback with barge-in detection
```

### **🛡️ Privacy & Routing**
- **local_fast** (default): Full local STT/LLM/TTS pipeline
- **cloud_complex** (optional/off): OpenAI via Safe-Summary filter only
- **Safe-Summary gate**: Rewrites tool results to 1-2 sentences, no PII
- **Privacy-first**: No transcripts/audio persisted, local processing by default

### **🎚️ Barge-in & Micro-acks**
- **Barge-in**: VAD detects speech → `barge_in` signal → 80-120ms TTS fadeout
- **Micro-acks**: Pre-baked "Mm?" (~180ms) on first partial, cross-fade to TTS
- **Ducking**: Speaker volume to -18dB when TTS active, prevent echo

### **📊 Event Protocol (WebSocket/DataChannel)**
**Upstream**: `audio.frame`, `control.barge_in`, `control.mic`
**Downstream**: `stt.partial/final`, `llm.delta`, `tts.audio_chunk/begin/end/active`

### **🧪 Testing Requirements**
- **Latency**: 50 short utterances p95 ≤500ms
- **Barge-in**: 20 interrupts <120ms cut, no clicks
- **Privacy**: 0 leaks in PII tool prompts
- **Offline**: Full local_fast operation without network

---

## 🎯 **Current Implementation Status**

### **✅ Phase 1: Voice Pipeline Infrastructure (COMPLETE)**
1. **✅ Transport Layer** - WebSocket binary audio streaming complete
2. **✅ Audio Processing** - Jitter buffer, cross-fade, ducking, echo cancellation
3. **✅ Voice Activity Detection** - Real-time VAD with energy calculation
4. **✅ Session Management** - Multi-client WebSocket with cleanup
5. **✅ Comprehensive Testing** - Full test suite with browser validation

### **🔄 Phase 2: ASR Integration (NEXT)**
1. **faster-whisper Adapter** - Streaming ASR with ≤200ms partial transcription
2. **Event System** - Real-time STT events with confidence scores
3. **Performance Optimization** - Sub-200ms first partial target

### **📱 Phase 2: Platform Deployment**
1. **Desktop Application** - Electron/Tauri with OS keyring
2. **Mobile Applications** - React Native iOS/Android apps
3. **Web Enhancement** - PWA features and offline support
4. **Production Pipeline** - CI/CD deployment workflows
5. **Security Audit** - Validate OS keyring and privacy filtering

---

**📌 Status**: Alice voice pipeline specification complete. Ready for implementation with sub-500ms streaming architecture and privacy-first design.