# Alice API Documentation

Komplett API-dokumentation för Alice AI Assistant Platform. Alice tillhandahåller REST API endpoints, WebSocket-anslutningar och ett omfattande verktygsekosystem.

## Översikt

Alice API består av flera huvudkomponenter:

- **REST API**: Huvudsakliga HTTP endpoints för chat, TTS, verktygsexekvering
- **Voice Pipeline**: OpenAI Realtime API integration med WebRTC streaming
- **WebSocket**: Real-time kommunikation för HUD-uppdateringar och voice streaming
- **NLU Agent**: Naturlig språkförståelse och intent-klassificering
- **Agent Bridge**: Server-Sent Events (SSE) för streaming agent responses
- **Verktygsystem**: Modulärt system för utökbar funktionalitet

**Base URLs:**
- Backend API: `http://localhost:8000`
- Frontend API: `http://localhost:3000/api` (Next.js API routes)
- NLU Agent: `http://localhost:7071`
- WebSocket: `ws://localhost:8000/ws/alice`
- Voice WebSocket: `ws://localhost:8000/ws/voice/{session_id}`

## Autentisering

Alice använder för närvarande ingen autentisering för lokala installationer. För production-deployment, implementera API-nycklar eller OAuth.

```http
# Headers för framtida autentisering
Authorization: Bearer <api-token>
X-API-Key: <api-key>
```

## REST API Endpoints

### Chat & Konversation

#### POST /api/chat
Skicka textmeddelanden till Alice och få intelligent svar.

**Request:**
```http
POST /api/chat
Content-Type: application/json

{
  "prompt": "spela musik",
  "provider": "auto",
  "context": "living_room",
  "user_id": "user123"
}
```

**Request Parameters:**
| Parameter | Type | Required | Default | Beskrivning |
|-----------|------|----------|---------|-------------|
| `prompt` | string | ✓ | - | Användarens textinput |
| `provider` | string | | "auto" | AI provider ("auto", "ollama", "openai") |
| `context` | string | | null | Kontextuell information |
| `user_id` | string | | null | Användar-ID för personalisering |

**Response:**
```json
{
  "text": "Spelar musik nu.",
  "provider": "ollama", 
  "engine": "gpt-oss:20b",
  "confidence": 0.95,
  "execution_time_ms": 245,
  "meta": {
    "tool": {
      "name": "PLAY",
      "args": {},
      "source": "router",
      "executed": true,
      "latency_ms": 12.3
    },
    "intent": {
      "name": "MEDIA_PLAY",
      "confidence": 0.98
    }
  }
}
```

**Error Responses:**
```json
// 400 Bad Request
{
  "error": "invalid_prompt",
  "message": "Prompt cannot be empty",
  "code": 400
}

// 500 Internal Server Error  
{
  "error": "ai_processing_failed",
  "message": "Failed to process with AI model",
  "code": 500
}
```

#### POST /api/chat/stream
Streaming chat för real-time svar (Server-Sent Events).

**Request:**
```http
POST /api/chat/stream
Content-Type: application/json
Accept: text/event-stream

{
  "prompt": "berätta en historia",
  "stream": true,
  "provider": "auto"
}
```

**Response Stream:**
```
data: {"type":"start","timestamp":"2025-01-20T10:30:00Z"}

data: {"type":"token","text":"Det","delta":"Det"}

data: {"type":"token","text":"Det var","delta":" var"}

data: {"type":"meta","meta":{"tool":null,"processing_time":150}}

data: {"type":"final","text":"Det var en gång...","complete":true}

data: [DONE]
```

### Verktygsexekvering

#### POST /api/tools/exec
Exekvera specifika verktyg direkt.

**Request:**
```http
POST /api/tools/exec
Content-Type: application/json

{
  "tool": "SET_VOLUME",
  "args": {
    "level": 75
  },
  "context": {
    "device": "spotify_player",
    "room": "living_room"
  }
}
```

**Available Tools:**
| Tool | Beskrivning | Arguments |
|------|------------|-----------|
| `PLAY` | Starta uppspelning | `{}` |
| `PAUSE` | Pausa uppspelning | `{}` |
| `STOP` | Stoppa uppspelning | `{}` |
| `NEXT` | Nästa spår | `{}` |
| `PREV` | Föregående spår | `{}` |
| `SET_VOLUME` | Ställ volym | `{"level": 0-100}` eller `{"delta": ±N}` |
| `MUTE` | Stäng av ljud | `{}` |
| `UNMUTE` | Sätt på ljud | `{}` |
| `SHUFFLE` | Slumpmässig ordning | `{"enabled": true/false}` |
| `REPEAT` | Upprepa läge | `{"mode": "off"/"one"/"all"}` |
| `LIKE` | Gilla aktuellt spår | `{}` |
| `UNLIKE` | Ogilla spår | `{}` |

**Response:**
```json
{
  "ok": true,
  "message": "Volym satt till 75%",
  "tool": "SET_VOLUME",
  "args": {"level": 75},
  "execution_time_ms": 45,
  "timestamp": "2025-01-20T10:30:00Z"
}
```

#### GET /api/tools/spec
Hämta specifikationer för alla tillgängliga verktyg.

