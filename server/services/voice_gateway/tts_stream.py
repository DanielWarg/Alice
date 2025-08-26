#!/usr/bin/env python3
"""
🗣️ TTS Streaming Manager for Alice Voice Gateway
GPT-5 Day 3: Real-time text-to-speech streaming with ElevenLabs/OpenAI TTS
"""
import asyncio
import json
import logging
import time
import io
import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, AsyncGenerator, Any
import aiohttp
import openai

# Optional import for advanced audio processing
try:
    import pydub
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    pydub = None
    AudioSegment = None
    HAS_PYDUB = False

logger = logging.getLogger(__name__)

class TTSProvider(Enum):
    """Supported TTS providers for streaming"""
    OPENAI_TTS = "openai_tts"
    ELEVENLABS = "elevenlabs"
    AZURE_TTS = "azure_tts"
    LOCAL_TTS = "local_tts"

class TTSVoice(Enum):
    """Voice options for different providers"""
    # OpenAI voices
    ALLOY = "alloy"
    ECHO = "echo" 
    FABLE = "fable"
    ONYX = "onyx"
    NOVA = "nova"
    SHIMMER = "shimmer"
    
    # ElevenLabs voices (examples)
    RACHEL = "21m00Tcm4TlvDq8ikWAM"  # Rachel
    DREW = "29vD33N1CtxCmqQRPOHJ"    # Drew
    CLYDE = "2EiwWnXFnvU5JabPnv8n"   # Clyde

@dataclass
class TTSConfig:
    """Configuration for TTS streaming"""
    provider: TTSProvider = TTSProvider.OPENAI_TTS
    voice: TTSVoice = TTSVoice.NOVA
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    # Audio settings
    sample_rate: int = 24000  # Hz
    format: str = "pcm"       # pcm, mp3, opus
    speed: float = 1.0        # Speech rate
    
    # Streaming parameters  
    chunk_size: int = 1024    # bytes per chunk
    buffer_size: int = 4096   # audio buffer size
    
    # Performance targets (GPT-5 Day 3)
    first_audio_target_ms: int = 300   # Time to first audio
    total_latency_target_ms: int = 500  # End-to-end latency

@dataclass
class TTSAudioChunk:
    """Single TTS audio chunk with metadata"""
    audio_data: bytes
    sample_rate: int = 24000
    format: str = "pcm"
    timestamp: float = field(default_factory=lambda: time.time() * 1000)
    is_final: bool = False
    provider: Optional[TTSProvider] = None
    chunk_index: int = 0

@dataclass
class TTSResponse:
    """Complete TTS response metadata"""
    text: str
    audio_chunks: List[TTSAudioChunk] = field(default_factory=list)
    total_duration_ms: float = 0.0
    session_id: str = ""
    provider: Optional[TTSProvider] = None
    
    # Performance metrics
    first_audio_latency_ms: Optional[float] = None
    synthesis_time_ms: float = 0.0
    audio_quality_score: Optional[float] = None

