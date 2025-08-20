# Alice Development Guide

Denna guide täcker utvecklingsprocessen för Alice AI Assistant Platform, inklusive utvecklingsmiljö, kodstrukturer, testning och bidragningsriktlinjer.

## Development Environment Setup

### Förkunskaper

- **Python**: 3.9+ (3.11 rekommenderat)
- **Node.js**: 18+ (LTS rekommenderat)
- **Git**: Senaste version
- **Editor**: VS Code rekommenderat med extensions
- **Ollama**: För lokal AI-modell hosting

### Första installation

#### 1. Klona repository
```bash
git clone <repository-url>
cd alice
```

#### 2. Python backend setup
```bash
# Skapa virtuell miljö
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Installera development dependencies
cd server
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Om utvecklingsspecifika paket finns
```

#### 3. Node.js frontend setup
```bash
cd web
npm install
```

#### 4. NLU Agent setup  
```bash
cd nlu-agent
npm install
```

#### 5. Alice Tools setup
```bash
cd alice-tools
npm install
```

#### 6. Development environment konfiguration
```bash
# Skapa development .env i projektets rot
cat > .env << EOF
# Development Environment
NODE_ENV=development
PYTHONPATH=$(pwd)/server

# Alice Core Configuration  
USE_HARMONY=false
USE_TOOLS=true
ENABLED_TOOLS=PLAY,PAUSE,STOP,NEXT,PREV,SET_VOLUME,MUTE,UNMUTE,SHUFFLE,REPEAT,LIKE,UNLIKE
HARMONY_TEMPERATURE_COMMANDS=0.2
NLU_CONFIDENCE_THRESHOLD=0.85
JARVIS_MINIMAL=0

# Local Development Ports
BACKEND_PORT=8000
FRONTEND_PORT=3100  
NLU_AGENT_PORT=7071

# Database
DATABASE_URL=sqlite:///$(pwd)/data/development.db

# Logging
LOG_LEVEL=DEBUG
LOG_FILE=$(pwd)/logs/alice-dev.log

# Spotify Development Credentials
SPOTIFY_CLIENT_ID=your_dev_client_id
SPOTIFY_CLIENT_SECRET=your_dev_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:3100/spotify/callback

# AI Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gpt-oss:7b  # Mindre modell för utveckling

# TTS Development
TTS_VOICE=sv_SE-nst-medium
TTS_SPEED=1.0
EOF
```

### VS Code Extensions

Rekommenderade extensions för optimal utvecklingsupplevelse:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter", 
    "ms-python.isort",
    "ms-python.mypy-type-checker",
    "bradlc.vscode-tailwindcss",
    "ms-vscode.vscode-typescript-next",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-json",
    "redhat.vscode-yaml",
    "ms-vscode.makefile-tools"
  ]
}
```

### Pre-commit hooks

```bash
# Installera pre-commit
pip install pre-commit

# Skapa .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.0.0-alpha.4
    hooks:
      - id: prettier
        files: \.(js|ts|jsx|tsx|json|css|md)$
EOF

