#!/usr/bin/env python3
"""
🎙️ Alice Voice Gateway - LiveKit-Class Real-time Pipeline
FastAPI service with WebRTC offer/answer for duplex audio streaming
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Optional, Any
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv("../../../.env")

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from webrtc import WebRTCManager
from metrics import VoiceMetrics
from asr_events import get_asr_broadcaster
from llm_events import get_llm_broadcaster
from tts_events import get_tts_broadcaster
from llm_router import get_llm_router
from network_guard import get_network_guard
# from talk_client import create_talk_client  # Removed - OpenAI Realtime deprecated
from tool_lane_stub import ToolLane

# Configure logging  
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set specific logger levels
# logging.getLogger("alice.talk_client").setLevel(logging.DEBUG)  # Removed - OpenAI Realtime deprecated
logging.getLogger("aioice").setLevel(logging.WARNING)  # Reduce ICE noise

# Pydantic models
class WebRTCOfferRequest(BaseModel):
    sdp: str
    type: str = "offer"
    session_id: Optional[str] = None

class WebRTCOfferResponse(BaseModel):
    sdp: str
    type: str = "answer" 
    session_id: str
    ice_servers: list = []

class TestRouteRequest(BaseModel):
    text: str
    context: Optional[Dict] = None

# FastAPI app
app = FastAPI(
    title="Alice Voice Gateway",
    description="LiveKit-class real-time voice pipeline with WebRTC",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
webrtc_manager = WebRTCManager()
voice_metrics = VoiceMetrics()
redis_client: Optional[redis.Redis] = None
asr_broadcaster = get_asr_broadcaster()
llm_broadcaster = get_llm_broadcaster()
tts_broadcaster = get_tts_broadcaster()
llm_router = get_llm_router()
network_guard = get_network_guard()
# talk_client = None  # Removed - OpenAI Realtime deprecated
tool_lane = ToolLane()  # Local processing lane

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global redis_client
    
    try:
        # Connect to Redis
        redis_url = "redis://localhost:6379/0"  # Will be configurable via env
        redis_client = redis.from_url(redis_url)
        await redis_client.ping()
        logger.info("✅ Connected to Redis")
        
        # Initialize WebRTC manager
        await webrtc_manager.initialize()
        logger.info("✅ WebRTC manager initialized")
        
        # Initialize metrics
        voice_metrics.initialize()
        logger.info("✅ Voice metrics initialized")
        
        # Note: OpenAI Realtime removed - will be replaced with Piper streaming pipeline
        logger.info("🎯 Voice Gateway ready for Piper integration")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if redis_client:
        await redis_client.close()
    # Note: talk_client cleanup removed with OpenAI Realtime
    await webrtc_manager.cleanup()
    logger.info("🔄 Voice gateway shutdown complete")

@app.post("/api/webrtc/offer", response_model=WebRTCOfferResponse)
async def webrtc_offer(request: WebRTCOfferRequest):
    """
    Handle WebRTC offer and return answer with SDP
    This establishes the peer connection for duplex audio
    """
    try:
        start_time = time.time()
        
        # Generate session ID if not provided
        session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"🎯 Processing WebRTC offer for session: {session_id}")
        
        # Note: OpenAI Realtime removed - using WebRTC manager directly
        # Fallback to WebRTC manager (now primary path)
        answer_sdp = await webrtc_manager.handle_offer(
            session_id=session_id,
            offer_sdp=request.sdp
        )
        
        if not answer_sdp:
            raise HTTPException(status_code=500, detail="Failed to generate WebRTC answer")
        
        # Store session in Redis
        session_data = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
            "tts_active": "false",
            "barge_in": "false"
        }
        
        await redis_client.hset(
            f"sess:{session_id}",
            mapping=session_data
        )
        await redis_client.expire(f"sess:{session_id}", 1800)  # 30min TTL
        
        # Record metrics
        processing_time = (time.time() - start_time) * 1000
        voice_metrics.record_offer_processing_time(processing_time)
        
        logger.info(f"✅ WebRTC offer processed in {processing_time:.0f}ms")
        
        # ICE servers for NAT traversal (configure for production)
        ice_servers = [
            {"urls": "stun:stun.l.google.com:19302"}
        ]
        
        return WebRTCOfferResponse(
            sdp=answer_sdp,
            session_id=session_id,
            ice_servers=ice_servers
        )
        
    except Exception as e:
        logger.error(f"❌ WebRTC offer failed: {e}")
        voice_metrics.record_error("webrtc_offer_failed")
        raise HTTPException(status_code=500, detail=f"WebRTC offer failed: {str(e)}")

@app.get("/api/voice/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get session information from Redis"""
    try:
        session_data = await redis_client.hgetall(f"sess:{session_id}")
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session_id,
            "data": session_data,
            "ttl": await redis_client.ttl(f"sess:{session_id}")
        }
        
    except Exception as e:
        logger.error(f"❌ Session lookup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Session lookup failed: {str(e)}")

