"""
B3 Ambient Voice System - Always-On Voice Processing
Handles continuous audio stream, transcription, and ambient memory ingestion
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
import base64
import numpy as np

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from b3_ambient_transcriber import get_b3_ambient_transcriber
from b3_barge_in_controller import get_b3_barge_in_controller

logger = logging.getLogger("alice.b3_ambient")
logger.setLevel(logging.DEBUG)

class VoiceFrame(BaseModel):
    """Single audio frame from client"""
    audio_data: str  # Base64 encoded PCM
    timestamp: float
    sample_rate: int = 16000
    duration_ms: int = 20

class AmbientState(BaseModel):
    """Current state of ambient voice system"""
    is_active: bool = False
    is_muted: bool = False
    session_start: Optional[datetime] = None
    frames_processed: int = 0
    last_transcription: Optional[str] = None
    memory_events_created: int = 0

class B3AmbientVoiceManager:
    """Manages always-on ambient voice processing"""
    
    def __init__(self, memory_store=None):
        self.memory = memory_store
        self.active_sessions: Dict[str, Dict] = {}
        self.global_state = AmbientState()
        
        # Audio processing buffer
        self.audio_buffer = []
        self.buffer_duration_ms = 2000  # 2 second buffer
        
        # Privacy and safety controls
        self.hard_mute = False
        
        # Initialize B3 transcriber and barge-in controller
        self.transcriber = get_b3_ambient_transcriber()
        self.barge_in_controller = get_b3_barge_in_controller()
        
    async def handle_ambient_voice(self, websocket: WebSocket, session_id: str = "default"):
        """Main handler for ambient voice WebSocket connection"""
        await websocket.accept()
        
        try:
            self.active_sessions[session_id] = {
                "websocket": websocket,
                "start_time": datetime.now(),
                "state": AmbientState(is_active=True, session_start=datetime.now()),
                "audio_buffer": [],
                "last_vad_activity": time.time()
            }
            
            logger.info(f"B3 Ambient voice session started: {session_id}")
            
            # Start transcriber
            logger.debug("Starting B3 transcriber...")
            await self.transcriber.start()
            logger.debug("B3 transcriber started successfully")
            
            # Send initial status
            logger.debug("Sending initial status update...")
            await self._send_status_update(websocket, session_id)
            logger.debug("Initial status sent successfully")
            
            while True:
                try:
                    # Receive audio frames or control messages
                    data = await websocket.receive_json()
                    await self._process_message(websocket, session_id, data)
                    
                except WebSocketDisconnect:
                    logger.info(f"Ambient voice session disconnected: {session_id}")
                    break
                except asyncio.TimeoutError:
                    # Send keepalive
                    await self._send_keepalive(websocket, session_id)
                except Exception as e:
                    logger.error(f"Error in ambient voice session {session_id}: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                        "timestamp": time.time()
                    })
                    
        except Exception as e:
            logger.error(f"Fatal error in ambient voice session {session_id}: {e}")
        finally:
            # Cleanup session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            # Stop transcriber if no active sessions
            if not self.active_sessions:
                await self.transcriber.stop()
                
            logger.info(f"B3 Ambient voice session cleanup: {session_id}")
    
    async def _process_message(self, websocket: WebSocket, session_id: str, data: Dict[str, Any]):
        """Process incoming WebSocket message"""
        msg_type = data.get("type")
        
        if msg_type == "audio_frame":
            await self._process_audio_frame(websocket, session_id, data)
        elif msg_type == "control":
            await self._process_control_message(websocket, session_id, data)
        elif msg_type == "ping":
            await websocket.send_json({"type": "pong", "timestamp": time.time()})
        else:
            logger.warning(f"Unknown message type: {msg_type}")
    
    async def _process_audio_frame(self, websocket: WebSocket, session_id: str, data: Dict[str, Any]):
        """Process single audio frame for ambient transcription"""
        session = self.active_sessions.get(session_id)
        if not session or self.hard_mute:
            return
            
        # Check if session is muted
        if session["state"].is_muted:
            return
            
        try:
            # Extract audio frame
            frame = VoiceFrame(**data)
            
            # Add to buffer
            session["audio_buffer"].append(frame)
            session["last_vad_activity"] = time.time()
            
            # Keep buffer size manageable
            max_buffer_frames = (self.buffer_duration_ms // frame.duration_ms)
            if len(session["audio_buffer"]) > max_buffer_frames:
                session["audio_buffer"].pop(0)
            
            # Update counters
            session["state"].frames_processed += 1
            
            # Process buffer if enough frames accumulated
            if len(session["audio_buffer"]) >= 50:  # ~1 second at 20ms frames
                await self._process_audio_buffer(websocket, session_id)
                
        except Exception as e:
            logger.error(f"Error processing audio frame: {e}")
    
    async def _process_audio_buffer(self, websocket: WebSocket, session_id: str):
        """Process accumulated audio buffer for transcription"""
        session = self.active_sessions.get(session_id)
        if not session:
            return
            
        try:
            buffer_size = len(session["audio_buffer"])
            
            if buffer_size > 0:
                # Convert audio frames to numpy array for transcriber
                audio_frames = []
                timestamps = []
                
                for frame in session["audio_buffer"]:
                    # Decode base64 PCM data
                    pcm_bytes = base64.b64decode(frame.audio_data)
                    pcm_array = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                    
                    audio_frames.append(pcm_array)
                    timestamps.append(frame.timestamp)
                
                # Combine frames
                if audio_frames:
                    combined_audio = np.concatenate(audio_frames)
                    avg_timestamp = sum(timestamps) / len(timestamps)
                    
                    # Process with transcriber
                    transcription_result = await self.transcriber.process_audio_frame(
                        combined_audio, avg_timestamp
                    )
                    
                    if transcription_result:
                        # Update session state
                        session["state"].last_transcription = transcription_result.get('text', '')
                        
                        # Check for barge-in trigger if voice activity detected
                        if transcription_result.get('has_voice_activity', False):
                            # Calculate voice energy level from audio
                            audio_energy = float(np.mean(np.abs(combined_audio)))
                            await self.barge_in_controller.check_voice_activity_barge_in(
                                audio_energy, 
                                transcription_result.get('confidence', 0)
                            )
                        
                        # Send result to client
                        await websocket.send_json({
                            "type": "transcription_result",
                            "text": transcription_result.get('text', ''),
                            "confidence": transcription_result.get('confidence', 0),
                            "importance_score": transcription_result.get('importance_score', 0),
                            "importance_reasons": transcription_result.get('importance_reasons', []),
                            "will_store": transcription_result.get('will_store', False),
                            "timestamp": time.time(),
                            "buffer_frames": buffer_size
                        })
                        
                        logger.debug(f"Transcription result: {transcription_result.get('text', '')[:50]}...")
                
                # Clear processed frames (keep overlap)
                session["audio_buffer"] = session["audio_buffer"][-10:]  # Keep last 10 frames
                
        except Exception as e:
            logger.error(f"Error processing audio buffer: {e}")
    
    async def _process_control_message(self, websocket: WebSocket, session_id: str, data: Dict[str, Any]):
        """Process control messages (mute/unmute, etc.)"""
        session = self.active_sessions.get(session_id)
        if not session:
            return
            
        command = data.get("command")
        
        if command == "mute":
            session["state"].is_muted = True
            session["audio_buffer"].clear()  # Clear buffer on mute
            logger.info(f"Session {session_id} muted")
            
        elif command == "unmute":
            if not self.hard_mute:  # Respect hard mute override
                session["state"].is_muted = False
                logger.info(f"Session {session_id} unmuted")
                
        elif command == "hard_mute":
            self.hard_mute = True
            # Mute all sessions
            for sid, sess in self.active_sessions.items():
                sess["state"].is_muted = True
                sess["audio_buffer"].clear()
            logger.warning("HARD MUTE activated - all sessions muted")
            
        elif command == "hard_unmute":
            self.hard_mute = False
            logger.info("Hard mute released")
            
        elif command == "clear_memory":
            # Implement memory clearing for privacy
            try:
                from b3_privacy_hooks import get_b3_privacy_manager, ForgetRequest
                privacy_manager = get_b3_privacy_manager()
                
                # Create forget request for recent session data
                forget_request = ForgetRequest(
                    time_range="last_hour"  # Clear last hour of data
                )
                
                await privacy_manager.process_forget_request(forget_request)
                logger.info(f"Processed memory clearing request for session {session_id}")
                
            except Exception as e:
                logger.error(f"Failed to clear memory for session {session_id}: {e}")
            
            logger.info(f"Memory clear requested for session {session_id}")
            
        # Send status update after control command
        await self._send_status_update(websocket, session_id)
    
    async def _send_status_update(self, websocket: WebSocket, session_id: str):
        """Send current status to client"""
        session = self.active_sessions.get(session_id)
        if not session:
            return
            
        status = {
            "type": "status_update",
            "session_id": session_id,
            "is_active": session["state"].is_active,
            "is_muted": session["state"].is_muted,
            "hard_mute": self.hard_mute,
            "frames_processed": session["state"].frames_processed,
            "buffer_size": len(session["audio_buffer"]),
            "session_duration": (datetime.now() - session["start_time"]).total_seconds(),
            "timestamp": time.time()
        }
        
        await websocket.send_json(status)
    
    async def _send_keepalive(self, websocket: WebSocket, session_id: str):
        """Send keepalive ping"""
        await websocket.send_json({
            "type": "keepalive",
            "session_id": session_id,
            "timestamp": time.time()
        })

# Global instance
_ambient_manager = None

def get_b3_ambient_manager(memory_store=None):
    """Get singleton B3 ambient voice manager"""
    global _ambient_manager
    if _ambient_manager is None:
        _ambient_manager = B3AmbientVoiceManager(memory_store)
    return _ambient_manager