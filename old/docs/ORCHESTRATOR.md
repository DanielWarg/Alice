# 🎯 Orchestrator Module

**Central "hjärnstam" för Alice's AI-system - State Machine & Event Routing**

---

## 📋 Översikt

Orchestrator är den centrala modulen som koordinerar all kommunikation och flöden i Alice. Den fungerar som systemets "hjärnstam" och hanterar:

- **State Machine**: Per session/turn tillståndshantering
- **Event Routing**: Routar meddelanden mellan Voice, LLM, Tools, Memory
- **Privacy Gate**: Safe Summary-generering före cloud/TTS
- **Performance Metrics**: SLO-mätning (p50/p95 latency)
- **Barge-in Propagation**: Avbryter LLM/TTS/Tools inom 120ms

## 🔄 När ska Orchestrator implementeras?

### ✅ **Implementera NU om:**
- Röstkedjan (STT → LLM → TTS) fungerar stabilt
- P95 total latency ≤ 500ms på korta turer  
- Barge-in kapar < 120ms utan klick
- Ska börja med verktyg (Gmail/Calendar/Files)
- Behöver cloud-routing och auto-degrade
- Vill ha privacy-gate (Safe Summary)
- Behöver systematisk SLO-mätning

### ⏳ **Vänta om:**
- Röstkedjan fortfarande instabil
- Endast demo-chatting utan verktyg
- Grundläggande ASR/LLM/TTS-trimning inte klar

---

## 🗂️ Systemarkitektur

### Katalogstruktur
```
core/orchestrator/
├── index.ts              # Orchestrator-klass (publikt API)
├── stateMachine.ts       # Finita tillstånd + övergångar  
├── eventBus.ts          # In-process pub/sub system
├── router.ts            # Route-policy + cloud degrade
├── planner.ts           # Intent/verktygsplanering (NLU)
├── toolExecutor.ts      # MCP-klient + sandbox
├── privacy.ts           # Safe Summary + no_cloud-guard
├── metrics.ts           # NDJSON-logger + p50/p95
├── config.ts            # Konfig/feature-flags
├── types.ts             # Event-typer och payloads
├── errors.ts            # Felklasser
│
├── adapters/            # Utbytbara adaptrar
│   ├── asr/fasterWhisper.ts    # partial/final ASR-API
│   ├── llm/gptOss7b.ts         # streaming tokens  
│   ├── tts/piper.ts            # PCM stream + cancel fade
│   ├── vision/yolo.ts          # vision events (valfritt)
│   ├── memory/sqlite.ts        # episodiskt minne + vektor-sökning
│   ├── mcp/client.ts           # MCP verktygsanslutning
│   └── cloud/responses.ts      # cloud lane (valfritt)
│
└── tests/              # Självtester (DoD-krav)
    ├── selftest_latency.spec.ts
    ├── selftest_bargein.spec.ts  
    ├── selftest_privacy.spec.ts
    ├── selftest_offline.spec.ts
    └── planner_schema.spec.ts
```

## 📡 Event-modell

### Event-typer
```typescript
export type EventType =
  | "stt.partial" | "stt.final"
  | "user.barge_in" | "user.mic_open" | "user.mic_close"  
  | "llm.delta" | "llm.end"
  | "tts.begin" | "tts.chunk" | "tts.end" | "tts.active"
  | "planner.intent" | "tool.call" | "tool.done"
  | "privacy.safe_summary"
  | "vision.event"
  | "turn.begin" | "turn.end" | "turn.interrupt";

export interface OrchestratorEvent {
  id: string;            // UUID
  ts: number;            // epoch ms  
  type: EventType;
  sessionId: string;
  turnId?: string;
  payload: Record<string, any>;
  seq?: number;          // för idempotens
}
```

## 🔄 State Machine

### Turn-tillstånd
```
IDLE → LYSSNAR → TOLKAR → (ROUTER) → 
  (LOCAL_FAST → TAL) |
  (PLANNER → KÖR_VERKTYG → PRIVACY → TAL) |  
  (CLOUD_COMPLEX → PRIVACY → TAL)
→ KLAR
```

### Avbrott (Barge-in)
- **AVBRUTEN** gren från TAL-tillstånd
- Stoppar TTS/LLM/verktyg med 80-120ms fade
- Övergår direkt till LYSSNAR-tillstånd

### Regler
- Endast **Safe Summary** får gå till TAL/moln vid verktygsflöden
- Muterande verktyg kräver användarbekräftelse
- `no_cloud` payloads får aldrig lämna processen

---

## 🛣️ Routing Logic

### Route-beslut
```typescript
export function decideRoute(ctx: {
  text: string; 
  hasPII: boolean; 
  needsTools: boolean; 
  estTokens: number;
  cloudEnabled: boolean; 
  cloudDegraded: boolean;
}): "local_fast" | "local_reason" | "cloud_complex" {
  
  if (ctx.hasPII || ctx.needsTools || ctx.estTokens > 60) {
    if (ctx.cloudEnabled && !ctx.cloudDegraded) return "cloud_complex";
    return "local_reason";
  }
  return "local_fast";
}
```

### Cloud Auto-degrade
- Om `ttfa_ms_p95 > 600ms` två gånger i rad
- → Låser cloud-routing i 5 minuter
- → Fallback till `local_reason`

---

## 🔒 Privacy Gate

### Safe Summary Regler
- **≤ 300 tecken** total längd
- **Inga namn/email/ID/adresser** inkluderade  
- **Inga exakta citat** eller specifika siffror
- **Grova beskrivningar** endast (ex: "flera meddelanden" istället för "23 emails")

