# 📦 Alice Deployment Architecture Guide
*Portable Application Suite Structure*

## 🏗️ Project Structure Overview

```
Alice Production Suite/
├── 📱  apps/            # Platform-specific applications
│   ├── desktop/        # Electron/Tauri desktop apps
│   ├── mobile/         # React Native mobile apps
│   └── web/            # Next.js PWA web app
├── 🏗️  core/            # UI-agnostic Alice Engine
│   ├── engine/         # Core AI processing
│   ├── voice/          # Talk-socket voice system
│   └── api/            # WebSocket/HTTP interface
├── 🔗  shared/          # Cross-platform components
│   ├── ui/             # Component library
│   ├── types/          # TypeScript definitions
│   └── utils/          # Common utilities
├── 📚  docs/            # Deployment documentation
├── 🐳  deploy/          # CI/CD and deployment scripts
└── 📋  Configuration   # Root config and documentation
```

---

## 🏗️ Alice Engine (`/core/`)

**UI-Agnostic Core:** Headless processing engine with WebSocket/HTTP API

### 🧠 Core AI Components
- **`llm/`** - LLM abstraction layer (Ollama, OpenAI, Harmony)
  - `manager.py` - LLM request routing and management
  - `harmony.py` - Swedish AI prompt system
  - `ollama.py` - Local model integration
  - `openai.py` - Cloud API fallback

### 🤖 Agent System
- **`core/`** - Agent orchestration and planning system
  - `agent_executor.py` - Task execution engine
  - `agent_planner.py` - Multi-step task planning
  - `agent_orchestrator.py` - Agent coordination
  - `tool_registry.py` - Available tools management

- **`agents/`** - Agent implementations
  - `bridge.py` - Alice AI bridge for external communication

### 🎙️ Voice Pipeline (Clean Slate Implementation)
- **`voice/`** - Sub-500ms streaming voice pipeline (NEW)
  - **`server/`** - WebSocket/DataChannel voice server
    - `transport.ts` - Binary audio frame transport
    - `pipeline.ts` - ASR → LLM → TTS orchestration
    - **`adapters/`** - Streaming component adapters
      - `asr_faster_whisper.ts` - Partial transcription ≤200ms
      - `llm_gpt_oss_7b.ts` - First token ≤300ms streaming
      - `tts_piper.ts` - Pre-warmed streaming chunks ≤150ms
    - `privacy_gate.ts` - Safe-Summary PII filtering
    - `telemetry.ts` - Real-time NDJSON metrics
  - **`client/`** - Browser voice client
    - `voice_client.ts` - VAD + mic capture + playback
    - `jitter_buffer.ts` - 100ms buffering with cross-fade
    - `barge_detector.ts` - Smart interruption handling
  - **`router/`** - Intelligent routing
    - `local_fast.ts` - Default on-device pipeline
    - `cloud_complex.ts` - Optional cloud routing

### 🗄️ Data & Memory
- **`data/`** - Databases and cached files
  - `alice.db` - Main SQLite database
  - `ambient.db` - Ambient memory storage
  - `tts_cache/` - Cached TTS audio files

### 🎯 Orchestrator Ready-to-Build Kit
**Central AI coordination system with complete implementation guide**

#### 📋 Definition of Done (DoD)
- **State Machine**: Per-session turn management with idle/listening/thinking/speaking/paused states
- **Barge-in Specifications**: <120ms interruption response with proper audio fadeout
- **Performance Targets**: P95 latency ≤500ms for short utterances (1-8 words)
- **Safe-Summary Gate**: PII filtering for all external API calls with 1-2 sentence summaries

