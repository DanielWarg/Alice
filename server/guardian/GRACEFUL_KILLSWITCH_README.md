# Graceful Killswitch Implementation för Alice Guardian

## Översikt

Implementering av en kontrollerad killswitch-sekvens som ersätter den brutala `pkill -9 -f ollama` metoden med en graceful eskalerande approach.

## Arkitektur

### Nya Komponenter

#### 1. `kill_sequence.py` - Huvudimplementation
- **GracefulKillSequence**: Huvudklass för killswitch-sekvens
- **OllamaSessionManager**: Hanterar Ollama sessions för graceful shutdown
- **PIDTracker**: Exakt PID-tracking för ollama serve process
- **HealthGate**: Health gating innan återöppning av systemet
- **KillSequenceConfig**: Konfiguration för killswitch-parametrar

#### 2. Uppdaterad `guardian.py`
- Integration av graceful killswitch i befintlig Guardian
- Fallback till legacy metod vid fel
- Killswitch status i health endpoint

## Förbättrad Killswitch-sekvens

### Steg 1: Stoppa Intake + Dränera Kö
```
1. POST /api/guard/stop-intake (429/"busy")
2. Vänta 5-10s för att dränera befintliga requests
```

### Steg 2a: Graceful Session Shutdown
```
1. Hämta aktiva sessions via `ollama ps`
2. Stoppa varje session individuellt med keep_alive=0
3. Verifiera att alla sessioner stoppats
```

### Steg 2b: Targeted Process Termination
```
1. Hitta exakt PID för `ollama serve` (inte alla "ollama" processer)
2. Skicka SIGTERM till endast serve-process
3. Vänta upp till 5s för graceful shutdown
4. Vid timeout: SIGKILL endast på serve-process
```

### Steg 3: Smart Restart
```
1. Exponentiell backoff: 5s → 15s → 60s
2. Försök systemd/launchctl före direkt binär-start
3. Spara ny serve-PID för framtida tracking
4. Max 3 restart-försök
```

### Steg 4: Health Gating
```
1. Vänta på /api/health/ready endpoint (HTTP 200)
2. LLM functionality test: "2+2=?" prompt
3. Endast öppna systemet när båda testen passerar
4. Timeout efter 60s om inte ready
```

## Säkerhetsförbättringar vs Brutal `pkill -9 -f ollama`

### 1. Exakt Process Targeting
**Tidigare**: `pkill -9 -f ollama` dödar ALLA processer med "ollama" i cmdline
```bash
# Riskabelt - kan döda:
# - ollama serve (önskat)
# - ollama pull model (oönskat)
# - annan applikation med "ollama" i namnet
# - editor med "ollama" i filnamn
```

**Nu**: Endast `ollama serve` process med exakt PID-matching
```python
# Säkert - endast serve-process:
cmdline = proc.cmdline()
if ('ollama' in cmdline[0].lower() and 'serve' in cmdline[1].lower()):
    target_pid = proc.pid
```

### 2. Graceful Session Cleanup
**Tidigare**: Modeller brutalt avslutade, potentiell datakorruption
```bash
pkill -9  # SIGKILL - inga cleanup möjligheter
```

**Nu**: Sessioner stoppas gracefully innan process-kill
```python
# Låt modeller spara state:
payload = {"model": model_name, "keep_alive": 0}
await client.post("/api/generate", json=payload)
```

### 3. Kontrollerad Eskalering
**Tidigare**: Direkt SIGKILL utan chans för graceful shutdown
```bash
pkill -9  # Ingen möjlighet för cleanup
```

**Nu**: SIGTERM → vänta → SIGKILL endast vid nöd
```python
proc.terminate()  # SIGTERM först
proc.wait(timeout=5.0)  # Vänta på graceful
# Endast vid timeout: proc.kill()  # SIGKILL
```

### 4. Restart Stability
**Tidigare**: Omedelbar restart utan systemvalidering
```python
# Riskabelt - kunde starta trasigt system:
subprocess.Popen([ollama_path, "serve"])
```

**Nu**: Health-gated restart med exponentiell backoff
```python
# Säkert - validera innan öppning:
await health_gate.wait_for_ready()
# + exponentiell backoff vid problem
```

### 5. State Management
**Tidigare**: Ingen tracking av restart-attempts eller PID
```python
# Okontrollerat - kunde loopa infinit
while True:
    restart_ollama()
```

**Nu**: PID-tracking och restart-limiting
```python
# Kontrollerat - max attempts + state tracking
if self.restart_attempt >= max_attempts:
    return False
```

## Konfiguration

### KillSequenceConfig Options
```python
@dataclass
class KillSequenceConfig:
    drain_timeout_s: float = 8.0        # Drain queue timeout
    sigterm_timeout_s: float = 5.0      # Graceful shutdown wait
    pid_file_path: str = "/tmp/alice_ollama.pid"
    restart_delays: List[float] = [5.0, 15.0, 60.0]  # Exponential backoff
    max_restart_attempts: int = 3
    health_timeout_s: float = 10.0
```

## Usage

### I Guardian
```python
from guardian.kill_sequence import GracefulKillSequence, KillSequenceConfig

# Setup
kill_config = KillSequenceConfig()
graceful_killer = GracefulKillSequence(kill_config)

# Execute
success = await graceful_killer.execute_full_sequence()
```

### Standalone
```python
from guardian.kill_sequence import execute_graceful_killswitch

# Simple usage
success = await execute_graceful_killswitch()
```

## Monitoring & Observability

### Health Endpoint Integration
```json
{
  "status": "ok",
  "killswitch": {
    "last_kill_time": "2025-01-15T10:30:00Z",
    "restart_attempts": 0,
    "max_attempts": 3,
    "serve_pid": 12345,
    "pid_file_exists": true
  }
}
```

### Logging
- Strukturerad loggning för varje steg i sekvensen
- Separata loggers för olika komponenter
- JSON metrics för monitoring integration

## Testing

### Test Suite
```bash
# PID operations test
python server/guardian/test_graceful_killswitch.py

# Choose option 1 for PID testing
# Choose option 2 for full sequence testing
```

### Validering
1. **PID Tracking**: Verify correct ollama serve identification
2. **Session Management**: Test individual session shutdown
3. **Process Termination**: Confirm SIGTERM → SIGKILL escalation
4. **Health Gating**: Validate LLM functionality after restart
5. **Restart Limiting**: Test exponential backoff behavior

## Fallback Behavior

Om graceful killswitch misslyckas, faller systemet tillbaka till legacy-metoden:
```python
if await actions.kill_ollama_graceful():
    # Framgång - system ready
    pass
else:
    # Fallback till brutal metod
    actions.kill_ollama_legacy()
    await asyncio.sleep(3)
    actions.restart_ollama_legacy()
```

## Säkerhetsvinster Sammanfattning

1. **Precisionsökning**: Endast target process påverkas
2. **Dataintegrity**: Graceful session shutdown förhindrar korruption
3. **Systemstabilitet**: Health-gating säkerställer funktionell restart
4. **Felhantering**: Exponentiell backoff förhindrar restart-loopar
5. **Observability**: Fullständig logging och status tracking
6. **Säker fallback**: Legacy-metod vid kritiska fel

Den nya implementeringen uppfyller alla specifikationskrav samtidigt som den dramatiskt förbättrar systemsäkerheten jämfört med den brutala `pkill -9 -f ollama` approachen.