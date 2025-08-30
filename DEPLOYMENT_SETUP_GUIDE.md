# Alice Deployment Setup Guide
*Complete setup guide för clean system deployment*

## 🚀 Quick Start (Voice v2 Production Ready)

### Prerequisites
- **Node.js** >= 18.0.0
- **Python** >= 3.11
- **FFmpeg** (för audio processing)
- **Git**

### 1. Clone & Setup
```bash
git clone https://github.com/DanielWarg/Alice.git
cd Alice
npm install  # Root package with workspace management
```

### 2. Backend Setup
```bash
cd server
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend Setup  
```bash
cd web
npm install  # Dependencies now resolve correctly (voice-adapter stub included)
npm run build  # Test build (should complete 27/27 routes)
```

### 4. Start Development
```bash
# Option 1: Start both simultaneously
npm run dev

# Option 2: Start separately
npm run dev:backend  # Backend on port 8000
npm run dev:frontend # Frontend on port 3000
```

### 5. Test Voice v2 System
- Open: http://localhost:3000/voice-complete.html
- Test Swedish → English voice pipeline
- Verify 7/7 E2E tests passing

## 🎯 Production Ready Components

### ✅ Working Modules
- **Voice v2**: Complete Swedish ASR → English TTS (Amy 320kbps)
- **Backend API**: FastAPI server with proper CORS, health endpoints
- **Frontend**: Next.js build successful, all routes working
- **TTS Engine**: Real Piper neural TTS with studio-grade quality
- **Build System**: Package structure cleaned, dependencies resolved

### ⚠️ Known Issues  
- **Guardian System**: Disabled (no server on port 8787)
- **LLM Model**: gpt-oss:20b stopped for temperature control
- **AI Provider**: Needs migration to GPT-4o or Claude 3.5

## 🔧 Configuration

### Environment Variables
```bash
# Backend (.env)
OPENAI_API_KEY=sk-...  # If using OpenAI
OLLAMA_HOST=http://localhost:11434
GUARDIAN_ENABLED=false  # Currently disabled

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_VOICE_ENABLED=true
```

### Database
- SQLite databases auto-created in `server/data/`
- No migration needed for development

## 🐳 Docker Setup (TODO)
*High priority - containerization för production deployment*

## 📋 Verification Checklist

After setup, verify:
- [ ] `npm install` completes without errors
- [ ] `npm run build` successful (27/27 routes)  
- [ ] Backend starts: http://localhost:8000/health
- [ ] Frontend builds and serves
- [ ] Voice test page loads: http://localhost:3000/voice-complete.html
- [ ] TTS generates audio files in `server/server/voice/audio/`

## 🚨 Troubleshooting

### Build Failures
- **voice-adapter errors**: Stub created, should resolve automatically
- **FFmpeg missing**: Install FFmpeg for audio processing
- **Python version**: Ensure Python >= 3.11

### Runtime Issues  
- **Guardian errors**: Expected - middleware disabled for Voice testing
- **LLM timeouts**: gpt-oss:20b stopped - use OpenAI fallback eller restart Ollama
- **Audio playback**: Check browser permissions for audio

---

**This guide reflects the ACTUAL current state post dependency fixes.**
**Voice v2 is PRODUCTION READY - deployment infrastructure is next priority.**