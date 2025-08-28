# 🚀 Alice Project - Quick Start Guide

**Get started with Alice - but read this first if you're new!**

---

## 🚨 **IMPORTANT: Read this first if you're a new developer**

**Alice has impressive functionality but the voice pipeline is unstable.**

🟢 **What works well:**
- Text chat with Swedish responses (2-4s response time) 
- Basic voice input and TTS
- Spotify, calendars, tools

🔴 **Known voice issues:**
- Echo loops (Alice hears her own voice)
- Unstable test interfaces (buttons don't work)
- "Messy" behavior in conversations
- Partial detection can be unreliable

**🎯 If voice is messy → jump directly to [🔧 Troubleshooting](#-troubleshooting-voice-issues)**

---

## 🎯 **What is Alice? (Realistic description)**

Alice is a **private Swedish AI assistant** with:
- 🎙️ **Experimental voice response** (~700ms when it works) with LiveKit-style streaming  
- 🤖 **Stable local AI** with gpt-oss:20b (no data sent to cloud)
- 🇸🇪 **Reliable Swedish** language support and cultural understanding
- 🛠️ **Working tools** for calendar, weather, Spotify, Gmail, etc.

---

## 📋 **Quick check (30 seconds)**

Run this first to see if everything is installed:

```bash
echo "🔍 Checking dependencies..." && \
python3 --version && \
node --version && \
ollama --version && \
echo "✅ All prerequisites found!"
```

**Missing something?** See [Installation](#-installation-missing-something) below.

---

## ⚡ **EASIEST START (2 minutes)**

### 1. Navigate to project folder
```bash
cd /Users/evil/Desktop/EVIL/PROJECT/Alice
```

### 2. Run startup script
```bash
./start_alice.sh
```

### 3. Wait for "All systems ready!" message

### 4. Open Alice
```bash
open http://localhost:3000
```

**🎉 Done! Alice is now running with sub-second voice response.**

---

## 🎙️ **Test Voice Function**

When Alice is running, test the new voice functions:

### LiveKit-Style Streaming Voice
1. **Open test interface**: `open test_streaming_voice.html`
2. **Click "🎤 Start Recording"**
3. **Say**: "What's the weather in Göteborg today"
4. **See TTFA measurement**: Should show ~700ms to first audio

### In Main App
1. **Open**: http://localhost:3000
2. **Click voice button** (or say "Hey Alice")
3. **Test Swedish commands**: 
   - "Vad är klockan?"
   - "Skapa ett möte imorgon"
   - "Spela musik"

---

## 🔧 **Troubleshooting voice issues**

### If voice is "messy" or echoing
```bash
# 1. Restart Alice completely
pkill -f "python.*run.py"; pkill -f "npm run dev"; pkill -f "ollama serve"
sleep 5
./start_alice.sh

# 2. Test specifically the voice pipeline
open test_streaming_voice.html
# Click Connect → Start Recording
# If buttons don't work = known issue
```

### If test page doesn't work
- **Known Issue**: Test buttons are broken
- **Workaround**: Use main app http://localhost:3000
- **Focus**: We're working on fixing this

### If echo loops (Alice hears herself)
```bash
# Temporary fix: use headphones instead of speakers
# Or manually mute mic during Alice's responses
# This is our #1 problem to solve
```

### Report voice issues
If you find new voice issues, document:
1. What you said
2. What Alice heard (transcript)
3. What happened (echo/double response/nothing)
4. Browser & OS version

---

## 🛠️ **Manual Setup (if script doesn't work)**

### Quick parallel start (advanced)
```bash
cd /Users/evil/Desktop/EVIL/PROJECT/Alice

# Start everything in parallel for fastest startup
(cd server && source ../.venv/bin/activate && python3 -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload) &
(cd web && npm run dev) &
(ollama serve > /dev/null 2>&1) &

# Wait for everything to start
sleep 10

echo "🔍 System Status:"
curl -s http://localhost:8000/api/v1/llm/status >/dev/null && echo "✅ Backend ready"
curl -s http://localhost:3000 >/dev/null && echo "✅ Frontend ready" 
curl -s http://localhost:11434/api/tags >/dev/null && echo "✅ Ollama ready"

echo "🎉 Alice ready at: http://localhost:3000"
```

### Step-by-step troubleshooting
```bash
# 1. Fix dependencies
cd /Users/evil/Desktop/EVIL/PROJECT/Alice
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
cd web && npm install && cd ..

# 2. Start backend
cd server && python3 -m uvicorn app:app --host 127.0.0.1 --port 8000 &

# 3. Start frontend
cd web && npm run dev &

# 4. Check Ollama
ollama serve > /dev/null 2>&1 &
```

---

## 🎯 **Final check - Everything should work**

Run this verification:

```bash
echo "🔍 Final System Check:"
curl -s http://localhost:8000/api/tools/spec >/dev/null && echo "✅ Backend OK" || echo "❌ Backend FAIL"
curl -s http://localhost:3000 >/dev/null && echo "✅ Frontend OK" || echo "❌ Frontend FAIL"  
curl -s http://localhost:11434/api/tags >/dev/null && echo "✅ AI OK" || echo "❌ AI FAIL"
curl -s http://localhost:8000/api/v1/llm/status >/dev/null && echo "✅ LLM System OK" || echo "❌ LLM System FAIL"
```

**Expected output:**
```
🔍 Final System Check:
✅ Backend OK
✅ Frontend OK
✅ AI OK
✅ LLM System OK
```

---

## 🌐 **Open Alice**

When all ✅ are shown, open the browser:

**🎯 http://localhost:3000**

You should now see:
- 🎨 **Alice HUD** with glassmorphism design
- 🤖 **LLM Status Badge** showing "gpt-oss:20b (healthy)"
- 🎙️ **VoiceStreamClient** for LiveKit-style streaming voice
- 📊 **TTFA metrics** and real-time performance
- ⚡ **Sub-second voice response** (~700ms Time-To-First-Audio)

---

## 🚨 **If something doesn't work**

### Port conflicts
```bash
# Check which processes are using the ports
lsof -i :8000 && lsof -i :3000 && lsof -i :11434
# Kill conflicting processes
kill -9 <PID>
```

### Virtual Environment issues
```bash
# Total reset of venv
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt python-multipart httpx
```

### Dependencies issues
```bash
# Frontend dependencies
cd web && rm -rf node_modules package-lock.json && npm install

# Backend dependencies  
source .venv/bin/activate
pip install --upgrade pip
pip install -r server/requirements.txt python-multipart httpx
```

---

## 🔄 **Restart Everything**

If you need to restart the entire system:

```bash
# Stop everything
pkill -f "python.*run.py"; pkill -f "npm run dev"; pkill -f "ollama serve"

# Wait 5 seconds
sleep 5

# Restart with manual setup above
```

---

## 📱 **Smart Startup Script**

Create this for future one-click start:

```bash
#!/bin/bash
# save as: ~/alice-start.sh

cd /Users/evil/Desktop/EVIL/PROJECT/Alice

echo "🚀 Starting Alice Project..."

# Fix venv if broken
source .venv/bin/activate 2>/dev/null || {
  echo "🔧 Recreating virtual environment..."
  rm -rf .venv
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r server/requirements.txt python-multipart httpx
}

# Clean up ports
pkill -f "python.*run.py" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
sleep 2

# Start backend
cd server && python run.py &
sleep 5

# Start frontend  
cd ../web && npm run dev &
sleep 5

# Verify all systems
echo "🔍 System Status:"
curl -s http://localhost:8000/api/tools/spec >/dev/null && echo "✅ Backend" || echo "❌ Backend"
curl -s http://localhost:3000 >/dev/null && echo "✅ Frontend" || echo "❌ Frontend"
curl -s http://localhost:11434/api/tags >/dev/null && echo "✅ AI" || echo "❌ AI"

echo ""
echo "🎉 Alice is ready!"
echo "🌐 Open: http://localhost:3000"
```

**Make it executable:**
```bash
chmod +x ~/alice-start.sh
```

**Run Alice anytime:**
```bash
~/alice-start.sh
```

---

---

## 💾 **Installation (missing something?)**

### Python 3.9+
```bash
# macOS with Homebrew
brew install python3

# Check version
python3 --version  # Should be 3.9+
```

### Node.js 18+
```bash
# macOS with Homebrew  
brew install node

# Check version
node --version      # Should be 18+
```

### Ollama + gpt-oss model
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download gpt-oss:20b model (once)
ollama pull gpt-oss:20b

# Check that model exists
ollama list | grep gpt-oss
```

### Virtual environment (Python dependencies)
```bash
cd /Users/evil/Desktop/EVIL/PROJECT/Alice
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
```

---

## 🚀 **Performance & Improvements**

### Alice v2.1 vs v1.0 Comparison
| Metric | v1 Batch | v2.1 LiveKit-Style | Improvement |
|--------|----------|---------------------|-------------|
| First audio | ~5.5s | ~700ms | **7.8x faster** |
| Voice processing | Waits for final version | Stable partial (250ms) | **Real-time** |
| TTS Audio | Entire sentences | Micro-chunks (3-5 words) | **Progressive** |
| Echo control | Simple blocking | Smart mute/unmute | **Sophisticated** |

### Test Streaming Voice Features
- ✅ **Stable Partial Detection** - Triggers on 250ms stability
- ✅ **Micro-Chunked TTS** - 3-5 word chunks with 20ms delay  
- ✅ **TTFA Measurement** - Real-time performance metrics
- ✅ **Smart Echo Control** - Mute during TTS playback

---

**🎯 Alice should now start in 2 minutes with sub-second voice response!**

For technical support, see [VOICE_PIPELINE_STATUS.md](VOICE_PIPELINE_STATUS.md) or [docs/VOICE_SETUP.md](docs/VOICE_SETUP.md).