**Response:**
```json
[
  {
    "name": "SET_VOLUME",
    "description": "Kontrollera volymnivå",
    "parameters": {
      "type": "object",
      "properties": {
        "level": {
          "type": "integer",
          "minimum": 0,
          "maximum": 100,
          "description": "Absolut volymnivå (0-100)"
        },
        "delta": {
          "type": "integer", 
          "minimum": -100,
          "maximum": 100,
          "description": "Relativ volymändring"
        }
      },
      "anyOf": [
        {"required": ["level"]},
        {"required": ["delta"]}
      ]
    },
    "enabled": true
  }
]
```

#### GET /api/tools/enabled
Lista aktiverade verktyg.

**Response:**
```json
{
  "enabled_tools": ["PLAY", "PAUSE", "SET_VOLUME", "NEXT", "PREV"],
  "total_available": 12,
  "configuration_source": "environment"
}
```

### Enhanced Text-till-Tal (TTS)

#### POST /api/tts/synthesize
Förbättrad röstsyntes med emotioner, personlighet och caching.

**Request:**
```http
POST /api/tts/synthesize
Content-Type: application/json

{
  "text": "Hej! Jag är Alice, din AI-assistent.",
  "voice": "sv_SE-nst-high",
  "speed": 1.0,
  "emotion": "friendly",
  "personality": "alice",
  "pitch": 1.0,
  "volume": 1.0,
  "cache": true
}
```

**Parameters:**
| Parameter | Type | Default | Beskrivning |
|-----------|------|---------|-------------|
| `text` | string | - | Text att syntetisera |
| `voice` | string | "sv_SE-nst-medium" | Röstmodell |
| `speed` | float | 1.0 | Talhastighet (0.5-2.0) |
| `emotion` | string | null | Emotionell ton |
| `personality` | string | "alice" | Personlighet |
| `pitch` | float | 1.0 | Rösttonhöjd (0.8-1.2) |
| `volume` | float | 1.0 | Ljudvolym (0.1-1.0) |
| `cache` | boolean | true | Använd cache |

**Available Voices:**
- `sv_SE-nst-medium` - Svensk kvinnlig röst (medium kvalitet, naturalness: 7/10)
- `sv_SE-nst-high` - Svensk kvinnlig röst (hög kvalitet, naturalness: 8/10)
- `sv_SE-lisa-medium` - Svensk kvinnlig röst (medium kvalitet, naturalness: 8/10)

**Available Emotions:**
- `neutral` - Neutral ton
- `happy` - Glad och energisk
- `calm` - Lugn och avslappnad
- `confident` - Självsäker och bestämd
- `friendly` - Vänlig och tillgänglig

**Available Personalities:**
- `alice` - Energisk AI-assistent (speed: 1.05, pitch: 1.02)
- `formal` - Professionell och auktoritativ (speed: 0.95, pitch: 0.98)
- `casual` - Avslappnad och konversationell (speed: 1.1, pitch: 1.05)

**Response:**
```json
{
  "success": true,
  "audio_data": "UklGRjY3AgBXQVZFZm10IBAAAAABAAEA...", 
  "format": "wav",
  "voice": "sv_SE-nst-high",
  "text": "Hej! Jag är Alice, din AI-assistent.",
  "emotion": "friendly",
  "personality": "alice",
  "cached": false,
  "settings": {
    "speed": 1.05,
    "pitch": 1.02,
    "emotion": "friendly",
    "confidence": 0.85
  },
  "quality_score": 8
}
```

#### GET /api/tts/voices
Hämta tillgängliga röstmodeller och deras egenskaper.

**Response:**
```json
{
  "voices": [
    {
      "id": "sv_SE-nst-high",
      "name": "Sv SE Nst High",
      "language": "Swedish",
      "quality": "high",
      "gender": "female",
      "naturalness": 8,
      "supported_emotions": ["neutral", "happy", "calm", "confident", "friendly"],
      "supported_personalities": ["alice", "formal", "casual"]
    }
  ],
  "default_voice": "sv_SE-nst-medium",
  "emotions": ["neutral", "happy", "calm", "confident", "friendly"],
  "personalities": ["alice", "formal", "casual"]
}
```

#### POST /api/tts/stream
Streaming TTS för snabbare responstider.

**Request:** Samma som `/api/tts/synthesize`
**Response:** Streaming audio/wav data

#### GET /api/tts/personality/{personality}
Hämta personlighetsspecifika röstinställningar.

**Response:**
```json
{
  "personality": "alice",
  "settings": {
    "speed": 1.05,
    "pitch": 1.02,
    "emotion_bias": "friendly",
    "confidence": 0.85
  },
  "description": "Energisk, vänlig AI-assistent med naturlig svenska"
}
```

**Användning i JavaScript:**
```javascript
async function playTTSAudio() {
  const response = await fetch('/api/tts/synthesize', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      text: 'Hej från Alice!',
      voice: 'sv_SE-nst-medium'
    })
  });
  
  const data = await response.json();
  if (data.success) {
    const audioBuffer = Uint8Array.from(atob(data.audio_data), c => c.charCodeAt(0));
    const blob = new Blob([audioBuffer], { type: 'audio/wav' });
    const audio = new Audio(URL.createObjectURL(blob));
    await audio.play();
  }
}
```