# Installera hooks
pre-commit install
```

## Projektstruktur

### Arkitekturöversikt

```
alice/
├── server/                 # FastAPI Backend
│   ├── app.py             # Huvudapplikation & routing
│   ├── core/              # Kärnfunktionalitet
│   │   ├── __init__.py    # Core module exports
│   │   ├── router.py      # Intent klassificering & routing
│   │   ├── tool_registry.py # Verktygshantering
│   │   ├── tool_specs.py  # Pydantic schemas för verktyg
│   │   └── preflight.py   # System-validering
│   ├── prompts/           # AI prompts & templates
│   │   └── system_prompts.py
│   ├── tests/             # Backend unit & integration tests
│   ├── memory.py          # RAG & långtidsminne
│   ├── decision.py        # AI beslutssystem
│   ├── metrics.py         # Performance metrics
│   └── requirements.txt   # Python dependencies
├── web/                   # Next.js Frontend
│   ├── app/               # Next.js 13+ App Router
│   │   ├── page.jsx       # Huvudsida (HUD)
│   │   ├── layout.jsx     # Layout wrapper
│   │   └── globals.css    # Global stilar
│   ├── components/        # React komponenter
│   │   ├── ui/           # UI primitives (shadcn/ui)
│   │   ├── AliceCore.jsx # AI Core visualisering
│   │   └── ...           # Andra komponenter
│   ├── lib/              # Utilities & API clients
│   │   ├── api.js        # Backend API wrapper
│   │   └── utils.js      # Helper funktioner
│   ├── store/            # State management (Zustand)
│   ├── types/            # TypeScript definitioner
│   └── package.json      # Node dependencies
├── alice-tools/         # Verktygsbibliotek (TypeScript)
│   ├── src/
│   │   ├── index.ts      # Entry point
│   │   ├── router/       # Routing logik
│   │   │   ├── router.ts # Main router implementation
│   │   │   └── slots.ts  # Slot extraction
│   │   └── lexicon/      # Språkdata
│   └── tests/            # Tool-specifika tester
├── nlu-agent/            # NLU mikroservice
│   ├── src/
│   │   └── index.ts      # Express server för NLU
│   └── data/             # NLU träningsdata
└── tests/                # End-to-end tester
```

### Modularkitektur

#### Backend Modules

**app.py** - Huvudapplikation
- FastAPI app initialization
- Route definitions
- WebSocket handling
- Middleware configuration

**core/** - Kärnfunktionalitet
- **router.py**: Intent klassificering med regex + fuzzy matching
- **tool_registry.py**: Verktygsvalidering och exekvering
- **tool_specs.py**: Pydantic schemas för alla verktyg
- **preflight.py**: System health checks

**prompts/** - AI Prompts
- Strukturerade prompts för olika AI-uppgifter
- Språkspecifika templates

#### Frontend Modules

**app/** - Next.js App Router
- Server-side rendering
- Client-side routing
- Layout definitions

**components/** - React komponenter
- Återanvändbara UI-komponenter
- Feature-specifika komponenter
- UI primitives från shadcn/ui

**lib/** - Hjälpbibliotek
- API integration
- Utilities och helpers
- Type definitions

## Kodstandard

### Python (Backend)

#### Style Guide
```python
# Följ PEP 8 med dessa tillägg:

# 1. Type hints är obligatoriska
def classify_intent(text: str) -> Optional[Dict[str, Any]]:
    """Klassificera användarintention från text."""
    pass

# 2. Docstrings för alla publika funktioner
def validate_tool_args(tool: str, args: dict) -> bool:
    """
    Validera verktygsargument mot schema.
    
    Args:
        tool: Verktygsnamn (t.ex. "PLAY")
        args: Argumentdictionary
        
    Returns:
        True om argumenten är giltiga
        
    Raises:
        ValidationError: Om argumenten inte matchar schema
    """
    pass

# 3. Explicita imports
from typing import Dict, List, Optional, Any
from core.tool_specs import TOOL_SPECS
```

#### Naming Conventions
```python
# Variabler och funktioner: snake_case
user_input = "spela musik"
confidence_threshold = 0.85

def extract_volume_level(text: str) -> Optional[int]:
    pass

# Klasser: PascalCase
class IntentClassifier:
    pass

# Konstanter: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_CONFIDENCE = 0.85

# Privata members: _underscore prefix
def _internal_helper() -> None:
    pass
```

### TypeScript/JavaScript (Frontend)

#### Style Guide
```typescript
// 1. Explicita typer för publika interfaces
interface ChatResponse {
  text: string;
  provider: string;
  confidence: number;
}

// 2. Functional components med TypeScript
const ChatInterface: React.FC<ChatInterfaceProps> = ({ 
  onMessage, 
  isLoading 
}) => {
  // Implementation
};

// 3. Custom hooks för logik separation
const useAliceChat = () => {
  const [response, setResponse] = useState<ChatResponse | null>(null);
  
  const sendMessage = async (message: string): Promise<void> => {
    // Implementation
  };
  
  return { response, sendMessage };
};
```

#### Component Structure
```jsx
// Komponentstruktur för React komponenter:

import React from 'react';
import { useState, useEffect } from 'react';

// 1. Props interface först
interface ComponentProps {
  title: string;
  onAction: () => void;
  optional?: boolean;
}

