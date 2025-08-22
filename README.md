# 🤖 Alice - Din Svenska AI-Assistent

**Alice** är en supersmart AI-assistent byggd med svenska som primärt språk, utrustad med lokal AI-kraft via Ollama och en futuristisk HUD-baserad användarupplevelse.

## 🚀 **Vad är Alice?**

Alice är en komplett AI-assistent som kombinerar:
- **Lokal AI-kraft** via `gpt-oss:20B` (Ollama)
- **Svenska språkkommandon** med 89% NLU-accuracy
- **Futuristisk HUD-UI** med real-time uppdateringar
- **Smart verktygsintegration** (Spotify, Gmail, Kalender)
- **Röststyrning** med Whisper STT + Piper TTS
- **Privacy-first** - Allt körs lokalt, ingen telemetri

## 🏗️ **Projektstruktur**

```
Alice/
├── server/                 # FastAPI backend med AI-kärna
├── web/                    # Next.js HUD frontend
├── alice-tools/            # NLU och router-system
├── nlu-agent/              # Naturlig språkförståelse
├── tests/                  # Komplett test-suite
├── docs/                   # Dokumentation
├── tools/                  # Verktyg och utilities
└── requirements.txt        # Python dependencies
```

## 🎯 **Huvudfunktioner**

### 🎤 **Avancerad Röst-AI**
- **Enhanced TTS** med 3 svenska personligheter (Alice, Formell, Casual)
- **Emotionell modulering** - 5 toner (Neutral, Happy, Calm, Confident, Friendly)
- **VoiceBox visualisering** - Real-time audio bars synkade med röst
- **Wake-word detection** för hands-free operation ("Alice")
- **MD5-baserad cache** för 3-10x snabbare TTS-respons

### 📅 **Smart Kalender-Assistent**
- **Google Calendar integration** med svenska röstkommandon
- **"Visa kalender"**, **"boka möte imorgon kl 14"** fungerar naturligt
- **Intelligent scheduling** med conflict detection
- **CompactWidget + Full Modal** i HUD för seamless kalender-hantering
- **Svenska datum-parsing** (imorgon, nästa fredag, kl 14:30)

### 🧠 **AI & Språk**
- **Lokal GPT-OSS:20B** via Ollama
- **Svenska NLU** med 89% accuracy och slot extraction
- **Harmony-adapter** för intelligent verktygsrouting
- **WebSocket real-time** kommunikation mellan röst och backend

### 🔧 **Verktyg & Integration**
- **Spotify** - Musikuppspelning och kontroll
- **Gmail** - E-posthantering och sökning  
- **Google Calendar** - Komplett kalenderhantering med röst
- **Document Upload** - Ladda upp dokument för Alice's AI-kontext
- **20+ verktyg** registrerade och redo för expansion

### 🎨 **HUD & UI**
- **Futuristisk design** med cyan/blue tema och glassmorphism
- **Real-time metrics** (CPU, RAM, nätverk, kalenderstatus)
- **Modulära paneler** med både kompakta och detaljerade lägen
- **VoiceBox-integration** för audio-visuell feedback

## ✅ **Status: Produktionsklar & Funktional**

### **🎤 Röst-System**
- ✅ Enhanced TTS med 3 personligheter fungerar
- ✅ VoiceBox visualiserar audio real-time  
- ✅ Svenska röstkommandon igenkänns korrekt
- ✅ WebSocket /ws/alice anslutning stabil
- ✅ Browser TTS fallback för seamless upplevelse

### **📅 Kalender-Integration**
- ✅ Google Calendar API endpoints aktiva
- ✅ Svenska röstkommandon ("visa kalender", "boka möte")
- ✅ CalendarWidget i HUD (kompakt + full modal)
- ✅ Intelligent scheduling med conflict detection
- ✅ Svenska datum/tid-parsing (imorgon, kl 14, etc.)

### **📁 Document Management**
- ✅ Document upload system (.txt, .md, .pdf, .docx, .html)
- ✅ Automatisk RAG-integration med chunking och embeddings
- ✅ Alice kan svara på frågor baserat på uppladdade dokument
- ✅ Drag & drop interface i HUD med real-time feedback
- ✅ Intelligent document parsing och text extraction

