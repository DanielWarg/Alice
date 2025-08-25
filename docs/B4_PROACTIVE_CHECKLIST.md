# B4 Proaktivitet - Alice som Intelligent Agent

## 🎯 Vision: Alice blir Proaktiv

**Mål:** Alice observerar ambient conversations och föreslår relevanta actions automatiskt, utan att vara påträngande.

**Kärnprincip:** *Observera → Mönster → Föreslå → Lär*

## 🚀 B4 Features Implementation

### Proaktiva Triggers på Ambient Summaries
- [ ] **Pattern detection:** "lampan nämns 3 gånger/vecka kl 06:30" → föreslå automation
- [ ] **Routine recognition:** "kaffe varje dag 07:15" → erbjud smart coffee maker integration  
- [ ] **Context awareness:** "stressat innan möten" → föreslå 5min meditation timer
- [ ] **Location triggers:** "hemma efter 18:00 + tysthet" → föreslå dagens sammanfattning

### Fast-Path HA-Tools på Partials
- [ ] **Quick commands:** "tänd lampan" → direkt HA-action utan LLM reasoning
- [ ] **Regex routing:** `/^(tänd|släck|dimma) (.+)/` → bypass LLM för ljuskommandon
- [ ] **Device shortcuts:** "spotify" → direkt musik utan tool selection step
- [ ] **Emergency fast-path:** "alarmkod", "ring ambulans" → prioriterade actions

### Contextual Prompts för Spontana Micro-Svar
- [ ] **Ambient context injection:** Senaste ambient_summary in LLM coordinator prompt
- [ ] **Smart interruptions:** Erbjud hjälp vid "hmm" eller "vad hette det där"
- [ ] **Micro-questions:** "vill du att jag kollar väder?" istället för långa monologer
- [ ] **Learning feedback:** "var det hjälpsamt?" efter proaktiva förslag

### Safety & Do-Not-Disturb
- [ ] **Tysta timmar:** 22:00-08:00 enbart emergency-triggers
- [ ] **DND mode:** Manual eller automatisk (calendar integration)
- [ ] **Sensitivity levels:** Låg/Medium/Hög proaktivitet per user preference
- [ ] **Context filtering:** Aldrig proaktiv under telefonsamtal eller focused work

## 📊 Intelligent Observation System

### Ambient Data Collection
- [ ] **Conversation summaries:** Dagliga/veckovisa mönster från transcripts
- [ ] **Activity correlation:** Koppla röstkommandon till tid/rum/väder
- [ ] **Tool usage patterns:** Vilka verktyg används när och varför
- [ ] **Success/failure tracking:** Lär från accepterade vs avvisade förslag

### Pattern Recognition Engine
- [ ] **Temporal patterns:** Rutiner baserade på tid/dag/månad
- [ ] **Keyword clustering:** Relaterade topics som diskuteras tillsammans  
- [ ] **Sentiment analysis:** Stress, glädje, frustration → olika förslag
- [ ] **Anomaly detection:** Avvikelser från vanliga mönster → checkup förslag

### Learning & Adaptation
- [ ] **Feedback loop:** Track accept/dismiss rate för varje trigger type
- [ ] **A/B testing:** Testa olika suggestion formats och timing
- [ ] **User preferences:** Lär individuella preferenser per user/household
- [ ] **Contextual learning:** Anpassa till changing life circumstances

## ⚡ Fast-Path Tool System

### Regex-Based Command Routing
```typescript
// Exempel implementation:
const fastPaths = [
  { pattern: /^(tänd|släck|dimma) (.+)/, action: 'homeassistant.light' },
  { pattern: /^spela (.+)/, action: 'spotify.play' },
  { pattern: /^timer (\d+)/, action: 'timer.set' },
  { pattern: /^väder/, action: 'weather.current' }
];
```

### Bypass LLM för Vanliga Kommandon  
- [ ] **Light control:** Tänd/släck utan reasoning
- [ ] **Music commands:** Spotify direct integration
- [ ] **Timer/alarm:** Set timers med voice command parsing
- [ ] **Weather queries:** Direct API calls för väder

### Smart Device State Awareness
- [ ] **Device state cache:** Vet vilka lampor som är tänd/släckt
- [ ] **Room context:** "tänd lampan" i sovrum → sovrumslampa
- [ ] **Time-based defaults:** "tänd lampan" kl 06:00 → lämplig brightness
- [ ] **Predictive preloading:** Ladda device states innan commands

## 🧠 Proactive Suggestion Engine

