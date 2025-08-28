# Guardian Hysteresis & Brownout Implementation

## Översikt

Guardian har implementerats med avancerad hysteresis, cooldown-logik och intelligent brownout-läge för att förhindra oscillation och ge graceful degradation före hårda kills.

## Tillståndsmaskin

Guardian arbetar med följande tillstånd:

```
NORMAL ──────► BROWNOUT ──────► EMERGENCY
   ▲               │                │
   │               ▼                │
   └─── DEGRADED ◄────────────────┘
                    │
                    ▼
                LOCKDOWN
```

### Tillståndsbeskrivningar

1. **NORMAL**: Normal operation, inga restriktioner
2. **BROWNOUT**: Intelligent feature degradation - behåller funktionalitet men minskar resurskrav
3. **DEGRADED**: Basic degradation - enklare åtgärder
4. **EMERGENCY**: Hard kill-sekvens aktiveras
5. **LOCKDOWN**: Manuell intervention krävs - systemet låst efter för många kills

## Hysteresis-logik

### Mätfönster
- **Trigger**: Kräver **5 konsekutiva mätpunkter** över tröskel för aktivering
- **Recovery**: Kräver värden under recovery-tröskel i **60 sekunder**
- **Förhindrar**: Oscillation genom att kräva konsistent data

### Trösklar
```python
RAM_SOFT_TRIGGER = 85%     # 5 mätpunkter → BROWNOUT
RAM_HARD_TRIGGER = 92%     # Omedelbar → EMERGENCY  
RAM_RECOVERY = 75%         # Under denna i 60s → NORMAL

CPU_SOFT_TRIGGER = 85%
CPU_HARD_TRIGGER = 92%
CPU_RECOVERY = 75%
```

### Flap Detection
- Spårar tillståndsändringar i ett 10-punkt fönster
- Om >50% av fönstret är ändringar → tvinga BROWNOUT för stabilisering

## Cooldown & Kill Rate Limiting

### Regler
1. **Kort cooldown**: Max 1 kill per 5 minuter
2. **Lång cooldown**: Max 3 kills per 30 minuter
3. **Lockdown**: Om över gränsen → 1 timme lockdown med manuell override

### Fallback-strategi
- Om kill blockeras av cooldown → Falla tillbaka till BROWNOUT/DEGRADED
- Förhindrar systemkollaps genom intelligent degradation

## Brownout-läge (Intelligent Degradation)

### Strategier per Degradation Level

#### LIGHT Brownout
- Context window: 8 → 6
- RAG top_k: 8 → 6  
- Disabled tools: `code_interpreter`

#### MODERATE Brownout
- Model: `gpt-oss:20b` → `gpt-oss:7b`
- Context window: 8 → 3
- RAG top_k: 8 → 3
- Disabled tools: `code_interpreter`, `file_search`, `web_search`

#### HEAVY Brownout  
- Model: `gpt-oss:20b` → `gpt-oss:7b`
- Context window: 8 → 3
- RAG top_k: 8 → 3
- Disabled tools: `code_interpreter`, `file_search`, `web_search`, `calendar`, `email`

### Brownout Actions
1. **Model Switch**: POST `/api/brain/model/switch` - Byt till mindre modell
2. **Context Reduction**: POST `/api/brain/context/set` - Minska context window
3. **RAG Reduction**: POST `/api/brain/rag/set` - Färre RAG-resultat
4. **Tool Disable**: POST `/api/brain/tools/disable` - Stäng av tunga tools

## Auto-tuning

### Concurrency Adjustment
- Mäter p95 latency varje 60 sekunder
- Om p95 > target (2000ms) → minska concurrency med 1
- Om p95 < 70% av target → öka concurrency med 1
- Range: 1-10 samtidiga förfrågningar

### Endpoint
```http
POST /api/guard/set-concurrency
{
  "concurrency": 5
}
```

## API Endpoints

### Guardian Control
```http
POST /api/guard/degrade          # Basic degradation
POST /api/guard/stop-intake      # Block new requests  
POST /api/guard/resume-intake    # Resume requests
POST /api/guard/set-concurrency  # Set concurrency level
```

### Brain/Model Control
```http
POST /api/brain/model/switch     # Switch LLM model
POST /api/brain/context/set      # Set context window
POST /api/brain/rag/set          # Set RAG parameters
POST /api/brain/tools/disable    # Disable tools
POST /api/brain/tools/enable-all # Re-enable all tools
GET  /api/brain/status           # Get current settings
```

