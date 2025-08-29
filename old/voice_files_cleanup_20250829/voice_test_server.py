"""
Voice Test Server - Simplified server för live testing
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

# Add server to path
sys.path.append('server')

from server.voice.input_processor import InputProcessor
from server.voice.orchestrator import VoiceOrchestrator

app = FastAPI(title="Alice Voice Pipeline Test")

# Serve test page
@app.get("/")
async def serve_test_page():
    return FileResponse("test_voice_live.html")

class VoiceTestRequest(BaseModel):
    source_type: str
    swedish_text: str

class VoiceTestResponse(BaseModel):
    success: bool
    original_text: str = ""
    english_text: str = ""
    style: str = ""
    rate: float = 1.0
    translation_time: float = 0
    error: str = None

# Global components
input_processor = None
orchestrator = None

@app.on_event("startup")
async def startup():
    global input_processor, orchestrator
    
    print("🎙️ Initializing Voice Pipeline for testing...")
    
    input_processor = InputProcessor()
    orchestrator = VoiceOrchestrator()
    
    print("🚀 Voice Test Server ready!")
    print("📝 Open: http://localhost:8001")

@app.post("/api/voice/test", response_model=VoiceTestResponse)
async def test_voice_pipeline(request: VoiceTestRequest):
    """Test voice pipeline - translation only"""
    
    if not request.swedish_text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    try:
        # Process input
        if request.source_type == "chat":
            input_pkg = input_processor.process_chat(request.swedish_text)
        elif request.source_type == "email":
            input_pkg = input_processor.process_email("Test", request.swedish_text)
        elif request.source_type == "calendar":
            input_pkg = input_processor.process_calendar("Event", "imorgon", request.swedish_text)
        else:
            input_pkg = input_processor.process_notification(request.swedish_text)
        
        # Translate
        start_time = time.time()
        voice_output = await orchestrator.process(input_pkg)
        translation_time = time.time() - start_time
        
        # Check if fallback
        if voice_output.meta.get("fallback", False):
            return VoiceTestResponse(
                success=False,
                original_text=request.swedish_text,
                english_text=voice_output.speak_text_en,
                error=voice_output.meta.get("error", "Translation failed")
            )
        
        return VoiceTestResponse(
            success=True,
            original_text=request.swedish_text,
            english_text=voice_output.speak_text_en,
            style=voice_output.style,
            rate=voice_output.rate,
            translation_time=translation_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/voice/health")
async def health_check():
    """Health check"""
    return {
        "status": "ready",
        "components": {
            "input_processor": input_processor is not None,
            "orchestrator": orchestrator is not None
        }
    }

if __name__ == "__main__":
    print("🎙️ Alice Voice Pipeline Test Server")
    print("=" * 40)
    
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=8001,
        log_level="info"
    )