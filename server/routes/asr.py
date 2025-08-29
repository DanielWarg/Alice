"""
ASR Route - WebSocket Speech Recognition with Whisper + VAD
===========================================================

Real-time speech recognition pipeline:
- WebSocket for audio streaming
- VAD (Voice Activity Detection) 
- Whisper ASR with Swedish support
- NDJSON event logging
"""

import asyncio
import json
import logging
import time
import random
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from pathlib import Path
import base64
import tempfile

logger = logging.getLogger("alice.asr")

# ASR Configuration
ASR_ENGINE = "whisper-sim"  # whisper-sim for testing, whisper for production
ASR_MODEL = "base"  # base, small, medium for whisper
ASR_LANG = "sv-SE"  # Swedish as default
VAD_ENGINE = "webrtc"
SAMPLE_RATE = 16000  # 16kHz for whisper

class ASRSession:
    """Manages a single ASR WebSocket session"""
    
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.is_listening = False
        self.audio_buffer = bytearray()
        self.start_time = time.time()
        self.vad_start_time = None
        self.partial_results = []
        
    async def send_event(self, event_type: str, data: Dict[str, Any]):
        """Send structured event to client"""
        
        event = {
            "event": event_type,
            "session_id": self.session_id,
            "timestamp": time.time(),
            "elapsed_ms": (time.time() - self.start_time) * 1000,
            **data
        }
        
        await self.websocket.send_text(json.dumps(event))
        logger.debug(f"ASR event sent: {event_type} - {data}")

async def simulate_whisper_asr(audio_data: bytes, lang: str = "sv-SE") -> Dict[str, Any]:
    """Simulate Whisper ASR processing with realistic latency"""
    
    # Simulate realistic Whisper processing time
    audio_duration_ms = len(audio_data) / 2 / SAMPLE_RATE * 1000  # Assuming 16-bit PCM
    
    # Whisper processing time: ~10-30% of audio duration + base overhead
    base_time = 0.1  # 100ms base processing
    audio_factor = audio_duration_ms * random.uniform(0.10, 0.25)  # 10-25% of audio length
    processing_time = base_time + (audio_factor / 1000)
    
    # Simulate processing delay
    await asyncio.sleep(processing_time)
    
    # Mock Swedish responses (in real implementation, this would be actual Whisper)
    mock_responses = [
        "kolla min email",
        "vad är klockan",
        "hur är vädret idag", 
        "sätt en påminnelse",
        "ring till johan",
        "spela musik",
        "hej alice hur mår du",
        "vad har jag för möten idag",
        "slå på lamporna",
        "stäng av ljudet"
    ]
    
    # Simulate confidence based on "audio quality"
    confidence = random.uniform(0.85, 0.98)
    text = random.choice(mock_responses)
    
    return {
        "text": text,
        "language": lang,
        "confidence": confidence,
        "processing_time_ms": processing_time * 1000,
        "audio_duration_ms": audio_duration_ms,
        "engine": ASR_ENGINE,
        "model": ASR_MODEL
    }

async def detect_voice_activity(audio_chunk: bytes) -> bool:
    """Simple VAD simulation (in production: use WebRTC VAD or Silero)"""
    
    # Simulate VAD processing
    await asyncio.sleep(0.005)  # 5ms VAD latency
    
    # Mock VAD: random activity detection with some logic
    # In reality, this analyzes audio energy, zero-crossing rate, etc.
    chunk_energy = sum(audio_chunk) / len(audio_chunk) if audio_chunk else 0
    
    # Simulate voice detection (very basic mock)
    has_voice = len(audio_chunk) > 1000 and random.random() > 0.3
    
    return has_voice

async def handle_asr_websocket(websocket: WebSocket):
    """Handle ASR WebSocket connection"""
    
    session_id = f"asr_session_{int(time.time())}_{random.randint(1000, 9999)}"
    session = ASRSession(websocket, session_id)
    
    logger.info(f"ASR session started: {session_id}")
    
    try:
        await session.send_event("session_start", {
            "asr_engine": ASR_ENGINE,
            "asr_model": ASR_MODEL,
            "language": ASR_LANG,
            "sample_rate": SAMPLE_RATE,
            "vad_engine": VAD_ENGINE
        })
        
        while True:
            # Receive audio data or control messages
            message = await websocket.receive_text()
            
            try:
                data = json.loads(message)
                msg_type = data.get("type", "unknown")
                
                if msg_type == "audio":
                    await handle_audio_data(session, data)
                    
                elif msg_type == "start_listening":
                    await start_listening(session)
                    
                elif msg_type == "stop_listening":
                    await stop_listening(session)
                    
                elif msg_type == "config":
                    await update_config(session, data)
                    
                else:
                    logger.warning(f"Unknown message type: {msg_type}")
                    
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {message[:100]}")
                await session.send_event("error", {
                    "error_type": "invalid_json",
                    "message": "Invalid JSON format"
                })
                
    except WebSocketDisconnect:
        logger.info(f"ASR session disconnected: {session_id}")
    except Exception as e:
        logger.error(f"ASR session error: {e}")
        try:
            await session.send_event("error", {
                "error_type": "session_error",
                "message": str(e)
            })
        except:
            pass

