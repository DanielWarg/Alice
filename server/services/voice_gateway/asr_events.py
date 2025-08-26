#!/usr/bin/env python3
"""
📡 ASR Event Broadcasting System
WebSocket-based real-time ASR events for Alice Voice Gateway
"""
import asyncio
import json
import logging
import time
from typing import Dict
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class ASREventBroadcaster:
    """Manage WebSocket connections and broadcast ASR events"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket):
        """Add new WebSocket connection for session"""
        await websocket.accept()
        self.connections[session_id] = websocket
        logger.info(f"🔌 ASR WebSocket connected for session {session_id}")
    
    def disconnect(self, session_id: str):
        """Remove WebSocket connection for session"""
        if session_id in self.connections:
            del self.connections[session_id]
            logger.info(f"🔌 ASR WebSocket disconnected for session {session_id}")
    
    async def broadcast_partial(self, session_id: str, text: str, confidence: float, provider: str):
        """Broadcast ASR partial result"""
        await self._broadcast_event(session_id, "asr_partial", {
            "text": text,
            "confidence": confidence,
            "provider": provider,
            "is_final": False
        })
    
    async def broadcast_final(self, session_id: str, text: str, confidence: float, provider: str):
        """Broadcast ASR final result"""
        await self._broadcast_event(session_id, "asr_final", {
            "text": text,
            "confidence": confidence,
            "provider": provider,
            "is_final": True
        })
    
    async def broadcast_error(self, session_id: str, error: str):
        """Broadcast ASR error"""
        await self._broadcast_event(session_id, "asr_error", {
            "error": error
        })
    
    async def _broadcast_event(self, session_id: str, event_type: str, data: dict):
        """Internal broadcast method"""
        if session_id not in self.connections:
            return
        
        message = {
            "type": event_type,
            "timestamp": time.time() * 1000,
            "session_id": session_id,
            "data": data
        }
        
        try:
            await self.connections[session_id].send_json(message)
            logger.debug(f"📡 Broadcast {event_type} to session {session_id}: {data.get('text', '')}")
        except Exception as e:
            logger.error(f"❌ Failed to broadcast {event_type}: {e}")
            self.disconnect(session_id)
    
    async def keep_alive(self, session_id: str):
        """Send keep-alive ping"""
        if session_id in self.connections:
            try:
                await self.connections[session_id].send_json({
                    "type": "ping",
                    "timestamp": time.time() * 1000
                })
            except Exception:
                self.disconnect(session_id)
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.connections)

# Global broadcaster instance
_event_broadcaster = ASREventBroadcaster()

def get_asr_broadcaster() -> ASREventBroadcaster:
    """Get global ASR event broadcaster"""
    return _event_broadcaster