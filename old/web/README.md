# 🎤 Alice Frontend - Voice Pipeline Development

Alice's Next.js frontend with voice pipeline development in progress.

⚠️  **Status**: API endpoints working, full voice integration being debugged.

## 🚀 **Voice Pipeline Overview**

Alice provides two complementary voice interfaces:

### **VoiceBox** - Basic Voice Interface
- **Real-time Audio Visualization** - Ambient breathing animation + reactive audio bars
- **Browser Speech Recognition** - Optimized for Swedish language
- **Enhanced TTS Integration** - Alice backend TTS with personality/emotion control
- **Fallback System** - Graceful degradation: mic → demo → pseudo modes
- **Swedish Post-processing** - Intelligent correction of common mishearings

### **VoiceClient** - Advanced OpenAI Realtime
- **OpenAI Realtime API** - Professional-grade speech-to-text via WebRTC
- **Low-latency Streaming** - Real-time conversation with barge-in support  
- **Agent Bridge Architecture** - Server-sent events for streaming responses
- **WebRTC Integration** - Direct OpenAI connection with 24kHz audio
- **Professional Audio Processing** - Echo cancellation, noise suppression

## 📁 **Project Structure**

```
web/
├── app/
│   ├── components/           # Advanced voice components
│   │   ├── VoiceClient.tsx   # OpenAI Realtime integration
│   │   └── VoiceClientExample.tsx
│   ├── api/                  # Next.js API routes
│   │   ├── agent/stream/     # Agent bridge for VoiceClient
│   │   ├── realtime/ephemeral/ # OpenAI session creation
│   │   └── tts/openai-stream/  # Streaming TTS endpoint
│   ├── voice/                # Voice demo page
│   └── page.jsx             # Main HUD interface
├── components/               # Shared voice components
│   ├── VoiceBox.tsx         # Basic voice interface
│   └── VoiceInterface.tsx   # Wrapper component
├── lib/
│   ├── voice-client.js      # Advanced voice client library
│   ├── audio-enhancement.js # Audio processing utilities
│   └── voice-activity-detection.js
└── public/
    └── lib/voice-client.js  # Browser-compatible voice client
```

## 🎯 **Voice Components API**

### VoiceBox Component

**Basic Usage:**
```tsx
import VoiceBox from '@/components/VoiceBox';

function MyApp() {
  const handleVoiceInput = (text: string) => {
    console.log('User said:', text);
    // Process voice command
  };

  return (
    <VoiceBox
      bars={7}                     // Number of visualization bars
      personality="alice"          // alice | formal | casual
      emotion="friendly"           // neutral | happy | calm | confident | friendly
      voiceQuality="high"          // medium | high
      onVoiceInput={handleVoiceInput}
      enableWakeWord={true}        // Enable "Alice" wake word
      wakeWordSensitivity={0.7}    // 0.0 - 1.0 sensitivity
      allowDemo={true}             // Allow demo mode if mic blocked
      allowPseudo={true}           // Allow visual-only fallback
    />
  );
}
```

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `bars` | number | 7 | Number of audio visualization bars |
| `smoothing` | number | 0.15 | Audio smoothing factor (0-1) |
| `personality` | string | "alice" | TTS personality setting |
| `emotion` | string | "friendly" | Emotional tone for TTS |
| `voiceQuality` | string | "medium" | Voice quality preference |
| `onVoiceInput` | function | - | Callback for voice input |
| `enableWakeWord` | boolean | false | Enable wake word detection |
| `wakeWordSensitivity` | number | 0.7 | Wake word sensitivity |
| `allowDemo` | boolean | true | Allow demo mode fallback |
| `allowPseudo` | boolean | true | Allow visual-only mode |

### VoiceClient Component  