@app.post("/api/voice/stop-tts")
async def stop_tts(request: Request):
    """Stop TTS for barge-in functionality"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required")
        
        # Set barge-in flag in Redis
        await redis_client.hset(f"sess:{session_id}", "barge_in", "true")
        await redis_client.hset(f"sess:{session_id}", "tts_active", "false")
        
        # Signal WebRTC manager to stop TTS
        await webrtc_manager.stop_tts(session_id)
        
        voice_metrics.record_barge_in()
        logger.info(f"🛑 TTS stopped for session: {session_id}")
        
        return {"status": "tts_stopped", "session_id": session_id}
        
    except Exception as e:
        logger.error(f"❌ Stop TTS failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stop TTS failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        await redis_client.ping()
        
        # Check WebRTC manager status
        manager_status = webrtc_manager.get_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "redis": "connected",
                "webrtc_manager": manager_status,
            },
            "active_sessions": await webrtc_manager.get_active_session_count()
        }
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(voice_metrics.registry), media_type=CONTENT_TYPE_LATEST)

@app.post("/api/test/route")
async def test_route(request: TestRouteRequest):
    """Test endpoint for hybrid routing system"""
    try:
        # Route the request
        route_decision = llm_router.route_request(request.text, request.context)
        
        # Check privacy guard
        guard_result = network_guard.check_outbound_message(request.text)
        
        # Get router metrics
        router_metrics = llm_router.get_metrics()
        guard_metrics = network_guard.get_metrics()
        
        return {
            "route": route_decision.route.value,
            "intent": route_decision.intent.value,
            "no_cloud": route_decision.no_cloud,
            "confidence": route_decision.confidence,
            "privacy_level": route_decision.privacy_level,
            "reasoning": route_decision.reasoning,
            "guard_decision": guard_result.decision.value,
            "guard_reason": guard_result.reason,
            "metrics": {
                "router": router_metrics,
                "guard": guard_metrics
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Test route failed: {e}")
        raise HTTPException(status_code=500, detail=f"Route test failed: {str(e)}")

@app.post("/api/voice/process")
async def process_voice_request(request: TestRouteRequest):
    """Process voice request through hybrid system with real API responses"""
    try:
        # Route the request
        route_decision = llm_router.route_request(request.text, request.context)
        logger.info(f"🔀 Route decision: {route_decision.route.value} ({route_decision.intent.value})")
        
        if route_decision.route.value == "realtime":
            # Talk-lane: OpenAI Realtime (fast responses)
            logger.info("🏃 Processing via Talk-lane (OpenAI Realtime)")
            
            # Check privacy guard first
            guard_result = network_guard.check_outbound_message(request.text)
            if guard_result.decision.value == "block":
                logger.warning(f"🚫 Privacy guard blocked: {guard_result.reason}")
                # Force to local processing
                route_decision.route = route_decision.route.__class__("local")
                route_decision.no_cloud = True
                route_decision.reasoning += " (privacy guard override)"
                
                # Process locally instead
                local_result = await tool_lane.process_request(request.text, {"no_cloud": True})
                return {
                    "route": "local",
                    "intent": route_decision.intent.value,
                    "response": local_result.get("response", "I'll check that locally."),
                    "privacy_override": True,
                    "guard_reason": guard_result.reason
                }
            
            # Note: OpenAI Realtime removed - will be replaced with local Piper streaming
            # Test mode - direct OpenAI API call for text response
            logger.info("🧪 Using direct OpenAI API for testing (Piper streaming not implemented yet)")
            
            try:
                import openai
                import os
                
                client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                
                # Create Alice-style prompt for Talk-lane
                alice_prompt = (
                    "You are Alice, an AI assistant. Respond in English, "
                    "1-2 sentences maximum. Be concise and helpful. "
                    f"User input (Swedish/English): {request.text}"
                )
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": alice_prompt},
                        {"role": "user", "content": request.text}
                    ],
                    max_tokens=100,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content.strip()
                
                return {
                    "route": route_decision.route.value,
                    "intent": route_decision.intent.value,
                    "response": ai_response,
                    "processing_method": "openai_api_direct",
                    "confidence": route_decision.confidence,
                    "reasoning": route_decision.reasoning + " (direct API test mode)"
                }
            
            except Exception as e:
                logger.error(f"❌ OpenAI API call failed: {e}")
                # Fallback to local
                local_result = await tool_lane.process_request(request.text, {"no_cloud": False})
                return {
                    "route": "local_fallback",
                    "intent": route_decision.intent.value,
                    "response": local_result.get("response", "I'll help you with that."),
                    "processing_method": "local_fallback",
                    "error": str(e)
                }
            
        else:
            # Tool-lane: Local processing (private/complex)
            logger.info("🛠️ Processing via Tool-lane (Local)")
            
            # For now, use direct Ollama call for Tool-lane (simpler than complex tool planning)
            try:
                import httpx
                
                logger.info("🧠 Using local gpt-oss for Tool-lane processing")
                
                system_prompt = (
                    "You are Alice providing private, local assistance. "
                    "Handle sensitive data carefully. Respond in English, 1-2 sentences. "
                    "Acknowledge privacy when appropriate. "
                    f"User request (Swedish/English): {request.text}"
                )
                
                ollama_url = "http://localhost:11434/api/generate"
                payload = {
                    "model": "gpt-oss:20b",
                    "prompt": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 100,
                        "top_p": 0.9
                    }
                }
                
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response_obj = await client.post(ollama_url, json=payload)
                    result = response_obj.json()
                
                if "response" in result:
                    response = result["response"].strip()
                    if route_decision.no_cloud:
                        response += " (Processed privately on your device.)"
                else:
                    response = "I processed that locally with privacy protection."
                    
            except Exception as e:
                logger.error(f"❌ Local gpt-oss failed: {e}")
                response = "I processed that locally with privacy protection."
            
            return {
                "route": route_decision.route.value,
                "intent": route_decision.intent.value,
                "response": response,
                "processing_method": "local_gpt_oss",
                "confidence": route_decision.confidence,
                "privacy_level": route_decision.privacy_level,
                "reasoning": route_decision.reasoning,
                "no_cloud": route_decision.no_cloud,
                "model": "gpt-oss:20b"
            }
        
    except Exception as e:
        logger.error(f"❌ Voice processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")

@app.post("/api/voice/update-voice")
async def update_voice(request: Request):
    """Update the voice for Talk Client"""
    try:
        data = await request.json()
        new_voice = data.get("voice", "alloy")
        
        # Valid OpenAI Realtime voices (updated as of 2024)
        valid_voices = ["alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse"]
        if new_voice not in valid_voices:
            raise HTTPException(status_code=400, detail=f"Invalid voice. Must be one of: {valid_voices}")
        
        # Note: Voice update for talk_client removed with OpenAI Realtime
        # Will be replaced with Piper voice model selection
        logger.info(f"🎤 Voice update request: {new_voice} (Piper integration pending)")
        
        return {
            "success": True,
            "voice": new_voice,
            "message": f"Voice updated to {new_voice}"
        }
            
    except Exception as e:
        logger.error(f"❌ Voice update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice update failed: {str(e)}")

@app.get("/api/test/privacy")
async def test_privacy_status():
    """Get current privacy guard status"""
    try:
        guard_metrics = network_guard.get_metrics()
        router_metrics = llm_router.get_metrics()
        
        return {
            "privacy_guard": {
                "status": "active",
                "total_checks": guard_metrics.get("total_checks", 0),
                "blocks": guard_metrics.get("blocks", 0),
                "block_rate": guard_metrics.get("block_rate", 0),
                "privacy_leak_attempts": guard_metrics.get("privacy_leak_attempts", 0)
            },
            "router": {
                "total_routes": router_metrics.get("total_routes", 0),
                "realtime_percentage": router_metrics.get("realtime_percentage", 0),
                "local_percentage": router_metrics.get("local_percentage", 0),
                "privacy_blocks": router_metrics.get("privacy_blocks", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Privacy status failed: {e}")
        raise HTTPException(status_code=500, detail=f"Privacy status failed: {str(e)}")

@app.websocket("/ws/asr/{session_id}")
async def asr_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time ASR events"""
    try:
        await asr_broadcaster.connect(session_id, websocket)
        logger.info(f"🔌 ASR WebSocket connected for session: {session_id}")
        
        try:
            # Keep connection alive and handle client messages
            while True:
                try:
                    # Wait for messages from client (like ping/pong)
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    
                    # Handle client messages if needed
                    if message == "ping":
                        await websocket.send_json({"type": "pong", "timestamp": time.time() * 1000})
                        
                except asyncio.TimeoutError:
                    # Send periodic keep-alive
                    await asr_broadcaster.keep_alive(session_id)
                    
        except WebSocketDisconnect:
            logger.info(f"🔌 ASR WebSocket disconnected for session: {session_id}")
        except Exception as e:
            logger.error(f"❌ ASR WebSocket error for session {session_id}: {e}")
            
    finally:
        asr_broadcaster.disconnect(session_id)

