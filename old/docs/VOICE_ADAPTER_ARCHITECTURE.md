# 🎙️ Voice Adapter Architecture

**Thin Slice Approach: OpenAI Realtime → Local Pipeline Migration**

---

## 📋 Översikt

Voice Adapter Architecture följer "thin slice"-strategin för att få röstfunktionalitet live så snabbt som möjligt, medan vi behåller flexibiliteten att migrera till lokala lösningar senare.

### Strategi
1. **Snabb värde**: OpenAI Realtime för omedelbar röstfunktionalitet
2. **Utbytbarhet**: Adapter pattern för enkla leverantörsbyten
3. **Datadriven migration**: Shadow mode för att mäta lokala alternativ
4. **Långsiktig kontroll**: Gradvis övergång till lokala modeller

---

## 🏗️ Implementation Plan

### Phase 1: OpenAI Realtime Thin Slice (Vecka 1)
**Mål: "Prata med Alice idag"**

```typescript
// Arkitektur: Mic → VAD → ASR+TTS (OpenAI Realtime) → Agent → Playback

// Kernkomponenter
voice/
├── adapter.ts              # VoiceAdapter interface
├── config.ts               # Environment flags + config
├── factory.ts              # Provider selection factory
├── providers/
│   ├── openaiRealtime.ts   # OpenAI Realtime implementation
│   ├── whisperStub.ts      # Placeholder for lokal ASR
│   └── piperStub.ts        # Placeholder for lokal TTS
└── metrics/
    ├── latency.ts          # Performance timing
    └── logger.ts           # Metrics collection
```

**Acceptanskriterier:**
- ✅ "Hej Alice, vad är vädret?" → röstinteraktion
- ✅ e2e roundtrip ≤1200ms p50, ≤2500ms p95
- ✅ Felhantering: reconnect, mic-varningar, timeout-fallbacks
- ✅ Metrics collection för kommande optimering

### Phase 2: Adapter Contracts (Vecka 2)
**Mål: Leverantörsoberoende**

```typescript
interface VoiceAdapter {
  asr: ASRAdapter;
  tts: TTSAdapter;
  config: VoiceConfig;
}

interface ASRAdapter {
  start(options: {
    onPartial: (result: PartialResult) => void;
    onFinal: (result: FinalResult) => void;
    onError: (error: ASRError) => void;
  }): Promise<void>;
  stop(): Promise<void>;
  isListening: boolean;
}

interface TTSAdapter {
  speak(options: {
    text: string;
    voiceId?: string;
    ssml?: boolean;
    onStart: () => void;
    onChunk: (chunk: AudioChunk) => void;
    onEnd: () => void;
    onError: (error: TTSError) => void;
  }): Promise<string>; // Returns playback ID
  cancel(playbackId?: string): Promise<void>;
  isSpeaking: boolean;
}
```

### Phase 3: Shadow Mode & Measurement (Vecka 3-4)
**Mål: Datadriven migration-beslut**

```typescript
// Shadow mode configuration
const shadowConfig = {
  shadowASR: 'whisper-local',  // Kör i bakgrunden
  primaryASR: 'openai-realtime', // Används för responses
  metrics: {
    collectWER: true,           // Word Error Rate
    collectLatency: true,       // Performance comparison
    collectFallbackRate: true   // Reliability metrics
  }
};

// Daglig rapport
interface VoiceMetrics {
  date: string;
  primary: ProviderMetrics;
  shadow: ProviderMetrics;
  comparison: {
    wer_improvement: number;    // % bättre/sämre WER
    latency_delta: number;      // ms skillnad
    availability: number;       // % uptime
  };
}
```

### Phase 4: Säkerhet & Etik (Ongoing)
**Mål: Ansvarsfull AI-användning**

- 🏷️ **Transparency**: "Syntetisk röst" banners
- ✋ **Consent**: Explicit samtycke för röstkloning
- 🔒 **Privacy**: Minimal data logging, no raw audio storage
- 🔍 **Auditability**: Watermarking när tekniskt möjligt

---

## 🔌 Adapter Interface Details

### ASR Events
```typescript
interface PartialResult {
  text: string;
  confidence: number;
  timestamp_ms: number;
  is_stable: boolean;
}

interface FinalResult {
  text: string;
  confidence: number;
  start_ms: number;
  end_ms: number;
  segments?: WordSegment[];
}
```

