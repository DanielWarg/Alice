# 🚀 Alice Project - Cursor Build Guide

**Snabb guide för att bygga Alice med Cursor AI**

---

## 🎯 **Projektöversikt**

Alice är en supersmart AI-assistent med:
- **Lokal AI-kraft** via `gpt-oss:20B` (Ollama)
- **Svenska språkkommandon** med 89% NLU-accuracy
- **Futuristisk HUD-UI** med real-time uppdateringar
- **Smart verktygsintegration** (Spotify, Gmail, Kalender)
- **Röststyrning** med Whisper STT + Piper TTS

---

## 🏗️ **Projektstruktur**

```
Alice/
├── server/                 # FastAPI backend med AI-kärna
├── web/                    # Next.js HUD frontend
├── alice-tools/            # NLU och router-system
├── nlu-agent/              # Naturlig språkförståelse
├── tests/                  # Komplett test-suite
├── docs/                   # Dokumentation
└── tools/                  # Verktyg och utilities
```

---

## 🚀 **Snabbstart**

### 1. **Backend (FastAPI)**
```bash
cd server
source ../.venv/bin/activate
python3 run.py
```

### 2. **Frontend (Next.js)**
```bash
cd web
npm run dev
```

### 3. **AI (Ollama)**
```bash
ollama serve
```

---

## 🧪 **Testning**

### Kör alla tester
```bash
cd tests
python -m pytest -v
```

### Specifika tester
```bash
python -m pytest tests/test_harmony.py
python -m pytest tests/test_voice_system.py
```

---

## 🔧 **Utveckling**

### Backend utveckling
```bash
cd server
source ../.venv/bin/activate
uvicorn app:app --reload
```

### Frontend utveckling
```bash
cd web
npm run dev
```

---

## 📚 **Dokumentation**

- **[STARTUP.md](STARTUP.md)** - Exakt startup-guide
- **[README.md](README.md)** - Projektöversikt
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Utvecklingsguide
- **[ALICE_ROADMAP.md](ALICE_ROADMAP.md)** - Utvecklingsplan

---

**Alice - Din supersmarta svenska AI-assistent! 🚀**
