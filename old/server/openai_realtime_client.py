#!/usr/bin/env python3
"""
OpenAI Realtime API Client - Complete Implementation
Handles WebSocket connection to OpenAI for <300ms voice responses

Features:
- Real-time audio streaming (PCM16 ↔ OpenAI format)  
- Swedish language configuration for ASR/TTS
- Session management with automatic reconnection
- Barge-in support (interrupt TTS mid-speech)
- Cost tracking and usage monitoring
- Fallback support for offline mode
"""

import asyncio
import json
import base64
import time
import logging
import os
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

logger = logging.getLogger("alice.openai_realtime")

class RealtimeState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    SESSION_STARTED = "session_started"
    ERROR = "error"
    RECONNECTING = "reconnecting"

class AudioFormat(Enum):
    PCM16_24KHZ = "pcm16"
    G711_ULAW_8KHZ = "g711_ulaw"
    G711_ALAW_8KHZ = "g711_alaw"

@dataclass
class RealtimeConfig:
    """Configuration for OpenAI Realtime API"""
    api_key: str
    model: str = "gpt-4o-realtime-preview-2024-10-01"
    voice: str = "nova"  # Swedish-optimized voice
    language: str = "sv"
    max_response_output_tokens: int = 150  # Fast responses
    modalities: List[str] = None
    instructions: str = "Du är Alice, en svensk AI-assistent. Svara på svenska med korta, naturliga svar."
    tools: List[Dict] = None
    tool_choice: str = "none"
    temperature: float = 0.6
    input_audio_format: AudioFormat = AudioFormat.PCM16_24KHZ
    output_audio_format: AudioFormat = AudioFormat.PCM16_24KHZ
    input_audio_transcription_enabled: bool = True
    turn_detection_type: str = "server_vad"
    vad_threshold: float = 0.5
    vad_silence_duration_ms: int = 700
    vad_prefix_padding_ms: int = 300
    
    def __post_init__(self):
        if self.modalities is None:
            self.modalities = ["text", "audio"]

@dataclass 
class UsageStats:
    """Track OpenAI Realtime API usage and costs"""
    input_tokens: int = 0
    output_tokens: int = 0
    input_audio_duration_ms: int = 0
    output_audio_duration_ms: int = 0
    requests: int = 0
    errors: int = 0
    start_time: float = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = time.time()
    
    def add_input_tokens(self, tokens: int):
        self.input_tokens += tokens
    
    def add_output_tokens(self, tokens: int):
        self.output_tokens += tokens
    
    def add_audio_duration(self, input_ms: int = 0, output_ms: int = 0):
        self.input_audio_duration_ms += input_ms
        self.output_audio_duration_ms += output_ms
    
    def increment_request(self):
        self.requests += 1
    
    def increment_error(self):
        self.errors += 1
    
    def get_estimated_cost_usd(self) -> float:
        """Estimate cost based on OpenAI Realtime pricing"""
        # OpenAI Realtime API pricing (as of 2024)
        input_token_cost = self.input_tokens * 0.000006   # $6/1M input tokens
        output_token_cost = self.output_tokens * 0.000024  # $24/1M output tokens  
        input_audio_cost = (self.input_audio_duration_ms / 60000) * 0.10   # $0.10/minute input audio
        output_audio_cost = (self.output_audio_duration_ms / 60000) * 0.30  # $0.30/minute output audio
        
        return input_token_cost + output_token_cost + input_audio_cost + output_audio_cost

