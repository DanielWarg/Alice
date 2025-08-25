# 🚀 Alice - Development Guide

**Alice är en svensk AI-assistent med hybrid LLM-arkitektur och voice processing.**

---

## ⚡ **Quick Start**

```bash
# 1. Starta Alice (ett kommando)
./start_alice.sh

# 2. Öppna Alice
open http://localhost:3000
```

**Klart!** Alice körs nu med Ollama + OpenAI fallback.

---

## 📁 **Projektstruktur**

```
Alice/
├── README.md              # Projektöversikt
├── ALICE_ROADMAP.md       # Utvecklingsplan  
├── STARTUP.md             # Startinstruktioner
├── start_alice.sh         # Startup-script
├── .env.example           # Miljövariabler
│
├── server/                # FastAPI backend
│   ├── app.py            # Huvudserver
│   ├── llm/              # LLM-koordinator (Ollama+OpenAI)
│   ├── agent/            # Agent-system (policy+tools)
│   ├── core/             # Verktyg (väder, kalender)
│   └── run.py            # Server launcher
│
├── web/                   # Next.js frontend
│   ├── app/              # Next.js 13+ pages
│   ├── components/       # React-komponenter
│   └── package.json      # Dependencies
│
└── docs/                  # All dokumentation
    ├── ALICE_SYSTEM_OVERVIEW.md
    ├── B2_DOCUMENTATION.md
    └── ...
```

---

## 🔧 **Core Components**

### **LLM System** (`server/llm/`)
- **ModelManager**: Hybrid Ollama + OpenAI med circuit breaker
- **OllamaAdapter**: Lokal gpt-oss:20b för privata queries  
- **OpenAI Adapter**: Cloud fallback för performance
- **Health monitoring**: TTFT-mätning och failover-logik

### **Agent System** (`server/agent/`)
- **Policy**: FAST/DEEP routing baserat på intent
- **Tool Router**: Extraherar och kör verktygsanrop
- **Intent Classification**: Svenska NLU med privacy-nivåer

### **Voice Processing** (`web/components/`)
- **VoiceInterface**: Browser SpeechRecognition (sv-SE)
- **LLMStatusBadge**: Real-time LLM provider status
- **AudioProcessor**: B1+B2 voice systems (production ready)

---

## 🎯 **Development Workflow**

### **Backend Development**
```bash
# Starta backend i dev-läge
cd server
source ../.venv/bin/activate
python run.py

# Testa API
curl http://localhost:8000/api/v1/llm/status
```

### **Frontend Development**  
```bash
# Starta frontend
cd web
npm run dev

# Öppna browser
open http://localhost:3000
```

### **Testing**
```bash
# Backend tests
cd server && python -m pytest

# Frontend tests
cd web && npm test

# E2E tests
cd web && npm run test:e2e
```

---

## 🚀 **Current Status (Aug 2025)**

### ✅ **Production Ready**
- **B1**: Ambient Memory System (voice → memory → summaries)
- **B2**: Barge-in & Echo-skydd (ultra-low latency)  
- **Hybrid LLM**: Ollama primary + OpenAI fallback
- **Agent Core**: Autonomous workflow execution
- **Swedish NLU**: 89% accuracy med svenska idiom

### 🔄 **In Development**
- **B3**: Always-On Voice + Ambient Summaries
- **Production Polish**: Docker, SBOM, performance budgets
- **Vision Pipeline**: YOLO på Pi-satelliter

---

## 🐛 **Common Issues**

### **Startup Problems**
```bash
# Virtual environment trasig?
rm -rf .venv && python3 -m venv .venv
source .venv/bin/activate && pip install -r server/requirements.txt

# Port conflicts?
pkill -f "python.*run.py"
pkill -f "npm run dev"
```

### **Ollama Issues**  
```bash
# Ollama inte startad?
ollama serve

# Modell saknas?
ollama pull gpt-oss:20b
```

### **LLM Fallback Active**
Om Ollama timeout (>1.5s) switchas automatiskt till OpenAI fallback. Lägg till `OPENAI_API_KEY` i `.env` för full funktionalitet.

---

## 📚 **Mer Information**

- **System Architecture**: `docs/ALICE_SYSTEM_OVERVIEW.md`
- **B2 Voice System**: `docs/B2_DOCUMENTATION.md`  
- **API Reference**: `API.md`
- **Troubleshooting**: `TROUBLESHOOTING.md`
- **Full Documentation**: `docs/` directory

---

**🎯 För att bidra till Alice, läs `docs/CONTRIBUTING.md`**