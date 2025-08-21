# 🛠️ Alice Development Guide

Komplett utvecklingsguide för Alice AI Assistant Platform. Denna guide täcker allt från lokal utvecklingsmiljö till production deployment.

## 🚀 **Snabbstart för Utvecklare**

### Förutsättningar
- **Python 3.9+** - Backend och AI-kärna
- **Node.js 18+** - Frontend och build-tools
- **Git** - Versionshantering
- **Ollama** - Lokal AI-modell (gpt-oss:20B)

### Lokal Utvecklingsmiljö

1. **Klon och navigera:**
```bash
git clone https://github.com/DanielWarg/Alice.git
cd Alice
```

2. **Backend Setup:**
```bash
# Skapa virtuell miljö
python3 -m venv .venv
source .venv/bin/activate  # På Windows: .venv\Scripts\activate

# Installera dependencies
pip install -r server/requirements.txt
```

3. **Frontend Setup:**
```bash
cd web
npm install
```

4. **AI Setup (Ollama):**
```bash
# Installera Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Ladda ner modell
ollama pull gpt-oss:20b

# Starta Ollama
ollama serve
```

## 🏗️ **Projektstruktur**

```
Alice/
├── server/                 # FastAPI backend
│   ├── app.py             # Huvudapplikation
│   ├── core/              # Kärnmoduler
│   │   ├── router.py      # Intent-klassificering
│   │   ├── tool_registry.py # Verktygshantering
│   │   ├── tool_specs.py  # Verktygsspecifikationer
│   │   ├── calendar_service.py # Google Calendar
│   │   ├── gmail_service.py # Gmail integration
│   │   └── preflight.py   # System-kontroller
│   ├── prompts/           # AI-prompts på svenska
│   ├── tests/             # Backend-tester
│   ├── voice_stream.py    # Rösthantering
│   ├── voice_stt.py       # Speech-to-Text
│   └── requirements.txt   # Python dependencies
├── web/                    # Next.js frontend
│   ├── app/               # Next.js 13+ app directory
│   ├── components/        # React-komponenter
│   ├── lib/               # Hjälpbibliotek
│   └── package.json       # Node.js dependencies
├── alice-tools/            # NLU och router-system (TypeScript)
│   ├── src/router/        # Intent-klassificering
│   ├── src/lexicon/       # Svenska kommandon
│   └── tests/             # Router-tester
├── nlu-agent/              # Naturlig språkförståelse
├── tests/                  # Integrationstester
├── docs/                   # Dokumentation
└── tools/                  # Verktyg och utilities
```

## 🔧 **Utvecklingskommandon**

### Git & Repository
```bash
# Kontrollera remote
git remote -v

# Pusha till Alice-repositoryt
git push origin feature/harmony

# Hämta från Alice-repositoryt
git pull origin feature/harmony
```

### Backend Utveckling
```bash
# Starta backend med hot-reload
cd server
source ../.venv/bin/activate
uvicorn app:app --host 127.0.0.1 --port 8000 --reload

# Kör tester
python -m pytest tests/ -v

# Kör specifika tester
python -m pytest tests/test_harmony.py
python -m pytest tests/test_voice_system.py
```

### Frontend Utveckling
```bash
# Starta utvecklingsserver
cd web
npm run dev

# Bygg för produktion
npm run build

# Starta i produktionsläge
npm start
```

### Fullstack Utveckling
```bash
# Terminal 1: Backend
cd server && source ../.venv/bin/activate && uvicorn app:app --reload

# Terminal 2: Frontend
cd web && npm run dev

# Terminal 3: Ollama
ollama serve
```

## 🧪 **Testning**

### Teststruktur
```bash
tests/
├── harmony_e2e_test.py     # End-to-end Harmony-tester
├── test_harmony_tools.py   # Verktygsintegration
├── test_voice_system.py    # Röstsystem
└── results/                # Testresultat och rapporter
```

### Kör Tester
```bash
# Alla tester
cd tests
python -m pytest -v

# Specifika testkategorier
python -m pytest test_harmony_tools.py -v
python -m pytest test_voice_system.py -v

# Med coverage
python -m pytest --cov=../server --cov-report=html
```