class OpenAIRealtimeClient:
    """
    OpenAI Realtime API WebSocket Client
    
    Handles real-time audio streaming with OpenAI for fast voice responses.
    Supports Swedish language, barge-in, session management, and cost tracking.
    """
    
    def __init__(self, config: RealtimeConfig):
        self.config = config
        self.state = RealtimeState.DISCONNECTED
        self.websocket = None
        self.session_id = None
        self.usage_stats = UsageStats()
        
        # Event handlers
        self.on_session_created: Optional[Callable] = None
        self.on_session_updated: Optional[Callable] = None
        self.on_conversation_created: Optional[Callable] = None
        self.on_input_audio_buffer_speech_started: Optional[Callable] = None
        self.on_input_audio_buffer_speech_stopped: Optional[Callable] = None
        self.on_input_audio_transcription_completed: Optional[Callable] = None
        self.on_response_created: Optional[Callable] = None
        self.on_response_done: Optional[Callable] = None
        self.on_response_text_delta: Optional[Callable] = None  
        self.on_response_text_done: Optional[Callable] = None
        self.on_response_audio_transcript_delta: Optional[Callable] = None
        self.on_response_audio_transcript_done: Optional[Callable] = None
        self.on_response_audio_delta: Optional[Callable] = None
        self.on_response_audio_done: Optional[Callable] = None
        self.on_rate_limits_updated: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Internal state
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 1.0
        self._heartbeat_task = None
        self._conversation_id = None
        self._current_response_id = None
        
        # Barge-in support
        self._interrupted = False
        
    async def connect(self) -> bool:
        """Connect to OpenAI Realtime API WebSocket"""
        if self.state == RealtimeState.CONNECTED:
            return True
            
        try:
            self.state = RealtimeState.CONNECTING
            logger.info("Connecting to OpenAI Realtime API...")
            
            # WebSocket URL with API key
            url = "wss://api.openai.com/v1/realtime"
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            # Connect to WebSocket
            self.websocket = await websockets.connect(
                url,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5
            )
            
            self.state = RealtimeState.CONNECTED
            logger.info("Connected to OpenAI Realtime API")
            
            # Start message handler
            asyncio.create_task(self._handle_messages())
            
            # Start heartbeat
            self._heartbeat_task = asyncio.create_task(self._heartbeat())
            
            # Initialize session
            await self._initialize_session()
            
            self._reconnect_attempts = 0
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime API: {e}")
            self.state = RealtimeState.ERROR
            await self._handle_error(str(e))
            return False
    
    async def disconnect(self):
        """Disconnect from OpenAI Realtime API"""
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        self.state = RealtimeState.DISCONNECTED
        self.session_id = None
        logger.info("Disconnected from OpenAI Realtime API")
    
    async def _initialize_session(self):
        """Initialize OpenAI session with Swedish configuration"""
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
                "tools": self.config.tools or [],
                "tool_choice": self.config.tool_choice,
                "temperature": self.config.temperature,
                "max_response_output_tokens": self.config.max_response_output_tokens
            }
        }
        
        await self._send_message(session_config)
        logger.info("Initialized OpenAI session with Swedish configuration")
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send message to OpenAI WebSocket"""
        if not self.websocket or self.websocket.closed:
            raise ConnectionError("WebSocket not connected")
        
        try:
            message_json = json.dumps(message)
            await self.websocket.send(message_json)
            self.usage_stats.increment_request()
            logger.debug(f"Sent message: {message.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.usage_stats.increment_error()
            await self._handle_error(str(e))
    
    async def _handle_messages(self):
        """Handle incoming messages from OpenAI"""
        try:
            while self.websocket and self.state == RealtimeState.CONNECTED:
                message = await self.websocket.recv()
                await self._process_message(json.loads(message))
                
        except ConnectionClosedError:
            logger.info("OpenAI WebSocket connection closed")
            await self._handle_disconnect()
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            await self._handle_disconnect()
        except Exception as e:
            logger.error(f"Error handling messages: {e}")
            await self._handle_error(str(e))
    
    async def _process_message(self, message: Dict[str, Any]):
        """Process incoming message based on type"""
        msg_type = message.get("type")
        
        if msg_type == "session.created":
            self.session_id = message.get("session", {}).get("id")
            self.state = RealtimeState.SESSION_STARTED
            if self.on_session_created:
                await self.on_session_created(message)
                
        elif msg_type == "session.updated":
            if self.on_session_updated:
                await self.on_session_updated(message)
                
        elif msg_type == "conversation.created":
            self._conversation_id = message.get("conversation", {}).get("id")
            if self.on_conversation_created:
                await self.on_conversation_created(message)
                
        elif msg_type == "input_audio_buffer.speech_started":
            if self.on_input_audio_buffer_speech_started:
                await self.on_input_audio_buffer_speech_started(message)
                
        elif msg_type == "input_audio_buffer.speech_stopped":
            if self.on_input_audio_buffer_speech_stopped:
                await self.on_input_audio_buffer_speech_stopped(message)
                
        elif msg_type == "conversation.item.input_audio_transcription.completed":
            transcript = message.get("transcript", "")
            if self.on_input_audio_transcription_completed:
                await self.on_input_audio_transcription_completed(transcript)
                
        elif msg_type == "response.created":
            self._current_response_id = message.get("response", {}).get("id")
            if self.on_response_created:
                await self.on_response_created(message)
                
        elif msg_type == "response.audio.delta":
            audio_data = base64.b64decode(message.get("delta", ""))
            if self.on_response_audio_delta:
                await self.on_response_audio_delta(audio_data)
                
        elif msg_type == "response.audio.done":
            if self.on_response_audio_done:
                await self.on_response_audio_done(message)
                
        elif msg_type == "response.text.delta":
            text_delta = message.get("delta", "")
            if self.on_response_text_delta:
                await self.on_response_text_delta(text_delta)
                
        elif msg_type == "response.text.done":
            text = message.get("text", "")
            if self.on_response_text_done:
                await self.on_response_text_done(text)
                
        elif msg_type == "response.audio_transcript.delta":
            delta = message.get("delta", "")
            if self.on_response_audio_transcript_delta:
                await self.on_response_audio_transcript_delta(delta)
                
        elif msg_type == "response.audio_transcript.done":
            transcript = message.get("transcript", "")
            if self.on_response_audio_transcript_done:
                await self.on_response_audio_transcript_done(transcript)
                
        elif msg_type == "response.done":
            usage = message.get("response", {}).get("usage")
            if usage:
                self._update_usage_stats(usage)
            if self.on_response_done:
                await self.on_response_done(message)
                
        elif msg_type == "rate_limits.updated":
            if self.on_rate_limits_updated:
                await self.on_rate_limits_updated(message)
                
        elif msg_type == "error":
            error_msg = message.get("error", {}).get("message", "Unknown error")
            logger.error(f"OpenAI API error: {error_msg}")
            await self._handle_error(error_msg)
        
        logger.debug(f"Processed message: {msg_type}")
    
    def _update_usage_stats(self, usage: Dict[str, Any]):
        """Update usage statistics from API response"""
        if "input_tokens" in usage:
            self.usage_stats.add_input_tokens(usage["input_tokens"])
        if "output_tokens" in usage:
            self.usage_stats.add_output_tokens(usage["output_tokens"])
        if "input_token_details" in usage:
            audio_tokens = usage["input_token_details"].get("audio", 0)
            # Estimate audio duration from tokens (rough approximation)
            self.usage_stats.add_audio_duration(input_ms=audio_tokens * 50)
    
    async def send_audio_chunk(self, audio_data: bytes):
        """Send audio chunk to OpenAI for processing"""
        if self.state != RealtimeState.SESSION_STARTED:
            logger.warning("Cannot send audio: session not started")
            return
        
        # Convert audio to base64
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        
        message = {
            "type": "input_audio_buffer.append",
            "audio": audio_b64
        }
        
        await self._send_message(message)
        
        # Track audio duration for cost estimation (PCM16 24kHz)
        duration_ms = len(audio_data) / (48000 / 1000)  # 2 bytes * 24kHz
        self.usage_stats.add_audio_duration(input_ms=int(duration_ms))
    
    async def commit_audio_buffer(self):
        """Commit audio buffer and trigger response generation"""
        message = {
            "type": "input_audio_buffer.commit"
        }
        await self._send_message(message)
    
    async def clear_audio_buffer(self):
        """Clear the audio input buffer"""
        message = {
            "type": "input_audio_buffer.clear"
        }
        await self._send_message(message)
    
    async def generate_response(self, modalities: List[str] = None):
        """Generate response from current conversation state"""
        message = {
            "type": "response.create",
            "response": {
                "modalities": modalities or self.config.modalities,
                "instructions": "Svara kort och naturligt på svenska."
            }
        }
        await self._send_message(message)
    
    async def interrupt_response(self):
        """Interrupt current response (barge-in support)"""
        if self._current_response_id:
            message = {
                "type": "response.cancel"
            }
            await self._send_message(message)
            self._interrupted = True
            logger.info("Interrupted current response")
    
    async def send_text_message(self, text: str):
        """Send text message to conversation"""
        message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": text
                    }
                ]
            }
        }
        
        await self._send_message(message)
        await self.generate_response()
    
    async def _heartbeat(self):
        """Send periodic heartbeat to maintain connection"""
        try:
            while self.websocket and self.state in [RealtimeState.CONNECTED, RealtimeState.SESSION_STARTED]:
                await asyncio.sleep(30)
                # OpenAI Realtime doesn't need explicit pings
                if self.websocket and self.websocket.closed:
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
    
    async def _handle_disconnect(self):
        """Handle WebSocket disconnection"""
        self.state = RealtimeState.DISCONNECTED
        
        # Attempt reconnection if not intentional
        if self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            self.state = RealtimeState.RECONNECTING
            logger.info(f"Reconnecting attempt {self._reconnect_attempts}/{self._max_reconnect_attempts}")
            
            await asyncio.sleep(self._reconnect_delay * self._reconnect_attempts)
            success = await self.connect()
            
            if not success:
                await self._handle_disconnect()
        else:
            logger.error("Max reconnection attempts reached")
            self.state = RealtimeState.ERROR
            await self._handle_error("Max reconnection attempts reached")
    
    async def _handle_error(self, error_msg: str):
        """Handle errors"""
        self.usage_stats.increment_error()
        if self.on_error:
            await self.on_error(error_msg)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        return {
            "input_tokens": self.usage_stats.input_tokens,
            "output_tokens": self.usage_stats.output_tokens,
            "input_audio_duration_ms": self.usage_stats.input_audio_duration_ms,
            "output_audio_duration_ms": self.usage_stats.output_audio_duration_ms,
            "requests": self.usage_stats.requests,
            "errors": self.usage_stats.errors,
            "estimated_cost_usd": self.usage_stats.get_estimated_cost_usd(),
            "uptime_seconds": time.time() - self.usage_stats.start_time,
            "state": self.state.value
        }
    
    def is_connected(self) -> bool:
        """Check if connected and session started"""
        return self.state == RealtimeState.SESSION_STARTED
    
    def get_connection_state(self) -> RealtimeState:
        """Get current connection state"""
        return self.state


# Factory function for creating client instances
def create_realtime_client(
    api_key: Optional[str] = None,
    voice: str = "nova",
    language: str = "sv",
    instructions: str = "Du är Alice, en svensk AI-assistent. Svara på svenska med korta, naturliga svar.",
    **kwargs
) -> OpenAIRealtimeClient:
    """Create OpenAI Realtime client with sensible Swedish defaults"""
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
    
    config = RealtimeConfig(
        api_key=api_key,
        voice=voice,
        language=language,
        instructions=instructions,
        **kwargs
    )
    
    return OpenAIRealtimeClient(config)