#!/usr/bin/env python3
"""
🎙️ Complete Voice Pipeline Server
WebSocket server with integrated ASR streaming
Connects browser clients → ASR → future LLM/TTS integration
"""

import asyncio
import json
import logging
import time
import struct
import numpy as np
from typing import Dict, Any, Optional
from dataclasses import dataclass
import websockets
from websockets import WebSocketServerProtocol

from adapters.asr_faster_whisper import StreamingASR, ASRConfig, ASRResult, create_streaming_asr
from adapters.llm_gpt_oss import StreamingLLM, LLMConfig, LLMResult, create_streaming_llm
from adapters.tts_dummy import StreamingTTS, TTSConfig, TTSResult, create_streaming_tts

logger = logging.getLogger(__name__)

@dataclass
class VoiceSession:
    """Complete voice processing session"""
    session_id: str
    websocket: WebSocketServerProtocol
    asr: StreamingASR
    llm: StreamingLLM
    tts: StreamingTTS
    connected_at: float
    last_activity: float
    
    # Statistics
    frames_received: int = 0
    partial_transcriptions: int = 0
    final_transcriptions: int = 0
    llm_requests: int = 0
    llm_responses: int = 0
    tts_requests: int = 0
    tts_responses: int = 0
    
    # State
    mic_enabled: bool = False
    is_speaking: bool = False
    is_processing_llm: bool = False
    is_processing_tts: bool = False

