"""
TTS Route - Voice v2 with OpenAI TTS and disk caching
"""

import os
import hashlib
import aiofiles
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import httpx
import json
import logging

logger = logging.getLogger("alice.tts")

router = APIRouter(prefix="/api/tts", tags=["tts"])

# Configuration
AUDIO_DIR = Path(os.getenv("AUDIO_DIR", "./server/voice/audio"))
OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "tts-1")

class TTSRequest(BaseModel):
    text: str
    voice: str = "nova"
    rate: float = 1.0

class TTSResponse(BaseModel):
    url: str
    cached: bool
    processing_time_ms: float = 0.0

def create_cache_key(text: str, voice: str, rate: float) -> str:
    """Create normalized cache key for TTS"""
    normalized = text.strip().replace(r'\s+', ' ')
    key_string = f"{voice}|{rate}|{normalized}"
    return hashlib.sha1(key_string.encode('utf-8')).hexdigest()

@router.post("/", response_model=TTSResponse)
async def generate_tts(request: TTSRequest):
    """
    Generate TTS audio with caching
    - Returns cached audio if available
    - Otherwise generates new audio via OpenAI TTS
    """
    
    if not request.text or not isinstance(request.text, str):
        raise HTTPException(status_code=400, detail="text required")
    
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    start_time = asyncio.get_event_loop().time()
    
    # Create cache key and file path
    cache_key = create_cache_key(request.text, request.voice, request.rate)
    audio_file = AUDIO_DIR / f"tts_{cache_key}.mp3"
    
    # Ensure audio directory exists
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if cached version exists
    if audio_file.exists():
        processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.debug(f"TTS cache hit: {request.text[:50]}...")
        
        return TTSResponse(
            url=f"/audio/{audio_file.name}",
            cached=True,
            processing_time_ms=processing_time
        )
    
    # Generate new TTS audio
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENAI_TTS_URL,
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_TTS_MODEL,
                    "voice": request.voice,
                    "input": request.text,
                    "response_format": "mp3",
                    "speed": min(max(request.rate, 0.25), 4.0)  # OpenAI limits: 0.25-4.0
                }
            )
        
        if response.status_code != 200:
            error_detail = response.text[:200] if response.text else "Unknown error"
            logger.error(f"OpenAI TTS failed: {response.status_code} - {error_detail}")
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"TTS upstream failed: {error_detail}"
            )
        
        # Save audio to cache
        async with aiofiles.open(audio_file, 'wb') as f:
            await f.write(response.content)
        
        processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        logger.info(f"TTS generated: {request.text[:50]}... ({processing_time:.0f}ms)")
        
        return TTSResponse(
            url=f"/audio/{audio_file.name}",
            cached=False,
            processing_time_ms=processing_time
        )
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="TTS request timed out")
    except Exception as e:
        logger.error(f"TTS generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

@router.post("/batch")
async def generate_batch_tts(requests: list[TTSRequest]):
    """
    Generate multiple TTS files in batch for pre-caching
    """
    
    if not requests:
        raise HTTPException(status_code=400, detail="No requests provided")
    
    if len(requests) > 20:
        raise HTTPException(status_code=400, detail="Too many requests (max 20)")
    
    results = []
    
    for req in requests:
        try:
            result = await generate_tts(req)
            results.append({
                "text": req.text,
                "result": result.dict()
            })
        except Exception as e:
            results.append({
                "text": req.text,
                "error": str(e)
            })
    
    return {"results": results}

@router.get("/cache/stats")
async def get_cache_stats():
    """Get TTS cache statistics"""
    
    if not AUDIO_DIR.exists():
        return {"cached_files": 0, "total_size_mb": 0.0}
    
    files = list(AUDIO_DIR.glob("tts_*.mp3"))
    total_size = sum(f.stat().st_size for f in files if f.is_file())
    
    return {
        "cached_files": len(files),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "cache_directory": str(AUDIO_DIR)
    }

@router.delete("/cache/clear")
async def clear_cache():
    """Clear TTS cache"""
    
    if not AUDIO_DIR.exists():
        return {"cleared_files": 0}
    
    files = list(AUDIO_DIR.glob("tts_*.mp3"))
    cleared_count = 0
    
    for file in files:
        try:
            file.unlink()
            cleared_count += 1
        except Exception as e:
            logger.warning(f"Failed to delete {file}: {e}")
    
    return {"cleared_files": cleared_count}

# Health check endpoint
@router.get("/health")
async def tts_health():
    """Check TTS system health"""
    
    health_status = {
        "service": "tts",
        "status": "healthy",
        "openai_configured": OPENAI_API_KEY is not None,
        "cache_directory_exists": AUDIO_DIR.exists(),
        "cache_writable": False
    }
    
    # Test cache directory write access
    try:
        test_file = AUDIO_DIR / "test_write.tmp"
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test")
        test_file.unlink()
        health_status["cache_writable"] = True
    except Exception:
        health_status["cache_writable"] = False
        health_status["status"] = "degraded"
    
    return health_status