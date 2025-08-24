# 🛠️ Alice Development Guide

Development guide for Alice AI Assistant Platform. Currently implements a working voice system with local AI, with plans for advanced hybrid architecture.

> **🚧 Important:** Read [PROJECT_STATUS.md](PROJECT_STATUS.md) first to understand current implementation vs future vision!

> **🇸🇪 Svenska:** [docs/sv/DEVELOPMENT.md](docs/sv/DEVELOPMENT.md) - Full Swedish version available

## 🚀 **Quick Start for Developers**

### Prerequisites (Current System)
- **Python 3.9+** - Backend FastAPI server
- **Node.js 18+** - Frontend Next.js application
- **Git** - Version control
- **Ollama with gpt-oss:20B** - Local AI model (required)
- **Modern browser** - For voice recognition (Chrome/Safari/Firefox)
- **OpenAI API Key** - Optional (for future hybrid features)

### Local Development Environment

1. **Clone and navigate:**
```bash
git clone https://github.com/DanielWarg/Alice.git
cd Alice
```

2. **Backend Setup:**
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r server/requirements.txt
```

3. **Frontend Setup:**
```bash
cd web
npm install
```

4. **AI Setup (Ollama):**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download model
ollama pull gpt-oss:20b

# Start Ollama
ollama serve
```

## 🔄 **Hybrid Development Philosophy**

Alice's hybrid architecture balances performance, privacy, and user experience. Understanding this philosophy is crucial for effective development:

### Core Principles

**🚀 Speed Where It Matters**
- Simple queries (greetings, weather, time) use OpenAI Realtime API for <300ms responses
- Complex reasoning and tool execution happen locally for privacy and control
- Smart intent routing ensures optimal performance for each interaction type

**🔒 Privacy-First Design** 
- Sensitive data never leaves the local system
- Personal information, documents, and complex conversations stay local
- Clear boundaries: only simple voice transcripts go to OpenAI
- User maintains full control over data sharing preferences

**🇸🇪 Swedish Cultural Authenticity**
- All Swedish language processing, cultural context, and personality remain local
- Local AI (gpt-oss:20B) handles cultural nuances and complex Swedish interactions
- OpenAI integration used only for basic conversational elements

### Development Guidelines

**When developing new features, consider:**

1. **Data Classification**: Is this personal/sensitive data? → Keep local
2. **Response Time**: Does this need <300ms response? → Consider fast path
3. **Complexity**: Multi-step reasoning or tool use? → Think path (local)
4. **Privacy Impact**: Could this compromise user privacy? → Always local

**Example Decision Tree:**
```
User Request: "Boka möte med Anna imorgon kl 14"
├── Contains personal data (Anna, calendar)? ✅ Yes
├── Requires tool execution (calendar)? ✅ Yes  
├── Complex multi-step process? ✅ Yes
└── Route Decision: 🏠 Think Path (Local AI + Tools)

User Request: "Vad är klockan?"
├── Simple factual query? ✅ Yes
├── No personal data? ✅ Correct
├── No tools needed? ✅ Correct
└── Route Decision: ☁️ Fast Path (OpenAI Realtime)
```

## 🏗️ **Project Structure**

```
Alice/
├── server/                 # FastAPI backend
│   ├── app.py             # Main application
│   ├── core/              # Core modules
│   │   ├── router.py      # Intent classification
│   │   ├── tool_registry.py # Tool management
│   │   ├── tool_specs.py  # Tool specifications
│   │   ├── calendar_service.py # Google Calendar
│   │   ├── gmail_service.py # Gmail integration
│   │   └── preflight.py   # System checks
│   ├── prompts/           # AI prompts in Swedish
│   ├── tests/             # Backend tests
│   ├── voice_stream.py    # Voice handling
│   ├── voice_stt.py       # Speech-to-Text
│   └── requirements.txt   # Python dependencies
├── web/                    # Next.js frontend
│   ├── app/               # Next.js 13+ app directory
│   ├── components/        # React components
│   ├── lib/               # Helper libraries
│   └── package.json       # Node.js dependencies
├── alice-tools/            # NLU and router system (TypeScript)
│   ├── src/router/        # Intent classification
│   ├── src/lexicon/       # Swedish commands
│   └── tests/             # Router tests
├── nlu-agent/              # Natural language understanding
├── tests/                  # Integration tests
├── docs/                   # Documentation
│   └── sv/                 # Swedish documentation
└── tools/                  # Tools and utilities
```

## 🔧 **Development Commands**

