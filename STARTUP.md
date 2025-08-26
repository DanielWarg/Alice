# 🚀 Alice Project - Snabbstart Guide

**Kom igång med Alice - men läs detta först om du är ny!**

---

## 🚨 **VIKTIGT: Läs detta först om du är ny utvecklare**

**Alice har imponerande funktionalitet men röstpipelinen är instabil.**

🟢 **Vad som fungerar bra:**
- Text-chat med svenska svar (2-4s responstid) 
- Grundläggande röstinput och TTS
- Spotify, kalendrar, verktyg

🔴 **Kända problem med röst:**
- Echo loops (Alice hör sin egen röst)
- Instabila test-gränssnitt (knappar fungerar inte)
- "Stökigt" beteende i konversationer
- Partiell detektering kan vara opålitlig

**🎯 Om rösten är stökig → hoppa direkt till [🔧 Troubleshooting](#-troubleshooting-röstproblem)**

---

## 🎯 **Vad är Alice? (Realistisk beskrivning)**

Alice är en **privat svenska AI-assistent** med:
- 🎙️ **Experimentell röstrespons** (~700ms när det fungerar) med LiveKit-stil streaming  
- 🤖 **Stabil lokal AI** med gpt-oss:20b (ingen data skickas till molnet)
- 🇸🇪 **Pålitlig svenska** språkstöd och kulturell förståelse
- 🛠️ **Fungerande verktyg** för kalender, väder, Spotify, Gmail m.m.

---

## 📋 **Snabb-check (30 sekunder)**

Kör detta först för att se om allt är installerat:

```bash
echo "🔍 Checking dependencies..." && \
python3 --version && \
node --version && \
ollama --version && \
echo "✅ All prerequisites found!"
```

**Saknar du något?** Se [Installation](#-installation-saknas-något) längre ner.

---

## ⚡ **ENKLASTE STARTEN (2 minuter)**

### 1. Navigera till projektmappen
```bash
cd /Users/evil/Desktop/EVIL/PROJECT/Alice
```

### 2. Kör startup-scriptet
```bash
./start_alice.sh
```

### 3. Vänta på "All systems ready!" meddelandet

### 4. Öppna Alice
```bash
open http://localhost:3000
```

**🎉 Klart! Alice körs nu med sub-sekund röstrespons.**

---

## 🎙️ **Testa Röstfunktionen**

När Alice är igång, testa de nya röstfunktionerna:

### LiveKit-Stil Streaming Voice
1. **Öppna test-gränssnittet**: `open test_streaming_voice.html`
2. **Klicka "🎤 Start Recording"**
3. **Säg**: "Vad är det för väder i Göteborg idag"
4. **Se TTFA-mätning**: Borde visa ~700ms till första ljud

### I Huvudappen
1. **Öppna**: http://localhost:3000
2. **Klicka röstknappen** (eller säg "Hej Alice")
3. **Testa svenska kommandon**: 
   - "Vad är klockan?"
   - "Skapa ett möte imorgon"
   - "Spela musik"

---

## 🔧 **Troubleshooting röstproblem**

### Om rösten är "stökig" eller ekar
```bash
# 1. Starta om Alice helt
pkill -f "python.*run.py"; pkill -f "npm run dev"; pkill -f "ollama serve"
sleep 5
./start_alice.sh

# 2. Testa specifikt röstpipelinen
open test_streaming_voice.html
# Klicka Connect → Start Recording
# Om knappar inte fungerar = känt problem
```

### Om test-sidan inte fungerar
- **Known Issue**: Test-knapparna är trasiga
- **Workaround**: Använd huvudappen http://localhost:3000
- **Focus**: Vi jobbar på att fixa detta

### Om echo loops (Alice hör sig själv)
```bash
# Temporary fix: använd headphones istället för speakers
# Eller muta micken manuellt under Alice's svar
# Detta är vårt #1 problem att lösa
```

### Rapportera röstproblem
Om du hittar nya röstproblem, dokumentera:
1. Vad du sa
2. Vad Alice hörde (transcript)
3. Vad som hände (echo/dubbelsvar/nothing)
4. Browser & OS version

---

## 🛠️ **Manual Setup (om scriptet inte fungerar)**

### Snabb parallell-start (avancerat)
```bash
cd /Users/evil/Desktop/EVIL/PROJECT/Alice

# Starta allt parallellt för snabbaste uppstart
(cd server && source ../.venv/bin/activate && python3 -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload) &
(cd web && npm run dev) &
(ollama serve > /dev/null 2>&1) &

# Vänta på att allt startar
sleep 10

echo "🔍 System Status:"
curl -s http://localhost:8000/api/v1/llm/status >/dev/null && echo "✅ Backend ready"
curl -s http://localhost:3000 >/dev/null && echo "✅ Frontend ready" 
curl -s http://localhost:11434/api/tags >/dev/null && echo "✅ Ollama ready"

echo "🎉 Alice ready at: http://localhost:3000"
```

### Steg-för-steg troubleshooting
```bash
# 1. Fixa dependencies
cd /Users/evil/Desktop/EVIL/PROJECT/Alice
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
cd web && npm install && cd ..

# 2. Starta backend
cd server && python3 -m uvicorn app:app --host 127.0.0.1 --port 8000 &

# 3. Starta frontend
cd web && npm run dev &

# 4. Kontrollera Ollama
ollama serve > /dev/null 2>&1 &
```

---

## 🎯 **Slutkontroll - Allt ska fungera**

Kör denna verifiering:

```bash
echo "🔍 Final System Check:"
curl -s http://localhost:8000/api/tools/spec >/dev/null && echo "✅ Backend OK" || echo "❌ Backend FAIL"
curl -s http://localhost:3000 >/dev/null && echo "✅ Frontend OK" || echo "❌ Frontend FAIL"  
curl -s http://localhost:11434/api/tags >/dev/null && echo "✅ AI OK" || echo "❌ AI FAIL"
curl -s http://localhost:8000/api/v1/llm/status >/dev/null && echo "✅ LLM System OK" || echo "❌ LLM System FAIL"
```

**Förväntad output:**
```
🔍 Final System Check:
✅ Backend OK
✅ Frontend OK
✅ AI OK
✅ LLM System OK
```

---

## 🌐 **Öppna Alice**

När alla ✅ visas, öppna webbläsaren:

**🎯 http://localhost:3000**

Du ska nu se:
- 🎨 **Alice HUD** med glassmorphism-design
- 🤖 **LLM Status Badge** som visar "gpt-oss:20b (healthy)"
- 🎙️ **VoiceStreamClient** för LiveKit-stil streaming voice
- 📊 **TTFA metrics** och realtidsprestanda
- ⚡ **Sub-sekund röstrespons** (~700ms Time-To-First-Audio)

---

## 🚨 **Om något inte fungerar**

### Port-konflikter
```bash
# Kontrollera vilka processer som använder portarna
lsof -i :8000 && lsof -i :3000 && lsof -i :11434
# Döda konflikterande processer
kill -9 <PID>
```

### Virtual Environment-problem
```bash
# Total reset av venv
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt python-multipart httpx
```

### Dependencies-problem
```bash
# Frontend dependencies
cd web && rm -rf node_modules package-lock.json && npm install

# Backend dependencies  
source .venv/bin/activate
pip install --upgrade pip
pip install -r server/requirements.txt python-multipart httpx
```

---

## 🔄 **Starta Om Allt**

Om du behöver starta om hela systemet:

```bash
# Stoppa allt
pkill -f "python.*run.py"; pkill -f "npm run dev"; pkill -f "ollama serve"

# Vänta 5 sekunder
sleep 5

# Starta om med manual setup ovan
```

---

## 📱 **Smart Startup Script**

Skapa detta för framtida one-click start:

```bash
#!/bin/bash
# save as: ~/alice-start.sh

cd /Users/evil/Desktop/EVIL/PROJECT/Alice

echo "🚀 Starting Alice Project..."

# Fix venv if broken
source .venv/bin/activate 2>/dev/null || {
  echo "🔧 Recreating virtual environment..."
  rm -rf .venv
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r server/requirements.txt python-multipart httpx
}

# Clean up ports
pkill -f "python.*run.py" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
sleep 2

# Start backend
cd server && python run.py &
sleep 5

# Start frontend  
cd ../web && npm run dev &
sleep 5

# Verify all systems
echo "🔍 System Status:"
curl -s http://localhost:8000/api/tools/spec >/dev/null && echo "✅ Backend" || echo "❌ Backend"
curl -s http://localhost:3000 >/dev/null && echo "✅ Frontend" || echo "❌ Frontend"
curl -s http://localhost:11434/api/tags >/dev/null && echo "✅ AI" || echo "❌ AI"

echo ""
echo "🎉 Alice is ready!"
echo "🌐 Open: http://localhost:3000"
```

**Gör det körbart:**
```bash
chmod +x ~/alice-start.sh
```

**Kör Alice när som helst:**
```bash
~/alice-start.sh
```

---

---

## 💾 **Installation (saknas något?)**

### Python 3.9+
```bash
# macOS med Homebrew
brew install python3

# Kontrollera version
python3 --version  # Bör vara 3.9+
```

### Node.js 18+
```bash
# macOS med Homebrew  
brew install node

# Kontrollera version
node --version      # Bör vara 18+
```

### Ollama + gpt-oss modell
```bash
# Installera Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Ladda ner gpt-oss:20b modell (en gång)
ollama pull gpt-oss:20b

# Kontrollera att modellen finns
ollama list | grep gpt-oss
```

### Virtuell miljö (Python dependencies)
```bash
cd /Users/evil/Desktop/EVIL/PROJECT/Alice
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
```

---

## 🚀 **Prestanda & Förbättringar**

### Alice v2.1 vs v1.0 Jämförelse
| Metric | v1 Batch | v2.1 LiveKit-Style | Förbättring |
|--------|----------|---------------------|-------------|
| Första ljudet | ~5.5s | ~700ms | **7.8x snabbare** |
| Röstprocessing | Väntar på slutversion | Stabil partial (250ms) | **Real-tid** |
| TTS Audio | Hela meningar | Micro-chunks (3-5 ord) | **Progressiv** |
| Echo-kontroll | Enkel blockering | Smart mute/unmute | **Sofistikerat** |

### Test Streaming Voice Funktioner
- ✅ **Stabil Partial Detection** - Triggar på 250ms stabilitet
- ✅ **Micro-Chunked TTS** - 3-5 ord chunks med 20ms delay  
- ✅ **TTFA Mätning** - Real-tid performance metrics
- ✅ **Smart Echo-kontroll** - Mute under TTS-uppspelning

---

**🎯 Nu borde Alice starta på 2 minuter med sub-sekund röstrespons!**

För teknisk support, se [VOICE_PIPELINE_STATUS.md](VOICE_PIPELINE_STATUS.md) eller [docs/VOICE_SETUP.md](docs/VOICE_SETUP.md).