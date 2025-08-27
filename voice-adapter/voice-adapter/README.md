# @alice/voice-adapter

A TypeScript voice adapter module for Alice AI system supporting multiple voice providers with sub-500ms latency targets.

## Features

- **Provider Abstraction**: Swap voice providers without changing application code
- **OpenAI Realtime API**: Primary provider with WebSocket real-time communication
- **Performance Monitoring**: Built-in latency tracking and metrics collection
- **Voice Activity Detection**: Intelligent audio processing utilities
- **Extensible Architecture**: Easy to add new voice providers
- **TypeScript First**: Complete type safety and IntelliSense support

## Installation

```bash
npm install @alice/voice-adapter
```

## Quick Start

```typescript
import { VoiceProviderFactory, VoiceConfig } from '@alice/voice-adapter';

// Initialize configuration
const config = new VoiceConfig({
  provider: 'openai-realtime',
  openai: {
    apiKey: process.env.OPENAI_API_KEY,
    model: 'gpt-4o-realtime-preview-2024-10-01'
  }
});

// Create voice provider
const voiceProvider = await VoiceProviderFactory.create('openai-realtime', config);

// Start voice session
await voiceProvider.connect();

// Handle events
voiceProvider.on('transcript', (data) => {
  console.log('User said:', data.text);
});

voiceProvider.on('audio_response', (data) => {
  // Play audio response
  console.log('Assistant response audio received');
});
```

## Architecture

### Core Components

- **VoiceProvider**: Main interface for voice communication
- **ASRAdapter**: Speech-to-text processing
- **TTSAdapter**: Text-to-speech synthesis
- **LatencyTracker**: Performance monitoring
- **VAD**: Voice Activity Detection
- **AudioUtils**: Audio format conversion utilities

### Supported Providers

- **OpenAI Realtime API**: Real-time voice conversation
- **Whisper (Stub)**: Speech recognition (future implementation)
- **Piper (Stub)**: Text-to-speech (future implementation)

## Configuration

```typescript
interface VoiceConfig {
  provider: 'openai-realtime' | 'whisper' | 'piper';
  latencyTarget: number; // Target latency in milliseconds
  openai?: {
    apiKey: string;
    model: string;
    voice?: string;
  };
  whisper?: {
    modelPath: string;
    language?: string;
  };
  piper?: {
    modelPath: string;
    voice?: string;
  };
}
```

## Performance Targets

- **Latency**: Sub-500ms end-to-end response time
- **Real-time Processing**: Streaming audio with minimal buffering
- **Memory Efficiency**: Optimized for continuous voice sessions

## Development

```bash
# Install dependencies
npm install

# Build the module
npm run build

# Run tests
npm test

# Watch mode for development
npm run build:watch
```

## License

MIT