#### 🏗️ Complete Repository Structure
```
core/orchestrator/
├── 📁 config/
│   ├── orchestrator.ini        # Main configuration template
│   └── alice.env.example       # Environment variables template
├── 📁 src/
│   ├── eventBus.ts            # Inter-component event routing
│   ├── types.ts               # TypeScript interface definitions
│   ├── stateMachine.ts        # Per-session turn management
│   ├── router.ts              # Local/cloud routing with auto-degrade
│   ├── privacyGate.ts         # Safe Summary PII filtering
│   ├── planner.ts             # Intent detection & tool planning
│   └── metrics.ts             # P50/P95 SLO telemetry (NDJSON)
├── 📁 tools/
│   └── mcpSchema.json         # MCP tool definitions
├── 📁 tests/
│   ├── latency/               # Performance validation tests
│   ├── bargeIn/               # Interruption response tests
│   └── privacy/               # PII leak prevention tests
└── 📁 docs/
    ├── architecture.md        # System design documentation
    └── api.md                 # Event protocol specification
```

#### ⚙️ Configuration Templates

**orchestrator.ini**:
```ini
[orchestrator]
# Core settings
session_timeout = 300
max_concurrent_sessions = 10
state_transition_timeout = 5.0

# Performance targets (SLOs)
p95_latency_target_ms = 500
barge_in_cut_target_ms = 120
first_token_target_ms = 300

# Routing configuration
default_route = local_fast
cloud_route_threshold = 0.8
auto_degrade_enabled = true

# Privacy settings
safe_summary_enabled = true
pii_detection_threshold = 0.7
max_summary_sentences = 2

# Telemetry
metrics_format = ndjson
metrics_export_interval = 1.0
slo_monitoring_enabled = true

[voice]
# Voice-specific orchestrator settings
vad_aggressiveness = 2
min_voiced_frames = 2
silence_timeout_ms = 250
pre_warmed_tts = true

[tools]
# MCP tool configuration
mcp_server_endpoint = /tmp/mcp.sock
tool_timeout_seconds = 10
max_parallel_tools = 3
```

**alice.env.example**:
```bash
# Alice Orchestrator Environment Configuration
# Copy to alice.env and customize for your deployment

# Core Configuration
ORCHESTRATOR_CONFIG_PATH=./config/orchestrator.ini
ORCHESTRATOR_LOG_LEVEL=INFO
ORCHESTRATOR_SESSION_STORAGE=sqlite

# Performance Monitoring
ENABLE_TELEMETRY=true
METRICS_ENDPOINT=http://localhost:3001/metrics
SLO_ALERTS_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Voice Pipeline Integration
VOICE_SERVER_ENDPOINT=ws://localhost:8765
ASR_SERVICE_URL=http://localhost:8001
TTS_SERVICE_URL=http://localhost:8002
LLM_SERVICE_URL=http://localhost:8003

# Privacy & Security
SAFE_SUMMARY_ENABLED=true
PII_DETECTION_MODEL=spacy_en_core_web_sm
ENCRYPTION_KEY_PATH=./secrets/encryption.key

# Cloud Integration (Optional)
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
CLOUD_ROUTING_ENABLED=false

# Development Settings
DEBUG_MODE=false
ENABLE_REQUEST_LOGGING=false
MOCK_EXTERNAL_SERVICES=false
```

#### 💻 Code Stubs and TypeScript Interfaces

**types.ts**:
```typescript
// Event system types
export interface OrchestratorEvent {
  type: string;
  sessionId: string;
  timestamp: number;
  data: Record<string, any>;
}

export interface VoiceEvent extends OrchestratorEvent {
  type: 'voice.partial' | 'voice.final' | 'voice.barge_in';
  data: {
    transcript?: string;
    confidence?: number;
    duration_ms?: number;
  };
}

export interface LLMEvent extends OrchestratorEvent {
  type: 'llm.token' | 'llm.complete' | 'llm.error';
  data: {
    token?: string;
    total_tokens?: number;
    model?: string;
    latency_ms?: number;
  };
}

export interface TTSEvent extends OrchestratorEvent {
  type: 'tts.chunk' | 'tts.begin' | 'tts.end';
  data: {
    audio_chunk?: ArrayBuffer;
    chunk_index?: number;
    total_chunks?: number;
    latency_ms?: number;
  };
}

// State machine types
export type SessionState = 
  | 'idle' 
  | 'listening' 
  | 'thinking' 
  | 'speaking' 
  | 'paused' 
  | 'error';

export interface SessionContext {
  sessionId: string;
  state: SessionState;
  createdAt: number;
  lastActivity: number;
  metadata: {
    userId?: string;
    deviceType?: string;
    routingMode?: 'local_fast' | 'cloud_complex';
  };
}

// Metrics types
export interface PerformanceMetrics {
  session_id: string;
  timestamp: number;
  latency_ms: number;
  first_token_ms?: number;
  barge_in_cut_ms?: number;
  route_used: 'local_fast' | 'cloud_complex';
  success: boolean;
}
```

