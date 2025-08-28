# B4 - Proaktiv AI Pipeline 🧠
**Alice learns your patterns and proactively suggests automations**

---

## 🎯 B4 Vision
Alice observerar dina beteendemönster från ambient summaries (B3) och föreslår automationer/påminnelser **innan** du ber om dem. Diskreta toast-meddelanden, inga HUD-knappar.

---

## 📋 B4 Implementation Checklist

### **Phase 1: Backend Pattern Recognition** 🔍
- [ ] **Skapa `server/agent/pattern_recognizer.py`**
  - [ ] Analysera ambient summaries från B3 privacy system
  - [ ] Identifiera upprepade mönster (tid, plats, aktivitet)
  - [ ] Kandidat-logik för olika mönstertyper:
    - [ ] Tidsmönster: "Varje måndag 09:00 → meeting prep"
    - [ ] Platsmönster: "Hemma + kväll → review emails" 
    - [ ] Aktivitetsmönster: "Efter lunch → check calendar"
  - [ ] Spara patterns i SQLite med confidence score

- [ ] **Skapa `server/agent/proactive_trigger.py`**
  - [ ] Event trigger-system baserat på igenkända patterns
  - [ ] Respekterar Settings (quiet hours, max prompts/dag)
  - [ ] WebSocket push till `/ws/proactive` med suggestion payload
  - [ ] Logging av alla triggers för analys

- [ ] **Proactive WebSocket endpoint `/ws/proactive`**
  - [ ] Separate WebSocket för proactive suggestions
  - [ ] Payload format: `{type: "suggestion", pattern: {...}, message: "..."}`
  - [ ] Rate limiting enligt user settings

### **Phase 2: Frontend Proactive UI** 💡
- [ ] **Skapa `components/ProactiveToast.tsx`**
  - [ ] Diskret snackbar (top-right corner, ej HUD-intrång)
  - [ ] Design matchar HUD cyan-tema med glassmorphic stil
  - [ ] Auto-dismiss efter 10s om ingen interaktion
  - [ ] Knappar: [✅ Accept] [❌ Decline] [⏰ Snooze 1h]

- [ ] **Integrera WebSocket i main app**
  - [ ] Lyssna på `/ws/proactive` i main HUD
  - [ ] State management för active toasts
  - [ ] Max 1 toast åt gången (queue system)

- [ ] **Uppdatera SettingsDialog → Proactivity tab**
  - [ ] Level slider: Off → Minimal → Standard → Eager
  - [ ] Quiet hours: time picker för start/end
  - [ ] Max prompts per dag: slider 0-10
  - [ ] "View recent suggestions" button → modal med history

### **Phase 3: API & Feedback Loop** 🔄
- [ ] **`POST /api/proactive/feedback`**
  - [ ] Accept: `{action: "accept", pattern_id: "...", metadata: {...}}`
  - [ ] Decline: `{action: "decline", pattern_id: "...", reason: "..."}`
  - [ ] Snooze: `{action: "snooze", pattern_id: "...", duration_hours: 1}`
  - [ ] Uppdatera pattern confidence baserat på feedback

- [ ] **`GET /api/proactive/status`**
  - [ ] Return: settings, recent triggers, pattern stats
  - [ ] För Settings UI och debugging

- [ ] **`GET /api/proactive/history`**
  - [ ] Senaste 50 suggestions med feedback
  - [ ] För "View recent suggestions" modal

### **Phase 4: Pattern Learning Algorithm** 🤖
- [ ] **Implementera confidence scoring**
  - [ ] Initial pattern: confidence = 0.3
  - [ ] Accept feedback: +0.2 confidence
  - [ ] Decline feedback: -0.1 confidence
  - [ ] Min threshold 0.5 för trigger

- [ ] **Multi-pattern correlation**
  - [ ] Kombinera tid + aktivitet patterns
  - [ ] "Måndag morgon + email patterns → meeting prep suggestion"
  - [ ] Avoid spam: max 1 suggestion per pattern typ per dag

- [ ] **Privacy-aware learning**
  - [ ] Patterns försvinner efter TTL (samma som B3 privacy)
  - [ ] Sensitive patterns (private info) → shorter TTL
  - [ ] "Glöm mönster" kommando → pattern deletion

---

## 🎯 B4 DoD (Definition of Done)

### **Must Have**
- [ ] Alice identifierar minst 2 enkla patterns (tid/aktivitet)
- [ ] Proactive suggestions visas som toast (ej HUD-knappar)
- [ ] User kan accept/decline/snooze med feedback till algoritmen
- [ ] Settings → Proactivity tab funktionell med level/quiet hours
- [ ] All pattern data respekterar B3 privacy TTL

### **Nice to Have**
- [ ] Pattern confidence learning över tid
- [ ] Multi-pattern correlation (tid + aktivitet)
- [ ] Suggestion history viewer i Settings
- [ ] Voice commands: "Alice, suggest something" / "stop suggestions"

### **Technical Requirements**
- [ ] Proactive system körs som bakgrundstask (ej blocking)
- [ ] WebSocket isolation (proactive separate från B3 voice)
- [ ] SQLite schema för patterns + feedback
- [ ] Rate limiting: max prompts enligt user settings
- [ ] Logging för pattern analysis och debugging

---

## 🚀 B4 Launch Success Criteria

**Scenario A: Time Pattern**
1. User checkar emails varje måndag 09:00 (3 veckor i rad)
2. Alice identifierar mönster, föreslår: "Set Monday morning email reminder?"
3. User accepterar → automation skapas
4. Nästa måndag → påminnelse aktiveras automatiskt

**Scenario B: Activity Pattern**  
1. User säger "check calendar" efter lunch (5 dagar i rad)
2. Alice föreslår: "Add daily post-lunch calendar review?"
3. User snoozer → förslag kommer tillbaka nästa vecka
4. User accepterar → daglig automation

**Scenario C: Privacy Respect**
1. Quiet hours 22:00-07:00 → inga suggestions
2. Max 3 prompts/dag → stops efter limit
3. User säger "stop being proactive" → level = off
4. Patterns äldre än TTL → raderas automatiskt

---

## 📊 B4 Metrics & Success

- **Pattern Recognition**: % av identifierade patterns som blir accepterade
- **User Satisfaction**: Accept/Decline ratio över tid  
- **Privacy Compliance**: Patterns respekterar TTL settings
- **Performance**: Pattern analysis < 100ms, suggestions < 2s latency
- **Adoption**: % users som aktiverar proactive mode efter 1 vecka

---

**Ready to start B4? 🎯**
Nästa steg: börja med `server/agent/pattern_recognizer.py` → analysera befintliga B3 ambient summaries för första patterns.