**Advanced Usage:**
```tsx
import VoiceClient from '@/app/components/VoiceClient';

function AdvancedVoiceApp() {
  const handleTranscript = (text: string, isFinal: boolean) => {
    console.log(`${isFinal ? 'Final' : 'Interim'}: ${text}`);
  };

  const handleError = (error: string) => {
    console.error('Voice error:', error);
  };

  const handleConnectionChange = (connected: boolean) => {
    console.log('Connection status:', connected);
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

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `personality` | string | "alice" | Voice personality |
| `emotion` | string | "friendly" | Emotional tone |
| `voiceQuality` | string | "medium" | Voice quality (medium/high) |
| `onTranscript` | function | - | Transcript callback |
| `onError` | function | - | Error callback |
| `onConnectionChange` | function | - | Connection status callback |

## ⚙️ **Configuration**

### Environment Variables

```bash
# .env.local
OPENAI_API_KEY=sk-...                    # Required for VoiceClient
NEXT_PUBLIC_VOICE_MODE=dual              # dual | voicebox | voiceclient
NEXT_PUBLIC_ALICE_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_ENABLE_VOICE_DEBUG=false     # Enable voice debugging
```

### Voice Client Library

**Browser Integration:**
```html
<!-- Include Alice Voice Client -->
<script src="/lib/voice-client.js"></script>
<script>
const alice = new AliceVoiceClient('session_123');

alice.on('voice_input', (data) => {
  console.log('Voice input:', data.text, data.final);
});

alice.on('alice_response', (response) => {
  console.log('Alice says:', response.text);
});

// Connect and start listening
await alice.connect();
alice.startListening();
</script>
```

**ES Module Usage:**
```javascript
import AliceVoiceClient from '@/lib/voice-client.js';

const voiceClient = new AliceVoiceClient();

// Event handlers
voiceClient.on('listening_started', () => {
  console.log('Started listening...');
});

voiceClient.on('speaking_started', (text) => {
  console.log('Alice speaking:', text);
});

// Initialize
await voiceClient.connect();
voiceClient.startListening();

// Swedish-optimized speech
voiceClient.speak('Hej! Jag är Alice.', {
  personality: 'alice',
  emotion: 'friendly',
  voice: 'sv_SE-nst-high'
});
```

## 🔧 **Development Setup**

### Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Open browser
open http://localhost:3000
```

### Voice Development

```bash
# Start with voice debugging enabled
NEXT_PUBLIC_ENABLE_VOICE_DEBUG=true npm run dev

# Test voice components
open http://localhost:3000/voice
```

### Backend Integration

Ensure Alice backend is running for full functionality:

```bash
# Start Alice backend (separate terminal)
cd ../server && python run.py

# Backend should be available at:
# http://localhost:8000
```

## 🎛️ **API Routes**

### `/api/realtime/ephemeral` 
Creates OpenAI Realtime session for VoiceClient.

**Response:**
```json
{
  "client_secret": { "value": "sk-..." },
  "ephemeral_key_id": "ephemeral_...",
  "model": "gpt-4o-realtime-preview",
  "voice": "alloy"
}
```

### `/api/agent/stream`
Forwards VoiceClient requests to Alice agent with SSE streaming.

**Request:**
```json
{
  "prompt": "spela musik",
  "context": {
    "personality": "alice",
    "emotion": "friendly"
  }
}
```

### `/api/tts/openai-stream`
Streaming TTS endpoint with Alice backend fallback.

**Features:**
- OpenAI TTS integration  
- Alice backend TTS fallback
- Streaming audio response
- Error handling with graceful degradation

## 🎨 **Voice Interface Design**

### VoiceBox Styling

- **Glassmorphism** - Cyan/blue theme with transparency
- **Ambient Animation** - Ultra-slow "zen breathing" when idle  
- **Reactive Visualization** - Audio bars respond to real-time input
- **Status Indicators** - Visual feedback for listening/processing/speaking states

### VoiceClient Interface

- **Connection Status** - Real-time connection state display
- **Transcript Display** - Scrollable transcript with timestamps  
- **Agent Response** - Streaming response visualization
- **Error Handling** - Clear error messages and recovery options

## 🔍 **Debugging & Troubleshooting**

### Common Issues

**Microphone Access Denied:**
```bash
# Enable HTTPS for development (required for mic access)
HTTPS=true npm run dev
```

**OpenAI API Key Missing:**
```bash
# VoiceClient requires OpenAI API key
echo "OPENAI_API_KEY=sk-..." >> .env.local
```

