# 🎙️ Cursor Instructions: Voice Adapter Implementation

**Exact step-by-step implementation för OpenAI Realtime Voice Adapter Architecture**

---

## 📁 Implementation Order

### STEP 1: Skapa Base Directory Structure
```bash
mkdir -p voice/{providers,metrics,types,utils}
```

### STEP 2: Core Type Definitions
**File: `voice/types/index.ts`**
```typescript
// Voice Adapter Core Types
export interface VoiceConfig {
  provider: 'openai' | 'local' | 'hybrid';
  vad: {
    enabled: boolean;
    sensitivity: number; // 0-1
    timeout_ms: number;
  };
  metrics: {
    enabled: boolean;
    batch_interval_ms: number;
  };
}

export interface ASROptions {
  onPartial: (result: PartialResult) => void;
  onFinal: (result: FinalResult) => void;
  onError: (error: ASRError) => void;
}

export interface TTSOptions {
  text: string;
  voiceId?: string;
  ssml?: boolean;
  speed?: number; // 0.25-4.0
  onStart: () => void;
  onChunk: (chunk: AudioChunk) => void;
  onEnd: () => void;
  onError: (error: TTSError) => void;
}

export interface PartialResult {
  text: string;
  confidence: number;
  timestamp_ms: number;
  is_stable: boolean;
}

export interface FinalResult {
  text: string;
  confidence: number;
  start_ms: number;
  end_ms: number;
  segments?: WordSegment[];
}

export interface WordSegment {
  word: string;
  start_ms: number;
  end_ms: number;
  confidence: number;
}

export interface AudioChunk {
  data: Float32Array;
  sample_rate: number;
  timestamp_ms: number;
  is_final: boolean;
}

export interface ASRError {
  code: 'network' | 'audio' | 'permission' | 'timeout' | 'quota';
  message: string;
  recoverable: boolean;
}

export interface TTSError {
  code: 'network' | 'quota' | 'timeout' | 'format' | 'voice_unavailable';
  message: string;
  recoverable: boolean;
}

// Metrics Types
export interface VoiceMetrics {
  session_id: string;
  timestamp_ms: number;
  asr_partial_latency_ms?: number;
  asr_final_latency_ms?: number;
  tts_ttfa_ms?: number; // Time to First Audio
  e2e_roundtrip_ms?: number;
  error_count: number;
  fallback_triggered: boolean;
}
```

### STEP 3: Adapter Interface Contracts
**File: `voice/adapter.ts`**
```typescript
import { 
  ASROptions, TTSOptions, VoiceConfig, AudioChunk, 
  PartialResult, FinalResult 
} from './types';

export interface ASRAdapter {
  start(options: ASROptions): Promise<void>;
  stop(): Promise<void>;
  isListening: boolean;
}

export interface TTSAdapter {
  speak(options: TTSOptions): Promise<string>; // Returns playback ID
  cancel(playbackId?: string): Promise<void>;
  isSpeaking: boolean;
}

export interface VoiceAdapter {
  asr: ASRAdapter;
  tts: TTSAdapter;
  config: VoiceConfig;
  
  // Lifecycle
  initialize(): Promise<void>;
  destroy(): Promise<void>;
  
  // Health & Status
  isHealthy(): boolean;
  getStats(): Record<string, any>;
}

// Event Emitter for Voice Pipeline
export interface VoiceEvents {
  'asr:partial': (result: PartialResult) => void;
  'asr:final': (result: FinalResult) => void;
  'asr:error': (error: ASRError) => void;
  'tts:start': (playbackId: string) => void;
  'tts:chunk': (chunk: AudioChunk) => void;
  'tts:end': (playbackId: string) => void;
  'tts:error': (error: TTSError, playbackId?: string) => void;
  'metrics': (metrics: VoiceMetrics) => void;
}
```

