# Alice API Documentation

Complete API documentation for the Alice AI Assistant Platform. Alice provides REST API endpoints, WebSocket connections and a comprehensive tool ecosystem.

> **🇸🇪 Svenska:** [docs/sv/API.md](docs/sv/API.md) - Full Swedish version available

## Overview

Alice API consists of several main components:

- **REST API**: Main HTTP endpoints for chat, TTS, tool execution
- **Voice System**: Currently Browser SpeechRecognition, planned OpenAI Realtime API integration
- **WebSocket**: Real-time communication for HUD updates (voice streaming in development)
- **NLU Processing**: Intent classification and Swedish language understanding
- **Agent Bridge**: Server-Sent Events (SSE) for streaming agent responses
- **Tool System**: Modular system for extensible functionality (calendar, weather, etc.)

**Base URLs (Current Implementation):**
- Backend API: `http://localhost:8000` (FastAPI server)
- Frontend: `http://localhost:3000` (Next.js development server)
- WebSocket: `ws://localhost:8000/ws/alice`
- Voice Gateway: `ws://localhost:8000/ws/voice-gateway` (in development)

## Authentication

Alice currently uses no authentication for local installations. For production deployment, implement API keys or OAuth.

```http
# Headers for future authentication
Authorization: Bearer <api-token>
X-API-Key: <api-key>
```

## REST API Endpoints

### Chat & Conversation

#### POST /api/chat
Send text messages to Alice and get intelligent responses.

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
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | ✓ | - | User's text input |
| `provider` | string | | "auto" | AI provider ("auto", "ollama", "openai") |
| `context` | string | | null | Contextual information |
| `user_id` | string | | null | User ID for personalization |

**Response:**
```json
{
  "text": "Playing music now.",
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
Streaming chat for real-time responses (Server-Sent Events).

**Request:**
```http
POST /api/chat/stream
Content-Type: application/json
Accept: text/event-stream

{
  "prompt": "tell me a story",
  "stream": true,
  "provider": "auto"
}
```

**Response Stream:**
```
data: {"type":"start","timestamp":"2025-01-20T10:30:00Z"}

data: {"type":"token","text":"It","delta":"It"}

data: {"type":"token","text":"It was","delta":" was"}

data: {"type":"meta","meta":{"tool":null,"processing_time":150}}

data: {"type":"final","text":"It was once...","complete":true}