class VoicePipelineServer:
    """Complete voice pipeline server with ASR integration"""
    
    def __init__(self, host: str = "localhost", port: int = 8001):
        self.host = host
        self.port = port
        self.sessions: Dict[str, VoiceSession] = {}
        self.server = None
        
        # ASR configuration optimized for real-time
        self.asr_config = ASRConfig(
            model_size="tiny",      # Fast but reasonable accuracy
            device="cpu",
            compute_type="int8",
            chunk_ms=160,           # 160ms chunks for faster response
            stabilize_ms=250,       # 250ms silence for final
            no_speech_threshold=0.3, # Balanced threshold
            min_partial_words=1,    # Allow single words
            vad_filter=False        # Disabled for testing
        )
        
        # LLM configuration optimized for voice conversations
        self.llm_config = LLMConfig(
            model_name="gpt-oss:20b",
            max_tokens=50,          # Short voice responses
            temperature=0.3,        # Focused but natural
            system_prompt="You are Alice, a helpful AI assistant. Give very concise, natural responses suitable for voice conversation. Keep responses to 1-2 short sentences."
        )
        
        # TTS configuration optimized for streaming
        self.tts_config = TTSConfig(
            model_path="../../server/models/tts/sv_SE-nst-medium.onnx",
            chunk_ms=60,            # 60ms chunks for low latency
            max_text_length=150,    # Split long responses
            speed=1.1,              # Slightly faster speech
            sentence_split=True     # Split on punctuation
        )
        
        # Server statistics
        self.stats = {
            "start_time": time.time(),
            "total_sessions": 0,
            "active_sessions": 0,
            "total_audio_frames": 0,
            "total_partial_transcriptions": 0,
            "total_final_transcriptions": 0,
            "average_asr_latency": 0.0
        }
        
        logger.info(f"VoicePipelineServer initialized: {host}:{port}")
    
    async def start_server(self) -> None:
        """Start the voice pipeline WebSocket server"""
        try:
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                max_size=2*1024*1024,  # 2MB max message
                max_queue=64,          # Max queued messages
                ping_interval=15,      # Ping every 15s
                ping_timeout=10,       # Timeout after 10s
                compression=None       # No compression for audio
            )
            
            logger.info(f"✅ Voice Pipeline Server started on ws://{self.host}:{self.port}")
            logger.info(f"   ASR Model: {self.asr_config.model_size}")
            logger.info(f"   Chunk size: {self.asr_config.chunk_ms}ms")
            logger.info(f"   Ready for voice clients!")
            
        except Exception as e:
            logger.error(f"❌ Failed to start voice pipeline server: {e}")
            raise
    
    async def handle_client(self, websocket: WebSocketServerProtocol) -> None:
        """Handle new WebSocket voice client"""
        session_id = f"voice_session_{int(time.time()*1000)}"
        remote_addr = websocket.remote_address
        
        logger.info(f"🔌 New voice session: {session_id} from {remote_addr}")
        
        # Store event loop reference for thread-safe callback execution
        loop = asyncio.get_event_loop()
        
        # Create ASR instance for this session
        asr = create_streaming_asr(
            on_partial=lambda result: asyncio.run_coroutine_threadsafe(
                self._handle_asr_partial(session_id, result), loop
            ),
            on_final=lambda result: asyncio.run_coroutine_threadsafe(
                self._handle_asr_final(session_id, result), loop
            ),
            config=self.asr_config
        )
        
        # Create LLM instance for this session  
        llm = create_streaming_llm(
            on_token=lambda result: asyncio.run_coroutine_threadsafe(
                self._handle_llm_token(session_id, result), loop
            ),
            on_complete=lambda result: asyncio.run_coroutine_threadsafe(
                self._handle_llm_complete(session_id, result), loop
            ),
            config=self.llm_config
        )
        
        # Create TTS instance for this session
        tts = create_streaming_tts(
            on_chunk=lambda result: asyncio.run_coroutine_threadsafe(
                self._handle_tts_chunk(session_id, result), loop
            ),
            on_complete=lambda result: asyncio.run_coroutine_threadsafe(
                self._handle_tts_complete(session_id, result), loop
            ),
            config=self.tts_config
        )
        
        # Initialize ASR, LLM and TTS in parallel
        try:
            start_time = time.time()
            
            # Initialize all components concurrently
            asr_task = asr.initialize()
            llm_task = llm.initialize()
            tts_task = tts.initialize()
            
            await asyncio.gather(asr_task, llm_task, tts_task)
            
            # Start ASR processing
            asr.start_processing()
            
            init_time = (time.time() - start_time) * 1000
            logger.info(f"✅ ASR + LLM + TTS initialized for {session_id} in {init_time:.1f}ms")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize ASR/LLM/TTS for {session_id}: {e}")
            await websocket.close(code=1011, reason="Voice pipeline initialization failed")
            return
        
        # Create session
        session = VoiceSession(
            session_id=session_id,
            websocket=websocket,
            asr=asr,
            llm=llm,
            tts=tts,
            connected_at=time.time(),
            last_activity=time.time()
        )
        
        self.sessions[session_id] = session
        self.stats["total_sessions"] += 1
        self.stats["active_sessions"] += 1
        
        # Send handshake with capabilities
        await self._send_message(websocket, {
            "type": "voice.handshake",
            "session_id": session_id,
            "timestamp": int(time.time() * 1000),
            "capabilities": {
                "asr": {
                    "model": self.asr_config.model_size,
                    "sample_rate": self.asr_config.sample_rate,
                    "chunk_ms": self.asr_config.chunk_ms,
                    "supports_partial": True,
                    "supports_final": True
                },
                "llm": {
                    "model": self.llm_config.model_name,
                    "max_tokens": self.llm_config.max_tokens,
                    "supports_streaming": True,
                    "available": True
                },
                "tts": {"available": False}  # Future
            }
        })
        
        try:
            # Handle client messages
            async for message in websocket:
                await self._process_client_message(session, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 Voice session closed: {session_id}")
        except Exception as e:
            logger.error(f"❌ Voice session error {session_id}: {e}")
        finally:
            # Cleanup session
            await self._cleanup_session(session_id)
    
    async def _process_client_message(self, session: VoiceSession, message) -> None:
        """Process message from voice client"""
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
                logger.warning(f"Invalid JSON from {session.session_id}")
    
    async def _handle_audio_frame(self, session: VoiceSession, audio_data: bytes) -> None:
        """Handle binary audio frame from client"""
        try:
            if not session.mic_enabled:
                return  # Ignore audio when mic is disabled
                
            # Convert binary audio (Int16) to Float32
            if len(audio_data) % 2 != 0:
                logger.warning(f"Invalid audio frame size: {len(audio_data)} bytes")
                return
                
            # Unpack Int16 samples and normalize to [-1, 1]
            int16_data = struct.unpack(f"<{len(audio_data)//2}h", audio_data)
            samples = np.array(int16_data, dtype=np.float32) / 32768.0
            
            # Validate frame size (expect ~20ms frames = 320 samples @ 16kHz)
            expected_samples = int(0.02 * self.asr_config.sample_rate)
            if len(samples) != expected_samples:
                logger.debug(f"Frame size: {len(samples)} (expected {expected_samples})")
            
            # Send to ASR
            session.asr.add_audio_frame(session.session_id, samples)
            session.frames_received += 1
            self.stats["total_audio_frames"] += 1
            
            # Periodic logging
            if session.frames_received % 200 == 0:  # Every 4 seconds
                logger.debug(f"📊 {session.session_id}: {session.frames_received} frames, "
                           f"{session.partial_transcriptions}P/{session.final_transcriptions}F")
            
        except Exception as e:
            logger.error(f"❌ Audio frame error: {e}")
    
    async def _handle_control_message(self, session: VoiceSession, data: Dict[str, Any]) -> None:
        """Handle JSON control message from client"""
        msg_type = data.get("type")
        
        if msg_type == "voice.mic":
            # Microphone control
            enabled = data.get("enabled", False)
            session.mic_enabled = enabled
            logger.info(f"🎤 {session.session_id}: Mic {'ON' if enabled else 'OFF'}")
            
            if not enabled:
                # Clear ASR buffer when mic disabled
                session.asr.audio_buffer.clear()
                
            # Acknowledge
            await self._send_message(session.websocket, {
                "type": "voice.mic.ack",
                "enabled": enabled,
                "timestamp": int(time.time() * 1000)
            })
            
        elif msg_type == "voice.barge_in":
            # Barge-in / interrupt
            logger.info(f"🛑 Barge-in from {session.session_id}")
            session.asr.audio_buffer.clear()
            session.is_speaking = False
            
            await self._send_message(session.websocket, {
                "type": "voice.barge_in.ack",
                "timestamp": int(time.time() * 1000)
            })
            
        elif msg_type == "voice.stats":
            # Request statistics
            stats = await self._get_session_stats(session.session_id)
            await self._send_message(session.websocket, {
                "type": "voice.stats",
                "stats": stats,
                "timestamp": int(time.time() * 1000)
            })
            
        elif msg_type == "ping":
            # Ping response
            await self._send_message(session.websocket, {
                "type": "pong",
                "timestamp": int(time.time() * 1000)
            })
            
        else:
            logger.debug(f"Unknown control message: {msg_type}")
    
    async def _handle_asr_partial(self, session_id: str, result: ASRResult) -> None:
        """Handle partial transcription from ASR"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        session.partial_transcriptions += 1
        self.stats["total_partial_transcriptions"] += 1
        
        # Update average ASR latency
        self._update_average_latency(result.processing_ms)
        
        # Send to client
        await self._send_message(session.websocket, {
            "type": "voice.transcript.partial",
            "text": result.text,
            "confidence": result.confidence,
            "timestamp": int(result.timestamp_end * 1000),
            "processing_ms": result.processing_ms,
            "session_id": session_id
        })
        
        logger.info(f"📝 PARTIAL {session_id}: '{result.text}' "
                   f"(conf={result.confidence:.3f}, {result.processing_ms:.1f}ms)")
    
    async def _handle_asr_final(self, session_id: str, result: ASRResult) -> None:
        """Handle final transcription from ASR"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        session.final_transcriptions += 1
        self.stats["total_final_transcriptions"] += 1
        
        # Update average ASR latency
        self._update_average_latency(result.processing_ms)
        
        # Send to client
        await self._send_message(session.websocket, {
            "type": "voice.transcript.final",
            "text": result.text,
            "confidence": result.confidence,
            "timestamp": int(result.timestamp_end * 1000),
            "processing_ms": result.processing_ms,
            "session_id": session_id
        })
        
        logger.info(f"🎯 FINAL {session_id}: '{result.text}' "
                   f"(conf={result.confidence:.3f}, {result.processing_ms:.1f}ms)")
        
        # Send to LLM pipeline for response generation
        if result.text.strip():  # Only process non-empty transcriptions
            await self._send_to_llm_pipeline(session_id, result.text)
    
    def _update_average_latency(self, latency_ms: float) -> None:
        """Update running average of ASR latency"""
        total_transcriptions = (self.stats["total_partial_transcriptions"] + 
                               self.stats["total_final_transcriptions"])
        
        current_avg = self.stats["average_asr_latency"]
        self.stats["average_asr_latency"] = (current_avg * (total_transcriptions - 1) + latency_ms) / total_transcriptions
    
    async def _send_to_llm_pipeline(self, session_id: str, user_text: str) -> None:
        """Send user text to LLM for response generation"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        if session.is_processing_llm:
            logger.warning(f"⚠️ {session_id}: LLM already processing, skipping new request")
            return
            
        session.is_processing_llm = True
        session.llm_requests += 1
        
        logger.info(f"🧠 Sending to LLM {session_id}: '{user_text}'")
        
        try:
            # Generate streaming response
            async for llm_result in session.llm.generate_response(user_text, session_id):
                # LLM tokens are handled by callbacks (_handle_llm_token, _handle_llm_complete)
                if llm_result.is_final:
                    break
                    
        except Exception as e:
            logger.error(f"❌ LLM generation error for {session_id}: {e}")
            session.is_processing_llm = False
            
            # Send error message to client
            await self._send_message(session.websocket, {
                "type": "voice.llm.error",
                "error": str(e),
                "session_id": session_id,
                "timestamp": int(time.time() * 1000)
            })
    
    async def _handle_llm_token(self, session_id: str, result: LLMResult) -> None:
        """Handle streaming token from LLM"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        # Send token to client
        await self._send_message(session.websocket, {
            "type": "voice.llm.token",
            "token": result.token,
            "full_response": result.full_response,
            "ttft_ms": result.time_to_first_token_ms,
            "tokens_per_sec": result.generation_speed_tokens_per_sec,
            "session_id": session_id,
            "timestamp": int(time.time() * 1000)
        })
        
        # Log first token for performance tracking
        if result.total_tokens == 1:
            logger.info(f"🎯 First LLM token {session_id}: '{result.token}' "
                       f"(TTFT={result.time_to_first_token_ms:.1f}ms)")
    
    async def _handle_llm_complete(self, session_id: str, result: LLMResult) -> None:
        """Handle complete LLM response"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        session.is_processing_llm = False
        session.llm_responses += 1
        
        # Send complete response to client
        await self._send_message(session.websocket, {
            "type": "voice.llm.complete",
            "full_response": result.full_response,
            "total_tokens": result.total_tokens,
            "ttft_ms": result.time_to_first_token_ms,
            "tokens_per_sec": result.generation_speed_tokens_per_sec,
            "session_id": session_id,
            "timestamp": int(time.time() * 1000)
        })
        
        logger.info(f"✅ LLM complete {session_id}: '{result.full_response}' "
                   f"({result.total_tokens} tokens, TTFT={result.time_to_first_token_ms:.1f}ms, "
                   f"{result.generation_speed_tokens_per_sec:.1f} tokens/sec)")
        
        # Send to TTS pipeline for voice response
        if result.full_response.strip():
            await self._send_to_tts_pipeline(session_id, result.full_response)

    async def _send_to_tts_pipeline(self, session_id: str, text: str) -> None:
        """Send text to TTS for speech generation"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        try:
            session.is_processing_tts = True
            logger.info(f"🔊 Starting TTS generation for {session_id}: '{text[:50]}...'")
            
            # Generate streaming TTS
            async for tts_result in session.tts.generate_speech(text, session_id):
                await self._handle_tts_chunk(session_id, tts_result)
                
        except Exception as e:
            logger.error(f"❌ TTS pipeline error {session_id}: {e}")
            session.is_processing_tts = False
    
    async def _handle_tts_chunk(self, session_id: str, result: TTSResult) -> None:
        """Handle streaming TTS audio chunk"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        # Convert numpy array to bytes for WebSocket transmission
        try:
            # Convert float32 audio to int16 for transmission
            audio_int16 = (result.audio_chunk * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            
            # Send binary audio chunk to client
            await session.websocket.send(audio_bytes)
            
            # Send metadata as JSON
            await self._send_message(session.websocket, {
                "type": "voice.tts.chunk",
                "chunk_index": result.chunk_index,
                "total_chunks": result.total_chunks,
                "is_final": result.is_final,
                "generation_ms": result.generation_ms,
                "text_processed": result.text_processed,
                "session_id": session_id,
                "timestamp": int(time.time() * 1000)
            })
            
            logger.debug(f"🎵 TTS chunk {session_id}: {result.chunk_index+1}/{result.total_chunks} "
                        f"({len(result.audio_chunk)} samples, {result.generation_ms:.1f}ms)")
                        
            # Handle final chunk
            if result.is_final:
                await self._handle_tts_complete(session_id, result)
                
        except Exception as e:
            logger.error(f"❌ TTS chunk error {session_id}: {e}")
    
    async def _handle_tts_complete(self, session_id: str, result: TTSResult) -> None:
        """Handle complete TTS response"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        session.is_processing_tts = False
        session.tts_responses += 1
        
        # Send completion message
        await self._send_message(session.websocket, {
            "type": "voice.tts.complete",
            "total_chunks": result.total_chunks,
            "time_to_first_chunk_ms": result.time_to_first_chunk_ms,
            "total_generation_time_ms": result.total_generation_time_ms,
            "session_id": session_id,
            "timestamp": int(time.time() * 1000)
        })
        
        logger.info(f"✅ TTS complete {session_id}: {result.total_chunks} chunks "
                   f"(TTFC={result.time_to_first_chunk_ms:.1f}ms, "
                   f"Total={result.total_generation_time_ms:.1f}ms)")

    async def _send_message(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Send JSON message to WebSocket client"""
        try:
            message = json.dumps(data)
            await websocket.send(message)
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
    
    async def _cleanup_session(self, session_id: str) -> None:
        """Clean up voice session resources"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        # Wait for LLM processing to complete before cleanup
        if session.is_processing_llm:
            logger.info(f"⏳ Waiting for LLM processing to complete for {session_id}")
            # Wait up to 10 seconds for LLM to complete
            wait_time = 0
            while session.is_processing_llm and wait_time < 10.0:
                await asyncio.sleep(0.1)
                wait_time += 0.1
            
            if session.is_processing_llm:
                logger.warning(f"⚠️ LLM processing timeout for {session_id}")
        
        # Wait for TTS processing to complete before cleanup
        if session.is_processing_tts:
            logger.info(f"⏳ Waiting for TTS processing to complete for {session_id}")
            # Wait up to 10 seconds for TTS to complete
            wait_time = 0
            while session.is_processing_tts and wait_time < 10.0:
                await asyncio.sleep(0.1)
                wait_time += 0.1
            
            if session.is_processing_tts:
                logger.warning(f"⚠️ TTS processing timeout for {session_id}")
            
        # Stop ASR processing
        try:
            session.asr.stop_processing()
        except Exception as e:
            logger.error(f"❌ Error stopping ASR: {e}")
        
        # Remove from sessions
        del self.sessions[session_id]
        self.stats["active_sessions"] -= 1
        
        # Log session summary
        duration = time.time() - session.connected_at
        logger.info(f"🧹 Voice session cleanup {session_id}: "
                   f"{duration:.1f}s, {session.frames_received} frames, "
                   f"{session.partial_transcriptions}P/{session.final_transcriptions}F, "
                   f"LLM {session.llm_requests}→{session.llm_responses}, "
                   f"TTS {session.tts_requests}→{session.tts_responses}")
    
    async def _get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a specific session"""
        session = self.sessions.get(session_id)
        if not session:
            return {}
        
        asr_stats = session.asr.get_stats()
        llm_stats = session.llm.get_stats()
        tts_stats = session.tts.get_stats()
        current_time = time.time()
        
        return {
            "session_id": session_id,
            "duration_s": current_time - session.connected_at,
            "frames_received": session.frames_received,
            "partial_transcriptions": session.partial_transcriptions,
            "final_transcriptions": session.final_transcriptions,
            "llm_requests": session.llm_requests,
            "llm_responses": session.llm_responses,
            "tts_requests": session.tts_requests,
            "tts_responses": session.tts_responses,
            "mic_enabled": session.mic_enabled,
            "is_speaking": session.is_speaking,
            "is_processing_llm": session.is_processing_llm,
            "is_processing_tts": session.is_processing_tts,
            "asr": asr_stats,
            "llm": llm_stats,
            "tts": tts_stats
        }
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get comprehensive server statistics"""
        current_time = time.time()
        uptime = current_time - self.stats["start_time"]
        
        # Session summaries
        session_stats = {}
        for session_id, session in self.sessions.items():
            session_stats[session_id] = {
                "duration_s": current_time - session.connected_at,
                "frames_received": session.frames_received,
                "partial_transcriptions": session.partial_transcriptions,
                "final_transcriptions": session.final_transcriptions,
                "mic_enabled": session.mic_enabled
            }
        
        return {
            "uptime_s": uptime,
            "active_sessions": len(self.sessions),
            "session_details": session_stats,
            **self.stats
        }
    
    async def shutdown(self) -> None:
        """Shutdown voice pipeline server gracefully"""
        logger.info("🛑 Shutting down Voice Pipeline Server...")
        
        # Cleanup all sessions
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self._cleanup_session(session_id)
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("✅ Voice Pipeline Server shutdown complete")

# Test server function
async def run_voice_pipeline_server():
    """Run voice pipeline server for testing"""
    server = VoicePipelineServer(host="localhost", port=8765)
    
    try:
        await server.start_server()
        
        # Print server info
        logger.info("🎙️ Voice Pipeline Server running...")
        logger.info("   Connect voice clients to ws://localhost:8001")
        logger.info("   Send binary audio frames (Int16, 16kHz, 20ms frames)")
        logger.info("   Receive real-time transcriptions!")
        
        # Keep server running
        while True:
            await asyncio.sleep(10)
            
            # Print periodic stats
            stats = server.get_server_stats()
            logger.info(f"📊 Server stats: {stats['active_sessions']} sessions, "
                       f"{stats['total_audio_frames']} frames, "
                       f"{stats['average_asr_latency']:.1f}ms avg ASR latency")
            
    except KeyboardInterrupt:
        logger.info("🛑 Server interrupted")
    finally:
        await server.shutdown()

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run server
    asyncio.run(run_voice_pipeline_server())