### STEP 4: Environment Configuration
**File: `voice/config.ts`**
```typescript
export interface VoiceEnvConfig {
  VOICE_PROVIDER: 'openai' | 'local' | 'hybrid';
  VOICE_VAD: 'on' | 'off';
  VOICE_LOG_METRICS: 'on' | 'off';
  
  // OpenAI Realtime
  OPENAI_REALTIME_MODEL: string;
  OPENAI_REALTIME_VOICE: string;
  OPENAI_REALTIME_MAX_TOKENS: number;
  OPENAI_API_KEY: string;
  
  // VAD Settings
  VAD_SENSITIVITY: number;
  VAD_TIMEOUT_MS: number;
  
  // Performance
  METRICS_BATCH_INTERVAL_MS: number;
}

export function getVoiceConfig(): VoiceEnvConfig {
  return {
    VOICE_PROVIDER: (process.env.VOICE_PROVIDER as any) || 'openai',
    VOICE_VAD: process.env.VOICE_VAD || 'on',
    VOICE_LOG_METRICS: process.env.VOICE_LOG_METRICS || 'on',
    
    OPENAI_REALTIME_MODEL: process.env.OPENAI_REALTIME_MODEL || 'gpt-4-realtime',
    OPENAI_REALTIME_VOICE: process.env.OPENAI_REALTIME_VOICE || 'alloy',
    OPENAI_REALTIME_MAX_TOKENS: Number(process.env.OPENAI_REALTIME_MAX_TOKENS) || 150,
    OPENAI_API_KEY: process.env.OPENAI_API_KEY || '',
    
    VAD_SENSITIVITY: Number(process.env.VAD_SENSITIVITY) || 0.6,
    VAD_TIMEOUT_MS: Number(process.env.VAD_TIMEOUT_MS) || 1000,
    
    METRICS_BATCH_INTERVAL_MS: Number(process.env.METRICS_BATCH_INTERVAL_MS) || 5000,
  };
}

export function validateVoiceConfig(config: VoiceEnvConfig): string[] {
  const errors: string[] = [];
  
  if (config.VOICE_PROVIDER === 'openai' && !config.OPENAI_API_KEY) {
    errors.push('OPENAI_API_KEY required when VOICE_PROVIDER=openai');
  }
  
  if (config.VAD_SENSITIVITY < 0 || config.VAD_SENSITIVITY > 1) {
    errors.push('VAD_SENSITIVITY must be between 0 and 1');
  }
  
  if (config.OPENAI_REALTIME_MAX_TOKENS < 1 || config.OPENAI_REALTIME_MAX_TOKENS > 4096) {
    errors.push('OPENAI_REALTIME_MAX_TOKENS must be between 1 and 4096');
  }
  
  return errors;
}
```

### STEP 5: Metrics & Performance Tracking
**File: `voice/metrics/latency.ts`**
```typescript
import { VoiceMetrics } from '../types';

export class LatencyTracker {
  private startTimes: Map<string, number> = new Map();
  private metrics: VoiceMetrics[] = [];
  
  constructor(private sessionId: string) {}
  
  // Mark start of measurement
  start(event: string): void {
    this.startTimes.set(event, performance.now());
  }
  
  // Mark end and return duration
  end(event: string): number {
    const startTime = this.startTimes.get(event);
    if (!startTime) {
      console.warn(\`LatencyTracker: No start time for event \${event}\`);
      return 0;
    }
    
    const duration = performance.now() - startTime;
    this.startTimes.delete(event);
    return duration;
  }
  
  // Record metric
  record(metric: Partial<VoiceMetrics>): void {
    const fullMetric: VoiceMetrics = {
      session_id: this.sessionId,
      timestamp_ms: Date.now(),
      error_count: 0,
      fallback_triggered: false,
      ...metric
    };
    
    this.metrics.push(fullMetric);
  }
  
  // Get accumulated metrics
  getMetrics(): VoiceMetrics[] {
    return [...this.metrics];
  }
  
  // Clear metrics (after reporting)
  clear(): void {
    this.metrics = [];
  }
  
  // Calculate summary stats
  getSummary() {
    if (this.metrics.length === 0) return null;
    
    const asrPartialLatencies = this.metrics
      .map(m => m.asr_partial_latency_ms)
      .filter(l => l !== undefined) as number[];
      
    const e2eLatencies = this.metrics
      .map(m => m.e2e_roundtrip_ms)
      .filter(l => l !== undefined) as number[];
    
    return {
      total_interactions: this.metrics.length,
      asr_partial_p50: percentile(asrPartialLatencies, 0.5),
      asr_partial_p95: percentile(asrPartialLatencies, 0.95),
      e2e_p50: percentile(e2eLatencies, 0.5),
      e2e_p95: percentile(e2eLatencies, 0.95),
      error_rate: this.metrics.filter(m => m.error_count > 0).length / this.metrics.length,
      fallback_rate: this.metrics.filter(m => m.fallback_triggered).length / this.metrics.length,
    };
  }
}

function percentile(arr: number[], p: number): number {
  if (arr.length === 0) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const index = Math.ceil(sorted.length * p) - 1;
  return sorted[Math.max(0, index)];
}
```