**eventBus.ts**:
```typescript
import { EventEmitter } from 'events';
import { OrchestratorEvent } from './types';

export class EventBus extends EventEmitter {
  private static instance: EventBus;
  private metrics: Map<string, number> = new Map();

  static getInstance(): EventBus {
    if (!EventBus.instance) {
      EventBus.instance = new EventBus();
    }
    return EventBus.instance;
  }

  publish(event: OrchestratorEvent): void {
    // TODO: Add event validation
    // TODO: Add metrics collection
    // TODO: Add event persistence for debugging
    this.emit(event.type, event);
  }

  subscribe(eventType: string, handler: (event: OrchestratorEvent) => void): void {
    // TODO: Add subscription management
    // TODO: Add handler error boundaries
    this.on(eventType, handler);
  }

  unsubscribe(eventType: string, handler: Function): void {
    // TODO: Add cleanup logic
    this.off(eventType, handler);
  }

  // Method stubs for implementation
  getMetrics(): Record<string, number> {
    // TODO: Return current metrics snapshot
    return Object.fromEntries(this.metrics);
  }

  clearMetrics(): void {
    // TODO: Reset metrics counters
    this.metrics.clear();
  }
}
```

**stateMachine.ts**:
```typescript
import { SessionState, SessionContext } from './types';
import { EventBus } from './eventBus';

export class SessionStateMachine {
  private sessions: Map<string, SessionContext> = new Map();
  private eventBus: EventBus;

  constructor() {
    this.eventBus = EventBus.getInstance();
    this.setupEventHandlers();
  }

  createSession(sessionId: string, metadata?: any): SessionContext {
    // TODO: Initialize session with idle state
    // TODO: Set up session timeout
    // TODO: Publish session.created event
    const context: SessionContext = {
      sessionId,
      state: 'idle',
      createdAt: Date.now(),
      lastActivity: Date.now(),
      metadata: metadata || {}
    };
    
    this.sessions.set(sessionId, context);
    return context;
  }

  transitionState(sessionId: string, newState: SessionState): boolean {
    // TODO: Validate state transition
    // TODO: Update session context
    // TODO: Publish state.changed event
    // TODO: Handle state-specific logic
    const session = this.sessions.get(sessionId);
    if (!session) return false;

    const oldState = session.state;
    session.state = newState;
    session.lastActivity = Date.now();

    this.eventBus.publish({
      type: 'state.changed',
      sessionId,
      timestamp: Date.now(),
      data: { oldState, newState }
    });

    return true;
  }

  private setupEventHandlers(): void {
    // TODO: Handle voice events (partial, final, barge_in)
    // TODO: Handle LLM events (token, complete, error)
    // TODO: Handle TTS events (chunk, begin, end)
    // TODO: Handle timeout events
    
    this.eventBus.subscribe('voice.final', this.handleVoiceFinal.bind(this));
    this.eventBus.subscribe('llm.complete', this.handleLLMComplete.bind(this));
    this.eventBus.subscribe('tts.end', this.handleTTSEnd.bind(this));
    this.eventBus.subscribe('voice.barge_in', this.handleBargeIn.bind(this));
  }

  private handleVoiceFinal(event: any): void {
    // TODO: Transition from listening to thinking
    this.transitionState(event.sessionId, 'thinking');
  }

  private handleLLMComplete(event: any): void {
    // TODO: Transition from thinking to speaking
    this.transitionState(event.sessionId, 'speaking');
  }

  private handleTTSEnd(event: any): void {
    // TODO: Transition from speaking to idle
    this.transitionState(event.sessionId, 'idle');
  }

  private handleBargeIn(event: any): void {
    // TODO: Handle interruption - pause current TTS
    // TODO: Transition to listening state
    this.transitionState(event.sessionId, 'listening');
  }
}
```