## Voice Pipeline API

Alice's advanced voice pipeline provides two complementary approaches for voice interaction:

### VoiceBox (Basic Voice Interface)
- Browser Speech Recognition API
- Real-time audio visualization 
- Swedish speech post-processing
- Alice backend TTS integration

### VoiceClient (Advanced OpenAI Realtime)
- OpenAI Realtime API with WebRTC streaming
- Low-latency voice interaction
- Agent bridge for streaming responses
- Professional-grade audio processing

### OpenAI Realtime Integration

#### GET /api/realtime/ephemeral
Create ephemeral session for OpenAI Realtime API.

**Response:**
```json
{
  "client_secret": {
    "value": "your-openai-api-key"
  },
  "ephemeral_key_id": "ephemeral_1234567890",
  "model": "gpt-4o-realtime-preview",
  "voice": "alloy",
  "expires_at": "2025-01-21T10:30:00Z"
}
```

**Usage in VoiceClient:**
```javascript
const session = await fetch('/api/realtime/ephemeral').then(r => r.json());
// Session används för att initiera WebRTC connection
```

#### POST /api/tts/openai-stream
Stream TTS audio från OpenAI eller Alice backend.

**Request:**
```http
POST /api/tts/openai-stream
Content-Type: application/json

{
  "text": "Hej från Alice!",
  "model": "tts-1-hd",
  "voice": "nova",
  "speed": 1.0,
  "response_format": "mp3",
  "stream": true
}
```

**Response:**
Streaming audio data i MP3 eller WAV format.

**Fallback Logic:**
1. Försöker först Alice backend TTS (`/api/tts/synthesize`)
2. Vid fel, fallback till mock audio för graceful degradation

#### POST /api/agent/stream
Stream agent responses för VoiceClient integration.

**Request:**
```http
POST /api/agent/stream
Content-Type: application/json

{
  "prompt": "spela musik",
  "model": "gpt-oss:20b",
  "provider": "local",
  "use_rag": true,
  "use_tools": true,
  "language": "svenska",
  "context": {
    "personality": "alice",
    "emotion": "friendly",
    "voice_quality": "high"
  }
}
```

**Response:**
```json
{
  "type": "chunk",
  "content": "Spelar musik nu!",
  "metadata": {
    "memory_id": "mem_12345",
    "provider": "local"
  }
}
```

**Agent Response Types:**
- `chunk` - Text chunk från agent response
- `tool` - Tool execution result
- `error` - Error message
- `planning` - Agent planning phase
- `executing` - Tool execution phase
- `done` - Response complete

### WebRTC Voice Communication

Alice VoiceClient använder WebRTC för real-time audio streaming:

**WebRTC Flow:**
1. **Session Creation** - Skapa ephemeral session via `/api/realtime/ephemeral`
2. **Peer Connection** - Etablera WebRTC peer connection med OpenAI
3. **Media Stream** - Lägg till mikrofon audio track
4. **Data Channel** - Använd data channel för real-time messaging
5. **Audio Processing** - Stream incoming OpenAI audio

**WebRTC Configuration:**
```javascript
const pcConfig = {
  iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
};

const pc = new RTCPeerConnection(pcConfig);

// Audio constraints för optimal kvalitet
const audioConstraints = {
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
  sampleRate: 24000,
  channelCount: 1
};
```

### Voice WebSocket API

#### Connection
```javascript
const sessionId = 'voice_' + Date.now();
const ws = new WebSocket(`ws://localhost:8000/ws/voice/${sessionId}`);
```

#### Message Types

**Outgoing Messages:**
```javascript
// Ping/heartbeat
ws.send(JSON.stringify({ type: 'ping' }));

// Voice input from speech recognition
ws.send(JSON.stringify({
  type: 'voice_input',
  text: 'spela musik',
  timestamp: Date.now()
}));
```

**Incoming Messages:**
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'pong':
      // Heartbeat response
      break;
      
    case 'heard':
      // Alice acknowledged voice input
      console.log('Alice heard:', data.text);
      break;
      
    case 'acknowledge':
      // Quick acknowledgment before processing
      console.log('Alice says:', data.message);
      break;
      
    case 'speak':
      // Alice response for TTS
      if (data.final) {
        synthesizeAndPlay(data.text);
      }
      break;
      
    case 'tool_success':
      // Tool execution completed
      console.log('Tool result:', data.result);
      break;
      
    case 'tool_error':
      // Tool execution failed
      console.error('Tool error:', data.message);
      break;
  }
};
```

### Integration Examples

#### Complete VoiceClient Setup
```javascript
import VoiceClient from '@/components/VoiceClient';

function MyVoiceApp() {
  const handleTranscript = (text, isFinal) => {
    console.log('Transcript:', text, isFinal ? '(final)' : '(interim)');
  };
  
  const handleError = (error) => {
    console.error('Voice error:', error);
  };
  
  const handleConnectionChange = (connected) => {
    console.log('Connection:', connected ? 'Connected' : 'Disconnected');
  };
  
  return (
    <VoiceClient
      personality="alice"
      emotion="friendly"
      voiceQuality="high"
      onTranscript={handleTranscript}
      onError={handleError}
      onConnectionChange={handleConnectionChange}
    />
  );
}
```