// 2. Komponent implementation
export const Component: React.FC<ComponentProps> = ({ 
  title, 
  onAction, 
  optional = false 
}) => {
  // 3. State hooks
  const [isActive, setIsActive] = useState(false);
  
  // 4. Effect hooks
  useEffect(() => {
    // Side effects
  }, []);
  
  // 5. Event handlers
  const handleClick = () => {
    onAction();
  };
  
  // 6. Render
  return (
    <div className="component">
      <h2>{title}</h2>
      {/* JSX content */}
    </div>
  );
};
```

## Testing Strategy

### Backend Testing

#### Unit Tests (pytest)
```python
# server/tests/test_router.py
import pytest
from core.router import classify, similarity

class TestIntentClassification:
    
    def test_play_command_exact_match(self):
        """Test exakt match för PLAY kommando."""
        result = classify("spela")
        assert result is not None
        assert result["tool"] == "PLAY"
        assert result["confidence"] == 1.0
    
    def test_volume_with_level(self):
        """Test volymkommando med specifik nivå."""
        result = classify("sätt volym till 50")
        assert result["tool"] == "SET_VOLUME"
        assert result["args"]["level"] == 50
        
    @pytest.mark.parametrize("input_text,expected_tool", [
        ("pausa", "PAUSE"),
        ("stoppa", "STOP"),
        ("nästa", "NEXT"),
    ])
    def test_media_commands(self, input_text, expected_tool):
        """Test olika mediakommandon."""
        result = classify(input_text)
        assert result["tool"] == expected_tool
```

#### Integration Tests
```python
# server/tests/test_api_integration.py
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

class TestAPIIntegration:
    
    def test_chat_endpoint(self):
        """Test chat API endpoint."""
        response = client.post("/api/chat", json={
            "prompt": "spela musik",
            "provider": "auto"
        })
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
    
    def test_tool_execution(self):
        """Test verktygsexekvering."""
        response = client.post("/api/tools/exec", json={
            "tool": "PLAY",
            "args": {}
        })
        assert response.status_code == 200
        assert response.json()["ok"] is True
```

### Frontend Testing

#### Component Tests (Jest + React Testing Library)
```jsx
// web/__tests__/components/ChatInterface.test.jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatInterface } from '@/components/ChatInterface';

describe('ChatInterface', () => {
  const mockOnMessage = jest.fn();
  
  beforeEach(() => {
    mockOnMessage.mockClear();
  });
  
  it('renders chat input', () => {
    render(<ChatInterface onMessage={mockOnMessage} />);
    expect(screen.getByPlaceholderText(/fråga alice/i)).toBeInTheDocument();
  });
  
  it('calls onMessage when form is submitted', async () => {
    render(<ChatInterface onMessage={mockOnMessage} />);
    
    const input = screen.getByPlaceholderText(/fråga alice/i);
    const button = screen.getByText(/fråga/i);
    
    fireEvent.change(input, { target: { value: 'spela musik' } });
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockOnMessage).toHaveBeenCalledWith('spela musik');
    });
  });
});
```

#### E2E Tests (Playwright)
```javascript
// tests/e2e/alice-integration.spec.js
const { test, expect } = require('@playwright/test');

test.describe('Alice Integration', () => {
  test('complete chat flow works', async ({ page }) => {
    await page.goto('http://localhost:3100');
    
    // Vänta på att Alice Core laddas
    await expect(page.locator('.alice-core')).toBeVisible();
    
    // Testa chatfunktion
    const chatInput = page.locator('input[placeholder*="Fråga Alice"]');
    await chatInput.fill('spela musik');
    
    await page.click('button:has-text("Fråga")');
    
    // Vänta på svar
    await expect(page.locator('.chat-response')).toBeVisible();
  });
});
```

### Test Commands

```bash
# Backend tests
cd server
python -m pytest tests/ -v --cov=. --cov-report=html

# Frontend tests  
cd web
npm test
npm run test:e2e

# Alla tester
npm run test:all
```

## Development Workflow

### Git Workflow

#### Branch Strategy
```bash
# Main branches
main              # Production-ready code
develop           # Integration branch for features

# Feature branches
feature/ai-voice-integration
feature/spotify-playlist-support
feature/user-preferences