### Testdata
```bash
# Generera testdata
cd tests
python generate_test_data.py

# Kör stress-tester
python stress_test_integrated.py
```

## 🔍 **Debugging**

### Backend Debug
```bash
# Starta med debug-loggar
export LOG_LEVEL=DEBUG
cd server
python -c "import app; print('App loaded successfully')"

# Kontrollera endpoints
curl http://localhost:8000/api/health
curl http://localhost:8000/api/tools/spec
```

### Frontend Debug
```bash
# Browser Developer Tools
# - Console för JavaScript-fel
# - Network tab för API-anrop
# - React DevTools för komponenter

# Logga till konsolen
console.log('Debug info:', data);
```

### AI Debug
```bash
# Testa Ollama-anslutning
curl http://localhost:11434/api/tags

# Testa modell
ollama run gpt-oss:20b "Hej, testar anslutningen"
```

## 📝 **Kodstandard**

### Python
- **PEP 8** - Python style guide
- **Type hints** - Använd `typing` modulen
- **Docstrings** - Google style docstrings
- **Black** - Automatisk kodformatering

```python
from typing import Dict, List, Optional
from pydantic import BaseModel

class ToolResponse(BaseModel):
    """Response model för verktygsexekvering."""
    
    success: bool
    message: str
    data: Optional[Dict] = None
    
    def __str__(self) -> str:
        return f"ToolResponse(success={self.success}, message='{self.message}')"
```

### TypeScript/JavaScript
- **ESLint** - Kodkvalitet
- **Prettier** - Kodformatering
- **TypeScript** - Typesäkerhet
- **Conventional Commits** - Git commit messages

```typescript
interface RouterResponse {
  intent: string;
  confidence: number;
  slots: Record<string, any>;
}

export function classifyIntent(text: string): RouterResponse {
  // Implementation
}
```

### Git Commits
```bash
# Conventional Commits
feat: add voice STT functionality
fix: resolve metrics variable collision
docs: update README with new structure
refactor: clean up project structure
test: add voice system tests
```

## 🚀 **Deployment**

För detaljerad deployment-information, se **[DEPLOYMENT.md](DEPLOYMENT.md)**.

### Snabbstart för lokal production
```bash
# Backend
cd server
source ../.venv/bin/activate
python run.py --production

# Frontend
cd web
npm run build
npm start
```

## 🔧 **Verktyg och Utilities**

### Preflight Checks
```bash
cd server
python -c "from core.preflight import run_preflight_checks; run_preflight_checks()"
```

### Tool Surface Verification
```bash
cd tests
python verify_tool_surface.py
```

### Performance Testing
```bash
cd tests
python stress_test_integrated.py
python stress_test_nlu.py
python stress_test_rag.py
```

## 📚 **API-utveckling**

### Nya Endpoints
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class NewEndpointRequest(BaseModel):
    data: str

