# 🚀 Alice – Uppdaterad Roadmap (Aug 2025)

## 📋 **Phase 1 — AI Core Completion** ⚡

✅ Hybrid LLM (Ollama gpt-oss:20B + OpenAI fallback)
✅ Harmony prompt-system i svenska kanaler
✅ Circuit breaker & health monitoring
✅ FAST/DEEP routing (intent-based)
✅ Tool execution med interleaved feedback
✅ Ambient Memory (B1) – production ready
✅ Barge-in & Echo-skydd (B2) – production ready
✅ Kodbas-organisering & dokumentation cleanup
⬜ Acceptance tests ≥95%
⬜ ARCHITECTURE.md + Runbook för nya verktyg
⬜ Memory API endpoints

---

## 📋 **Phase 2 — Supersmart Features** 🎯

### **B3 – Always-On Voice + Ambient Summaries**

- [ ] Bygg *permanent lyssningsläge* med real-time transkribering
- [ ] Ringbuffer (10–15 min) → autosammanfattning → långminne
- [ ] Brusfiltrering + importance scoring (klar från B1)
- [ ] UI/HUD: "Live / Mute" toggle + badge för voice source

**DoD:**
- [ ] Alice lyssnar kontinuerligt
- [ ] Irrelevant transkript kasseras, summaries sparas i vektor-minne
- [ ] Kan spontant kommentera baserat på ambient minne

---

### **Calendar Master (spår A)**

- [ ] Google Calendar API-integration
- [ ] Intelligent scheduling + conflict resolution
- [ ] Meeting prep automation
- [ ] Natural svenska voice commands

### **Email Intelligence (spår A)**

- [ ] Smart kategorisering
- [ ] Sentimentanalys
- [ ] Tråd-summering

### **Predictive Engine (spår A)**

- [ ] Pattern recognition på ambient summaries
- [ ] Proaktiva frågor ("Vill du automatisera det här?")

---

### **Production Polish (spår B)**

- [ ] Dependencies & SBOM scanning (supply chain security)
- [ ] OAuth flows + rate limiting + graceful degradation
- [ ] Performance soak tests & budgets
- [ ] Docker packaging + desktop distribution
- [ ] Demo mode & onboarding

---

## 📋 **Phase 3 — Advanced Intelligence** 🚀

### **Vision & Multimodal (B5)**

- [ ] Pi 3 som audio/video-satellit
- [ ] YOLOv8 på Pi/extern pipeline → tool för Alice
- [ ] Interleaved reasoning mellan speech+vision

### **Predictive Proactive Agent (B6)**

- [ ] Proaktiv schemaläggning baserat på mönster
- [ ] Automation-förslag ("ska jag lägga detta i Home Assistant?")

### **Workflow Automation**

- [ ] If-this-then-that builder
- [ ] Multi-tool orchestration

---

## 📋 **Phase 4 — Optimization & Scale** 📈

- [ ] Sub-300ms partial latency (voice path)
- [ ] Sub-100ms TTS-start (med caching)
- [ ] Failover PROBE→Laptop ≤1s
- [ ] Observability: metrics + E2E loop tests
- [ ] Multi-user & GDPR compliance
- [ ] Plugin-arkitektur

---

### 🎯 Justeringar mot tidigare plan:

1. **B1 och B2 är redan production ready** → flyttas upp som ✓ i Phase 1.
2. **B3 Always-On Voice/Memory Summaries** läggs in som nytt första fokus i Phase 2.
3. **Predictive Engine** blir två steg: pattern recognition (A) → proaktiv agent (B6).
4. **Vision/YOLO** flyttas till Phase 3 för att bygga ovanpå B3.
5. **Production Polish** måste köras parallellt för att undvika teknisk skuld.

---

👉 **Roadmap framåt**:

* **Nu**: Slutför production polish (spår B) och bygg B3 Always-On Voice.
* **Kortsiktigt**: Calendar/Email integration (spår A).
* **Mellan**: Predictive Engine + YOLO-satellit.
* **Långsiktigt**: Full multimodal + proaktiv agent.