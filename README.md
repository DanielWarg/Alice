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

### AI & Språk
- **Lokal GPT-OSS:20B** via Ollama
- **Svenska NLU** med avancerad slot extraction
- **Harmony-adapter** för intelligent verktygsrouting
- **Röststyrning** med svenska kommandon

### Verktyg & Integration
- **Spotify** - Musikuppspelning och kontroll
- **Gmail** - E-posthantering och sökning
- **Google Calendar** - Kalenderhantering
- **Smart Home** - IoT-integration (framtida)

### HUD & UI
- **Futuristisk design** med cyan/blue tema
- **Real-time metrics** (CPU, RAM, nätverk)
- **Modulära paneler** (kalender, mail, finans)
- **Responsiv design** för alla enheter

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
- **[STATUS.md](STATUS.md)** - Status och utvecklingsplan
- **[API.md](API.md)** - Komplett API-dokumentation
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment och production-guide
- **[VISION.md](VISION.md)** - Projektvision och roadmap
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