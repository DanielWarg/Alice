# 🚀 Alice Project - One-Command Startup

**Starta hela Alice-projektet med ett enda kommando!**

---

## 📋 **Snabb-check förutsättningar**

```bash
python3 --version && node --version && ollama --version
```
**Förväntad output:** Versionsnummer för alla tre

---

## ⚡ **ONE-COMMAND STARTUP**

Kopiera och kör detta kommando i terminalen:

```bash
cd /Users/evil/Desktop/EVIL/PROJECT/Alice && curl -s https://raw.githubusercontent.com/example/alice-startup/main/quick-start.sh | bash
```

**ELLER använd det inbyggda startup-scriptet:**

```bash
cd /Users/evil/Desktop/EVIL/PROJECT/Alice && ./start_alice.sh
```

---

## 🛠️ **Manual Setup (om one-command inte fungerar)**

### Steg 1: Navigera till projekt
```bash
cd /Users/evil/Desktop/EVIL/PROJECT/Alice
```

### Steg 2: Fix virtual environment (om trasig)
```bash
# Kontrollera om venv fungerar
source .venv/bin/activate
if [[ $(which python3) != *".venv"* ]]; then
  echo "🔧 Fixing broken venv..."
  deactivate 2>/dev/null || true
  rm -rf .venv
  python3 -m venv .venv
  source .venv/bin/activate
fi
echo "✅ venv: $(which python3)"
```

### Steg 3: Installera dependencies (en gång)
```bash
# Uppgradera pip och installera
pip install --upgrade pip
pip install -r server/requirements.txt
pip install python-multipart httpx

# Frontend dependencies
cd web && npm install && cd ..
```

### Steg 4: Rensa gamla processer
```bash
# Döda gamla processer som kan störa
pkill -f "python.*run.py" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
sleep 2
```

### Steg 5: Starta alla services
```bash
# Starta backend (i bakgrunden)
cd server
source ../.venv/bin/activate
python run.py &
BACKEND_PID=$!
cd ..

# Vänta och kontrollera backend
sleep 5
if curl -s http://localhost:8000/api/tools/spec >/dev/null; then
  echo "✅ Backend started on http://localhost:8000"
else
  echo "❌ Backend failed to start"
  kill $BACKEND_PID 2>/dev/null
  exit 1
fi

# Starta frontend (i bakgrunden)
cd web
npm run dev &
FRONTEND_PID=$!
cd ..

# Vänta och kontrollera frontend
sleep 8
if curl -s http://localhost:3000 >/dev/null; then
  echo "✅ Frontend started on http://localhost:3000"
else
  echo "❌ Frontend failed to start"
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  exit 1
fi

# Kontrollera Ollama (startar automatiskt)
if curl -s http://localhost:11434/api/tags >/dev/null; then
  echo "✅ Ollama running on http://localhost:11434"
else
  echo "🤖 Starting Ollama..."
  ollama serve &
  sleep 3
fi
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
- 🤖 **LLM Status Badge** (top-right) som visar "ollama:gpt-oss:20b (healthy)"
- 🎙️ **Voice Interface** för Swedish speech
- 📊 **System metrics** och verktyg

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

**🎯 Nu borde Alice starta på 30 sekunder utan krångel!**

För support, se [README.md](README.md) eller [DEVELOPMENT.md](DEVELOPMENT.md).