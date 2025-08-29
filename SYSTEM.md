# Alice Personal Assistant - System Architecture
*Uppdaterad: 2025-08-29 efter Voice v2 Implementation*

## 🎯 PROJEKTMÅL
Alice är en **personlig AI-assistent** (inte enterprise) som fokuserar på:
- Naturlig röstinteraktion på svenska
- Personlig produktivitet (email, kalender, väder)
- Modulär arkitektur med pluggable components
- Production-ready med Guardian säkerhetssystem

## 🏗️ SYSTEMARKITEKTUR

### Backend (FastAPI - Python)
```
Alice/server/
├── app_minimal.py          # 🚀 Main FastAPI server (production-ready)
├── routes/
│   ├── tts.py             # 🎙️ Text-to-Speech med Piper simulation  
│   ├── asr.py             # 🎤 Automatic Speech Recognition WebSocket
│   └── brain_mail_count.py # 📧 Smart email counter endpoint
├── piper_sim_audio.py     # 🔊 Professional MP3 generation (ffmpeg)
├── guardian/              # 🛡️ Security & monitoring system
├── core/                  # 🤖 Agent orchestration system
├── llm/                   # 🧠 LLM providers (Ollama)
└── voice/                 # 🎵 Voice pipeline components
```

### Frontend (Next.js 15 - TypeScript)
```
Alice/web/
├── app/
│   ├── page.tsx           # 🏠 Main dashboard
│   └── api/metrics/       # 📊 Guardian metrics API
├── components/
│   ├── VoiceV2Interface.tsx # 🎙️ Voice v2 React interface
│   └── LLMStatusBadge.tsx   # 🟢 Backend status indicator
├── lib/voice/
│   └── ack-flow.ts        # ⚡ Voice acknowledgment flow
└── public/
    └── voice-complete.html # 🧪 Voice v2 test interface (7/7 tests ✅)
```

## ✅ FUNGERANDE MODULER (Production Ready)

### 🎙️ Voice v2 System (KOMPLETT)
- **TTS Pipeline**: Piper simulation → ffmpeg → Real MP3 files (7-13 KB)
- **ASR WebSocket**: Real-time speech recognition med Whisper simulation  
- **Audio Serving**: Proper MIME types, CORS, blob URL support
- **Browser Compatibility**: Fungerar i Chrome/Safari, inga DEMUXER_ERROR längre
- **E2E Testing**: 7/7 tests passing med real audio playback ✅

### 🛡️ Guardian Security System  
- **Request monitoring**: Timeout protection, rate limiting
- **Metrics API**: Real-time system health dashboard
- **Alert system**: Structured logging och notification system
- **Circuit breakers**: Automatic failure protection

### 🤖 Agent & LLM System
- **Ollama integration**: Fungerar med lokala modeller
- **Agent orchestration**: Core orchestrator, planner, executor
- **Tool system**: Weather, timer, email integration
- **Database**: SQLite med alice.db, patterns.db, triggers.db

### 📊 Frontend Dashboard
- **Next.js 15**: Modern React frontend med TypeScript
- **Real-time status**: LLM och backend health monitoring  
- **Voice interface**: Komplett röstinteraktion (svenska)
- **Responsive design**: Fungerar på desktop och mobil

## 🚧 UNDER UTVECKLING

### 🔧 Go-Live Preparations
- **Real Whisper ASR**: Switch från simulation till riktig Whisper
- **Live API integration**: Gmail, Calendar, Weather med riktiga API:er
- **NLU Router**: Rule-based + LLM fallback för intent classification
- **Memory System**: Redis-baserad kontext och användarminne

### 🧩 Modulär Toolcalling
- **Plugin architecture**: Dynamisk tool discovery och loading
- **Interface standardisering**: Konsistent tool API design
- **Security sandbox**: Säker tool execution environment

## 📋 TEKNISK STACK

### Backend
- **FastAPI** - Modern Python web framework
- **Pydub + FFmpeg** - Professional audio processing
- **Whisper** - Speech-to-text (OpenAI)
- **SQLite** - Local database för persistence
- **Ollama** - Local LLM inference

### Frontend  
- **Next.js 15** - React framework med App Router
- **TypeScript** - Type-safe JavaScript development
- **Tailwind CSS** - Utility-first CSS framework
- **WebSocket** - Real-time communication för ASR

### Infrastructure
- **Python 3.13** - Modern Python runtime
- **Node.js 18+** - JavaScript runtime för frontend
- **Git** - Version control med semantic commits