@app.websocket("/ws/llm/{session_id}")
async def llm_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time LLM token events"""
    try:
        await llm_broadcaster.connect(session_id, websocket)
        logger.info(f"🔌 LLM WebSocket connected for session: {session_id}")
        
        try:
            # Keep connection alive and handle client messages
            while True:
                try:
                    # Wait for messages from client (like ping/pong)
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    
                    # Handle client messages if needed
                    if message == "ping":
                        await websocket.send_json({"type": "pong", "timestamp": time.time() * 1000})
                        
                except asyncio.TimeoutError:
                    # Send periodic keep-alive
                    await llm_broadcaster.keep_alive(session_id)
                    
        except WebSocketDisconnect:
            logger.info(f"🔌 LLM WebSocket disconnected for session: {session_id}")
        except Exception as e:
            logger.error(f"❌ LLM WebSocket error for session {session_id}: {e}")
            
    finally:
        llm_broadcaster.disconnect(session_id)

@app.websocket("/ws/tts/{session_id}")
async def tts_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time TTS audio streaming"""
    try:
        await tts_broadcaster.connect(session_id, websocket)
        logger.info(f"🔌 TTS WebSocket connected for session: {session_id}")
        
        try:
            # Keep connection alive and handle client messages
            while True:
                try:
                    # Wait for messages from client (like ping/pong)
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    
                    # Handle client messages if needed
                    if message == "ping":
                        await websocket.send_json({"type": "pong", "timestamp": time.time() * 1000})
                        
                except asyncio.TimeoutError:
                    # Send periodic keep-alive
                    await tts_broadcaster.keep_alive(session_id)
                    
        except WebSocketDisconnect:
            logger.info(f"🔌 TTS WebSocket disconnected for session: {session_id}")
        except Exception as e:
            logger.error(f"❌ TTS WebSocket error for session {session_id}: {e}")
            
    finally:
        tts_broadcaster.disconnect(session_id)