class TTSStreamBase(ABC):
    """Base class for TTS streaming implementations"""
    
    def __init__(self, config: TTSConfig, session_id: str):
        self.config = config
        self.session_id = session_id
        
        # Callbacks for streaming events
        self.on_audio_chunk: Optional[Callable[[TTSAudioChunk], None]] = None
        self.on_synthesis_start: Optional[Callable[[str], None]] = None
        self.on_synthesis_complete: Optional[Callable[[TTSResponse], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
        # Performance tracking
        self.start_time: Optional[float] = None
        self.first_audio_time: Optional[float] = None
        self.chunk_count = 0
        
    @abstractmethod
    async def synthesize_streaming(self, text: str) -> AsyncGenerator[TTSAudioChunk, None]:
        """Generate streaming TTS audio chunks"""
        pass

class OpenAITTSStream(TTSStreamBase):
    """OpenAI TTS streaming implementation"""
    
    def __init__(self, config: TTSConfig, session_id: str):
        super().__init__(config, session_id)
        self.client = openai.AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
        
    async def synthesize_streaming(self, text: str) -> AsyncGenerator[TTSAudioChunk, None]:
        """Generate streaming TTS using OpenAI API"""
        try:
            self.start_time = time.time() * 1000
            self.chunk_count = 0
            
            if self.on_synthesis_start:
                self.on_synthesis_start(text)
            
            # OpenAI TTS API call
            response = await self.client.audio.speech.create(
                model="tts-1",  # or tts-1-hd for higher quality
                voice=self.config.voice.value,
                input=text,
                response_format="pcm" if self.config.format == "pcm" else "mp3",
                speed=self.config.speed
            )
            
            # Stream audio in chunks
            audio_data = response.content
            
            # Track first audio timing
            if self.first_audio_time is None:
                self.first_audio_time = time.time() * 1000
                first_audio_latency = self.first_audio_time - self.start_time
                logger.debug(f"🔊 First audio: {first_audio_latency:.0f}ms (target: <300ms)")
            
            # Split into chunks for streaming
            chunk_size = self.config.chunk_size
            for i in range(0, len(audio_data), chunk_size):
                chunk_data = audio_data[i:i + chunk_size]
                
                is_final = (i + chunk_size) >= len(audio_data)
                
                chunk = TTSAudioChunk(
                    audio_data=chunk_data,
                    sample_rate=self.config.sample_rate,
                    format=self.config.format,
                    is_final=is_final,
                    provider=self.config.provider,
                    chunk_index=self.chunk_count
                )
                
                self.chunk_count += 1
                
                if self.on_audio_chunk:
                    self.on_audio_chunk(chunk)
                
                yield chunk
                
                # Small delay for realistic streaming
                await asyncio.sleep(0.01)
            
            # Calculate performance metrics
            total_time = time.time() * 1000 - self.start_time
            
            response_obj = TTSResponse(
                text=text,
                total_duration_ms=total_time,
                session_id=self.session_id,
                provider=self.config.provider,
                first_audio_latency_ms=self.first_audio_time - self.start_time if self.first_audio_time else None,
                synthesis_time_ms=total_time
            )
            
            if self.on_synthesis_complete:
                self.on_synthesis_complete(response_obj)
                
        except Exception as e:
            logger.error(f"❌ OpenAI TTS streaming error: {e}")
            if self.on_error:
                self.on_error(e)
            raise

class ElevenLabsTTSStream(TTSStreamBase):
    """ElevenLabs TTS streaming implementation"""
    
    def __init__(self, config: TTSConfig, session_id: str):
        super().__init__(config, session_id)
        self.api_key = config.api_key
        self.base_url = config.base_url or "https://api.elevenlabs.io/v1"
        
    async def synthesize_streaming(self, text: str) -> AsyncGenerator[TTSAudioChunk, None]:
        """Generate streaming TTS using ElevenLabs API"""
        try:
            self.start_time = time.time() * 1000
            self.chunk_count = 0
            
            if self.on_synthesis_start:
                self.on_synthesis_start(text)
            
            # ElevenLabs streaming endpoint
            voice_id = self.config.voice.value
            url = f"{self.base_url}/text-to-speech/{voice_id}/stream"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            payload = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"ElevenLabs API error: {response.status}")
                    
                    # Track first audio timing
                    if self.first_audio_time is None:
                        self.first_audio_time = time.time() * 1000
                        first_audio_latency = self.first_audio_time - self.start_time
                        logger.debug(f"🔊 First audio: {first_audio_latency:.0f}ms (target: <300ms)")
                    
                    # Stream audio chunks
                    async for chunk_data in response.content.iter_chunked(self.config.chunk_size):
                        if chunk_data:
                            chunk = TTSAudioChunk(
                                audio_data=chunk_data,
                                sample_rate=self.config.sample_rate,
                                format="mp3",  # ElevenLabs returns MP3
                                is_final=False,
                                provider=self.config.provider,
                                chunk_index=self.chunk_count
                            )
                            
                            self.chunk_count += 1
                            
                            if self.on_audio_chunk:
                                self.on_audio_chunk(chunk)
                            
                            yield chunk
                    
                    # Final chunk
                    final_chunk = TTSAudioChunk(
                        audio_data=b"",
                        is_final=True,
                        provider=self.config.provider,
                        chunk_index=self.chunk_count
                    )
                    yield final_chunk
            
            # Calculate performance metrics
            total_time = time.time() * 1000 - self.start_time
            
            response_obj = TTSResponse(
                text=text,
                total_duration_ms=total_time,
                session_id=self.session_id,
                provider=self.config.provider,
                first_audio_latency_ms=self.first_audio_time - self.start_time if self.first_audio_time else None,
                synthesis_time_ms=total_time
            )
            
            if self.on_synthesis_complete:
                self.on_synthesis_complete(response_obj)
                
        except Exception as e:
            logger.error(f"❌ ElevenLabs TTS streaming error: {e}")
            if self.on_error:
                self.on_error(e)
            raise

class TTSStreamManager:
    """Manages TTS streaming sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, TTSStreamBase] = {}
        self.config = self._load_config()
        
    def _load_config(self) -> TTSConfig:
        """Load TTS configuration from environment"""
        import os
        
        provider_name = os.getenv("TTS_PROVIDER", "openai_tts").upper()
        try:
            provider = TTSProvider[provider_name]
        except KeyError:
            logger.warning(f"Unknown TTS provider: {provider_name}, using OpenAI TTS")
            provider = TTSProvider.OPENAI_TTS
        
        # Voice selection
        voice_name = os.getenv("TTS_VOICE", "nova").upper()
        try:
            voice = TTSVoice[voice_name]
        except KeyError:
            logger.warning(f"Unknown voice: {voice_name}, using NOVA")
            voice = TTSVoice.NOVA
            
        return TTSConfig(
            provider=provider,
            voice=voice,
            api_key=os.getenv("OPENAI_API_KEY") if provider == TTSProvider.OPENAI_TTS else os.getenv("ELEVENLABS_API_KEY"),
            sample_rate=int(os.getenv("TTS_SAMPLE_RATE", "24000")),
            speed=float(os.getenv("TTS_SPEED", "1.0")),
            format=os.getenv("TTS_FORMAT", "pcm")
        )
    
    async def create_session(self, session_id: str) -> TTSStreamBase:
        """Create new TTS streaming session"""
        if session_id in self.sessions:
            logger.info(f"🔄 Reusing existing TTS session: {session_id}")
            return self.sessions[session_id]
            
        if self.config.provider == TTSProvider.OPENAI_TTS:
            tts_stream = OpenAITTSStream(self.config, session_id)
        elif self.config.provider == TTSProvider.ELEVENLABS:
            tts_stream = ElevenLabsTTSStream(self.config, session_id)
        else:
            raise ValueError(f"Unsupported TTS provider: {self.config.provider}")
        
        self.sessions[session_id] = tts_stream
        logger.info(f"✅ TTS session created: {session_id} (provider: {self.config.provider.value}, voice: {self.config.voice.value})")
        return tts_stream
    
    async def remove_session(self, session_id: str):
        """Remove TTS streaming session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"🔌 TTS session removed: {session_id}")
    
    def get_session(self, session_id: str) -> Optional[TTSStreamBase]:
        """Get existing TTS session"""
        return self.sessions.get(session_id)
    
    def get_session_count(self) -> int:
        """Get number of active TTS sessions"""
        return len(self.sessions)

# Global TTS manager instance
_tts_manager = TTSStreamManager()

def get_tts_manager() -> TTSStreamManager:
    """Get global TTS stream manager"""
    return _tts_manager