async def handle_audio_data(session: ASRSession, data: Dict[str, Any]):
    """Process incoming audio data"""
    
    # Decode base64 audio data
    audio_b64 = data.get("audio", "")
    if not audio_b64:
        return
        
    try:
        audio_bytes = base64.b64decode(audio_b64)
        session.audio_buffer.extend(audio_bytes)
        
        # VAD processing
        has_voice = await detect_voice_activity(audio_bytes)
        
        if has_voice and not session.is_listening:
            # Voice activity detected - start listening
            session.vad_start_time = time.time()
            session.is_listening = True
            await session.send_event("speech_start", {
                "vad_trigger_ms": (time.time() - session.start_time) * 1000
            })
            
        elif has_voice and session.is_listening:
            # Continue listening - send partial results occasionally
            if len(session.audio_buffer) > SAMPLE_RATE * 2:  # Every 2 seconds of audio
                await send_partial_result(session)
                
        elif not has_voice and session.is_listening:
            # Voice activity ended - finalize transcription
            await finalize_transcription(session)
            
    except Exception as e:
        logger.error(f"Audio processing error: {e}")
        await session.send_event("error", {
            "error_type": "audio_processing",
            "message": str(e)
        })

async def send_partial_result(session: ASRSession):
    """Send partial transcription result"""
    
    if len(session.audio_buffer) < 1000:
        return
        
    # Mock partial result (in production: call Whisper with partial buffer)
    partial_text = "kolla min..."  # Simulated partial
    
    await session.send_event("partial", {
        "text": partial_text,
        "confidence": 0.7,
        "is_final": False
    })

async def finalize_transcription(session: ASRSession):
    """Finalize and send complete transcription"""
    
    if not session.audio_buffer:
        session.is_listening = False
        return
        
    vad_duration = (time.time() - session.vad_start_time) * 1000 if session.vad_start_time else 0
    
    # Run ASR on complete audio buffer
    asr_result = await simulate_whisper_asr(bytes(session.audio_buffer), ASR_LANG)
    
    await session.send_event("final", {
        "text": asr_result["text"],
        "language": asr_result["language"], 
        "confidence": asr_result["confidence"],
        "asr_latency_ms": asr_result["processing_time_ms"],
        "vad_duration_ms": vad_duration,
        "audio_duration_ms": asr_result["audio_duration_ms"],
        "engine": asr_result["engine"],
        "model": asr_result["model"]
    })
    
    # Reset for next utterance
    session.audio_buffer.clear()
    session.is_listening = False
    session.vad_start_time = None
    
    logger.info(f"ASR final: '{asr_result['text']}' ({asr_result['processing_time_ms']:.1f}ms)")

async def start_listening(session: ASRSession):
    """Start listening mode"""
    session.start_time = time.time()
    await session.send_event("listening_start", {
        "mode": "continuous"
    })

async def stop_listening(session: ASRSession):
    """Stop listening and finalize any pending audio"""
    if session.is_listening:
        await finalize_transcription(session)
    
    await session.send_event("listening_stop", {
        "total_session_ms": (time.time() - session.start_time) * 1000
    })

async def update_config(session: ASRSession, data: Dict[str, Any]):
    """Update ASR configuration"""
    config = data.get("config", {})
    
    # Update language, model, etc.
    global ASR_LANG, ASR_MODEL
    ASR_LANG = config.get("language", ASR_LANG)
    ASR_MODEL = config.get("model", ASR_MODEL)
    
    await session.send_event("config_updated", {
        "language": ASR_LANG,
        "model": ASR_MODEL
    })

# Health check for ASR system
async def asr_health() -> Dict[str, Any]:
    """ASR system health check"""
    
    return {
        "service": "asr",
        "status": "healthy",
        "engine": ASR_ENGINE,
        "model": ASR_MODEL,
        "language": ASR_LANG,
        "vad_engine": VAD_ENGINE,
        "sample_rate": SAMPLE_RATE
    }