data: [DONE]
```

### Tool Execution

#### POST /api/tools/exec
Execute specific tools directly.

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
| Tool | Description | Arguments |
|------|------------|-----------|
| `PLAY` | Start playback | `{}` |
| `PAUSE` | Pause playback | `{}` |
| `STOP` | Stop playback | `{}` |
| `NEXT` | Next track | `{}` |
| `PREV` | Previous track | `{}` |
| `SET_VOLUME` | Set volume | `{"level": 0-100}` or `{"delta": ±N}` |
| `MUTE` | Mute audio | `{}` |
| `UNMUTE` | Unmute audio | `{}` |
| `SHUFFLE` | Random order | `{"enabled": true/false}` |
| `REPEAT` | Repeat mode | `{"mode": "off"/"one"/"all"}` |
| `LIKE` | Like current track | `{}` |
| `UNLIKE` | Unlike track | `{}` |

**Response:**
```json
{
  "ok": true,
  "message": "Volume set to 75%",
  "tool": "SET_VOLUME",
  "args": {"level": 75},
  "execution_time_ms": 45,
  "timestamp": "2025-01-20T10:30:00Z"
}
```

#### GET /api/tools/spec
Get specifications for all available tools.

**Response:**
```json
[
  {
    "name": "SET_VOLUME",
    "description": "Control volume level",
    "parameters": {
      "type": "object",
      "properties": {
        "level": {
          "type": "integer",
          "minimum": 0,
          "maximum": 100,
          "description": "Absolute volume level (0-100)"
        },
        "delta": {
          "type": "integer", 
          "minimum": -100,
          "maximum": 100,
          "description": "Relative volume change"
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
List enabled tools.

**Response:**
```json
{
  "enabled_tools": ["PLAY", "PAUSE", "SET_VOLUME", "NEXT", "PREV"],
  "total_available": 12,
  "configuration_source": "environment"
}
```

### Enhanced Text-to-Speech (TTS)

#### POST /api/tts/synthesize
Enhanced speech synthesis with emotions, personality and caching.

**Request:**
```http
POST /api/tts/synthesize
Content-Type: application/json

{
  "text": "Hello! I'm Alice, your AI assistant.",
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
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | string | - | Text to synthesize |
| `voice` | string | "sv_SE-nst-medium" | Voice model |
| `speed` | float | 1.0 | Speech speed (0.5-2.0) |
| `emotion` | string | null | Emotional tone |
| `personality` | string | "alice" | Personality |
| `pitch` | float | 1.0 | Voice pitch (0.8-1.2) |
| `volume` | float | 1.0 | Audio volume (0.1-1.0) |
| `cache` | boolean | true | Use cache |

**Available Voices:**
- `sv_SE-nst-medium` - Swedish female voice (medium quality, naturalness: 7/10)
- `sv_SE-nst-high` - Swedish female voice (high quality, naturalness: 8/10)
- `sv_SE-lisa-medium` - Swedish female voice (medium quality, naturalness: 8/10)

**Available Emotions:**
- `neutral` - Neutral tone
- `happy` - Happy and energetic
- `calm` - Calm and relaxed
- `confident` - Confident and determined
- `friendly` - Friendly and approachable

**Available Personalities:**
- `alice` - Energetic AI assistant (speed: 1.05, pitch: 1.02)
- `formal` - Professional and authoritative (speed: 0.95, pitch: 0.98)
- `casual` - Relaxed and conversational (speed: 1.1, pitch: 1.05)

**Response:**
```json
{
  "success": true,
  "audio_data": "UklGRjY3AgBXQVZFZm10IBAAAAABAAEA...", 
  "format": "wav",
  "voice": "sv_SE-nst-high",
  "text": "Hello! I'm Alice, your AI assistant.",
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
Get available voice models and their properties.

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
Streaming TTS for faster response times.

**Request:** Same as `/api/tts/synthesize`
**Response:** Streaming audio/wav data

#### GET /api/tts/personality/{personality}
Get personality-specific voice settings.

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
  "description": "Energetic, friendly AI assistant with natural Swedish"
}
```

**Usage in JavaScript:**
```javascript
async function playTTSAudio() {
  const response = await fetch('/api/tts/synthesize', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      text: 'Hello from Alice!',
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
// Session used to initialize WebRTC connection
```

#### POST /api/tts/openai-stream
Stream TTS audio from OpenAI or Alice backend.

**Request:**
```http
POST /api/tts/openai-stream
Content-Type: application/json

{
  "text": "Hello from Alice!",
  "model": "tts-1-hd",
  "voice": "nova",
  "speed": 1.0,
  "response_format": "mp3",
  "stream": true
}
```

**Response:**
Streaming audio data in MP3 or WAV format.

**Fallback Logic:**
1. First tries Alice backend TTS (`/api/tts/synthesize`)
2. On error, fallback to mock audio for graceful degradation

#### POST /api/agent/stream
Stream agent responses for VoiceClient integration.

**Request:**
```http
POST /api/agent/stream
Content-Type: application/json

{
  "prompt": "play music",
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
  "content": "Playing music now!",
  "metadata": {
    "memory_id": "mem_12345",
    "provider": "local"
  }
}
```

**Agent Response Types:**
- `chunk` - Text chunk from agent response
- `tool` - Tool execution result
- `error` - Error message
- `planning` - Agent planning phase
- `executing` - Tool execution phase
- `done` - Response complete

### WebRTC Voice Communication

Alice VoiceClient uses WebRTC for real-time audio streaming:

**WebRTC Flow:**
1. **Session Creation** - Create ephemeral session via `/api/realtime/ephemeral`
2. **Peer Connection** - Establish WebRTC peer connection with OpenAI
3. **Media Stream** - Add microphone audio track
4. **Data Channel** - Use data channel for real-time messaging
5. **Audio Processing** - Stream incoming OpenAI audio

**WebRTC Configuration:**
```javascript
const pcConfig = {
  iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
};

const pc = new RTCPeerConnection(pcConfig);

// Audio constraints for optimal quality
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
  text: 'play music',
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

### System & Health

#### GET /api/health
System health check.

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
Tool statistics and usage.

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

### Memory & Context

#### POST /api/memory/upsert
Store information in long-term memory.

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
Retrieve information from memory.

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
Get upcoming calendar events from Google Calendar.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_results` | integer | 10 | Max number of events to fetch |
| `time_min` | string | null | Start time (ISO format) |
| `time_max` | string | null | End time (ISO format) |

**Response:**
```json
{
  "success": true,
  "events": [
    {
      "id": "event_12345",
      "title": "Team meeting",
      "start": "2025-01-22T14:00:00+01:00",
      "end": "2025-01-22T15:00:00+01:00",
      "description": "Weekly meeting for project status",
      "attendees": ["john@example.com"],
      "location": "Conference room A"
    }
  ],
  "total_count": 5
}
```

#### POST /api/calendar/events
Create new calendar event with intelligent scheduling.

**Request:**
```http
POST /api/calendar/events
Content-Type: application/json

{
  "title": "Lunch with Anna",
  "start_time": "2025-01-23 12:00",
  "end_time": "2025-01-23 13:00",
  "description": "Lunch at Café Linné",
  "attendees": ["anna@example.com"],
  "check_conflicts": true
}
```

**Response:**
```json
{
  "success": true,
  "event_id": "event_67890",
  "message": "Event created successfully",
  "conflicts_found": false,
  "calendar_url": "https://calendar.google.com/event?eid=..."
}
```

#### PUT /api/calendar/events
Update existing calendar event.

**Request:**
```http
PUT /api/calendar/events
Content-Type: application/json

{
  "event_id": "event_12345",
  "title": "Updated meeting",
  "start_time": "2025-01-22 15:00",
  "end_time": "2025-01-22 16:00"
}
```

#### DELETE /api/calendar/events/{event_id}
Delete calendar event.

**Response:**
```json
{
  "success": true,
  "message": "Event deleted"
}
```

#### POST /api/calendar/events/search
Search for events with natural language.

**Request:**
```http
POST /api/calendar/events/search
Content-Type: application/json

{
  "query": "meetings with Anna next week",
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
      "title": "Project meeting with Anna",
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
Check conflicts for proposed time.

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
  "message": "Conflict found with 'Development meeting'",
  "conflicts": [
    {
      "id": "event_456",
      "title": "Development meeting",
      "start": "2025-01-23T14:30:00+01:00",
      "end": "2025-01-23T15:30:00+01:00"
    }
  ],
  "suggestions": [
    {
      "start_time": "2025-01-23T13:00:00+01:00",
      "end_time": "2025-01-23T14:00:00+01:00",
      "formatted": "Today 13:00-14:00",
      "confidence": 0.9
    }
  ]
}
```

#### POST /api/calendar/suggest-times
Get AI-based time suggestions for meetings.

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
      "formatted": "Tomorrow 09:00-10:00",
      "confidence": 0.95,
      "rationale": "Optimal morning time, no conflicts"
    },
    {
      "start_time": "2025-01-24T14:00:00+01:00",
      "end_time": "2025-01-24T15:00:00+01:00",
      "formatted": "Tomorrow 14:00-15:00",
      "confidence": 0.85,
      "rationale": "Afternoon focus, short break after lunch"
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
Get supported Swedish voice commands for calendar.

**Response:**
```json
{
  "commands": {
    "view": [
      "show calendar",
      "what meetings do I have",
      "check my schedule"
    ],
    "create": [
      "book meeting tomorrow at 2 PM",
      "create event next Friday",
      "add lunch on Monday"
    ],
    "search": [
      "when is my meeting with Anna",
      "search for project meetings",
      "find my Teams meetings"
    ]
  },
  "supported_time_expressions": [
    "tomorrow", "next week", "at 2:30 PM",
    "on Monday", "in an hour", "next Friday"
  ]
}
```

**Swedish Voice Integration:**
```javascript
// Usage of calendar voice commands
const calendarVoiceCommands = {
  "show calendar": () => alice.getEvents(),
  "book meeting tomorrow at 2 PM": () => alice.createEvent({
    title: "Meeting",
    start_time: "tomorrow 14:00",
    end_time: "tomorrow 15:00"
  }),
  "when is my meeting with Anna": () => alice.searchEvents("Anna")
};
```

### Spotify Integration

#### GET /api/spotify/auth_url
Get Spotify OAuth URL.

**Parameters:**
| Parameter | Type | Default | Description |
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
OAuth callback endpoint (used automatically).

#### GET /api/spotify/devices
List available playback devices.

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
Start playback on Spotify.

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
  // Send initial configuration
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

### Message Types

#### Incoming Messages

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
    "result": "Volume set to 80%"
  }
}
```

**Chat Response:**
```json
{
  "type": "chat_response", 
  "timestamp": "2025-01-20T10:30:00Z",
  "data": {
    "text": "Music is now playing",
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

#### Outgoing Messages

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
    "prompt": "what's playing now?"
  }
}
```

## NLU Agent API

NLU Agent runs separately on port 7071 and provides natural language understanding.

### Base URL: `http://localhost:7071`

#### POST /nlu/classify
Classify user intent from text.

**Request:**
```http
POST /nlu/classify
Content-Type: application/json

{
  "text": "raise volume to 80 percent"
}
```

**Response:**
```json
{
  "ok": true,
  "intent": "SET_VOL",
  "score": 1.0,
  "phrase": "raise volume to 80 percent",
  "slots": {
    "level": 80
  }
}
```

#### POST /nlu/extract
Extract specific slots from text.

**Request:**
```http
POST /nlu/extract
Content-Type: application/json

{
  "text": "skip forward 30 seconds and raise volume a bit"
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
Complete routing from text to tool plan.

**Request:**
```http
POST /agent/route
Content-Type: application/json

{
  "text": "play jazz in the kitchen"
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

Alice implements rate limiting to prevent abuse:

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

| Code | Meaning | Common Causes |
|------|----------|----------------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid input, missing parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Endpoint or resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server or AI model error |
| 503 | Service Unavailable | AI model or service unavailable |

### Error Codes

| Code | Description |
|------|-------------|
| `invalid_prompt` | Empty or invalid prompt |
| `ai_processing_failed` | AI model could not process request |
| `tool_not_found` | Requested tool does not exist |
| `tool_execution_failed` | Tool execution failed |
| `invalid_tool_args` | Invalid arguments for tool |
| `tts_synthesis_failed` | Speech synthesis failed |
| `rate_limit_exceeded` | Too many requests |
| `websocket_connection_failed` | WebSocket connection failed |

## SDK and Client Libraries

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

// Usage
const alice = new AliceClient();

// Chat
const response = await alice.chat('play music');
console.log(response.text);

// Tool execution  
await alice.executeTool('SET_VOLUME', {level: 75});

// TTS
const ttsData = await alice.synthesizeTTS('Hello from Alice!');
// ... play audio data

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
        """Send chat message to Alice."""
        async with self.session.post(
            f"{self.base_url}/api/chat",
            json={"prompt": prompt, **kwargs}
        ) as response:
            return await response.json()
    
    async def execute_tool(self, tool: str, args: Dict = None) -> Dict[str, Any]:
        """Execute specific tool."""
        async with self.session.post(
            f"{self.base_url}/api/tools/exec",
            json={"tool": tool, "args": args or {}}
        ) as response:
            return await response.json()
    
    async def synthesize_tts(self, text: str, **kwargs) -> Dict[str, Any]:
        """Generate TTS from text."""
        async with self.session.post(
            f"{self.base_url}/api/tts/synthesize",
            json={"text": text, **kwargs}
        ) as response:
            return await response.json()
    
    async def connect_websocket(self, 
                              on_message: Callable[[Dict], None] = None):
        """Connect to WebSocket for real-time updates."""
        self.ws = await websockets.connect(self.ws_url)
        
        if on_message:
            async for message in self.ws:
                data = json.loads(message)
                on_message(data)

# Usage
async def main():
    async with AliceClient() as alice:
        # Chat
        response = await alice.chat("play music")
        print(f"Alice: {response['text']}")
        
        # Tool execution
        result = await alice.execute_tool("SET_VOLUME", {"level": 80})
        print(f"Tool result: {result['message']}")
        
        # TTS
        tts_data = await alice.synthesize_tts("Hello from Alice!")
        # ... handle audio_data
        
        # WebSocket
        def handle_message(msg):
            print(f"WS Message: {msg}")
        
        await alice.connect_websocket(handle_message)

# Run example
# asyncio.run(main())
```

## Examples and Recipes

### Common Use Cases

#### 1. Simple Media Playback
```javascript
const alice = new AliceClient();

// Via natural language
await alice.chat('play jazz music');

// Via direct tool calls
await alice.executeTool('PLAY');
await alice.executeTool('SET_VOLUME', {level: 60});
```

#### 2. Voice Assistant Pipeline
```javascript
// Complete voice interaction
async function voiceAssistant() {
  const alice = new AliceClient();
  
  // 1. STT (requires Web Speech API or external service)
  const userSpeech = await recognizeSpeech();
  
  // 2. Process with Alice
  const response = await alice.chat(userSpeech);
  
  // 3. TTS for response
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
        # Connect Alice commands to smart home
        commands = [
            ("turn on lights", "LIGHTS_ON"),
            ("raise volume", "SET_VOLUME", {"level": 80}),
            ("play morning music", "PLAY_PLAYLIST", {"name": "morning"})
        ]
        
        for text, tool, *args in commands:
            response = await alice.chat(text)
            if response.get('meta', {}).get('tool'):
                print(f"Executing: {tool}")
                # Integrate with smart home system
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

### Performance Tips

#### 1. Batch Requests
```javascript
// Instead of multiple separate calls
const responses = await Promise.all([
  alice.chat('what is playing now?'),
  alice.executeTool('GET_VOLUME'),
  alice.chat('which devices are available?')
]);
```

#### 2. WebSocket for Real-time
```javascript
// Use WebSocket for updates instead of polling
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

## Versioning

Alice API uses semantic versioning. Current version: `v1.0.0`

### Backwards Compatibility

- **Major version** (v1 → v2): Breaking changes
- **Minor version** (v1.0 → v1.1): New features, backwards compatible
- **Patch version** (v1.0.0 → v1.0.1): Bug fixes, backwards compatible

### API Versioning
```http
# Specify API version in headers
Accept: application/vnd.alice.v1+json

# Or in URL
GET /api/v1/chat
```

## Testing

### API Testing with curl

```bash
# Health check
curl -X GET http://localhost:8000/api/health

# Chat test
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "play music"}'

# Tool execution
curl -X POST http://localhost:8000/api/tools/exec \
  -H "Content-Type: application/json" \
  -d '{"tool": "SET_VOLUME", "args": {"level": 75}}'

# TTS test
curl -X POST http://localhost:8000/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from Alice!"}' \
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

**Complete interactive API documentation is available at:**
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

For additional help, see [README.md](README.md) for basic usage and [DEVELOPMENT.md](DEVELOPMENT.md) for development guides.

**Note on Swedish AI Identity:** While this documentation is in English for global accessibility, Alice maintains its core Swedish AI assistant identity. Voice commands, cultural references, and personality remain authentically Swedish. Swedish voice commands like "spela musik" (play music), "visa kalender" (show calendar) are preserved throughout the API to maintain Alice's unique character.