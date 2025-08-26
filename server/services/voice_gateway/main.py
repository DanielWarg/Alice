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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if redis_client:
        await redis_client.close()
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
        
        # Create peer connection and process offer
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
            "metrics": "/metrics"
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