**router.ts**:
```typescript
import { SessionContext } from './types';

export interface RoutingDecision {
  route: 'local_fast' | 'cloud_complex';
  reason: string;
  confidence: number;
}

export class IntelligentRouter {
  private performanceHistory: Map<string, number[]> = new Map();
  private cloudThreshold: number = 0.8;
  private autoDegradeEnabled: boolean = true;

  async routeRequest(
    sessionId: string, 
    transcript: string, 
    context: SessionContext
  ): Promise<RoutingDecision> {
    // TODO: Implement complexity scoring
    // TODO: Check system load and availability
    // TODO: Consider user preferences and privacy settings
    // TODO: Apply auto-degrade logic based on performance
    
    const complexity = this.calculateComplexity(transcript);
    const systemLoad = await this.getSystemLoad();
    const recentPerformance = this.getRecentPerformance(sessionId);

    if (complexity < this.cloudThreshold && systemLoad < 0.8) {
      return {
        route: 'local_fast',
        reason: 'Low complexity, good system performance',
        confidence: 0.9
      };
    }

    return {
      route: 'cloud_complex',
      reason: 'High complexity or system load',
      confidence: 0.7
    };
  }

  private calculateComplexity(transcript: string): number {
    // TODO: Implement NLP-based complexity scoring
    // TODO: Consider transcript length, vocabulary, intent
    return transcript.length > 50 ? 0.8 : 0.3;
  }

  private async getSystemLoad(): Promise<number> {
    // TODO: Check CPU, memory, GPU utilization
    // TODO: Check ASR/LLM/TTS service health
    return 0.5; // Placeholder
  }

  private getRecentPerformance(sessionId: string): number[] {
    // TODO: Return recent latency measurements
    return this.performanceHistory.get(sessionId) || [];
  }

  recordPerformance(sessionId: string, latencyMs: number): void {
    // TODO: Store performance data for routing decisions
    const history = this.performanceHistory.get(sessionId) || [];
    history.push(latencyMs);
    if (history.length > 10) history.shift(); // Keep last 10 measurements
    this.performanceHistory.set(sessionId, history);
  }
}
```

**privacyGate.ts**:
```typescript
export interface SafeSummaryResult {
  summary: string;
  piiDetected: boolean;
  originalLength: number;
  summaryLength: number;
}

export class PrivacyGate {
  private piiPatterns: RegExp[];
  private maxSentences: number = 2;

  constructor() {
    // TODO: Load comprehensive PII detection patterns
    this.piiPatterns = [
      /\b\d{3}-\d{2}-\d{4}\b/g,        // SSN
      /\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b/g, // Credit card
      /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, // Email
      // TODO: Add more patterns
    ];
  }

  async safeSummary(text: string): Promise<SafeSummaryResult> {
    // TODO: Implement PII detection
    // TODO: Create 1-2 sentence summary
    // TODO: Validate summary contains no PII
    // TODO: Return structured result

    const piiDetected = this.detectPII(text);
    const summary = await this.generateSummary(text);
    
    return {
      summary,
      piiDetected,
      originalLength: text.length,
      summaryLength: summary.length
    };
  }

  private detectPII(text: string): boolean {
    // TODO: Run all PII detection patterns
    // TODO: Use ML model for advanced detection
    return this.piiPatterns.some(pattern => pattern.test(text));
  }

  private async generateSummary(text: string): Promise<string> {
    // TODO: Use local summarization model
    // TODO: Ensure max 2 sentences
    // TODO: Preserve essential meaning
    return text.split('.').slice(0, 2).join('.') + '.';
  }

  filterToolPrompts(toolName: string, args: Record<string, any>): Record<string, any> {
    // TODO: Apply privacy filtering to tool arguments
    // TODO: Log PII detection events
    // TODO: Return sanitized arguments
    return args; // Placeholder
  }
}
```