### STEP 6: OpenAI Realtime Provider (Primary Implementation)
**File: `voice/providers/openaiRealtime.ts`**
```typescript
import { EventEmitter } from 'events';
import { 
  VoiceAdapter, ASRAdapter, TTSAdapter, VoiceConfig,
  ASROptions, TTSOptions, PartialResult, FinalResult, AudioChunk,
  ASRError, TTSError, VoiceEvents
} from '../adapter';
import { LatencyTracker } from '../metrics/latency';

export class OpenAIRealtimeAdapter extends EventEmitter implements VoiceAdapter {
  public asr: ASRAdapter;
  public tts: TTSAdapter;
  public config: VoiceConfig;
  
  private ws: WebSocket | null = null;
  private latencyTracker: LatencyTracker;
  private sessionId: string;
  
  constructor(config: VoiceConfig) {
    super();
    this.config = config;
    this.sessionId = \`voice_\${Date.now()}\`;
    this.latencyTracker = new LatencyTracker(this.sessionId);
    
    this.asr = new OpenAIRealtimeASR(this);
    this.tts = new OpenAIRealtimeTTS(this);
  }
  
  async initialize(): Promise<void> {
    // Initialize OpenAI Realtime WebSocket connection
    const wsUrl = 'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01';
    
    this.ws = new WebSocket(wsUrl, {
      headers: {
        'Authorization': \`Bearer \${process.env.OPENAI_API_KEY}\`,
        'OpenAI-Beta': 'realtime=v1',
      }
    });
    
    return new Promise((resolve, reject) => {
      if (!this.ws) return reject(new Error('Failed to create WebSocket'));
      
      this.ws.onopen = () => {
        console.log('OpenAI Realtime connected');
        this._setupEventHandlers();
        resolve();
      };
      
      this.ws.onerror = (error) => {
        console.error('OpenAI Realtime error:', error);
        reject(error);
      };
      
      this.ws.onclose = (event) => {
        console.log('OpenAI Realtime disconnected:', event.code, event.reason);
        this._handleDisconnection();
      };
    });
  }
  
  private _setupEventHandlers(): void {
    if (!this.ws) return;
    
    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this._handleRealtimeMessage(message);
      } catch (error) {
        console.error('Failed to parse Realtime message:', error);
      }
    };
  }
  
  private _handleRealtimeMessage(message: any): void {
    const { type } = message;
    
    switch (type) {
      case 'conversation.item.input_audio_transcription.completed':
        this._handleASRResult(message, false); // Final
        break;
        
      case 'conversation.item.input_audio_transcription.partial':
        this._handleASRResult(message, true); // Partial  
        break;
        
      case 'response.audio.delta':
        this._handleTTSChunk(message);
        break;
        
      case 'response.audio.done':
        this._handleTTSComplete(message);
        break;
        
      case 'error':
        this._handleRealtimeError(message);
        break;
        
      default:
        console.log('Unhandled Realtime message type:', type);
    }
  }
  
  private _handleASRResult(message: any, isPartial: boolean): void {
    const { transcript, confidence } = message;
    const timestamp_ms = Date.now();
    
    if (isPartial) {
      const result: PartialResult = {
        text: transcript,
        confidence: confidence || 0.8,
        timestamp_ms,
        is_stable: false
      };
      this.emit('asr:partial', result);
    } else {
      const latency = this.latencyTracker.end('asr_processing');
      const result: FinalResult = {
        text: transcript,
        confidence: confidence || 0.8,
        start_ms: timestamp_ms - latency,
        end_ms: timestamp_ms
      };
      
      this.latencyTracker.record({ asr_final_latency_ms: latency });
      this.emit('asr:final', result);
    }
  }
  
  private _handleTTSChunk(message: any): void {
    const { audio, item_id } = message;
    // Convert base64 audio to Float32Array
    const audioData = this._base64ToFloat32Array(audio);
    
    const chunk: AudioChunk = {
      data: audioData,
      sample_rate: 24000, // OpenAI Realtime uses 24kHz
      timestamp_ms: Date.now(),
      is_final: false
    };
    
    this.emit('tts:chunk', chunk);
  }
  
  private _handleTTSComplete(message: any): void {
    const { item_id } = message;
    const latency = this.latencyTracker.end('tts_processing');
    
    this.latencyTracker.record({ tts_ttfa_ms: latency });
    this.emit('tts:end', item_id);
  }
  
  private _handleRealtimeError(message: any): void {
    const { error } = message;
    console.error('OpenAI Realtime error:', error);
    
    const asrError: ASRError = {
      code: 'network',
      message: error.message || 'Unknown Realtime error',
      recoverable: true
    };
    
    this.emit('asr:error', asrError);
  }
  
  private _handleDisconnection(): void {
    // Implement reconnection logic
    console.log('Realtime disconnected, attempting reconnect...');
    setTimeout(() => this.initialize().catch(console.error), 1000);
  }
  
  private _base64ToFloat32Array(base64: string): Float32Array {
    // Implement base64 audio decoding
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    // Convert PCM16 to Float32
    const int16Array = new Int16Array(bytes.buffer);
    const float32Array = new Float32Array(int16Array.length);
    
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }
    
    return float32Array;
  }
  
  async destroy(): Promise<void> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close();
    }
    this.removeAllListeners();
  }
  
  isHealthy(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
  
  getStats(): Record<string, any> {
    return {
      provider: 'openai-realtime',
      session_id: this.sessionId,
      connection_state: this.ws?.readyState || 'disconnected',
      metrics_summary: this.latencyTracker.getSummary(),
    };
  }
}

// ASR Implementation for OpenAI Realtime
class OpenAIRealtimeASR implements ASRAdapter {
  public isListening = false;
  
  constructor(private parent: OpenAIRealtimeAdapter) {}
  
  async start(options: ASROptions): Promise<void> {
    // Register callbacks
    this.parent.on('asr:partial', options.onPartial);
    this.parent.on('asr:final', options.onFinal);
    this.parent.on('asr:error', options.onError);
    
    // Start audio capture and streaming to Realtime API
    this.isListening = true;
    this.parent.latencyTracker.start('asr_processing');
    
    // Send audio configuration to Realtime API
    if (this.parent.ws) {
      this.parent.ws.send(JSON.stringify({
        type: 'input_audio_buffer.append',
        // Audio streaming implementation here
      }));
    }
  }
  
  async stop(): Promise<void> {
    this.isListening = false;
    this.parent.removeAllListeners('asr:partial');
    this.parent.removeAllListeners('asr:final');
    this.parent.removeAllListeners('asr:error');
  }
}

// TTS Implementation for OpenAI Realtime  
class OpenAIRealtimeTTS implements TTSAdapter {
  public isSpeaking = false;
  private playbackId = 0;
  
  constructor(private parent: OpenAIRealtimeAdapter) {}
  
  async speak(options: TTSOptions): Promise<string> {
    const playbackId = \`tts_\${++this.playbackId}\`;
    
    // Register callbacks
    this.parent.once('tts:start', options.onStart);
    this.parent.on('tts:chunk', options.onChunk);
    this.parent.once('tts:end', options.onEnd);
    this.parent.once('tts:error', options.onError);
    
    this.isSpeaking = true;
    this.parent.latencyTracker.start('tts_processing');
    
    // Send TTS request to Realtime API
    if (this.parent.ws) {
      this.parent.ws.send(JSON.stringify({
        type: 'response.create',
        response: {
          modalities: ['audio', 'text'],
          instructions: \`Please respond with: "\${options.text}"\`,
          voice: this.parent.config.provider === 'openai' ? 'alloy' : options.voiceId,
        }
      }));
    }
    
    return playbackId;
  }
  
  async cancel(playbackId?: string): Promise<void> {
    this.isSpeaking = false;
    
    if (this.parent.ws) {
      this.parent.ws.send(JSON.stringify({
        type: 'response.cancel'
      }));
    }
  }
}
```