**Backend Connection Failed:**
```bash
# Ensure Alice backend is running
curl http://localhost:8000/api/health
```

### Debug Mode

Enable comprehensive voice debugging:

```bash
# Enable debug logging
NEXT_PUBLIC_ENABLE_VOICE_DEBUG=true npm run dev
```

**Browser Console:**
```javascript
// Check voice client status
console.log(window.AliceVoiceClient?.prototype.getStatus());

// Enable verbose logging
localStorage.setItem('alice_debug', 'true');
```

### Audio Issues

**No Audio Output:**
1. Check browser audio permissions
2. Verify TTS endpoint connectivity
3. Test with different audio devices

**Poor Speech Recognition:**
1. Check microphone quality/positioning
2. Verify Swedish language setting
3. Test in quiet environment

## 🚀 **Deployment**

### Production Build

```bash
# Build for production
npm run build

# Start production server  
npm run start
```

### Environment Setup

**Production Environment Variables:**
```bash
OPENAI_API_KEY=sk-...                 # OpenAI API key
NEXT_PUBLIC_VOICE_MODE=voiceclient    # Production voice mode
NEXT_PUBLIC_ALICE_BACKEND_URL=https://your-alice-backend.com
```

### HTTPS Requirements

For production voice features:
- **HTTPS Required** - Microphone access requires secure context
- **WebRTC** - Secure connection needed for real-time audio
- **Service Worker** - PWA features require HTTPS

## 📚 **Advanced Usage**

### Custom Voice Integration

```typescript
// Create custom voice component
import { useVoice } from '@/hooks/useVoice';

function CustomVoiceInterface() {
  const {
    isListening,
    isConnected,
    transcript,
    response,
    startListening,
    stopListening,
    speak
  } = useVoice({
    mode: 'voiceclient',
    personality: 'alice',
    onTranscript: (text, final) => {
      if (final) processCommand(text);
    }
  });

  return (
    <div>
      <button onClick={startListening} disabled={isListening}>
        {isListening ? 'Listening...' : 'Start Voice'}
      </button>
      
      <div>Status: {isConnected ? 'Connected' : 'Disconnected'}</div>
      <div>Transcript: {transcript}</div>
      <div>Alice: {response}</div>
    </div>
  );
}
```

### Voice Command Processing

```typescript
// Advanced command processing with Agent Core integration
class VoiceCommandProcessor {
  constructor() {
    this.agentCore = new AliceAgentCore();
    this.voiceClient = new AliceVoiceClient();
  }

  async processVoiceCommand(transcript: string) {
    try {
      // Send to Agent Core for processing
      const workflow = await this.agentCore.execute_workflow(transcript);
      
      // Handle streaming response
      workflow.on('chunk', (chunk) => {
        this.voiceClient.speak(chunk.content);
      });
      
      workflow.on('tool_executed', (result) => {
        this.voiceClient.speak(result.message);
      });
      
    } catch (error) {
      console.error('Voice command failed:', error);
      this.voiceClient.speak('Jag kunde inte utföra det kommandot.');
    }
  }
}
```

## 🏆 **Best Practices**

### Performance Optimization

1. **Lazy Loading** - Load voice components only when needed
2. **Audio Buffering** - Implement audio buffer management
3. **Connection Pooling** - Reuse WebSocket connections
4. **Caching** - Cache TTS responses for repeated phrases

### User Experience

1. **Progressive Enhancement** - Graceful fallbacks for unsupported browsers
2. **Visual Feedback** - Clear indicators for voice states
3. **Error Recovery** - Automatic retry with user notification
4. **Accessibility** - Keyboard shortcuts and screen reader support

### Security Considerations

1. **API Key Protection** - Never expose OpenAI keys client-side
2. **Input Validation** - Sanitize voice input before processing
3. **Rate Limiting** - Implement client-side request throttling
4. **CORS Configuration** - Proper cross-origin resource sharing setup

---

**För mer information:**
- **[API Documentation](../API.md)** - Complete API reference
- **[Agent Core](../AGENT_CORE.md)** - Voice pipeline architecture  
- **[Main README](../README.md)** - Overall system overview