#### VoiceBox Basic Integration
```javascript
import VoiceBox from '@/components/VoiceBox';

function MyVoiceApp() {
  const handleVoiceInput = (text) => {
    // Process voice input
    sendToAlice(text);
  };
  
  return (
    <VoiceBox
      bars={7}
      personality="alice"
      emotion="friendly"
      voiceQuality="medium"
      onVoiceInput={handleVoiceInput}
      enableWakeWord={true}
      wakeWordSensitivity={0.7}
    />
  );
}
```

#### Hybrid Voice Implementation
```javascript
class AliceVoiceInterface {
  constructor() {
    this.mode = 'voicebox'; // 'voicebox' | 'voiceclient' | 'dual'
    this.voiceBox = null;
    this.voiceClient = null;
  }
  
  async initialize() {
    // Initialize based on capabilities and user preference
    const hasOpenAI = Boolean(process.env.OPENAI_API_KEY);
    const hasWebRTC = Boolean(window.RTCPeerConnection);
    
    if (hasOpenAI && hasWebRTC && this.mode !== 'voicebox') {
      // Use advanced VoiceClient
      this.voiceClient = new VoiceClient({
        personality: 'alice',
        emotion: 'friendly',
        voiceQuality: 'high'
      });
    } else {
      // Use basic VoiceBox
      this.voiceBox = new VoiceBox({
        personality: 'alice',
        emotion: 'friendly',
        allowDemo: true,
        allowPseudo: true
      });
    }
  }
}
```

### System & Hälsa

#### GET /api/health
Systemhälsokontroll.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-20T10:30:00Z",
  "version": "0.1.0",
  "components": {
    "database": {"status": "up", "latency_ms": 2},
    "ollama": {"status": "up", "model_loaded": "gpt-oss:20b"},
    "nlu_agent": {"status": "up", "endpoint": "http://localhost:7071"},
    "tts_engine": {"status": "up", "voices_loaded": 1}
  },
  "metrics": {
    "uptime_seconds": 3600,
    "requests_total": 1247,
    "active_connections": 3
  }
}
```

#### GET /api/tools/stats
Verktygsstatistik och användning.

**Response:**
```json
{
  "total_executions": 1543,
  "success_rate": 0.987,
  "tool_usage": {
    "PLAY": {"count": 234, "success_rate": 1.0, "avg_latency_ms": 15},
    "PAUSE": {"count": 198, "success_rate": 1.0, "avg_latency_ms": 12},
    "SET_VOLUME": {"count": 456, "success_rate": 0.99, "avg_latency_ms": 8}
  },
  "recent_errors": [
    {
      "tool": "SPOTIFY_PLAY",
      "error": "Device not found",
      "timestamp": "2025-01-20T10:25:00Z"
    }
  ]
}
```

### Memory & Kontext

#### POST /api/memory/upsert
Lagra information i långtidsminne.

**Request:**
```http
POST /api/memory/upsert
Content-Type: application/json

{
  "key": "user_preferences",
  "value": {
    "favorite_genre": "jazz",
    "preferred_volume": 70,
    "wake_word": "Alice"
  },
  "category": "preferences",
  "user_id": "user123",
  "ttl_hours": 168
}
```

**Response:**
```json
{
  "success": true,
  "key": "user_preferences", 
  "stored_at": "2025-01-20T10:30:00Z",
  "expires_at": "2025-01-27T10:30:00Z"
}
```

#### POST /api/memory/retrieve
Hämta information från minnet.

**Request:**
```http
POST /api/memory/retrieve
Content-Type: application/json

{
  "query": "jazz preferences",
  "user_id": "user123",
  "limit": 5,
  "category": "preferences"
}
```

**Response:**
```json
{
  "results": [
    {
      "key": "user_preferences",
      "value": {"favorite_genre": "jazz", "preferred_volume": 70},
      "relevance_score": 0.95,
      "stored_at": "2025-01-20T10:30:00Z",
      "category": "preferences"
    }
  ],
  "total_results": 1,
  "query_time_ms": 15
}
```

### Google Calendar Integration

#### GET /api/calendar/events
Hämta kommande kalenderhändelser från Google Calendar.

**Parameters:**
| Parameter | Type | Default | Beskrivning |
|-----------|------|---------|-------------|
| `max_results` | integer | 10 | Max antal händelser att hämta |
| `time_min` | string | null | Start tid (ISO format) |
| `time_max` | string | null | Slut tid (ISO format) |

**Response:**
```json
{
  "success": true,
  "events": [
    {
      "id": "event_12345",
      "title": "Möte med teamet",
      "start": "2025-01-22T14:00:00+01:00",
      "end": "2025-01-22T15:00:00+01:00",
      "description": "Veckomöte för projektstatus",
      "attendees": ["john@example.com"],
      "location": "Konferensrum A"
    }
  ],
  "total_count": 5
}
```

#### POST /api/calendar/events
Skapa ny kalenderhändelse med intelligent scheduling.

**Request:**
```http
POST /api/calendar/events
Content-Type: application/json

