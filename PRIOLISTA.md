# 🔥 ALICE PRODUCTION PRIOLISTA - HÅRDHANDSKAR PÅ!

*Datum: 2025-08-28*  
*Status: Guardian 2.0 klar, nu integrerar vi ALLT*

## 🎙️ VOICE PIPELINE - NY #1 PRIORITET

### UNIVERSAL SVENSKA → ENGELSKA VOICE PIPELINE (HÖGSTA PRIO)
- [ ] **Voice Pipeline Implementation** - Se VOICE_PIPELINE_PLAN.md
  - [ ] Phase 1: Universal Voice Module Foundation (Dag 1-2)
  - [ ] Phase 2: Realtime API Integration (Dag 3-4) 
  - [ ] Phase 3: Integration Points (Dag 5-6)
  - [ ] Phase 4: Frontend Universal Voice UI (Dag 7-8)
  - [ ] Phase 5: Advanced Features (Dag 9-10)
  - [ ] Phase 6: Production Features (Dag 11-12)
  - [ ] Alla svenska input → engelsk voice output (chat, mail, calendar, etc.)
  - [ ] OpenAI Realtime API med Marin/Cedar röster
  - [ ] GPT-OSS för översättning och orchestration
  - [ ] Smart caching och fallback chain

## 🚨 KRITISKT - MÅSTE FIXAS NU (Week 2)

### ENTERPRISE VALIDATION REQUIREMENTS
- [ ] **14-dagars soak testing** med kontinuerlig svensk trafik
  - [ ] Kör minst 7-14 dygn burn-in med kontinuerlig last
  - [ ] Visa p50/p95/p99/p99.9 samt felklasser över tid
  - [ ] Verifiera CPU/RAM telemetri accuracy ("cpu_pct: 0.0" under 10+ RPS = orealistiskt)
  - [ ] Mät cache-effekt under cache-miss/cold-start scenarios
  - [ ] Dokumentera tail-latens och back-pressure-policy

- [ ] **PostgreSQL migrering** (SQLite räcker ej i produktion)
  - [ ] Schema design med migrationsplan från SQLite  
  - [ ] Connection pooling setup (pgpool/pgbouncer)
  - [ ] Point-in-time recovery (PITR) implementation
  - [ ] Backup/restore automation och testning
  - [ ] Performance benchmarking vs SQLite baseline

- [ ] **SLO/SLA definitioner** 
  - [ ] Definiera mål: tillgänglighet 99.5% månadsvis, p95≤2s, p99≤3s
  - [ ] Alert-trösklar och eskalering paths
  - [ ] On-call runbook för vanliga scenarios
  - [ ] Error budget tracking och policy

- [ ] **Enterprise observability**
  - [ ] Separera "unknown", "degraded", "hard-fail" i brownout/hysteresis
  - [ ] Queue length, tail-latens monitoring för concurrency-limit (3) vs 10+ RPS
  - [ ] Cold-start performance mätning
  - [ ] P99 ≤3s under peak load garantering

- [ ] **GDPR compliance** (kritiskt innan "Brain Worker")
  - [ ] Datakartläggning av all minneshantering
  - [ ] Data retention policies och cleanup
  - [ ] DSAR export/forget functionality  
  - [ ] Policy-taggar för private/sensitive minnen
  - [ ] Audit-loggar för dataåtkomst

## 🚨 KRITISKT - MÅSTE FIXAS NU (Week 1-2)

### A. VERKLIG LLM INTEGRATION - HÖGSTA PRIO
- [ ] **Chat API → Guardian → Ollama pipeline**
  - [ ] Integrera `old/server/llm/` moduler i current system  
  - [ ] Chat requests går genom Guardian model_wrapper.py
  - [ ] Ersätt mock responses med riktig gpt-oss:20b/7b
  - [ ] **FIX KRITISKT**: /api/chat MÅSTE peka på riktig LLM (inte mock echo)
  - [ ] Implement real chat handler med httpx → Ollama
  - [ ] Testa brownout switching under load (20b → 7b)
  - [ ] Verifiera Guardian skyddar mot hangs/crashes

- [ ] **OMEDELBAR TESTNING** efter LLM integration
  - [ ] Verifiera: `curl -X POST localhost:8000/api/chat -d '{"text":"Hej"}'` → riktig AI svar
  - [ ] Smoke test: 20 requests med baseline p95 timing
  - [ ] Guardian protection fungerar under LLM load

### B. AGENT SYSTEM INTEGRATION  
- [ ] **Koppla core agent system till chat API**  
  - [ ] Flytta `old/archive/pre_fas2_cleanup_20250827/server/core/` → current `server/core/`
  - [ ] Integrera agent_orchestrator.py i chat endpoint
  - [ ] Verifiera tool_registry.py med calendar/weather/etc tools
  - [ ] Testa agent chains med Guardian protection
  - [ ] Validera Swedish prompts & responses

