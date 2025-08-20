```
       █████╗ ██╗     ██╗ ██████╗███████╗
      ██╔══██╗██║     ██║██╔════╝██╔════╝
      ███████║██║     ██║██║     █████╗  
      ██╔══██║██║     ██║██║     ██╔══╝  
      ██║  ██║███████╗██║╚██████╗███████╗
      ╚═╝  ╚═╝╚══════╝╚═╝ ╚═════╝╚══════╝
             The Ultimate AI Assistant
```

──────────────────────────────

# 🚀 ALICE HUD — Local AI with Voice, Vision & Memory

*"Your personal AI. Local. Private. Limitless."*

---

🌌 Vision
Alice HUD is a self-hosted AI powerhouse.
It listens, speaks, understands Swedish commands with precision, remembers context, and controls your world — from media to email, calendars, IoT, and beyond — all inside a sleek, futuristic heads-up display.

Built for speed, privacy, and total control — no cloud lock-in, no compromises.

<div style="background-color:#0d1117;padding:20px;border-radius:10px;text-align:center;"> <img src="docs/image.png" alt="Alice HUD — Local AI with Voice, Vision & Memory in a Futuristic Interface" style="max-width:100%;border-radius:8px;"> <p style="color:#8b949e;font-style:italic;">Preview of the Alice HUD interface</p> </div>

---

## ✨ Features

### 🧠 **Supersmart AI Core**
* **Deep Understanding** — Natural svenska conversations with full context retention
* **RAG Memory System** — Remembers everything, retrieves intelligently
* **Predictive Analysis** — Learns patterns, suggests next steps
* **Advanced Reasoning** — Complex multi-step problem solving

### 🎯 **Intelligent Tools**
* **Email Intelligence** — Smart sorting, drafting, scheduling responses
* **Calendar Master** — Automated scheduling, conflict resolution, meeting prep
* **Project Planner** — Goal setting, milestone tracking, resource allocation
* **Data Synthesizer** — Report generation, trend analysis, insights
* **Predictive Assistant** — Anticipates needs, proactive suggestions

### 🎨 **Futuristic Interface**
* **HUD Panels** — System stats, weather, tasks, diagnostics, insights
* **Overlay Modules** — Calendar, email, finance, reminders, analytics
* **Voice Control** — Natural Swedish commands with hybrid API/local processing
* **Safe Boot Mode** — Privacy controls, instant disable
* **PWA Ready** — Installable desktop experience
* **Sensor Network** — Raspberry Pi probes för vision och audio

---

## 🛠 Tech Stack

**Frontend:** Next.js 15, React 19, Tailwind CSS v4, PWA-enabled
**Backend:** FastAPI, Harmony Response Format, SQLite memory, streaming
**AI Core:** `gpt-oss:20B` (Ollama), RAG retrieval, Whisper STT, Piper TTS
**Intelligence:** NLU routing, tool calling, memory synthesis, predictive modeling

*Chosen for cutting-edge AI capabilities, local-first execution, and zero-latency responsiveness.*

---

## ⚡ Quick Start

### Backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.app:app --host 127.0.0.1 --port 8000
```

### Frontend
```bash
cd web
npm install
npm run dev -- -p 3100
```

Then open: [http://localhost:3100](http://localhost:3100)

### AI Setup
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download Alice's brain
ollama pull gpt-oss:20b

# Start local AI
ollama serve
```

---

## 🎵 Spotify Setup

1. Create an app in [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).
2. Add redirect URI: `http://127.0.0.1:3100/spotify/callback`
3. Create `.env` in project root:
```bash
SPOTIFY_CLIENT_ID=xxxx
SPOTIFY_CLIENT_SECRET=xxxx
SPOTIFY_REDIRECT_URI=http://127.0.0.1:3100/spotify/callback
```
4. Start backend, open HUD → Connect Spotify.

---

## 📂 Structure

```
alice/
├─ VISION.md           # This file
├─ README.md           # Technical documentation
├─ API.md              # Complete API reference
├─ DEPLOYMENT.md       # Production setup guide
├─ DEVELOPMENT.md      # Developer handbook
├─ server/             # FastAPI backend + AI core
│  ├─ core/           # NLU, tools, memory system
│  ├─ prompts/        # AI personality & instructions
│  └─ models/         # Local AI models (TTS, etc.)
├─ web/               # Next.js HUD frontend
├─ alice-tools/       # Extensible tool library
├─ nlu-agent/         # Natural language understanding
└─ tests/             # Comprehensive test suite
```

---

## 🧠 Master Development Roadmap

### Phase 1 — AI Core Completion ⚡
* **Harmony Integration** — Complete local gpt-oss:20B setup
* **Memory Enhancement** — Advanced RAG with semantic search
* **Tool Expansion** — Email, calendar, planning, analytics tools
* **Swedish NLU** — Perfect language understanding
* **Evaluation Suite** — ≥95% accuracy on complex tasks

### Phase 2 — Supersmart Features 🎯
* **Predictive Engine** — Pattern recognition, proactive suggestions  
* **Deep Planning** — Multi-step project management
* **Synthesis Master** — Intelligent report generation
* **Context Mastery** — Long-term conversation memory
* **Learning System** — Continuous improvement from usage

### Phase 3 — Advanced Intelligence 🚀
* **Multi-modal AI** — Vision, document analysis
* **IoT Integration** — Smart home control
* **Workflow Automation** — Complex task orchestration
* **Collaborative AI** — Team assistance features
* **External Integrations** — CRM, productivity tools

### Phase 4 — Optimization & Scale 📈
* **Performance Tuning** — Sub-100ms response times
* **Advanced UI/UX** — Immersive HUD experience
* **Mobile Companion** — Cross-platform sync
* **Enterprise Features** — Team deployments
* **Plugin Ecosystem** — Community extensions

---

## 🎯 Core Principles

* **Local-First** — Your data never leaves your machine
* **Privacy by Design** — No tracking, no telemetry, pure local AI
* **Speed Above All** — Sub-second response times for everything
* **Swedish-Native** — Perfect understanding of Swedish context and nuance
* **Infinitely Extensible** — Plugin architecture for unlimited growth
* **Production Ready** — Enterprise-grade reliability and security

---

## 🛡 Fallback Strategy

**Latest stable Alice version:**
```bash
git reset --hard alice-stable-harmony && git clean -fd
```

**Emergency rollback:**
```bash
git reset --hard alice-basic-working && git clean -fd
```

---

## 🤝 Contributing

We welcome contributions to make Alice even smarter!

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/super-intelligence`)
3. Commit your changes (`git commit -m 'Add mind-reading capability'`)
4. Push to the branch (`git push origin feature/super-intelligence`)
5. Open a Pull Request

---

## 📜 License

MIT License - Build amazing things with Alice!

---

*Alice - Where artificial intelligence meets human potential. 🤖✨*