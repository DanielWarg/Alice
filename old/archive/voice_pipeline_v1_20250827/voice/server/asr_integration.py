#!/usr/bin/env python3
"""
🔗 ASR Integration Bridge
Connects faster-whisper ASR with voice transport system
Handles audio frames → transcription → WebSocket events
"""

import asyncio
import json
import logging
import time
import struct
import numpy as np
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass
import websockets
from websockets import WebSocketServerProtocol

from adapters.asr_faster_whisper import StreamingASR, ASRConfig, ASRResult, create_streaming_asr

logger = logging.getLogger(__name__)

@dataclass
class SessionState:
    """Per-session ASR state"""
    session_id: str
    asr: StreamingASR
    websocket: WebSocketServerProtocol
    connected_at: float
    last_activity: float
    frames_processed: int = 0
    partial_count: int = 0
    final_count: int = 0

class ASRWebSocketServer:
    """WebSocket server with integrated ASR processing"""
    
    def __init__(self, host: str = "localhost", port: int = 8001):
        self.host = host
        self.port = port
        self.sessions: Dict[str, SessionState] = {}
        self.server = None
        
        # ASR configuration for optimal performance
        self.asr_config = ASRConfig(
            model_size="base",  # Good balance of speed/accuracy
            device="cpu",       # Most compatible
            compute_type="int8", # Fastest on CPU
            chunk_ms=200,       # 200ms chunks for ≤200ms partial
            stabilize_ms=250,   # 250ms silence for final
            beam_size=1,        # Fastest decoding
            temperature=0.0,    # Deterministic
            min_partial_words=2, # Avoid noise
            vad_filter=True     # Built-in VAD
        )
        
        # Performance tracking
        self.stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "total_frames": 0,
            "total_partials": 0,
            "total_finals": 0,
            "avg_partial_latency": 0.0,
            "avg_final_latency": 0.0
        }
        
        logger.info(f"ASRWebSocketServer initialized: {host}:{port}")
    
    async def start_server(self) -> None:
        """Start WebSocket server"""
        try:
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                max_size=1024*1024,  # 1MB max message size
                max_queue=32,        # Max queued messages
                ping_interval=10,    # Ping every 10s
                ping_timeout=5,      # Timeout after 5s
            )
            
            logger.info(f"✅ ASR WebSocket server started on ws://{self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start ASR server: {e}")
            raise
    
    async def handle_client(self, websocket: WebSocketServerProtocol) -> None:
        """Handle new WebSocket client connection"""
        session_id = f"session_{int(time.time()*1000)}"
        remote_addr = websocket.remote_address
        
        logger.info(f"🔌 New ASR session: {session_id} from {remote_addr}")
        
        # Create per-session ASR instance
        asr = create_streaming_asr(
            on_partial=lambda result: asyncio.create_task(self._handle_partial(session_id, result)),
            on_final=lambda result: asyncio.create_task(self._handle_final(session_id, result)),
            config=self.asr_config
        )
        
        # Initialize ASR
        try:
            await asr.initialize()
            asr.start_processing()
        except Exception as e:
            logger.error(f"❌ Failed to initialize ASR for {session_id}: {e}")
            await websocket.close(code=1011, reason="ASR initialization failed")
            return
        
        # Create session state
        session = SessionState(
            session_id=session_id,
            asr=asr,
            websocket=websocket,
            connected_at=time.time(),
            last_activity=time.time()
        )
        
        self.sessions[session_id] = session
        self.stats["total_sessions"] += 1
        self.stats["active_sessions"] += 1
        
        # Send handshake
        await self._send_message(websocket, {
            "type": "handshake",
            "session_id": session_id,
            "timestamp": int(time.time() * 1000),
            "asr_config": {
                "model": self.asr_config.model_size,
                "sample_rate": self.asr_config.sample_rate,
                "chunk_ms": self.asr_config.chunk_ms
            }
        })
        
        try:
            # Handle messages from client
            async for message in websocket:
                await self._process_client_message(session, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 Client disconnected: {session_id}")
        except Exception as e:
            logger.error(f"❌ Session error {session_id}: {e}")
        finally:
            # Cleanup session
            await self._cleanup_session(session_id)
    
    async def _process_client_message(self, session: SessionState, message) -> None:
        """Process message from WebSocket client"""
        session.last_activity = time.time()
        
        if isinstance(message, bytes):
            # Binary audio frame
            await self._handle_audio_frame(session, message)
            
        elif isinstance(message, str):
            # JSON control message
            try:
                data = json.loads(message)
                await self._handle_control_message(session, data)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from {session.session_id}: {message[:100]}")
    
    async def _handle_audio_frame(self, session: SessionState, audio_data: bytes) -> None:
        """Handle binary audio frame from client"""
        try:
            # Convert binary audio to Float32Array
            # Assuming 16-bit signed integers (client sends as Int16)
            if len(audio_data) % 2 != 0:
                logger.warning(f"Invalid audio frame size: {len(audio_data)} bytes")
                return
                
            # Convert from Int16 to Float32
            int16_data = struct.unpack(f"<{len(audio_data)//2}h", audio_data)
            samples = np.array(int16_data, dtype=np.float32) / 32768.0  # Normalize to [-1, 1]
            
            # Validate frame size
            expected_samples = int(0.02 * self.asr_config.sample_rate)  # 20ms frame
            if len(samples) != expected_samples:
                logger.debug(f"Unexpected frame size: {len(samples)} (expected {expected_samples})")
            
            # Send to ASR processor
            session.asr.add_audio_frame(session.session_id, samples)
            session.frames_processed += 1
            self.stats["total_frames"] += 1
            
            # Log periodic stats
            if session.frames_processed % 100 == 0:
                logger.debug(f"📊 {session.session_id}: {session.frames_processed} frames processed")
            
        except Exception as e:
            logger.error(f"❌ Audio frame processing error: {e}")
    
    async def _handle_control_message(self, session: SessionState, data: Dict[str, Any]) -> None:
        """Handle JSON control message"""
        msg_type = data.get("type")
        
        if msg_type == "control.barge_in":
            logger.info(f"🛑 Barge-in from {session.session_id}")
            # Clear ASR buffer on barge-in
            session.asr.audio_buffer.clear()
            
            # Send barge-in acknowledgment
            await self._send_message(session.websocket, {
                "type": "barge_in_ack",
                "timestamp": int(time.time() * 1000)
            })
            
        elif msg_type == "control.mic":
            enabled = data.get("enabled", False)
            logger.info(f"🎤 Mic control {session.session_id}: {'ON' if enabled else 'OFF'}")
            
            if not enabled:
                # Clear buffer when mic is disabled
                session.asr.audio_buffer.clear()
                
        elif msg_type == "ping":
            # Respond to ping
            await self._send_message(session.websocket, {
                "type": "pong", 
                "timestamp": int(time.time() * 1000)
            })
            
        else:
            logger.debug(f"Unknown control message from {session.session_id}: {msg_type}")
    
    async def _handle_partial(self, session_id: str, result: ASRResult) -> None:
        """Handle partial transcription result"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        session.partial_count += 1
        self.stats["total_partials"] += 1
        
        # Update average latency
        current_avg = self.stats["avg_partial_latency"]
        total_count = self.stats["total_partials"]
        self.stats["avg_partial_latency"] = (current_avg * (total_count - 1) + result.processing_ms) / total_count
        
        # Send to client
        await self._send_message(session.websocket, {
            "type": "stt.partial",
            "text": result.text,
            "confidence": result.confidence,
            "timestamp": int(result.timestamp_end * 1000),
            "processing_ms": result.processing_ms
        })
        
        logger.info(f"📝 PARTIAL {session_id}: '{result.text}' ({result.processing_ms:.1f}ms)")
    
    async def _handle_final(self, session_id: str, result: ASRResult) -> None:
        """Handle final transcription result"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        session.final_count += 1
        self.stats["total_finals"] += 1
        
        # Update average latency
        current_avg = self.stats["avg_final_latency"]
        total_count = self.stats["total_finals"]
        self.stats["avg_final_latency"] = (current_avg * (total_count - 1) + result.processing_ms) / total_count
        
        # Send to client
        await self._send_message(session.websocket, {
            "type": "stt.final",
            "text": result.text,
            "confidence": result.confidence,
            "timestamp": int(result.timestamp_end * 1000),
            "processing_ms": result.processing_ms
        })
        
        logger.info(f"🎯 FINAL {session_id}: '{result.text}' ({result.processing_ms:.1f}ms, conf={result.confidence:.3f})")
    
    async def _send_message(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Send JSON message to WebSocket client"""
        try:
            message = json.dumps(data)
            await websocket.send(message)
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
    
    async def _cleanup_session(self, session_id: str) -> None:
        """Clean up session resources"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        # Stop ASR processing
        try:
            session.asr.stop_processing()
        except Exception as e:
            logger.error(f"❌ Error stopping ASR for {session_id}: {e}")
        
        # Remove from sessions
        del self.sessions[session_id]
        self.stats["active_sessions"] -= 1
        
        duration = time.time() - session.connected_at
        logger.info(f"🧹 Session cleanup {session_id}: {duration:.1f}s, {session.frames_processed} frames, {session.partial_count}P/{session.final_count}F")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        current_time = time.time()
        
        # Calculate session stats
        session_stats = {}
        for session_id, session in self.sessions.items():
            asr_stats = session.asr.get_stats()
            session_stats[session_id] = {
                "frames_processed": session.frames_processed,
                "partial_count": session.partial_count,
                "final_count": session.final_count,
                "duration_s": current_time - session.connected_at,
                "last_activity_s": current_time - session.last_activity,
                **asr_stats
            }
        
        return {
            **self.stats,
            "sessions": session_stats,
            "uptime_s": current_time - self.start_time if hasattr(self, 'start_time') else 0
        }
    
    async def shutdown(self) -> None:
        """Shutdown server gracefully"""
        logger.info("🛑 Shutting down ASR WebSocket server...")
        
        # Cleanup all sessions
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self._cleanup_session(session_id)
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("✅ ASR WebSocket server shutdown complete")

# Test server
async def test_asr_server():
    """Test ASR WebSocket server"""
    server = ASRWebSocketServer(host="localhost", port=8001)
    server.start_time = time.time()
    
    try:
        await server.start_server()
        
        logger.info("🧪 ASR WebSocket server test running...")
        logger.info("   Connect a client to ws://localhost:8001")
        logger.info("   Send binary audio frames to test transcription")
        
        # Run server
        await asyncio.Future()  # Run forever
        
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted")
    finally:
        await server.shutdown()

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run test server
    asyncio.run(test_asr_server())