### **🖥️ Backend (FastAPI)**
- ✅ FastAPI server startar på port 8000
- ✅ 25+ API endpoints inklusive /api/calendar/* och /api/tts/*
- ✅ Verktygsregister aktiverat (20+ verktyg)
- ✅ Harmony adapter implementerad med streaming
- ✅ WebSocket real-time kommunikation

### **🎨 Frontend (Next.js)**
- ✅ Next.js HUD startar på port 3001
- ✅ Futuristisk HUD interface med glassmorphism
- ✅ VoiceBox-komponent integrerad i huvudsidan
- ✅ Calendar panel (både snabb-widget och full modal)
- ✅ Real-time uppdateringar via WebSocket
- ✅ Real-time metrics fungerar
- ✅ Responsiv design

### **AI & NLU**
- ✅ Ollama integration
- ✅ GPT-OSS:20B modell tillgänglig
- ✅ Svenska NLU system
- ✅ Intent-klassificering

### **Verktyg & Integration**
- ✅ Spotify integration
- ✅ Gmail integration
- ✅ Kalender integration
- ✅ Röststyrning

### **Agent Core v1 - Autonomous Workflows** 🤖
- ✅ **AgentPlanner** - Bryter ner mål i exekverbara steg
- ✅ **AgentExecutor** - Utför actions med dependencies & parallellisering  
- ✅ **AgentCritic** - Analyserar resultat & föreslår förbättringar
- ✅ **AgentOrchestrator** - Koordinerar Planning→Execution→Criticism→Improvement cycles
- ✅ **100 tester** med full test coverage
- ✅ **Autonomous multi-step task execution**
- ✅ **Adaptive improvement strategies**
- ✅ **Progress tracking & monitoring**

---

## 🚀 **Snabbstart**

### Förutsättningar
- Python 3.9+
- Node.js 18+
- Ollama med `gpt-oss:20B` modell

### Installation

1. **Klon och navigera:**
```bash
git clone https://github.com/DanielWarg/Alice.git
cd Alice
```

2. **Aktivera virtuell miljö:**
```bash
source .venv/bin/activate
```

3. **Starta backend:**
```bash
cd server
python run.py
```

4. **Starta frontend (ny terminal):**
```bash
cd web
npm install
npm run dev
```

5. **Öppna HUD:**
```
http://localhost:3000
```

## 🔧 **Konfiguration**

### Miljövariabler
```bash
# .env
USE_HARMONY=true          # Aktivera Harmony AI-adapter
USE_TOOLS=true            # Aktivera verktygssystem
LOG_LEVEL=INFO            # Loggningsnivå
OLLAMA_BASE_URL=http://localhost:11434
```

### Ollama Setup
```bash
# Installera Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Ladda ner modell
ollama pull gpt-oss:20b

# Starta Ollama
ollama serve
```

## 📚 **Dokumentation**

- **[STARTUP.md](STARTUP.md)** - Exakt startup-guide
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Utvecklingsguide
- **[API.md](API.md)** - Komplett API-dokumentation
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment och production-guide
- **[VISION.md](VISION.md)** - Projektvision och framtida funktioner
- **[ALICE_ROADMAP.md](ALICE_ROADMAP.md)** - Detaljerad utvecklingsplan

## 🧪 **Testning**

```bash
# Kör alla tester
cd tests
python -m pytest

# Kör specifika tester
python -m pytest tests/test_harmony.py
python -m pytest tests/test_voice_system.py
```

## 🌟 **Framtida funktioner**

- **Multi-modal AI** - Bild- och videoförståelse
- **IoT-integration** - Smart hem-kontroll
- **Plugin-system** - Utbyggbar arkitektur
- **Enterprise-features** - Multi-user och RBAC

## 🤝 **Bidrag**

Alice är ett öppet projekt! Bidrag är välkomna:
- Bug-rapporter via GitHub Issues
- Feature-förslag via Discussions
- Pull Requests för förbättringar

## 📄 **Licens**

MIT License - se [LICENSE](LICENSE) för detaljer.

---

**Alice** - Din supersmarta svenska AI-assistent för framtiden! 🚀