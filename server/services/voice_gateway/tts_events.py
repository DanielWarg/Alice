#!/usr/bin/env python3
"""
📡 TTS Event Broadcasting System
WebSocket-based real-time TTS audio streaming for Alice Voice Gateway
"""
import asyncio
import json
import logging
import time
import base64
from typing import Dict
from fastapi import WebSocket, WebSocketDisconnect

from tts_stream import TTSAudioChunk, TTSResponse

logger = logging.getLogger(__name__)

class TTSEventBroadcaster:
    """Manage WebSocket connections and broadcast TTS audio events"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket):
        """Add new WebSocket connection for session"""
        await websocket.accept()
        self.connections[session_id] = websocket
        logger.info(f"🔌 TTS WebSocket connected for session {session_id}")
    
    def disconnect(self, session_id: str):
        """Remove WebSocket connection for session"""
        if session_id in self.connections:
            del self.connections[session_id]
            logger.info(f"🔌 TTS WebSocket disconnected for session {session_id}")
    
    async def broadcast_audio_chunk(self, session_id: str, chunk: TTSAudioChunk):
        """Broadcast TTS audio chunk"""
        # Encode audio data as base64 for WebSocket transmission
        audio_b64 = base64.b64encode(chunk.audio_data).decode('utf-8')
        
        await self._broadcast_event(session_id, "tts_audio_chunk", {
            "audio_data": audio_b64,
            "sample_rate": chunk.sample_rate,
            "format": chunk.format,
            "is_final": chunk.is_final,
            "provider": chunk.provider.value if chunk.provider else None,
            "chunk_index": chunk.chunk_index,
            "chunk_timestamp": chunk.timestamp
        })
    
    async def broadcast_synthesis_start(self, session_id: str, text: str):
        """Broadcast TTS synthesis start"""
        await self._broadcast_event(session_id, "tts_synthesis_start", {
            "text": text
        })
    
    async def broadcast_synthesis_complete(self, session_id: str, response: TTSResponse):
        """Broadcast TTS synthesis completion"""
        await self._broadcast_event(session_id, "tts_synthesis_complete", {
            "text": response.text,
            "total_duration_ms": response.total_duration_ms,
            "first_audio_latency_ms": response.first_audio_latency_ms,
            "synthesis_time_ms": response.synthesis_time_ms,
            "provider": response.provider.value if response.provider else None,
            "audio_quality_score": response.audio_quality_score,
            "total_chunks": len(response.audio_chunks)
        })
    
    async def broadcast_error(self, session_id: str, error: str):
        """Broadcast TTS error"""
        await self._broadcast_event(session_id, "tts_error", {
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
            
            # Log without audio data to avoid spam
            if event_type == "tts_audio_chunk":
                logger.debug(f"📡 Broadcast audio chunk to session {session_id} (chunk {data.get('chunk_index', 0)})")
            else:
                logger.debug(f"📡 Broadcast {event_type} to session {session_id}")
                
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
_tts_event_broadcaster = TTSEventBroadcaster()

def get_tts_broadcaster() -> TTSEventBroadcaster:
    """Get global TTS event broadcaster"""
    return _tts_event_broadcaster