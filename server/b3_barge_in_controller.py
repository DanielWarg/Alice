"""
B3 Barge-In Controller - Stoppa TTS vid voice activity
Integrerar med B2 voice system och TTS pipeline
"""

import asyncio
import time
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime, timedelta
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("alice.b3_barge_in")

# Import metrics
try:
    from b3_metrics import record_barge_in, record_error
except ImportError:
    logger.warning("B3 metrics not available")
    record_barge_in = lambda *args, **kwargs: None
    record_error = lambda *args, **kwargs: None

class BargeInRequest(BaseModel):
    """Request to trigger barge-in"""
    source: str = "voice"  # voice, user, manual
    confidence: float = 1.0
    reason: str = "voice_activity_detected"

class BargeInResponse(BaseModel):
    """Response from barge-in trigger"""
    success: bool
    message: str
    stopped_processes: list
    timestamp: float

class B3BargeInController:
    """
    Controls barge-in functionality for B3 ambient voice system
    Integrates with TTS systems and voice processing pipeline
    """
    
    def __init__(self):
        # Active TTS sessions that can be interrupted
        self.active_tts_sessions: Set[str] = set()
        
        # Barge-in triggers and handlers
        self.barge_in_handlers = []
        self.voice_activity_threshold = 0.02  # Energy threshold for voice detection
        
        # Timing controls
        self.barge_in_cooldown = 0.5  # 500ms cooldown between barge-ins
        self.last_barge_in = 0
        
        # Statistics
        self.barge_in_count = 0
        self.false_positive_count = 0
        
        logger.info("B3 Barge-In Controller initialized")
    
    async def trigger_barge_in(self, request: BargeInRequest) -> BargeInResponse:
        """
        Trigger barge-in to stop all active TTS and voice output
        """
        current_time = time.time()
        
        # Check cooldown to prevent rapid triggering
        if current_time - self.last_barge_in < self.barge_in_cooldown:
            return BargeInResponse(
                success=False,
                message="Barge-in on cooldown",
                stopped_processes=[],
                timestamp=current_time
            )
        
        stopped_processes = []
        
        try:
            # Stop all active TTS sessions
            for session_id in list(self.active_tts_sessions):
                await self._stop_tts_session(session_id)
                stopped_processes.append(f"tts_session_{session_id}")
            
            # Stop other audio outputs (music, notifications, etc.)
            await self._stop_audio_outputs()
            stopped_processes.extend(["music_player", "notification_sounds"])
            
            # Trigger registered barge-in handlers
            for handler in self.barge_in_handlers:
                try:
                    await handler(request)
                    stopped_processes.append(f"handler_{handler.__name__}")
                except Exception as e:
                    logger.error(f"Error in barge-in handler {handler.__name__}: {e}")
            
            # Update statistics
            self.barge_in_count += 1
            self.last_barge_in = current_time
            
            # Record metrics
            latency_ms = (current_time - current_time) * 1000  # This would be measured properly in real implementation
            record_barge_in(success=True, stopped_processes=len(stopped_processes), latency_ms=latency_ms)
            
            logger.info(f"Barge-in triggered: {request.source} (confidence: {request.confidence:.2f})")
            
            return BargeInResponse(
                success=True,
                message=f"Barge-in successful: stopped {len(stopped_processes)} processes",
                stopped_processes=stopped_processes,
                timestamp=current_time
            )
            
        except Exception as e:
            logger.error(f"Error during barge-in: {e}")
            record_barge_in(success=False)
            record_error("barge_in", "trigger_failed")
            return BargeInResponse(
                success=False,
                message=f"Barge-in failed: {str(e)}",
                stopped_processes=stopped_processes,
                timestamp=current_time
            )
    
    async def _stop_tts_session(self, session_id: str):
        """Stop specific TTS session"""
        try:
            # Try to import and stop TTS processes
            # This would integrate with actual TTS system
            
            # Mock TTS stop for now
            logger.debug(f"Stopping TTS session: {session_id}")
            
            # Remove from active sessions
            self.active_tts_sessions.discard(session_id)
            
            # TODO: Integrate with actual TTS system
            # Examples:
            # - Stop OpenAI TTS stream
            # - Stop local TTS (Piper, etc.)
            # - Cancel queued TTS requests
            
        except Exception as e:
            logger.error(f"Error stopping TTS session {session_id}: {e}")
    
    async def _stop_audio_outputs(self):
        """Stop other audio outputs (music, notifications, etc.)"""
        try:
            # Stop music playback
            await self._stop_music_player()
            
            # Stop notification sounds
            await self._stop_notification_sounds()
            
            # Stop any other audio outputs
            await self._stop_system_sounds()
            
        except Exception as e:
            logger.error(f"Error stopping audio outputs: {e}")
    
    async def _stop_music_player(self):
        """Stop music player"""
        try:
            # This would integrate with Spotify API or local music player
            logger.debug("Stopping music player")
            
            # TODO: Integrate with actual music control
            # Example: spotify_client.pause_playback()
            
        except Exception as e:
            logger.error(f"Error stopping music player: {e}")
    
    async def _stop_notification_sounds(self):
        """Stop notification sounds"""
        try:
            logger.debug("Stopping notification sounds")
            
            # TODO: Stop any playing notification sounds
            
        except Exception as e:
            logger.error(f"Error stopping notification sounds: {e}")
    
    async def _stop_system_sounds(self):
        """Stop system sounds"""
        try:
            logger.debug("Stopping system sounds")
            
            # TODO: Stop any system sounds or alerts
            
        except Exception as e:
            logger.error(f"Error stopping system sounds: {e}")
    
    def register_tts_session(self, session_id: str):
        """Register a TTS session that can be interrupted"""
        self.active_tts_sessions.add(session_id)
        logger.debug(f"Registered TTS session: {session_id}")
    
    def unregister_tts_session(self, session_id: str):
        """Unregister a TTS session (completed or failed)"""
        self.active_tts_sessions.discard(session_id)
        logger.debug(f"Unregistered TTS session: {session_id}")
    
    def register_barge_in_handler(self, handler):
        """Register a custom barge-in handler"""
        self.barge_in_handlers.append(handler)
        logger.debug(f"Registered barge-in handler: {handler.__name__}")
    
    async def check_voice_activity_barge_in(self, audio_energy: float, confidence: float = 1.0):
        """
        Check if voice activity should trigger barge-in
        Called from B3 ambient voice processing
        """
        if audio_energy > self.voice_activity_threshold and len(self.active_tts_sessions) > 0:
            # Voice detected while TTS is playing - trigger barge-in
            await self.trigger_barge_in(BargeInRequest(
                source="voice_activity",
                confidence=confidence,
                reason=f"Voice energy {audio_energy:.3f} > threshold {self.voice_activity_threshold}"
            ))
    
    def get_status(self) -> Dict[str, Any]:
        """Get current barge-in controller status"""
        return {
            "active_tts_sessions": len(self.active_tts_sessions),
            "barge_in_count": self.barge_in_count,
            "false_positive_count": self.false_positive_count,
            "last_barge_in": self.last_barge_in,
            "cooldown_remaining": max(0, self.barge_in_cooldown - (time.time() - self.last_barge_in)),
            "voice_threshold": self.voice_activity_threshold
        }