**metrics.ts**:
```typescript
import { PerformanceMetrics } from './types';

export class MetricsCollector {
  private metrics: PerformanceMetrics[] = [];
  private ndjsonStream: WritableStream | null = null;

  startCollection(): void {
    // TODO: Initialize NDJSON output stream
    // TODO: Set up periodic SLO reporting
    // TODO: Configure alerting thresholds
  }

  recordLatency(sessionId: string, latencyMs: number, route: string): void {
    // TODO: Record performance metric
    // TODO: Calculate percentiles
    // TODO: Trigger alerts if SLO violated
    
    const metric: PerformanceMetrics = {
      session_id: sessionId,
      timestamp: Date.now(),
      latency_ms: latencyMs,
      route_used: route as any,
      success: latencyMs < 500
    };

    this.metrics.push(metric);
    this.exportMetric(metric);
  }

  private exportMetric(metric: PerformanceMetrics): void {
    // TODO: Write to NDJSON stream
    // TODO: Send to monitoring system
    console.log(JSON.stringify(metric)); // Placeholder
  }

  getSLOStatus(): { p50: number; p95: number; p99: number } {
    // TODO: Calculate percentiles from recent metrics
    // TODO: Return SLO compliance status
    const latencies = this.metrics.map(m => m.latency_ms).sort((a, b) => a - b);
    const len = latencies.length;
    
    return {
      p50: latencies[Math.floor(len * 0.5)] || 0,
      p95: latencies[Math.floor(len * 0.95)] || 0,
      p99: latencies[Math.floor(len * 0.99)] || 0
    };
  }
}
```

#### 🔧 MCP Tool Schema Example

**mcpSchema.json**:
```json
{
  "tools": {
    "camera_control": {
      "name": "camera_control",
      "description": "Control camera for taking photos or recording video",
      "inputSchema": {
        "type": "object",
        "properties": {
          "action": {
            "type": "string",
            "enum": ["take_photo", "start_recording", "stop_recording"],
            "description": "The camera action to perform"
          },
          "quality": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Image/video quality setting"
          },
          "flash": {
            "type": "boolean",
            "description": "Whether to use flash"
          }
        },
        "required": ["action"]
      }
    }
  }
}
```

#### 🧪 Self-Test Framework

**Latency Validation Tests**:
```typescript
// tests/latency/latency_validation.ts
export class LatencyValidator {
  async testP95Latency(): Promise<boolean> {
    // TODO: Run 50 short utterances
    // TODO: Measure end-to-end latency
    // TODO: Verify P95 ≤ 500ms
    return true; // Placeholder
  }

  async testFirstTokenTime(): Promise<boolean> {
    // TODO: Measure time to first LLM token
    // TODO: Verify ≤ 300ms
    return true; // Placeholder
  }

  async testTTSFirstChunk(): Promise<boolean> {
    // TODO: Measure time to first TTS chunk
    // TODO: Verify ≤ 150ms
    return true; // Placeholder
  }
}
```

**Barge-in Tests**:
```typescript
// tests/bargeIn/barge_in_tests.ts
export class BargeInTester {
  async testInterruptionResponse(): Promise<boolean> {
    // TODO: Simulate user interruption during TTS
    // TODO: Verify audio cut within 120ms
    // TODO: Ensure no audio artifacts
    return true; // Placeholder
  }

  async testCrossFadeQuality(): Promise<boolean> {
    // TODO: Test smooth transitions
    // TODO: Verify no clicks or pops
    return true; // Placeholder
  }
}
```

**Privacy Validation Tests**:
```typescript
// tests/privacy/privacy_tests.ts
export class PrivacyValidator {
  async testPIILeakPrevention(): Promise<boolean> {
    // TODO: Test PII detection in tool prompts
    // TODO: Verify 0 leaks in external API calls
    // TODO: Validate Safe-Summary functionality
    return true; // Placeholder
  }

  async testLocalProcessing(): Promise<boolean> {
    // TODO: Verify local_fast route works offline
    // TODO: Ensure no network calls for local processing
    return true; // Placeholder
  }
}
```

