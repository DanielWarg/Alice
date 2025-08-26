#!/usr/bin/env python3
"""
🎯 Example Integration: OpenAI Realtime Talk Client with Voice Gateway
Demonstrates how to integrate the talk client into the existing voice gateway infrastructure
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import our talk client and existing components
from talk_client import create_talk_client, OpenAIRealtimeTalkClient
from webrtc import WebRTCManager
from metrics import VoiceMetrics

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("integration_example")

# Request/Response models
class WebRTCOfferRequest(BaseModel):
    """WebRTC offer request model"""
    session_id: str
    sdp: str
    voice: Optional[str] = "alloy"  # alloy or nova
    instructions: Optional[str] = None

class WebRTCOfferResponse(BaseModel):
    """WebRTC offer response model"""
    session_id: str
    sdp: str
    status: str

class SafeSummaryRequest(BaseModel):
    """Safe summary request model"""
    session_id: str
    summary: str

class MetricsResponse(BaseModel):
    """Metrics response model"""
    session_id: str
    metrics: Dict[str, Any]

@dataclass
class VoiceGatewaySession:
    """Voice gateway session with talk client"""
    session_id: str
    talk_client: OpenAIRealtimeTalkClient
    metrics: VoiceMetrics
    created_at: float
    is_active: bool = True
    
    # Event counters
    transcript_count: int = 0
    audio_chunks_received: int = 0
    errors_count: int = 0

class EnhancedVoiceGateway:
    """
    Enhanced Voice Gateway with OpenAI Realtime Talk Client Integration
    
    This class demonstrates how to integrate the talk client with the existing
    voice gateway infrastructure for production use.
    """
    
    def __init__(self):
        self.sessions: Dict[str, VoiceGatewaySession] = {}
        self.global_metrics = VoiceMetrics()
        self.global_metrics.initialize()
        
        # Initialize FastAPI app
        self.app = FastAPI(title="Alice Voice Gateway", version="2.0.0")
        self._setup_routes()
        
        logger.info("🚀 Enhanced Voice Gateway initialized")
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.post("/webrtc/offer", response_model=WebRTCOfferResponse)
        async def handle_webrtc_offer(request: WebRTCOfferRequest):
            """Handle WebRTC offer and create talk client session"""
            try:
                return await self.handle_webrtc_offer(request)
            except Exception as e:
                logger.error(f"❌ WebRTC offer handling failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/session/{session_id}/safe_summary")
        async def send_safe_summary(session_id: str, request: SafeSummaryRequest):
            """Send safe summary to talk client"""
            try:
                await self.send_safe_summary(session_id, request.summary)
                return {"status": "success", "session_id": session_id}
            except Exception as e:
                logger.error(f"❌ Safe summary sending failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/session/{session_id}/metrics", response_model=MetricsResponse)
        async def get_session_metrics(session_id: str):
            """Get performance metrics for a session"""
            try:
                metrics = await self.get_session_metrics(session_id)
                return MetricsResponse(session_id=session_id, metrics=metrics)
            except Exception as e:
                logger.error(f"❌ Metrics retrieval failed: {e}")
                raise HTTPException(status_code=404, detail="Session not found")
        
        @self.app.get("/metrics/global")
        async def get_global_metrics():
            """Get global voice gateway metrics"""
            return {
                "active_sessions": len([s for s in self.sessions.values() if s.is_active]),
                "total_sessions": len(self.sessions),
                "global_metrics": self.global_metrics.get_summary_metrics(),
                "session_details": {
                    sid: {
                        "active": session.is_active,
                        "transcript_count": session.transcript_count,
                        "audio_chunks": session.audio_chunks_received,
                        "errors": session.errors_count
                    } for sid, session in self.sessions.items()
                }
            }
        
        @self.app.delete("/session/{session_id}")
        async def close_session(session_id: str):
            """Close a voice session"""
            try:
                await self.close_session(session_id)
                return {"status": "success", "session_id": session_id}
            except Exception as e:
                logger.error(f"❌ Session closure failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def handle_webrtc_offer(self, request: WebRTCOfferRequest) -> WebRTCOfferResponse:
        """Handle WebRTC offer and create talk client session"""
        session_id = request.session_id
        
        try:
            # Close existing session if any
            if session_id in self.sessions:
                await self.close_session(session_id)
            
            logger.info(f"🔗 Creating new talk client session: {session_id}")
            
            # Create talk client with custom configuration
            talk_client = create_talk_client(
                voice=request.voice or "alloy",
                instructions=request.instructions
            )
            
            # Setup event handlers
            self._setup_talk_client_handlers(session_id, talk_client)
            
            # Initialize talk client
            if not await talk_client.initialize():
                raise Exception("Failed to initialize talk client")
            
            # Handle WebRTC offer
            answer_sdp = await talk_client.handle_webrtc_offer(request.sdp)
            
            # Create session tracking
            session_metrics = VoiceMetrics()
            session_metrics.initialize()
            
            session = VoiceGatewaySession(
                session_id=session_id,
                talk_client=talk_client,
                metrics=session_metrics,
                created_at=asyncio.get_event_loop().time()
            )
            
            self.sessions[session_id] = session
            
            # Update global metrics
            self.global_metrics.record_webrtc_offer()
            self.global_metrics.update_active_sessions(len(self.sessions))
            
            logger.info(f"✅ Talk client session created: {session_id}")
            
            return WebRTCOfferResponse(
                session_id=session_id,
                sdp=answer_sdp,
                status="success"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to create talk client session {session_id}: {e}")
            self.global_metrics.record_error("webrtc_offer_failed")
            raise
    
    def _setup_talk_client_handlers(self, session_id: str, talk_client: OpenAIRealtimeTalkClient):
        """Setup event handlers for talk client"""
        
        def on_transcript(text: str, is_final: bool):
            """Handle transcript events"""
            logger.info(f"📝 [{session_id}] {'Final' if is_final else 'Partial'} transcript: {text}")
            if session_id in self.sessions:
                self.sessions[session_id].transcript_count += 1
        
        def on_audio_start():
            """Handle AI audio start"""
            logger.info(f"🔊 [{session_id}] AI started speaking")
        
        def on_audio_end():
            """Handle AI audio end"""
            logger.info(f"🔇 [{session_id}] AI finished speaking")
        
        def on_error(error: str):
            """Handle errors"""
            logger.error(f"❌ [{session_id}] Talk client error: {error}")
            if session_id in self.sessions:
                self.sessions[session_id].errors_count += 1
                self.sessions[session_id].metrics.record_error("talk_client_error")
        
        def on_connection_change(connected: bool):
            """Handle connection changes"""
            status = "Connected" if connected else "Disconnected"
            logger.info(f"🔗 [{session_id}] Connection: {status}")
            if session_id in self.sessions:
                self.sessions[session_id].is_active = connected
        
        def on_safe_summary(summary: str):
            """Handle safe summary requests"""
            logger.info(f"📋 [{session_id}] Safe summary needed: {summary[:100]}...")
            # Here you would typically trigger local tool execution
            # For demo, we'll just echo back a response
            asyncio.create_task(self._handle_safe_summary_request(session_id, summary))
        
        # Assign handlers
        talk_client.on_transcript = on_transcript
        talk_client.on_audio_start = on_audio_start
        talk_client.on_audio_end = on_audio_end
        talk_client.on_error = on_error
        talk_client.on_connection_change = on_connection_change
        talk_client.on_safe_summary = on_safe_summary
    
    async def _handle_safe_summary_request(self, session_id: str, summary_request: str):
        """Handle safe summary request by executing local tools"""
        try:
            # Simulate local tool execution
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Create mock response
            if "weather" in summary_request.lower():
                response = "The weather in Stockholm is currently 15°C and partly cloudy."
            elif "time" in summary_request.lower():
                response = "The current time is 14:30 CET."
            else:
                response = "I've processed that information locally and it looks good."
            
            # Send response back to talk client
            await self.send_safe_summary(session_id, response)
            
        except Exception as e:
            logger.error(f"❌ Safe summary handling failed for {session_id}: {e}")
    
    async def send_safe_summary(self, session_id: str, summary: str):
        """Send safe summary response to talk client"""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        await session.talk_client.send_safe_summary(summary)
        logger.info(f"📤 [{session_id}] Sent safe summary: {summary[:50]}...")
    
    async def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive metrics for a session"""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        
        # Get talk client performance metrics
        talk_client_metrics = session.talk_client.get_performance_metrics()
        
        # Get session-specific metrics
        session_metrics = session.metrics.get_summary_metrics()
        
        # Combine metrics
        return {
            "session_info": {
                "session_id": session_id,
                "created_at": session.created_at,
                "uptime_seconds": asyncio.get_event_loop().time() - session.created_at,
                "is_active": session.is_active
            },
            "activity_counters": {
                "transcript_count": session.transcript_count,
                "audio_chunks_received": session.audio_chunks_received,
                "errors_count": session.errors_count
            },
            "talk_client_performance": talk_client_metrics,
            "session_metrics": session_metrics
        }
    
    async def close_session(self, session_id: str):
        """Close and cleanup a session"""
        if session_id not in self.sessions:
            logger.warning(f"⚠️  Session {session_id} not found for closure")
            return
        
        session = self.sessions[session_id]
        
        try:
            # Close talk client
            await session.talk_client.disconnect()
            
            # Mark as inactive
            session.is_active = False
            
            # Remove from active sessions
            del self.sessions[session_id]
            
            # Update global metrics
            self.global_metrics.update_active_sessions(len(self.sessions))
            
            logger.info(f"✅ Session {session_id} closed successfully")
            
        except Exception as e:
            logger.error(f"❌ Error closing session {session_id}: {e}")
    
    async def cleanup_inactive_sessions(self):
        """Periodic cleanup of inactive sessions"""
        while True:
            try:
                current_time = asyncio.get_event_loop().time()
                to_remove = []
                
                for session_id, session in self.sessions.items():
                    # Remove sessions inactive for more than 5 minutes
                    if (not session.is_active and 
                        current_time - session.created_at > 300):
                        to_remove.append(session_id)
                
                for session_id in to_remove:
                    await self.close_session(session_id)
                    logger.info(f"🧹 Cleaned up inactive session: {session_id}")
                
                # Update metrics
                self.global_metrics.update_uptime()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"❌ Cleanup error: {e}")
                await asyncio.sleep(60)
    
    async def start(self, host: str = "0.0.0.0", port: int = 8001):
        """Start the enhanced voice gateway"""
        import uvicorn
        
        logger.info(f"🚀 Starting Enhanced Voice Gateway on {host}:{port}")
        
        # Start cleanup task
        cleanup_task = asyncio.create_task(self.cleanup_inactive_sessions())
        
        try:
            # Start FastAPI server
            config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
            server = uvicorn.Server(config)
            await server.serve()
        finally:
            cleanup_task.cancel()
            
            # Close all sessions
            for session_id in list(self.sessions.keys()):
                await self.close_session(session_id)

# Example usage
async def main():
    """Example usage of the enhanced voice gateway"""
    logging.basicConfig(level=logging.INFO)
    
    # Create and start the enhanced voice gateway
    gateway = EnhancedVoiceGateway()
    await gateway.start(host="127.0.0.1", port=8001)

# Production deployment example
async def production_example():
    """Example production deployment with monitoring"""
    
    # Setup structured logging
    import structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logger = structlog.get_logger("production_voice_gateway")
    
    try:
        # Create gateway with production settings
        gateway = EnhancedVoiceGateway()
        
        # Add health check endpoint
        @gateway.app.get("/health")
        async def health_check():
            active_sessions = len([s for s in gateway.sessions.values() if s.is_active])
            return {
                "status": "healthy",
                "active_sessions": active_sessions,
                "total_sessions": len(gateway.sessions),
                "timestamp": asyncio.get_event_loop().time()
            }
        
        # Start with production configuration
        logger.info("🏭 Starting production voice gateway")
        await gateway.start(host="0.0.0.0", port=8000)
        
    except Exception as e:
        logger.error("💥 Production startup failed", error=str(e))
        raise

if __name__ == "__main__":
    # Choose which example to run
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "production":
        asyncio.run(production_example())
    else:
        asyncio.run(main())