### STEP 7: Stub Providers (för framtida implementation)
**File: `voice/providers/whisperStub.ts`**
```typescript
import { ASRAdapter, ASROptions } from '../adapter';

export class WhisperStubASR implements ASRAdapter {
  public isListening = false;
  
  async start(options: ASROptions): Promise<void> {
    throw new Error('Whisper ASR not implemented - use VOICE_PROVIDER=openai');
  }
  
  async stop(): Promise<void> {
    this.isListening = false;
  }
}
```

**File: `voice/providers/piperStub.ts`**
```typescript
import { TTSAdapter, TTSOptions } from '../adapter';

export class PiperStubTTS implements TTSAdapter {
  public isSpeaking = false;
  
  async speak(options: TTSOptions): Promise<string> {
    throw new Error('Piper TTS not implemented - use VOICE_PROVIDER=openai');
  }
  
  async cancel(playbackId?: string): Promise<void> {
    this.isSpeaking = false;
  }
}
```

### STEP 8: Factory & Provider Selection
**File: `voice/factory.ts`**
```typescript
import { VoiceAdapter } from './adapter';
import { getVoiceConfig, validateVoiceConfig } from './config';
import { OpenAIRealtimeAdapter } from './providers/openaiRealtime';

export function createVoiceAdapter(): VoiceAdapter {
  const config = getVoiceConfig();
  const errors = validateVoiceConfig(config);
  
  if (errors.length > 0) {
    throw new Error(\`Voice configuration errors: \${errors.join(', ')}\`);
  }
  
  switch (config.VOICE_PROVIDER) {
    case 'openai':
      return new OpenAIRealtimeAdapter({
        provider: 'openai',
        vad: {
          enabled: config.VOICE_VAD === 'on',
          sensitivity: config.VAD_SENSITIVITY,
          timeout_ms: config.VAD_TIMEOUT_MS,
        },
        metrics: {
          enabled: config.VOICE_LOG_METRICS === 'on',
          batch_interval_ms: config.METRICS_BATCH_INTERVAL_MS,
        }
      });
      
    case 'local':
      throw new Error('Local voice provider not yet implemented');
      
    case 'hybrid':
      throw new Error('Hybrid voice provider not yet implemented');
      
    default:
      throw new Error(\`Unknown voice provider: \${config.VOICE_PROVIDER}\`);
  }
}

export { VoiceAdapter } from './adapter';
export * from './types';
```