### Trigger Rule System
```yaml
# Exempel YAML config för trigger rules
triggers:
  morning_routine:
    pattern: "ambient mentions coffee + time between 06:00-09:00"
    cooldown: "24h" 
    action: "suggest timer for coffee brewing"
    priority: "low"
  
  stress_detection:
    pattern: "sentiment negative + meeting mentioned"
    cooldown: "4h"
    action: "suggest 5min breathing exercise"
    priority: "medium"
```

### Context-Aware Timing
- [ ] **Opportunistic moments:** Föreslå under naturliga pauser i conversation
- [ ] **Non-intrusive delivery:** Visual notifications, inte voice interrupts
- [ ] **Batch suggestions:** Samla förslag till "Alice har 3 idéer" istället för spam
- [ ] **Progressive disclosure:** Start subtle, bli mer specific om user interested

### Personalization Engine  
- [ ] **Individual profiles:** Olika triggers per household member
- [ ] **Historical success:** Högre priority för previously accepted suggestion types
- [ ] **Seasonal adaptation:** Sommartips vs vintertips
- [ ] **Mood-aware:** Anpassa tone baserat på detected sentiment

## 🔒 Privacy & Ethics för Proaktivitet

### Data Minimization
- [ ] **Pattern abstractions:** Lagra patterns, inte raw conversations  
- [ ] **Aggregated insights:** "often discusses X" utan specific quotes
- [ ] **Temporal decay:** Gamla patterns får lägre weight över tid
- [ ] **Opt-out granularity:** Disable specifika trigger categories

### Transparent Operations
- [ ] **Explainable suggestions:** "Alice noticed you mention coffee every morning"
- [ ] **Suggestion audit:** "Alice has made 12 suggestions, you accepted 7"  
- [ ] **Pattern transparency:** User kan see sina egna detected patterns
- [ ] **Learning dashboard:** Visa vad Alice lär sig om dig

### Bias Prevention
- [ ] **Diverse suggestion sources:** Inte bara en typ av förslag
- [ ] **Counter-bias testing:** Testa suggestions mot olika demografier
- [ ] **Cultural sensitivity:** Svenska vs internationella customs/holidays
- [ ] **Avoid stereotypes:** Föreslå inte baserat på kön/ålder assumptions

## 📋 Implementation Phases

### Phase 1: Foundation (vecka 1-2)
- [ ] Ambient data aggregation system
- [ ] Basic pattern detection (temporal, keyword)
- [ ] Simple trigger rule engine
- [ ] Fast-path regex routing för 5 vanligaste commands

### Phase 2: Intelligence (vecka 3-4)  
- [ ] Machine learning för pattern recognition
- [ ] Context-aware suggestion timing
- [ ] User feedback collection system
- [ ] A/B testing framework för suggestions

### Phase 3: Personalization (vecka 5-6)
- [ ] Individual user profiles
- [ ] Learning från feedback
- [ ] Advanced context (calendar, weather, location)
- [ ] Privacy controls & transparency features

### Phase 4: Polish (vecka 7-8)
- [ ] UI för managing proactive settings
- [ ] Analytics dashboard för users
- [ ] Advanced safety features (DND, sensitivity)
- [ ] Documentation & user onboarding

## 🎯 Success Metrics

### User Engagement
- **Acceptance rate:** >30% av proactive suggestions accepteras
- **User retention:** Proactive users använder Alice 2x mer ofta  
- **Satisfaction score:** >4/5 på "Alice suggestions are helpful"
- **Discovery rate:** Users hittar nya features genom suggestions

### System Performance  
- **Latency:** Fast-path commands execute <100ms
- **Accuracy:** >90% av detected patterns är relevanta för user
- **False positive rate:** <5% av suggestions dismissed som irrelevant  
- **Resource usage:** Proactive system adds <10% CPU overhead

### Privacy Compliance
- **Data minimization:** Pattern storage <1KB per user per month
- **Transparency:** 100% av users kan explain vad Alice vet om dem
- **User control:** 100% av trigger types kan disable individuellt
- **Audit trail:** Alla proactive actions logged för review

---

## 🚀 Quick Start Implementation

1. **Börja med enkel temporal pattern detection**
2. **Implementera 3-5 fast-path commands först** 
3. **Bygg feedback collection från dag 1**
4. **Testa med power users innan general rollout**
5. **Prioritera privacy transparency över advanced features**

**Next Steps:** Create GitHub project board med dessa tasks, börja med Phase 1 items.