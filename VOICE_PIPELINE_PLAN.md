# 🎙️ Alice Voice Pipeline – Snappy HTTP TTS (svenska → engelsk uppläsning)

## Vision
**All svensk input** (chat, mejl, notiser) översätts snabbt till idiomatisk engelska och läses upp med **HTTP-based TTS** (Nova/Alloy voices).

**Fokus:** låg latens (<1.5s), låg kostnad (~pennies), enkel drift på din Mac. Ingen Guardian, ingen PII-maskning, inga consent-flöden.

## Arkitektur (4 delar) - UPPDATERAD

```
[Svensk Input] → [GPT-OSS Orchestrator] → [HTTP TTS + Cache] → [HUD/Player]
     ↓               ↓                       ↓                   ↓
Chat/Email/Cal  Smart översättning      Nova/Alloy HTTP      Original + English
                tone/style              + LRU Cache          + Audio playback
                                        + Piper Fallback
```

**Flöde:**
1. **Ingest:** tar in text från valfri källa (chat, mejl, kalenderrad, notis)
2. **Orchestrator (gpt-oss lokalt):** gör "smart översättning" + formaterar talvänlig text och enkel metadata (tone/style). Segmenterar långa texter.
3. **TTS (HTTP OpenAI + fallback):** HTTP POST till OpenAI TTS API, LRU cache (300 entries), Piper local fallback
4. **HUD/Player:** visar original (svenska) och engelsk text, spelar upp ljudet, sparar enkel cache

## Implementation (minsta möjliga)

**En process (eller tre små moduler i samma repo):**

```
server/voice/
├── input_processor.py    # Källor (chat, mejl, notiser)
├── translator.py         # gpt-oss svenska → engelska  
├── realtime_client.py    # OpenAI Realtime API
└── voice_capabilities.json  # { default_voice: "marin", fallback: "cedar", rate: 1.0 }
```

**Core Components:**

```python
# input_processor.py
class InputProcessor:
    def process_chat(text: str) -> str
    def process_email(subject: str, body: str) -> str  
    def process_notification(text: str) -> str

# translator.py (gpt-oss)
class SwedishToEnglishTranslator:
    def translate(swedish_text: str) -> dict:
        # Smart översättning via gpt-oss:20b
        return {
            "original": swedish_text,
            "speak_text": "...",  # Kort, klar engelska
            "tone": "neutral"     # Eller cheerful, formal
        }

# realtime_client.py
class RealtimeVoiceClient:
    def speak(text: str, voice="marin") -> audio_stream
    def cache_get(text_hash: str) -> audio_data
    def cache_set(text_hash: str, audio_data: bytes)
```

## Konfiguration

```env
# Enkel konfiguration
VOICE_OUTPUT_LANGUAGE=en
VOICE_DEFAULT_VOICE=marin
OLLAMA_MODEL=gpt-oss:20b  
OLLAMA_KEEP_ALIVE=15m
OPENAI_REALTIME_KEY=sk-...

# Performance
CACHE_SIZE=300
MAX_SEGMENT_LEN=320  # tecken för låg latens
```

## Kvalitetsregler (enkla, lokala)

- **Översätt alltid till "en-US"** - behåll namn, siffror, datum
- **Kapning:** om texten är lång, läs först en 1–2 men "TL;DR" och fortsätt på begäran  
- **Talslipning:** basic list med 10–20 svenska namn/orter där du lägger in små uttalstips i speak_text vid behov (valfritt)

## Mäta bara det som spelar roll

- **End-to-first-audio p95:** 
  - Chat < 1.5s
  - Email < 2.0s  
- **Cache hit-rate efter några dagar:** ≥ 30%
- **Felfrekvens Realtime:** < 2% (automatisk retry 1–2 ggr)

## Rollout i tre steg

1. **Chat först:** översätt → läs upp, visa dubbeltext
2. **Email ingest:** lyssna på inbox, gör samma sak; cachning på mail-ID  
3. **Notiser/kalender:** kort speak_text ("Möte 10:00 med Anna") för ultrasnabb uppläsning

## Vad vi uttryckligen hoppar över

**Ingen Guardian, ingen PII-maskning, ingen consent, inga dataresidency-krav, inga komplexa policyer eller audit-spår. Bara rak funktion för dig.**

## Felhantering & Fallback

**Enkel fallback chain:**
1. **OpenAI Realtime** (primary - Marin/Cedar)
2. **Piper lokal TTS** (backup - lägre kvalitet men fungerar offline)
3. **Text only** (om inget ljud fungerar)

```python
async def speak_text(text: str):
    try:
        return await realtime_client.speak(text, voice="marin")
    except RealtimeAPIError:
        return await local_piper_tts.speak(text, lang="en")
    except Exception:
        return {"text_only": text}  # Visa bara texten
```

## Enkel LRU Cache

```python
class VoiceCache:
    def __init__(self, size=300):
        self.cache = {}  # hash(text+voice) -> audio_bytes
        self.max_size = size
    
    def get_audio(self, text: str, voice: str) -> bytes:
        key = hash(text + voice)
        return self.cache.get(key)
    
    def save_audio(self, text: str, voice: str, audio_bytes: bytes):
        key = hash(text + voice) 
        self.cache[key] = audio_bytes
        # LRU cleanup om nödvändigt
```

## Klar att bygga

**Lägg tre moduler:**
1. `input_processor` - hantera chat/email/notiser
2. `translator_gptoss` - svensk → engelsk översättning  
3. `realtime_client` - OpenAI Realtime för audio

**Koppla din HUD:**
- Realtime_client för uppspelning
- Dubbelspråkig visning (svensk original + engelsk översättning)
- Aktivera cache

**Det är allt.**

---

## Current Alice Status

- **Agent Integration**: ✅ KOMPLETT - Alice kan använda tools (tid, kalender, musik)
- **Chat System**: ✅ KOMPLETT - Svensk input, smart fallback till LLM
- **Database**: ✅ KOMPLETT - Chat history och sessions fungerar
- **LLM Pipeline**: ✅ KOMPLETT - gpt-oss:20b + OpenAI fallback

**Status**: ✅ HTTP TTS approach validerad - kostnad $15/miljon tecken istället för $900/månad!

**Implementation pågår**: 
- ✅ Input processor skapad
- ✅ Voice capabilities konfigurerad  
- 🔄 Orchestrator (pågår)
- ⏳ HTTP TTS client med cache
- ⏳ SSML phoneme support
- ⏳ HUD interface

---
*Personlig Alice voice pipeline - svensk input → engelsk uppläsning, inga enterprise-krångel.*