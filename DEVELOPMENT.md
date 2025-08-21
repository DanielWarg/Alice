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

### Lokal Production
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

### Docker Deployment
```bash
# Bygg image
docker build -t alice:latest .

# Kör container
docker run -p 8000:8000 -p 3000:3000 alice:latest
```

### Environment Variables
```bash
# .env
USE_HARMONY=true
USE_TOOLS=true
LOG_LEVEL=INFO
OLLAMA_BASE_URL=http://localhost:11434
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
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

---

**Alice Development** - Bygg framtidens AI-assistent! 🚀

*För ytterligare hjälp, se [API.md](API.md) och [VISION.md](VISION.md).*