### Git & Repository
```bash
# Check remote
git remote -v

# Push to Alice repository
git push origin feature/harmony

# Pull from Alice repository
git pull origin feature/harmony
```

### Backend Development
```bash
# Start backend with hot-reload
cd server
source ../.venv/bin/activate
uvicorn app:app --host 127.0.0.1 --port 8000 --reload

# Run tests
python -m pytest tests/ -v

# Run specific tests
python -m pytest tests/test_harmony.py
python -m pytest tests/test_voice_system.py
```

### Frontend Development
```bash
# Start development server
cd web
npm run dev

# Build for production
npm run build

# Start in production mode
npm start
```

### Full Stack Development
```bash
# Terminal 1: Backend
cd server && source ../.venv/bin/activate && uvicorn app:app --reload

# Terminal 2: Frontend
cd web && npm run dev

# Terminal 3: Ollama
ollama serve
```

### Voice Pipeline Development
```bash
# Setup for voice development with HTTPS
cd web
npm install --save-dev @next/https
HTTPS=true npm run dev

# Voice debugging enabled
NEXT_PUBLIC_ENABLE_VOICE_DEBUG=true npm run dev

# Test OpenAI Realtime integration
curl -X GET http://localhost:3000/api/realtime/ephemeral

# Test TTS streaming
curl -X POST http://localhost:3000/api/tts/openai-stream \
  -H "Content-Type: application/json" \
  -d '{"text": "Test voice", "model": "tts-1"}'

# Voice component isolated tests
# Open: http://localhost:3000/voice
```

## 🧪 **Testing**

### Test Structure
```bash
tests/
├── harmony_e2e_test.py     # End-to-end Harmony tests
├── test_harmony_tools.py   # Tool integration
├── test_voice_system.py    # Voice system
└── results/                # Test results and reports
```

### Run Tests
```bash
# All tests
cd tests
python -m pytest -v

# Specific test categories
python -m pytest test_harmony_tools.py -v
python -m pytest test_voice_system.py -v

# With coverage
python -m pytest --cov=../server --cov-report=html
```

### Test Data
```bash
# Generate test data
cd tests
python generate_test_data.py

# Run stress tests
python stress_test_integrated.py
```

## 🔍 **Debugging**

### Backend Debug
```bash
# Start with debug logs
export LOG_LEVEL=DEBUG
cd server
python -c "import app; print('App loaded successfully')"

# Check endpoints
curl http://localhost:8000/api/health
curl http://localhost:8000/api/tools/spec
```

### Frontend Debug
```bash
# Browser Developer Tools
# - Console for JavaScript errors
# - Network tab for API calls
# - React DevTools for components

# Log to console
console.log('Debug info:', data);
```

### AI Debug
```bash
# Test Ollama connection
curl http://localhost:11434/api/tags

# Test model
ollama run gpt-oss:20b "Hello, testing connection"
```

## 📝 **Code Standards**

### Python
- **PEP 8** - Python style guide
- **Type hints** - Use `typing` module
- **Docstrings** - Google style docstrings
- **Black** - Automatic code formatting

```python
from typing import Dict, List, Optional
from pydantic import BaseModel

class ToolResponse(BaseModel):
    """Response model for tool execution."""
    
    success: bool
    message: str
    data: Optional[Dict] = None
    
    def __str__(self) -> str:
        return f"ToolResponse(success={self.success}, message='{self.message}')"
```

### TypeScript/JavaScript
- **ESLint** - Code quality
- **Prettier** - Code formatting
- **TypeScript** - Type safety
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

For detailed deployment information, see **[DEPLOYMENT.md](DEPLOYMENT.md)**.

### Quick Start for Local Production
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

## 🔧 **Tools and Utilities**

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

### 🎤 Voice & TTS Testing
```bash
# Test enhanced TTS system
cd server
python test_enhanced_tts.py

# Test Swedish calendar voice commands
python test_swedish_calendar_voice.py

# Test complete calendar integration
python test_calendar_integration.py
```

## 🎯 **Feature Development Guides**

### Enhanced TTS System
Alice's voice system now supports:
- **3 Personalities**: Alice (energetic), Formal (professional), Casual (relaxed)
- **5 Emotions**: Neutral, Happy, Calm, Confident, Friendly
- **MD5-based cache** for 3-10x faster response
- **Browser fallback** for seamless experience

**Test TTS:**
1. Start Alice (`./start_alice.sh`)
2. Open http://localhost:3001
3. Click "Test TTS" in VoiceBox
4. Test different personalities and emotions