{
  "title": "Lunch med Anna",
  "start_time": "2025-01-23 12:00",
  "end_time": "2025-01-23 13:00",
  "description": "Lunch på Café Linné",
  "attendees": ["anna@example.com"],
  "check_conflicts": true
}
```

**Response:**
```json
{
  "success": true,
  "event_id": "event_67890",
  "message": "Händelse skapad framgångsrikt",
  "conflicts_found": false,
  "calendar_url": "https://calendar.google.com/event?eid=..."
}
```

#### PUT /api/calendar/events
Uppdatera befintlig kalenderhändelse.

**Request:**
```http
PUT /api/calendar/events
Content-Type: application/json

{
  "event_id": "event_12345",
  "title": "Uppdaterat möte",
  "start_time": "2025-01-22 15:00",
  "end_time": "2025-01-22 16:00"
}
```

#### DELETE /api/calendar/events/{event_id}
Ta bort kalenderhändelse.

**Response:**
```json
{
  "success": true,
  "message": "Händelse borttagen"
}
```

#### POST /api/calendar/events/search
Sök efter händelser med naturligt språk.

**Request:**
```http
POST /api/calendar/events/search
Content-Type: application/json

{
  "query": "möten med Anna nästa vecka",
  "max_results": 20
}
```

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "id": "event_789",
      "title": "Projektmöte med Anna",
      "start": "2025-01-29T10:00:00+01:00",
      "relevance_score": 0.95
    }
  ],
  "query_interpretation": {
    "person": "Anna",
    "timeframe": "next_week",
    "type": "meeting"
  }
}
```

#### POST /api/calendar/check-conflicts
Kontrollera konflikter för föreslagen tid.

**Request:**
```http
POST /api/calendar/check-conflicts
Content-Type: application/json

{
  "start_time": "2025-01-23 14:00",
  "end_time": "2025-01-23 15:00",
  "exclude_event_id": null
}
```

**Response:**
```json
{
  "success": true,
  "has_conflict": true,
  "message": "Konflikt funnen med 'Utvecklingsmöte'",
  "conflicts": [
    {
      "id": "event_456",
      "title": "Utvecklingsmöte",
      "start": "2025-01-23T14:30:00+01:00",
      "end": "2025-01-23T15:30:00+01:00"
    }
  ],
  "suggestions": [
    {
      "start_time": "2025-01-23T13:00:00+01:00",
      "end_time": "2025-01-23T14:00:00+01:00",
      "formatted": "Idag 13:00-14:00",
      "confidence": 0.9
    }
  ]
}
```

#### POST /api/calendar/suggest-times
Få AI-baserade tidsförslag för möten.

**Request:**
```http
POST /api/calendar/suggest-times
Content-Type: application/json

{
  "duration_minutes": 60,
  "date_preference": "2025-01-24",
  "max_suggestions": 5,
  "meeting_type": "focus_work",
  "attendees": ["colleague@example.com"]
}
```

**Response:**
```json
{
  "success": true,
  "suggestions": [
    {
      "start_time": "2025-01-24T09:00:00+01:00",
      "end_time": "2025-01-24T10:00:00+01:00",
      "formatted": "Imorgon 09:00-10:00",
      "confidence": 0.95,
      "rationale": "Optimal morgontid, inga konflikter"
    },
    {
      "start_time": "2025-01-24T14:00:00+01:00",
      "end_time": "2025-01-24T15:00:00+01:00",
      "formatted": "Imorgon 14:00-15:00",
      "confidence": 0.85,
      "rationale": "Eftermiddagsfokus, kort paus efter lunch"
    }
  ],
  "ai_insights": {
    "best_time_of_day": "morning",
    "productivity_score": 0.9,
    "energy_level": "high"
  }
}
```

#### GET /api/calendar/voice-commands
Hämta supporterade svenska röstkommandon för kalender.

**Response:**
```json
{
  "commands": {
    "view": [
      "visa kalender",
      "vad har jag för möten",
      "kolla mitt schema"
    ],
    "create": [
      "boka möte imorgon kl 14",
      "skapa händelse nästa fredag",
      "lägg till lunch på måndag"
    ],
    "search": [
      "när har jag möte med Anna",
      "sök efter projekt-möten",
      "hitta mina Teams-möten"
    ]
  },
  "supported_time_expressions": [
    "imorgon", "nästa vecka", "kl 14:30",
    "på måndag", "om en timme", "nästa fredag"
  ]
}
```

**Svenska Röstintegration:**
```javascript
// Användning av calendar voice commands
const calendarVoiceCommands = {
  "visa kalender": () => alice.getEvents(),
  "boka möte imorgon kl 14": () => alice.createEvent({
    title: "Möte",
    start_time: "tomorrow 14:00",
    end_time: "tomorrow 15:00"
  }),
  "när har jag möte med Anna": () => alice.searchEvents("Anna")
};
```

### Spotify Integration

#### GET /api/spotify/auth_url
Hämta Spotify OAuth URL.

**Parameters:**
| Parameter | Type | Default | Beskrivning |
|-----------|------|---------|-------------|
| `scopes` | string | "user-read-playback-state,user-modify-playback-state,streaming" | OAuth scopes |

