#!/usr/bin/env python3
"""
🎙️ Streaming ASR for Alice Voice Gateway
Real-time speech recognition with partials <300ms target

GPT-5 Day 1 Implementation:
- WebSocket streaming to Deepgram/OpenAI
- Partials every 40-80ms
- Semantic stabilizer for finals at 250-300ms silence
- Integration with WebRTC audio pipeline
"""
import asyncio
import json
import logging
import time
import websockets
import aiohttp
from typing import Optional, Callable, Dict, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class ASRProvider(Enum):
    DEEPGRAM = "deepgram"
    OPENAI_REALTIME = "openai_realtime"
    WHISPER_LOCAL = "whisper_local"

@dataclass
class ASRResult:
    """ASR result with timing and confidence"""
    text: str
    is_final: bool
    confidence: float
    start_time_ms: int
    end_time_ms: int
    session_id: str
    provider: ASRProvider

@dataclass
class ASRConfig:
    """ASR configuration"""
    provider: ASRProvider = ASRProvider.DEEPGRAM
    language: str = "sv"  # Swedish primary, English fallback
    sample_rate: int = 16000
    channels: int = 1
    encoding: str = "linear16"
    
    # Performance targets (GPT-5 specification)
    partial_threshold_ms: int = 250  # Silence before final
    max_partial_interval_ms: int = 80  # Max time between partials
    min_partial_interval_ms: int = 40  # Min time between partials
    confidence_threshold: float = 0.7
    
    # Provider-specific configs
    deepgram_model: str = "nova-2"
    deepgram_features: list = None
    openai_model: str = "whisper-1"
    
    def __post_init__(self):
        if self.deepgram_features is None:
            self.deepgram_features = [
                "punctuate", "diarize", "interim_results", 
                "endpointing", "vad_events", "language"
            ]

