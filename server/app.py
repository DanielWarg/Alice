from __future__ import annotations

import asyncio
import time
import json
import os
import subprocess
import tempfile
import base64
import hashlib
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional, Set, List

# Additional imports for enhanced metrics
try:
    import psutil
except ImportError:
    psutil = None

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter, HTTPException, File, UploadFile
from fastapi.responses import ORJSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from security import configure_secure_app
from pydantic import BaseModel, Field
import logging
from dotenv import load_dotenv
import httpx

from memory import MemoryStore
from decision import EpsilonGreedyBandit, simulate_first
from prompts.system_prompts import system_prompt as SP, developer_prompt as DP
from metrics import metrics
from training import stream_dataset
from core import (
    list_tool_specs, 
    validate_and_execute_tool,
    enabled_tools,
    build_harmony_tool_specs,
    classify,
    run_preflight_checks,
    log_preflight_results
)
from harmony_test_endpoint import HarmonyTestBatchRequest, HarmonyTestBatchResponse, run_harmony_test_case
from voice_stream import get_voice_manager
from voice_stt import transcribe_audio_file, get_stt_status
from audio_processor import audio_processor
from deps import get_global_openai_settings, OpenAIClient, validate_openai_config
from agents.bridge import AliceAgentBridge, AgentBridgeRequest, StreamChunk, create_alice_bridge
from http_client import spotify_client, resilient_http_client, safe_external_call
from error_handlers import setup_error_handlers, RequestIDMiddleware, ValidationError, SwedishDateTimeValidationError
from validators import CalendarEventRequest as EnhancedCalendarEventRequest, ChatMessage, validate_swedish_datetime_string
from rate_limiter import create_alice_rate_limiter


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alice")

# Advanced TTS Handler
class EnhancedTTSHandler:
    """Enhanced TTS system with emotion, personality, caching, and quality improvements"""
    
    def __init__(self):
        self.cache_dir = "data/tts_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Available voice models with quality ratings
        self.voice_models = {
            "sv_SE-nst-medium": {"quality": "medium", "gender": "female", "naturalness": 7},
            "sv_SE-nst-high": {"quality": "high", "gender": "female", "naturalness": 8},
            "sv_SE-lisa-medium": {"quality": "medium", "gender": "female", "naturalness": 8}
        }
        
        # Alice's personality voice settings
        self.personality_presets = {
            "alice": {
                "speed": 1.05,  # Slightly faster, more energetic
                "pitch": 1.02,  # Slightly higher, friendlier
                "emotion_bias": "friendly",
                "confidence": 0.85
            },
            "formal": {
                "speed": 0.95,  # Slower, more deliberate
                "pitch": 0.98,  # Slightly lower, more authoritative
                "emotion_bias": "neutral",
                "confidence": 0.95
            },
            "casual": {
                "speed": 1.1,   # Faster, more conversational
                "pitch": 1.05,  # Higher, more expressive
                "emotion_bias": "happy",
                "confidence": 0.8
            }
        }
        
        # Emotional modulation parameters
        self.emotion_settings = {
            "neutral": {"noise_scale": 0.667, "length_scale": 1.0, "noise_w": 0.8},
            "happy": {"noise_scale": 0.6, "length_scale": 0.95, "noise_w": 0.75},
            "calm": {"noise_scale": 0.7, "length_scale": 1.05, "noise_w": 0.85},
            "confident": {"noise_scale": 0.65, "length_scale": 0.98, "noise_w": 0.75},
            "friendly": {"noise_scale": 0.63, "length_scale": 0.97, "noise_w": 0.78}
        }
    
    def get_cache_key(self, text: str, voice: str, speed: float, emotion: str, personality: str, pitch: float) -> str:
        """Generate cache key for TTS request"""
        cache_data = f"{text}_{voice}_{speed}_{emotion}_{personality}_{pitch}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def get_cached_audio(self, cache_key: str) -> Optional[bytes]:
        """Retrieve cached audio if available"""
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.wav")
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                return f.read()
        return None
    
    def cache_audio(self, cache_key: str, audio_data: bytes) -> None:
        """Cache audio data"""
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.wav")
        with open(cache_path, 'wb') as f:
            f.write(audio_data)
    
    def select_best_voice(self, requested_voice: str) -> str:
        """Select the best available voice model"""
        if requested_voice in self.voice_models:
            return requested_voice
        
        # Fallback to best available Swedish voice
        available_voices = [v for v in self.voice_models.keys() if os.path.exists(f"models/tts/{v}.onnx")]
        if available_voices:
            # Prioritize high quality voices
            high_quality = [v for v in available_voices if self.voice_models[v]["quality"] == "high"]
            return high_quality[0] if high_quality else available_voices[0]
        
        return "sv_SE-nst-medium"  # Final fallback
    
    def apply_personality_settings(self, request: 'TTSRequest') -> Dict[str, Any]:
        """Apply personality-based voice modifications"""
        preset = self.personality_presets.get(request.personality, self.personality_presets["alice"])
        
        # Combine request parameters with personality preset
        final_speed = request.speed * preset["speed"]
        final_pitch = request.pitch * preset["pitch"]
        
        # Select emotion based on personality bias if none specified
        final_emotion = request.emotion or preset["emotion_bias"]
        
        return {
            "speed": max(0.5, min(2.0, final_speed)),
            "pitch": max(0.8, min(1.2, final_pitch)),
            "emotion": final_emotion,
            "confidence": preset["confidence"]
        }
    
    async def synthesize_enhanced(self, request: 'TTSRequest') -> Dict[str, Any]:
        """Enhanced TTS synthesis with emotion, personality, and caching"""
        try:
            # Apply personality settings
            settings = self.apply_personality_settings(request)
            
            # Select best voice
            selected_voice = self.select_best_voice(request.voice)
            
            # Generate cache key
            cache_key = self.get_cache_key(
                request.text, selected_voice, settings["speed"], 
                settings["emotion"], request.personality, settings["pitch"]
            )
            
            # Check cache first
            if request.cache:
                cached_audio = self.get_cached_audio(cache_key)
                if cached_audio:
                    logger.info(f"TTS cache hit for key: {cache_key[:8]}...")
                    audio_b64 = base64.b64encode(cached_audio).decode('utf-8')
                    return {
                        "success": True,
                        "audio_data": audio_b64,
                        "format": "wav",
                        "voice": selected_voice,
                        "text": request.text,
                        "emotion": settings["emotion"],
                        "personality": request.personality,
                        "cached": True,
                        "settings": settings
                    }
            
            # Generate audio with enhanced parameters
            audio_data = await self._generate_audio(request.text, selected_voice, settings)
            
            # Cache the result
            if request.cache:
                self.cache_audio(cache_key, audio_data)
            
            # Return enhanced response
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            return {
                "success": True,
                "audio_data": audio_b64,
                "format": "wav",
                "voice": selected_voice,
                "text": request.text,
                "emotion": settings["emotion"],
                "personality": request.personality,
                "cached": False,
                "settings": settings,
                "quality_score": self.voice_models[selected_voice]["naturalness"]
            }
            
        except Exception as e:
            logger.error(f"Enhanced TTS synthesis failed: {str(e)}")
            raise e
    
    async def _generate_audio(self, text: str, voice: str, settings: Dict[str, Any]) -> bytes:
        """Generate audio using Piper with enhanced parameters"""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            model_path = f"models/tts/{voice}.onnx"
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Voice model {voice} not found")
            
            # Get emotion-specific inference parameters
            emotion_params = self.emotion_settings.get(settings["emotion"], self.emotion_settings["neutral"])
            
            # Build enhanced Piper command
            cmd = [
                "python", "-m", "piper",
                "--model", model_path,
                "--output_file", temp_path,
                "--noise_scale", str(emotion_params["noise_scale"]),
                "--length_scale", str(emotion_params["length_scale"] * (1/settings["speed"])),
                "--noise_w", str(emotion_params["noise_w"])
            ]
            
            # Run Piper synthesis
            process = subprocess.run(
                cmd,
                input=text,
                text=True,
                capture_output=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            if process.returncode != 0:
                logger.error(f"Piper TTS failed: {process.stderr}")
                raise RuntimeError(f"TTS synthesis failed: {process.stderr}")
            
            # Read generated audio
            with open(temp_path, 'rb') as f:
                raw_audio_data = f.read()
            
            # Apply audio post-processing and enhancement
            try:
                enhanced_audio = audio_processor.enhance_audio(raw_audio_data, settings)
                logger.info("Audio enhancement applied to TTS output")
                return enhanced_audio
            except Exception as e:
                logger.warning(f"Audio enhancement failed, using raw audio: {e}")
                return raw_audio_data
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

# Initialize enhanced TTS handler
enhanced_tts = EnhancedTTSHandler()

app = FastAPI(title="Alice 2.0 Backend", version="0.1.0", default_response_class=ORJSONResponse)

# Setup standardized error handling (RFC 7807)
setup_error_handlers(app)
app.add_middleware(RequestIDMiddleware)

# Add professional rate limiting
rate_limiter = create_alice_rate_limiter()
app.add_middleware(type(rate_limiter), rules=rate_limiter.rules)

MINIMAL_MODE = os.getenv("ALICE_MINIMAL", "0") == "1"
# Harmony feature flags (Fas 1 – adapter bakom flaggor)
USE_HARMONY = (os.getenv("USE_HARMONY", "false").lower() == "true")
USE_TOOLS = (os.getenv("USE_TOOLS", "false").lower() == "true")
try:
    HARMONY_TEMPERATURE_COMMANDS = float(os.getenv("HARMONY_TEMPERATURE_COMMANDS", "0.2"))
except Exception:
    HARMONY_TEMPERATURE_COMMANDS = 0.2
try:
    NLU_CONFIDENCE_THRESHOLD = float(os.getenv("NLU_CONFIDENCE_THRESHOLD", "0.9"))
except Exception:
    NLU_CONFIDENCE_THRESHOLD = 0.9
NLU_AGENT_URL = os.getenv("NLU_AGENT_URL", "http://127.0.0.1:7071")

# Optional: styr resonemangsnivå (påverkar temp om HARMONY_TEMPERATURE_COMMANDS inte satts)
HARMONY_REASONING_LEVEL = (os.getenv("HARMONY_REASONING_LEVEL", "low").strip().lower())
if os.getenv("HARMONY_TEMPERATURE_COMMANDS") is None:
    if HARMONY_REASONING_LEVEL == "high":
        HARMONY_TEMPERATURE_COMMANDS = 0.5
    elif HARMONY_REASONING_LEVEL == "medium":
        HARMONY_TEMPERATURE_COMMANDS = 0.35
    else:
        HARMONY_TEMPERATURE_COMMANDS = 0.2

# Verktygs-whitelist för PR3 (aktivera 2–3 verktyg initialt)
_enabled_tools_env = os.getenv("ENABLED_TOOLS")
if _enabled_tools_env is None:
    # Default: aktivera enbart PLAY/PAUSE/SET_VOLUME i första steget
    ENABLED_TOOLS = {"PLAY", "PAUSE", "SET_VOLUME"} if USE_TOOLS else set()
else:
    ENABLED_TOOLS = {t.strip().upper() for t in _enabled_tools_env.split(",") if t.strip()}

# Exportera ENABLED_TOOLS till miljövariabeln för verify_tool_surface.py
os.environ["ENABLED_TOOLS"] = ",".join(sorted(ENABLED_TOOLS))


# Använd core.is_tool_enabled istället


def _harmony_system_prompt() -> str:
    return SP() + " För denna fas: skriv ENDAST slutligt svar mellan taggarna [FINAL] och [/FINAL]."


def _harmony_developer_prompt() -> str:
    return DP()


def _extract_final(text: str) -> str:
    try:
        start = text.find("[FINAL]")
        end = text.find("[/FINAL]")
        if start != -1 and end != -1 and end > start:
            return text[start + len("[FINAL]"):end].strip()
    except Exception:
        pass
    return (text or "").strip()


def _maybe_parse_tool_call(text: str) -> Optional[Dict[str, Any]]:
    """Detektera ett verktygsanrop i modellens svar.
    Stödjer två format:
    1) Prefix-taggen [TOOL_CALL]{...}
    2) Naket JSON som innehåller fälten {"tool": NAME, "args": {...}}
    Returnerar {"tool": str, "args": dict} eller None.
    """
    try:
        if not text:
            return None
        s = text.strip()
        # 1) [TOOL_CALL]{json}
        if s.startswith("[TOOL_CALL]"):
            s = s[len("[TOOL_CALL]"):].lstrip()
        # Försök att hitta ett JSON-objekt
        import re as _re
        m = _re.search(r"\{[\s\S]*\}", s)
        if not m:
            return None
        candidate = json.loads(m.group(0))
        if isinstance(candidate, dict) and isinstance(candidate.get("tool"), str):
            args = candidate.get("args") or {}
            if isinstance(args, dict):
                return {"tool": candidate["tool"], "args": args}
    except Exception:
        return None
    return None

async def _router_first_try(prompt: str) -> Optional[Dict[str, Any]]:
    """Försök router-först med core.router för snabba intents.
    Returnerar plan-dict eller None.
    """
    try:
        # Först, testa core.router
        router_result = classify(prompt)
        if router_result and router_result.get("confidence", 0) >= NLU_CONFIDENCE_THRESHOLD:
            return {
                "tool": router_result["tool"],
                "params": router_result["args"],
                "confidence": router_result["confidence"],
                "source": "core_router"
            }
        
        # Fallback till NLU/Agent-routern
        async with httpx.AsyncClient(timeout=2.5) as client:
            r = await client.post(f"{NLU_AGENT_URL}/agent/route", json={"text": prompt})
            if r.status_code != 200:
                return None
            j = r.json() or {}
            plan = j.get("plan")
            conf = float(j.get("confidence") or 0.0)
            if plan and conf >= NLU_CONFIDENCE_THRESHOLD:
                return plan
    except Exception:
        pass
    return None


def _format_tool_confirmation(name: str, args: Dict[str, Any]) -> str:
    n = (name or "").upper()
    a = args or {}
    if n == "PLAY":
        return "Spelar upp."
    if n == "PAUSE":
        return "Pausar."
    if n == "SET_VOLUME":
        if isinstance(a.get("level"), int):
            return f"Volym satt till {a['level']}%."
        if isinstance(a.get("delta"), int):
            d = a['delta']
            return f"Volym {'höjd' if d>0 else 'sänkt'} med {abs(d)}%."
        return "Volym uppdaterad."
    if n == "SAY":
        return str(a.get("text") or "")
    if n == "DISPLAY":
        return str(a.get("text") or "")
    return "Klart."

# Configure secure CORS and security headers
app = configure_secure_app(app)

# Harmony E2E test endpoint (kan stängas av i prod via proxy)
router = APIRouter()

@router.post("/harmony/test", response_model=HarmonyTestBatchResponse)
async def harmony_test(req: HarmonyTestBatchRequest):
    results = []
    for case in req.cases:
        res = await run_harmony_test_case(case, req)
        results.append(res)
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    summary = {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "pass_rate": round(100.0 * passed / max(1, len(results)), 2),
    }
    return HarmonyTestBatchResponse(results=results, summary=summary)

@router.get("/tools/spec")
async def tools_spec():
    """Hämta Harmony-verktygsspecs för aktiverade verktyg"""
    return build_harmony_tool_specs()

@router.get("/tools/registry")
async def tools_registry():
    """Hämta lista över tillgängliga verktygsexekverare"""
    from core import get_executor_names
    return {"executors": get_executor_names()}

@router.get("/tools/enabled")
async def tools_enabled():
    """Hämta lista över aktiverade verktyg från miljövariabel"""
    return {"enabled": enabled_tools()}

# Calendar API endpoints
from core.calendar_service import calendar_service

class CalendarEventRequest(BaseModel):
    title: str = Field(..., description="Händelsens titel")
    start_time: str = Field(..., description="Starttid (svensk format)")
    end_time: Optional[str] = Field(None, description="Sluttid (valfritt)")
    description: Optional[str] = Field(None, description="Beskrivning")
    attendees: Optional[List[str]] = Field(None, description="E-postadresser till deltagare")
    check_conflicts: bool = Field(True, description="Kontrollera konflikter innan skapande")

class CalendarListRequest(BaseModel):
    max_results: int = Field(10, ge=1, le=50, description="Antal händelser att hämta")
    time_min: Optional[str] = Field(None, description="Tidigaste tid")
    time_max: Optional[str] = Field(None, description="Senaste tid")

class CalendarSearchRequest(BaseModel):
    query: str = Field(..., description="Sökfråga")
    max_results: int = Field(20, ge=1, le=100, description="Max antal resultat")

class CalendarUpdateRequest(BaseModel):
    event_id: str = Field(..., description="Händelse-ID")
    title: Optional[str] = Field(None, description="Ny titel")
    start_time: Optional[str] = Field(None, description="Ny starttid")
    end_time: Optional[str] = Field(None, description="Ny sluttid")
    description: Optional[str] = Field(None, description="Ny beskrivning")

class SuggestTimesRequest(BaseModel):
    duration_minutes: int = Field(60, ge=15, le=480, description="Möteslängd i minuter")
    date_preference: Optional[str] = Field(None, description="Önskat datum (svensk format)")
    max_suggestions: int = Field(5, ge=1, le=10, description="Max antal förslag")

class ConflictCheckRequest(BaseModel):
    start_time: str = Field(..., description="Starttid")
    end_time: Optional[str] = Field(None, description="Sluttid")
    exclude_event_id: Optional[str] = Field(None, description="Exkludera händelse-ID")

@router.post("/api/calendar/events")
async def create_calendar_event(request: CalendarEventRequest):
    """Skapa en ny kalenderhändelse"""
    try:
        result = calendar_service.create_event(
            title=request.title,
            start_time=request.start_time,
            end_time=request.end_time,
            description=request.description,
            attendees=request.attendees,
            check_conflicts_first=request.check_conflicts
        )
        return {"success": True, "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/calendar/events")
async def list_calendar_events(
    max_results: int = 10,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None
):
    """Lista kommande kalenderhändelser"""
    try:
        result = calendar_service.list_events(max_results, time_min, time_max)
        return {"success": True, "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/calendar/events/search")
async def search_calendar_events(request: CalendarSearchRequest):
    """Sök kalenderhändelser"""
    try:
        result = calendar_service.search_events(request.query, request.max_results)
        return {"success": True, "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/calendar/events/{event_id}")
async def delete_calendar_event(event_id: str):
    """Ta bort en kalenderhändelse"""
    try:
        result = calendar_service.delete_event(event_id)
        return {"success": True, "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/calendar/events")
async def update_calendar_event(request: CalendarUpdateRequest):
    """Uppdatera en kalenderhändelse"""
    try:
        result = calendar_service.update_event(
            event_id=request.event_id,
            title=request.title,
            start_time=request.start_time,
            end_time=request.end_time,
            description=request.description
        )
        return {"success": True, "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/calendar/suggest-times")
async def suggest_meeting_times(request: SuggestTimesRequest):
    """Föreslå lämpliga mötestider"""
    try:
        suggestions = calendar_service.suggest_meeting_times(
            duration_minutes=request.duration_minutes,
            date_preference=request.date_preference,
            max_suggestions=request.max_suggestions
        )
        return {"success": True, "suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/calendar/check-conflicts")
async def check_calendar_conflicts(request: ConflictCheckRequest):
    """Kontrollera konflikter för en föreslagen tid"""
    try:
        result = calendar_service.check_conflicts(
            start_time=request.start_time,
            end_time=request.end_time,
            exclude_event_id=request.exclude_event_id
        )
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/calendar/events")
async def create_enhanced_calendar_event(request: EnhancedCalendarEventRequest):
    """
    Enhanced calendar event creation with robust Swedish datetime parsing
    Uses Pydantic validation with comprehensive error handling
    """
    try:
        # Extract parsed datetime from validated request
        start_dt = request.start_time.parsed_datetime
        end_dt = request.end_time.parsed_datetime if request.end_time else None
        
        # Convert to string format for existing calendar service
        start_str = start_dt.isoformat() if start_dt else request.start_time.raw_input
        end_str = end_dt.isoformat() if end_dt and end_dt else None
        
        result = calendar_service.create_event(
            title=request.title,
            start_time=start_str,
            end_time=end_str,
            description=request.description,
            attendees=None,  # Could be extended
            check_conflicts_first=True
        )
        
        return {
            "success": True, 
            "message": result,
            "parsed_datetime": {
                "start": {
                    "original": request.start_time.raw_input,
                    "parsed": start_dt.isoformat() if start_dt else None,
                    "confidence": request.start_time.confidence,
                    "is_relative": request.start_time.is_relative
                },
                "end": {
                    "original": request.end_time.raw_input if request.end_time else None,
                    "parsed": end_dt.isoformat() if end_dt else None,
                    "confidence": request.end_time.confidence if request.end_time else None,
                    "is_relative": request.end_time.is_relative if request.end_time else None
                } if request.end_time else None
            }
        }
        
    except SwedishDateTimeValidationError as e:
        # This will be handled by our error handlers
        raise e
    except Exception as e:
        logger.exception("Enhanced calendar event creation failed")
        raise HTTPException(status_code=500, detail=f"Calendar service error: {str(e)}")


@app.post("/api/v2/chat/validate-datetime")  
async def validate_datetime_endpoint(request: ChatMessage):
    """
    Endpoint to validate Swedish datetime expressions in chat messages
    Useful for testing and debugging datetime parsing
    """
    response = {
        "content": request.content,
        "datetime_detected": request.swedish_datetime is not None
    }
    
    if request.swedish_datetime:
        response["datetime_info"] = {
            "raw_input": request.swedish_datetime.raw_input,
            "parsed": request.swedish_datetime.parsed_datetime.isoformat() if request.swedish_datetime.parsed_datetime else None,
            "confidence": request.swedish_datetime.confidence,
            "is_relative": request.swedish_datetime.is_relative,
            "format_used": request.swedish_datetime.format_used
        }
    
    return response


app.include_router(router)

# Kör preflight-kontroller vid startup
@app.on_event("startup")
async def startup_event():
    """Kör preflight-kontroller när servern startar"""
    try:
        logger.info("Running preflight checks...")
        all_passed, results = run_preflight_checks()
        log_preflight_results(results)
        
        if not all_passed:
            logger.error("Preflight checks failed - server may not work correctly")
        else:
            logger.info("All preflight checks passed - server ready")
            
    except Exception as e:
        logger.error(f"Error during preflight checks: {e}")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
MEMORY_PATH = os.path.join(DATA_DIR, "alice.db")
memory = MemoryStore(MEMORY_PATH)
bandit = EpsilonGreedyBandit(memory)


class AliceCommand(BaseModel):
    type: str = Field(..., description="Command type, e.g., SHOW_MODULE, HIDE_OVERLAY, OPEN_VIDEO")
    payload: Optional[Dict[str, Any]] = None


class AliceResponse(BaseModel):
    ok: bool
    message: str
    ts: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    command: Optional[AliceCommand] = None


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize to speech")
    voice: str = Field(default="sv_SE-nst-medium", description="Voice model to use")
    speed: float = Field(default=1.0, description="Speech speed multiplier", ge=0.5, le=2.0)
    emotion: Optional[str] = Field(default=None, description="Emotional tone: neutral, happy, calm, confident, friendly")
    personality: Optional[str] = Field(default="alice", description="Personality preset: alice, formal, casual")
    pitch: float = Field(default=1.0, description="Voice pitch multiplier", ge=0.8, le=1.2)
    volume: float = Field(default=1.0, description="Audio volume", ge=0.1, le=1.0)
    cache: bool = Field(default=True, description="Use cached audio if available")


class RealtimeSessionRequest(BaseModel):
    """Request för OpenAI Realtime ephemeral session"""
    model: Optional[str] = Field(default="gpt-4o-realtime-preview", description="OpenAI Realtime model")
    voice: Optional[str] = Field(default="nova", description="Voice model: alloy, echo, fable, onyx, nova, shimmer")
    instructions: Optional[str] = Field(default=None, description="Custom instructions for the session")
    modalities: Optional[List[str]] = Field(default=["text", "audio"], description="Supported modalities")
    input_audio_format: Optional[str] = Field(default="pcm16", description="Input audio format")
    output_audio_format: Optional[str] = Field(default="pcm16", description="Output audio format")
    temperature: Optional[float] = Field(default=0.8, ge=0.0, le=2.0, description="Response randomness")
    max_response_output_tokens: Optional[int] = Field(default=4096, description="Max tokens in response")


class RealtimeSessionResponse(BaseModel):
    """Response för ephemeral session creation"""
    client_secret: Dict[str, Any]
    expires_at: int
    session_config: Dict[str, Any]


class OpenAITTSRequest(BaseModel):
    """Request för OpenAI TTS streaming"""
    text: str = Field(..., description="Text to synthesize")
    model: Optional[str] = Field(default="tts-1", description="TTS model: tts-1 or tts-1-hd")
    voice: Optional[str] = Field(default="nova", description="Voice: alloy, echo, fable, onyx, nova, shimmer") 
    speed: Optional[float] = Field(default=1.0, ge=0.25, le=4.0, description="Speech speed")
    response_format: Optional[str] = Field(default="mp3", description="Audio format: mp3, opus, aac, flac, wav, pcm")
    stream: bool = Field(default=True, description="Stream audio response")


@app.get("/api/health")
async def health() -> Dict[str, Any]:
    """Enhanced health endpoint with detailed system status"""
    try:
        # Test database connection
        db_status = memory.ping()
        
        # Test external service availability (basic checks)
        services_status = {
            "ollama": "unknown",  # Would need actual connection test
            "tts": "ok",  # Basic assumption for now
            "stt": "ok"   # Basic assumption for now  
        }
        
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "2.0.0",
            "database": {
                "status": "ok" if db_status else "error",
                "ping": db_status
            },
            "features": {
                "harmony": USE_HARMONY,
                "tools": USE_TOOLS,
                "voice": True,
                "tts": True
            },
            "services": services_status
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }


