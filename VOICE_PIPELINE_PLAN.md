# 🎙️ Alice Voice Pipeline Implementation Plan - Universal Swedish→English

## Vision
Bygga en komplett, modulär voice pipeline för Alice som hanterar **ALL svensk input** och producerar **engelsk voice output**:
- **GPT-OSS** som huvudhjärna (orchestration, översättning, beslut)
- **OpenAI Realtime API** för premium engelska TTS med låg latens
- **Universal Swedish input** → **English voice output** för alla interaktioner
- **Modulär arkitektur** som fungerar för chat, mail, commands, dokument, etc.

## Arkitektur Overview

```
[Svensk Input Source]
    ├── Chat Messages
    ├── Email
    ├── Calendar Events
    ├── Documents
    ├── Voice Commands
    └── System Notifications
            ↓
    [Language Detector]
            ↓
    [Guardian PII Filter]
            ↓
    [GPT-OSS Orchestrator]
        ├── Translate to English
        ├── Determine tone/style
        └── Format for speech
            ↓
    [OpenAI Realtime API]
        ├── Text response
        └── Audio stream
            ↓
    [Output Channels]
        ├── Audio Player (English voice)
        ├── HUD Text (Swedish original + English)
        └── Cache Storage
```

## Implementation Plan

### Phase 1: Universal Voice Module Foundation (Dag 1-2)

**1. Core Voice Module Structure:**
```
server/voice/
├── __init__.py
├── voice_orchestrator.py      # Universal orchestrator för alla input types
├── input_processor.py         # Hantera olika input källor
├── language_service.py        # Svensk→Engelsk översättning
├── realtime_client.py         # OpenAI Realtime API
├── audio_streaming.py         # Audio format & streaming
├── voice_cache.py            # Intelligent caching
└── config.py                 # Voice pipeline configuration
```

**2. Input Processor - Hantera alla svenska källor:**
```python
class UniversalInputProcessor:
    def process_chat_message(text: str) -> InputPackage
    def process_email(email: dict) -> InputPackage
    def process_calendar_event(event: dict) -> InputPackage
    def process_document(doc: str) -> InputPackage
    def process_notification(notif: dict) -> InputPackage
    def process_voice_command(cmd: str) -> InputPackage
```

**3. Translation Service med GPT-OSS:**
```python
class SwedishToEnglishTranslator:
    def translate(
        swedish_text: str,
        context_type: str,  # "chat", "email", "calendar", etc.
        preserve: List[str]  # namn, datum, tal som ska bevaras
    ) -> TranslationResult:
        # Använd GPT-OSS för intelligent, kontextmedveten översättning
        return {
            "original_swedish": swedish_text,
            "english_speech": "...",  # Optimerad för uppläsning
            "english_display": "...", # För text display
            "tone": "neutral",        # eller cheerful, formal, urgent
            "emphasis_words": []      # Ord att betona i tal
        }
```

### Phase 2: Realtime API Integration (Dag 3-4)

**4. OpenAI Realtime Client:**
```python
class RealtimeVoiceClient:
    async def create_session(voice="marin")
    async def send_text(text: str, tone: str)
    async def stream_audio() -> AsyncIterator[bytes]
    async def close_session()
```

**5. Audio Streaming Pipeline:**
- WebRTC för lägsta latens
- WebSocket som fallback
- Chunked streaming för snabb start
- Buffer management för smooth playback

**6. Multi-Input Queue System:**
```python
class VoiceQueue:
    def add_item(input_package: InputPackage, priority: int)
    def get_next() -> InputPackage
    def preprocess_upcoming()  # Förberedd nästa medan nuvarande spelas
```

### Phase 3: Integration Points (Dag 5-6)

**7. Chat Integration:**
```python
# I app_minimal.py chat endpoint
if swedish_detected and voice_enabled:
    voice_response = await voice_orchestrator.process_chat(
        user_message,
        user_context
    )
    return {
        "text": response,
        "voice_url": voice_response.audio_url,
        "translation": voice_response.english_text
    }
```

**8. Email Integration:**
```python
class EmailVoiceProcessor:
    async def process_new_emails():
        emails = fetch_swedish_emails()
        for email in emails:
            voice_package = await voice_orchestrator.process_email(
                subject=email.subject,
                body=email.body,
                sender=email.sender
            )
            queue.add(voice_package)
```

**9. Calendar Integration:**
```python
class CalendarVoiceProcessor:
    async def announce_event(event):
        if event.language == "sv":
            voice_package = await voice_orchestrator.process_calendar(
                title=event.title,
                time=event.start_time,
                attendees=event.attendees
            )
            play_immediately(voice_package)
```

### Phase 4: Frontend Universal Voice UI (Dag 7-8)

**10. Universal Voice HUD:**
```typescript
// web/components/voice/UniversalVoiceHUD.tsx
interface VoiceHUDProps {
    sourceType: "chat" | "email" | "calendar" | "document" | "notification"
    originalSwedish: string
    englishTranslation: string
    audioStream: MediaStream
    metadata: any
}

const UniversalVoiceHUD = () => {
    return (
        <div className="voice-hud">
            <SourceIndicator type={sourceType} />
            <DualLanguageDisplay 
                swedish={originalSwedish}
                english={englishTranslation}
            />
            <AudioControls stream={audioStream} />
            <VoiceSelector currentVoice={voice} />
        </div>
    )
}
```

