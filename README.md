# Alice - AI Assistant Platform

Alice är en avancerad, lokal AI-assistent som kombinerar naturlig språkförståelse, röstsyntes, och intelligenta verktyg i en modern HUD-baserad gränssnittsdesign. Systemet är designat för att köras helt lokalt med fokus på integritet, prestanda och modulärhet.

## Översikt

Alice kombinerar flera teknologier för att leverera en kraftfull AI-assistent:

- **Frontend**: Next.js 15-baserat HUD (Heads-Up Display) med real-time uppdateringar
- **Backend**: FastAPI-server med modulär arkitektur  
- **AI-kärna**: Lokal LLM-integration via Ollama (gpt-oss:20B)
- **NLU**: Naturlig språkförståelse med svensk språkstöd
- **TTS/STT**: Piper för text-till-tal, Whisper för tal-till-text
- **Verktygsystem**: Modulärt verktygsregister med Spotify-integration

## Projektstruktur

```
alice/
├── server/                 # FastAPI backend
│   ├── app.py             # Huvudapplikation 
│   ├── core/              # Kärnmoduler
│   │   ├── router.py      # Intent-klassificering
│   │   ├── tool_registry.py # Verktygshantering
│   │   └── tool_specs.py  # Verktygsspecifikationer
│   ├── prompts/           # AI-prompts
│   ├── tests/             # Enhetstester
│   └── requirements.txt   # Python-dependencies
├── web/                   # Next.js frontend
│   ├── app/               # Next.js 13+ app directory
│   ├── components/        # React-komponenter
│   ├── lib/               # Hjälpbibliotek och API-klienter
│   └── package.json       # Node.js dependencies
├── alice-tools/          # Verktygsmodul (TypeScript)
├── nlu-agent/             # NLU-agent för språkförståelse
└── tests/                 # Integrationstester
```

## Snabbstart

### Förkunskaper

- Python 3.9+
- Node.js 18+
- Ollama (för lokal LLM)

### Installation

1. **Klona repository**
   ```bash
   git clone <repository-url>
   cd alice
   ```

2. **Backend Setup**
   ```bash
   # Skapa och aktivera virtuell miljö
   python3 -m venv .venv
   source .venv/bin/activate  # På Windows: .venv\Scripts\activate
   
   # Installera dependencies
   cd server
   pip install -r requirements.txt
   ```

3. **Frontend Setup**
   ```bash
   cd web
   npm install
   ```

4. **Environment Configuration**
   
   Skapa `.env` i projektets rot:
   ```env
   # AI Konfiguration
   USE_HARMONY=false
   USE_TOOLS=true
   HARMONY_TEMPERATURE_COMMANDS=0.2
   NLU_CONFIDENCE_THRESHOLD=0.85
   ENABLED_TOOLS=PLAY,PAUSE,SET_VOLUME,NEXT,PREV
   
   # Spotify Integration (valfritt)
   SPOTIFY_CLIENT_ID=your_client_id
   SPOTIFY_CLIENT_SECRET=your_client_secret
   SPOTIFY_REDIRECT_URI=http://127.0.0.1:3100/spotify/callback
   
   # API Konfiguration
   JARVIS_MINIMAL=0
   NLU_AGENT_URL=http://127.0.0.1:7071
   ```

### Starta Systemet

1. **Starta Backend** (Terminal 1)
   ```bash
   source .venv/bin/activate
   uvicorn server.app:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Starta NLU Agent** (Terminal 2)
   ```bash
   cd nlu-agent
   npm run dev
   ```

3. **Starta Frontend** (Terminal 3)
   ```bash
   cd web
   npm run dev -- -p 3100
   ```

4. **Öppna Applikationen**
   
   Navigera till: http://localhost:3100

## Utvecklingsworkflow

### Kodstandard

- **Python**: Följer PEP 8, använder type hints
- **TypeScript/JavaScript**: ESLint + Prettier konfiguration
- **Git**: Conventional commits (feat, fix, docs, refactor, test)

### Testing

```bash
# Backend-tester
cd server
python -m pytest tests/ -v

# Frontend-tester  
cd web
npm test

# Integrationstester
cd tests
python harmony_e2e_test.py
```

### Byggprocess

```bash
# Produktionsbygge
cd web
npm run build

# Starta i produktionsläge
npm start
```

## Systemarkitektur

### Komponenter

1. **Frontend (Next.js HUD)**
   - React-baserat användargränssnitt
   - Real-time kommunikation via WebSocket
   - Modulär overlay-arkitektur
   - PWA-stöd med offline-funktionalitet

2. **Backend API (FastAPI)**
   - RESTful API med automatisk dokumentation
   - WebSocket för real-time kommunikation
   - Modulär verktygsarkitektur
   - Integrerad AI-router

3. **NLU System**
   - Regex-baserad intent-klassificering
   - Slot-extraction för parametrar
   - Fallback till LLM vid osäkerhet
   - Svenskspråkigt stöd

4. **Verktygsystem**
   - Pluggbar arkitektur
   - Validering via Pydantic-scheman
   - Configurable activation
   - Built-in Spotify-integration

### Dataflöde

```
Användare Input → NLU Agent → Intent Klassificering → Verktygsexekvering → Respons → HUD
```

## API-dokumentation

### Kärnändpunkter

#### Chat API
```http
POST /api/chat
Content-Type: application/json