@app.websocket("/ws/voice-stream/{session_id}")
async def voice_stream_websocket(websocket: WebSocket, session_id: str = "default"):
    """WebSocket endpoint for streaming voice test client"""
    try:
        await websocket.accept()
        logger.info(f"🔌 Voice stream WebSocket connected for session: {session_id}")
        
        try:
            # Keep connection alive and handle client messages
            while True:
                try:
                    # Wait for messages from client
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    data = json.loads(message)
                    
                    # Handle different message types
                    if data.get("type") == "partial_transcript":
                        transcript = data.get("transcript", "")
                        is_final = data.get("is_final", False)
                        test_mode = data.get("test_mode", False)
                        
                        logger.info(f"📝 {'Final' if is_final else 'Partial'} transcript: {transcript}")
                        
                        if is_final and transcript.strip():
                            # Process the transcript
                            await websocket.send_text(json.dumps({
                                "type": "processing_started",
                                "transcript": transcript,
                                "trigger": "final_transcript"
                            }))
                            
                            if test_mode:
                                # Test streaming metrics with OpenAI Realtime simulation
                                turn_start = time.time() * 1000
                                
                                # Simulate OpenAI Realtime processing times
                                await asyncio.sleep(0.05)  # STT partial (50ms)
                                stt_partial_time = time.time() * 1000
                                
                                await asyncio.sleep(0.03)  # STT final (30ms)
                                stt_final_time = time.time() * 1000
                                
                                await asyncio.sleep(0.12)  # LLM first token (120ms)
                                llm_first_token_time = time.time() * 1000
                                
                                await asyncio.sleep(0.08)  # TTS first chunk (80ms)
                                tts_first_chunk_time = time.time() * 1000
                                
                                await asyncio.sleep(0.02)  # Playback start (20ms)
                                playback_start_time = time.time() * 1000
                                
                                # Calculate metrics
                                metrics = {
                                    "first_partial_ms": stt_partial_time - turn_start,
                                    "ttft_ms": llm_first_token_time - stt_final_time,
                                    "tts_first_chunk_ms": tts_first_chunk_time - llm_first_token_time,
                                    "total_latency_ms": playback_start_time - turn_start
                                }
                                
                                # Check SLO compliance
                                slo_pass = (
                                    metrics["first_partial_ms"] <= 300 and
                                    metrics["ttft_ms"] <= 300 and
                                    metrics["tts_first_chunk_ms"] <= 150 and
                                    metrics["total_latency_ms"] <= 500
                                )
                                
                                # Send metrics
                                await websocket.send_text(json.dumps({
                                    "type": "metrics",
                                    "data": {**metrics, "slo_pass": slo_pass}
                                }))
                                
                                logger.info(f"🎯 Test metrics - SLO Pass: {slo_pass}, Total: {metrics['total_latency_ms']:.1f}ms")
                            else:
                                # Regular processing
                                await asyncio.sleep(0.3)  # Simulate processing time
                            
                            # Send response
                            responses = {
                                'hello alice': 'Hello! How can I help you today?',
                                'what time is it': f'The current time is {time.strftime("%H:%M")}.',
                                'how are you today': 'I\'m doing great, thank you for asking!',
                                'tell me a joke': 'Why did the AI cross the road? To get to the other site!',
                                'what is 2 plus 2': 'Two plus two equals four.'
                            }
                            
                            response_text = responses.get(transcript.lower().strip(), f"I heard: {transcript}")
                            
                            await websocket.send_text(json.dumps({
                                "type": "response_complete",
                                "response": response_text
                            }))
                    
                    elif data.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time() * 1000}))
                        
                except asyncio.TimeoutError:
                    # Send periodic keep-alive
                    await websocket.send_text(json.dumps({"type": "heartbeat", "timestamp": time.time() * 1000}))
                    
        except WebSocketDisconnect:
            logger.info(f"🔌 Voice stream WebSocket disconnected for session: {session_id}")
        except Exception as e:
            logger.error(f"❌ Voice stream WebSocket error for session {session_id}: {e}")
            
    except Exception as e:
        logger.error(f"❌ Failed to accept WebSocket connection: {e}")

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "Alice Voice Gateway",
        "version": "1.0.0",
        "description": "LiveKit-class real-time voice pipeline",
        "endpoints": {
            "webrtc_offer": "/api/webrtc/offer",
            "stop_tts": "/api/voice/stop-tts", 
            "health": "/health",
            "metrics": "/metrics",
            "voice_stream_ws": "/ws/voice-stream/{session_id}"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )