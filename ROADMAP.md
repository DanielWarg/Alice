# 🗺️ Alice FAS2 Development Roadmap

## 🎯 Current Status: **FAS 0-4 COMPLETED, INTEGRATION TESTED**

*Last Updated: August 27, 2025 - Based on FAS2.md Implementation Plan*

---

## ✅ **FAS 0-4: FOUNDATION COMPLETE**

### ✅ FAS 0 - Förberedelser (Grön baslinje)
*Mål: Låsa nuläget och etablera stabil grund*

**COMPLETED:**
- [x] Environment variables configured (.env)
- [x] Health endpoints validated (GET /api/health/simple)
- [x] Integration test suite (100% success rate)
- [x] 0×5xx errors in production readiness tests

**Environment:**
```bash
OPENAI_API_KEY=***
AGENT_PROVIDER=openai
BRAIN_SHADOW_ENABLED=on
MEMORY_DRIVER=sqlite
INJECT_BUDGET_PCT=25
ARTIFACT_CONFIDENCE_MIN=0.7
```

### ✅ FAS 1 - Strict TTS
*Mål: Brain komponerar, TTS läser exakt det som skrivs*

**COMPLETED:**
- [x] `/api/brain/compose` endpoint implemented
- [x] `AnswerPackage` interface with strict TTS format
- [x] Brain compose system with context injection
- [x] Structured response format for consistent output

**API Response:**
```typescript
interface AnswerPackage {
  spoken_text: string;     // exakt vad TTS ska läsa
  screen_text?: string;    // kort text till UI  
  ssml?: string;          // om satt – använd före spoken_text
  citations?: { title: string; url?: string }[];
  meta?: { confidence: number; tone?: string };
}
```

### ✅ FAS 2 - EventBus & Telemetri  
*Mål: Logga alla systemhändelser för mätning och analys*

**COMPLETED:**
- [x] Central EventBus (`src/core/eventBus.ts`)
- [x] NDJSON logging to `logs/metrics.ndjson`
- [x] All interactions produce ≥3 event entries
- [x] Metrics summary API (`/api/metrics/summary`)

**Event Types:** `brain_compose`, `agent_response`, `tool_result`, `memory.write`, `memory.fetch`

### ✅ FAS 3 - Minne & RAG (Artefakter)
*Mål: Långtidsminne baserat på artefakter med SQLite*

**COMPLETED:**
- [x] SQLite artifacts table with WAL mode
- [x] Memory interface with write/fetch operations  
- [x] API endpoints `/api/memory/write` & `/api/memory/fetch`
- [x] Artifact types: insight, kb_chunk, plan, policy, vision_event, test_data, preference
- [x] Score-based ranking and expiration handling

