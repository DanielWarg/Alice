#!/usr/bin/env python3
"""
🎙️ WebRTC Manager for Alice Voice Gateway
Handles aiortc peer connections, audio tracks, and streaming processing
Enhanced with streaming ASR integration (GPT-5 Day 1)
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Optional, Set, Callable
import wave
import io

from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaPlayer, MediaRecorder
import numpy as np

# Import streaming ASR components
from asr_stream import ASRStreamManager, ASRConfig, ASRProvider, ASRResult, get_asr_manager
from asr_events import get_asr_broadcaster

# Import streaming LLM components
from llm_stream import LLMStreamManager, LLMToken, LLMResponse, get_llm_manager
from llm_events import get_llm_broadcaster

# Import streaming TTS components (Day 3)
from tts_stream import TTSStreamManager, TTSAudioChunk, TTSResponse, get_tts_manager
from tts_events import get_tts_broadcaster

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Process incoming audio from microphone track with streaming ASR"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.sample_rate = 16000  # 16kHz for ASR
        self.channels = 1  # Mono
        self.chunk_size = 320  # 20ms at 16kHz
        
        # Streaming ASR integration
        self.asr_session = None
        self.asr_manager = get_asr_manager()
        self.asr_broadcaster = get_asr_broadcaster()
        
        # Streaming LLM integration (Day 2)
        self.llm_session = None
        self.llm_manager = get_llm_manager()
        self.llm_broadcaster = get_llm_broadcaster()
        
        # Streaming TTS integration (Day 3)
        self.tts_session = None
        self.tts_manager = get_tts_manager()
        self.tts_broadcaster = get_tts_broadcaster()
        self.tts_buffer = []  # Buffer for token accumulation
        
        # Performance tracking
        self.first_partial_time = None
        self.audio_chunks_sent = 0
        
    async def process_audio_frame(self, frame) -> Optional[bytes]:
        """Convert audio frame to PCM16 for ASR processing"""
        try:
            # Convert frame to numpy array with proper error handling
            try:
                audio_data = frame.to_ndarray()
            except Exception as e:
                logger.debug(f"Frame conversion failed: {e}")
                return None
                
            # Validate array
            if audio_data is None or audio_data.size == 0:
                return None
                
            # Handle different array layouts systematically
            original_shape = audio_data.shape
            
            if len(audio_data.shape) == 3:
                # Multi-dimensional array - flatten to 2D first
                audio_data = audio_data.reshape(-1, audio_data.shape[-1])
                
            if len(audio_data.shape) == 2:
                # Stereo or multi-channel audio
                if audio_data.shape[1] == 1:
                    # Single channel in (samples, 1) format
                    audio_data = audio_data.flatten()
                elif audio_data.shape[0] == 1:
                    # Single channel in (1, samples) format  
                    audio_data = audio_data.flatten()
                else:
                    # True multi-channel - convert to mono by averaging
                    audio_data = np.mean(audio_data, axis=1 if audio_data.shape[0] > audio_data.shape[1] else 0)
                    
            elif len(audio_data.shape) == 1:
                # Already mono - perfect
                pass
            else:
                logger.warning(f"⚠️ Unexpected audio shape: {original_shape} → skipping")
                return None
            
            # Ensure we have a proper 1D array
            audio_data = audio_data.flatten().astype(np.float32)
            
            if len(audio_data) == 0:
                return None
                
            # Resample if needed
            if hasattr(frame, 'sample_rate') and frame.sample_rate != self.sample_rate:
                ratio = self.sample_rate / frame.sample_rate
                new_length = max(1, int(len(audio_data) * ratio))
                if new_length > 0:
                    indices = np.linspace(0, len(audio_data) - 1, new_length)
                    audio_data = np.interp(indices, np.arange(len(audio_data)), audio_data)
            
            # Normalize and convert to int16 PCM
            if len(audio_data) > 0:
                # Safe normalization
                max_val = max(abs(audio_data.min()), abs(audio_data.max()))
                if max_val > 0:
                    audio_data = audio_data / max_val * 0.95  # Leave headroom
                
                # Convert to 16-bit PCM
                pcm_data = (audio_data * 32767).astype(np.int16)
                pcm_bytes = pcm_data.tobytes()
                
                # Stream to ASR if session exists
                if self.asr_session:
                    asyncio.create_task(self._stream_to_asr(pcm_bytes))
                
                return pcm_bytes
            
            return None
            
        except Exception as e:
            # Only log every 50th error to avoid spam
            if not hasattr(self, '_error_count'):
                self._error_count = 0
            self._error_count += 1
            
            if self._error_count % 50 == 1:
                logger.warning(f"⚠️ Audio processing error (#{self._error_count}): {e}")
            return None
    
    async def _stream_to_asr(self, pcm_bytes: bytes):
        """Stream audio to ASR service"""
        try:
            if self.asr_session:
                await self.asr_session.send_audio(pcm_bytes)
                self.audio_chunks_sent += 1
                
                # Log streaming stats occasionally
                if self.audio_chunks_sent % 50 == 0:  # Every second at 50fps
                    logger.debug(f"🎙️ Streamed {self.audio_chunks_sent} chunks to ASR (session: {self.session_id})")
                    
        except Exception as e:
            logger.error(f"❌ ASR streaming error: {e}")
    
    async def start_asr_streaming(self):
        """Initialize ASR streaming session"""
        try:
            self.asr_session = await self.asr_manager.create_session(self.session_id)
            
            # Set up ASR event handlers
            self.asr_session.on_partial = self._on_asr_partial
            self.asr_session.on_final = self._on_asr_final
            self.asr_session.on_error = self._on_asr_error
            
            logger.info(f"✅ ASR streaming started for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start ASR streaming: {e}")
            self.asr_session = None
    
    async def start_llm_streaming(self):
        """Initialize LLM streaming session (Day 2)"""
        try:
            self.llm_session = await self.llm_manager.create_session(self.session_id)
            
            # Set up LLM event handlers
            self.llm_session.on_token = self._on_llm_token
            self.llm_session.on_response_start = self._on_llm_response_start
            self.llm_session.on_response_complete = self._on_llm_response_complete
            self.llm_session.on_error = self._on_llm_error
            
            logger.info(f"✅ LLM streaming started for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start LLM streaming: {e}")
            self.llm_session = None
    
    async def stop_asr_streaming(self):
        """Stop ASR streaming session"""
        if self.asr_session:
            await self.asr_manager.remove_session(self.session_id)
            self.asr_session = None
            logger.info(f"🔌 ASR streaming stopped for session {self.session_id}")
    
    async def stop_llm_streaming(self):
        """Stop LLM streaming session"""
        if self.llm_session:
            await self.llm_manager.remove_session(self.session_id)
            self.llm_session = None
            logger.info(f"🔌 LLM streaming stopped for session {self.session_id}")
    
    async def start_tts_streaming(self):
        """Initialize TTS streaming session (Day 3)"""
        try:
            self.tts_session = await self.tts_manager.create_session(self.session_id)
            
            # Set up TTS event handlers
            self.tts_session.on_audio_chunk = self._on_tts_audio_chunk
            self.tts_session.on_synthesis_start = self._on_tts_synthesis_start
            self.tts_session.on_synthesis_complete = self._on_tts_synthesis_complete
            self.tts_session.on_error = self._on_tts_error
            
            logger.info(f"✅ TTS streaming started for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start TTS streaming: {e}")
            self.tts_session = None
    
    async def stop_tts_streaming(self):
        """Stop TTS streaming session"""
        if self.tts_session:
            await self.tts_manager.remove_session(self.session_id)
            self.tts_session = None
            logger.info(f"🔌 TTS streaming stopped for session {self.session_id}")
    
    def _on_asr_partial(self, result: ASRResult):
        """Handle ASR partial result"""
        # Track first partial timing (GPT-5 <300ms target)
        if self.first_partial_time is None:
            self.first_partial_time = time.time() * 1000
            
        logger.info(f"⚡ ASR Partial ({result.provider.value}): {result.text} (confidence: {result.confidence:.2f})")
        
        # Broadcast partial result to WebSocket clients
        asyncio.create_task(self.asr_broadcaster.broadcast_partial(
            self.session_id, result.text, result.confidence, result.provider.value
        ))
        
        # TODO Day 2: Route to LLM immediately
        # asyncio.create_task(self._route_to_llm(result))
    
    def _on_asr_final(self, result: ASRResult):
        """Handle ASR final result"""
        logger.info(f"🎯 ASR Final ({result.provider.value}): {result.text} (confidence: {result.confidence:.2f})")
        
        # Log performance metrics
        if self.first_partial_time:
            partial_latency = self.first_partial_time
            logger.info(f"📊 First partial latency: {partial_latency:.1f}ms (target: <300ms)")
        
        # Broadcast final result to WebSocket clients
        asyncio.create_task(self.asr_broadcaster.broadcast_final(
            self.session_id, result.text, result.confidence, result.provider.value
        ))
        
        # Day 2: Route final result to LLM
        asyncio.create_task(self._route_to_llm(result.text))
    
    def _on_asr_error(self, error: Exception):
        """Handle ASR error"""
        logger.error(f"❌ ASR error for session {self.session_id}: {error}")
        
        # Broadcast error to WebSocket clients
        asyncio.create_task(self.asr_broadcaster.broadcast_error(
            self.session_id, str(error)
        ))
        
        # TODO: Implement fallback ASR provider
    
    async def _route_to_llm(self, user_input: str):
        """Route ASR result to LLM for streaming response (Day 2)"""
        try:
            if not self.llm_session:
                await self.start_llm_streaming()
            
            if self.llm_session:
                logger.info(f"🧠 Routing to LLM: {user_input}")
                
                # Generate streaming LLM response
                async for token in self.llm_session.generate_streaming_response(user_input):
                    # LLM token events are handled by callbacks
                    pass
                    
        except Exception as e:
            logger.error(f"❌ LLM routing error: {e}")
    
    def _on_llm_response_start(self, user_input: str):
        """Handle LLM response start"""
        logger.info(f"🚀 LLM response starting for: {user_input}")
        
        # Broadcast response start event
        asyncio.create_task(self.llm_broadcaster.broadcast_response_start(
            self.session_id, user_input
        ))
        
        # TODO Day 3: Signal TTS preparation
    
    def _on_llm_token(self, token: LLMToken):
        """Handle LLM token streaming"""
        if token.is_final:
            logger.info(f"🎯 LLM response complete")
        else:
            logger.debug(f"🧠 LLM token: {token.text}")
        
        # Broadcast token via WebSocket
        asyncio.create_task(self.llm_broadcaster.broadcast_token(
            self.session_id, token
        ))
        
        # Day 3: Stream tokens to TTS for real-time synthesis
        self.tts_buffer.append(token.text)
        
        # Check if we have enough tokens to start TTS (word-level synthesis)
        if len(self.tts_buffer) >= 5 or token.is_final:  # 5 tokens or final
            text_to_synthesize = "".join(self.tts_buffer)
            if text_to_synthesize.strip():
                asyncio.create_task(self._synthesize_text_chunk(text_to_synthesize))
                self.tts_buffer = []  # Clear buffer
    
    def _on_llm_response_complete(self, response: LLMResponse):
        """Handle LLM response completion"""
        logger.info(f"✅ LLM complete: {response.text[:100]}{'...' if len(response.text) > 100 else ''}")
        logger.info(f"📊 Performance - First token: {response.first_token_latency_ms:.0f}ms, Rate: {response.tokens_per_second:.1f} tok/s")
        
        # Broadcast response completion
        asyncio.create_task(self.llm_broadcaster.broadcast_response_complete(
            self.session_id, response
        ))
        
        # Day 3: Final TTS synthesis cleanup
        if self.tts_buffer:  # Synthesize any remaining tokens
            final_text = "".join(self.tts_buffer)
            if final_text.strip():
                asyncio.create_task(self._synthesize_text_chunk(final_text))
                self.tts_buffer = []
    
    def _on_llm_error(self, error: Exception):
        """Handle LLM error"""
        logger.error(f"❌ LLM error for session {self.session_id}: {error}")
        
        # Broadcast error event
        asyncio.create_task(self.llm_broadcaster.broadcast_error(
            self.session_id, str(error)
        ))
        
        # TODO: Implement LLM fallback or error response
    
    async def _synthesize_text_chunk(self, text: str):
        """Synthesize text chunk to audio using TTS (Day 3)"""
        try:
            if not self.tts_session:
                await self.start_tts_streaming()
            
            if self.tts_session:
                logger.info(f"🗣️ Synthesizing text: {text[:50]}{'...' if len(text) > 50 else ''}")
                
                # Generate streaming TTS audio
                async for audio_chunk in self.tts_session.synthesize_streaming(text):
                    # TTS audio events are handled by callbacks
                    pass
                    
        except Exception as e:
            logger.error(f"❌ TTS synthesis error: {e}")
    
    def _on_tts_synthesis_start(self, text: str):
        """Handle TTS synthesis start"""
        logger.info(f"🚀 TTS synthesis starting for: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        # Broadcast synthesis start event
        asyncio.create_task(self.tts_broadcaster.broadcast_synthesis_start(
            self.session_id, text
        ))
    
    def _on_tts_audio_chunk(self, chunk: TTSAudioChunk):
        """Handle TTS audio chunk streaming"""
        if chunk.is_final:
            logger.info(f"🎯 TTS synthesis complete (chunk {chunk.chunk_index})")
        else:
            logger.debug(f"🔊 TTS audio chunk: {len(chunk.audio_data)} bytes")
        
        # Broadcast audio chunk via WebSocket
        asyncio.create_task(self.tts_broadcaster.broadcast_audio_chunk(
            self.session_id, chunk
        ))
        
        # TODO Day 4: Stream audio back to WebRTC for duplex playback
    
    def _on_tts_synthesis_complete(self, response: TTSResponse):
        """Handle TTS synthesis completion"""
        logger.info(f"✅ TTS complete: {response.text[:50]}{'...' if len(response.text) > 50 else ''}")
        logger.info(f"📊 Performance - First audio: {response.first_audio_latency_ms:.0f}ms, Synthesis: {response.synthesis_time_ms:.0f}ms")
        
        # Broadcast synthesis completion
        asyncio.create_task(self.tts_broadcaster.broadcast_synthesis_complete(
            self.session_id, response
        ))
    
    def _on_tts_error(self, error: Exception):
        """Handle TTS error"""
        logger.error(f"❌ TTS error for session {self.session_id}: {error}")
        
        # Broadcast error event
        asyncio.create_task(self.tts_broadcaster.broadcast_error(
            self.session_id, str(error)
        ))
        
        # TODO: Implement TTS fallback provider
    
    def _resample_audio(self, audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
        """Basic resampling (production should use proper resampling)"""
        if source_rate == target_rate:
            return audio
        
        # Simple decimation/interpolation (replace with scipy.signal.resample in production)
        ratio = target_rate / source_rate
        new_length = int(len(audio) * ratio)
        return np.interp(np.linspace(0, len(audio), new_length), np.arange(len(audio)), audio)

class TestToneTrack(MediaStreamTrack):
    """Generate test tone for remote audio verification"""
    
    kind = "audio"
    
    def __init__(self, frequency: int = 440, sample_rate: int = 48000):
        super().__init__()
        self.frequency = frequency  # Hz
        self.sample_rate = sample_rate
        self.samples_per_frame = 960  # 20ms at 48kHz
        self.sample_count = 0
        self._is_stopped = False  # Critical: Stop tone when needed
        
    async def recv(self):
        """Generate audio frame with test tone"""
        import av
        from fractions import Fraction
        
        try:
            # CRITICAL: Return silence if stopped
            if self._is_stopped:
                return await self._generate_silence()
            
            # Generate sine wave samples with fade-in/out for smoother audio
            t = np.arange(self.sample_count, self.sample_count + self.samples_per_frame) / self.sample_rate
            samples = np.sin(2 * np.pi * self.frequency * t)
            
            # Apply envelope to reduce clicks
            envelope = np.ones_like(samples)
            fade_samples = min(48, len(samples) // 4)  # ~1ms fade at 48kHz
            envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
            envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
            samples *= envelope
            
            # Convert to int16 with proper scaling
            samples = (samples * 16383).astype(np.int16)
            
            # Create audio frame
            frame = av.AudioFrame.from_ndarray(
                samples.reshape(1, -1), format='s16', layout='mono'
            )
            frame.sample_rate = self.sample_rate
            frame.pts = self.sample_count
            frame.time_base = Fraction(1, self.sample_rate)
            
            self.sample_count += self.samples_per_frame
            
            # Maintain real-time timing
            await asyncio.sleep(0.02)  # 20ms
            
            return frame
            
        except Exception as e:
            logger.error(f"❌ Test tone generation failed: {e}")
            return await self._generate_silence()
    
    async def _generate_silence(self):
        """Generate silent frame to avoid audio leaks"""
        import av
        from fractions import Fraction
        
        silence = np.zeros(self.samples_per_frame, dtype=np.int16)
        frame = av.AudioFrame.from_ndarray(
            silence.reshape(1, -1), format='s16', layout='mono'
        )
        frame.sample_rate = self.sample_rate
        frame.pts = self.sample_count
        frame.time_base = Fraction(1, self.sample_rate)
        
        self.sample_count += self.samples_per_frame
        await asyncio.sleep(0.02)
        return frame
    
    def stop(self):
        """Stop the test tone immediately"""
        self._is_stopped = True
        logger.info(f"🔇 Test tone stopped (was {self.frequency}Hz)")

class WebRTCSession:
    """Individual WebRTC session handling"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.pc = RTCPeerConnection()
        self.audio_processor = AudioProcessor(session_id)
        self.test_tone_track = TestToneTrack()
        self.created_at = datetime.utcnow()
        self.is_active = True
        
        # Setup event handlers
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Setup WebRTC peer connection event handlers"""
        
        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"🔗 Session {self.session_id} connection state: {self.pc.connectionState}")
            if self.pc.connectionState == "closed":
                self.is_active = False
                
        @self.pc.on("track")
        async def on_track(track):
            logger.info(f"🎵 Received {track.kind} track for session {self.session_id}")
            
            if track.kind == "audio":
                # Start processing incoming audio
                asyncio.create_task(self._process_incoming_audio(track))
        
        @self.pc.on("datachannel")
        async def on_datachannel(channel):
            logger.info(f"📡 Data channel established: {channel.label}")
    
    async def _process_incoming_audio(self, track):
        """Process incoming audio frames from microphone with streaming ASR"""
        logger.info(f"🎙️ Starting audio processing for session {self.session_id} (Day 1 - Streaming ASR)")
        
        # Start ASR streaming
        await self.audio_processor.start_asr_streaming()
        
        frame_count = 0
        try:
            while self.is_active:
                frame = await track.recv()
                frame_count += 1
                
                # Process every frame now (streaming requires real-time)
                pcm_data = await self.audio_processor.process_audio_frame(frame)
                
                if pcm_data:
                    # Log successful processing occasionally
                    if frame_count % 50 == 0:  # Every second
                        logger.debug(f"🎵 Processed frame {frame_count}: {len(pcm_data)} bytes PCM → ASR stream")
                    
        except Exception as e:
            logger.info(f"ℹ️ Audio processing ended for session {self.session_id}: {e}")
        finally:
            # Stop ASR streaming when audio processing ends
            await self.audio_processor.stop_asr_streaming()
    
    async def handle_offer(self, offer_sdp: str) -> str:
        """Process WebRTC offer and return answer SDP"""
        try:
            # Set remote description (offer)
            offer = RTCSessionDescription(sdp=offer_sdp, type="offer")
            await self.pc.setRemoteDescription(offer)
            
            # Add test tone track for audio verification
            self.pc.addTrack(self.test_tone_track)
            
            # Create answer
            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)
            
            logger.info(f"✅ WebRTC answer created for session {self.session_id}")
            return self.pc.localDescription.sdp
            
        except Exception as e:
            logger.error(f"❌ WebRTC offer processing failed: {e}")
            raise
    
    async def stop_tts(self):
        """Stop TTS playback for barge-in"""
        # TODO: Implement TTS stop mechanism
        logger.info(f"🛑 TTS stopped for session {self.session_id}")
    
    async def close(self):
        """Close WebRTC session"""
        self.is_active = False
        
        # CRITICAL: Stop test tone to prevent audio leaks
        if hasattr(self, 'test_tone_track') and self.test_tone_track:
            self.test_tone_track.stop()
        
        await self.pc.close()
        logger.info(f"🔄 Session {self.session_id} closed")

class WebRTCManager:
    """Manages multiple WebRTC sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, WebRTCSession] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize WebRTC manager"""
        # Start cleanup task for inactive sessions
        self.cleanup_task = asyncio.create_task(self._cleanup_inactive_sessions())
        logger.info("✅ WebRTC manager initialized")
    
    async def handle_offer(self, session_id: str, offer_sdp: str) -> str:
        """Handle WebRTC offer for a session"""
        try:
            # Create new session if doesn't exist
            if session_id in self.sessions:
                await self.sessions[session_id].close()
            
            session = WebRTCSession(session_id)
            self.sessions[session_id] = session
            
            # Process offer and get answer
            answer_sdp = await session.handle_offer(offer_sdp)
            
            logger.info(f"✅ WebRTC session {session_id} established")
            return answer_sdp
            
        except Exception as e:
            logger.error(f"❌ WebRTC offer handling failed: {e}")
            # Clean up failed session
            if session_id in self.sessions:
                await self.sessions[session_id].close()
                del self.sessions[session_id]
            raise
    
    async def stop_tts(self, session_id: str):
        """Stop TTS for a specific session"""
        if session_id in self.sessions:
            await self.sessions[session_id].stop_tts()
        else:
            logger.warning(f"⚠️ Session {session_id} not found for TTS stop")
    
    async def get_active_session_count(self) -> int:
        """Get count of active sessions"""
        active_count = sum(1 for session in self.sessions.values() if session.is_active)
        return active_count
    
    def get_status(self) -> Dict:
        """Get manager status"""
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": sum(1 for s in self.sessions.values() if s.is_active),
            "status": "running"
        }
    
    async def _cleanup_inactive_sessions(self):
        """Periodically clean up inactive sessions"""
        while True:
            try:
                to_remove = []
                
                for session_id, session in self.sessions.items():
                    if not session.is_active or session.pc.connectionState == "closed":
                        to_remove.append(session_id)
                
                for session_id in to_remove:
                    session = self.sessions[session_id]
                    # Ensure test tone is stopped before cleanup
                    if hasattr(session, 'test_tone_track') and session.test_tone_track:
                        session.test_tone_track.stop()
                    await session.close()
                    del self.sessions[session_id]
                    logger.info(f"🧹 Cleaned up inactive session: {session_id}")
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Session cleanup error: {e}")
                await asyncio.sleep(30)
    
    async def cleanup(self):
        """Cleanup manager and all sessions"""
        # Cancel cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Close all sessions and stop test tones
        for session in self.sessions.values():
            if hasattr(session, 'test_tone_track') and session.test_tone_track:
                session.test_tone_track.stop()
            await session.close()
        
        self.sessions.clear()
        logger.info("🔄 WebRTC manager cleanup complete")