# 🎙️ Alice Voice v2 System Overview

**Datum:** 29 augusti 2025  
**Version:** v2.0 - Post-Realtime Architecture  
**Status:** 🚧 **I UTVECKLING**

---

## 🎯 Designfilosofi v2

### **Ut med komplexiteten:**
- ❌ Ingen OpenAI Realtime API (WebRTC-krångel)
- ❌ Ingen streaming audio pipeline  
- ❌ Inga WebSocket-connections för röst

### **In med enkelheten:**
- ✅ **Förprogrammerade ack-fraser** (förprogrammerad, cachad)
- ✅ **Same-TTS consistency** (ack + resultat = samma röst)  
- ✅ **GPT-OSS toolcalling** i backend (ingen realtime)
- ✅ **HTTP TTS endpoint** med disk-cache
- ✅ **Crossfade audio** för smidig upplevelse

---

## 📋 Arkitektur v2

```
┌─────────────────────────────────────────┐
│                FRONTEND                 │
│ 🎙️ Voice v2 - Ack + Crossfade System   │  
├─────────────────────────────────────────┤
│ ✅ Ack-Flow Manager     Status: DEV     │
│ ✅ Audio Crossfader     Status: DEV     │  
│ ✅ TTS Client           Status: DEV     │
│ ✅ Pre-Cache Warmer     Status: DEV     │
└─────────────────────────────────────────┘
                    │
                    │ HTTP TTS Requests
                    ▼
┌─────────────────────────────────────────┐
│             BACKEND - v2                │
│  🎯 TTS Route + Cache + GPT-OSS Tools   │
├─────────────────────────────────────────┤
│ ✅ /api/tts Endpoint    Status: LIVE    │
│ ✅ Disk Cache (MP3)     Status: LIVE    │
│ ✅ Ack Catalog          Status: DEV     │  
│ ✅ GPT-OSS Toolcalling  Status: EXISTING│
│ ✅ Cache Statistics     Status: LIVE    │
└─────────────────────────────────────────┘
                    │
                    │ OpenAI TTS HTTP API
                    ▼
┌─────────────────────────────────────────┐
│           🔊 OPENAI TTS API             │
│    Standard HTTP Audio Generation       │
├─────────────────────────────────────────┤
│ ✅ Model: tts-1/tts-1-hd               │
│ ✅ Voice: nova (konsistent)            │
│ ✅ Rate: 0.25-4.0 support              │
│ ✅ Response: MP3 binary                │
└─────────────────────────────────────────┘
```

---

## 🎬 User Experience Flow

### **Scenario: "Kolla mina mail"**

1. **🎤 User input:** "Kolla mina mail"

2. **⚡ Instant ack (0.1s):**
   ```
   Frontend: startAck("mail.check_unread") 
   → Spelar: "Let me check your inbox for a second..."
   ```

3. **🧠 Backend processing (2-4s parallellt):**
   ```
   GPT-OSS → Planerar → Toolcalling → Gmail API → Resultat
   ```

4. **🎵 Smooth crossfade (0.2s):**
   ```
   announceResult("You have 3 new emails. Would you like me to read them?")
   → Crossfade: ack volume 1.0→0.0, result volume 0.0→1.0  
   ```

5. **🎯 Total perceived latency: ~0.3s** (istället för 6-8s)

---

## 🗂️ Filstruktur v2

```
server/
├── routes/
│   └── tts.py                 # 🆕 TTS HTTP endpoint
├── voice/
│   ├── ack_catalog.json       # 🆕 Förprogrammerade fraser  
│   ├── ack_warmer.py          # 🆕 Pre-cache startup
│   └── audio/                 # 🆕 Disk cache directory
│       ├── cache_index.json   # Cache metadata
│       └── tts_*.mp3          # Cached audio files
└── app_minimal.py             # ✏️ Updated med TTS route

web/
├── lib/
│   └── voice/
│       ├── ack-flow.ts        # 🆕 Ack management
│       ├── audio-crossfade.ts # 🆕 Crossfade logic
│       └── tts-client.ts      # 🆕 TTS HTTP client
└── components/
    └── VoiceV2Interface.tsx   # 🆕 New voice component
```

---

## 🎯 Ack-Catalog Design

