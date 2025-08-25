# 🎙️ Alice Voice Pipeline Status

## ✅ Current Implementation (v1 - Batch Pipeline)

### **System Status**
- ✅ **OpenAI Integration**: Working with gpt-4o-mini (~1.5s response)
- ✅ **Swedish TTS**: Piper TTS with sv_SE-nst-medium voice
- ✅ **Speech Recognition**: Browser Web Speech API (svenska)
- ✅ **Echo Prevention**: TTS playback blocking during voice input
- ✅ **Audio Playback**: Fixed CSP issues, WAV blob playback working
- ✅ **Feedback Loop**: Prevented with `isTTSPlayingRef` blocking

### **Performance Metrics (Current)**
| Component | Latency | Status |
|-----------|---------|---------|
| Speech Recognition | ~2-3s | ⚠️ Waits for final transcript |
| OpenAI Processing | ~1.5s | ✅ Fast with gpt-4o-mini |
| TTS Generation | ~1.0s | ⚠️ Full file generation |
| Audio Playback | ~0.1s | ✅ Direct blob playback |
| **Total Pipeline** | **~5.5s** | ❌ Too slow for natural conversation |

### **Architecture (Sekventiell)**
```
🎤 Mic → Web Speech API (FINAL) → OpenAI API → Piper TTS → Audio Playback
  2-3s  +        1.5s            +    1s      +    0.1s   = 5.5s total
```

### **Key Optimizations Applied**
- ✅ Parallel TTS generation during typewriter effect
- ✅ Shorter AI responses ("max 2 meningar")
- ✅ CSP policy fixed for blob audio (`media-src 'self' blob:`)
- ✅ Echo feedback prevention
- ✅ Faster typewriter (100ms → 50ms)

---

## 🚀 Next Phase: Streaming Pipeline (v2)

### **Target Architecture (OpenAI Realtime API)**
```
🎤 Mic ──→ OpenAI Realtime WebSocket ──→ Streaming Audio ──→ 🎵 Play
          ASR partials (200ms)        TTS chunks (300ms)
          
Total TTFA (Time-To-First-Audio): <1s
```

### **Benefits**
- ⚡ **<300ms** ASR partials instead of 2-3s final transcript
- 🔄 **Streaming TTS** instead of full file generation
- 🎯 **Sub-second** end-to-end latency
- 🤝 **Barge-in** support (interrupt Alice while speaking)
- 🌍 **Swedish support** with OpenAI's multilingual models

### **Implementation Plan**
1. ✅ Document current pipeline
2. ✅ Commit current optimizations
3. 🔧 Implement OpenAI Realtime WebSocket client
4. 🔧 Replace Web Speech + Piper with streaming
5. 🧪 Test and optimize for <1s latency

---

## 📁 File Structure

### **Frontend (React/Next.js)**
```
/web/
  /components/
    VoiceBox.tsx              # Voice input & visualization (current)
    VoiceRealtimeClient.tsx   # OpenAI Realtime client (planned)
  /app/
    page.jsx                  # Alice Core with voice logic
  next.config.mjs             # CSP config for audio playback
```

### **Backend (Python/FastAPI)**
```
/server/
  app.py                      # TTS endpoints & chat API
  openai_realtime_client.py   # OpenAI Realtime WebSocket handler
  /data/
    *.onnx                    # Piper TTS models (fallback)
```

---

## 🔧 Technical Details

### **Current Voice Flow**
1. **VoiceBox** captures mic input via `getUserMedia()`
2. **Web Speech API** converts to text (waits for final)
3. **handleVoiceInput()** sends to `/api/chat` with OpenAI
4. **Parallel TTS** generates audio while showing typewriter
5. **Audio playback** via blob URLs with echo prevention

### **Known Issues**
- ❌ **High latency**: 5.5s total pipeline time
- ❌ **No interruption**: Can't stop Alice while speaking
- ❌ **Batch processing**: Everything waits for previous step
- ⚠️ **Echo prevention**: Basic blocking, not sophisticated

### **Fixed Issues**
- ✅ Content Security Policy for blob audio
- ✅ TTS python path (python3 vs python)
- ✅ RAG variable scope errors (ctx_text)
- ✅ OpenAI API authentication
- ✅ Audio feedback loops

---

## 📊 Performance Comparison

### **Current (Batch) vs Target (Streaming)**

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Time to First Audio | 5.5s | <1s | **5.5x faster** |
| Speech Recognition | Final only | 200ms partials | **Real-time** |
| TTS Generation | Full file | Streaming chunks | **Progressive** |
| Interruption | None | Barge-in | **Natural conversation** |
| Feedback Prevention | Basic blocking | Smart VAD | **Sophisticated** |

---

## 🎯 Success Criteria for v2

- [ ] **<1s TTFA** (Time-To-First-Audio)
- [ ] **<300ms ASR** partial updates
- [ ] **Barge-in support** (interrupt Alice)
- [ ] **Swedish language** preservation
- [ ] **Natural conversation** flow
- [ ] **Fallback gracefully** to current system if needed

---

*Updated: 2025-08-25*
*Current Status: Ready for OpenAI Realtime implementation*