class ASRStreamBase(ABC):
    """Abstract base for streaming ASR providers"""
    
    def __init__(self, config: ASRConfig, session_id: str):
        self.config = config
        self.session_id = session_id
        self.is_connected = False
        self.last_partial_time = 0
        self.silence_start_time = 0
        self.current_utterance = ""
        
        # Callbacks for events
        self.on_partial: Optional[Callable[[ASRResult], None]] = None
        self.on_final: Optional[Callable[[ASRResult], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to ASR service"""
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from ASR service"""
        pass
        
    @abstractmethod
    async def send_audio(self, audio_chunk: bytes) -> None:
        """Send audio chunk to ASR service"""
        pass
        
    def _should_emit_partial(self, text: str, confidence: float) -> bool:
        """Determine if partial should be emitted based on timing/confidence"""
        current_time = time.time() * 1000
        time_since_last = current_time - self.last_partial_time
        
        # Emit if enough time passed or high confidence
        return (
            time_since_last >= self.config.min_partial_interval_ms and
            (time_since_last >= self.config.max_partial_interval_ms or 
             confidence >= self.config.confidence_threshold)
        )
    
    def _detect_utterance_end(self, text: str) -> bool:
        """Detect if utterance has ended based on semantic cues"""
        current_time = time.time() * 1000
        
        # Start silence timer if text hasn't changed
        if text == self.current_utterance:
            if self.silence_start_time == 0:
                self.silence_start_time = current_time
            elif current_time - self.silence_start_time >= self.config.partial_threshold_ms:
                return True
        else:
            # Reset silence timer on new text
            self.silence_start_time = 0
            self.current_utterance = text
            
        return False

class DeepgramASRStream(ASRStreamBase):
    """Deepgram streaming ASR implementation"""
    
    def __init__(self, config: ASRConfig, session_id: str):
        super().__init__(config, session_id)
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable required")
            
    async def connect(self) -> bool:
        """Connect to Deepgram streaming API"""
        try:
            # Construct Deepgram WebSocket URL
            features = "&".join([f"{feat}=true" for feat in self.config.deepgram_features])
            url = (
                f"wss://api.deepgram.com/v1/listen?"
                f"model={self.config.deepgram_model}&"
                f"language={self.config.language}&"
                f"encoding={self.config.encoding}&"
                f"sample_rate={self.config.sample_rate}&"
                f"channels={self.config.channels}&"
                f"{features}"
            )
            
            headers = {"Authorization": f"Token {self.api_key}"}
            
            self.websocket = await websockets.connect(url, extra_headers=headers)
            self.is_connected = True
            
            # Start listening for responses
            asyncio.create_task(self._listen_for_results())
            
            logger.info(f"✅ Deepgram connected for session {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Deepgram connection failed: {e}")
            if self.on_error:
                self.on_error(e)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Deepgram"""
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        logger.info(f"🔌 Deepgram disconnected for session {self.session_id}")
    
    async def send_audio(self, audio_chunk: bytes) -> None:
        """Send audio chunk to Deepgram"""
        if self.websocket and self.is_connected:
            try:
                await self.websocket.send(audio_chunk)
            except Exception as e:
                logger.error(f"❌ Deepgram send error: {e}")
                if self.on_error:
                    self.on_error(e)
    
    async def _listen_for_results(self):
        """Listen for Deepgram streaming results"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self._process_deepgram_result(data)
        except Exception as e:
            logger.error(f"❌ Deepgram listen error: {e}")
            if self.on_error:
                self.on_error(e)
    
    async def _process_deepgram_result(self, data: Dict[str, Any]):
        """Process Deepgram result and emit events"""
        try:
            if "channel" not in data or "alternatives" not in data["channel"]:
                return
                
            alternatives = data["channel"]["alternatives"]
            if not alternatives:
                return
                
            result = alternatives[0]  # Best alternative
            text = result.get("transcript", "").strip()
            confidence = result.get("confidence", 0.0)
            is_final = data.get("is_final", False)
            
            if not text:
                return
                
            current_time = int(time.time() * 1000)
            
            asr_result = ASRResult(
                text=text,
                is_final=is_final,
                confidence=confidence,
                start_time_ms=current_time,
                end_time_ms=current_time,
                session_id=self.session_id,
                provider=ASRProvider.DEEPGRAM
            )
            
            if is_final:
                if self.on_final:
                    self.on_final(asr_result)
                logger.debug(f"🎯 Final: {text} (confidence: {confidence:.2f})")
            else:
                # Emit partial based on timing/confidence rules
                if self._should_emit_partial(text, confidence):
                    if self.on_partial:
                        self.on_partial(asr_result)
                    self.last_partial_time = current_time
                    logger.debug(f"⚡ Partial: {text} (confidence: {confidence:.2f})")
                    
        except Exception as e:
            logger.error(f"❌ Error processing Deepgram result: {e}")

class OpenAIRealtimeASRStream(ASRStreamBase):
    """OpenAI Realtime API streaming ASR implementation"""
    
    def __init__(self, config: ASRConfig, session_id: str):
        super().__init__(config, session_id)
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable required")
    
    async def connect(self) -> bool:
        """Connect to OpenAI Realtime API"""
        try:
            url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            self.websocket = await websockets.connect(url, extra_headers=headers)
            self.is_connected = True
            
            # Send session configuration
            await self._configure_session()
            
            # Start listening for responses
            asyncio.create_task(self._listen_for_results())
            
            logger.info(f"✅ OpenAI Realtime connected for session {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ OpenAI Realtime connection failed: {e}")
            if self.on_error:
                self.on_error(e)
            return False
    
    async def _configure_session(self):
        """Configure OpenAI Realtime session"""
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["audio", "text"],
                "instructions": "You are a helpful assistant that transcribes Swedish and English speech.",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": self.config.partial_threshold_ms
                }
            }
        }
        
        await self.websocket.send(json.dumps(config))
    
    async def disconnect(self) -> None:
        """Disconnect from OpenAI Realtime"""
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        logger.info(f"🔌 OpenAI Realtime disconnected for session {self.session_id}")
    
    async def send_audio(self, audio_chunk: bytes) -> None:
        """Send audio chunk to OpenAI Realtime"""
        if self.websocket and self.is_connected:
            try:
                # Convert audio to base64 for OpenAI
                import base64
                audio_b64 = base64.b64encode(audio_chunk).decode('utf-8')
                
                message = {
                    "type": "input_audio_buffer.append",
                    "audio": audio_b64
                }
                
                await self.websocket.send(json.dumps(message))
            except Exception as e:
                logger.error(f"❌ OpenAI Realtime send error: {e}")
                if self.on_error:
                    self.on_error(e)
    
    async def _listen_for_results(self):
        """Listen for OpenAI Realtime streaming results"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self._process_openai_result(data)
        except Exception as e:
            logger.error(f"❌ OpenAI Realtime listen error: {e}")
            if self.on_error:
                self.on_error(e)
    
    async def _process_openai_result(self, data: Dict[str, Any]):
        """Process OpenAI Realtime result and emit events"""
        try:
            event_type = data.get("type", "")
            
            if event_type == "conversation.item.input_audio_transcription.completed":
                # Final transcription
                text = data.get("transcript", "").strip()
                if text:
                    current_time = int(time.time() * 1000)
                    
                    asr_result = ASRResult(
                        text=text,
                        is_final=True,
                        confidence=0.95,  # OpenAI doesn't provide confidence
                        start_time_ms=current_time,
                        end_time_ms=current_time,
                        session_id=self.session_id,
                        provider=ASRProvider.OPENAI_REALTIME
                    )
                    
                    if self.on_final:
                        self.on_final(asr_result)
                    logger.debug(f"🎯 OpenAI Final: {text}")
            
            elif event_type == "conversation.item.input_audio_transcription.partial":
                # Partial transcription
                text = data.get("transcript", "").strip()
                if text and self._should_emit_partial(text, 0.8):
                    current_time = int(time.time() * 1000)
                    
                    asr_result = ASRResult(
                        text=text,
                        is_final=False,
                        confidence=0.8,
                        start_time_ms=current_time,
                        end_time_ms=current_time,
                        session_id=self.session_id,
                        provider=ASRProvider.OPENAI_REALTIME
                    )
                    
                    if self.on_partial:
                        self.on_partial(asr_result)
                    self.last_partial_time = current_time
                    logger.debug(f"⚡ OpenAI Partial: {text}")
                    
        except Exception as e:
            logger.error(f"❌ Error processing OpenAI Realtime result: {e}")

class ASRStreamManager:
    """Manager for ASR streaming with multiple provider support"""
    
    def __init__(self, config: ASRConfig):
        self.config = config
        self.sessions: Dict[str, ASRStreamBase] = {}
        
    async def create_session(self, session_id: str) -> ASRStreamBase:
        """Create new ASR streaming session"""
        if session_id in self.sessions:
            await self.sessions[session_id].disconnect()
        
        # Create provider instance
        if self.config.provider == ASRProvider.DEEPGRAM:
            asr_stream = DeepgramASRStream(self.config, session_id)
        elif self.config.provider == ASRProvider.OPENAI_REALTIME:
            asr_stream = OpenAIRealtimeASRStream(self.config, session_id)
        else:
            raise ValueError(f"Unsupported ASR provider: {self.config.provider}")
        
        # Connect to provider
        if await asr_stream.connect():
            self.sessions[session_id] = asr_stream
            logger.info(f"✅ ASR session created: {session_id} ({self.config.provider.value})")
            return asr_stream
        else:
            raise Exception(f"Failed to connect ASR provider for session {session_id}")
    
    async def get_session(self, session_id: str) -> Optional[ASRStreamBase]:
        """Get existing ASR session"""
        return self.sessions.get(session_id)
    
    async def remove_session(self, session_id: str) -> None:
        """Remove and disconnect ASR session"""
        if session_id in self.sessions:
            await self.sessions[session_id].disconnect()
            del self.sessions[session_id]
            logger.info(f"🗑️ ASR session removed: {session_id}")
    
    async def cleanup(self) -> None:
        """Clean up all sessions"""
        for session_id in list(self.sessions.keys()):
            await self.remove_session(session_id)
        logger.info("🧹 ASR manager cleanup complete")

# Global ASR manager instance
_asr_manager: Optional[ASRStreamManager] = None

def get_asr_manager(config: Optional[ASRConfig] = None) -> ASRStreamManager:
    """Get global ASR manager instance"""
    global _asr_manager
    if _asr_manager is None:
        if config is None:
            # Default configuration
            provider = ASRProvider(os.getenv("ASR_PROVIDER", "deepgram"))
            config = ASRConfig(provider=provider)
        _asr_manager = ASRStreamManager(config)
    return _asr_manager

async def test_asr_streaming():
    """Test ASR streaming with sample audio"""
    config = ASRConfig(provider=ASRProvider.DEEPGRAM)
    manager = ASRStreamManager(config)
    
    # Create test session
    session = await manager.create_session("test_session")
    
    # Set up callbacks
    def on_partial(result: ASRResult):
        print(f"⚡ Partial: {result.text} (confidence: {result.confidence:.2f})")
    
    def on_final(result: ASRResult):
        print(f"🎯 Final: {result.text} (confidence: {result.confidence:.2f})")
    
    session.on_partial = on_partial
    session.on_final = on_final
    
    print("🎙️ ASR streaming test started - speak now!")
    
    # In real usage, WebRTC would send audio chunks here
    # For testing, we'd need actual audio data
    
    await asyncio.sleep(10)  # Test for 10 seconds
    await manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test_asr_streaming())