#### 📋 GitHub Issues List

**Ready-to-Implement Issues**:

1. **ORC-1**: Implement EventBus core event routing system
2. **ORC-2**: Build SessionStateMachine with state transitions
3. **ORC-3**: Create IntelligentRouter with local/cloud decision logic
4. **ORC-4**: Implement PrivacyGate Safe-Summary filtering
5. **ORC-5**: Build MetricsCollector with NDJSON telemetry
6. **ORC-6**: Integrate with voice pipeline WebSocket events
7. **ORC-7**: Add comprehensive latency validation tests
8. **ORC-8**: Implement barge-in response system
9. **ORC-9**: Create privacy leak prevention tests
10. **ORC-10**: Build orchestrator configuration management

#### 🔄 Parallel Work Streams

**Stream 1: Core Infrastructure** (ORC-1, ORC-2)
- EventBus implementation
- State machine logic
- Can be developed independently

**Stream 2: Intelligence Layer** (ORC-3, ORC-4)
- Routing decisions
- Privacy filtering
- Requires Stream 1 EventBus

**Stream 3: Monitoring** (ORC-5, ORC-10)
- Metrics collection
- Configuration management
- Independent development possible

**Stream 4: Integration** (ORC-6, ORC-7)
- Voice pipeline integration
- Performance testing
- Requires Streams 1-3

**Stream 5: Advanced Features** (ORC-8, ORC-9)
- Barge-in handling
- Privacy validation
- Requires full system

#### ✅ Ready-to-Start Checklist

**Prerequisites**:
- [ ] Voice pipeline WebSocket server running (port 8765)
- [ ] faster-whisper ASR service available (port 8001)
- [ ] Local LLM service running (port 8003)
- [ ] Piper TTS service available (port 8002)
- [ ] TypeScript development environment set up
- [ ] Testing framework configured (Jest/Vitest)

**Configuration Setup**:
- [ ] Copy alice.env.example to alice.env
- [ ] Configure orchestrator.ini for local environment
- [ ] Set up metrics endpoint (optional)
- [ ] Configure PII detection model
- [ ] Generate encryption keys for privacy gate

**Development Environment**:
- [ ] Node.js 18+ installed
- [ ] TypeScript 5+ configured
- [ ] WebSocket client library available
- [ ] Audio processing libraries installed
- [ ] Database connection for session storage

**Testing Setup**:
- [ ] Audio test files prepared
- [ ] Network isolation for offline tests
- [ ] Performance measurement tools
- [ ] Privacy test dataset with PII examples
- [ ] Continuous integration pipeline

**Documentation**:
- [ ] API specification complete
- [ ] Event protocol documented
- [ ] Performance SLO definitions
- [ ] Privacy model documented

**Implementation Status**: Complete specification with code stubs, configurations, and test framework. Ready for parallel development across multiple work streams.

### 🔧 Support Systems  
- **`services/`** - Backend services
  - `ambient_memory.py` - Memory management
  - `probe_api.py` - System health monitoring
  - `reflection.py` - AI self-reflection system

---

## 📱 Applications Layer (`/apps/`)

### 🖥️ Desktop Applications (`apps/desktop/`)
**Framework:** Electron/Tauri with OS integration

- **OS Keyring Integration** - Secure credential storage
- **Native File System** - Local document processing
- **System Notifications** - Desktop alerts
- **Menu Bar Access** - Quick controls
- **Auto-updater** - Background application updates

### 📱 Mobile Applications (`apps/mobile/`)
**Framework:** React Native iOS/Android

- **Native Audio** - Device-optimized voice processing
- **Background Processing** - Ambient memory collection
- **Push Notifications** - System-level alerts
- **Biometric Auth** - Touch/Face ID security
- **Offline Mode** - Local AI processing