### TTS Events  
```typescript
interface AudioChunk {
  data: Float32Array;
  sample_rate: number;
  timestamp_ms: number;
  is_final: boolean;
}

interface TTSOptions {
  text: string;
  voiceId?: 'alloy' | 'echo' | 'nova' | 'piper-sv';
  speed?: number; // 0.25-4.0
  pitch?: number; // -20 to +20
  format?: 'pcm16' | 'opus';
}
```

---

## 📊 Performance Targets

### OpenAI Realtime (Phase 1)
- **ASR Partial**: ≤200ms efter ljud-stopp
- **ASR Final**: ≤500ms efter ljud-stopp  
- **TTS TTFA**: ≤400ms (Time to First Audio)
- **E2E Roundtrip**: ≤1200ms p50, ≤2500ms p95

### Local Pipeline (Future Phase)
- **ASR Partial**: ≤160ms (faster-whisper)
- **ASR Final**: ≤300ms (faster-whisper)
- **TTS TTFA**: ≤150ms (Piper pre-warmed)
- **E2E Roundtrip**: ≤500ms p50, ≤800ms p95

---

## 🛠️ Environment Configuration

```bash
# Voice Provider Selection
VOICE_PROVIDER=openai          # openai | local | hybrid
VOICE_VAD=on                   # VAD aktivering
VOICE_LOG_METRICS=on           # Metrics collection

# OpenAI Realtime Config
OPENAI_REALTIME_MODEL=gpt-4-realtime
OPENAI_REALTIME_VOICE=alloy
OPENAI_REALTIME_MAX_TOKENS=150

# Local Pipeline Config (för framtid)
WHISPER_MODEL=tiny             # tiny | base | small
PIPER_VOICE=sv_SE-nst-medium
TTS_CHUNK_MS=60

# Shadow Mode
SHADOW_ASR_ENABLED=false       # Aktiveras i Phase 3
SHADOW_METRICS_INTERVAL=300    # 5min batching
```

---

## 🎯 Migration Strategy

### Stage 1: Pure OpenAI (Vecka 1-2)
- 100% OpenAI Realtime
- Baseline metrics collection
- UI/UX optimering

### Stage 2: Shadow Testing (Vecka 3-8)  
- Primary: OpenAI Realtime (för users)
- Shadow: Local ASR (för mätning)
- Automatic fallback-testing

### Stage 3: Hybrid Mode (Vecka 9-12)
- A/B testing mellan providers
- Gradual rollout av lokala komponenter
- Performance-based routing

### Stage 4: Local Primary (Future)
- Lokala modeller som primary
- OpenAI som fallback för komplex input
- Full kostnadskontroll

---

## 🚨 Riskhantering

### OpenAI Realtime Risks
- **Latens**: Nätverksberoende → Timeout-fallbacks
- **Kostnad**: Usage spikes → Rate limiting + alerts
- **Tillgänglighet**: API downtime → Graceful degradation

### Local Pipeline Risks  
- **CPU Load**: Model inference → Background scheduling
- **Modellkvalitet**: WER regression → Shadow validation first
- **Komplexitet**: Multiple models → Automated testing

---

## 📈 Success Metrics

### User Experience
- **Activation Rate**: % users som aktiverar röst
- **Session Length**: Genomsnittlig röstkonversation
- **Satisfaction**: User feedback på röstinteraktion

### Technical Performance  
- **Latency p95**: ≤2500ms (Phase 1), ≤800ms (Future)
- **Availability**: ≥99.5% uptime
- **Error Rate**: ≤2% failed interactions

### Business Impact
- **Cost per Interaction**: OpenAI → Local migration savings
- **Development Velocity**: Time-to-market för röstfeatures
- **Competitive Position**: Multi-modal Alice vs text-only alternatives

---

## 🎯 Next Actions

### Omedelbart (Denna vecka)
1. **Adapterkontrakt**: Skapa voice/ folder med interfaces
2. **OpenAI Integration**: Minimal working voice loop
3. **Metrics Infrastructure**: Latency tracking + KPI reports

### Kommande veckor
1. **Shadow Mode Setup**: Parallel Whisper testing  
2. **UI Integration**: Voice states i Alice frontend
3. **Production Hardening**: Error handling + fallbacks

---

*Dokument uppdaterat: 2025-08-27*  
*Status: Redo för implementation av Phase 1*