### STEP 9: Package Index & Exports
**File: `voice/index.ts`**
```typescript
// Main voice package exports
export { createVoiceAdapter, VoiceAdapter } from './factory';
export * from './types';
export * from './adapter';
export { getVoiceConfig } from './config';
export { LatencyTracker } from './metrics/latency';

// Re-export providers for direct access if needed
export { OpenAIRealtimeAdapter } from './providers/openaiRealtime';
```

---

## 🧪 Testing Implementation

### STEP 10: Basic Integration Test
**File: `voice/test/integration.test.ts`**
```typescript
import { createVoiceAdapter } from '../index';

async function testVoiceAdapter() {
  console.log('🧪 Testing Voice Adapter Integration...');
  
  const adapter = createVoiceAdapter();
  
  try {
    // Test initialization
    await adapter.initialize();
    console.log('✅ Adapter initialized');
    
    // Test health check
    const isHealthy = adapter.isHealthy();
    console.log(\`✅ Health check: \${isHealthy ? 'healthy' : 'unhealthy'}\`);
    
    // Test ASR
    let partialReceived = false;
    let finalReceived = false;
    
    await adapter.asr.start({
      onPartial: (result) => {
        console.log('📝 ASR Partial:', result.text);
        partialReceived = true;
      },
      onFinal: (result) => {
        console.log('📝 ASR Final:', result.text);
        finalReceived = true;
      },
      onError: (error) => {
        console.error('❌ ASR Error:', error);
      }
    });
    
    // Test TTS
    const playbackId = await adapter.tts.speak({
      text: 'Hello, this is a test of the text-to-speech system.',
      onStart: () => console.log('🔊 TTS Started'),
      onChunk: (chunk) => console.log(\`🎵 TTS Chunk: \${chunk.data.length} samples\`),
      onEnd: () => console.log('✅ TTS Complete'),
      onError: (error) => console.error('❌ TTS Error:', error)
    });
    
    console.log(\`🎙️ TTS Playback ID: \${playbackId}\`);
    
    // Get stats
    const stats = adapter.getStats();
    console.log('📊 Adapter Stats:', JSON.stringify(stats, null, 2));
    
  } catch (error) {
    console.error('💥 Test failed:', error);
  } finally {
    await adapter.destroy();
    console.log('🧹 Adapter destroyed');
  }
}

// Run test if called directly
if (require.main === module) {
  testVoiceAdapter().catch(console.error);
}
```