**Response:**
```json
{
  "auth_url": "https://accounts.spotify.com/authorize?client_id=...&redirect_uri=...",
  "state": "abc123xyz",
  "scopes": ["user-read-playback-state", "user-modify-playback-state"]
}
```

#### GET /api/spotify/callback
OAuth callback endpoint (används automatiskt).

#### GET /api/spotify/devices
Lista tillgängliga uppspelningsenheter.

**Headers:**
```http
Authorization: Bearer <spotify_access_token>
```

**Response:**
```json
{
  "devices": [
    {
      "id": "5fbb3ba6aa454b5534c71340b0b58b81",
      "is_active": true,
      "is_private_session": false,
      "is_restricted": false,
      "name": "Kitchen Speaker",
      "type": "Speaker",
      "volume_percent": 70
    }
  ]
}
```

#### POST /api/spotify/play
Starta uppspelning på Spotify.

**Request:**
```http
POST /api/spotify/play
Content-Type: application/json
Authorization: Bearer <spotify_access_token>

{
  "device_id": "5fbb3ba6aa454b5534c71340b0b58b81",
  "context_uri": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",
  "position_ms": 30000,
  "uris": ["spotify:track:4iV5W9uYEdYUVa79Axb7Rh"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Playback started",
  "device": "Kitchen Speaker",
  "track": "Song Name - Artist",
  "position_ms": 30000
}
```

## WebSocket API

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/alice');

ws.onopen = () => {
  console.log('Connected to Alice');
  // Skicka initial konfiguration
  ws.send(JSON.stringify({
    type: 'config',
    user_id: 'user123',
    subscribe_to: ['system_metrics', 'tool_updates', 'chat_responses']
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  handleMessage(message);
};
```

### Meddelandetyper

#### Inkommande Meddelanden

**System Metrics:**
```json
{
  "type": "system_metrics",
  "timestamp": "2025-01-20T10:30:00Z",
  "data": {
    "cpu_percent": 45.2,
    "memory_percent": 62.1,
    "network_io": {"bytes_sent": 1024, "bytes_recv": 2048},
    "active_tools": 3,
    "websocket_connections": 2
  }
}
```

**Tool Execution Update:**
```json
{
  "type": "tool_update",
  "timestamp": "2025-01-20T10:30:00Z",
  "data": {
    "tool": "SET_VOLUME",
    "status": "completed",
    "args": {"level": 80},
    "execution_time_ms": 23,
    "result": "Volym satt till 80%"
  }
}
```

**Chat Response:**
```json
{
  "type": "chat_response", 
  "timestamp": "2025-01-20T10:30:00Z",
  "data": {
    "text": "Musik spelar nu",
    "provider": "ollama",
    "confidence": 0.95,
    "user_id": "user123"
  }
}
```

**Media State Update:**
```json
{
  "type": "media_state",
  "timestamp": "2025-01-20T10:30:00Z",
  "data": {
    "is_playing": true,
    "track": {
      "name": "Song Title",
      "artist": "Artist Name",
      "album": "Album Name",
      "duration_ms": 210000,
      "progress_ms": 45000
    },
    "device": "Kitchen Speaker",
    "volume": 75,
    "shuffle": false,
    "repeat": "off"
  }
}
```

#### Utgående Meddelanden

**Subscription Management:**
```json
{
  "type": "subscribe",
  "channels": ["system_metrics", "media_state"],
  "user_id": "user123"
}

{
  "type": "unsubscribe", 
  "channels": ["system_metrics"]
}
```

**Direct Commands:**
```json
{
  "type": "command",
  "action": "execute_tool",
  "data": {
    "tool": "PLAY",
    "args": {}
  }
}

{
  "type": "command",
  "action": "chat",
  "data": {
    "prompt": "vad spelar just nu?"
  }
}
```

## NLU Agent API

NLU Agent körs separat på port 7071 och tillhandahåller naturlig språkförståelse.

### Base URL: `http://localhost:7071`

#### POST /nlu/classify
Klassificera användarintent från text.

**Request:**
```http
POST /nlu/classify
Content-Type: application/json

{
  "text": "höj volymen till 80 procent"
}
```

**Response:**
```json
{
  "ok": true,
  "intent": "SET_VOL",
  "score": 1.0,
  "phrase": "höj volymen till 80 procent",
  "slots": {
    "level": 80
  }
}
```

#### POST /nlu/extract
Extrahera specifika slots från text.

**Request:**
```http
POST /nlu/extract
Content-Type: application/json

{
  "text": "hoppa fram 30 sekunder och höj volymen lite"
}
```

**Response:**
```json
{
  "ok": true,
  "slots": {
    "seconds": 30,
    "delta": 10
  },
  "confidence": 0.9
}
```

#### POST /agent/route
Fullständig routing från text till verktygsplan.

**Request:**
```http
POST /agent/route
Content-Type: application/json

{
  "text": "spela jazz på köket"
}
```

**Response:**
```json
{
  "ok": true,
  "plan": {
    "tool": "PLAY",
    "params": {
      "genre": "jazz",
      "device": "kitchen_speaker"
    }
  },
  "confidence": 0.95,
  "needs_confirmation": false,
  "rationale": "High confidence genre and device recognition"
}
```

## Rate Limiting

Alice implementerar rate limiting för att förhindra missbruk:

| Endpoint Category | Limit | Window |
|------------------|--------|---------|
| Chat endpoints | 60 requests | 1 minute |
| TTS synthesis | 30 requests | 1 minute |
| Tool execution | 120 requests | 1 minute |
| WebSocket messages | 200 messages | 1 minute |

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642694400
```

## Error Handling

### Standard Error Format
```json
{
  "error": "error_code",
  "message": "Human readable error message",
  "code": 400,
  "timestamp": "2025-01-20T10:30:00Z",
  "request_id": "req_abc123",
  "details": {
    "field": "prompt",
    "issue": "cannot be empty"
  }
}
```

### HTTP Status Codes

| Code | Betydelse | Vanliga Orsaker |
|------|----------|----------------|
| 200 | OK | Lyckad förfrågan |
| 400 | Bad Request | Ogiltig input, saknade parametrar |
| 401 | Unauthorized | Saknar eller ogiltig autentisering |
| 403 | Forbidden | Otillräckliga behörigheter |
| 404 | Not Found | Endpoint eller resurs finns inte |
| 429 | Too Many Requests | Rate limit överskriden |
| 500 | Internal Server Error | Server- eller AI-modellfel |
| 503 | Service Unavailable | AI-modell eller tjänst otillgänglig |

### Error Codes

| Code | Beskrivning |
|------|-------------|
| `invalid_prompt` | Tom eller ogiltig prompt |
| `ai_processing_failed` | AI-modell kunde inte bearbeta förfrågan |
| `tool_not_found` | Begärt verktyg existerar inte |
| `tool_execution_failed` | Verktygsexekvering misslyckades |
| `invalid_tool_args` | Ogiltiga argument till verktyg |
| `tts_synthesis_failed` | Röstsyntes misslyckades |
| `rate_limit_exceeded` | För många förfrågningar |
| `websocket_connection_failed` | WebSocket-anslutning misslyckades |

## SDK och Client Libraries

### JavaScript/TypeScript SDK

```javascript
// alice-sdk.js
class AliceClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.ws = null;
  }
  
  async chat(prompt, options = {}) {
    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({prompt, ...options})
    });
    return await response.json();
  }
  
  async executeTool(tool, args = {}) {
    const response = await fetch(`${this.baseUrl}/api/tools/exec`, {
      method: 'POST', 
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({tool, args})
    });
    return await response.json();
  }
  
  async synthesizeTTS(text, options = {}) {
    const response = await fetch(`${this.baseUrl}/api/tts/synthesize`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, ...options})
    });
    return await response.json();
  }
  
  connectWebSocket() {
    this.ws = new WebSocket(`ws://localhost:8000/ws/alice`);
    return new Promise((resolve, reject) => {
      this.ws.onopen = () => resolve(this.ws);
      this.ws.onerror = reject;
    });
  }
  
  onMessage(callback) {
    if (this.ws) {
      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        callback(message);
      };
    }
  }
}