### Guardian Status
```http
GET /health                      # Full Guardian status
POST /override-lockdown          # Manual lockdown override
```

## NDJSON Logging

Guardian loggar alla events som strukturerad NDJSON för analys:

### Event Types
- `guardian_started` - Startup med konfiguration
- `metrics_collected` - Löpande metrics med tillstånd
- `state_transition` - Tillståndsändringar med orsak
- `brownout_activated` - Brownout aktivering
- `brownout_restored` - Brownout återställning  
- `ollama_killed` - Kill events med metrics
- `kill_blocked_cooldown` - Blockerade kills
- `lockdown_activated` - Lockdown aktivering
- `lockdown_expired` - Automatisk lockdown-utgång
- `lockdown_manual_override` - Manuell override
- `auto_tuning_adjustment` - Concurrency-justeringar
- `guardian_shutdown` - Shutdown med stats

### Exempel NDJSON Entry
```json
{
  "timestamp": "2025-08-28T14:30:15.123",
  "event": "state_transition", 
  "from_state": "normal",
  "to_state": "brownout",
  "reason": "Soft trigger: RAM 5pt avg=87.2%, CPU 5pt avg=86.8%",
  "flapping_detected": false,
  "ram_measurements": [0.872, 0.874, 0.869, 0.871, 0.873],
  "cpu_measurements": [0.868, 0.871, 0.865, 0.869, 0.870]
}
```

## Implementation Files

### Core Components
- `guardian/guardian.py` - Huvudlogik med hysteresis state machine
- `guardian/brownout_manager.py` - Intelligent feature degradation
- `guardian/kill_sequence.py` - Graceful kill sequences
- `server/app_minimal.py` - Brain/Guard API endpoints

### Demo & Testing
- `guardian/demo_guardian.py` - Interaktiv demo med simulerade scenarios

## Användning

### Starta Guardian
```bash
cd server/guardian
python guardian.py
```

### Kör Demo
```bash
cd server/guardian  
python demo_guardian.py soft_trigger    # Brownout scenario
python demo_guardian.py hard_trigger    # Emergency scenario
python demo_guardian.py flapping       # Flap detection
python demo_guardian.py lockdown_test  # Lockdown scenario
```

### Status Monitoring
```bash
curl http://localhost:8787/health | jq .
```

### Manual Override (vid lockdown)
```bash
curl -X POST http://localhost:8787/override-lockdown \\
  -H "Content-Type: application/json" \\
  -d '{"confirm_override": true}'
```

## Fördelar

### Hysteresis
- ✅ Förhindrar oscillation mellan tillstånd
- ✅ Kräver konsistent data för triggers
- ✅ Graceful recovery med tidsfördröjning

### Cooldown  
- ✅ Förhindrar "kill storms"
- ✅ Automatisk lockdown vid överträdelser
- ✅ Fallback till intelligent degradation

### Brownout
- ✅ Behåller funktionalitet under belastning
- ✅ Gradvis degradation istället för total avbrott
- ✅ Automatisk återställning vid recovery

### Auto-tuning
- ✅ Dynamisk concurrency-justering
- ✅ Baserat på verklig latency-data
- ✅ Förhindrar överbelastning proaktivt

### Spårbarhet
- ✅ Fullständig NDJSON-loggning av alla events
- ✅ Korrelationsanalys möjlig
- ✅ Historisk data för optimering

## Konfiguration

Alla inställningar kan justeras via `GuardianConfig`:

```python
config = GuardianConfig(
    # Hysteresis
    measurement_window=5,
    recovery_window_s=60.0,
    
    # Trösklar  
    ram_soft_pct=0.85,
    ram_recovery_pct=0.75,
    
    # Cooldown
    kill_cooldown_short_s=300.0,   # 5 min
    kill_cooldown_long_s=1800.0,   # 30 min
    max_kills_per_window=3,
    lockdown_duration_s=3600.0,    # 1 hour
    
    # Brownout
    brownout_model_primary="gpt-oss:20b",
    brownout_model_fallback="gpt-oss:7b",
    
    # Auto-tuning
    target_p95_latency_ms=2000.0
)
```

Detta system ger en robust, intelligent och spårbar lösning för systemövervakning som förhindrar oscillation och ger graceful degradation under belastning.