---

## 🔧 Environment Setup

### STEP 11: Environment Variables
**File: `.env.example` (lägg till dessa rader)**
```bash
# Voice Adapter Configuration
VOICE_PROVIDER=openai
VOICE_VAD=on
VOICE_LOG_METRICS=on

# OpenAI Realtime API
OPENAI_API_KEY=sk-your-key-here
OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview-2024-10-01
OPENAI_REALTIME_VOICE=alloy
OPENAI_REALTIME_MAX_TOKENS=150

# VAD Settings  
VAD_SENSITIVITY=0.6
VAD_TIMEOUT_MS=1000

# Performance
METRICS_BATCH_INTERVAL_MS=5000
```

### STEP 12: Package Dependencies
**Lägg till i `package.json`:**
```json
{
  "dependencies": {
    "ws": "^8.14.2",
    "@types/ws": "^8.5.8"
  }
}
```

---

## 🎯 Implementation Checklist

### Phase 1 - Core Structure ✅
- [ ] Create directory structure (`voice/`)
- [ ] Implement type definitions (`types/index.ts`)
- [ ] Create adapter interfaces (`adapter.ts`)
- [ ] Setup configuration system (`config.ts`)

### Phase 2 - Metrics & Tracking ✅  
- [ ] Implement latency tracker (`metrics/latency.ts`)
- [ ] Add performance measurement points
- [ ] Create metrics collection system

### Phase 3 - OpenAI Realtime Provider ✅
- [ ] Implement OpenAI Realtime adapter (`providers/openaiRealtime.ts`)
- [ ] Add WebSocket connection management
- [ ] Handle ASR/TTS event routing
- [ ] Add error handling & reconnection

### Phase 4 - Stub Providers ✅
- [ ] Create Whisper stub (`providers/whisperStub.ts`)
- [ ] Create Piper stub (`providers/piperStub.ts`)
- [ ] Add "not implemented" errors

### Phase 5 - Factory & Integration ✅
- [ ] Implement provider factory (`factory.ts`)
- [ ] Add main package exports (`index.ts`)
- [ ] Create integration test (`test/integration.test.ts`)

### Phase 6 - Environment & Setup ✅
- [ ] Update environment variables (`.env.example`)
- [ ] Add package dependencies (`package.json`)
- [ ] Test end-to-end integration

---

## 🚀 Next Steps Efter Implementation

1. **Test Basic Integration**
   ```bash
   npm run test:voice-adapter
   ```

2. **Integrate with UI**
   - Connect voice events to UI states
   - Add microphone capture
   - Implement playback system

3. **Add Error Handling**
   - Reconnection on disconnect
   - Fallback to text mode
   - User-friendly error messages

4. **Performance Monitoring**  
   - KPI dashboard integration
   - Real-time latency alerts
   - Usage metrics collection

---

*Implementation Guide Complete - Ready for Development! 🎙️*