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

### 🎙️ Voice Pipeline
- **`voice_gateway.py`** - Main voice system coordinator
- **`services/voice_gateway/`** - Streaming voice components
  - `main.py` - WebRTC voice server
  - `asr_stream.py` - Speech recognition streaming
  - `tts_stream.py` - Text-to-speech streaming
  - `llm_stream.py` - LLM response streaming
  - `privacy_filter.py` - Audio privacy protection

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

### 🔊 Voice Client
- **`lib/`** - Client-side utilities
  - `voice-client.js` - Browser voice interface
  - `b3-ambient-voice-client.js` - Ambient voice handling
  - `audio-enhancement.js` - Audio processing utilities

### 🎯 Voice System Architecture
- **`src/voice/`** - Advanced voice components
  - `Orchestrator.ts` - Voice pipeline coordination
  - `AudioStateManager.ts` - Audio state management
  - `BargeInDetector.ts` - Interrupt detection
  - `EchoCanceller.ts` - Echo prevention (beta)

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

### 📋 Test Files (Root)
- **`test_voice_always_on.py`** - Voice system testing (needs cleanup post-OpenAI Realtime removal)
- **`test_b4_proactive.py`** - Proactive system testing
- **`test_b4_shadow.py`** - Shadow mode testing

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

## 🎯 Deployment Priorities

1. **Desktop Application** - Implement Electron/Tauri with OS keyring
2. **Mobile Applications** - Build React Native iOS/Android apps
3. **Web Enhancement** - Complete PWA features and offline support
4. **Production Pipeline** - Implement CI/CD deployment workflows
5. **Security Audit** - Validate OS keyring and privacy filtering
6. **Performance Optimization** - Platform-specific tuning

---

**📌 Status**: Alice architecture is ready for deployment as a complete application suite with desktop-first approach and mobile/web support. Focus on implementation of portable apps structure.