@app.get("/api/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Professional metrics endpoint with comprehensive system data"""
    try:
        # Get application metrics
        app_metrics = metrics.snapshot()
        
        # System info with fallback if psutil not available
        system_metrics = {}
        if psutil:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            system_metrics = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory": {
                    "used_mb": round(memory_info.rss / 1024 / 1024, 2),
                    "percent": process.memory_percent()
                }
            }
        else:
            system_metrics = {
                "cpu_percent": "unavailable",
                "memory": {"used_mb": "unavailable", "percent": "unavailable"}
            }
        
        # System info
        import sys
        system_metrics.update({
            "system": {
                "python_version": sys.version.split()[0],
                "platform": sys.platform,
                "uptime_seconds": time.time() - getattr(get_metrics, '_start_time', time.time())
            }
        })
        
        # Store start time for uptime calculation
        if not hasattr(get_metrics, '_start_time'):
            get_metrics._start_time = time.time()
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "application": app_metrics,
            "system": system_metrics,
            "features": {
                "harmony_enabled": USE_HARMONY,
                "tools_enabled": USE_TOOLS
            }
        }
        
    except Exception as e:
        logger.error(f"Metrics collection error: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": f"Metrics collection failed: {str(e)}",
            "status": "partial"
        }


@app.post("/api/tts/synthesize")
async def text_to_speech(request: TTSRequest):
    """Enhanced Swedish text-to-speech with emotion, personality, and caching"""
    try:
        # Use enhanced TTS handler
        result = await enhanced_tts.synthesize_enhanced(request)
        return result
        
    except Exception as e:
        logger.error(f"Enhanced TTS error: {str(e)}")
        # Fallback to basic TTS if enhanced fails
        return await _fallback_basic_tts(request)

