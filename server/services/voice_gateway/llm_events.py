#!/usr/bin/env python3
"""
📡 LLM Event Broadcasting System
WebSocket-based real-time LLM token events for Alice Voice Gateway
"""
import asyncio
import json
import logging
import time
from typing import Dict
from fastapi import WebSocket, WebSocketDisconnect

from llm_stream import LLMToken, LLMResponse

logger = logging.getLogger(__name__)

class LLMEventBroadcaster:
    """Manage WebSocket connections and broadcast LLM events"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket):
        """Add new WebSocket connection for session"""
        await websocket.accept()
        self.connections[session_id] = websocket
        logger.info(f"🔌 LLM WebSocket connected for session {session_id}")
    
    def disconnect(self, session_id: str):
        """Remove WebSocket connection for session"""
        if session_id in self.connections:
            del self.connections[session_id]
            logger.info(f"🔌 LLM WebSocket disconnected for session {session_id}")
    
    async def broadcast_token(self, session_id: str, token: LLMToken):
        """Broadcast LLM token"""
        await self._broadcast_event(session_id, "llm_token", {
            "text": token.text,
            "is_final": token.is_final,
            "provider": token.provider.value if token.provider else None,
            "token_timestamp": token.timestamp
        })
    
    async def broadcast_response_start(self, session_id: str, user_input: str):
        """Broadcast LLM response start"""
        await self._broadcast_event(session_id, "llm_response_start", {
            "user_input": user_input
        })
    
    async def broadcast_response_complete(self, session_id: str, response: LLMResponse):
        """Broadcast LLM response completion"""
        await self._broadcast_event(session_id, "llm_response_complete", {
            "text": response.text,
            "total_tokens": response.total_tokens,
            "tokens_per_second": response.tokens_per_second,
            "first_token_latency_ms": response.first_token_latency_ms,
            "provider": response.provider.value if response.provider else None,
            "user_utterance": response.user_utterance
        })
    
    async def broadcast_error(self, session_id: str, error: str):
        """Broadcast LLM error"""
        await self._broadcast_event(session_id, "llm_error", {
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
_llm_event_broadcaster = LLMEventBroadcaster()

def get_llm_broadcaster() -> LLMEventBroadcaster:
    """Get global LLM event broadcaster"""
    return _llm_event_broadcaster