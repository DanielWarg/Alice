"""
Voice Test API - FastAPI endpoint för live testing av voice pipeline
"""

import os
import sys
import asyncio
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# Add voice directory to path
sys.path.append('voice')

from voice.input_processor import InputProcessor
from voice.orchestrator import VoiceOrchestrator
from voice.tts_client import TTSClient
from voice.performance_monitor import performance_monitor

app = FastAPI(title="Alice Voice Pipeline Test API")

# Serve static files (audio)
audio_dir = Path("voice/audio")
audio_dir.mkdir(exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")

# Serve test page
@app.get("/")
async def serve_test_page():
    return FileResponse("../test_voice_live.html")

class VoiceTestRequest(BaseModel):
    source_type: str  # chat, email, calendar, notification
    swedish_text: str

class VoiceTestResponse(BaseModel):
    success: bool
    original_text: str = ""
    english_text: str = ""
    style: str = ""
    rate: float = 1.0
    translation_time: float = 0
    audio_file: str = None
    provider: str = None
    cached: bool = False
    text_only: bool = False
    error: str = None

# Global components - initialized on startup
input_processor = None
orchestrator = None
tts_client = None

@app.on_event("startup")
async def startup():
    global input_processor, orchestrator, tts_client
    
    print("🎙️ Initializing Voice Pipeline components...")
    
    input_processor = InputProcessor()
    orchestrator = VoiceOrchestrator()
    
    # Initialize TTS client only if API key is available
    try:
        if os.getenv("OPENAI_API_KEY") and not os.getenv("OPENAI_API_KEY").startswith("test-"):
            tts_client = TTSClient()
            print("✅ TTS client initialized with real API key")
        else:
            print("⚠️  No real OpenAI API key - translation only mode")
    except Exception as e:
        print(f"⚠️  TTS client initialization failed: {e}")
        tts_client = None
    
    print("🚀 Voice Pipeline API ready!")

@app.post("/api/voice/test", response_model=VoiceTestResponse)
async def test_voice_pipeline(request: VoiceTestRequest):
    """Test the voice pipeline with Swedish input"""
    
    if not request.swedish_text.strip():
        raise HTTPException(status_code=400, detail="Swedish text cannot be empty")
    
    start_time = time.time()
    
    try:
        # Step 1: Process input
        if request.source_type == "chat":
            input_pkg = input_processor.process_chat(request.swedish_text)
        elif request.source_type == "email":
            # Parse subject/body if formatted as email
            if "Ämne:" in request.swedish_text:
                lines = request.swedish_text.split("\n", 2)
                subject = lines[0].replace("Ämne: ", "")
                body = lines[2] if len(lines) > 2 else ""
            else:
                subject = "Test Email"
                body = request.swedish_text
            input_pkg = input_processor.process_email(subject, body)
        elif request.source_type == "calendar":
            input_pkg = input_processor.process_calendar("Test Event", "imorgon", request.swedish_text)
        else:  # notification
            input_pkg = input_processor.process_notification(request.swedish_text)
        
        # Step 2: Translate
        translation_start = time.time()
        voice_output = await orchestrator.process(input_pkg)
        translation_time = time.time() - translation_start
        
        # Check if translation failed
        if voice_output.meta.get("fallback", False):
            return VoiceTestResponse(
                success=False,
                original_text=request.swedish_text,
                english_text=voice_output.speak_text_en,
                error=voice_output.meta.get("error", "Translation failed")
            )
        
        response = VoiceTestResponse(
            success=True,
            original_text=request.swedish_text,
            english_text=voice_output.speak_text_en,
            style=voice_output.style,
            rate=voice_output.rate,
            translation_time=translation_time
        )
        
        # Step 3: TTS (if available)
        if tts_client:
            try:
                tts_result = await tts_client.synthesize(voice_output)
                
                if tts_result["success"] and tts_result.get("audio_file"):
                    # Convert absolute path to relative URL
                    audio_path = Path(tts_result["audio_file"])
                    response.audio_file = f"/audio/{audio_path.name}"
                    response.provider = tts_result.get("provider", "unknown")
                    response.cached = tts_result.get("cached", False)
                elif tts_result.get("text_only"):
                    response.text_only = True
                    response.error = tts_result.get("error", "TTS failed")
                else:
                    response.error = f"TTS failed: {tts_result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                response.error = f"TTS error: {str(e)}"
        else:
            response.text_only = True
            response.error = "TTS not available (no API key)"
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice pipeline error: {str(e)}")

@app.get("/api/voice/stats")
async def get_performance_stats():
    """Get current performance statistics"""
    
    stats = performance_monitor.get_current_stats()
    source_analysis = performance_monitor.get_source_type_analysis()
    
    return {
        "stats": stats,
        "source_analysis": source_analysis,
        "report": performance_monitor.generate_performance_report()
    }

@app.get("/api/voice/health")
async def health_check():
    """Health check endpoint"""
    
    components = {
        "input_processor": input_processor is not None,
        "orchestrator": orchestrator is not None, 
        "tts_client": tts_client is not None,
        "ollama_connection": False
    }
    
    # Test Ollama connection
    try:
        if orchestrator:
            health_status = await orchestrator.llm.health()
            components["ollama_connection"] = health_status.ok
    except Exception:
        pass
    
    return {
        "status": "healthy" if all(components.values()[:3]) else "partial",  # TTS optional
        "components": components,
        "total_requests": performance_monitor.total_requests
    }

if __name__ == "__main__":
    print("🎙️ Starting Alice Voice Pipeline Test Server...")
    print("📝 Test page will be available at: http://localhost:8001")
    print("🔗 API docs at: http://localhost:8001/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )