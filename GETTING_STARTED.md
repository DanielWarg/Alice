# 🚀 Getting Started with Alice FAS2

*A step-by-step guide for new AI assistants to start working on the Alice project*

## 🎯 What is Alice FAS2?

Alice is an AI assistant with **FAS2 architecture** - a modular, event-driven system with:
- **Brain Compose API** - Structured response generation  
- **Memory System** - SQLite-based long-term memory with artifacts
- **Event Bus** - Complete telemetry and metrics collection
- **Integration Tests** - 100% validation of all endpoints

**Current Status:** FAS 0-4 Complete, Ready for FAS 5 (Provider Switch & Failover)

---

## ⚡ Quick Start (5 minutes)

### 1. Prerequisites Check
```bash
# Required tools
node --version    # Should be 18+
npm --version     # Should be 8+
git --version     # Any recent version

# Clone the project
git clone [repository-url]
cd Alice/web
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env.local

# Add your OpenAI API key
echo "OPENAI_API_KEY=your-key-here" >> .env.local
echo "MEMORY_DRIVER=sqlite" >> .env.local
echo "INJECT_BUDGET_PCT=25" >> .env.local
```

### 3. Install & Start
```bash
# Install dependencies
npm install

# Start the development server
npm run dev

# Test the system (in another terminal)
npm run test:integration
```

### 4. Verify System
```bash
# Open browser to:
# http://localhost:3000 - Main interface
# http://localhost:3000/test_fas_system.html - Test suite
```

**Expected Result:** All integration tests pass (100% success rate)

---

## 📊 System Architecture (FAS2)