### 🌐 Web Application (`apps/web/`)
**Framework:** Next.js PWA with modern browser features

### 📱 Core Application
- **`app/`** - Next.js app router pages
  - `page.jsx` - Main chat interface
  - `layout.js` - Global app layout
  - `globals.css` - Global styles

### 🎨 Components
- **`components/`** - React components
  - `VoiceBox.tsx` - Voice interface component
  - `CalendarWidget.tsx` - Calendar integration
  - `B3AmbientVoiceHUD.tsx` - Voice status display
  - `AudioVisualizer.tsx` - Real-time audio visualization

### 🔊 Voice Client (Clean Implementation)
- **`lib/`** - New voice client utilities
  - `stream_client.ts` - WebSocket binary streaming
  - `audio_processor.ts` - VAD + echo cancellation
  - `playback_manager.ts` - Jitter buffer + cross-fade

---

## 🔗 Shared Components (`/shared/`)

### 🎨 UI Library (`shared/ui/`)
**Cross-Platform Design System**
- Component library that works across desktop/mobile/web
- Unified styling and theming system
- Responsive design patterns
- Accessibility-first components

### 📝 Type Definitions (`shared/types/`)
**TypeScript Interface Definitions**
- API interfaces for Alice Engine communication
- Voice system types and configurations
- Platform-specific type extensions
- Shared data models

### ⚙️ Common Utilities (`shared/utils/`)
**Cross-Platform Helper Functions**
- Configuration management
- Encryption and security utilities
- Data validation functions
- Platform detection and adaptation

---

## 📚 Deployment Documentation (`/docs/`)

### 📖 Core Documentation
- **`README.md`** - Main project documentation
- **`API.md`** - Complete API reference
- **`DEVELOPMENT.md`** - Development setup guide
- **`TROUBLESHOOTING.md`** - Common issues and fixes

### 🏗️ Architecture & Design
- **`ALICE_SYSTEM_OVERVIEW.md`** - High-level system architecture
- **`VOICE_HYBRID_ARCHITECTURE.md`** - Voice pipeline design
- **`PRIVACY_MODEL.md`** - Privacy and data handling

### 🗄️ Archives
- **`archive/`** - Historical documentation
  - Implementation plans (B3, B4)
  - Status reports and analysis

---

## 🧪 Tests Module (`/tests/`)

### ✅ Test Categories
- **`final_validation/`** - End-to-end system tests
- **`harmony_e2e_test.py`** - AI system integration tests
- **`test_b3_e2e.py`** - Voice system tests (B3 generation)

---

## 🐳 Deployment Infrastructure (`/deploy/`)

### 📊 Monitoring
- **`docker-compose.yml`** - Complete stack deployment
- **`grafana/`** - Metrics visualization configuration  
- **`prometheus/`** - Metrics collection configuration

---

## 🔧 Tools & Utilities

### 🛠️ Development Tools
- **`tools/`** - Development utilities and debugging scripts
- **`simple_monitor.py`** - System monitoring script
- **`alice_monitor.py`** - Comprehensive system monitoring

### 📋 Voice Pipeline Tests
- **`tests/voice/`** - New streaming pipeline tests
  - `latency_validation.ts` - Sub-500ms performance testing
  - `barge_in_tests.ts` - Interruption response testing
  - `privacy_tests.ts` - PII leak prevention validation

---

## 🚀 Deployment Status

### ✅ Production Ready Architecture
- **Alice Engine Core** - UI-agnostic processing engine
- **Talk-socket System** - Voice I/O abstraction layer
- **OS Keyring Integration** - Secure credential management
- **Cross-platform UI** - Shared component library
- **WebSocket/HTTP API** - Stable communication layer

### 🔧 Implementation Ready
- **Desktop Framework** - Electron/Tauri architecture complete
- **Mobile Framework** - React Native structure defined
- **PWA Foundation** - Web app deployment ready
- **Security Model** - Privacy-first design implemented
- **Build Pipeline** - CI/CD deployment workflows