# Hotfix branches
hotfix/security-update
hotfix/critical-bug-fix
```

#### Commit Conventions
```bash
# Conventional Commits format:
# <type>[optional scope]: <description>

feat(api): lägg till TTS synthesize endpoint
fix(router): korrigera volym-klassificering för svenska
docs(readme): uppdatera installation guide
test(nlu): lägg till tester för slot extraction
refactor(core): förbättra tool registry prestanda
perf(api): optimera WebSocket meddelanden
style(web): formatera komponenter enligt prettier
chore(deps): uppdatera dependencies
```

### Development Process

#### 1. Feature Development
```bash
# Starta ny feature
git checkout develop
git pull origin develop
git checkout -b feature/my-new-feature

# Utveckling med kontinuerlig testning
npm run test:watch  # Kontinuerliga tester
npm run dev        # Development server

# Commit changes
git add .
git commit -m "feat(feature): beskrivning av ändring"

# Push och skapa PR
git push origin feature/my-new-feature
# Skapa Pull Request via GitHub
```

#### 2. Code Review Process
- Alla ändringar måste granskas av minst en annan utvecklare
- Automated checks måste passera (tests, linting, type checking)
- Documentation updates för publika API ändringar

#### 3. Integration Testing
```bash
# Testa full integration lokalt innan PR
./scripts/test-full-integration.sh

# Starta alla services
./scripts/start-dev-env.sh

# Kör E2E tester
npm run test:e2e
```

## Debugging

### Backend Debugging

#### Logging Konfiguration
```python
# server/app.py
import logging
from rich.logging import RichHandler

# Konfigurera rich logging för utveckling
logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("alice")

# Användning i kod
logger.debug("Processing intent: %s", text)
logger.info("Tool executed: %s", tool_name)
logger.warning("Low confidence: %f", confidence)
logger.error("Tool execution failed: %s", error)
```

#### Interactive Debugging
```python
# Använd ipdb för interaktiv debugging
import ipdb; ipdb.set_trace()

# Eller använd VS Code debugger med launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Alice Backend",
      "type": "python",
      "request": "launch",
      "program": "server/app.py",
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    }
  ]
}
```

### Frontend Debugging

#### Browser DevTools
```javascript
// Debug hooks med React DevTools
const DebugComponent = () => {
  const [state, setState] = useState('initial');
  
  // Exponera för DevTools
  React.useDebugValue(`State: ${state}`);
  
  return <div>{state}</div>;
};

// Console debugging
console.group('Alice Chat');
console.log('Sending message:', message);
console.log('Response:', response);
console.groupEnd();
```

#### Network Debugging
```bash
# Övervaka API-anrop
npx http-server logs/ -p 8080  # Servera loggar över HTTP

# Använd network tab i DevTools för att inspektera:
# - API request/response
# - WebSocket meddelanden  
# - TTS audio data
# - Real-time updates
```

## Performance Optimization

### Backend Optimering

#### Database Queries
```python
# Optimera SQLite för utveckling
import sqlite3

def optimize_sqlite_connection():
    conn = sqlite3.connect('data/development.db')
    # Enable WAL mode för bättre concurrent access
    conn.execute('PRAGMA journal_mode=WAL')
    # Increase cache size
    conn.execute('PRAGMA cache_size=10000')
    # Store temporary tables in memory
    conn.execute('PRAGMA temp_store=MEMORY')
    return conn
```

#### Caching
```python
from functools import lru_cache
from typing import Dict, Any

# Cache intent classification results
@lru_cache(maxsize=1000)
def classify_intent_cached(text: str) -> Optional[Dict[str, Any]]:
    return classify_intent(text)

# Cache tool specs
@lru_cache(maxsize=1)
def get_tool_specs_cached() -> List[Dict[str, Any]]:
    return build_harmony_tool_specs()
```

### Frontend Optimering

#### React Optimization
```jsx
import { memo, useMemo, useCallback } from 'react';

// Memoize komponenter som inte behöver re-renderas
const ExpensiveComponent = memo(({ data }) => {
  const processedData = useMemo(() => {
    return processExpensiveData(data);
  }, [data]);
  
  return <div>{processedData}</div>;
});