**11. Real-time Audio Player:**
```typescript
class StreamingAudioPlayer {
    constructor(private realtimeEndpoint: string)
    async start(text: string, voice: string)
    pause()
    resume()
    setSpeed(rate: number)
    setVolume(level: number)
}
```

**12. Language Toggle Display:**
- Visa både svensk original och engelsk översättning
- Highlighta current spoken word
- Synca text med audio playback

### Phase 5: Advanced Features (Dag 9-10)

**13. Context-Aware Translation:**
```python
CONTEXT_RULES = {
    "chat": {
        "tone": "conversational",
        "formality": "casual",
        "speed": "normal"
    },
    "email": {
        "tone": "professional",
        "formality": "formal",
        "speed": "clear"
    },
    "calendar": {
        "tone": "informative",
        "formality": "neutral",
        "speed": "slightly_fast"
    },
    "urgent_notification": {
        "tone": "alert",
        "formality": "direct",
        "speed": "fast"
    }
}
```

**14. Smart Caching Strategy:**
```python
class IntelligentVoiceCache:
    def cache_key(text, voice, tone) -> str
    def should_cache(input_type, frequency) -> bool
    def preload_common_phrases()  # "Nytt meddelande", "Möte om", etc.
    def cleanup_old_entries()
```

**15. Batch Processing:**
```python
class BatchVoiceProcessor:
    async def process_multiple(items: List[InputPackage]):
        # Gruppera liknande items
        # Översätt i batch med GPT-OSS
        # Queue för Realtime API
        # Returnera alla audio URLs
```

### Phase 6: Production Features (Dag 11-12)

**16. Monitoring & Analytics:**
```python
VOICE_METRICS = {
    "translation_latency": histogram,
    "tts_latency": histogram,
    "cache_hit_rate": gauge,
    "daily_translations": counter,
    "api_costs": counter,
    "user_satisfaction": gauge  # Från feedback
}
```

**17. Cost Optimization:**
- Cache frequent translations
- Batch API calls där möjligt
- Use cheaper models för simple translations
- Implement daily/monthly limits

**18. Error Handling & Fallbacks:**
```python
FALLBACK_CHAIN = [
    ("openai_realtime", "Premium quality"),
    ("openai_tts", "Standard quality"),
    ("elevenlabs", "Alternative service"),
    ("piper_local", "Offline backup"),
    ("text_only", "No audio available")
]
```

## Configuration

**.env additions:**
```env
# Voice Pipeline Configuration
VOICE_INPUT_LANGUAGE=sv
VOICE_OUTPUT_LANGUAGE=en
VOICE_DEFAULT_VOICE=marin
VOICE_FALLBACK_VOICE=cedar

# API Keys
OPENAI_REALTIME_KEY=sk-...
ELEVENLABS_API_KEY=...  # Backup

# Performance
VOICE_CACHE_SIZE_MB=500
VOICE_QUEUE_SIZE=100
VOICE_PRELOAD_COMMON=true

# Features
VOICE_ENABLE_CHAT=true
VOICE_ENABLE_EMAIL=true
VOICE_ENABLE_CALENDAR=true
VOICE_ENABLE_DOCUMENTS=true
```

## API Endpoints

```python
# Voice Pipeline Endpoints
POST /api/voice/translate
    body: {
        text: str,
        source_type: str,
        priority: int,
        voice?: str,
        tone?: str
    }
    
GET /api/voice/stream/{session_id}
    SSE stream of audio chunks
    
POST /api/voice/batch
    body: {
        items: Array<TranslationRequest>
    }
    
GET /api/voice/status
    Current queue, active sessions, metrics
```

## Success Metrics

- **Universal Coverage**: 100% av svensk text kan processas
- **Translation Quality**: >95% accuracy (manuell verifiering)
- **End-to-end Latency**: 
  - Chat: <1.5s till första ljud
  - Email: <2s till första ljud
  - Notifications: <500ms till första ljud
- **Cache Performance**: >40% hit rate efter 1 vecka
- **Cost Efficiency**: <$0.01 per översättning
- **Audio Quality**: Ingen stuttering, clear pronunciation
- **Uptime**: 99.9% availability

## Testing Strategy

```python
tests/voice/
├── test_swedish_input_types.py    # Testa alla input källor
├── test_translation_accuracy.py   # Verifiera översättningar
├── test_realtime_streaming.py     # Audio streaming
├── test_cache_efficiency.py       # Cache hit rates
├── test_fallback_chain.py        # Alla fallback scenarios
└── test_e2e_pipeline.py          # Full pipeline test
```

## Rollout Plan

1. **Week 1**: Chat messages (mest använt)
2. **Week 2**: Email integration
3. **Week 3**: Calendar & notifications
4. **Week 4**: Documents & long-form content
5. **Week 5**: Voice commands & real-time interaction

## Current Status

- **Agent Integration**: ✅ KOMPLETT - Alice kan nu använda tools (tid, kalender, musik) via agent orchestrator
- **Chat Fallback**: ✅ KOMPLETT - Automatisk fallback från agent tools till LLM för generella frågor
- **Database**: ✅ KOMPLETT - Chat history och user sessions fungerar
- **Guardian**: ✅ KOMPLETT - Production-ready protection och monitoring
- **LLM Pipeline**: ✅ KOMPLETT - Ollama + OpenAI fallback fungerar perfekt

**Nästa steg**: Implementera voice pipeline som nästa stora feature!

---
*Detta dokument innehåller den kompletta planen för att bygga en universal voice pipeline som hanterar ALL svensk input och producerar professionell engelsk voice output.*