### C. DATABASE PERSISTENCE
- [ ] **SQLite integration från old/server/**
  - [ ] Kopiera database.py + migrations från old/
  - [ ] Chat history persistence 
  - [ ] User sessions & preferences
  - [ ] Guardian metrics storage för trending
  - [ ] Testa backup/restore funktioner

## 🛡️ SYSTEMVAKTER & PRODUCTION SAFETY (Week 2)  

### D. SYSTEM MONITORING UTÖKNING
- [ ] **Disk sentinel implementation**
  - [ ] Monitor disk space < 2GB → degrade mode
  - [ ] Log rotation enforcement 
  - [ ] Cleanup old chat history/logs automatically
  
- [ ] **Resource monitoring expansion**  
  - [ ] GPU/VRAM monitoring (om GPU finns)
  - [ ] OOM detection via dmesg
  - [ ] Process ulimits configuration
  - [ ] Temperature monitoring (macOS sensors)

### E. RATE LIMITING & BACKPRESSURE
- [ ] **Implement production rate limiting**
  - [ ] Token bucket per IP/user (6 req/10s)
  - [ ] Queue length limits i Guardian wrapper  
  - [ ] 429 responses när kö > N
  - [ ] Redis/memcached för distributed rate limiting

### F. ERROR RECOVERY & RESILIENCE  
- [ ] **Robust error handling**
  - [ ] Graceful degradation för alla components
  - [ ] Auto-restart failed services
  - [ ] Circuit breakers för external APIs
  - [ ] Fallback chains (Ollama → OpenAI → offline mode)

## 📊 OBSERVABILITY & OPERATIONS (Week 3)

### G. COMPREHENSIVE TESTING - LIVE PRODUCTION TESTS
- [ ] **Live Load Testing Med k6**  
  - [ ] `k6_e2e_live.js` - HTTP lasttest mot /api/chat med riktig AI
  - [ ] Ramping load: 1→3→6→10→2 rps över 6min
  - [ ] Thresholds: <1% fel, p95 <2.5s
  - [ ] Guardian mode tracking via x-guardian-mode headers
  
- [ ] **Soak Testing (15min kontinuerlig)**
  - [ ] `k6_soak_brownout.js` - Konstant 2 rps i 15min  
  - [ ] Manual brownout trigger under körning
  - [ ] Verifiera p95 <1.4s i brownout mode (7b)
  - [ ] Långtidsstabilitet utan minnesläckor

- [ ] **Chaos Engineering - Killswitch Testing**
  - [ ] `chaos_killswitch.sh` - Trigger verklig killswitch under load
  - [ ] Auto-recovery within 20s till mode=ok
  - [ ] k6 visar spike + recovery pattern
  - [ ] Guardian logs visar kill→restart sequence

- [ ] **NDJSON Log Analytics**
  - [ ] `metrics_parse.py` - Parse logs för p50/p95 trends  
  - [ ] Korrelation mellan Guardian mode och response times
  - [ ] TTFA metrics från voice pipeline om aktivt
  - [ ] Mode distribution histogram (ok/degrade/stop)

- [ ] **Production Acceptance Criteria**
  - [ ] **Chat API**: p95 <2.5s @ 6rps (gpt-oss:20b), <1% fel
  - [ ] **Brownout Mode**: p95 <1.4s (gpt-oss:7b), ~0% fel  
  - [ ] **Killswitch Recovery**: <20s till green mode=ok
  - [ ] **Voice TTFA**: p95 <300ms (om voice aktiv)
  - [ ] **15min Soak**: Stabil utan degradation eller crashes

### H. CHAOS ENGINEERING  
- [ ] **Automated system testing**
  - [ ] Weekly brownout drill automation
  - [ ] Memory pressure simulation  
  - [ ] Network failure simulation
  - [ ] Database corruption recovery
  - [ ] Incident artifacts collection

### I. MONITORING & ALERTING
- [ ] **Production monitoring stack**  
  - [ ] Prometheus metrics collection
  - [ ] Grafana dashboards för Guardian metrics
  - [ ] Slack/email alerts för system degradation
  - [ ] PagerDuty integration för critical failures

## 🔧 PRODUCTION POLISH (Week 4)

### J. CONFIGURATION & DEPLOYMENT
- [ ] **Environment management**
  - [ ] Production .env template 
  - [ ] Configuration validation on boot
  - [ ] Feature flags system
  - [ ] Blue/green deployment support

### K. DOCUMENTATION & RUNBOOKS
- [ ] **Operations documentation**  
  - [ ] Complete runbook.md "Om X → Gör Y"
  - [ ] Deployment guide för production  
  - [ ] Troubleshooting guide
  - [ ] API documentation updates

### L. PERFORMANCE OPTIMIZATION
- [ ] **System tuning**
  - [ ] Guardian correlation analysis implementation
  - [ ] Auto-tuning baserat på faktisk usage
  - [ ] Caching layer för frequent requests
  - [ ] Database query optimization

## 🧪 LIVE TESTING IMPLEMENTATION - READY TO RUN NOW

### IMMEDIATE TEST SETUP (Day 1 efter LLM integration)
- [ ] **Skapa test-scripts i repo root**
  - [ ] `k6_e2e_live.js` - Ramping load test med guardian mode tracking
  - [ ] `k6_soak_brownout.js` - 15min kontinuerlig belastning  
  - [ ] `chaos_killswitch.sh` - Automated killswitch + recovery test
  - [ ] `metrics_parse.py` - NDJSON log analysis för p50/p95
  
- [ ] **Förutsättnings-check script**
  ```bash
  # check_prerequisites.sh
  curl -s http://localhost:8787/status  # Guardian OK
  curl -s http://localhost:8000/health  # FastAPI OK  
  curl -s http://localhost:8000/api/chat -X POST -d '{"text":"test"}' # Real LLM (inte mock)
  ```

- [ ] **ENTERPRISE Production test pipeline**
  - [ ] 20 single requests för baseline
  - [ ] k6 ramp test (6min) → UTÖKA till 14-dagars kontinuerlig
  - [ ] 15min soak test → UTÖKA till multi-day burn-in
  - [ ] Brownout trigger mitt i soak
  - [ ] Chaos killswitch med recovery  
  - [ ] Log analysis med tydliga pass/fail kriterier
  - [ ] **NYTT**: Cold-start latency benchmarks
  - [ ] **NYTT**: Cache-miss scenario testing  
  - [ ] **NYTT**: PostgreSQL failover/recovery drills

## 🎯 INTEGRATION PRIORITIES - ANVÄNDA OLD/ MATERIEL

### DIREKT KOPIERING FRÅN OLD/
1. **LLM System**: `old/server/llm/` → `server/llm/` ✅ (redan kopierat, behöver integreras)
2. **Agent Core**: `old/archive/pre_fas2_cleanup_20250827/server/core/` → `server/core/`
3. **Database**: `old/server/database.py` → `server/database.py`  
4. **Tools Registry**: `old/archive/pre_fas2_cleanup_20250827/server/core/tool_registry.py`
5. **Calendar Integration**: `old/server/core/calendar_service.py`
6. **Gmail Integration**: `old/server/core/gmail_service.py`

### TESTNING FRÅN OLD/
- [ ] Använd `old/server/tests/` som referens för production test suite
- [ ] Implementera `old/tests/final_validation/` scenarios  
- [ ] Återanvänd `old/server/test_*.py` för integration testing

## ✅ DAILY VERIFICATION CHECKLIST

### Dag 1-7: Core Integration  
- [ ] Chat ger riktiga AI-svar (inte mock)
- [ ] Guardian skyddar mot gpt-oss hangs
- [ ] Agent tools funkar (weather, calendar, etc)  
- [ ] Database sparar chat history
- [ ] Brownout switching funkar under load

### Dag 8-14: System Resilience
- [ ] Disk monitoring & cleanup fungerar
- [ ] Rate limiting blockerar overload
- [ ] Error recovery utan user impact
- [ ] All logging structured & searchable

### Dag 15-21: Production Readiness  
- [ ] Full test suite passes
- [ ] Chaos tests validate resilience
- [ ] Monitoring/alerting operational  
- [ ] Performance optimizations active

### Dag 22-28: Operations Excellence
- [ ] Deployment automation complete
- [ ] Documentation comprehensive
- [ ] Team kan operera systemet i prod
- [ ] Metrics guide tuning decisions

---

## 🎪 EXECUTION STRATEGY

**Week 1**: Få det att fungera med riktig AI  
**Week 2**: Få det att överleva i production  
**Week 3**: Få det att rapportera vad som händer  
**Week 4**: Få det att förbättra sig självt  

**Mål**: Efter 4 veckor har vi Alice som kör 24/7 med Guardian-skydd, riktig AI, full observability och kan hantera alla produktions-scenarios.

**ENTERPRISE Success Metrics**:
- ✅ 99.5% månadsvis tillgänglighet (ej endast 7 dagar)
- ✅ p95≤2s, p99≤3s medianrespons med Guardian aktiv  
- ✅ 14-dagars burn-in utan degradation
- ✅ PostgreSQL PITR verified genom disaster recovery drill
- ✅ GDPR compliance audit pass
- ✅ Automatisk recovery från alla testade failures
- ✅ Noll manuella interventioner under normal drift
- ✅ CPU/RAM telemetri accuracy under realistisk belastning

---
*HÅRDHANDSKAR PÅ - VI GÖR DETTA! 💪*