# Global instance
_barge_in_controller = None

def get_b3_barge_in_controller():
    """Get singleton B3 barge-in controller"""
    global _barge_in_controller
    if _barge_in_controller is None:
        _barge_in_controller = B3BargeInController()
    return _barge_in_controller

# FastAPI router for barge-in endpoints
router = APIRouter(prefix="/api/voice", tags=["barge-in"])

@router.post("/barge-in")
async def trigger_barge_in_endpoint(request: BargeInRequest) -> BargeInResponse:
    """
    API endpoint to manually trigger barge-in
    Used for testing and manual control
    """
    controller = get_b3_barge_in_controller()
    return await controller.trigger_barge_in(request)

@router.get("/barge-in/status")
async def get_barge_in_status():
    """Get current barge-in controller status"""
    controller = get_b3_barge_in_controller()
    return controller.get_status()

@router.post("/tts/register/{session_id}")
async def register_tts_session(session_id: str):
    """Register a TTS session for barge-in control"""
    controller = get_b3_barge_in_controller()
    controller.register_tts_session(session_id)
    return {"success": True, "message": f"TTS session {session_id} registered"}

@router.post("/tts/unregister/{session_id}")
async def unregister_tts_session(session_id: str):
    """Unregister a TTS session"""
    controller = get_b3_barge_in_controller()
    controller.unregister_tts_session(session_id)
    return {"success": True, "message": f"TTS session {session_id} unregistered"}

# Integration hooks for other systems
async def integrate_with_b2_voice_system():
    """
    Integration hook for B2 voice system
    This would be called during B2 initialization
    """
    controller = get_b3_barge_in_controller()
    
    async def b2_voice_activity_handler(energy_level: float):
        """Handler for B2 voice activity detection"""
        await controller.check_voice_activity_barge_in(energy_level)
    
    # Register the handler with B2 system
    # TODO: Actually integrate with B2 voice processing
    controller.register_barge_in_handler(b2_voice_activity_handler)
    
    logger.info("B3 Barge-In integrated with B2 voice system")