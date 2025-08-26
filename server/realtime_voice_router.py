#!/usr/bin/env python3
"""
🎙️ LiveKit-Style WebSocket Router för Alice Real-time Voice
Integrerar den nya streaming voice engine i FastAPI
"""

import asyncio
import json
import logging
from typing import Dict, Optional
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from realtime_voice_engine import voice_engine, handle_voice_message

# Setup logging
logger = logging.getLogger("alice.realtime_voice")

# Router setup
router = APIRouter(prefix="/api/realtime-voice", tags=["Real-time Voice"])

# Active WebSocket connections
active_connections: Dict[str, WebSocket] = {}

@router.websocket("/ws")
async def realtime_voice_websocket(websocket: WebSocket):
    """
    LiveKit-style WebSocket för real-time voice processing
    
    Expected message format:
    {
        "type": "partial_transcript",
        "transcript": "hej alice vad är klockan",
        "confidence": 0.92,
        "is_final": false
    }
    
    Response format:
    {
        "type": "audio_chunk",
        "audio_data": "base64-encoded-audio",
        "chunk_index": 1,
        "metadata": {"ttfa_ms": 650}
    }
    """
    await websocket.accept()
    
    # Generate unique connection ID
    connection_id = f"conn_{datetime.now().strftime('%H%M%S')}_{len(active_connections)}"
    active_connections[connection_id] = websocket
    
    logger.info(f"🎙️ Real-time voice connection opened: {connection_id}")
    
    # Send welcome message
    await websocket.send_json({
        "type": "connection_established",
        "connection_id": connection_id,
        "engine_status": "ready",
        "features": {
            "stable_partial_detection": True,
            "streaming_tts": True,
            "american_english_voice": True,
            "sub_700ms_ttfa": True
        }
    })
    
    try:
        while True:
            # Vänta på meddelande från klient
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                logger.debug(f"📨 Mottaget meddelande: {message.get('type', 'unknown')}")
                
                # Validera meddelande-format
                if not isinstance(message, dict) or 'type' not in message:
                    await websocket.send_json({
                        "type": "error",
                        "error": "Invalid message format. Expected JSON with 'type' field.",
                        "timestamp": datetime.now().isoformat()
                    })
                    continue
                
                # Processa meddelandet och streama svar
                async for response in handle_voice_message(message):
                    await websocket.send_json(response)
                    
                    # Log för debugging
                    response_type = response.get('type', 'unknown')
                    if response_type == 'audio_chunk':
                        chunk_idx = response.get('chunk_index', 0)
                        ttfa = response.get('metadata', {}).get('ttfa_ms')
                        logger.info(f"🎵 Skickade audio chunk {chunk_idx}" + 
                                  (f" (TTFA: {ttfa:.0f}ms)" if ttfa else ""))
                    elif response_type == 'processing_started':
                        transcript = response.get('transcript', '')
                        logger.info(f"🎯 Processing startad: '{transcript[:50]}...'")
                    elif response_type == 'response_complete':
                        logger.info("✅ Response komplett")
                        
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                })
                logger.warning(f"❌ JSON decode fel från {connection_id}")
                
            except Exception as e:
                await websocket.send_json({
                    "type": "error", 
                    "error": f"Processing error: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
                logger.error(f"❌ Processing fel i {connection_id}: {e}")
                
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket frånkopplad: {connection_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket-fel i {connection_id}: {e}")
    finally:
        # Cleanup
        if connection_id in active_connections:
            del active_connections[connection_id]
        logger.info(f"🧹 Connection {connection_id} städad")

@router.get("/status")
async def get_realtime_voice_status():
    """
    Hämta status för real-time voice systemet
    """
    try:
        metrics = voice_engine.get_metrics()
        
        return JSONResponse({
            "status": "operational",
            "engine": "LiveKit-style",
            "connections": {
                "active": len(active_connections),
                "ids": list(active_connections.keys())
            },
            "metrics": metrics,
            "features": {
                "stable_partial_detection": True,
                "streaming_tts": True,
                "american_english_voice": True,
                "target_ttfa_ms": 700
            },
            "voice": {
                "model": "en_US-amy-medium",
                "language": "English",
                "response_language": "English (responds in English to Swedish input)"
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Status-fel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
async def reset_voice_engine():
    """
    Återställ voice engine (för debugging)
    """
    try:
        voice_engine.reset_session()
        
        # Notifiera alla aktiva anslutningar
        disconnected = []
        for conn_id, websocket in active_connections.items():
            try:
                await websocket.send_json({
                    "type": "engine_reset",
                    "message": "Voice engine has been reset",
                    "timestamp": datetime.now().isoformat()
                })
            except:
                disconnected.append(conn_id)
                
        # Cleanup disconnected
        for conn_id in disconnected:
            del active_connections[conn_id]
        
        return JSONResponse({
            "status": "reset_complete",
            "active_connections": len(active_connections),
            "reset_timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Reset-fel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_voice_metrics():
    """
    Detaljerade metrics för voice engine
    """
    try:
        metrics = voice_engine.get_metrics()
        
        return JSONResponse({
            "metrics": metrics,
            "connections": {
                "active_count": len(active_connections),
                "connection_ids": list(active_connections.keys())
            },
            "performance": {
                "target_ttfa_ms": 700,
                "current_avg_ttfa_ms": metrics.get('avg_ttfa_ms', 0),
                "is_meeting_target": metrics.get('avg_ttfa_ms', 0) < 700
            },
            "engine_info": {
                "type": "LiveKit-style",
                "version": "1.0",
                "features": ["stable_partial", "streaming_tts", "american_voice"]
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Metrics-fel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Test endpoint för enkla tester
@router.post("/test")
async def test_voice_processing(request: dict):
    """
    Test endpoint för att testa voice processing utan WebSocket
    
    Body: {
        "transcript": "hej alice",
        "confidence": 0.9,
        "is_final": true
    }
    """
    try:
        # Simulera voice processing
        results = []
        async for response in handle_voice_message({
            "type": "partial_transcript",
            **request
        }):
            results.append(response)
            
        return JSONResponse({
            "test_status": "success",
            "input": request,
            "responses": results,
            "response_count": len(results),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Test-fel: {e}")
        raise HTTPException(status_code=500, detail=str(e))