### No-Cloud Guard
```typescript
export function enforceNoCloud(payload: any): void {
  if (payload?.no_cloud === true && payload?.egress === "network") {
    throw new Error("no_cloud guard: blocked network egress");
  }
}
```

---

## 📊 Performance Metrics  

### NDJSON Telemetri (per turn)
```json
{
  "turn_id": "t_123",
  "route": "local_fast", 
  "first_partial_ms": 210,
  "ttft_ms": 280,
  "tts_first_chunk_ms": 120,
  "total_latency_ms": 460,
  "barge_in_cut_ms": 90,
  "tool_calls": [{"name":"email.search", "ms":430, "ok":true}],
  "privacy_leak_attempts": 0
}
```

### SLO-mål
- **P95 total latency**: ≤ 500ms
- **TTFT (Time to First Token)**: ≤ 300ms  
- **TTS first chunk**: ≤ 150ms
- **Barge-in cut**: < 120ms
- **Privacy leaks**: 0

---

## 🔧 Publikt API

```typescript
export interface Orchestrator {
  start(): Promise<void>;
  stop(): Promise<void>;

  // Röstinteraktion
  onAudioFrame(sessionId: string, frame: Float32Array | ArrayBuffer): void;
  onBargeIn(sessionId: string, playbackId?: string): void;

  // Kontrollkommandon  
  cancelTurn(sessionId: string): void;
  speak(sessionId: string, text: string): Promise<string /*playbackId*/>;

  // Event-system
  publish(event: OrchestratorEvent): void;

  // Diagnostik
  getHealth(): HealthSnapshot;
  getRecentTurns(n?: number): TurnSummary[];
}
```

---

## 🧪 Definition of Done (DoD)

### Tekniska krav
- [ ] State machine aktiv per session med deterministiska övergångar
- [ ] Barge-in stoppar LLM/TTS/verktyg inom 120ms utan klick
- [ ] Router väljer rätt lane; cloud auto-degrade fungerar  
- [ ] Planner + ToolExecutor via MCP; JSON-schema validering
- [ ] Safe Summary alltid före TTS/cloud vid verktygsflöden
- [ ] NDJSON telemetri skriv; diagnospanel visar p50/p95

### Obligatoriska självtester (grönt)
1. **Latency Test**: 50 korta fraser → p95 ≤ 500ms
2. **Barge-in Test**: 20 avbrott → cut < 120ms, inga klick  
3. **Privacy Test**: 20 PII-prompter → 0 läckor, endast safe summaries
4. **Offline Test**: Nätet av → local_fast fungerar end-to-end
5. **Schema Test**: Planner/verktyg följer JSON-schema; mutering kräver bekräftelse
6. **Degrade Test**: Cloud TTFA > 600ms × 2 → låser cloud i 5min

---

## 🚀 Implementationsordning

### Sprint 1 - Skelett & Talk-kedja (B2 början)
- [ ] EventBus, StateMachine, index.ts med bas-API
- [ ] ASR-adapter (partial/final)  
- [ ] LLM-adapter (streaming), phrase-splitter
- [ ] TTS-adapter (streaming + cancel fade)
- [ ] Grundläggande telemetri (ttft/tts_first_chunk/total)

### Sprint 2 - Router, Planner & Privacy (B2 mitt)  
- [ ] Router med cloud-degrade logik
- [ ] Planner (NLU → intent/tool) + JSON-schema
- [ ] ToolExecutor (MCP) + sandbox + rate-limits  
- [ ] Privacy-gate (Safe Summary + no_cloud-guard)
- [ ] Självtester: latency, barge-in, privacy

### Sprint 3 - Observability & Hälsa (B2 slut)
- [ ] Diagnostics-panel (p50/p95, senaste 50 turer)
- [ ] `/health` endpoint + warmup-sekvenser
- [ ] Offline-test & chaos-delays  
- [ ] Komplett dokumentation

---

## 📍 Roadmap Integration

### Nuvarande position
- **Efter B1** (Transport + Local Fast Lane stabil)
- **I början av B2** (Tool Lane & Memory) 
- **Före B2-B3** verktygsutbredning
- **Före C1-C2** (Cloud lane + MCP expansion)
- **Före C3-C4** (Vision/Persona integration)
- **Före D-fasen** (Pattern LLM/RL-light)

### Varför nu?
- Undviker "spagetti callbacks" när fler banor tillkommer
- Privacy-regler centraliserade (inte duplicerade)  
- Systematisk SLO-mätning på ett ställe
- Deterministisk barge-in för alla komponenter
- Grund för kommande cloud/vision/learning-integration

---

## ⚡ Startkriterier  

Implementera Orchestrator **när följande är uppfyllt:**

1. **Röstkedja stabil**: STT → LLM → TTS fungerar end-to-end
2. **Performance-mål**: P95 ≤ 500ms, barge-in < 120ms  
3. **Verktygsplaner**: Ska börja med MCP-verktyg (Calendar/Email/Files)
4. **Cloud-planer**: Ska aktivera Responses API eller annan cloud-lane
5. **Privacy-krav**: Behöver safe summary före TTS/cloud
6. **Mätning-behov**: Vill ha systematisk p50/p95 per tur

**Aktuell status**: Avvakta tills B1 ASR Streaming är implementerat och stabilt.

---

*Dokument uppdaterat: 2025-08-27*
*Nästa steg: Fortsätt med B1 ASR Streaming implementation*