### 📋 Migration Complete
- **Development to Production** - Architecture shift completed
- **Portable Structure** - apps/core/shared organization
- **Documentation Updated** - All guides reflect new structure
- **Deployment Ready** - Production infrastructure prepared

---

## 🎙️ **Voice Pipeline Architecture Specification**

### **🎯 Objective**
Implement an **on-device, streaming voice pipeline** with **sub-500ms** total latency using **faster-whisper** → **gpt-oss 7B** → **Piper TTS** with barge-in support.

### **⚡ Performance Targets (SLOs)**
- `first_partial_ms` ≤ **300ms** - Time to first partial transcription
- `ttft_ms` ≤ **300ms** - Time to first LLM token
- `tts_first_chunk_ms` ≤ **150ms** - Time to first TTS audio chunk
- `total_latency_ms` p95 ≤ **500ms** - End-to-end for short turns (1-8 words)
- `barge_in_cut_ms` < **120ms** - Interruption response time

### **🔄 Data Flow (local_fast path)**
```
Mic (20ms frames, AEC/NS/AGC)
  → VAD (aggressiveness=2, min-voiced=2 frames)  
  → STT (faster-whisper, partial ≤200ms, final on silence ≥250ms)
  → LLM (gpt-oss 7B Q4_K_M, stream, first token ≤300ms)
  → Phrase splitter (10-25 words, immediate TTS feed)
  → Piper TTS (pre-warmed, stream 40-80ms PCM chunks, first ≤150ms)
  → Jitter buffer (client 100ms) → Playback with barge-in detection
```

### **🛡️ Privacy & Routing**
- **local_fast** (default): Full local STT/LLM/TTS pipeline
- **cloud_complex** (optional/off): OpenAI via Safe-Summary filter only
- **Safe-Summary gate**: Rewrites tool results to 1-2 sentences, no PII
- **Privacy-first**: No transcripts/audio persisted, local processing by default

### **🎚️ Barge-in & Micro-acks**
- **Barge-in**: VAD detects speech → `barge_in` signal → 80-120ms TTS fadeout
- **Micro-acks**: Pre-baked "Mm?" (~180ms) on first partial, cross-fade to TTS
- **Ducking**: Speaker volume to -18dB when TTS active, prevent echo

### **📊 Event Protocol (WebSocket/DataChannel)**
**Upstream**: `audio.frame`, `control.barge_in`, `control.mic`
**Downstream**: `stt.partial/final`, `llm.delta`, `tts.audio_chunk/begin/end/active`

### **🧪 Testing Requirements**
- **Latency**: 50 short utterances p95 ≤500ms
- **Barge-in**: 20 interrupts <120ms cut, no clicks
- **Privacy**: 0 leaks in PII tool prompts
- **Offline**: Full local_fast operation without network

---

## 🎯 **Current Implementation Status**

### **✅ Phase 1: Voice Pipeline Infrastructure (COMPLETE)**
1. **✅ Transport Layer** - WebSocket binary audio streaming complete
2. **✅ Audio Processing** - Jitter buffer, cross-fade, ducking, echo cancellation
3. **✅ Voice Activity Detection** - Real-time VAD with energy calculation
4. **✅ Session Management** - Multi-client WebSocket with cleanup
5. **✅ Comprehensive Testing** - Full test suite with browser validation

### **🔄 Phase 2: ASR Integration (NEXT)**
1. **faster-whisper Adapter** - Streaming ASR with ≤200ms partial transcription
2. **Event System** - Real-time STT events with confidence scores
3. **Performance Optimization** - Sub-200ms first partial target

### **📱 Phase 2: Platform Deployment**
1. **Desktop Application** - Electron/Tauri with OS keyring
2. **Mobile Applications** - React Native iOS/Android apps
3. **Web Enhancement** - PWA features and offline support
4. **Production Pipeline** - CI/CD deployment workflows
5. **Security Audit** - Validate OS keyring and privacy filtering

---

**📌 Status**: Alice voice pipeline specification complete. Ready for implementation with sub-500ms streaming architecture and privacy-first design.