### Google Calendar Integration
Alice can now handle calendar naturally in Swedish:
- **"Visa kalender"** (Show calendar) - Lists upcoming events
- **"Boka möte imorgon kl 14"** (Book meeting tomorrow at 2 PM) - Guides to event creation
- **Swedish date parsing** - "imorgon" (tomorrow), "nästa fredag" (next Friday), "kl 14:30" (at 2:30 PM)

**Test Calendar:**
1. VoiceBox: Say "Visa kalender"
2. Calendar panel: Click "+" for quick event creation
3. HUD: Click calendar icon for full modal
4. Voice + UI: Seamless integration between voice and visual calendar

### Voice Command Development
**Add new Swedish voice commands:**
```python
# In voice_calendar_nlu.py or equivalent
calendar_patterns = [
    r"boka (möte|träff) (.+)",
    r"visa (kalender|schemat)",  
    r"vad har jag (.+)",
    # Add your new pattern here
]
```

## 📚 **API Development**

### New Endpoints
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class NewEndpointRequest(BaseModel):
    data: str

@router.post("/api/new-endpoint")
async def new_endpoint(request: NewEndpointRequest):
    """New endpoint for functionality."""
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

## 🧠 **AI Development**

### Harmony Adapter
```python
# Add new tools
from core.tool_registry import register_tool

@register_tool("NEW_TOOL")
def new_tool_function(args: Dict) -> str:
    """Implement new tool."""
    return "Tool executed successfully"
```

### **Harmony Implementation Guide**

#### **Phase 0 – Baseline and safety line**
- [x] Create branch `feature/harmony`
- [x] Add env flags: `USE_HARMONY=false`, `USE_TOOLS=false`
- [x] Set up `.venv` in `server/` and freeze dependencies

#### **Phase 1 – Harmony adapter in server**
- [x] Create adapter layer in `server/app.py`
- [x] Model instructions: reasoning in `analysis`, tool calls in `commentary`, only responses in `final`
- [x] Parsing: extract only `final` channel to client
- [x] Add debug logging in dev: role + channel

#### **Phase 2 – Tool registry and validation**
- [x] Create `server/tools/registry.py` with tool specs
- [x] Implement execution with Pydantic validation
- [x] First tools: `PLAY`, `PAUSE`, `SET_VOLUME`, `SAY`/`DISPLAY`

#### **Phase 3 – Runtime for gpt-oss locally**
- [x] Choose runtime: Ollama adapter
- [x] Document the choice
- [x] Smoke test: model responds in correct channels

#### **Phase 4 – Prompts and policies**
- [x] Create `server/prompts/system_prompts.py` (Swedish)
- [x] Create developer prompt: follow Harmony; "no-tool-if-unsure"
- [x] Link into adapter layer

#### **Phase 5 – Router first**
- [x] Keep existing NLU/router as first choice
- [x] Add threshold `NLU_CONFIDENCE_THRESHOLD` in env
- [x] Lower confidence → send via Harmony + tool spec

#### **Phase 6 – Streaming and UI**
- [x] Server streams only `final` to client
- [x] Add light metadata to UI: `tool_called`, `tool_result`

#### **Phase 7 – Telemetry and logging**
- [x] Log p50/p95: time to first `final` token
- [x] Log: time `tool_call` → `tool_result`, validation errors
- [x] Log: router vs LLM hit rate

#### **Phase 8 – Evals**
- [x] Create 20 commands requiring tools
- [x] Create 20 pure chat questions
- [x] Create 10 cases with missing parameters
- [ ] Goal: ≥95% correct routing, 0% `analysis` leakage

#### **Phase 9 – Rollout in small PRs**
- [x] PR1: flags + Harmony adapter
- [x] PR2: tool registry + validation
- [x] PR3: activate `USE_TOOLS=true`
- [x] PR4: router first with threshold
- [x] PR5: telemetry + synthetic evals

#### **Phase 10 – Documentation and runbooks**
- [ ] Update `README.md`/`ARCHITECTURE.md`
- [ ] Runbook: adding new tools
- [ ] Troubleshooting: channel leakage, validation errors, latency spikes

### NLU Development
```typescript
// Add new intents in alice-tools
export function classifyNewIntent(input: string): IntentResult | null {
  const patterns = [
    /new pattern/i,
    /another pattern/i
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

## 🐛 **Common Issues**

### Backend Won't Start
```bash
# Check ports
lsof -i :8000

# Check dependencies
pip install -r requirements.txt