// Användning
const alice = new AliceClient();

// Chat
const response = await alice.chat('spela musik');
console.log(response.text);

// Verktygsexekvering  
await alice.executeTool('SET_VOLUME', {level: 75});

// TTS
const ttsData = await alice.synthesizeTTS('Hej från Alice!');
// ... spela upp ljuddata

// WebSocket
await alice.connectWebSocket();
alice.onMessage((msg) => {
  console.log('Received:', msg);
});
```

### Python SDK

```python
# alice_sdk.py
import asyncio
import aiohttp
import websockets
import json
from typing import Dict, Any, Optional, Callable

class AliceClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http", "ws") + "/ws/alice"
        self.session = None
        self.ws = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def chat(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Skicka chat-meddelande till Alice."""
        async with self.session.post(
            f"{self.base_url}/api/chat",
            json={"prompt": prompt, **kwargs}
        ) as response:
            return await response.json()
    
    async def execute_tool(self, tool: str, args: Dict = None) -> Dict[str, Any]:
        """Exekvera specifikt verktyg."""
        async with self.session.post(
            f"{self.base_url}/api/tools/exec",
            json={"tool": tool, "args": args or {}}
        ) as response:
            return await response.json()
    
    async def synthesize_tts(self, text: str, **kwargs) -> Dict[str, Any]:
        """Generera TTS från text."""
        async with self.session.post(
            f"{self.base_url}/api/tts/synthesize",
            json={"text": text, **kwargs}
        ) as response:
            return await response.json()
    
    async def connect_websocket(self, 
                              on_message: Callable[[Dict], None] = None):
        """Anslut till WebSocket för real-time uppdateringar."""
        self.ws = await websockets.connect(self.ws_url)
        
        if on_message:
            async for message in self.ws:
                data = json.loads(message)
                on_message(data)

# Användning
async def main():
    async with AliceClient() as alice:
        # Chat
        response = await alice.chat("spela musik")
        print(f"Alice: {response['text']}")
        
        # Verktygsexekvering
        result = await alice.execute_tool("SET_VOLUME", {"level": 80})
        print(f"Tool result: {result['message']}")
        
        # TTS
        tts_data = await alice.synthesize_tts("Hej från Alice!")
        # ... hantera audio_data
        
        # WebSocket
        def handle_message(msg):
            print(f"WS Message: {msg}")
        
        await alice.connect_websocket(handle_message)

# Kör exempel
# asyncio.run(main())
```

## Exempel och Recept

### Vanliga Användningsfall

#### 1. Enkel Mediauppspelning
```javascript
const alice = new AliceClient();

// Via naturligt språk
await alice.chat('spela jazz musik');

// Via direkt verktygsanrop
await alice.executeTool('PLAY');
await alice.executeTool('SET_VOLUME', {level: 60});
```

#### 2. Röstassistent Pipeline
```javascript
// Komplett röstinteraktion
async function voiceAssistant() {
  const alice = new AliceClient();
  
  // 1. STT (kräver Web Speech API eller extern tjänst)
  const userSpeech = await recognizeSpeech();
  
  // 2. Process med Alice
  const response = await alice.chat(userSpeech);
  
  // 3. TTS för svar
  if (response.text) {
    const ttsData = await alice.synthesizeTTS(response.text);
    await playAudio(ttsData.audio_data);
  }
}
```

#### 3. Smart Home Integration  
```python
async def smart_home_control():
    async with AliceClient() as alice:
        # Koppla Alice-kommandon till smart home
        commands = [
            ("tänd lamporna", "LIGHTS_ON"),
            ("höj volymen", "SET_VOLUME", {"level": 80}),
            ("spela morgonmusik", "PLAY_PLAYLIST", {"name": "morning"})
        ]
        
        for text, tool, *args in commands:
            response = await alice.chat(text)
            if response.get('meta', {}).get('tool'):
                print(f"Executing: {tool}")
                # Integrera med smart home system
```

#### 4. Real-time Dashboard
```javascript
class AliceDashboard {
  constructor() {
    this.alice = new AliceClient();
    this.metrics = {};
  }
  
  async initialize() {
    await this.alice.connectWebSocket();
    
    this.alice.onMessage((msg) => {
      switch(msg.type) {
        case 'system_metrics':
          this.updateSystemMetrics(msg.data);
          break;
        case 'media_state':
          this.updateMediaPlayer(msg.data);
          break;
        case 'tool_update':
          this.logToolExecution(msg.data);
          break;
      }
    });
  }
  
  updateSystemMetrics(data) {
    document.getElementById('cpu').textContent = `${data.cpu_percent}%`;
    document.getElementById('memory').textContent = `${data.memory_percent}%`;
  }
}
```

### Prestanda Tips

#### 1. Batch Requests
```javascript
// Istället för flera separata anrop
const responses = await Promise.all([
  alice.chat('vad spelar nu?'),
  alice.executeTool('GET_VOLUME'),
  alice.chat('vilka enheter är tillgängliga?')
]);
```

#### 2. WebSocket för Real-time
```javascript
// Använd WebSocket för uppdateringar istället för polling
await alice.connectWebSocket();
alice.onMessage((msg) => {
  if (msg.type === 'media_state') {
    updateUI(msg.data);
  }
});
```

#### 3. Cache TTS Audio
```javascript
const ttsCache = new Map();

async function getTTSAudio(text) {
  if (ttsCache.has(text)) {
    return ttsCache.get(text);
  }
  
  const ttsData = await alice.synthesizeTTS(text);
  ttsCache.set(text, ttsData);
  return ttsData;
}
```

## Versionshantering

Alice API använder semantic versioning. Aktuell version: `v1.0.0`

### Bakåtkompatibilitet

- **Major version** (v1 → v2): Breaking changes
- **Minor version** (v1.0 → v1.1): Nya features, bakåtkompatibel
- **Patch version** (v1.0.0 → v1.0.1): Bugfixes, bakåtkompatibel

### API Versioning
```http
# Specificera API-version i headers
Accept: application/vnd.alice.v1+json

# Eller i URL
GET /api/v1/chat
```

## Testing

### API Testing med curl

```bash
# Health check
curl -X GET http://localhost:8000/api/health

# Chat test
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "spela musik"}'

# Tool execution
curl -X POST http://localhost:8000/api/tools/exec \
  -H "Content-Type: application/json" \
  -d '{"tool": "SET_VOLUME", "args": {"level": 75}}'

# TTS test
curl -X POST http://localhost:8000/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hej från Alice!"}' \
  --output audio.json
```

### Unit Testing

```python
import pytest
from alice_sdk import AliceClient

@pytest.mark.asyncio
async def test_chat_endpoint():
    async with AliceClient() as client:
        response = await client.chat("test message")
        assert "text" in response
        assert response.get("provider") in ["ollama", "openai"]

@pytest.mark.asyncio  
async def test_tool_execution():
    async with AliceClient() as client:
        result = await client.execute_tool("PLAY")
        assert result["ok"] is True
        assert "message" in result
```

---

**Den fullständiga interaktiva API-dokumentationen finns på:**
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

För ytterligare hjälp, se [README.md](README.md) för grundläggande användning och [DEVELOPMENT.md](DEVELOPMENT.md) för utvecklingsguider.