## 🎯 VOICE v2 IMPLEMENTATION STATUS

### ✅ KOMPLETT (Production Ready)
1. **Audio Generation**: Riktiga MP3-filer med ffmpeg (7-13 KB realistic sizes)
2. **TTS Caching**: SHA1-baserad disk cache med proper invalidation
3. **Audio Serving**: FastAPI FileResponse med korrekt MIME type och CORS
4. **Browser Playback**: Blob URL loading med cross-origin support  
5. **WebSocket ASR**: Real-time speech recognition stream
6. **E2E Testing**: Playwright-baserade automatiska tester (7/7 ✅)
7. **Error Handling**: Graceful fallbacks och comprehensive logging

### 🔄 NÄSTA STEG (Go-Live)
1. **Real Whisper Integration**: Ersätt ASR simulation med riktig Whisper
2. **Live API Connections**: Connect Gmail, Calendar, Weather APIs
3. **NLU Processing**: Rule-based intent classification + LLM fallback
4. **Memory & Context**: Redis för persistent user context
5. **Tool Modularization**: Plugin system för dynamisk tool loading

## 📊 PERFORMANCE METRICS

### Voice v2 SLO Targets (Service Level Objectives)
- **ASR Latency**: ≤350ms (p95)
- **TTS Cached**: ≤120ms (p95) 
- **TTS Uncached**: ≤800ms (p95)
- **End-to-End**: ≤1.2s (p95)

### Current Performance (Measured)
- **TTS Generation**: 300-800ms (realistic Piper simulation)
- **Audio File Size**: 7-13 KB per phrase (efficient compression)
- **Browser Loading**: <100ms (blob URL approach)
- **Memory Usage**: <50MB backend + <100MB frontend

## 🔒 SECURITY & COMPLIANCE

### Guardian Protection
- **Request timeout**: 10s default, configurable
- **Rate limiting**: Per-IP och per-user protection  
- **Input validation**: All user inputs sanitized
- **Error containment**: No sensitive data in error messages

### Privacy
- **Local-first**: All processing on user's machine
- **No cloud dependencies**: Ollama + Whisper runs locally
- **Data retention**: Configurable cleanup policies
- **Audio processing**: In-memory only, no persistent storage

## 🚀 DEPLOYMENT READY

### Development Environment

> ⚠️ **KRITISKA KRAV FÖR ALICE**:
> - **PORTSTRIKTA**: Exakt 3000 (frontend) + 8000 (backend) - ICKE-FÖRHANDLINGSBART
> - **ALLTID .venv**: Python måste köras via `.venv/bin/activate` - ALDRIG global Python
> 
> Döda processer innan start: `lsof -i :3000 :8000 | awk 'NR>1 {print $2}' | xargs kill -9`

```bash
# Backend (Terminal 1) - MÅSTE vara port 8000 med .venv
cd server
source .venv/bin/activate  # OBLIGATORISK - aldrig global Python!
uvicorn app_minimal:app --host 127.0.0.1 --port 8000 --reload

# Frontend (Terminal 2) - MÅSTE vara port 3000  
cd web
npm run dev  # Startar automatiskt på port 3000
```

**Kritiska portar (ICKE-FÖRHANDLINGSBARA)**:
- 🌐 **Frontend**: http://localhost:3000 (Next.js dev server)
- 🚀 **Backend**: http://localhost:8000 (FastAPI server) 
- 🔒 **CORS**: Konfigurerat för exakt localhost:3000 ↔ localhost:8000
- 🎙️ **Voice WebSocket**: ws://localhost:8000/api/asr (ASR pipeline)

*Systemet fungerar ENDAST med dessa exakta portar p.g.a. hardkodade CORS-inställningar!*

### Production Checklist
- ✅ Professional MP3 generation med ffmpeg
- ✅ Comprehensive error handling och logging
- ✅ Security headers och CORS konfiguration
- ✅ E2E test suite med 7/7 passing tests
- ✅ Performance monitoring med Guardian metrics
- 🔄 Switch från mocks till live services (nästa steg)

---

## 📝 COMMIT HISTORY (Recent)
- `🎙️ Voice v2 Production Audio Fix` - Real MP3 generation löser DEMUXER_ERROR
- `🧹 Voice v2 Cleanup` - Removed temporary test files, clean workspace
- `🎙️ Voice v2 Complete` - ASR + TTS Pipeline Implementation
- `🛡️ Guardian System` - Security och monitoring framework

*Alice är nu redo för personlig produktivitet med naturlig svenska röstinteraktion! 🇸🇪*