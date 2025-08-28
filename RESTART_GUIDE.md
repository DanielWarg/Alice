# Alice System Restart Guide
*Skapad: 2025-08-28 efter minnesoptimering*

## 🚀 Snabb uppstart efter restart

### 1. Kontrollera att alla tjänster är stoppade
```bash
# Kontrollera att inga processer kör
pkill -f "ollama"
pkill -f "node"
pkill -f "python"
```

### 2. Starta Alice System (Optimerad version)

**Terminal 1 - Backend:**
```bash
cd /Users/evil/Desktop/EVIL/PROJECT/Alice/server
source .venv/bin/activate
python app_minimal.py
```

**Terminal 2 - Frontend:**
```bash
cd /Users/evil/Desktop/EVIL/PROJECT/Alice/web
npm run dev
```

### 3. Testa systemet
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/health
- **LLM Status**: http://localhost:8000/api/v1/llm/status

## ⚙️ Aktuella konfigurationer (efter optimering)

### LLM Setup
- **Primary Model**: `llama3:8b` (4.6GB, säker minnesanvändning)
- **Fallback Model**: `openai:gpt-4o-mini`
- **Keep-alive**: 10 minuter (istället för 30m)
- **Model warmer**: 8 minuters intervall

### Filändringar gjorda:
1. `server/llm/ollama.py`: 
   - Bytt från `gpt-oss:20b` → `llama3:8b`
   - Keep-alive: `30m` → `10m`
2. `server/model_warmer.py`:
   - Default modell: `llama3:8b`
   - Intervall: `20m` → `8m`

### Miljövariabler (om du vill ändra):
```bash
export LLM_MODEL="llama3:8b"           # Eller phi3:mini (2GB) / qwen2.5-coder:1.5b (1GB)  
export LLM_KEEP_ALIVE="10m"            # Minnesvänligare
export LLM_HEALTH_TIMEOUT_MS="2000"    # Lite mer tid för health checks
```

## 🔍 Felsökning efter restart

### Om Ollama inte startar:
```bash
# Starta Ollama manuellt
ollama serve &

# Kontrollera att modeller finns
curl http://localhost:11434/api/tags
```

### Om modeller saknas:
```bash
# Ladda ner rekommenderade modeller (säkra alternativ till gpt-oss:20b)
ollama pull llama3:8b        # 4.6GB, bästa balans
ollama pull phi3:mini        # 2.1GB, snabb
ollama pull qwen2.5-coder:1.5b  # 1GB, extremt snabb
```

### Om frontend inte hittar backend:
- Kontrollera att backend körs på port 8000
- Kolla CORS-inställningar i `app_minimal.py`

## 📊 Minnestests (när systemet är igång)

### Testa minnesanvändning:
```bash
# Kör performance test (5 minuter, 10s intervall)
cd /Users/evil/Desktop/EVIL/PROJECT/Alice/server
python performance_test.py 10 10

# Övervaka systemresurser (5 minuter)  
python system_monitor.py 5
```

### Säkra modeller att testa:
1. **llama3:8b** - Bästa kvalitet vs minnesanvändning
2. **phi3:mini** - Snabbast, minst minne
3. **qwen2.5-coder:1.5b** - Extremt snabb för kodning

## ⚠️ Vad vi lärde oss från gpt-oss:20b

**Undvik:**
- gpt-oss:20b (20B parametrar = 14GB RAM konstant)
- Keep-alive > 15 minuter på stora modeller
- Model warming utan memory monitoring

**Använd istället:**
- Modeller < 10B parametrar för daglig användning
- Keep-alive 5-10 minuter
- System monitoring under första timmarna

## 🎯 Nästa steg efter restart

1. **Testa grundfunktioner** - Chat via HUD
2. **Verifiera prestanda** - Kör performance_test.py
3. **Övervaka minne** - system_monitor.py första 30 min
4. **Optimera vidare** - Justera keep-alive baserat på användning

---
**Anteckning**: Alla performance-script finns i `server/` mappen och är redo att köra.