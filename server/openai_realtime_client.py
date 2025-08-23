"""
OpenAI Realtime API Client - Phase 2 Implementation
Handles WebSocket connection to OpenAI for blixtsnabb voice responses

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
from typing import Dict, Any, Optional, Callable, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import os
from datetime import datetime

import websockets
import numpy as np
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
    max_response_output_tokens: int = 2048
    modalities: list = None
    instructions: str = "Du är Alice, en svensk AI-assistent. Svara på svenska med korta, naturliga svar."
    tools: list = None
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
        # Estimated pricing (adjust based on actual OpenAI pricing)
        input_token_cost = self.input_tokens * 0.000002  # $2/1M tokens
        output_token_cost = self.output_tokens * 0.000006  # $6/1M tokens
        input_audio_cost = (self.input_audio_duration_ms / 1000) * 0.0001  # $0.10/min
        output_audio_cost = (self.output_audio_duration_ms / 1000) * 0.0003  # $0.30/min
        
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
        self.on_input_audio_buffer_committed: Optional[Callable] = None
        self.on_input_audio_buffer_cleared: Optional[Callable] = None
        self.on_input_audio_buffer_speech_started: Optional[Callable] = None
        self.on_input_audio_buffer_speech_stopped: Optional[Callable] = None
        self.on_conversation_item_created: Optional[Callable] = None
        self.on_conversation_item_truncated: Optional[Callable] = None
        self.on_conversation_item_deleted: Optional[Callable] = None
        self.on_conversation_item_input_audio_transcription_completed: Optional[Callable] = None
        self.on_conversation_item_input_audio_transcription_failed: Optional[Callable] = None
        self.on_response_created: Optional[Callable] = None
        self.on_response_done: Optional[Callable] = None
        self.on_response_output_item_added: Optional[Callable] = None
        self.on_response_output_item_done: Optional[Callable] = None
        self.on_response_content_part_added: Optional[Callable] = None
        self.on_response_content_part_done: Optional[Callable] = None
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
        self._message_queue = asyncio.Queue()
        self._response_handlers = {}
        self._conversation_id = None
        self._current_response_id = None
        
        # Barge-in support
        self._current_audio_playback = None
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
                close_timeout=10
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
            self.usage_stats.increment_error()
            
            if self.on_error:
                await self.on_error(f"Connection failed: {e}")
                
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
        """Initialize OpenAI Realtime session with Swedish configuration"""
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": self.config.modalities,
                "instructions": self.config.instructions,
                "voice": self.config.voice,
                "input_audio_format": self.config.input_audio_format.value,
                "output_audio_format": self.config.output_audio_format.value,
                "input_audio_transcription": {
                    "model": "whisper-1",
                    "language": self.config.language
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
        logger.info("Session initialized with Swedish configuration")
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send message to OpenAI Realtime API"""
        if not self.websocket or self.websocket.closed:
            raise ConnectionError("Not connected to OpenAI Realtime API")
            
        try:
            await self.websocket.send(json.dumps(message))
            self.usage_stats.increment_request()
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.usage_stats.increment_error()
            raise
    
    async def _handle_messages(self):
        """Handle incoming messages from OpenAI Realtime API"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except ConnectionClosedError:
            logger.info("OpenAI Realtime connection closed")
            await self._handle_disconnect()
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            await self._handle_disconnect()
        except Exception as e:
            logger.error(f"Unexpected error in message handler: {e}")
            await self._handle_disconnect()
    
    async def _process_message(self, data: Dict[str, Any]):
        """Process incoming message from OpenAI"""
        event_type = data.get("type", "")
        
        # Handle session events
        if event_type == "session.created":
            self.session_id = data.get("session", {}).get("id")
            self.state = RealtimeState.SESSION_STARTED
            if self.on_session_created:
                await self.on_session_created(data.get("session", {}))
                
        elif event_type == "session.updated":
            if self.on_session_updated:
                await self.on_session_updated(data.get("session", {}))
                
        # Handle conversation events
        elif event_type == "conversation.created":
            self._conversation_id = data.get("conversation", {}).get("id")
            if self.on_conversation_created:
                await self.on_conversation_created(data.get("conversation", {}))
                
        # Handle input audio buffer events
        elif event_type == "input_audio_buffer.committed":
            if self.on_input_audio_buffer_committed:
                await self.on_input_audio_buffer_committed(data)
                
        elif event_type == "input_audio_buffer.cleared":
            if self.on_input_audio_buffer_cleared:
                await self.on_input_audio_buffer_cleared(data)
                
        elif event_type == "input_audio_buffer.speech_started":
            if self.on_input_audio_buffer_speech_started:
                await self.on_input_audio_buffer_speech_started(data)
                
        elif event_type == "input_audio_buffer.speech_stopped":
            if self.on_input_audio_buffer_speech_stopped:
                await self.on_input_audio_buffer_speech_stopped(data)
        
        # Handle conversation item events
        elif event_type == "conversation.item.created":
            if self.on_conversation_item_created:
                await self.on_conversation_item_created(data.get("item", {}))
                
        elif event_type == "conversation.item.input_audio_transcription.completed":
            transcript = data.get("transcript", "")
            if self.on_input_audio_buffer_committed:
                await self.on_conversation_item_input_audio_transcription_completed(transcript)
                
        elif event_type == "conversation.item.input_audio_transcription.failed":
            error = data.get("error", {})
            if self.on_conversation_item_input_audio_transcription_failed:
                await self.on_conversation_item_input_audio_transcription_failed(error)
                
        # Handle response events
        elif event_type == "response.created":
            self._current_response_id = data.get("response", {}).get("id")
            if self.on_response_created:
                await self.on_response_created(data.get("response", {}))
                
        elif event_type == "response.done":
            response_data = data.get("response", {})
            # Track usage from response
            usage = response_data.get("usage", {})
            if usage:
                self.usage_stats.add_input_tokens(usage.get("input_tokens", 0))
                self.usage_stats.add_output_tokens(usage.get("output_tokens", 0))
                
            if self.on_response_done:
                await self.on_response_done(response_data)
                
        elif event_type == "response.output_item.added":
            if self.on_response_output_item_added:
                await self.on_response_output_item_added(data.get("item", {}))
                
        elif event_type == "response.output_item.done":
            if self.on_response_output_item_done:
                await self.on_response_output_item_done(data.get("item", {}))
                
        elif event_type == "response.content_part.added":
            if self.on_response_content_part_added:
                await self.on_response_content_part_added(data.get("part", {}))
                
        elif event_type == "response.content_part.done":
            if self.on_response_content_part_done:
                await self.on_response_content_part_done(data.get("part", {}))
                
        # Handle streaming content
        elif event_type == "response.text.delta":
            delta = data.get("delta", "")
            if self.on_response_text_delta:
                await self.on_response_text_delta(delta)
                
        elif event_type == "response.text.done":
            text = data.get("text", "")
            if self.on_response_text_done:
                await self.on_response_text_done(text)
                
        elif event_type == "response.audio_transcript.delta":
            delta = data.get("delta", "")
            if self.on_response_audio_transcript_delta:
                await self.on_response_audio_transcript_delta(delta)
                
        elif event_type == "response.audio_transcript.done":
            transcript = data.get("transcript", "")
            if self.on_response_audio_transcript_done:
                await self.on_response_audio_transcript_done(transcript)
                
        elif event_type == "response.audio.delta":
            audio_data = data.get("delta", "")
            if self.on_response_audio_delta:
                await self.on_response_audio_delta(audio_data)
                
        elif event_type == "response.audio.done":
            if self.on_response_audio_done:
                await self.on_response_audio_done()
                
        # Handle rate limits
        elif event_type == "rate_limits.updated":
            rate_limits = data.get("rate_limits", [])
            if self.on_rate_limits_updated:
                await self.on_rate_limits_updated(rate_limits)
                
        # Handle errors
        elif event_type == "error":
            error_data = data.get("error", {})
            error_message = error_data.get("message", "Unknown error")
            logger.error(f"OpenAI Realtime error: {error_message}")
            self.usage_stats.increment_error()
            
            if self.on_error:
                await self.on_error(error_message)
        
        else:
            logger.debug(f"Unhandled event type: {event_type}")
    
    async def _handle_disconnect(self):
        """Handle connection disconnect and attempt reconnection"""
        self.state = RealtimeState.DISCONNECTED
        
        if self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            self.state = RealtimeState.RECONNECTING
            
            logger.info(f"Attempting reconnection {self._reconnect_attempts}/{self._max_reconnect_attempts}")
            
            await asyncio.sleep(self._reconnect_delay * self._reconnect_attempts)
            
            if await self.connect():
                logger.info("Successfully reconnected to OpenAI Realtime API")
            else:
                await self._handle_disconnect()
        else:
            logger.error("Max reconnection attempts reached")
            self.state = RealtimeState.ERROR
            if self.on_error:
                await self.on_error("Connection lost and max reconnection attempts reached")
    
    async def _heartbeat(self):
        """Send periodic heartbeat to keep connection alive"""
        try:
            while self.state in [RealtimeState.CONNECTED, RealtimeState.SESSION_STARTED]:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                
                if self.websocket and not self.websocket.closed:
                    # OpenAI Realtime doesn't have explicit ping, but we can check the connection
                    continue
                else:
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
    
    async def send_audio_chunk(self, audio_data: bytes):
        """Send audio chunk to OpenAI for processing"""
        if self.state != RealtimeState.SESSION_STARTED:
            raise ConnectionError("Session not started")
            
        # Convert PCM16 to base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        message = {
            "type": "input_audio_buffer.append",
            "audio": audio_base64
        }
        
        await self._send_message(message)
        
        # Track audio duration for cost estimation
        # PCM16 mono 24kHz = 48,000 bytes per second
        duration_ms = len(audio_data) / (48000 / 1000)  # Convert to milliseconds
        self.usage_stats.add_audio_duration(input_ms=int(duration_ms))
    
    async def commit_audio_buffer(self):
        """Commit audio buffer and trigger response generation"""
        message = {
            "type": "input_audio_buffer.commit"
        }
        
        await self._send_message(message)
    
    async def clear_audio_buffer(self):
        """Clear audio buffer"""
        message = {
            "type": "input_audio_buffer.clear"
        }
        
        await self._send_message(message)
    
    async def send_text_message(self, text: str, role: str = "user"):
        """Send text message to conversation"""
        message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": role,
                "content": [
                    {
                        "type": "input_text",
                        "text": text
                    }
                ]
            }
        }
        
        await self._send_message(message)
        
        # Trigger response
        await self.create_response()
    
    async def create_response(self, modalities: Optional[list] = None):
        """Create response from OpenAI"""
        message = {
            "type": "response.create",
            "response": {
                "modalities": modalities or self.config.modalities
            }
        }
        
        await self._send_message(message)
    
    async def cancel_response(self):
        """Cancel current response (barge-in support)"""
        if self._current_response_id:
            message = {
                "type": "response.cancel"
            }
            
            await self._send_message(message)
            self._interrupted = True
    
    async def truncate_conversation_item(self, item_id: str, content_index: int, audio_end_ms: int):
        """Truncate conversation item (for barge-in)"""
        message = {
            "type": "conversation.item.truncate",
            "item_id": item_id,
            "content_index": content_index,
            "audio_end_ms": audio_end_ms
        }
        
        await self._send_message(message)
    
    def get_usage_stats(self) -> UsageStats:
        """Get current usage statistics"""
        return self.usage_stats
    
    def reset_usage_stats(self):
        """Reset usage statistics"""
        self.usage_stats = UsageStats()
    
    def is_connected(self) -> bool:
        """Check if connected to OpenAI Realtime API"""
        return self.state == RealtimeState.SESSION_STARTED
    
    def get_connection_state(self) -> RealtimeState:
        """Get current connection state"""
        return self.state


def create_realtime_client(
    api_key: Optional[str] = None,
    voice: str = "nova",
    language: str = "sv",
    instructions: str = "Du är Alice, en svensk AI-assistent. Svara på svenska med korta, naturliga svar."
) -> OpenAIRealtimeClient:
    """
    Create OpenAI Realtime client with Swedish defaults
    
    Args:
        api_key: OpenAI API key (if None, uses OPENAI_API_KEY env var)
        voice: Voice to use for TTS
        language: Language code 
        instructions: System instructions for the model
    
    Returns:
        Configured OpenAI Realtime client
    """
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
    
    config = RealtimeConfig(
        api_key=api_key,
        voice=voice,
        language=language,
        instructions=instructions,
        model=os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview-2024-10-01"),
        temperature=float(os.getenv("OPENAI_REALTIME_TEMPERATURE", "0.6")),
        max_response_output_tokens=int(os.getenv("FAST_PATH_MAX_TOKENS", "150"))
    )
    
    return OpenAIRealtimeClient(config)