### **server/voice/ack_catalog.json**
```json
{
  "default": [
    "Let me check that for you...",
    "One moment...", 
    "Got it. Checking now..."
  ],
  "mail.check_unread": [
    "Let me check your inbox for a second...",
    "Checking your email now...",
    "Looking up your new emails..."
  ],
  "weather.current": [
    "Let me check the weather in {city}...",
    "Checking today's weather for {city}..."
  ],
  "calendar.today": [
    "Let me pull up your schedule for today...",
    "Checking your meetings..."
  ],
  "spotify.play": [
    "Starting your music...",
    "Playing that for you now..."
  ],
  "timer.set": [
    "Setting a timer for {duration}...",
    "Got it. Timer starting now..."
  ]
}
```

### **Parametrar:**
- `{city}` → "Stockholm", "Göteborg"  
- `{duration}` → "10 minutes", "5 minuter"
- `{name}` → "Anna", "Per"

---

## ⚡ Performance Targets v2

| Metric | v1 (Realtime) | v2 (Ack-Flow) | Förbättring |
|--------|---------------|----------------|-------------|
| **Perceived Latency** | 6-8s | 0.1-0.3s | **95% snabbare** |
| **Total System Latency** | 6-8s | 2-4s | 50% snabbare |  
| **Consistency** | Variabel röst | Samma TTS | 100% konsistent |
| **Reliability** | WebRTC issues | HTTP only | 90% mindre fel |
| **Cache Hit Rate** | ~30% | ~80% | Förprogrammerade fraser |

---

## 🛠️ Implementation Steps

### **✅ Fas 1: TTS Infrastructure** 
- [x] TTS HTTP route med caching
- [x] Disk cache med SHA1 nycklar
- [x] Health check endpoints
- [ ] Integration i app_minimal.py

### **🚧 Fas 2: Ack System**
- [ ] Ack catalog med vanliga fraser
- [ ] Pre-cache warmer vid startup  
- [ ] Parameter substitution {city}, {duration}

### **🚧 Fas 3: Frontend v2**
- [ ] Ack-flow manager
- [ ] Audio crossfade logic
- [ ] TTS client integration

### **🚧 Fas 4: Integration**  
- [ ] Koppla ack-intents till GPT-OSS tools
- [ ] Ersätt gamla voice interface
- [ ] Performance validation

---

## 🧪 Testing Strategy

### **Unit Tests**
- TTS caching functionality
- Ack phrase selection
- Parameter substitution
- Crossfade timing

### **Integration Tests**  
- Complete ack-flow scenarios
- Cache hit/miss performance
- Audio quality validation
- Multi-user cache consistency

### **Performance Tests**
- Perceived latency measurement
- Cache warming time
- Concurrent TTS requests
- Disk space usage

---

## 🚀 Deployment Considerations

### **Environment Variables**
```bash
# OpenAI TTS
OPENAI_API_KEY=sk-...
OPENAI_TTS_MODEL=tts-1        # eller tts-1-hd för högre kvalitet

# Cache Settings
AUDIO_DIR=./server/voice/audio
TTS_CACHE_SIZE_MB=500
TTS_CACHE_TTL_DAYS=30
```

### **Disk Requirements**
- **Base cache:** ~50MB (20 ack-fraser)
- **Per user/dag:** ~5-10MB typiskt
- **Cache rotation:** 30 dagar standard

### **Performance Monitoring**
- Cache hit rates per intent
- TTS generation times  
- Perceived latency metrics
- Audio playback success rates

---

## 💡 Future Optimizations

### **Fas 2 (Optional)**
- **Språkstöd:** Svenska ack-fraser med svensk TTS
- **Personalization:** User-specific cache warming
- **Compression:** OPUS istället för MP3 för mindre filer

### **Fas 3 (Advanced)**
- **Pre-generation:** AI-genererade ack-variationer
- **Context-aware acks:** "Checking your calendar for this week..."
- **Sentiment matching:** Enthusiastic vs neutral acks

---

## ✅ Success Criteria

### **Functional Requirements**
- ✅ Perceived latency <0.5s för ack-fase  
- ✅ Samma röst-timbre för ack + resultat
- ✅ 95% cache hit rate för vanliga ack-fraser
- ✅ Graceful fallback om TTS misslyckas

### **Non-Functional Requirements**  
- ✅ HTTP-only (inget WebRTC/WebSocket)
- ✅ Disk cache <1GB standard användning
- ✅ Zero-config för vanliga use-cases
- ✅ Bakåtkompatibilitet med GPT-OSS tools

---

**Voice v2 Design Doc Complete** 🎉  
*Ready for implementation with clear scope and performance targets*