# Alice Voice Client Component

A comprehensive React component that integrates WebRTC, OpenAI Realtime API, and Alice's agent system for real-time voice interactions.

## Overview

The `VoiceClient.tsx` component provides:

- **WebRTC Integration**: Real-time audio communication with OpenAI's Realtime API
- **Speech Recognition**: Real-time transcription of Swedish speech input
- **Agent Integration**: Server-Sent Events (SSE) connection to Alice's agent bridge
- **Text-to-Speech**: Streaming TTS with barge-in capability
- **State Management**: Comprehensive connection and voice state tracking

## Features

### 🎙️ Audio Input/Output
- Microphone access with audio enhancements (echo cancellation, noise suppression)
- Real-time audio streaming via WebRTC
- Support for 24kHz audio sampling

### 📝 Real-time Transcription
- Interim and final transcript display
- Swedish language optimization with post-processing
- Timestamp tracking for conversation history

### 🤖 Alice Agent Integration
- SSE streaming connection to `/api/agent/stream`
- Real-time agent responses with typing indicators
- Tool execution support and metadata handling

### 🔊 Text-to-Speech
- OpenAI TTS streaming via `/api/tts/openai-stream`
- Barge-in capability (interrupt current speech)
- Configurable voice quality and personality

### 🎨 UI/UX
- Alice's signature cyan/blue color scheme
- Real-time status indicators
- Progressive UX: listening → processing → speaking
- Error boundaries with user feedback

## API Dependencies

The component requires these backend endpoints:

```typescript
GET /api/realtime/ephemeral          // Create OpenAI Realtime session
POST /api/agent/stream               // Stream Alice agent responses
POST /api/tts/openai-stream         // Stream TTS audio
```

## Usage

### Basic Usage

```tsx
import VoiceClient from './components/VoiceClient'

export default function MyPage() {
  const handleTranscript = (text: string, isFinal: boolean) => {
    console.log('Transcript:', text, isFinal ? '(final)' : '(interim)')
  }

  const handleError = (error: string) => {
    console.error('Voice error:', error)
  }

  const handleConnectionChange = (connected: boolean) => {
    console.log('Connection:', connected ? 'connected' : 'disconnected')
  }

  return (
    <VoiceClient
      personality="alice"
      emotion="friendly"
      voiceQuality="medium"
      onTranscript={handleTranscript}
      onError={handleError}
      onConnectionChange={handleConnectionChange}
    />
  )
}
```

### Advanced Usage with State Management

```tsx
import { useState } from 'react'
import VoiceClient from './components/VoiceClient'

export default function AdvancedVoicePage() {
  const [transcripts, setTranscripts] = useState<string[]>([])
  const [isConnected, setIsConnected] = useState(false)

  return (
    <div>
      <VoiceClient
        personality="alice"
        emotion="confident"
        voiceQuality="high"
        onTranscript={(text, isFinal) => {
          if (isFinal) {
            setTranscripts(prev => [...prev, text])
          }
        }}
        onConnectionChange={setIsConnected}
      />
      
      {/* Display conversation history */}
      <div>
        <h3>Conversation History</h3>
        {transcripts.map((transcript, i) => (
          <p key={i}>{transcript}</p>
        ))}
      </div>
    </div>
  )
}
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `personality` | `string` | `'alice'` | Voice personality: 'alice', 'formal', 'casual' |
| `emotion` | `string` | `'friendly'` | Emotional tone: 'neutral', 'happy', 'calm', 'confident', 'friendly' |
| `voiceQuality` | `string` | `'medium'` | TTS quality: 'medium', 'high' |
| `className` | `string` | `''` | Additional CSS classes |
| `onTranscript` | `(text: string, isFinal: boolean) => void` | - | Transcript callback |
| `onError` | `(error: string) => void` | - | Error callback |
| `onConnectionChange` | `(connected: boolean) => void` | - | Connection state callback |

## State Management

### Connection States
- `'disconnected'` - Not connected to any services
- `'connecting'` - Establishing connections  
- `'connected'` - All systems connected and ready
- `'error'` - Connection or system error

### Voice States  
- `'idle'` - Ready to listen
- `'listening'` - Actively recording audio
- `'processing'` - Transcribing and processing with Alice
- `'speaking'` - Playing TTS response

## Technical Architecture

### WebRTC Flow
1. Create ephemeral session via `/api/realtime/ephemeral`
2. Establish WebRTC peer connection with OpenAI
3. Stream microphone audio to OpenAI Realtime API
4. Receive real-time transcriptions and audio responses

### Agent Processing Flow
1. Final transcript sent to `/api/agent/stream` via SSE
2. Alice agent processes request with RAG and tools
3. Streaming response chunks displayed in real-time
4. Complete response sent to TTS for speech synthesis

### Audio Pipeline
```
Microphone → WebRTC → OpenAI Realtime → Transcription
                                     ↓
TTS Audio ← Alice Agent ← SSE Stream ← Agent Bridge
```

## Browser Requirements

- **WebRTC Support**: Chrome 54+, Firefox 63+, Safari 11+
- **MediaDevices API**: For microphone access
- **EventSource API**: For SSE connections
- **Web Audio API**: For real-time audio processing
- **HTTPS Required**: For microphone permissions (localhost exception)

## Error Handling

The component includes comprehensive error handling for:

- Microphone permission denied
- WebRTC connection failures  
- OpenAI Realtime API errors
- SSE connection drops
- TTS synthesis failures
- Network connectivity issues

All errors are surfaced through the `onError` callback and displayed in the UI.

## Styling

The component uses Alice's signature design system:

- **Primary Colors**: Cyan (#22d3ee) for connections and controls
- **Secondary Colors**: Purple (#a855f7) for agent responses  
- **Status Colors**: Green (connected), Yellow (processing), Red (error)
- **Glass Morphism**: Semi-transparent backgrounds with subtle borders
- **Animations**: Smooth transitions and pulsing indicators

## Performance Considerations

- **Audio Buffering**: Optimized for low-latency real-time streaming
- **Memory Management**: Automatic cleanup of audio contexts and streams
- **Connection Pooling**: Efficient WebRTC and SSE connection management
- **Barge-in Support**: Instant interruption without audio buildup

## Development & Testing

1. Ensure Alice server is running with all required endpoints
2. Use HTTPS or localhost for microphone access
3. Test with various audio qualities and network conditions
4. Verify barge-in functionality with overlapping audio

## Integration with Alice

The component seamlessly integrates with:

- **Alice Agent Bridge**: For intelligent response processing
- **Alice Memory System**: For conversation context
- **Alice Tool System**: For action execution
- **Alice TTS**: For Swedish voice synthesis
- **Alice RAG**: For knowledge-enhanced responses

This creates a complete voice-first interface for natural Swedish conversations with Alice.