### Core Components
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Brain API     │    │   Memory System  │    │   Event Bus     │
│ /api/brain/*    │────│  /api/memory/*   │────│   Telemetry     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         └────────────────────────┼───────────────────────┘
                                  │
                         ┌─────────────────┐
                         │ Integration     │
                         │ Test Suite      │
                         └─────────────────┘
```

### Key Endpoints
- **`/api/brain/compose`** - Main brain endpoint (FAS 1)
- **`/api/memory/write`** - Store artifacts (FAS 3)  
- **`/api/memory/fetch`** - Retrieve memories (FAS 3)
- **`/api/metrics/summary`** - System telemetry (FAS 2)
- **`/api/health/simple`** - System health (FAS 0)

---

## 🧪 Understanding the Test Suite

### Integration Tests (`npm run test:integration`)
The **most important validation** - tests real system behavior:

```javascript
// Tests actual endpoints against live system
✅ Health Check: System responsive
✅ Memory System: Write/read cycle working  
✅ Brain Compose: Budget 25%, Context injection OK
✅ Metrics Collection: Telemetry data collected
✅ Weather Tool: API validation successful
✅ Agent Integration: Direct response working
```

**Why This Matters:** Mock tests lie, integration tests tell the truth.

### Manual Testing via Browser
- **`http://localhost:3000/test_fas_system.html`** - Interactive test interface
- Test each FAS component individually
- Verify budget compliance in real-time
- Monitor metrics and memory operations

---

## 🗂️ Project Structure (Key Files)

### Core Implementation (FAS 0-4)
```
web/
├── src/                          # FAS2 Core Implementation
│   ├── brain/compose.ts         # FAS 1: Brain composition
│   ├── core/
│   │   ├── eventBus.ts          # FAS 2: Event system  
│   │   ├── metrics.ts           # FAS 2: NDJSON logging
│   │   └── promptBuilder.ts     # FAS 4: Context injection
│   ├── memory/                  # FAS 3: Memory system
│   │   ├── sqlite.ts           # SQLite driver
│   │   ├── types.ts            # Memory interfaces  
│   │   └── index.ts            # Memory factory
│   └── types/
│       ├── answer.ts           # AnswerPackage interface
│       └── events.ts           # Event type definitions
```

### API Routes
```
app/api/
├── brain/compose/route.ts       # FAS 1: Main brain endpoint
├── memory/
│   ├── write/route.ts          # FAS 3: Store artifacts
│   └── fetch/route.ts          # FAS 3: Retrieve artifacts  
├── metrics/summary/route.ts     # FAS 2: Telemetry summary
└── health/simple/route.ts       # FAS 0: System health
```

### Configuration
```
alice/identity/
├── persona.yml                  # Alice personality config
└── style.yml                   # Response style config

logs/
└── metrics.ndjson              # FAS 2: Event telemetry

data/
└── alice.db                    # FAS 3: SQLite memory store
```

---

## 🛠️ Development Workflow

### 1. Understanding Current State
```bash
# Check what's implemented
npm run test:integration         # Validate all systems

# Review current metrics  
curl http://localhost:3000/api/metrics/summary | jq

# Check memory system
curl -X POST http://localhost:3000/api/memory/fetch \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","k":5}' | jq
```

### 2. Making Changes
```bash
# Before changes: Run tests
npm run test:integration

# Make your changes to files in src/ or app/api/

# After changes: Validate
npm run test:integration         # Must pass 100%
npm run build                   # Must compile cleanly
```

### 3. Adding New Features
- **Follow FAS pattern:** Each feature is a "FAS phase"
- **Add integration tests:** Real endpoint validation
- **Update telemetry:** Event logging for monitoring  
- **Document in ROADMAP.md:** Track progress

---

## 📚 Key Documentation

### For Development
- **`ROADMAP.md`** - FAS implementation status and next steps
- **`FAS2.md`** - Complete technical specification (original plan)
- **`tests/integration.test.js`** - How integration testing works

### For Architecture
- **`src/core/eventBus.ts`** - How event system works
- **`src/memory/sqlite.ts`** - How memory persistence works  
- **`src/core/promptBuilder.ts`** - How context injection works

### For API Usage  
- **`test_fas_system.html`** - Interactive API testing
- **`logs/metrics.ndjson`** - System telemetry format

---

## ❓ Common Questions

### "How do I test my changes?"
```bash
# Always use integration tests - they test real system
npm run test:integration

# For specific components, use the browser test interface:
# http://localhost:3000/test_fas_system.html
```

### "Where do I add new API endpoints?"
```bash
# Add to app/api/ following existing pattern:
app/api/your-feature/route.ts

# Add integration test in tests/integration.test.js
# Update telemetry in src/core/eventBus.ts
```

### "How does the memory system work?"
```bash
# Write artifact:
curl -X POST /api/memory/write -d '{
  "user_id":"test","kind":"insight","text":"Alice prefers concise answers","score":0.9
}'

# Fetch artifacts:  
curl -X POST /api/memory/fetch -d '{"user_id":"test","k":5}'
```

### "What's next in development?"
Check **`ROADMAP.md`** - Next up is **FAS 5: Provider Switch & Failover**

---

## 🚨 Important Notes

### Never Skip Integration Tests
- **Mock tests lie, integration tests tell truth**
- Always run `npm run test:integration` after changes
- 100% pass rate required for deployment readiness

### Environment Variables Matter
```bash
# Required in .env.local:
OPENAI_API_KEY=your-key-here     # For agent functionality
MEMORY_DRIVER=sqlite             # Use SQLite memory
INJECT_BUDGET_PCT=25             # Context budget limit
ARTIFACT_CONFIDENCE_MIN=0.7      # Memory filtering
```

### Budget Compliance is Critical
- **Target:** <25% token injection rate
- **Current:** 24.6% (compliant) 
- **Monitor:** Check /api/metrics/summary

---

## 🎯 Success Checklist

### Before You Start Coding
- [ ] Integration tests pass 100%
- [ ] Understand FAS 0-4 architecture  
- [ ] Know how to use test_fas_system.html
- [ ] Read ROADMAP.md for context

### Before You Submit Changes
- [ ] Integration tests still pass 100%
- [ ] `npm run build` compiles cleanly
- [ ] New features have integration tests
- [ ] Telemetry events added for monitoring

### Understanding System Health
- [ ] Can explain what each FAS phase does
- [ ] Know where to check system metrics
- [ ] Understand memory artifact system
- [ ] Can debug using event logs

---

**🚀 Ready to contribute to Alice FAS2!**

*For specific implementation questions, check the relevant source files or run the integration test suite to see expected behavior.*