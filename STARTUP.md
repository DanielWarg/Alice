# 🚀 Alice Project - Exakt Startguide

**Denna guide visar exakt hur du startar Alice-projektet från början till slut.**

---

## 📋 **Förutsättningar**

Kontrollera att du har följande installerade:
- **Python 3.9+** - `python3 --version`
- **Node.js 18+** - `node --version`
- **Git** - `git --version`
- **Ollama** - `ollama --version`

---

## 🏗️ **Steg 1: Projektstruktur**

Projektet har nu en ren struktur:
```
Alice/                    # Root-katalog
├── server/              # FastAPI backend
├── web/                 # Next.js frontend
├── alice-tools/         # NLU system
├── nlu-agent/           # Språkförståelse
├── .venv/               # Python virtuell miljö
└── requirements.txt     # Python dependencies
```

---

## 🐍 **Steg 2: Starta Backend (FastAPI)**

### 2.1 Aktivera virtuell miljö
```bash
cd /Users/evil/Desktop/EVIL/PROJECT/Alice
source .venv/bin/activate
```

**Förväntad output:**
```bash
(.venv) evil@MacBook-Pro-som-tillhor-EVIL Alice %
```

### 2.2 Installera Python dependencies (endast första gången)
```bash
pip3 install -r server/requirements.txt
pip3 install python-multipart
```

**Viktigt:** `python-multipart` krävs för filuppladdningar och måste installeras separat.

### 2.3 Verifiera verktygskonsistens
```bash
# Kontrollera att alla verktyg är synkroniserade
cd server
python3 -c "from core.tool_specs import enabled_tools; print('Aktiverade verktyg:', enabled_tools())"
```

**Förväntad output:** Lista med alla verktyg (PLAY, PAUSE, STOP, NEXT, PREV, etc.)

### 2.4 Starta backend-servern
```bash
cd server
python3 run.py
```

**Förväntad output:**
```bash
INFO:     Will watch for changes in these directories: ['/Users/evil/Desktop/EVIL/PROJECT/Alice/server']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [XXXXX] using WatchFiles
```

### 2.5 Verifiera backend (ny terminal)
```bash
curl http://localhost:8000/api/tools/spec
```

**Förväntad output:** JSON med verktygsspecifikationer

---

## ⚛️ **Steg 3: Starta Frontend (Next.js)**

### 3.1 Öppna ny terminal (behåll backend igång)
```bash
cd /Users/evil/Desktop/EVIL/PROJECT/Alice/web
```

### 3.2 Installera Node.js dependencies (endast första gången)
```bash
npm install
```

### 3.3 Starta frontend-servern
```bash
npm run dev
```

**Förväntad output:**
```bash
> web@0.1.0 dev
> next dev

   ▲ Next.js 15.4.6
   - Local:        http://localhost:3000
   - Network:      http://192.168.0.XXX:3000

 ✓ Starting...
 ✓ Ready in X.Xs
 ✓ Compiled / in XXXXms
```

### 3.4 Verifiera frontend
Öppna webbläsaren: **http://localhost:3000**

---

## 🤖 **Steg 4: Starta AI (Ollama)**

### 4.1 Öppna tredje terminal (behåll backend och frontend igång)
```bash
ollama serve
```

**Förväntad output:**
```bash
Starting Ollama server...
```

### 4.2 Verifiera Ollama-anslutning
```bash
curl http://localhost:11434/api/tags
```

**Förväntad output:** JSON med tillgängliga modeller inklusive `gpt-oss:20b`

### 4.3 Testa AI-modell
```bash
ollama run gpt-oss:20b "Hej, testar Alice"
```

---

## 🔧 **Steg 5: Verifiera Allt Fungerar**

### 5.1 Backend (Terminal 1)
```bash
curl http://localhost:8000/api/tools/spec
# Ska returnera JSON med verktyg
```

### 5.2 Frontend (Terminal 2)
```bash
curl http://localhost:3000
# Ska returnera HTML
```

### 5.3 AI (Terminal 3)
```bash
curl http://localhost:11434/api/tags
# Ska returnera JSON med modeller
```

---

## 🚨 **Vanliga Problem och Lösningar**

### Problem 1: Port 8000 redan i användning
```bash
# Kontrollera vad som använder porten
lsof -i :8000

# Döda processen
kill -9 <PID>

# Starta om backend
cd server && python3 run.py
```

### Problem 2: Port 3000 redan i användning
```bash
# Kontrollera vad som använder porten
lsof -i :3000

# Döda processen
kill -9 <PID>

# Starta om frontend
cd web && npm run dev
```

### Problem 3: Python-multipart saknas
```bash
# Installera saknad dependency
pip3 install python-multipart

# Starta om backend
cd server && python3 run.py
```

### Problem 4: Next.js-moduler saknas
```bash
# Rensa och installera om
cd web
rm -rf node_modules package-lock.json
npm install

# Starta om frontend
npm run dev
```

### Problem 5: Ollama-port redan i användning
```bash
# Kontrollera Ollama-status
ollama list

# Starta om Ollama
ollama serve
```

---

## 📱 **Komplett Startup-script**

För snabb start, skapa detta script:

```bash
#!/bin/bash
# start_alice.sh

echo "🚀 Starting Alice Project..."

# Terminal 1: Backend
echo "🐍 Starting Backend..."
cd /Users/evil/Desktop/EVIL/PROJECT/Alice
source .venv/bin/activate
cd server
python3 run.py &

# Terminal 2: Frontend  
echo "⚛️ Starting Frontend..."
cd /Users/evil/Desktop/EVIL/PROJECT/Alice/web
npm run dev &

# Terminal 3: AI
echo "🤖 Starting Ollama..."
ollama serve &

echo "✅ Alice Project started!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend: http://localhost:8000"
echo "🤖 AI: http://localhost:11434"
```

---

## 🎯 **Verifieringschecklista**

- [ ] **Backend körs** på http://localhost:8000
- [ ] **Frontend körs** på http://localhost:3000  
- [ ] **Ollama körs** på http://localhost:11434
- [ ] **API svarar** - `/api/tools/spec` returnerar JSON
- [ ] **HUD laddas** - Alice HUD visas i webbläsaren
- [ ] **AI fungerar** - Ollama kan köra `gpt-oss:20b`

---

## 🔄 **Starta Om Projektet**

För att starta om allt:

```bash
# 1. Stoppa alla processer
pkill -f "python3 run.py"
pkill -f "npm run dev"
pkill -f "ollama serve"

# 2. Vänta 5 sekunder
sleep 5

# 3. Följ steg 2-4 ovan
```

---

## 📚 **Användbara Kommandon**

### Kontrollera status
```bash
# Backend status
curl -s http://localhost:8000/api/tools/spec > /dev/null && echo "✅ Backend OK" || echo "❌ Backend FAIL"

# Frontend status  
curl -s http://localhost:3000 > /dev/null && echo "✅ Frontend OK" || echo "❌ Frontend FAIL"

# AI status
curl -s http://localhost:11434/api/tags > /dev/null && echo "✅ AI OK" || echo "❌ AI FAIL"
```

### Loggar
```bash
# Backend loggar
tail -f server/logs/app.log

# Frontend loggar (browser console)
# Öppna Developer Tools i webbläsaren
```

---

**🎉 Nu borde Alice-projektet köra perfekt!**

För hjälp, se [DEVELOPMENT.md](DEVELOPMENT.md), [README.md](README.md) eller [ALICE_ROADMAP.md](ALICE_ROADMAP.md).
