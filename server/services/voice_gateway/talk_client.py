#!/usr/bin/env python3
"""
🎙️ OpenAI Realtime Talk Client - Production WebRTC Implementation

Direct WebRTC communication with OpenAI Realtime API featuring:
- Real-time audio streaming with jitter buffering (80-120ms)
- Barge-in support with ducking
- English voice (alloy/nova)
- Complete error handling and performance monitoring
- P50/P95 latency tracking
- Safe_summary message handling

Production-ready with comprehensive logging and metrics.
"""

import asyncio
import json
import base64
import time
import logging
import os
import threading
from collections import deque
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import statistics
import wave
import io

import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
import av

# Import local metrics and utilities
from metrics import VoiceMetrics
from streaming_metrics import TalkLatencyLogger, BargeInLogger, Route

logger = logging.getLogger("alice.talk_client")

class TalkClientState(Enum):
    """Client connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SESSION_ACTIVE = "session_active"
    ERROR = "error"
    RECONNECTING = "reconnecting"

class AudioFormat(Enum):
    """Supported audio formats"""
    PCM16_24KHZ = "pcm16"
    PCM16_16KHZ = "pcm16_16k"

@dataclass
class LatencyMetrics:
    """Track latency performance metrics"""
    samples: deque = field(default_factory=lambda: deque(maxlen=1000))
    first_audio_times: deque = field(default_factory=lambda: deque(maxlen=100))
    barge_in_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def add_latency(self, latency_ms: float):
        """Add latency sample"""
        self.samples.append(latency_ms)
    
    def add_first_audio_time(self, time_ms: float):
        """Add first audio time sample"""
        self.first_audio_times.append(time_ms)
    
    def add_barge_in_time(self, time_ms: float):
        """Add barge-in response time"""
        self.barge_in_times.append(time_ms)
    
    def get_p50_p95_latency(self) -> Tuple[float, float]:
        """Get P50 and P95 latency metrics"""
        if not self.samples:
            return 0.0, 0.0
        
        sorted_samples = sorted(self.samples)
        n = len(sorted_samples)
        p50 = sorted_samples[int(n * 0.5)]
        p95 = sorted_samples[int(n * 0.95)]
        return p50, p95
    
    def get_stats(self) -> Dict[str, float]:
        """Get comprehensive latency statistics"""
        if not self.samples:
            return {"p50": 0, "p95": 0, "mean": 0, "min": 0, "max": 0}
        
        sorted_samples = sorted(self.samples)
        n = len(sorted_samples)
        
        return {
            "p50": sorted_samples[int(n * 0.5)],
            "p95": sorted_samples[int(n * 0.95)],
            "mean": statistics.mean(self.samples),
            "min": min(self.samples),
            "max": max(self.samples),
            "count": n
        }

@dataclass
class JitterBuffer:
    """Audio jitter buffer for smooth playback"""
    buffer: deque = field(default_factory=deque)
    target_size_ms: int = 100  # Target buffer size (80-120ms)
    sample_rate: int = 24000
    channels: int = 1
    bytes_per_sample: int = 2
    max_buffer_ms: int = 200  # Maximum buffer size
    min_buffer_ms: int = 50   # Minimum buffer size
    
    def add_audio(self, audio_data: bytes) -> None:
        """Add audio data to jitter buffer"""
        self.buffer.append(audio_data)
        
        # Prevent buffer overflow
        max_chunks = self._ms_to_chunks(self.max_buffer_ms)
        while len(self.buffer) > max_chunks:
            self.buffer.popleft()
    
    def get_audio(self) -> Optional[bytes]:
        """Get audio data if buffer has enough"""
        current_size_ms = self._get_buffer_size_ms()
        
        # Only return audio if we have minimum buffer
        if current_size_ms >= self.min_buffer_ms and self.buffer:
            return self.buffer.popleft()
        
        return None
    
    def _get_buffer_size_ms(self) -> float:
        """Get current buffer size in milliseconds"""
        if not self.buffer:
            return 0
        
        total_bytes = sum(len(chunk) for chunk in self.buffer)
        bytes_per_ms = (self.sample_rate * self.channels * self.bytes_per_sample) / 1000
        return total_bytes / bytes_per_ms
    
    def _ms_to_chunks(self, ms: int) -> int:
        """Convert milliseconds to number of chunks (rough estimate)"""
        # Assume ~20ms per chunk on average
        return max(1, ms // 20)
    
    def clear(self):
        """Clear the buffer"""
        self.buffer.clear()

@dataclass
class RealtimeConfig:
    """Configuration for OpenAI Realtime API"""
    api_key: str
    model: str = "gpt-4o-realtime-preview-2024-10-01"
    voice: str = "alloy"  # English voice (alloy or nova)
    language: str = "en"
    max_response_output_tokens: int = 150
    modalities: List[str] = field(default_factory=lambda: ["text", "audio"])
    instructions: str = ("You are the speaking persona 'Alice'. Language: English. "
                        "Speak concisely, 1–2 sentences. Do not call tools. "
                        "If a tool seems required, say: 'I'll check that locally.' "
                        "and wait for a 'local_result' message.")
    tools: List[Dict] = field(default_factory=list)
    tool_choice: str = "none"
    temperature: float = 0.7
    input_audio_format: AudioFormat = AudioFormat.PCM16_24KHZ
    output_audio_format: AudioFormat = AudioFormat.PCM16_24KHZ
    input_audio_transcription_enabled: bool = True
    turn_detection_type: str = "server_vad"
    vad_threshold: float = 0.5
    vad_silence_duration_ms: int = 500  # Faster response
    vad_prefix_padding_ms: int = 300

class AudioPlaybackTrack(MediaStreamTrack):
    """WebRTC audio track for AI response playback"""
    
    kind = "audio"
    
    def __init__(self, jitter_buffer: JitterBuffer):
        super().__init__()
        self.jitter_buffer = jitter_buffer
        self.sample_rate = 24000
        self.samples_per_frame = 480  # 20ms at 24kHz
        self.sample_count = 0
        self._is_playing = False
        self._volume = 1.0  # For ducking
        
    async def recv(self):
        """Generate audio frame from jitter buffer"""
        import av
        from fractions import Fraction
        
        try:
            # Get audio from jitter buffer
            audio_data = self.jitter_buffer.get_audio()
            
            if audio_data and self._is_playing:
                # Convert bytes to numpy array
                audio_samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Apply volume (for ducking)
                if self._volume != 1.0:
                    audio_samples *= self._volume
                
                # Ensure correct frame size
                if len(audio_samples) < self.samples_per_frame:
                    # Pad with zeros
                    padding = np.zeros(self.samples_per_frame - len(audio_samples))
                    audio_samples = np.concatenate([audio_samples, padding])
                elif len(audio_samples) > self.samples_per_frame:
                    # Truncate
                    audio_samples = audio_samples[:self.samples_per_frame]
                
                # Convert back to int16
                int16_samples = (audio_samples * 32767).astype(np.int16)
            else:
                # Generate silence
                int16_samples = np.zeros(self.samples_per_frame, dtype=np.int16)
            
            # Create audio frame
            frame = av.AudioFrame.from_ndarray(
                int16_samples.reshape(1, -1), format='s16', layout='mono'
            )
            frame.sample_rate = self.sample_rate
            frame.pts = self.sample_count
            frame.time_base = Fraction(1, self.sample_rate)
            
            self.sample_count += self.samples_per_frame
            
            # Maintain real-time timing
            await asyncio.sleep(0.02)  # 20ms
            
            return frame
            
        except Exception as e:
            logger.error(f"❌ Audio playback frame generation failed: {e}")
            return await self._generate_silence()
    
    async def _generate_silence(self):
        """Generate silent frame"""
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
    
    def set_playing(self, playing: bool):
        """Control playback state"""
        self._is_playing = playing
    
    def set_volume(self, volume: float):
        """Set volume for ducking (0.0 - 1.0)"""
        self._volume = max(0.0, min(1.0, volume))
    
    def duck(self, duck_level: float = 0.2):
        """Duck audio for barge-in"""
        self.set_volume(duck_level)
    
    def unduck(self):
        """Restore normal volume"""
        self.set_volume(1.0)

class OpenAIRealtimeTalkClient:
    """
    Production OpenAI Realtime API Talk Client
    
    Features:
    - Direct WebRTC communication with OpenAI Realtime API
    - Jitter buffering (80-120ms) for smooth audio playback
    - Barge-in support with audio ducking
    - English voice configuration (alloy/nova)
    - Comprehensive performance monitoring
    - Safe_summary message handling
    """
    
    def __init__(self, config: RealtimeConfig, metrics: Optional[VoiceMetrics] = None):
        self.config = config
        self.state = TalkClientState.DISCONNECTED
        self.metrics = metrics or VoiceMetrics()
        
        # WebSocket connection
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.session_id: Optional[str] = None
        
        # WebRTC components
        self.peer_connection: Optional[RTCPeerConnection] = None
        self.jitter_buffer = JitterBuffer(target_size_ms=100)
        self.playback_track: Optional[AudioPlaybackTrack] = None
        
        # Performance tracking
        self.latency_metrics = LatencyMetrics()
        self.start_time = time.time()
        self.response_start_time: Optional[float] = None
        self.first_audio_time: Optional[float] = None
        
        # Streaming metrics loggers
        self.talk_latency_logger = TalkLatencyLogger()
        self.barge_in_logger = BargeInLogger()
        self.current_turn_id: Optional[str] = None
        self.current_playback_id: Optional[str] = None
        
        # Audio state management
        self.is_speaking = False  # AI is speaking
        self.is_listening = False  # User is speaking
        self.barge_in_detected = False
        
        # Event handlers
        self.on_transcript: Optional[Callable[[str, bool], None]] = None
        self.on_audio_start: Optional[Callable[[], None]] = None
        self.on_audio_end: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_connection_change: Optional[Callable[[bool], None]] = None
        self.on_safe_summary: Optional[Callable[[str], None]] = None
        
        # Test callbacks
        self.on_text_response: Optional[Callable[[str], None]] = None
        self.on_audio_response: Optional[Callable[[bytes], None]] = None
        
        # Connection management
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3
        self._reconnect_delay = 2.0
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._message_handler_task: Optional[asyncio.Task] = None
        
        # Thread-safe audio processing
        self._audio_lock = threading.Lock()
        
    async def initialize(self) -> bool:
        """Initialize the talk client"""
        try:
            logger.info("🚀 Initializing OpenAI Realtime Talk Client")
            
            # Initialize metrics
            self.metrics.initialize()
            
            # Create WebRTC peer connection
            self.peer_connection = RTCPeerConnection()
            self._setup_peer_connection_handlers()
            
            # Create audio playback track
            self.playback_track = AudioPlaybackTrack(self.jitter_buffer)
            self.peer_connection.addTrack(self.playback_track)
            
            logger.info("✅ Talk client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize talk client: {e}")
            await self._handle_error(f"Initialization failed: {e}")
            return False
    
    def _setup_peer_connection_handlers(self):
        """Setup WebRTC peer connection event handlers"""
        
        @self.peer_connection.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"🔗 WebRTC connection state: {self.peer_connection.connectionState}")
            
            if self.peer_connection.connectionState == "connected":
                # Start OpenAI connection when WebRTC is ready
                if self.state == TalkClientState.DISCONNECTED:
                    await self.connect_to_openai()
            elif self.peer_connection.connectionState == "closed":
                await self.disconnect()
        
        @self.peer_connection.on("track")
        async def on_track(track):
            logger.info(f"🎵 Received {track.kind} track")
            
            if track.kind == "audio":
                # Process incoming microphone audio
                asyncio.create_task(self._process_microphone_audio(track))
    
    async def handle_webrtc_offer(self, offer_sdp: str) -> str:
        """Handle WebRTC offer and return answer SDP"""
        try:
            # Record WebRTC offer
            self.metrics.record_webrtc_offer()
            offer_start_time = time.time()
            
            # Set remote description
            offer = RTCSessionDescription(sdp=offer_sdp, type="offer")
            await self.peer_connection.setRemoteDescription(offer)
            
            # Create answer
            answer = await self.peer_connection.createAnswer()
            await self.peer_connection.setLocalDescription(answer)
            
            # Record processing time
            processing_time_ms = (time.time() - offer_start_time) * 1000
            self.metrics.record_offer_processing_time(processing_time_ms)
            
            logger.info(f"✅ WebRTC answer created (processing time: {processing_time_ms:.1f}ms)")
            return self.peer_connection.localDescription.sdp
            
        except Exception as e:
            logger.error(f"❌ WebRTC offer processing failed: {e}")
            await self._handle_error(f"WebRTC offer failed: {e}")
            raise
    
    async def connect_to_openai(self) -> bool:
        """Connect to OpenAI Realtime API"""
        if self.state in [TalkClientState.CONNECTED, TalkClientState.SESSION_ACTIVE]:
            return True
        
        try:
            self.state = TalkClientState.CONNECTING
            logger.info("🔌 Connecting to OpenAI Realtime API...")
            
            # WebSocket URL and headers
            url = f"wss://api.openai.com/v1/realtime?model={self.config.model}"
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            # Connect
            self.websocket = await websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5
            )
            
            self.state = TalkClientState.CONNECTED
            logger.info("✅ Connected to OpenAI Realtime API")
            
            # Start message handler
            self._message_handler_task = asyncio.create_task(self._handle_messages())
            
            # Start heartbeat
            self._heartbeat_task = asyncio.create_task(self._heartbeat())
            
            # Initialize session
            await self._initialize_session()
            
            # Notify connection change
            if self.on_connection_change:
                await self._safe_callback(self.on_connection_change, True)
            
            self._reconnect_attempts = 0
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to OpenAI: {e}")
            self.state = TalkClientState.ERROR
            await self._handle_error(f"OpenAI connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from OpenAI and cleanup"""
        logger.info("🔌 Disconnecting talk client...")
        
        # Cancel tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._message_handler_task:
            self._message_handler_task.cancel()
        
        # Close WebSocket
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.debug(f"WebSocket already closed: {e}")
        
        # Close WebRTC
        if self.peer_connection:
            await self.peer_connection.close()
        
        # Clear state
        self.state = TalkClientState.DISCONNECTED
        self.session_id = None
        self.jitter_buffer.clear()
        
        # Notify connection change
        if self.on_connection_change:
            await self._safe_callback(self.on_connection_change, False)
        
        logger.info("✅ Talk client disconnected")
    
    async def _initialize_session(self):
        """Initialize OpenAI session with English configuration"""
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": self.config.modalities,
                "instructions": self.config.instructions,
                "voice": self.config.voice,
                "input_audio_format": self.config.input_audio_format.value,
                "output_audio_format": self.config.output_audio_format.value,
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": self.config.turn_detection_type,
                    "threshold": self.config.vad_threshold,
                    "silence_duration_ms": self.config.vad_silence_duration_ms,
                    "prefix_padding_ms": self.config.vad_prefix_padding_ms
                },
                "tools": self.config.tools,
                "tool_choice": self.config.tool_choice,
                "temperature": self.config.temperature,
                "max_response_output_tokens": self.config.max_response_output_tokens
            }
        }
        
        await self._send_message(session_config)
        logger.info(f"🔧 OpenAI session initialized (voice: {self.config.voice}, language: {self.config.language})")
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send message to OpenAI WebSocket"""
        if not self.websocket:
            raise ConnectionError("WebSocket not connected")
        
        try:
            message_json = json.dumps(message)
            await self.websocket.send(message_json)
            logger.debug(f"📤 Sent message: {message.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
            await self._handle_error(f"Message send failed: {e}")
            raise
    
    async def _handle_messages(self):
        """Handle incoming messages from OpenAI"""
        try:
            while self.websocket and self.state in [TalkClientState.CONNECTED, TalkClientState.SESSION_ACTIVE]:
                try:
                    message = await self.websocket.recv()
                    await self._process_message(json.loads(message))
                except asyncio.TimeoutError:
                    continue
                    
        except ConnectionClosedError:
            logger.info("🔌 OpenAI WebSocket connection closed")
            await self._handle_disconnect()
        except WebSocketException as e:
            logger.error(f"❌ WebSocket error: {e}")
            await self._handle_disconnect()
        except Exception as e:
            logger.error(f"❌ Error handling messages: {e}")
            await self._handle_error(f"Message handling error: {e}")
    
    async def _process_message(self, message: Dict[str, Any]):
        """Process incoming message from OpenAI"""
        msg_type = message.get("type", "")
        
        try:
            if msg_type == "session.created":
                self.session_id = message.get("session", {}).get("id")
                self.state = TalkClientState.SESSION_ACTIVE
                logger.info(f"✅ OpenAI session created: {self.session_id}")
                
            elif msg_type == "session.updated":
                logger.info("🔄 OpenAI session updated")
                
            elif msg_type == "input_audio_buffer.speech_started":
                self.is_listening = True
                logger.info("🎤 Speech started (user speaking)")
                
                # Start new conversation turn
                self.current_turn_id = f"turn_{int(time.time() * 1000)}"
                self.talk_latency_logger.start_turn(self.current_turn_id, Route.REALTIME)
                
                # Implement barge-in if AI is currently speaking
                if self.is_speaking and self.playback_track:
                    if self.current_playback_id:
                        self.barge_in_logger.mark_user_voice_detected(self.current_playback_id)
                    barge_in_start = time.time()
                    await self._handle_barge_in()
                    barge_in_time = (time.time() - barge_in_start) * 1000
                    self.latency_metrics.add_barge_in_time(barge_in_time)
                    self.metrics.record_barge_in(barge_in_time)
                    
            elif msg_type == "input_audio_buffer.speech_stopped":
                self.is_listening = False
                logger.info("🔇 Speech stopped (user finished)")
                
            elif msg_type == "conversation.item.input_audio_transcription.completed":
                transcript = message.get("transcript", "")
                logger.info(f"📝 User transcript: {transcript}")
                
                # Mark transcript timing
                if self.current_turn_id:
                    self.talk_latency_logger.mark_event(self.current_turn_id, "stt_final")
                
                if self.on_transcript:
                    await self._safe_callback(self.on_transcript, transcript, True)
                    
            elif msg_type == "response.created":
                self.response_start_time = time.time()
                logger.info("🤖 AI response created")
                
            elif msg_type == "response.audio.delta":
                # Streaming audio from AI
                if "delta" in message:
                    # Mark first TTS chunk timing  
                    if self.current_turn_id and not self.first_audio_time:
                        self.talk_latency_logger.mark_event(self.current_turn_id, "tts_first_chunk")
                    
                    await self._handle_audio_delta(message["delta"])
                    # Call test callback if set
                    if self.on_audio_response and "delta" in message:
                        try:
                            import base64
                            audio_data = base64.b64decode(message["delta"])
                            await self._safe_callback(self.on_audio_response, audio_data)
                        except Exception as e:
                            logger.debug(f"Audio callback error: {e}")
                    
            elif msg_type == "response.audio.done":
                self.is_speaking = False
                if self.playback_track:
                    self.playback_track.set_playing(False)
                logger.info("✅ AI audio response completed")
                if self.on_audio_end:
                    await self._safe_callback(self.on_audio_end)
                    
            elif msg_type == "response.text.delta":
                # Handle text responses (for safe_summary messages)
                text_delta = message.get("delta", "")
                if "I'll check that locally" in text_delta or "local_result" in text_delta:
                    if self.on_safe_summary:
                        await self._safe_callback(self.on_safe_summary, text_delta)
                # Call test callback if set
                if self.on_text_response and text_delta:
                    await self._safe_callback(self.on_text_response, text_delta)
                        
            elif msg_type == "response.done":
                # Calculate and record latency metrics
                if self.response_start_time:
                    total_latency = (time.time() - self.response_start_time) * 1000
                    self.latency_metrics.add_latency(total_latency)
                
                if self.first_audio_time:
                    first_audio_latency = (self.first_audio_time - self.response_start_time) * 1000
                    self.latency_metrics.add_first_audio_time(first_audio_latency)
                    self.metrics.record_first_audio(first_audio_latency)
                
                # Log performance metrics
                p50, p95 = self.latency_metrics.get_p50_p95_latency()
                logger.info(f"📊 Response complete - P50: {p50:.1f}ms, P95: {p95:.1f}ms")
                
                # Finalize turn metrics
                if self.current_turn_id:
                    self.talk_latency_logger.mark_event(self.current_turn_id, "playback_start")
                    asyncio.create_task(self._finalize_turn_metrics())
                
                # Reset timing
                self.response_start_time = None
                self.first_audio_time = None
                
            elif msg_type == "error":
                error_msg = message.get("error", {}).get("message", "Unknown error")
                logger.error(f"❌ OpenAI API error: {error_msg}")
                await self._handle_error(f"API error: {error_msg}")
                
            else:
                logger.debug(f"📨 Unhandled message type: {msg_type}")
                
        except Exception as e:
            logger.error(f"❌ Error processing message type {msg_type}: {e}")
            await self._handle_error(f"Message processing error: {e}")
    
    async def _handle_audio_delta(self, audio_delta_b64: str):
        """Handle streaming audio delta from OpenAI"""
        try:
            # Decode base64 audio
            audio_data = base64.b64decode(audio_delta_b64)
            
            # Track first audio timing
            if not self.first_audio_time:
                self.first_audio_time = time.time()
                if not self.is_speaking:
                    self.is_speaking = True
                    # Start barge-in session tracking
                    self.current_playback_id = f"playback_{int(time.time() * 1000)}"
                    self.barge_in_logger.start_playback(self.current_playback_id, Route.REALTIME)
                    
                    if self.playback_track:
                        self.playback_track.set_playing(True)
                    if self.on_audio_start:
                        await self._safe_callback(self.on_audio_start)
            
            # Add to jitter buffer for smooth playback
            with self._audio_lock:
                self.jitter_buffer.add_audio(audio_data)
            
            logger.debug(f"🔊 Added {len(audio_data)} bytes to jitter buffer")
            
        except Exception as e:
            logger.error(f"❌ Error handling audio delta: {e}")
    
    async def _handle_barge_in(self):
        """Handle barge-in scenario - duck current audio and prepare for new response"""
        try:
            logger.info("🛑 Barge-in detected - ducking audio")
            self.barge_in_detected = True
            
            # Duck the current audio playback
            if self.playback_track:
                self.playback_track.duck(duck_level=0.1)  # Duck to 10% volume
            
            # Clear jitter buffer to stop current response quickly
            with self._audio_lock:
                self.jitter_buffer.clear()
            
            # Cancel current response
            await self._send_message({"type": "response.cancel"})
            
            # Brief pause before unducking
            await asyncio.sleep(0.05)  # 50ms
            
            # Restore volume
            if self.playback_track:
                self.playback_track.unduck()
            
            # Log barge-in completion
            if self.current_playback_id:
                asyncio.create_task(self._finalize_barge_in_metrics())
            
            self.barge_in_detected = False
            logger.info("✅ Barge-in handled successfully")
            
        except Exception as e:
            logger.error(f"❌ Error handling barge-in: {e}")
    
    async def _process_microphone_audio(self, track):
        """Process incoming microphone audio and stream to OpenAI"""
        logger.info("🎤 Starting microphone audio processing")
        audio_frame_count = 0
        
        try:
            while self.state == TalkClientState.SESSION_ACTIVE:
                frame = await track.recv()
                audio_frame_count += 1
                
                # Log every 10th frame initially to track activity more frequently
                if audio_frame_count % 10 == 0:
                    logger.info(f"🎤 Processed {audio_frame_count} audio frames from microphone")
                
                # Log first frame immediately to confirm mic is working
                if audio_frame_count == 1:
                    logger.info(f"🎤 FIRST AUDIO FRAME RECEIVED! Frame format: {frame.format if hasattr(frame, 'format') else 'unknown'}, Sample rate: {frame.sample_rate if hasattr(frame, 'sample_rate') else 'unknown'}")
                
                # Convert frame to PCM16 for OpenAI
                pcm_data = await self._convert_frame_to_pcm16(frame)
                if pcm_data:
                    logger.debug(f"🔊 Sending {len(pcm_data)} bytes of audio to OpenAI")
                    await self._send_audio_to_openai(pcm_data)
                else:
                    logger.warning("⚠️ Failed to convert audio frame to PCM16")
                    
        except Exception as e:
            logger.info(f"ℹ️ Microphone audio processing ended after {audio_frame_count} frames: {e}")
    
    async def _convert_frame_to_pcm16(self, frame) -> Optional[bytes]:
        """Convert WebRTC audio frame to PCM16 format for OpenAI"""
        try:
            # Convert frame to numpy array
            audio_data = frame.to_ndarray()
            logger.debug(f"🔊 Converting audio frame: shape={audio_data.shape}, dtype={audio_data.dtype}, size={len(audio_data) if audio_data is not None else 0}")
            
            # Handle different array layouts
            if len(audio_data.shape) == 2:
                if audio_data.shape[1] == 1:
                    audio_data = audio_data.flatten()
                else:
                    # Convert to mono by averaging channels
                    audio_data = np.mean(audio_data, axis=1)
            
            # Normalize to float32
            audio_data = audio_data.astype(np.float32)
            
            # Resample to 24kHz if needed
            if hasattr(frame, 'sample_rate') and frame.sample_rate != 24000:
                # Simple resampling (production should use proper resampling)
                ratio = 24000 / frame.sample_rate
                new_length = int(len(audio_data) * ratio)
                if new_length > 0:
                    indices = np.linspace(0, len(audio_data) - 1, new_length)
                    audio_data = np.interp(indices, np.arange(len(audio_data)), audio_data)
            
            # Convert to 16-bit PCM
            if len(audio_data) > 0:
                # Normalize and convert
                max_val = max(abs(audio_data.min()), abs(audio_data.max()))
                if max_val > 0:
                    audio_data = audio_data / max_val * 0.95  # Leave headroom
                
                pcm_data = (audio_data * 32767).astype(np.int16)
                return pcm_data.tobytes()
            
            return None
            
        except Exception as e:
            logger.debug(f"Frame conversion error: {e}")
            return None
    
    async def _send_audio_to_openai(self, pcm_data: bytes):
        """Send PCM audio data to OpenAI Realtime API"""
        try:
            # Convert to base64
            audio_b64 = base64.b64encode(pcm_data).decode('utf-8')
            
            # Send to OpenAI
            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_b64
            }
            
            await self._send_message(message)
            
        except Exception as e:
            logger.error(f"❌ Error sending audio to OpenAI: {e}")
    
    async def send_safe_summary(self, summary: str):
        """Send safe_summary message from local tools"""
        try:
            message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"local_result: {summary}"
                        }
                    ]
                }
            }
            
            await self._send_message(message)
            await self._send_message({"type": "response.create"})
            logger.info(f"📤 Sent safe_summary: {summary[:100]}...")
            
        except Exception as e:
            logger.error(f"❌ Error sending safe_summary: {e}")
    
    async def _heartbeat(self):
        """Maintain connection heartbeat"""
        try:
            while self.state in [TalkClientState.CONNECTED, TalkClientState.SESSION_ACTIVE]:
                await asyncio.sleep(30)
                
                # Check connection health
                if not self.websocket:
                    logger.warning("⚠️ WebSocket connection lost during heartbeat")
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"❌ Heartbeat error: {e}")
    
    async def _handle_disconnect(self):
        """Handle unexpected disconnection"""
        logger.warning("⚠️ Unexpected disconnection from OpenAI")
        self.state = TalkClientState.DISCONNECTED
        
        # Attempt reconnection
        if self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            self.state = TalkClientState.RECONNECTING
            logger.info(f"🔄 Reconnection attempt {self._reconnect_attempts}/{self._max_reconnect_attempts}")
            
            await asyncio.sleep(self._reconnect_delay * self._reconnect_attempts)
            success = await self.connect_to_openai()
            
            if not success:
                await self._handle_disconnect()
        else:
            logger.error("❌ Max reconnection attempts reached")
            await self._handle_error("Connection lost - max reconnection attempts reached")
    
    async def _handle_error(self, error_msg: str):
        """Handle errors with metrics tracking"""
        self.metrics.record_error("talk_client_error")
        
        if self.on_error:
            await self._safe_callback(self.on_error, error_msg)
        
        logger.error(f"🚨 Talk client error: {error_msg}")
    
    async def _safe_callback(self, callback: Callable, *args):
        """Safely execute callback with error handling"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"❌ Callback error: {e}")
    
    async def _finalize_turn_metrics(self):
        """Finalize and log turn latency metrics"""
        if self.current_turn_id:
            try:
                result = await self.talk_latency_logger.finalize_turn(self.current_turn_id)
                logger.info(f"🎯 Turn metrics: {result.get('slo_pass', False)} - {result.get('metrics', {})}")
                self.current_turn_id = None
            except Exception as e:
                logger.error(f"❌ Error finalizing turn metrics: {e}")
    
    async def _finalize_barge_in_metrics(self):
        """Finalize and log barge-in metrics"""
        if self.current_playback_id:
            try:
                result = await self.barge_in_logger.mark_tts_cut_complete(self.current_playback_id)
                logger.info(f"🛑 Barge-in metrics: {result.get('slo_pass', False)} - {result.get('metrics', {})}")
                self.current_playback_id = None
            except Exception as e:
                logger.error(f"❌ Error finalizing barge-in metrics: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        latency_stats = self.latency_metrics.get_stats()
        
        return {
            "connection_state": self.state.value,
            "uptime_seconds": time.time() - self.start_time,
            "latency_metrics": latency_stats,
            "audio_state": {
                "is_speaking": self.is_speaking,
                "is_listening": self.is_listening,
                "barge_in_detected": self.barge_in_detected,
                "jitter_buffer_size_ms": self.jitter_buffer._get_buffer_size_ms()
            },
            "reconnect_attempts": self._reconnect_attempts,
            "session_id": self.session_id
        }
    
    def is_connected(self) -> bool:
        """Check if client is connected and session is active"""
        return self.state == TalkClientState.SESSION_ACTIVE
    
    def set_response_callback(self, callback: Callable[[str], None]):
        """Set callback for text responses"""
        self.on_text_response = callback
    
    def set_audio_callback(self, callback: Callable[[bytes], None]):
        """Set callback for audio responses"""
        self.on_audio_response = callback


# Factory function for easy client creation
def create_talk_client(
    api_key: Optional[str] = None,
    voice: str = "alloy",  # or "nova" 
    instructions: Optional[str] = None,
    metrics: Optional[VoiceMetrics] = None,
    **kwargs
) -> OpenAIRealtimeTalkClient:
    """Create OpenAI Realtime Talk Client with production defaults"""
    
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
    
    # Use provided instructions or default
    if not instructions:
        instructions = ("You are the speaking persona 'Alice'. Language: English. "
                       "Speak concisely, 1–2 sentences. Do not call tools. "
                       "If a tool seems required, say: 'I'll check that locally.' "
                       "and wait for a 'local_result' message.")
    
    config = RealtimeConfig(
        api_key=api_key,
        voice=voice,
        instructions=instructions,
        **kwargs
    )
    
    return OpenAIRealtimeTalkClient(config, metrics)


# Example usage and testing
async def main():
    """Example usage of the Talk Client"""
    logging.basicConfig(level=logging.INFO)
    
    # Create client
    client = create_talk_client(voice="nova")
    
    # Set up event handlers
    def on_transcript(text: str, is_final: bool):
        print(f"{'📝 Final' if is_final else '⚡ Partial'} transcript: {text}")
    
    def on_audio_start():
        print("🔊 AI started speaking")
    
    def on_audio_end():
        print("🔇 AI finished speaking")
    
    def on_error(error: str):
        print(f"❌ Error: {error}")
    
    def on_connection_change(connected: bool):
        print(f"🔗 Connection: {'Connected' if connected else 'Disconnected'}")
    
    def on_safe_summary(summary: str):
        print(f"📋 Safe summary: {summary}")
    
    client.on_transcript = on_transcript
    client.on_audio_start = on_audio_start
    client.on_audio_end = on_audio_end
    client.on_error = on_error
    client.on_connection_change = on_connection_change
    client.on_safe_summary = on_safe_summary
    
    # Initialize and connect
    if await client.initialize():
        print("🚀 Talk client initialized successfully")
        
        # Handle WebRTC offer (would come from frontend)
        # offer_sdp = get_webrtc_offer_from_frontend()
        # answer_sdp = await client.handle_webrtc_offer(offer_sdp)
        # send_webrtc_answer_to_frontend(answer_sdp)
        
        # Keep running
        try:
            while True:
                # Print metrics every 30 seconds
                await asyncio.sleep(30)
                metrics = client.get_performance_metrics()
                print(f"📊 Metrics: {metrics}")
        except KeyboardInterrupt:
            print("👋 Shutting down...")
        finally:
            await client.disconnect()
    else:
        print("❌ Failed to initialize talk client")


if __name__ == "__main__":
    asyncio.run(main())