# Check Python version
python --version
```

### Frontend Build Fails
```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version
```

### Ollama Connection
```bash
# Check Ollama status
ollama list

# Restart Ollama
ollama serve

# Test model
ollama run gpt-oss:20b "test"
```

## 🤝 **Contributing**

### Pull Request Process
1. **Fork repository**
2. **Create feature branch**
3. **Implement functionality**
4. **Add tests**
5. **Update documentation**
6. **Submit PR**

### Code Review
- **Code quality** - Follows standards
- **Tests** - All tests pass
- **Documentation** - Updated
- **Performance** - No regression

## 📚 **Documentation**

- **[STARTUP.md](STARTUP.md)** - Exact startup guide
- **[README.md](README.md)** - Project overview and status
- **[VISION.md](VISION.md)** - Project vision and future features
- **[ALICE_ROADMAP.md](ALICE_ROADMAP.md)** - Detailed development plan
- **[API.md](API.md)** - Complete API documentation
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment and production guide

---

**Alice Development** - Build the future AI assistant! 🚀

*For additional help, see the documentation above or check the Swedish version in [docs/sv/DEVELOPMENT.md](docs/sv/DEVELOPMENT.md).*

# 🎤 VoiceBox Integration & Planning

## Component Overview

**VoiceBox** is an advanced voice component that replaces the old simple voice function in Alice HUD. The component is designed to provide a visual representation of audio input with real-time bars and integrated speech recognition.

### Technical Specifications

- **Bars**: Configurable (default: 5-7 bars)
- **Audio Processing**: WebAudio API with AnalyserNode
- **Speech Recognition**: Web Speech API (Swedish)
- **Fallback modes**: Demo and pseudo mode if mic not available
- **Styling**: Customized for Alice's HUD theme (cyan/blue)

### Component Structure

```typescript
interface VoiceBoxProps {
  bars?: number                    // Number of bars (default: 7)
  smoothing?: number              // EMA smoothing (0.15)
  minScale?: number               // Minimum scale (0.1)
  label?: string                  // Label text
  allowDemo?: boolean             // Demo mode
  allowPseudo?: boolean           // Pseudo mode
  onVoiceInput?: (text: string) => void  // Callback
}
```

## Integration Plans

### 1. Reference Implementation (Current)
- **Placement**: VOICE panel (left column)
- **Status**: ✅ Works correctly
- **Functionality**: 
  - 5 bars with audio visualization
  - "Start mic" button
  - Voice input added to journal
  - "Add to To-do" functionality

### 2. ALICE CORE Integration (Planned)
- **Goal**: Replace sphere in ALICE CORE with VoiceBox
- **Placement**: Centered in ALICE CORE panel
- **Identified challenges**:
  - ✅ Component renders correctly with audio bars
  - ❌ Placement is wrong - not where we want it
  - ❌ Shape is wrong - maybe too narrow, too tall, or wrong position
  - ❌ "Start mic" button placed incorrectly

### 3. Troubleshooting & Solutions

#### Problem 1: Wrong placement
- **Symptom**: VoiceBox not positioned where we want it in ALICE CORE
- **Possible causes**:
  - CSS positioning (top, left, transform)
  - Container structure in ALICE CORE
  - Z-index or overflow issues

#### Problem 2: Wrong shape
- **Symptom**: VoiceBox is too narrow, too tall, or has wrong proportions
- **Solution**: Copy exact same attributes as reference component

#### Problem 3: Button placement
- **Symptom**: "Start mic" button positioned incorrectly
- **Solution**: Adjust positioning within VoiceBox component

### 4. Recommended Approach

1. **Keep reference component** in VOICE panel
2. **Copy exact same attributes** to ALICE CORE version
3. **Test incrementally** - first placement, then styling
4. **Use same container structure** that works in VOICE panel

### 5. Future Improvements

- **TTS Integration**: Let Alice respond with voice
- **WebSocket Integration**: Real-time communication with backend
- **Voice Commands**: Integrate with Alice's tool system
- **Custom Styling**: Customize for different HUD themes

## Current Status

- ✅ **VoiceBox component**: Works correctly
- ✅ **Reference implementation**: Visible in VOICE panel
- ❌ **ALICE CORE integration**: Requires troubleshooting
- 🔄 **Planning**: Under development

## Next Steps

1. **Troubleshoot ALICE CORE integration**
2. **Copy working attributes**
3. **Test placement and styling**
4. **Integrate with Alice's voice system**

---

*Last updated: August 21, 2024*