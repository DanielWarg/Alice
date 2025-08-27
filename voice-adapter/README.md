# @alice/voice-adapter

Modular voice adapter with OpenAI Realtime API and local provider support for Alice AI Assistant.

## Features

- 🎙️ **OpenAI Realtime API** - Production-ready voice with GPT-4 integration  
- 🔌 **Adapter Pattern** - Swap providers without changing application code
- 📊 **Performance Metrics** - Built-in latency tracking and performance monitoring
- 🎚️ **Voice Activity Detection** - Smart speech/silence detection
- 🔧 **Environment Configuration** - Easy setup with environment variables
- 📈 **Future-Proof** - Ready for local Whisper + Piper integration

## Quick Start

```bash
npm install @alice/voice-adapter
```

```typescript
import { createVoiceAdapter } from '@alice/voice-adapter';

// Initialize the voice adapter
const voiceAdapter = createVoiceAdapter();
console.log(voiceAdapter.status); // "Voice adapter ready for implementation"
```

## Architecture

### Provider Pattern
```
┌─────────────────────┐
│   Application UI    │
├─────────────────────┤
│   Voice Adapter     │
├─────────────────────┤
│ Provider (OpenAI)   │
│ ┌─────────┐ ┌─────┐ │
│ │   ASR   │ │ TTS │ │
│ └─────────┘ └─────┘ │
└─────────────────────┘
```

### Performance Metrics
- **ASR Partial Latency**: Time to first transcription result
- **ASR Final Latency**: Time to complete transcription  
- **TTS TTFA**: Time to First Audio generation
- **E2E Roundtrip**: Complete conversation turn latency

## Provider Status

| Provider | ASR | TTS | Status | Notes |
|----------|-----|-----|---------|--------|
| OpenAI Realtime | 🚧 | 🚧 | Stub | Ready for implementation |
| Local Whisper | 🚧 | ❌ | Stub | Privacy-first ASR |
| Local Piper | ❌ | 🚧 | Stub | Multi-language TTS |
| Hybrid | 🚧 | 🚧 | Future | Best of both worlds |

## Development Status

This is currently a **foundational implementation** with comprehensive TypeScript types and interfaces. The core architecture is complete with stub implementations ready for:

1. **OpenAI Realtime API Integration** - WebSocket connection, session management
2. **Local Provider Integration** - Whisper ASR and Piper TTS adapters  
3. **Performance Monitoring** - Latency tracking and metrics collection
4. **Voice Activity Detection** - Audio processing utilities

## Next Steps

1. Implement OpenAI Realtime Provider with actual WebSocket connection
2. Add local Whisper and Piper provider implementations
3. Build comprehensive test suite
4. Integrate with Alice's main application

## Contributing

This module is designed for easy extension with new voice providers. See `src/providers/` for implementation examples.

## License

MIT License - Part of Alice AI Assistant