{
  "prompt": "spela musik",
  "provider": "auto"
}
```

#### Tool Execution
```http
POST /api/tools/exec
Content-Type: application/json

{
  "tool": "PLAY",
  "args": {}
}
```

#### TTS Synthesis  
```http
POST /api/tts/synthesize
Content-Type: application/json

{
  "text": "Hej, jag är Alice",
  "voice": "sv_SE-nst-medium",
  "speed": 1.0
}
```

#### WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/alice');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

### Autogenererad API-dokumentation

Fullständig API-dokumentation finns tillgänglig på:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Konfiguration

### Environment Variables

| Variable | Default | Beskrivning |
|----------|---------|-------------|
| `USE_HARMONY` | `false` | Aktivera Harmony AI-system |
| `USE_TOOLS` | `true` | Aktivera verktygsexekvering |
| `ENABLED_TOOLS` | `PLAY,PAUSE,SET_VOLUME` | Kommaseparerad lista av aktiva verktyg |
| `NLU_CONFIDENCE_THRESHOLD` | `0.85` | Konfidensminimum för NLU-beslut |
| `JARVIS_MINIMAL` | `0` | Minimalt läge (1 = aktivera) |

### Verktyg Konfiguration

Aktivera/inaktivera verktyg genom `ENABLED_TOOLS`:

```env
ENABLED_TOOLS=PLAY,PAUSE,STOP,NEXT,PREV,SET_VOLUME,MUTE,UNMUTE,SHUFFLE,REPEAT
```

Tillgängliga verktyg:
- **Mediauppspelning**: PLAY, PAUSE, STOP, NEXT, PREV
- **Volymkontroll**: SET_VOLUME, MUTE, UNMUTE  
- **Uppspelningslägen**: SHUFFLE, REPEAT
- **Interaktion**: LIKE, UNLIKE

## Spotify Integration

### Setup

1. Skapa Spotify App på [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)

2. Konfigurera redirect URI:
   ```
   http://127.0.0.1:3100/spotify/callback
   ```

3. Lägg till credentials i `.env`:
   ```env
   SPOTIFY_CLIENT_ID=your_app_client_id
   SPOTIFY_CLIENT_SECRET=your_app_client_secret  
   SPOTIFY_REDIRECT_URI=http://127.0.0.1:3100/spotify/callback
   ```

4. Auktorisera via HUD:
   - Öppna Alice HUD
   - Klicka på Spotify-integration
   - Följ OAuth-flödet

### Funktioner

- Uppspelningskontroll (play/pause/next/previous)
- Volymjustering och mute/unmute
- Sök efter musik, artister, spellistor
- Köhantering 
- Enhetsvälkoppling
- Real-time uppspelningsstatus

## Felsökning

### Vanliga Problem

**Backend startar inte**
```bash
# Kontrollera portar
lsof -i :8000
# Kontrollera dependencies
pip install -r requirements.txt
```

**Frontend bygg misslyckas**
```bash
# Rensa cache och installera om
rm -rf node_modules package-lock.json
npm install
```

**NLU Agent otillgänglig**
```bash
# Kontrollera NLU Agent status
curl http://localhost:7071/nlu/classify -X POST -d '{"text":"test"}'
```

**Spotify inte ansluten**
- Verifiera CLIENT_ID och CLIENT_SECRET
- Kontrollera redirect URI matchar exakt
- Kontrollera nätverksanslutning

### Loggar

**Backend loggar**
```bash
# Visa real-time loggar
tail -f server/logs/app.log
```

**Frontend loggar**
- Browser Developer Tools Console
- Network tab för API-anrop

### Debug Mode

```bash
# Starta backend med debug
export DEBUG=1
uvicorn server.app:app --host 127.0.0.1 --port 8000 --reload --log-level debug
```

## Bidrag

Vi välkomnar bidrag! Se [DEVELOPMENT.md](DEVELOPMENT.md) för detaljerade utvecklingsriktlinjer.

### Pull Request Process

1. Forka repositoryet
2. Skapa feature branch (`git checkout -b feature/amazing-feature`)
3. Commit ändringar (`git commit -m 'Add amazing feature'`)  
4. Push till branch (`git push origin feature/amazing-feature`)
5. Öppna Pull Request

## Säkerhet

Alice är designad för lokal hosting och inkluderar:

- Ingen data lämnar din maskin (utan explicit konfiguration)
- Safe Boot-läge för att inaktivera kamera/mikrofon
- Modulär aktivering av verktyg
- Environment-baserad konfiguration

## Licens

Se [LICENSE](LICENSE) fil för detaljer.

## Support

- **Issues**: [GitHub Issues](../../issues)
- **Discussions**: [GitHub Discussions](../../discussions)
- **Wiki**: [Project Wiki](../../wiki)

---

**Alice - Din personliga AI-assistent. Lokal. Privat. Kraftfull.**