// Memoize event handlers
const ChatInterface = ({ onMessage }) => {
  const handleSubmit = useCallback((message) => {
    onMessage(message);
  }, [onMessage]);
  
  return <form onSubmit={handleSubmit}>...</form>;
};
```

#### Bundle Optimization
```javascript
// next.config.mjs
const nextConfig = {
  // Code splitting för bättre performance
  experimental: {
    optimizeCss: true,
  },
  
  // Compress images
  images: {
    formats: ['image/webp', 'image/avif'],
  },
  
  // Bundle analyzer för development
  webpack: (config, { dev }) => {
    if (dev) {
      config.plugins.push(
        new (require('webpack-bundle-analyzer')).BundleAnalyzerPlugin({
          openAnalyzer: false,
          analyzerMode: 'static'
        })
      );
    }
    return config;
  }
};
```

## Contributing Guidelines

### Pull Request Process

1. **Pre-PR Checklist**
   ```bash
   # Kör alla kvalitetskontroller
   npm run lint        # Linting
   npm run type-check  # TypeScript
   npm run test        # Unit tests
   npm run test:e2e    # E2E tests
   npm run build       # Build check
   ```

2. **PR Template**
   ```markdown
   ## Beskrivning
   Kort beskrivning av ändringarna

   ## Typ av ändring
   - [ ] Bug fix
   - [ ] Ny feature
   - [ ] Breaking change
   - [ ] Dokumentation

   ## Testing
   - [ ] Unit tests tillagda/uppdaterade
   - [ ] Integration tests körs
   - [ ] Manuell testning genomförd

   ## Checklist
   - [ ] Code följer projektets style guide
   - [ ] Self-review genomförd
   - [ ] Dokumentation uppdaterad
   - [ ] Inga varningar i console
   ```

3. **Review Process**
   - Minst en godkänd review krävs
   - Alla CI checks måste passera
   - Diskussion och feedback uppmuntras

### Code Quality Standards

#### Definition of Done
- [ ] Feature fungerar som specificerat
- [ ] Unit tests skrivna och passerar
- [ ] Integration tests passerar  
- [ ] Kod granskad och godkänd
- [ ] Dokumentation uppdaterad
- [ ] Performance påverkan bedömd
- [ ] Säkerhetsaspekter bedömda
- [ ] Accessibility kontrollerad (för UI ändringar)

#### Security Guidelines
```python
# 1. Input validation
from pydantic import BaseModel, validator

class UserInput(BaseModel):
    text: str
    
    @validator('text')
    def validate_text(cls, v):
        if len(v) > 1000:
            raise ValueError('Text too long')
        # Filtrera potentiellt farlig input
        return sanitize_input(v)

# 2. Environment secrets
import os
from dotenv import load_dotenv

# Aldrig hardkoda secrets
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError('SECRET_KEY environment variable required')
```

## Troubleshooting Common Issues

### Development Environment

#### Port Conflicts
```bash
# Kontrollera vilka portar som används
lsof -i :8000  # Backend
lsof -i :3100  # Frontend  
lsof -i :7071  # NLU Agent

# Döda processes om nödvändigt
kill -9 <PID>
```

#### Module Import Errors
```bash
# Python path issues
export PYTHONPATH="${PYTHONPATH}:$(pwd)/server"

# Node modules issues
cd web && rm -rf node_modules && npm install
cd nlu-agent && rm -rf node_modules && npm install
```

#### Database Issues
```bash
# Reset development database
rm data/development.db
python server/app.py  # Kommer skapa ny databas
```

### Common Development Pitfalls

1. **Glömma aktivera virtual environment**
   ```bash
   # Kontrollera att du är i venv
   which python  # Ska peka till .venv/bin/python
   ```

2. **Environment variables inte laddade**
   ```bash
   # Kontrollera att .env läses
   python -c "import os; print(os.getenv('USE_HARMONY'))"
   ```

3. **Build cache issues**
   ```bash
   # Rensa alla caches
   cd web && npm run clean
   cd server && pip cache purge
   ```

---

**Happy coding! 🚀**

För ytterligare hjälp, se:
- [README.md](README.md) för grundläggande installation
- [API.md](API.md) för API-dokumentation  
- [DEPLOYMENT.md](DEPLOYMENT.md) för production deployment