@router.post("/api/new-endpoint")
async def new_endpoint(request: NewEndpointRequest):
    """Ny endpoint för funktionalitet."""
    try:
        # Implementation
        return {"success": True, "data": request.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### WebSocket Development
```python
@app.websocket("/ws/new-feature")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Process data
            await websocket.send_text(f"Processed: {data}")
    except WebSocketDisconnect:
        pass
```

## 🧠 **AI-utveckling**

### Harmony Adapter
```python
# Lägg till nya verktyg
from core.tool_registry import register_tool

@register_tool("NEW_TOOL")
def new_tool_function(args: Dict) -> str:
    """Implementera nytt verktyg."""
    return "Tool executed successfully"
```

### **Harmony Implementation Guide**

#### **Fas 0 – Baseline och säkerhetslina**
- [x] Skapa branch `feature/harmony`
- [x] Lägg env-flaggor: `USE_HARMONY=false`, `USE_TOOLS=false`
- [x] Sätt upp `.venv` i `server/` och frys beroenden

#### **Fas 1 – Harmony-adapter i servern**
- [x] Skapa adapter-lager i `server/app.py`
- [x] Instruktioner till modellen: resonemang i `analysis`, tool-calls i `commentary`, endast svar i `final`
- [x] Parsning: extrahera endast kanal `final` till klient
- [x] Lägg debug-loggning i dev: roll + kanal

#### **Fas 2 – Verktygsregister och validering**
- [x] Skapa `server/tools/registry.py` med verktygsspecar
- [x] Implementera exekvering med Pydantic-validering
- [x] Första verktyg: `PLAY`, `PAUSE`, `SET_VOLUME`, `SAY`/`DISPLAY`

#### **Fas 3 – Körsätt för gpt-oss lokalt**
- [x] Välj körsätt: Ollama-adapter
- [x] Dokumentera valet
- [x] Smoke-test: modell svarar i rätt kanaler

#### **Fas 4 – Prompts och policys**
- [x] Skapa `server/prompts/system_prompts.py` (svenska)
- [x] Skapa developer-prompt: följ Harmony; "no-tool-if-unsure"
- [x] Länka in i adapter-lagret

#### **Fas 5 – Router-först**
- [x] Behåll existerande NLU/router som förstaval
- [x] Lägg tröskel `NLU_CONFIDENCE_THRESHOLD` i env
- [x] Lägre confidence → skicka via Harmony + verktygsspec

#### **Fas 6 – Streaming och UI**
- [x] Servern streamar endast `final` till klient
- [x] Lägg lätt metadata till UI: `tool_called`, `tool_result`

#### **Fas 7 – Telemetri och loggning**
- [x] Logga p50/p95: tid till första `final`-token
- [x] Logga: tid `tool_call` → `tool_result`, valideringsfel
- [x] Logga: router-vs-LLM hit-rate

#### **Fas 8 – Evals**
- [x] Skapa 20 kommandon som kräver verktyg
- [x] Skapa 20 rena chattfrågor
- [x] Skapa 10 fall med saknade parametrar
- [ ] Mål: ≥95% korrekt vägval, 0% `analysis`-läckage

#### **Fas 9 – Utrullning i små PR:er**
- [x] PR1: flaggor + Harmony-adapter
- [x] PR2: tool-registry + validering
- [x] PR3: aktivera `USE_TOOLS=true`
- [x] PR4: router-först med tröskel
- [x] PR5: telemetri + syntetiska evals

#### **Fas 10 – Dokumentation och runbooks**
- [ ] Uppdatera `README.md`/`ARCHITECTURE.md`
- [ ] Runbook: lägga till nytt verktyg
- [ ] Felsökning: kanalläckage, valideringsfel, latensspikar

### NLU-utveckling
```typescript
// Lägg till nya intents i alice-tools
export function classifyNewIntent(input: string): IntentResult | null {
  const patterns = [
    /nytt mönster/i,
    /annat mönster/i
  ];
  
  for (const pattern of patterns) {
    if (pattern.test(input)) {
      return {
        intent: "NEW_INTENT",
        confidence: 1.0,
        slots: {}
      };
    }
  }
  
  return null;
}
```

## 🐛 **Vanliga Problem**

### Backend startar inte
```bash
# Kontrollera portar
lsof -i :8000

# Kontrollera dependencies
pip install -r requirements.txt

# Kontrollera Python-version
python --version
```

### Frontend bygg misslyckas
```bash
# Rensa cache
rm -rf node_modules package-lock.json
npm install

# Kontrollera Node-version
node --version
```

### Ollama-anslutning
```bash
# Kontrollera Ollama-status
ollama list

# Starta om Ollama
ollama serve

# Testa modell
ollama run gpt-oss:20b "test"
```

## 🤝 **Bidrag**

### Pull Request Process
1. **Forka repository**
2. **Skapa feature branch**
3. **Implementera funktionalitet**
4. **Lägg till tester**
5. **Uppdatera dokumentation**
6. **Skicka PR**

### Code Review
- **Kodkvalitet** - Följer standarder
- **Tester** - Alla tester passerar
- **Dokumentation** - Uppdaterad
- **Performance** - Ingen regression

## 📚 **Dokumentation**

- **[STARTUP.md](STARTUP.md)** - Exakt startup-guide
- **[README.md](README.md)** - Projektöversikt och status
- **[VISION.md](VISION.md)** - Projektvision och framtida funktioner
- **[ALICE_ROADMAP.md](ALICE_ROADMAP.md)** - Detaljerad utvecklingsplan
- **[API.md](API.md)** - Komplett API-dokumentation
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment och production-guide

---

**Alice Development** - Bygg framtidens AI-assistent! 🚀

*För ytterligare hjälp, se dokumentationen ovan.*

# 🎤 VoiceBox Integration & Planering

## Komponentöversikt

**VoiceBox** är en avancerad röst-komponent som ersätter den gamla enkla röst-funktionen i Alice HUD. Komponenten är designad för att ge en visuell representation av audio-input med real-time bars och integrerad speech recognition.

### Tekniska Specifikationer

- **Bars**: Konfigurerbar (standard: 5-7 bars)
- **Audio Processing**: WebAudio API med AnalyserNode
- **Speech Recognition**: Web Speech API (svenska)
- **Fallback-lägen**: Demo och pseudo-läge om mic inte är tillgänglig
- **Styling**: Anpassad för Alice's HUD tema (cyan/blue)

### Komponentstruktur

```typescript
interface VoiceBoxProps {
  bars?: number                    // Antal bars (default: 7)
  smoothing?: number              // EMA smoothing (0.15)
  minScale?: number               // Minimum skala (0.1)
  label?: string                  // Label text
  allowDemo?: boolean             // Demo-läge
  allowPseudo?: boolean           // Pseudo-läge
  onVoiceInput?: (text: string) => void  // Callback
}
```

## Integration Planer

### 1. Referens-implementation (Aktuell)
- **Placering**: VOICE-panelen (vänster kolumn)
- **Status**: ✅ Fungerar korrekt
- **Funktionalitet**: 
  - 5 bars med audio visualisering
  - "Starta mic" knapp
  - Röst-input läggs till i journal
  - "Add to To-do" funktionalitet

### 2. ALICE CORE Integration (Planerad)
- **Mål**: Ersätta spheren i ALICE CORE med VoiceBox
- **Placering**: Centrerad i ALICE CORE-panelen
- **Utmaningar identifierade**:
  - ✅ Komponenten renderar korrekt med audio bars
  - ❌ Placeringen är fel - inte där vi vill ha den
  - ❌ Formen är fel - kanske för smal, för hög, eller fel position
  - ❌ "Starta mic" knapp placerad fel

### 3. Felsökning & Lösningar

#### Problem 1: Fel placering
- **Symptom**: VoiceBox ligger inte där vi vill ha den i ALICE CORE
- **Möjliga orsaker**:
  - CSS-positionering (top, left, transform)
  - Container-struktur i ALICE CORE
  - Z-index eller overflow-problem

#### Problem 2: Fel form
- **Symptom**: VoiceBox är för smal, för hög, eller har fel proportioner
- **Lösning**: Kopiera exakt samma attribut som referens-komponenten

#### Problem 3: Knapp-placering
- **Symptom**: "Starta mic" knapp ligger fel
- **Lösning**: Justera positionering inom VoiceBox-komponenten

### 4. Rekommenderad Approach

1. **Behåll referens-komponenten** i VOICE-panelen
2. **Kopiera exakt samma attribut** till ALICE CORE-versionen
3. **Testa stegvis** - först placering, sedan styling
4. **Använd samma container-struktur** som fungerar i VOICE-panelen

### 5. Framtida Förbättringar

- **TTS Integration**: Låt Alice svara med röst
- **WebSocket Integration**: Real-time kommunikation med backend
- **Voice Commands**: Integrera med Alice's verktygssystem
- **Custom Styling**: Anpassa för olika HUD-teman

## Aktuell Status

- ✅ **VoiceBox-komponent**: Fungerar korrekt
- ✅ **Referens-implementation**: Synlig i VOICE-panelen
- ❌ **ALICE CORE integration**: Kräver felsökning
- 🔄 **Planering**: Under utveckling

## Nästa Steg

1. **Felsök ALICE CORE integration**
2. **Kopiera fungerande attribut**
3. **Testa placering och styling**
4. **Integrera med Alice's röst-system**

---

*Senast uppdaterad: 21 Augusti 2024*