async def _fallback_basic_tts(request: TTSRequest):
    """Fallback basic TTS implementation"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        model_path = f"models/tts/{request.voice}.onnx"
        if not os.path.exists(model_path):
            available_voices = ["sv_SE-nst-medium", "sv_SE-nst-high", "sv_SE-lisa-medium"]
            return {"error": f"Voice model {request.voice} not found", "available": available_voices}
        
        cmd = [
            "python", "-m", "piper",
            "--model", model_path,
            "--output_file", temp_path
        ]
        
        if request.speed != 1.0:
            cmd.extend(["--speed", str(request.speed)])
        
        process = subprocess.run(
            cmd,
            input=request.text,
            text=True,
            capture_output=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if process.returncode != 0:
            logger.error(f"Fallback Piper TTS failed: {process.stderr}")
            return {"error": "TTS synthesis failed", "details": process.stderr}
        
        with open(temp_path, 'rb') as f:
            audio_data = f.read()
        
        os.unlink(temp_path)
        
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        return {
            "success": True,
            "audio_data": audio_b64,
            "format": "wav",
            "voice": request.voice,
            "text": request.text,
            "fallback": True
        }
        
    except Exception as e:
        logger.error(f"Fallback TTS error: {str(e)}")
        return {"error": "TTS synthesis failed", "details": str(e)}


@app.get("/api/tts/voices")
async def get_available_voices():
    """Get available TTS voices with their capabilities"""
    available_voices = []
    
    for voice_id, voice_info in enhanced_tts.voice_models.items():
        model_path = f"models/tts/{voice_id}.onnx"
        is_available = os.path.exists(model_path)
        
        if is_available:
            available_voices.append({
                "id": voice_id,
                "name": voice_id.replace("_", " ").replace("-", " ").title(),
                "language": "Swedish",
                "quality": voice_info["quality"],
                "gender": voice_info["gender"],
                "naturalness": voice_info["naturalness"],
                "supported_emotions": list(enhanced_tts.emotion_settings.keys()),
                "supported_personalities": list(enhanced_tts.personality_presets.keys())
            })
    
    return {
        "voices": available_voices,
        "default_voice": "sv_SE-nst-medium",
        "emotions": list(enhanced_tts.emotion_settings.keys()),
        "personalities": list(enhanced_tts.personality_presets.keys())
    }


@app.get("/api/tts/personality/{personality}")
async def get_personality_settings(personality: str):
    """Get personality-specific voice settings"""
    if personality not in enhanced_tts.personality_presets:
        raise HTTPException(status_code=404, detail=f"Personality '{personality}' not found")
    
    preset = enhanced_tts.personality_presets[personality]
    return {
        "personality": personality,
        "settings": preset,
        "description": {
            "alice": "Energisk, vänlig AI-assistent med naturlig svenska",
            "formal": "Professionell, tydlig och auktoritativ ton",
            "casual": "Avslappnad, uttrycksfull och konversationell"
        }.get(personality, "Anpassad personlighet")
    }


@app.post("/api/tts/stream")
async def stream_tts(request: TTSRequest):
    """Streaming TTS for faster response times"""
    async def generate_audio_stream():
        try:
            # Apply personality settings
            settings = enhanced_tts.apply_personality_settings(request)
            selected_voice = enhanced_tts.select_best_voice(request.voice)
            
            # Check cache first for instant response
            cache_key = enhanced_tts.get_cache_key(
                request.text, selected_voice, settings["speed"], 
                settings["emotion"], request.personality, settings["pitch"]
            )
            
            if request.cache:
                cached_audio = enhanced_tts.get_cached_audio(cache_key)
                if cached_audio:
                    # Stream cached audio immediately
                    yield cached_audio
                    return
            
            # Generate new audio
            audio_data = await enhanced_tts._generate_audio(request.text, selected_voice, settings)
            
            # Apply quick normalization (faster than full enhancement)
            normalized_audio = audio_processor.normalize_audio_levels(audio_data)
            
            # Cache for future use
            if request.cache:
                enhanced_tts.cache_audio(cache_key, normalized_audio)
            
            yield normalized_audio
            
        except Exception as e:
            logger.error(f"Streaming TTS failed: {e}")
            # Return error as audio metadata (client should handle)
            yield b''
    
    return StreamingResponse(
        generate_audio_stream(),
        media_type="audio/wav",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Voice-Model": request.voice,
            "X-Personality": request.personality,
            "X-Emotion": request.emotion or "friendly"
        }
    )


@app.post("/api/alice/command", response_model=AliceResponse)
async def alice_command(cmd: AliceCommand) -> AliceResponse:
    # Persist basic interaction for future learning
    memory.append_event("command", json.dumps(cmd.dict(), ensure_ascii=False))
    # Extra: spara USER_QUERY som textminne
    try:
        if (cmd.type or "").upper() == "USER_QUERY":
            q = (cmd.payload or {}).get("query", "")
            if q:
                memory.upsert_text_memory_single_single(q, score=0.0, tags_json=json.dumps({"source": "user_query"}, ensure_ascii=False))
    except Exception:
        pass
    # simulate-first risk gating
    scores = simulate_first(cmd.dict())
    logger.info("/api/jarvis/command type=%s risk=%.3f", cmd.type, scores.get("risk", 1.0))
    if scores.get("risk", 1.0) > 0.8:
        return AliceResponse(ok=False, message="Command blocked by safety", command=cmd)
    # Optional WS broadcast for HUD when receiving explicit dispatch commands
    try:
        ctype = (cmd.type or "").lower()
        if ctype in {"dispatch", "hud"} and isinstance(cmd.payload, dict):
            logger.info("broadcasting hud_command via WS")
            await hub.broadcast({"type": "hud_command", "command": cmd.payload})
    except Exception:
        logger.exception("ws broadcast failed")
    return AliceResponse(ok=True, message="Command received", command=cmd)


class ToolPickBody(BaseModel):
    candidates: List[str]


@app.post("/api/decision/pick_tool")
async def pick_tool(body: ToolPickBody) -> Dict[str, Any]:
    choice = bandit.pick(body.candidates)
    return {"ok": True, "tool": choice}


class ExecToolBody(BaseModel):
    name: str
    args: Optional[Dict[str, Any]] = None


@app.post("/api/tools/exec")
async def tools_exec(body: ExecToolBody) -> Dict[str, Any]:
    if not USE_TOOLS:
        return {"ok": False, "error": "tools_disabled"}
    res = validate_and_execute_tool(body.name, body.args or {}, memory)
    # Enkel telemetri
    try:
        if res.get("ok"):
            memory.update_tool_stats(body.name, success=True)
        else:
            memory.update_tool_stats(body.name, success=False)
    except Exception:
        pass
    return res


# Använd core-modulerna istället

@app.get("/api/tools/spec")
async def tools_spec() -> Dict[str, Any]:
    """Hämta verktygsspecifikationer för Harmony"""
    from core.tool_specs import build_harmony_tool_specs
    return {"ok": True, "specs": build_harmony_tool_specs()}

@app.get("/api/tools/registry")
async def tools_registry() -> Dict[str, Any]:
    """Hämta registrerade verktyg från registry"""
    from core.tool_registry import EXECUTORS
    return {"ok": True, "executors": sorted(list(EXECUTORS.keys()))}

@app.get("/api/tools/enabled")
async def tools_enabled() -> Dict[str, Any]:
    """Hämta aktiverade verktyg från miljövariabeln"""
    from core.tool_specs import enabled_tools
    return {"ok": True, "enabled": enabled_tools()}


class ChatBody(BaseModel):
    prompt: str
    model: Optional[str] = "gpt-oss:20b"
    stream: Optional[bool] = False
    provider: Optional[str] = "auto"  # 'local' | 'openai' | 'auto'
    raw: Optional[bool] = False         # when True → no RAG/context, clean reply
    context: Optional[dict] = None      # HUD context: weather, location, time, etc.


@app.post("/api/chat")
async def chat(body: ChatBody) -> Dict[str, Any]:
    logger.info("/api/chat model=%s prompt_len=%d provider=%s context=%s", 
                body.model, len(body.prompt or ""), body.provider, body.context is not None)
    t_request = time.time()
    
    # Generate session ID based on model and time
    import hashlib
    session_id = hashlib.md5(f"{body.model or 'default'}_{int(t_request/3600)}".encode()).hexdigest()[:8]
    
    # Track user message in conversation context
    try:
        memory.add_conversation_turn(session_id, "user", body.prompt or "")
    except Exception:
        pass
    
    # Minimal RAG: hämta relevanta textminnen via LIKE och inkludera i prompten
    if MINIMAL_MODE or bool(body.raw):
        contexts = []
        ctx_payload = []
        full_prompt = f"Besvara på svenska.\n\nFråga: {body.prompt}\nSvar:"
    else:
        # Enhanced RAG retrieval with expanded search and reranking
        try:
            # Swedish synonyms and aliases for better matching
            synonyms = {
                'agent core': ['Agent Core v1', 'autonomous workflow', 'planner', 'executor', 'orchestrator'],
                'förmågor': ['vad kan du göra', 'funktioner', 'kapaciteter', 'färdigheter'],
                'response time': ['svarstid', 'latens', 'prestanda', 'snabb'],
                'embedding': ['text-embedding', 'semantisk', 'vektor', 'embedding-modell'],
                'chunk': ['chunking', 'uppdelning', 'segment', 'textstycke'],
                'dokument': ['document', 'fil', 'upload', 'ladda upp'],
                'format': ['filformat', 'filtyp', 'typ', 'extension'],
                'spotify': ['musik', 'spela', 'låt', 'musikuppspelning'],
                'kalender': ['calendar', 'möte', 'boka', 'schema', 'tid']
            }
            
            # Extract key words and expand with synonyms
            import re
            key_words = re.findall(r'\b\w+\b', body.prompt.lower())
            expanded_words = set(key_words)
            
            for word in key_words:
                if word in synonyms:
                    expanded_words.update(synonyms[word])
                # Also check if any synonym maps to this word
                for key, values in synonyms.items():
                    if word in [v.lower() for v in values]:
                        expanded_words.add(key)
                        expanded_words.update(values)
            
            # Search with expanded terms (increased limit for reranking)
            contexts = []
            for word in expanded_words:
                if len(word) > 2:  # Skip short words
                    word_results = memory.retrieve_text_memories(word, limit=10)  # Increased from 2 to 10
                    contexts.extend(word_results)
            
            # Remove duplicates and score by relevance
            seen_ids = set()
            scored_contexts = []
            
            for ctx in contexts:
                if ctx['id'] not in seen_ids:
                    seen_ids.add(ctx['id'])
                    
                    # Calculate relevance score based on term frequency
                    text_lower = ctx['text'].lower()
                    score = 0
                    
                    # Boost for exact query matches
                    if body.prompt.lower() in text_lower:
                        score += 10
                    
                    # Boost for individual key words
                    for word in key_words:
                        if word in text_lower:
                            score += 2
                    
                    # Boost for synonyms
                    for word in expanded_words:
                        if word.lower() in text_lower:
                            score += 1
                    
                    # Boost for headers and structured content
                    if any(marker in text_lower for marker in ['#', '<h', '**', 'viktigt', 'exempel']):
                        score += 1
                        
                    ctx['relevance_score'] = score + ctx.get('score', 0)
                    scored_contexts.append(ctx)
            
            # Sort by relevance and apply quality threshold
            scored_contexts.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # Quality threshold - only include contexts with decent relevance
            MIN_RELEVANCE_SCORE = 2  # Require at least some keyword matches
            high_quality_contexts = [ctx for ctx in scored_contexts if ctx['relevance_score'] >= MIN_RELEVANCE_SCORE]
            
            if len(high_quality_contexts) >= 2:
                contexts = high_quality_contexts[:5]  # Use high-quality matches
            elif len(scored_contexts) >= 1 and scored_contexts[0]['relevance_score'] >= 1:
                contexts = scored_contexts[:3]  # Use best available matches
            else:
                # Very low relevance - suggest clarification
                contexts = []
                logger.info(f"Low relevance scores (max: {scored_contexts[0]['relevance_score'] if scored_contexts else 0}), suggesting clarification")
            
            logger.info(f"RAG memory retrieval found {len(contexts)} contexts (from {len(scored_contexts)} candidates, {len(high_quality_contexts)} high-quality) for query: {body.prompt[:50]}")
        except Exception as e:
            logger.warning(f"Primary memory retrieval failed: {e}")
            try:
                # Enhanced: använd conversation context för bättre retrieval
                contexts = memory.get_related_memories_from_context(session_id, body.prompt, limit=5)
                logger.info(f"Context-based retrieval found {len(contexts)} contexts")
            except Exception as e2:
                logger.warning(f"Context-based retrieval failed: {e2}")
                try:
                    contexts = memory.retrieve_text_bm25_recency(body.prompt, limit=5)
                    logger.info(f"BM25 retrieval found {len(contexts)} contexts")
                except Exception as e3:
                    logger.warning(f"BM25 retrieval failed: {e3}")
                    contexts = []
        ctx_text = "\n".join([f"- {it.get('text','')}" for it in (contexts or []) if it.get('text')])
        ctx_payload = [it.get('text','') for it in contexts[:3] if it.get('text')]
        logger.info(f"Built ctx_text length: {len(ctx_text)}, ctx_payload items: {len(ctx_payload)}")
        
        # Build HUD context information
        hud_context = ""
        if body.context:
            context_parts = []
            if body.context.get('weather'):
                context_parts.append(f"Aktuellt väder: {body.context['weather']}")
            if body.context.get('location'):
                context_parts.append(f"Plats: {body.context['location']}")
            if body.context.get('time'):
                context_parts.append(f"Tid: {body.context['time']}")
            if body.context.get('systemMetrics'):
                system_metrics = body.context['systemMetrics']
                context_parts.append(f"System: CPU {system_metrics.get('cpu', 0)}%, RAM {system_metrics.get('mem', 0)}%, Nätverk {system_metrics.get('net', 0)}%")
            if context_parts:
                hud_context = "Aktuell systeminfo:\n" + "\n".join(f"- {part}" for part in context_parts) + "\n\n"
        
        full_prompt = (
            hud_context +
            (("Relevanta minnen:\n" + ctx_text + "\n\n") if ctx_text else "")
        ) + f"Använd relevant kontext ovan vid behov. Besvara på svenska.\n\nFråga: {body.prompt}\nSvar:"
        logger.info(f"Final full_prompt length: {len(full_prompt)}, includes RAG: {bool(ctx_text)}")
    try:
        memory.append_event("chat.in", json.dumps({"prompt": body.prompt}, ensure_ascii=False))
    except Exception:
        pass
    # Välj provider
    provider = (body.provider or "auto").lower()
    last_error = None
    async def respond(text: str, used_provider: str, engine: Optional[str] = None) -> Dict[str, Any]:
        mem_id: Optional[int] = None
        try:
            tags = {"source": "chat", "model": body.model or "gpt-oss:20b", "provider": used_provider, "engine": engine}
            mem_id = memory.upsert_text_memory_single(text, score=0.0, tags_json=json.dumps(tags, ensure_ascii=False))
            memory.append_event("chat.out", json.dumps({"text": text, "memory_id": mem_id}, ensure_ascii=False))
            # Track assistant message in conversation context
            memory.add_conversation_turn(session_id, "assistant", text, mem_id)
        except Exception:
            pass
        return {"ok": True, "text": text, "memory_id": mem_id, "provider": used_provider, "engine": engine}

    # 1) Lokal (Ollama)
    async def try_local():
        try:
            t0 = time.time()
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={
                        "model": body.model or os.getenv("LOCAL_MODEL", "gpt-oss:20b"),
                        "prompt": (f"System: {_harmony_system_prompt()}\nDeveloper: {_harmony_developer_prompt()}\nUser: {full_prompt}\nSvar: ") if USE_HARMONY else f"System: Du heter Alice och är en svensk AI-assistent. Du är INTE ChatGPT. Presentera dig alltid som Alice. Svara på svenska.\n\nUser: {full_prompt}\nAlice:",
                        "stream": False,
                        "options": {
                            "num_predict": 256,  # Reduced from 512 for faster responses  
                            "temperature": HARMONY_TEMPERATURE_COMMANDS if USE_HARMONY else 0.3,
                            "num_ctx": 2048,     # Smaller context window for speed
                            "num_threads": -1,   # Use all available CPU cores
                            "repeat_penalty": 1.1,
                            "top_p": 0.9,
                            "top_k": 40
                        },
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    dt = (time.time() - t0) * 1000
                    logger.info("chat local ms=%.0f", dt)
                    raw_text = (data.get("response", "") or "").strip()
                    # Harmony: tolka ev. verktygsanrop innan FINAL-extraktion
                    if USE_TOOLS and USE_HARMONY:
                        call = _maybe_parse_tool_call(raw_text)
                        if call:
                            name = str(call.get("tool") or "").upper()
                            args = call.get("args") or {}
                            if is_tool_enabled(name):
                                t_tool = time.time()
                                res = validate_and_execute_tool(name, args, memory)
                                dt_tool = (time.time() - t_tool) * 1000
                                try:
                                    metrics.record_tool_call_attempted()
                                    if res.get("ok"):
                                        metrics.record_llm_hit()
                                        metrics.record_tool_call_latency(dt_tool)
                                    metrics.record_final_latency((time.time() - t_request) * 1000)
                                except Exception:
                                    pass
                                msg = _format_tool_confirmation(name, args)
                                resp = await respond(msg, used_provider="local", engine=(body.model or os.getenv("LOCAL_MODEL", "gpt-oss:20b")))
                                resp["meta"] = {"tool": {"name": name, "args": args, "source": "harmony", "executed": bool(res.get("ok")), "latency_ms": dt_tool}}
                                return resp
                    local_text = _extract_final(raw_text) if USE_HARMONY else raw_text
                    if USE_HARMONY:
                        try:
                            logger.debug("harmony.final.extracted provider=local len=%d", len(local_text))
                        except Exception:
                            pass
                    if not local_text:
                        return RuntimeError("local_empty")
                    return await respond(local_text, used_provider="local", engine=(body.model or os.getenv("LOCAL_MODEL", "gpt-oss:20b")))
        except Exception as e:
            return e
        return RuntimeError("local_failed")

    # 2) OpenAI
    async def try_openai():
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return RuntimeError("openai_key_missing")
        try:
            t0 = time.time()
            async with httpx.AsyncClient(timeout=25.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        "messages": (
                            [
                                {"role": "system", "content": _harmony_system_prompt()},
                                {"role": "developer", "content": _harmony_developer_prompt()},
                                {"role": "user", "content": full_prompt},
                            ] if USE_HARMONY else [
                                {"role": "system", "content": "Du är Alice. Svara på svenska och använd 'Relevanta minnen' om de hjälper."},
                                {"role": "user", "content": full_prompt},
                            ]
                        ),
                        "temperature": HARMONY_TEMPERATURE_COMMANDS if USE_HARMONY else 0.5,
                        "max_tokens": 256,
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    raw_text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
                    # Harmony: tolka ev. verktygsanrop innan FINAL-extraktion
                    if USE_TOOLS and USE_HARMONY:
                        call = _maybe_parse_tool_call(raw_text)
                        if call:
                            name = str(call.get("tool") or "").upper()
                            args = call.get("args") or {}
                            if is_tool_enabled(name):
                                t_tool = time.time()
                                res = validate_and_execute_tool(name, args, memory)
                                dt_tool = (time.time() - t_tool) * 1000
                                try:
                                    metrics.record_tool_call_attempted()
                                    if res.get("ok"):
                                        metrics.record_llm_hit()
                                        metrics.record_tool_call_latency(dt_tool)
                                    metrics.record_final_latency((time.time() - t_request) * 1000)
                                except Exception:
                                    pass
                                msg = _format_tool_confirmation(name, args)
                                resp = await respond(msg, used_provider="openai", engine=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
                                resp["meta"] = {"tool": {"name": name, "args": args, "source": "harmony", "executed": bool(res.get("ok")), "latency_ms": dt_tool}}
                                return resp
                    text = _extract_final(raw_text) if USE_HARMONY else raw_text
                    if USE_HARMONY:
                        try:
                            logger.debug("harmony.final.extracted provider=openai len=%d", len(text))
                        except Exception:
                            pass
                    dt = (time.time() - t0) * 1000
                    logger.info("chat openai ms=%.0f", dt)
                    return await respond(text, used_provider="openai", engine=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        except Exception as e:
            return e
        return RuntimeError("openai_failed")

    try:
        # Router-först: snabba intents exekveras direkt utan LLM om high-confidence
        plan = await _router_first_try(body.prompt)
        if plan and USE_TOOLS:
            name = str(plan.get("tool") or "")
            args = plan.get("params") or {}
            if not is_tool_enabled(name):
                logger.info("router tool disabled name=%s", name)
                raise RuntimeError("router_tool_disabled")
            t_tool = time.time()
            res = validate_and_execute_tool(name, args, memory)
            if res.get("ok"):
                metrics.record_router_hit()
                metrics.record_tool_call_attempted()
                dt_tool = (time.time() - t_tool) * 1000
                metrics.record_tool_call_latency(dt_tool)
                metrics.record_final_latency((time.time() - t_request) * 1000)
                msg = _format_tool_confirmation(name, args)
                return {
                    "ok": True,
                    "text": msg,
                    "memory_id": None,
                    "provider": "router",
                    "engine": None,
                    "meta": {
                        "tool": {
                            "name": (name or "").upper(),
                            "args": args,
                            "source": "router",
                            "executed": True,
                            "latency_ms": dt_tool,
                        }
                    },
                }
            # vid valideringsfel → fall-through till LLM
            metrics.record_tool_validation_failed()

        if provider == "local":
            res = await try_local()
            if isinstance(res, dict):
                return res
            # if local failed/empty under 'local', fall back to stub at end
            last_error = res
        elif provider == "openai":
            res = await try_openai()
            if isinstance(res, dict):
                return res
            last_error = res
        else:  # auto: race local vs openai
            t_local = asyncio.create_task(try_local())
            t_openai = asyncio.create_task(try_openai())
            done, pending = await asyncio.wait({t_local, t_openai}, return_when=asyncio.FIRST_COMPLETED)
            for d in done:
                res = d.result()
                if isinstance(res, dict) and (res.get("text") or "").strip():
                    # cancel the slower one
                    for p in pending:
                        p.cancel()
                    metrics.record_llm_hit()
                    metrics.record_final_latency((time.time() - t_request) * 1000)
                    return res
                last_error = res
            # if first completed wasn't dict, wait the other
            for p in pending:
                try:
                    res = await p
                    if isinstance(res, dict) and (res.get("text") or "").strip():
                        metrics.record_llm_hit()
                        metrics.record_final_latency((time.time() - t_request) * 1000)
                        return res
                    last_error = res
                except asyncio.CancelledError:
                    pass
    except Exception:
        logger.exception("/api/chat error")
    # Stub: visa vilken kontext som skulle ha använts, för verifiering i UI
    stub_ctx = ("\n\n[Kontext]\n" + ctx_text) if ctx_text else ""
    metrics.record_final_latency((time.time() - t_request) * 1000)
    return {"ok": True, "text": f"[stub] {body.prompt}{stub_ctx}", "memory_id": None, "provider": provider, "engine": None, "contexts": ctx_payload}


@app.post("/api/chat/stream")
async def chat_stream(body: ChatBody):
    # Förbered RAG-kontekst likt /api/chat
    if MINIMAL_MODE or bool(body.raw):
        contexts = []
        ctx_payload = []
        full_prompt = f"Besvara på svenska.\n\nFråga: {body.prompt}\nSvar:"
    else:
        # Temporarily use simple LIKE-based retrieval since BM25 has issues
        try:
            contexts = memory.retrieve_text_memories(body.prompt, limit=5)
        except Exception:
            try:
                contexts = memory.retrieve_text_bm25_recency(body.prompt, limit=5)
            except Exception:
                contexts = []
        ctx_text = "\n".join([f"- {it.get('text','')}" for it in (contexts or []) if it.get('text')])
        ctx_payload = [it.get('text','') for it in (contexts or []) if it.get('text')][:3]
        
        # Build HUD context information
        hud_context = ""
        if body.context:
            context_parts = []
            if body.context.get('weather'):
                context_parts.append(f"Aktuellt väder: {body.context['weather']}")
            if body.context.get('location'):
                context_parts.append(f"Plats: {body.context['location']}")
            if body.context.get('time'):
                context_parts.append(f"Tid: {body.context['time']}")
            if body.context.get('systemMetrics'):
                system_metrics = body.context['systemMetrics']
                context_parts.append(f"System: CPU {system_metrics.get('cpu', 0)}%, RAM {system_metrics.get('mem', 0)}%, Nätverk {system_metrics.get('net', 0)}%")
            if context_parts:
                hud_context = "Aktuell systeminfo:\n" + "\n".join(f"- {part}" for part in context_parts) + "\n\n"
        
        full_prompt = (
            hud_context +
            (("Relevanta minnen:\n" + ctx_text + "\n\n") if ctx_text else "")
        ) + f"Använd relevant kontext ovan vid behov. Besvara på svenska.\n\nFråga: {body.prompt}\nSvar:"

    provider = (body.provider or "auto").lower()

    async def gen():
        t_request = time.time()
        final_text = ""
        used_provider = None
        emitted = False
        # För Harmony-streaming: buffra och extrahera endast [FINAL]...[/FINAL]
        final_started = False
        final_ended = False
        buffer_text = ""

        async def sse_send(obj):
            yield f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

        async def openai_stream():
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    r = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={
                            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                            "messages": (
                                [
                                    {"role": "system", "content": _harmony_system_prompt()},
                                    {"role": "developer", "content": _harmony_developer_prompt()},
                                    {"role": "user", "content": full_prompt},
                                ] if USE_HARMONY else [
                                    {"role": "system", "content": "Du är Alice. Svara på svenska och använd 'Relevanta minnen' om de hjälper."},
                                    {"role": "user", "content": full_prompt},
                                ]
                            ),
                            "temperature": HARMONY_TEMPERATURE_COMMANDS if USE_HARMONY else 0.5,
                            "stream": True,
                            "max_tokens": 256,
                        },
                    )
                    if r.status_code != 200:
                        return
                    nonlocal final_text, used_provider, emitted
                    used_provider = "openai"
                    harmony_tool_handled = False
                    async for line in r.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data = line[len("data: "):].strip()
                            if data == "[DONE]":
                                break
                            try:
                                obj = json.loads(data)
                                raw_delta = (((obj.get("choices") or [{}])[0]).get("delta") or {}).get("content")
                                if not raw_delta:
                                    continue
                                if USE_HARMONY:
                                    nonlocal final_started, final_ended, buffer_text
                                    buffer_text += raw_delta
                                    # Försök upptäcka Harmony-tool innan FINAL
                                    if USE_TOOLS and not harmony_tool_handled:
                                        if "[TOOL_CALL]" in buffer_text and "}" in buffer_text:
                                            call = _maybe_parse_tool_call(buffer_text)
                                            if call:
                                                name = str(call.get("tool") or "").upper()
                                                args = call.get("args") or {}
                                                if is_tool_enabled(name):
                                                    t_tool = time.time()
                                                    res = validate_and_execute_tool(name, args, memory)
                                                    dt_tool = (time.time() - t_tool) * 1000
                                                    meta = {"tool": {"name": name, "args": args, "source": "harmony", "executed": bool(res.get("ok")), "latency_ms": dt_tool}}
                                                    async for out in sse_send({"type": "meta", "meta": meta}):
                                                        yield out
                                                    if res.get("ok"):
                                                        emitted = True
                                                        if len(final_text) == 0:
                                                            try:
                                                                from metrics import metrics as _metrics
                                                                _metrics.record_first_token((time.time() - t_request) * 1000)
                                                            except Exception:
                                                                pass
                                                        confirm = _format_tool_confirmation(name, args)
                                                        final_text += confirm
                                                        async for out in sse_send({"type": "chunk", "text": confirm}):
                                                            yield out
                                                        # done och mem
                                                        mem_id = None
                                                        try:
                                                            tags = {"source": "chat", "provider": "openai"}
                                                            mem_id = memory.upsert_text_memory_single(confirm, score=0.0, tags_json=json.dumps(tags, ensure_ascii=False))
                                                        except Exception:
                                                            pass
                                                        try:
                                                            from metrics import metrics as _metrics
                                                            _metrics.record_tool_call_attempted()
                                                            _metrics.record_tool_call_latency(dt_tool)
                                                            _metrics.record_final_latency((time.time() - t_request) * 1000)
                                                        except Exception:
                                                            pass
                                                        async for out in sse_send({"type": "done", "provider": "openai", "memory_id": mem_id}):
                                                            yield out
                                                        return
                                                    harmony_tool_handled = True
                                    out_chunk = ""
                                    if not final_started:
                                        si = buffer_text.find("[FINAL]")
                                        if si != -1:
                                            final_started = True
                                            buffer_text = buffer_text[si + len("[FINAL]"):]
                                            try:
                                                logger.debug("harmony.final.start provider=openai")
                                            except Exception:
                                                pass
                                    if final_started and not final_ended:
                                        ei = buffer_text.find("[/FINAL]")
                                        if ei != -1:
                                            out_chunk = buffer_text[:ei]
                                            final_ended = True
                                            buffer_text = ""
                                            try:
                                                logger.debug("harmony.final.end provider=openai")
                                            except Exception:
                                                pass
                                        else:
                                            out_chunk = buffer_text
                                            buffer_text = ""
                                    if out_chunk:
                                        emitted = True
                                        if len(final_text) == 0:
                                            # first token latency
                                            try:
                                                from metrics import metrics as _metrics
                                                _metrics.record_first_token((time.time() - t_request) * 1000)
                                            except Exception:
                                                pass
                                        final_text += out_chunk
                                        async for out in sse_send({"type": "chunk", "text": out_chunk}):
                                            yield out
                                else:
                                    emitted = True
                                    if len(final_text) == 0:
                                        try:
                                            from metrics import metrics as _metrics
                                            _metrics.record_first_token((time.time() - t_request) * 1000)
                                        except Exception:
                                            pass
                                    final_text += raw_delta
                                    async for out in sse_send({"type": "chunk", "text": raw_delta}):
                                        yield out
                            except Exception:
                                continue
            except Exception:
                return

        async def local_stream():
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    r = await client.post(
                        "http://127.0.0.1:11434/api/generate",
                        json={
                            "model": body.model or os.getenv("LOCAL_MODEL", "gpt-oss:20b"),
                            "prompt": (f"System: {_harmony_system_prompt()}\nDeveloper: {_harmony_developer_prompt()}\nUser: {full_prompt}\nSvar: ") if USE_HARMONY else f"System: Du heter Alice och är en svensk AI-assistent. Du är INTE ChatGPT. Presentera dig alltid som Alice. Svara på svenska.\n\nUser: {full_prompt}\nAlice:",
                            "stream": True,
                            "options": {
                                "num_predict": 128,  # Even smaller for streaming
                                "temperature": HARMONY_TEMPERATURE_COMMANDS if USE_HARMONY else 0.3,
                                "num_ctx": 2048,
                                "num_threads": -1,
                                "repeat_penalty": 1.1,
                                "top_p": 0.9,
                                "top_k": 40
                            },
                        },
                    )
                    if r.status_code != 200:
                        return
                    nonlocal final_text, used_provider, emitted
                    used_provider = "local"
                    harmony_tool_handled = False
                    async for line in r.aiter_lines():
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            if obj.get("done"):
                                break
                            raw_delta = obj.get("response")
                            if not raw_delta:
                                continue
                            if USE_HARMONY:
                                nonlocal final_started, final_ended, buffer_text
                                buffer_text += raw_delta
                                # Försök upptäcka Harmony-tool innan FINAL
                                if USE_TOOLS and not harmony_tool_handled:
                                    if "[TOOL_CALL]" in buffer_text and "}" in buffer_text:
                                        call = _maybe_parse_tool_call(buffer_text)
                                        if call:
                                            name = str(call.get("tool") or "").upper()
                                            args = call.get("args") or {}
                                            if is_tool_enabled(name):
                                                t_tool = time.time()
                                                res = validate_and_execute_tool(name, args, memory)
                                                dt_tool = (time.time() - t_tool) * 1000
                                                meta = {"tool": {"name": name, "args": args, "source": "harmony", "executed": bool(res.get("ok")), "latency_ms": dt_tool}}
                                                async for out in sse_send({"type": "meta", "meta": meta}):
                                                    yield out
                                                if res.get("ok"):
                                                    emitted = True
                                                    if len(final_text) == 0:
                                                        try:
                                                            from metrics import metrics as _metrics
                                                            _metrics.record_first_token((time.time() - t_request) * 1000)
                                                        except Exception:
                                                            pass
                                                    confirm = _format_tool_confirmation(name, args)
                                                    final_text += confirm
                                                    async for out in sse_send({"type": "chunk", "text": confirm}):
                                                        yield out
                                                    mem_id = None
                                                    try:
                                                        tags = {"source": "chat", "provider": "local"}
                                                        mem_id = memory.upsert_text_memory_single(confirm, score=0.0, tags_json=json.dumps(tags, ensure_ascii=False))
                                                    except Exception:
                                                        pass
                                                    try:
                                                        from metrics import metrics as _metrics
                                                        _metrics.record_tool_call_attempted()
                                                        _metrics.record_tool_call_latency(dt_tool)
                                                        _metrics.record_final_latency((time.time() - t_request) * 1000)
                                                    except Exception:
                                                        pass
                                                    async for out in sse_send({"type": "done", "provider": "local", "memory_id": mem_id}):
                                                        yield out
                                                    return
                                                harmony_tool_handled = True
                                out_chunk = ""
                                if not final_started:
                                    si = buffer_text.find("[FINAL]")
                                    if si != -1:
                                        final_started = True
                                        buffer_text = buffer_text[si + len("[FINAL]"):]
                                        try:
                                            logger.debug("harmony.final.start provider=local")
                                        except Exception:
                                            pass
                                if final_started and not final_ended:
                                    ei = buffer_text.find("[/FINAL]")
                                    if ei != -1:
                                        out_chunk = buffer_text[:ei]
                                        final_ended = True
                                        buffer_text = ""
                                        try:
                                            logger.debug("harmony.final.end provider=local")
                                        except Exception:
                                            pass
                                    else:
                                        out_chunk = buffer_text
                                        buffer_text = ""
                                if out_chunk:
                                    emitted = True
                                    if len(final_text) == 0:
                                        try:
                                            from metrics import metrics as _metrics
                                            _metrics.record_first_token((time.time() - t_request) * 1000)
                                        except Exception:
                                            pass
                                    final_text += out_chunk
                                    async for out in sse_send({"type": "chunk", "text": out_chunk}):
                                        yield out
                            else:
                                emitted = True
                                if len(final_text) == 0:
                                    try:
                                        from metrics import metrics as _metrics
                                        _metrics.record_first_token((time.time() - t_request) * 1000)
                                    except Exception:
                                        pass
                                final_text += raw_delta
                                async for out in sse_send({"type": "chunk", "text": raw_delta}):
                                    yield out
                        except Exception:
                            continue
            except Exception:
                return

        # skicka meta först
        async for out in sse_send({"type": "meta", "contexts": ctx_payload}):
            yield out

        # Router-först även för streaming: exekvera verktyg direkt och streama endast final-bekräftelse
        if USE_TOOLS:
            plan = await _router_first_try(body.prompt)
            if plan:
                name = str(plan.get("tool") or "")
                args = plan.get("params") or {}
                if not is_tool_enabled(name):
                    async for out in sse_send({"type": "tool_called", "name": name, "args": args, "disabled": True}):
                        yield out
                    # Fortsätt till LLM-stream
                else:
                    # Skicka standardiserat meta-event före final
                    meta = {
                        "tool": {
                            "name": (name or "").upper(),
                            "args": args,
                            "source": "router",
                            "executed": bool(res.get("ok")),
                        }
                    }
                    async for out in sse_send({"type": "meta", "meta": meta}):
                        yield out
                    t_tool = time.time()
                    res = validate_and_execute_tool(name, args, memory)
                    async for out in sse_send({"type": "tool_result", "ok": bool(res.get("ok")), "result": res, "tool": (name or "").upper(), "args": args}):
                        yield out
                    if res.get("ok"):
                        confirm = _format_tool_confirmation(name, args)
                        emitted = True
                        metrics.record_router_hit()
                        metrics.record_tool_call_attempted()
                        metrics.record_tool_call_latency((time.time() - t_tool) * 1000)
                        metrics.record_first_token((time.time() - t_request) * 1000)
                        final_text += confirm
                        async for out in sse_send({"type": "chunk", "text": confirm}):
                            yield out
                        mem_id = None
                        try:
                            tags = {"source": "chat", "provider": "router"}
                            mem_id = memory.upsert_text_memory_single(confirm, score=0.0, tags_json=json.dumps(tags, ensure_ascii=False))
                        except Exception:
                            pass
                        async for out in sse_send({"type": "done", "provider": "router", "memory_id": mem_id}):
                            yield out
                        return
                async for out in sse_send({"type": "meta", "meta": {"tool": {"name": (name or "").upper(), "args": args, "source": "router", "executed": False}}}):
                    yield out
                res = validate_and_execute_tool(name, args, memory)
                # Efter exekvering uppdateras executed=true via final/done, chunk nedan räcker för UI
                if res.get("ok"):
                    confirm = _format_tool_confirmation(name, args)
                    emitted = True
                    final_text += confirm
                    async for out in sse_send({"type": "chunk", "text": confirm}):
                        yield out
                    mem_id = None
                    try:
                        tags = {"source": "chat", "provider": "router"}
                        mem_id = memory.upsert_text_memory_single(confirm, score=0.0, tags_json=json.dumps(tags, ensure_ascii=False))
                    except Exception:
                        pass
                    async for out in sse_send({"type": "done", "provider": "router", "memory_id": mem_id}):
                        yield out
                    return

        if provider == "openai":
            async for out in openai_stream():
                yield out
        elif provider == "local":
            async for out in local_stream():
                yield out
        else:
            # auto: försök online först, sedan lokal om inget kom
            async for out in openai_stream():
                yield out
            if not emitted:
                async for out in local_stream():
                    yield out

        # done-event och minnesupsert
        mem_id = None
        try:
            if final_text:
                tags = {"source": "chat", "provider": used_provider}
                mem_id = memory.upsert_text_memory_single(final_text, score=0.0, tags_json=json.dumps(tags, ensure_ascii=False))
        except Exception:
            pass
        try:
            from metrics import metrics as _metrics
            _metrics.record_final_latency((time.time() - t_request) * 1000)
        except Exception:
            pass
        async for out in sse_send({"type": "done", "provider": used_provider, "memory_id": mem_id}):
            yield out

    return StreamingResponse(gen(), media_type="text/event-stream")


# WebSocket endpoint for real-time voice conversation
@app.websocket("/ws/voice/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str):
    """Real-time voice conversation with Alice using hybrid API/local approach"""
    voice_mgr = get_voice_manager(memory)
    await voice_mgr.handle_voice_session(websocket, session_id)


class ActBody(BaseModel):
    prompt: Optional[str] = ""
    model: Optional[str] = "gpt-oss:20b"
    allow: Optional[List[str]] = None  # e.g. ["SHOW_MODULE","HIDE_OVERLAY","OPEN_VIDEO"]
    provider: Optional[str] = "auto"  # 'local' | 'openai' | 'auto'
    dry_run: Optional[bool] = False


def _validate_hud_command(cmd: Dict[str, Any], allow: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    if not isinstance(cmd, dict):
        return None
    ctype = (cmd.get("type") or "").upper()
    if allow and ctype not in allow:
        return None
    if ctype == "SHOW_MODULE":
        # Normalisera svenska/alias -> interna moduler
        raw = (cmd.get("module") or "").strip().lower()
        alias = {
            "kalender": "calendar",
            "calendar": "calendar",
            "mail": "mail",
            "mejl": "mail",
            "email": "mail",
            "finans": "finance",
            "ekonomi": "finance",
            "finance": "finance",
            "påminnelser": "reminders",
            "paminnelser": "reminders",
            "reminders": "reminders",
            "plånbok": "wallet",
            "planbok": "wallet",
            "wallet": "wallet",
            "video": "video",
        }
        mod = alias.get(raw, raw)
        if mod in {"calendar","mail","finance","reminders","wallet","video"}:
            return {"type": "SHOW_MODULE", "module": mod}
        return None
    if ctype == "HIDE_OVERLAY":
        return {"type": "HIDE_OVERLAY"}
    if ctype == "OPEN_VIDEO":
        src = cmd.get("source") or {"kind": "webcam"}
        if isinstance(src, str):
            src = {"kind": src}
        if isinstance(src, dict):
            return {"type": "OPEN_VIDEO", "source": {"kind": (src.get("kind") or "webcam")}}
    return None


@app.post("/api/ai/act")
async def ai_act(body: ActBody) -> Dict[str, Any]:
    """Be modellen föreslå ett HUD-kommando och sänd via WS (med säkerhetsgrind)."""
    allow = ["SHOW_MODULE","HIDE_OVERLAY","OPEN_VIDEO"] if body.allow is None else body.allow
    instruction = (
        "Du styr ett HUD-UI. Välj ETT av följande kommandon som JSON utan extra text: "
        "SHOW_MODULE{\"module\": one of [calendar,mail,finance,reminders,wallet,video]}, "
        "HIDE_OVERLAY{}, OPEN_VIDEO{\"source\":{\"kind\":\"webcam\"}}. "
        "Svara endast med ett JSON-objekt. På svenska i val av modulnamn går bra.\n"
    )
    user = body.prompt or ""
    full_prompt = f"{instruction}\nAnvändarens önskemål: {user}\nJSON:"
    proposed: Optional[Dict[str, Any]] = None
    # Försök med modell(er)
    provider = (body.provider or "auto").lower()
    import re, json as pyjson
    async def try_local():
        try:
            t0 = time.time()
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={
                        "model": body.model or os.getenv("LOCAL_MODEL", "gpt-oss:20b"),
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {"num_predict": 128, "temperature": 0.2},
                    },
                )
                if r.status_code == 200:
                    text = (r.json() or {}).get("response", "")
                    m = re.search(r"\{[\s\S]*\}", text)
                    if m:
                        logger.info("ai_act local ms=%.0f", (time.time()-t0)*1000)
                        return pyjson.loads(m.group(0))
        except Exception:
            return None
        return None
    async def try_openai():
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        try:
            t0 = time.time()
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        "messages": [
                            {"role": "system", "content": "Svara med ENBART ett JSON-objekt med HUD-kommandot enligt specifikationen."},
                            {"role": "user", "content": full_prompt},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 100,
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
                    m = re.search(r"\{[\s\S]*\}", text)
                    if m:
                        logger.info("ai_act openai ms=%.0f", (time.time()-t0)*1000)
                        return pyjson.loads(m.group(0))
        except Exception:
            return None
        return None

    if provider == "local":
        proposed = await try_local()
    elif provider == "openai":
        proposed = await try_openai()
    else:
        # auto: race
        t_local = asyncio.create_task(try_local())
        t_openai = asyncio.create_task(try_openai())
        done, pending = await asyncio.wait({t_local, t_openai}, return_when=asyncio.FIRST_COMPLETED)
        proposed = None
        for d in done:
            val = d.result()
            if val:
                proposed = val
                break
        if proposed is None:
            for p in pending:
                try:
                    val = await p
                    if val:
                        proposed = val
                        break
                except asyncio.CancelledError:
                    pass
    # Fallback: enkel regelbaserad tolkning
    if proposed is None:
        low = (user or "").lower()
        if any(k in low for k in ["stäng", "hide", "close"]):
            proposed = {"type": "HIDE_OVERLAY"}
        elif any(k in low for k in ["video", "kamera"]):
            proposed = {"type": "OPEN_VIDEO", "source": {"kind": "webcam"}}
        elif any(k in low for k in ["kalender", "calendar"]):
            proposed = {"type": "SHOW_MODULE", "module": "calendar"}
        elif any(k in low for k in ["mail", "mejl"]):
            proposed = {"type": "SHOW_MODULE", "module": "mail"}
        else:
            # sista utväg: visa finance som demo
            proposed = {"type": "SHOW_MODULE", "module": "finance"}

    cmd = _validate_hud_command(proposed, allow=allow)
    if not cmd:
        # Sista fallback: härleda från användartext om modellen gav ogiltigt JSON
        low = (user or "").lower()
        heuristic = None
        if any(k in low for k in ["stäng", "hide", "close"]):
            heuristic = {"type": "HIDE_OVERLAY"}
        elif any(k in low for k in ["video", "kamera"]):
            heuristic = {"type": "OPEN_VIDEO", "source": {"kind": "webcam"}}
        elif any(k in low for k in ["kalender", "calendar"]):
            heuristic = {"type": "SHOW_MODULE", "module": "calendar"}
        elif any(k in low for k in ["mail", "mejl", "email"]):
            heuristic = {"type": "SHOW_MODULE", "module": "mail"}
        elif any(k in low for k in ["finans", "ekonomi", "finance"]):
            heuristic = {"type": "SHOW_MODULE", "module": "finance"}
        elif any(k in low for k in ["påminnelser", "paminnelser", "reminders"]):
            heuristic = {"type": "SHOW_MODULE", "module": "reminders"}
        elif any(k in low for k in ["plånbok", "planbok", "wallet"]):
            heuristic = {"type": "SHOW_MODULE", "module": "wallet"}
        if heuristic:
            cmd = _validate_hud_command(heuristic, allow=allow)
    if not cmd:
        return {"ok": False, "error": "invalid_command"}
    # Safety gate
    scores = simulate_first(cmd)
    if body.dry_run:
        return {"ok": True, "command": cmd, "scores": scores}
    if scores.get("risk", 1.0) > 0.8:
        return {"ok": False, "error": "blocked_by_safety", "scores": scores}
    try:
        await hub.broadcast({"type": "hud_command", "command": cmd})
        memory.append_event("ai.act", json.dumps({"prompt": user, "command": cmd}, ensure_ascii=False))
    except Exception:
        logger.exception("ai_act broadcast failed")
        return {"ok": False, "error": "broadcast_failed"}
    return {"ok": True, "command": cmd}


class CVIngestBody(BaseModel):
    source: str
    meta: Optional[Dict[str, Any]] = None


@app.post("/api/cv/ingest")
async def cv_ingest(body: CVIngestBody) -> Dict[str, Any]:
    meta_json = json.dumps(body.meta) if body.meta is not None else None
    frame_id = memory.add_cv_frame(body.source, meta_json=meta_json)
    memory.append_event("cv.ingest", json.dumps({"id": frame_id, "source": body.source}))
    return {"ok": True, "id": frame_id}


class SensorBody(BaseModel):
    sensor: str
    value: float
    meta: Optional[Dict[str, Any]] = None


@app.post("/api/sensor/telemetry")
async def sensor_telemetry(body: SensorBody) -> Dict[str, Any]:
    meta_json = json.dumps(body.meta) if body.meta is not None else None
    sid = memory.add_sensor_telemetry(body.sensor, body.value, meta_json=meta_json)
    memory.append_event("sensor.telemetry", json.dumps({"id": sid, "sensor": body.sensor}))
    return {"ok": True, "id": sid}


@app.get("/api/training/dump")
async def training_dump():
    # Stream newline-delimited JSON for offline training pipeline
    async def gen():
        for chunk in stream_dataset(MEMORY_PATH):
            yield chunk
    return ORJSONResponse(gen(), media_type="application/x-ndjson")


class WeatherQuery(BaseModel):
    lat: float
    lon: float


@app.post("/api/weather/current")
async def weather_current(body: WeatherQuery) -> Dict[str, Any]:
    """Proxar Open‑Meteo för enkel väderhämtning utan API‑nyckel."""
    url = (
        "https://api.open-meteo.com/v1/forecast?"\
        f"latitude={body.lat}&longitude={body.lon}&current=temperature_2m,weather_code"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            cur = (data or {}).get("current") or {}
            temp = cur.get("temperature_2m")
            code = cur.get("weather_code")
            return {"ok": True, "temperature": temp, "code": code}
    except Exception as e:
        logger.exception("weather fetch failed")
        return {"ok": False, "error": str(e)}


@app.post("/api/weather/openweather")
async def weather_openweather(body: WeatherQuery) -> Dict[str, Any]:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {"ok": False, "error": "OPENWEATHER_API_KEY missing"}
    url = (
        "https://api.openweathermap.org/data/2.5/weather?"\
        f"lat={body.lat}&lon={body.lon}&units=metric&appid={api_key}"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            main = (data or {}).get("main") or {}
            weather = ((data or {}).get("weather") or [{}])[0]
            temp = main.get("temp")
            desc = weather.get("description")
            code = weather.get("id")
            return {"ok": True, "temperature": temp, "code": code, "description": desc}
    except Exception as e:
        logger.exception("openweather fetch failed")
        return {"ok": False, "error": str(e)}


class CityQuery(BaseModel):
    city: str
    provider: Optional[str] = "openmeteo"  # or 'openweather'


@app.post("/api/weather/by_city")
async def weather_by_city(body: CityQuery) -> Dict[str, Any]:
    # Geokoda stadsnamn via Open-Meteo (gratis, ingen nyckel)
    try:
        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search?"\
            f"name={httpx.QueryParams({'name': body.city})['name']}&count=1&language=sv&format=json"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            gr = await client.get(geo_url)
            gr.raise_for_status()
            g = gr.json() or {}
            results = g.get("results") or []
            if not results:
                return {"ok": False, "error": "city_not_found"}
            lat = float(results[0]["latitude"])
            lon = float(results[0]["longitude"])

        # Använd vald provider
        if (body.provider or "").lower() == "openweather":
            return await weather_openweather(WeatherQuery(lat=lat, lon=lon))
        else:
            return await weather_current(WeatherQuery(lat=lat, lon=lon))
    except Exception as e:
        logger.exception("weather by_city failed")
        return {"ok": False, "error": str(e)}


class ReverseQuery(BaseModel):
    lat: float
    lon: float


@app.post("/api/geo/reverse")
async def geo_reverse(body: ReverseQuery) -> Dict[str, Any]:
    """Reverse‑geokoda lat/lon till närmaste platsnamn via Open‑Meteo (gratis)."""
    try:
        url = (
            "https://geocoding-api.open-meteo.com/v1/reverse?"
            f"latitude={body.lat}&longitude={body.lon}&language=sv&format=json"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json() or {}
                results = data.get("results") or []
                if results:
                    top = results[0]
                    return {
                        "ok": True,
                        "city": top.get("name"),
                        "admin1": top.get("admin1"),
                        "admin2": top.get("admin2"),
                        "country": top.get("country"),
                    }
            # Fallback: Nominatim (kräver User-Agent), jsonv2, svenska
            nurl = (
                "https://nominatim.openstreetmap.org/reverse?"
                f"format=jsonv2&lat={body.lat}&lon={body.lon}&accept-language=sv"
            )
            r2 = await client.get(nurl, headers={"User-Agent": "Jarvis/0.1 (+https://example.local)"})
            r2.raise_for_status()
            d2 = r2.json() or {}
            addr = d2.get("address") or {}
            city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality")
            if not city:
                city = addr.get("county") or addr.get("state") or addr.get("country")
            return {
                "ok": True,
                "city": city,
                "admin1": addr.get("state"),
                "admin2": addr.get("county"),
                "country": addr.get("country"),
            }
    except Exception as e:
        logger.exception("reverse geocoding failed")
        return {"ok": False, "error": str(e)}


class MemoryUpsert(BaseModel):
    text: str
    score: Optional[float] = 0.0
    tags: Optional[Dict[str, Any]] = None


@app.post("/api/memory/upsert")
async def memory_upsert(body: MemoryUpsert) -> Dict[str, Any]:
    tags_json = json.dumps(body.tags) if body.tags is not None else None
    mem_id = memory.upsert_text_memory_single(body.text, score=body.score or 0.0, tags_json=tags_json)
    # Skapa embeddings (OpenAI) om nyckel finns
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and (body.text or "").strip():
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"input": body.text, "model": os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")},
                )
                if r.status_code == 200:
                    d = r.json() or {}
                    vec = ((d.get("data") or [{}])[0].get("embedding") or [])
                    memory.upsert_embedding(mem_id, model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"), dim=len(vec), vector_json=json.dumps(vec))
    except Exception:
        logger.exception("embedding upsert failed")
    return {"ok": True, "id": mem_id}


class MemoryQuery(BaseModel):
    query: str
    limit: Optional[int] = 5


@app.post("/api/memory/retrieve")
async def memory_retrieve(body: MemoryQuery) -> Dict[str, Any]:
    # Hybrid: BM25/LIKE + semantisk (cosine)
    like_items = memory.retrieve_text_memories(body.query, limit=(body.limit or 5))
    results = list(like_items)
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and (body.query or "").strip():
            async with httpx.AsyncClient(timeout=20.0) as client:
                rq = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"input": body.query, "model": os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")},
                )
                if rq.status_code == 200:
                    qv = ((rq.json().get("data") or [{}])[0].get("embedding") or [])
                    rows = memory.get_all_embeddings(model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"))
                    # Cosine similarity
                    def cos(a,b):
                        if not a or not b:
                            return 0.0
                        num = sum(x*y for x,y in zip(a,b))
                        da = math.sqrt(sum(x*x for x in a))
                        db = math.sqrt(sum(y*y for y in b))
                        return (num/(da*db)) if da>0 and db>0 else 0.0
                    sims = []
                    for mem_id, dim, vec_json in rows:
                        try:
                            v = json.loads(vec_json)
                            sims.append((mem_id, cos(qv, v)))
                        except Exception:
                            continue
                    sims.sort(key=lambda x: x[1], reverse=True)
                    top_ids = [mid for mid,_ in sims[: (body.limit or 5)]]
                    id_to_text = memory.get_texts_for_mem_ids(top_ids)
                    for mid in top_ids:
                        txt = id_to_text.get(mid)
                        if txt and all(x.get('text') != txt for x in results):
                            results.append({"id": mid, "text": txt, "kind": "text", "score": 0.0, "ts": ""})
    except Exception:
        logger.exception("hybrid retrieve failed")
    # Trim till limit*2 för att undvika för stor retur
    return {"ok": True, "items": results[: max(1,(body.limit or 5))]}


class MemoryRecentBody(BaseModel):
    limit: Optional[int] = 10


@app.post("/api/memory/recent")
async def memory_recent(body: MemoryRecentBody) -> Dict[str, Any]:
    items = memory.get_recent_text_memories(limit=body.limit or 10)
    return {"ok": True, "items": items}


@app.get("/api/tools/stats")
async def tools_stats() -> Dict[str, Any]:
    items = memory.get_all_tool_stats()
    return {"ok": True, "items": items}


class FeedbackBody(BaseModel):
    kind: str  # 'memory' | 'tool'
    id: Optional[int] = None
    tool: Optional[str] = None
    up: bool = True


@app.post("/api/feedback")
async def feedback(body: FeedbackBody) -> Dict[str, Any]:
    if body.kind == "memory" and body.id is not None:
        memory.update_memory_score(body.id, 1.0 if body.up else -1.0)
        return {"ok": True}
    if body.kind == "tool" and body.tool:
        memory.update_tool_stats(body.tool, success=body.up)
        return {"ok": True}
    return {"ok": False, "error": "invalid feedback payload"}


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    tags: Optional[str] = None  # JSON string of tags
) -> Dict[str, Any]:
    """
    Ladda upp dokument till Alice's RAG-minne för bättre context.
    Supporterar: .txt, .md, .pdf, .docx, .html
    """
    try:
        # Validate file type
        allowed_types = {
            'text/plain': ['.txt', '.md'],
            'application/pdf': ['.pdf'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
            'text/html': ['.html', '.htm'],
            'text/markdown': ['.md']
        }
        
        file_extension = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        content_type = file.content_type or 'text/plain'
        
        # Check if file type is supported
        supported = False
        for mime_type, extensions in allowed_types.items():
            if content_type == mime_type or file_extension in extensions:
                supported = True
                break
        
        if not supported:
            return {
                "ok": False, 
                "error": f"Filtyp {content_type} ({file_extension}) stöds inte. Tillåtna: .txt, .md, .pdf, .docx, .html"
            }
        
        # Read file content
        content_bytes = await file.read()
        
        # Extract text based on file type
        if file_extension == '.pdf':
            try:
                import PyPDF2
                import io
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
            except ImportError:
                return {"ok": False, "error": "PyPDF2 krävs för PDF-stöd. Installera: pip install PyPDF2"}
            except Exception as e:
                return {"ok": False, "error": f"Fel vid PDF-läsning: {str(e)}"}
                
        elif file_extension == '.docx':
            try:
                import docx
                import io
                doc = docx.Document(io.BytesIO(content_bytes))
                text_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            except ImportError:
                return {"ok": False, "error": "python-docx krävs för Word-stöd. Installera: pip install python-docx"}
            except Exception as e:
                return {"ok": False, "error": f"Fel vid Word-läsning: {str(e)}"}
                
        else:
            # Plain text, markdown, HTML
            try:
                text_content = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text_content = content_bytes.decode('latin1')
                except UnicodeDecodeError:
                    return {"ok": False, "error": "Kunde inte dekoda textinnehåll"}
        
        # Clean and validate content
        if not text_content.strip():
            return {"ok": False, "error": "Dokumentet innehåller ingen text"}
        
        # Prepare tags
        document_tags = {
            "source": "document_upload",
            "filename": file.filename,
            "content_type": content_type,
            "file_size": len(content_bytes),
            "uploaded_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Add user-provided tags if any
        if tags:
            try:
                user_tags = json.loads(tags)
                document_tags.update(user_tags)
            except json.JSONDecodeError:
                pass  # Ignore invalid JSON tags
        
        # Upsert to memory (will auto-chunk if large)
        memory_ids = memory.upsert_text_memory(
            text=text_content,
            score=2.0,  # Higher score for uploaded documents
            tags_json=json.dumps(document_tags, ensure_ascii=False),
            auto_chunk=True
        )
        
        # Create embeddings för semantisk sökning
        chunks_processed = 0
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                # Get text chunks for embedding
                for mem_id in memory_ids:
                    text_data = memory.get_texts_for_mem_ids([mem_id])
                    chunk_text = text_data.get(mem_id, "")
                    if chunk_text.strip():
                        try:
                            async with httpx.AsyncClient(timeout=30.0) as client:
                                r = await client.post(
                                    "https://api.openai.com/v1/embeddings",
                                    headers={"Authorization": f"Bearer {api_key}"},
                                    json={
                                        "input": chunk_text,
                                        "model": os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
                                    },
                                )
                                if r.status_code == 200:
                                    d = r.json() or {}
                                    vec = ((d.get("data") or [{}])[0].get("embedding") or [])
                                    if vec:
                                        memory.upsert_embedding(
                                            mem_id, 
                                            model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"), 
                                            dim=len(vec), 
                                            vector_json=json.dumps(vec)
                                        )
                                        chunks_processed += 1
                        except Exception as e:
                            logger.warning(f"Embedding failed for chunk {mem_id}: {e}")
                            
        except Exception as e:
            logger.exception("Embedding processing failed")
        
        # Broadcast to connected clients
        await hub.broadcast({
            "type": "document_uploaded",
            "data": {
                "filename": file.filename,
                "chunks": len(memory_ids),
                "embeddings": chunks_processed,
                "size_kb": round(len(content_bytes) / 1024, 1)
            }
        })
        
        return {
            "ok": True,
            "message": f"Dokument '{file.filename}' uppladdades framgångsrikt",
            "memory_ids": memory_ids,
            "chunks_created": len(memory_ids),
            "embeddings_created": chunks_processed,
            "file_size_kb": round(len(content_bytes) / 1024, 1),
            "content_preview": text_content[:200] + "..." if len(text_content) > 200 else text_content
        }
        
    except Exception as e:
        logger.exception("Document upload failed")
        return {"ok": False, "error": f"Upload misslyckades: {str(e)}"}


class Hub:
    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, event: Dict[str, Any]) -> None:
        data = json.dumps(event)
        async with self._lock:
            clients = list(self._clients)
        # Skicka i parallell utanför låset för att undvika att blockera andra operationer
        results = await asyncio.gather(
            *[ws.send_text(data) for ws in clients], return_exceptions=True
        )
        # Rensa döda anslutningar
        async with self._lock:
            for ws, res in zip(clients, results):
                if isinstance(res, Exception):
                    self._clients.discard(ws)


hub = Hub()


@app.websocket("/ws/alice")
async def ws_alice(ws: WebSocket) -> None:
    await hub.connect(ws)
    try:
        await ws.send_text(json.dumps({"type": "hello", "ts": datetime.utcnow().isoformat() + "Z"}))
        while True:
            raw = await ws.receive_text()
            memory.append_event("ws_in", raw)
            try:
                msg = json.loads(raw)
            except Exception:
                await ws.send_text(json.dumps({"type": "error", "message": "invalid json"}))
                continue

            # Minimal intent handling: echo back and optionally forward to HUD
            if msg.get("type") == "ping":
                await ws.send_text(json.dumps({"type": "pong", "ts": datetime.utcnow().isoformat() + "Z"}))
            elif msg.get("type") == "dispatch":
                # Forward as a HUD command event
                event = {"type": "hud_command", "command": msg.get("command")}
                await hub.broadcast(event)
                await ws.send_text(json.dumps({"type": "ack", "event": "hud_command"}))
            else:
                await ws.send_text(json.dumps({"type": "echo", "data": msg}))
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(ws)


async def ai_autonomous_loop() -> AsyncGenerator[None, None]:
    # Placeholder for a proactive loop that could broadcast HUD actions
    while True:
        await asyncio.sleep(60)
        # Example heartbeat event
        await hub.broadcast({"type": "heartbeat", "ts": datetime.utcnow().isoformat() + "Z"})


@app.on_event("startup")
async def on_startup() -> None:
    # Start autonomous loop (non-blocking)
    asyncio.create_task(ai_autonomous_loop())


# ────────────────────────────────────────────────────────────────────────────────
# Spotify OAuth (Authorization Code)

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


class SpotifyAuthBody(BaseModel):
    scopes: Optional[List[str]] = None


@app.get("/api/spotify/auth_url")
async def spotify_auth_url(scopes: Optional[str] = None) -> Dict[str, Any]:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:3100/spotify/callback")
    if not client_id:
        return {"ok": False, "error": "missing_client_id"}
    scope_str = scopes or " ".join([
        "streaming",
        "user-read-email",
        "user-read-private",
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-currently-playing",
        "playlist-read-private",
        "playlist-modify-private",
        "playlist-modify-public",
    ])
    params = {
        "response_type": "code",
        "client_id": client_id,
        "scope": scope_str,
        "redirect_uri": redirect_uri,
        "show_dialog": "true",
    }
    return {"ok": True, "url": f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"}


@app.get("/api/spotify/callback")
async def spotify_callback(code: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
    if not code:
        return {"ok": False, "error": "missing_code"}
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:3100/spotify/callback")
    if not client_id or not client_secret:
        return {"ok": False, "error": "missing_client_config"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(SPOTIFY_TOKEN_URL, data=data)
            r.raise_for_status()
            token = r.json()
    except Exception:
        logger.exception("spotify token exchange failed")
        return {"ok": False, "error": "token_exchange_failed"}
    try:
        memory.append_event("spotify.tokens", json.dumps({"received": True}))
    except Exception:
        pass
    return {"ok": True, "token": token}


@app.get("/api/spotify/me")
async def spotify_me(access_token: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get("https://api.spotify.com/v1/me", headers={"Authorization": f"Bearer {access_token}"})
            r.raise_for_status()
            return {"ok": True, "me": r.json()}
    except Exception:
        logger.exception("spotify me failed")
        return {"ok": False, "error": "spotify_me_failed"}


# Token refresh för Spotify
class SpotifyRefreshBody(BaseModel):
    refresh_token: str


@app.post("/api/spotify/refresh")
async def spotify_refresh(body: SpotifyRefreshBody) -> Dict[str, Any]:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return {"ok": False, "error": "missing_client_config"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                SPOTIFY_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": body.refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            r.raise_for_status()
            token = r.json()
            try:
                memory.append_event("spotify.refresh", json.dumps({"ok": True}))
            except Exception:
                pass
            return {"ok": True, "token": token}
    except Exception:
        logger.exception("spotify refresh failed")
        return {"ok": False, "error": "refresh_failed"}


@app.get("/api/spotify/devices")
async def spotify_devices(access_token: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.spotify.com/v1/me/player/devices",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            r.raise_for_status()
            return {"ok": True, "devices": r.json()}
    except Exception:
        logger.exception("spotify devices failed")
        return {"ok": False, "error": "spotify_devices_failed"}


@app.get("/api/spotify/state")
async def spotify_state(access_token: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.spotify.com/v1/me/player",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if r.status_code == 204:
                return {"ok": True, "state": None}
            r.raise_for_status()
            return {"ok": True, "state": r.json()}
    except Exception:
        logger.exception("spotify state failed")
        return {"ok": False, "error": "spotify_state_failed"}


@app.get("/api/spotify/current")
async def spotify_current(access_token: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.spotify.com/v1/me/player/currently-playing",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if r.status_code == 204:
                return {"ok": True, "item": None}
            r.raise_for_status()
            return {"ok": True, "item": r.json()}
    except Exception:
        logger.exception("spotify current failed")
        return {"ok": False, "error": "spotify_current_failed"}


@app.get("/api/spotify/recommendations")
async def spotify_recommendations(access_token: str, seed_tracks: Optional[str] = None, seed_artists: Optional[str] = None, seed_genres: Optional[str] = None, limit: Optional[int] = 5) -> Dict[str, Any]:
    try:
        params: Dict[str, Any] = {"limit": int(limit or 5)}
        if seed_tracks:
            params["seed_tracks"] = seed_tracks
        if seed_artists:
            params["seed_artists"] = seed_artists
        if seed_genres:
            params["seed_genres"] = seed_genres
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.spotify.com/v1/recommendations",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
            r.raise_for_status()
            return {"ok": True, "recs": r.json()}
    except Exception:
        logger.exception("spotify recommendations failed")
        return {"ok": False, "error": "spotify_recommendations_failed"}


# Lista användarens spellistor
@app.get("/api/spotify/playlists")
async def spotify_playlists(access_token: str, limit: Optional[int] = 20, offset: Optional[int] = 0) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"https://api.spotify.com/v1/me/playlists?limit={int(limit or 20)}&offset={int(offset or 0)}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            r.raise_for_status()
            return {"ok": True, "playlists": r.json()}
    except Exception:
        logger.exception("spotify playlists failed")
        return {"ok": False, "error": "spotify_playlists_failed"}


# Sök låtar/playlist with resilient HTTP client
@app.get("/api/spotify/search")
async def spotify_search(access_token: str, q: str, type: Optional[str] = "track,playlist", limit: Optional[int] = 10) -> Dict[str, Any]:
    """Enhanced Spotify search with retry and circuit breaker patterns"""
    try:
        qp = httpx.QueryParams({"q": q, "type": type or "track,playlist", "limit": int(limit or 10)})
        
        response = await spotify_client.get(
            f"https://api.spotify.com/v1/search?{qp}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=httpx.Timeout(10.0)
        )
        response.raise_for_status()
        return {"ok": True, "result": response.json()}
        
    except Exception as e:
        logger.exception(f"Spotify search failed: {str(e)}")
        return {"ok": False, "error": "spotify_search_failed", "details": str(e)}


class SpotifyPlayBody(BaseModel):
    access_token: str
    device_id: Optional[str] = None
    uris: Optional[List[str]] = None
    context_uri: Optional[str] = None
    position_ms: Optional[int] = None
    offset_position: Optional[int] = None  # for context playback
    offset_uri: Optional[str] = None       # alternative to position


@app.post("/api/spotify/play")
async def spotify_play(body: SpotifyPlayBody) -> Dict[str, Any]:
    if not body.uris and not body.context_uri:
        return {"ok": False, "error": "missing_uris_or_context"}
    try:
        qp = ""
        if body.device_id:
            qp = "?" + str(httpx.QueryParams({"device_id": body.device_id}))
        payload: Dict[str, Any] = {}
        if body.uris:
            payload["uris"] = body.uris
        if body.context_uri:
            payload["context_uri"] = body.context_uri
        if body.position_ms is not None:
            payload["position_ms"] = int(body.position_ms)
        if body.offset_uri or (body.offset_position is not None):
            off: Dict[str, Any] = {}
            if body.offset_uri:
                off["uri"] = body.offset_uri
            if body.offset_position is not None:
                off["position"] = int(body.offset_position)
            if off:
                payload["offset"] = off
        # Use resilient HTTP client with retry and circuit breaker
        response = await spotify_client.put(
            f"https://api.spotify.com/v1/me/player/play{qp}",
            headers={"Authorization": f"Bearer {body.access_token}", "Content-Type": "application/json"},
            json=payload,
            timeout=httpx.Timeout(10.0)
        )
        # 204 No Content på success
        if response.status_code in (200, 204):
            return {"ok": True}
        return {"ok": False, "error": f"status_{response.status_code}", "details": response.text}
    except Exception as e:
        logger.exception("spotify play failed")
        return {"ok": False, "error": "spotify_play_failed", "message": str(e)}


class SpotifyQueueBody(BaseModel):
    access_token: str
    device_id: Optional[str] = None
    uri: str


@app.post("/api/spotify/queue")
async def spotify_queue(body: SpotifyQueueBody) -> Dict[str, Any]:
    try:
        params: Dict[str, Any] = {"uri": body.uri}
        if body.device_id:
            params["device_id"] = body.device_id
        qp = str(httpx.QueryParams(params))
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"https://api.spotify.com/v1/me/player/queue?{qp}",
                headers={"Authorization": f"Bearer {body.access_token}"},
            )
            if r.status_code in (200, 204):
                return {"ok": True}
            return {"ok": False, "error": f"status_{r.status_code}", "details": r.text}
    except Exception as e:
        logger.exception("spotify queue failed")
        return {"ok": False, "error": "spotify_queue_failed", "message": str(e)}


# ────────────────────────────────────────────────────────────────────────────────
# AI‑driven media‑akt (NL → spela låt/playlist på Spotify)
class MediaActBody(BaseModel):
    prompt: str
    access_token: str
    device_id: Optional[str] = None
    provider: Optional[str] = "auto"  # 'local' | 'openai' | 'auto'


@app.post("/api/ai/media_act")
async def ai_media_act(body: MediaActBody) -> Dict[str, Any]:
    """Tolka prompten och spela upp via Spotify.
    Förväntat JSON från modellen:
    {"action":"play_track","track":"Back In Black","artist":"AC/DC"}
    eller {"action":"play_playlist","playlist":"Hard Rock Classics"}
    """
    if not body.access_token:
        return {"ok": False, "error": "missing_access_token"}

    instruction = (
        "Du får en svensk text om musikuppspelning. Svara ENBART med ett JSON-objekt utan förklaring. "
        "Fält: action = 'play_track' | 'play_playlist'. För play_track: 'track' (namn), valfritt 'artist'. "
        "För play_playlist: 'playlist' (namn). Exempel: {\"action\":\"play_track\",\"track\":\"Back In Black\",\"artist\":\"AC/DC\"}."
    )
    provider = (body.provider or "auto").lower()

    import re as _re

    async def try_local():
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={
                        "model": os.getenv("LOCAL_MODEL", "gpt-oss:20b"),
                        "prompt": f"{instruction}\n\nAnvändarens önskemål: {body.prompt}\nJSON:",
                        "stream": False,
                        "options": {"num_predict": 128, "temperature": 0.2},
                    },
                )
                if r.status_code == 200:
                    text = (r.json() or {}).get("response", "")
                    m = _re.search(r"\{[\s\S]*\}", text)
                    if m:
                        return json.loads(m.group(0))
        except Exception:
            return None
        return None

    async def try_openai():
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        "messages": [
                            {"role": "system", "content": instruction},
                            {"role": "user", "content": body.prompt},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 100,
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
                    m = _re.search(r"\{[\s\S]*\}", text)
                    if m:
                        return json.loads(m.group(0))
        except Exception:
            return None
        return None

    parsed = None
    if provider == "local":
        parsed = await try_local()
    elif provider == "openai":
        parsed = await try_openai()
    else:
        t1 = asyncio.create_task(try_openai())
        t2 = asyncio.create_task(try_local())
        done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
        for d in done:
            val = d.result()
            if val:
                parsed = val
        for p in pending:
            try:
                val = await p
                if not parsed and val:
                    parsed = val
            except asyncio.CancelledError:
                pass

    if not isinstance(parsed, dict):
        # Heuristisk fallback: tolka "spela X med Y" → play_track
        low = (body.prompt or "").strip().lower()
        try:
            import re as _re
            m = _re.search(r"spela\s+(.+?)(?:\s+med\s+(.+))?$", low)
            if m:
                track_guess = (m.group(1) or "").strip()
                artist_guess = (m.group(2) or "").strip()
                parsed = {"action": "play_track", "track": track_guess}
                if artist_guess:
                    parsed["artist"] = artist_guess
            else:
                parsed = {"action": "play_track", "track": low.replace("spela", "").strip()}
        except Exception:
            return {"ok": False, "error": "parse_failed"}

    action = (parsed.get("action") or "").lower()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if action == "play_track":
                q = (parsed.get("track") or "").strip()
                artist = (parsed.get("artist") or "").strip()
                if not q:
                    return {"ok": False, "error": "missing_track"}
                query = f"{q} artist:{artist}" if artist else q
                sr = await client.get(
                    f"https://api.spotify.com/v1/search",
                    params={"q": query, "type": "track", "limit": 5},
                    headers={"Authorization": f"Bearer {body.access_token}"},
                )
                sr.raise_for_status()
                data = sr.json() or {}
                items = (data.get("tracks") or {}).get("items") or []
                # Om artist inte angavs men prompten innehåller en favorit: använd recommendations med seed på artist
                if not items and artist:
                    # hämta artist-id
                    ar = await client.get(
                        "https://api.spotify.com/v1/search",
                        params={"q": artist, "type": "artist", "limit": 1},
                        headers={"Authorization": f"Bearer {body.access_token}"},
                    )
                    if ar.status_code == 200:
                        aid = (((ar.json() or {}).get("artists") or {}).get("items") or [{}])[0].get("id")
                        if aid:
                            rr = await client.get(
                                "https://api.spotify.com/v1/recommendations",
                                params={"seed_artists": aid, "limit": 5},
                                headers={"Authorization": f"Bearer {body.access_token}"},
                            )
                            if rr.status_code == 200:
                                items = ((rr.json() or {}).get("tracks") or [])
                if not items:
                    return {"ok": False, "error": "no_track_results"}
                uri = (items[0] or {}).get("uri")
                pr = await client.put(
                    f"https://api.spotify.com/v1/me/player/play",
                    params={"device_id": body.device_id} if body.device_id else None,
                    headers={"Authorization": f"Bearer {body.access_token}", "Content-Type": "application/json"},
                    json={"uris": [uri], "position_ms": 0},
                )
                if pr.status_code not in (200, 204):
                    return {"ok": False, "error": f"status_{pr.status_code}", "details": pr.text}
                return {"ok": True, "played": {"kind": "track", "uri": uri}}

            if action == "play_playlist":
                name = (parsed.get("playlist") or "").strip()
                if not name:
                    return {"ok": False, "error": "missing_playlist"}
                sr = await client.get(
                    f"https://api.spotify.com/v1/search",
                    params={"q": name, "type": "playlist", "limit": 5},
                    headers={"Authorization": f"Bearer {body.access_token}"},
                )
                sr.raise_for_status()
                items = ((sr.json() or {}).get("playlists") or {}).get("items") or []
                if not items:
                    return {"ok": False, "error": "no_playlist_results"}
                ctx = (items[0] or {}).get("uri")
                pr = await client.put(
                    f"https://api.spotify.com/v1/me/player/play",
                    params={"device_id": body.device_id} if body.device_id else None,
                    headers={"Authorization": f"Bearer {body.access_token}", "Content-Type": "application/json"},
                    json={"context_uri": ctx, "position_ms": 0, "offset": {"position": 0}},
                )
                if pr.status_code not in (200, 204):
                    return {"ok": False, "error": f"status_{pr.status_code}", "details": pr.text}
                return {"ok": True, "played": {"kind": "playlist", "uri": ctx}}
    except Exception as e:
        logger.exception("ai_media_act failed")
        return {"ok": False, "error": "media_act_failed", "message": str(e)}

    return {"ok": False, "error": "unsupported_action"}


# ────────────────────────────────────────────────────────────────────────────────
# En enda AI-router som väljer chat / HUD‑akt / media‑akt
class RouteBody(BaseModel):
    prompt: str
    provider: Optional[str] = "auto"
    hud_allow: Optional[List[str]] = ["SHOW_MODULE","OPEN_VIDEO","HIDE_OVERLAY"]
    spotify_access_token: Optional[str] = None
    spotify_device_id: Optional[str] = None


@app.post("/api/ai/route")
async def ai_route(body: RouteBody) -> Dict[str, Any]:
    instr = (
        "Klassificera användarens avsikt och svara ENDAST med JSON.\n"
        "Fält: intent in ['chat','hud','media_track','media_playlist'].\n"
        "Om media_track: ge 'track' och ev 'artist'. Om media_playlist: ge 'playlist'.\n"
        "Om hud: ge 'text' som beskriver vad HUD ska göra (svenska).\n"
    )
    provider = (body.provider or "auto").lower()

    import re as _re

    async def classify_local():
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                r = await client.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={
                        "model": os.getenv("LOCAL_MODEL", "gpt-oss:20b"),
                        "prompt": f"{instr}\n\nAnvändarens text: {body.prompt}\nJSON:",
                        "stream": False,
                        "options": {"num_predict": 100, "temperature": 0.2},
                    },
                )
                if r.status_code == 200:
                    text = (r.json() or {}).get("response", "")
                    m = _re.search(r"\{[\s\S]*\}", text)
                    if m:
                        return json.loads(m.group(0))
        except Exception:
            return None
        return None

    async def classify_openai():
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        "messages": [
                            {"role": "system", "content": instr},
                            {"role": "user", "content": body.prompt},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 80,
                    },
                )
                if r.status_code == 200:
                    d = r.json()
                    text = ((d.get("choices") or [{}])[0].get("message") or {}).get("content", "")
                    m = _re.search(r"\{[\s\S]*\}", text)
                    if m:
                        return json.loads(m.group(0))
        except Exception:
            return None
        return None

    parsed = None
    if provider == "local":
        parsed = await classify_local()
    elif provider == "openai":
        parsed = await classify_openai()
    else:
        t1 = asyncio.create_task(classify_openai())
        t2 = asyncio.create_task(classify_local())
        done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
        for d in done:
            v = d.result()
            if v:
                parsed = v
        for p in pending:
            try:
                v = await p
                if not parsed and v:
                    parsed = v
            except asyncio.CancelledError:
                pass

    # Heuristik om LLM fallerar
    if not isinstance(parsed, dict):
        low = (body.prompt or "").lower()
        if low.startswith("spela") or " spela " in low:
            parsed = {"intent": "media_track"}
        elif any(k in low for k in ["visa","öppna","stäng","open","close"]):
            parsed = {"intent": "hud"}
        else:
            parsed = {"intent": "chat"}

    intent = (parsed.get("intent") or "chat").lower()
    # Route
    if intent in {"media_track","media_playlist"}:
        if not body.spotify_access_token:
            return {"ok": False, "error": "missing_spotify_token"}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                rr = await client.post(
                    "http://127.0.0.1:8000/api/ai/media_act",
                    json={
                        "prompt": body.prompt,
                        "access_token": body.spotify_access_token,
                        "device_id": body.spotify_device_id,
                        "provider": provider,
                    },
                )
                return {"ok": True, "kind": "media", "result": rr.json()}
        except Exception:
            logger.exception("route->media failed")
            return {"ok": False, "error": "route_media_failed"}

    if intent == "hud":
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                rr = await client.post(
                    "http://127.0.0.1:8000/api/ai/act",
                    json={"prompt": body.prompt, "allow": body.hud_allow, "provider": provider},
                )
                return {"ok": True, "kind": "hud", "result": rr.json()}
        except Exception:
            logger.exception("route->hud failed")
            return {"ok": False, "error": "route_hud_failed"}

    # default chat
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            rr = await client.post(
                "http://127.0.0.1:8000/api/chat",
                json={"prompt": body.prompt, "provider": provider},
            )
            return {"ok": True, "kind": "chat", "result": rr.json()}
    except Exception:
        logger.exception("route->chat failed")
        return {"ok": False, "error": "route_chat_failed"}


# ────────────────────────────────────────────────────────────────────────────────
# Voice STT API (Whisper Integration)
# ────────────────────────────────────────────────────────────────────────────────

@app.post("/api/voice/transcribe")
async def api_transcribe_audio(audio: UploadFile = File(...)):
    """
    Transkribera ljudfil med Whisper
    Hybrid voice system - högkvalitativ transkribering
    """
    try:
        result = await transcribe_audio_file(audio)
        return result
    except Exception as e:
        logger.error(f"Voice transcription API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/voice/status")
async def api_voice_status():
    """
    Kontrollera status för röststyrning
    Visar både Browser API och Whisper status
    """
    try:
        status = await get_stt_status()
        return status
    except Exception as e:
        logger.error(f"Voice status API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== OpenAI Realtime API Endpoints ==========


@app.get("/api/realtime/ephemeral")
async def create_realtime_ephemeral_session(
    model: Optional[str] = "gpt-4o-realtime-preview",
    voice: Optional[str] = "nova",
    instructions: Optional[str] = None,
    modalities: Optional[str] = "text,audio"
):
    """
    Create ephemeral OpenAI Realtime API session key for WebRTC
    Compatible with OpenAI Realtime API documentation patterns
    """
    try:
        settings = get_global_openai_settings()
        
        # Validate OpenAI configuration
        validation = validate_openai_config(settings)
        if not validation["valid"]:
            raise HTTPException(
                status_code=500, 
                detail=f"OpenAI configuration error: {', '.join(validation['errors'])}"
            )
        
        # Parse modalities
        modalities_list = [m.strip() for m in (modalities or "text,audio").split(",")]
        
        # Use Alice's default instructions if none provided
        if not instructions:
            instructions = settings.session_config.instructions
        
        # Create session configuration
        session_config = {
            "model": model or settings.realtime_model.value,
            "voice": voice or settings.voice_settings.voice.value,
            "instructions": instructions,
            "modalities": modalities_list,
            "input_audio_format": settings.session_config.input_audio_format,
            "output_audio_format": settings.session_config.output_audio_format,
            "temperature": settings.session_config.temperature,
            "max_response_output_tokens": settings.session_config.max_response_output_tokens,
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 200
            }
        }
        
        # Create ephemeral token (valid for 60 seconds for WebRTC)
        import time
        expires_at = int(time.time()) + 60
        
        # Client secret for WebRTC connection
        client_secret = {
            "type": "ephemeral",
            "expires_at": expires_at,
            "api_key": settings.api_key,  # In real implementation, this would be a temporary token
            "base_url": settings.realtime_url,
            "headers": settings.websocket_headers
        }
        
        logger.info(f"Created ephemeral Realtime session: {model}, voice: {voice}")
        
        return RealtimeSessionResponse(
            client_secret=client_secret,
            expires_at=expires_at,
            session_config=session_config
        )
        
    except Exception as e:
        logger.error(f"Realtime ephemeral session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/stream")
async def stream_agent_response(request: AgentBridgeRequest):
    """
    Stream agent responses via Server-Sent Events (SSE)
    Integrates with Alice's agent bridge system for real-time AI responses
    """
    async def generate_sse_stream():
        try:
            # Create Alice agent bridge
            bridge = await create_alice_bridge(memory)
            
            # Set response headers for SSE
            yield "data: " + json.dumps({
                "type": "meta", 
                "message": "Alice agent stream startar...",
                "timestamp": datetime.now().isoformat()
            }) + "\n\n"
            
            # Stream response chunks
            async for chunk in bridge.stream_response(request):
                # Convert to SSE format
                sse_data = chunk.to_sse_format()
                yield sse_data
                
                # Add small delay for better streaming experience
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Agent stream error: {e}")
            error_data = json.dumps({
                "type": "error",
                "message": f"Streaming fel: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        generate_sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
            "X-Alice-Agent": "bridge-v1"
        }
    )


@app.post("/api/tts/openai-stream") 
async def stream_openai_tts(request: OpenAITTSRequest):
    """
    Stream TTS audio using OpenAI's Text-to-Speech API
    Streams binary audio chunks for real-time playback
    """
    async def generate_openai_audio_stream():
        try:
            settings = get_global_openai_settings()
            
            # Validate OpenAI configuration
            validation = validate_openai_config(settings)
            if not validation["valid"]:
                raise HTTPException(
                    status_code=500,
                    detail=f"OpenAI configuration error: {', '.join(validation['errors'])}"
                )
            
            # Prepare OpenAI TTS request
            tts_payload = {
                "model": request.model,
                "input": request.text,
                "voice": request.voice,
                "response_format": request.response_format,
                "speed": request.speed
            }
            
            # Stream from OpenAI TTS API
            async with OpenAIClient(settings) as client:
                async with client.stream(
                    "POST", 
                    "/audio/speech",
                    json=tts_payload,
                    headers={"Accept": "audio/*"}
                ) as response:
                    
                    if response.status_code != 200:
                        error_msg = await response.aread()
                        logger.error(f"OpenAI TTS API error: {response.status_code} - {error_msg}")
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"OpenAI TTS error: {response.status_code}"
                        )
                    
                    # Stream audio chunks
                    async for chunk in response.aiter_bytes(chunk_size=1024):
                        if chunk:
                            yield chunk
                            
        except Exception as e:
            logger.error(f"OpenAI TTS streaming error: {e}")
            # Return silence on error to avoid breaking audio stream
            yield b'\x00' * 1024
    
    # Determine media type based on response format
    media_types = {
        "mp3": "audio/mpeg",
        "opus": "audio/opus", 
        "aac": "audio/aac",
        "flac": "audio/flac",
        "wav": "audio/wav",
        "pcm": "audio/pcm"
    }
    
    media_type = media_types.get(request.response_format, "audio/mpeg")
    
    return StreamingResponse(
        generate_openai_audio_stream(),
        media_type=media_type,
        headers={
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
            "X-TTS-Model": request.model,
            "X-Voice": request.voice,
            "X-Speed": str(request.speed),
            "X-Format": request.response_format
        }
    )