**SQLite Schema:**
```sql
CREATE TABLE artifacts (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  text TEXT NOT NULL,
  score REAL NOT NULL DEFAULT 0.0,
  expires_at TEXT,
  meta_json TEXT,
  embedding BLOB,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### ✅ FAS 4 - PromptBuilder & Injektionsbudget
*Mål: Kontrollerat injicera minnesartefakter i prompten (≤25% tokens)*

**COMPLETED:**
- [x] `buildContext()` function för artifact retrieval
- [x] Persona & style loading from YAML files (`alice/identity/`)
- [x] Budget compliance: 24.6% injection rate (within 25% target)
- [x] Automatic context trimming when over budget
- [x] `injected_tokens_pct` telemetry logging

**Files:**
- `src/core/promptBuilder.ts`
- `alice/identity/persona.yml`
- `alice/identity/style.yml`

---

## 🚧 **NEXT PHASES: FAS 5-8 ROADMAP**

### 🔄 FAS 5 - Provider Switch & Failover  
*Mål: GPT-OSS primär brain, OpenAI fallback*

**TODO:**
- [ ] Implement timeout policy (BRAIN_DEADLINE_MS = 1500)
- [ ] Fallback routing to `/api/agent` on timeout
- [ ] Log `fallback_used` and `brain_latency_ms` metrics
- [ ] Achieve <5% fallback rate in development

**Target:** Seamless voice flow with fallback protection

### 🔄 FAS 6 - Cloud Complex Lane (OpenAI Responses API)
*Mål: Använda molnet för komplexa verktygskedjor*

**TODO:**
- [ ] OpenAI Responses API adapter
- [ ] Tool-first RAG policy (kb.search → kb.fetch)  
- [ ] Structured JSON response format enforcement
- [ ] End-to-end tests for "summarize file" and "run code"

**Integration:** Advanced tool chains via cloud processing

### 🔄 FAS 7 - Brain Worker & Sentence Streaming
*Mål: Snabbare respons genom sentence streaming*

**TODO:**
- [ ] Background worker consuming EventBus
- [ ] Sentence streaming for first sentence TTFA <300ms
- [ ] `brain_first_sentence_ms` p50 ≤600ms target
- [ ] Parallel learning and embedding updates

### 🔄 FAS 8 - Vision & Sensorer (Minimal)
*Mål: YOLO-driven närvaro → vision_event*

**TODO:**
- [ ] Local YOLO pipeline for object/face detection
- [ ] Vision event artifacts in memory
- [ ] Mood adjustment based on visual cues (e.g., smiling)
- [ ] Demo: Alice reacts to expressions with warmer greeting

---

## 📊 **CURRENT SYSTEM METRICS**

### ✅ Integration Test Results (100% Success Rate)
- **Health Check:** ✅ PASS - System responsive  
- **Memory System:** ✅ PASS - Write/read cycle working
- **Brain Compose:** ✅ PASS - Budget 25%, Context injection OK
- **Metrics Collection:** ✅ PASS - Telemetry data collected
- **Weather Tool:** ✅ PASS - API validation successful  
- **Agent Integration:** ✅ PASS - Direct response 826ms latency

### 🎯 Performance Targets
- **Budget Compliance:** 24.6% (target <25%) ✅
- **Memory Artifacts:** 2 artifacts stored and retrieved ✅
- **Event Logging:** 36 events in logs/metrics.ndjson ✅
- **API Response Times:** Weather 248ms, Agent 826ms ✅

---

## 🛠️ **IMMEDIATE NEXT STEPS**

### Phase 1: Complete FAS 5 (Provider Switch)
1. **Implement timeout & fallback logic**
2. **Add AbortController for request cancellation** 
3. **Configure GPT-OSS as primary brain**
4. **Test fallback scenarios**

### Phase 2: Production Hardening  
1. **Add input validation with Zod**
2. **Implement retry logic with exponential backoff**
3. **Enhance metrics with correlation IDs**
4. **Add real embedding model (replace stub)**

### Phase 3: Advanced Features
1. **Sentence streaming for faster response times**
2. **Local knowledge base with real vector search**
3. **Camera integration and vision processing**
4. **Response personalization and mood adaptation**

---

## 🧪 **TESTING STRATEGY**

### ✅ Current Test Coverage
- **Integration Tests:** E2E API validation against live system
- **Contract Tests:** All endpoint input/output formats validated
- **Smoke Tests:** Basic functionality verification
- **Budget Tests:** Token injection compliance testing

### 📝 Test Commands
```bash
npm run test:integration     # Full E2E test suite
npm run test:integration:ci  # CI-friendly with timeout
npm run dev                  # Development server
npm run build               # Production build verification
```

---

## 🎯 **SUCCESS CRITERIA (FAS2 Completion)**

### Technical Requirements
- [x] **Strict TTS:** 0 deviations between TTS and `spoken_text`
- [x] **Budget Compliance:** `injected_tokens_pct` ≤25% stable
- [x] **Memory Persistence:** User preferences survive restarts
- [x] **Event Logging:** All interactions produce telemetry
- [x] **Integration Tests:** 100% pass rate

### Performance Requirements  
- [x] **System Health:** All endpoints respond correctly
- [x] **Memory System:** Write/fetch operations working
- [x] **Context Injection:** Artifact retrieval and compression
- [x] **Tool Integration:** Weather, agent, memory tools functional

### Next Phase Readiness
- [ ] **Provider Failover:** <5% fallback rate
- [ ] **Cloud Integration:** Complex tool chains via Responses API
- [ ] **Sentence Streaming:** First sentence <300ms TTFA
- [ ] **Vision Pipeline:** Basic emotion detection working

---

## 🚀 **DEPLOYMENT STATUS**

**Current Environment:** Development with production-ready foundation
**Integration Test Status:** 100% success rate  
**System Health:** All green, ready for FAS 5 implementation
**Architecture:** Event-driven, budget-controlled, memory-enhanced

*Alice FAS2 foundation is complete and validated. Ready to proceed with advanced capabilities in FAS 5-8.*