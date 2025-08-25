#!/usr/bin/env python3
"""
Alice Always-On Voice System
Continuous listening with wake-word detection and spontaneous responses

Features:
- Kontinuerlig mikrofon-lyssning med wake-word "Hej Alice"
- OpenAI Realtime integration för snabba svar (<300ms)  
- Automatisk transkribering och intent-routing
- Background ambient awareness (B3 integration)
- Smart barge-in och interrupt hantering
- Battery-optimized VAD (Voice Activity Detection)
"""

import asyncio
import logging
import time
import json
import os
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
import numpy as np
import collections
try:
    import webrtcvad
    HAS_WEBRTC_VAD = True
except ImportError:
    HAS_WEBRTC_VAD = False
    print("⚠️ webrtcvad not available - using simple VAD fallback")

try:
    from .openai_realtime_client import create_realtime_client, OpenAIRealtimeClient, RealtimeState
    from .fast_path_handler import FastPathHandler, FastPathDecision
    from .logger_config import get_logger
except ImportError:
    # Fallback för när vi kör direkt
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from openai_realtime_client import create_realtime_client, OpenAIRealtimeClient, RealtimeState
    from fast_path_handler import FastPathHandler, FastPathDecision
    from logger_config import get_logger

logger = get_logger("alice.voice_always_on")

class VoiceState(Enum):
    IDLE = "idle"                    # Lyssnar passivt efter wake-word
    WAKE_DETECTED = "wake_detected"   # "Hej Alice" detekterat
    ACTIVE_LISTENING = "active"       # Aktivt lyssnande för kommando
    PROCESSING = "processing"         # Bearbetar input
    RESPONDING = "responding"         # Ger svar (TTS)
    ERROR = "error"                   # Fel tillstånd

@dataclass
class VoiceConfig:
    """Konfiguration för always-on voice system"""
    # Wake-word detection
    wake_phrase: str = "hej alice"
    wake_sensitivity: float = 0.7
    wake_timeout_ms: int = 3000
    
    # Audio processing  
    sample_rate: int = 16000         # 16kHz för optimal wake-word detection
    frame_duration_ms: int = 30      # 30ms frames för WebRTC VAD
    channels: int = 1                # Mono audio
    
    # Voice Activity Detection
    vad_mode: int = 2                # WebRTC VAD aggressivitet (0-3)
    min_speech_duration_ms: int = 300
    max_speech_duration_ms: int = 10000
    silence_timeout_ms: int = 1500
    
    # OpenAI Realtime
    use_realtime_api: bool = True
    realtime_voice: str = "nova"
    fast_response_timeout_ms: int = 300
    
    # Battery optimization
    energy_threshold: float = 0.01   # Minimum ljud-energi för aktivering
    background_check_interval_ms: int = 100

class WakeWordDetector:
    """Enkel wake-word detektor för "Hej Alice" """
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self.audio_buffer = collections.deque(maxlen=int(config.sample_rate * 3))  # 3 sekunder buffer
        self.last_detection_time = 0
        
    def add_audio(self, audio_data: np.ndarray) -> bool:
        """Lägg till audio och kolla för wake-word"""
        # Lägg till i buffer
        self.audio_buffer.extend(audio_data)
        
        # Enkel energi-baserad pre-filter
        energy = np.mean(audio_data ** 2)
        if energy < self.config.energy_threshold:
            return False
            
        # Förhindra dubbeldetektioner
        current_time = time.time() * 1000
        if current_time - self.last_detection_time < self.config.wake_timeout_ms:
            return False
        
        # Placeholder för mer sofistikerad wake-word detection
        # I produktion: använd Picovoice Porcupine, Mycroft Precise, eller träna egen modell
        if len(self.audio_buffer) > self.config.sample_rate * 2:  # Minst 2 sekunder
            detection_score = self._simple_wake_detection()
            
            if detection_score > self.config.wake_sensitivity:
                self.last_detection_time = current_time
                logger.info(f"Wake word detected! Score: {detection_score:.2f}")
                return True
                
        return False
    
    def _simple_wake_detection(self) -> float:
        """
        Enkel wake-word detektor baserad på spektral analys
        I produktion: ersätt med tränad neural network eller Porcupine
        """
        # Detta är en placeholder implementation
        # Riktiga implementationen skulle använda:
        # - Mel-frequency cepstral coefficients (MFCC)
        # - Tränad klassificeringsmodell för "hej alice"
        # - Temporal alignment med dynamisk programmering
        
        audio_array = np.array(list(self.audio_buffer))
        
        if len(audio_array) < self.config.sample_rate:
            return 0.0
            
        # Enkel spektral energi-analys som placeholder
        # Kännetecken för svensk "hej alice":
        # - Låg frekvens för "hej" (250-500 Hz)  
        # - Hög frekvens för "alice" (1000-2000 Hz)
        
        fft = np.fft.rfft(audio_array[-self.config.sample_rate:])
        freqs = np.fft.rfftfreq(len(audio_array[-self.config.sample_rate:]), 1/self.config.sample_rate)
        
        # Energi i olika frekvensband
        low_energy = np.sum(np.abs(fft[(freqs >= 250) & (freqs <= 500)]))
        mid_energy = np.sum(np.abs(fft[(freqs >= 500) & (freqs <= 1000)]))  
        high_energy = np.sum(np.abs(fft[(freqs >= 1000) & (freqs <= 2000)]))
        
        # Enkel score baserad på energifördelning
        total_energy = low_energy + mid_energy + high_energy
        if total_energy == 0:
            return 0.0
            
        # "Hej Alice" borde ha både låg och hög energi
        score = (low_energy + high_energy) / total_energy
        
        # Normalisera till 0-1 range
        return min(score * 2, 1.0)  # Multiplicera med 2 för att öka känslighet

class AlwaysOnVoiceSystem:
    """
    Always-On Voice System för Alice
    
    Hanterar kontinuerlig lyssning, wake-word detection och snabba svar
    """
    
    def __init__(self, config: VoiceConfig = None):
        self.config = config or VoiceConfig()
        self.state = VoiceState.IDLE
        
        # Components
        self.wake_detector = WakeWordDetector(self.config)
        self.realtime_client: Optional[OpenAIRealtimeClient] = None
        self.fast_path_handler: Optional[FastPathHandler] = None
        # Initialize VAD (Voice Activity Detection)
        if HAS_WEBRTC_VAD:
            self.vad = webrtcvad.Vad(self.config.vad_mode)
        else:
            self.vad = None  # Use simple energy-based VAD fallback
        
        # Audio buffers
        self.speech_buffer = []
        self.silence_frames = 0
        self.speech_frames = 0
        
        # Event handlers
        self.on_wake_detected: Optional[Callable] = None
        self.on_speech_started: Optional[Callable] = None
        self.on_speech_ended: Optional[Callable] = None
        self.on_transcript_received: Optional[Callable] = None
        self.on_response_started: Optional[Callable] = None
        self.on_response_completed: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # State tracking
        self._is_running = False
        self._current_session_id = None
        self._response_start_time = None
        
    async def start(self):
        """Starta always-on voice systemet"""
        if self._is_running:
            logger.warning("Voice system already running")
            return
            
        try:
            logger.info("Starting Alice Always-On Voice System...")
            
            # Initialisera OpenAI Realtime client om aktiverat
            if self.config.use_realtime_api:
                await self._setup_realtime_client()
            
            # Initialisera fast path handler
            self._setup_fast_path_handler()
            
            self._is_running = True
            self.state = VoiceState.IDLE
            
            # Starta audio processing loop
            asyncio.create_task(self._audio_processing_loop())
            
            logger.info("✅ Always-On Voice System started and listening for 'Hej Alice'")
            
        except Exception as e:
            logger.error(f"Failed to start voice system: {e}")
            await self._handle_error(str(e))
    
    async def stop(self):
        """Stoppa voice systemet"""
        logger.info("Stopping Always-On Voice System...")
        self._is_running = False
        
        if self.realtime_client:
            await self.realtime_client.disconnect()
        
        self.state = VoiceState.IDLE
        logger.info("Voice system stopped")
    
    async def _setup_realtime_client(self):
        """Setup OpenAI Realtime API client"""
        try:
            self.realtime_client = create_realtime_client(
                voice=self.config.realtime_voice,
                instructions="Du är Alice. Svara på svenska med korta, naturliga svar på max 2 meningar."
            )
            
            # Setup event handlers
            self.realtime_client.on_session_created = self._on_realtime_session_created
            self.realtime_client.on_input_audio_transcription_completed = self._on_transcription_completed
            self.realtime_client.on_response_audio_delta = self._on_response_audio_delta
            self.realtime_client.on_response_done = self._on_response_done
            self.realtime_client.on_error = self._on_realtime_error
            
            # Connect to OpenAI
            success = await self.realtime_client.connect()
            if success:
                logger.info("✅ OpenAI Realtime API connected")
            else:
                logger.error("❌ Failed to connect to OpenAI Realtime API")
                
        except Exception as e:
            logger.error(f"Failed to setup OpenAI Realtime client: {e}")
            self.realtime_client = None
    
    def _setup_fast_path_handler(self):
        """Setup fast path handler för intent routing"""
        try:
            self.fast_path_handler = FastPathHandler()
            logger.info("✅ Fast path handler initialized")
        except Exception as e:
            logger.error(f"Failed to setup fast path handler: {e}")
    
    async def _audio_processing_loop(self):
        """Huvudloop för audio processing"""
        try:
            # Placeholder för audio capture
            # I verklig implementation: använd pyaudio, sounddevice, eller WebRTC
            logger.info("Audio processing loop started (placeholder implementation)")
            
            frame_duration_s = self.config.frame_duration_ms / 1000
            frame_size = int(self.config.sample_rate * frame_duration_s)
            
            while self._is_running:
                # Simulerar audio capture
                # I verklig implementation: läs från mikrofon
                await asyncio.sleep(frame_duration_s)
                
                # Generera simulerat bakgrundsljud med lite variation
                audio_frame = np.random.normal(0, 0.001, frame_size).astype(np.float32)
                
                # Processa audio frame
                await self._process_audio_frame(audio_frame)
                
        except Exception as e:
            logger.error(f"Error in audio processing loop: {e}")
            await self._handle_error(str(e))
    
    async def _process_audio_frame(self, audio_frame: np.ndarray):
        """Processa en audio frame baserat på nuvarande tillstånd"""
        try:
            if self.state == VoiceState.IDLE:
                # Lyssna efter wake-word
                if self.wake_detector.add_audio(audio_frame):
                    await self._handle_wake_detected()
                    
            elif self.state == VoiceState.ACTIVE_LISTENING:
                # Voice Activity Detection för kommando
                await self._handle_speech_detection(audio_frame)
                
            elif self.state == VoiceState.RESPONDING:
                # Under response: lyssna efter interrupt
                if self.wake_detector.add_audio(audio_frame):
                    await self._handle_interrupt()
                    
        except Exception as e:
            logger.error(f"Error processing audio frame: {e}")
    
    async def _handle_wake_detected(self):
        """Hantera wake-word detection"""
        self.state = VoiceState.WAKE_DETECTED
        logger.info("🎙️ Wake word 'Hej Alice' detected - activating listening")
        
        if self.on_wake_detected:
            await self.on_wake_detected()
        
        # Övergå till aktivt lyssnande
        await asyncio.sleep(0.1)  # Kort paus efter wake-word
        self.state = VoiceState.ACTIVE_LISTENING
        self.speech_buffer = []
        self.silence_frames = 0
        self.speech_frames = 0
        
        if self.on_speech_started:
            await self.on_speech_started()
    
    async def _handle_speech_detection(self, audio_frame: np.ndarray):
        """Hantera tal-detection under aktivt lyssnande"""
        # Voice Activity Detection
        if HAS_WEBRTC_VAD and self.vad:
            # WebRTC VAD check
            audio_bytes = (audio_frame * 32767).astype(np.int16).tobytes()
            is_speech = self.vad.is_speech(audio_bytes, self.config.sample_rate)
        else:
            # Simple energy-based VAD fallback
            energy = np.mean(audio_frame ** 2)
            is_speech = energy > self.config.energy_threshold
        
        if is_speech:
            self.speech_frames += 1
            self.silence_frames = 0
            self.speech_buffer.extend(audio_frame)
        else:
            self.silence_frames += 1
            
        # Check för end of speech
        silence_duration_ms = self.silence_frames * self.config.frame_duration_ms
        speech_duration_ms = self.speech_frames * self.config.frame_duration_ms
        
        if (silence_duration_ms > self.config.silence_timeout_ms and 
            speech_duration_ms > self.config.min_speech_duration_ms):
            await self._handle_speech_ended()
            
        elif speech_duration_ms > self.config.max_speech_duration_ms:
            # Max speech duration nådd
            await self._handle_speech_ended()
    
    async def _handle_speech_ended(self):
        """Hantera när tal har slutat"""
        if not self.speech_buffer:
            logger.warning("No speech data captured")
            self.state = VoiceState.IDLE
            return
            
        logger.info(f"Speech ended - captured {len(self.speech_buffer)} samples")
        self.state = VoiceState.PROCESSING
        
        if self.on_speech_ended:
            await self.on_speech_ended()
        
        # Skicka audio till processing
        await self._process_captured_speech()
    
    async def _process_captured_speech(self):
        """Processa fångat tal"""
        try:
            if self.realtime_client and self.realtime_client.is_connected():
                # Skicka till OpenAI Realtime för snabb processing
                await self._process_with_realtime(self.speech_buffer)
            else:
                # Fallback till lokal processing
                await self._process_with_local_fallback()
                
        except Exception as e:
            logger.error(f"Error processing speech: {e}")
            await self._handle_error(str(e))
    
    async def _process_with_realtime(self, audio_data: List[float]):
        """Processa med OpenAI Realtime API"""
        try:
            # Convert till bytes för OpenAI
            audio_bytes = (np.array(audio_data) * 32767).astype(np.int16).tobytes()
            
            # Skicka audio chunks
            chunk_size = 1024
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i+chunk_size]
                await self.realtime_client.send_audio_chunk(chunk)
            
            # Commit audio buffer för processing
            await self.realtime_client.commit_audio_buffer()
            
            self._response_start_time = time.time()
            self.state = VoiceState.RESPONDING
            
        except Exception as e:
            logger.error(f"Error with OpenAI Realtime: {e}")
            await self._process_with_local_fallback()
    
    async def _process_with_local_fallback(self):
        """Fallback processing utan OpenAI"""
        logger.info("Processing with local fallback")
        # Placeholder för lokal processing
        # I verklig implementation: använd local STT + local LLM
        
        # Simulerad response
        await asyncio.sleep(1)
        
        if self.on_transcript_received:
            await self.on_transcript_received("Kunde inte förstå kommandot")
        
        self.state = VoiceState.IDLE
    
    async def _handle_interrupt(self):
        """Hantera avbrott under response"""
        logger.info("🛑 Interrupt detected during response")
        
        if self.realtime_client:
            await self.realtime_client.interrupt_response()
        
        self.state = VoiceState.WAKE_DETECTED
        await self._handle_wake_detected()
    
    # OpenAI Realtime event handlers
    async def _on_realtime_session_created(self, session_data):
        """OpenAI session skapad"""
        self._current_session_id = session_data.get("session", {}).get("id")
        logger.info(f"OpenAI Realtime session created: {self._current_session_id}")
    
    async def _on_transcription_completed(self, transcript: str):
        """Transkription klar från OpenAI"""
        logger.info(f"Transcript: '{transcript}'")
        
        if self.on_transcript_received:
            await self.on_transcript_received(transcript)
    
    async def _on_response_audio_delta(self, audio_data: bytes):
        """Audio response chunk från OpenAI"""
        # I verklig implementation: spela upp audio direkt
        # För nu: bara logga att vi får audio
        if not hasattr(self, '_response_logged'):
            logger.info("🔊 Receiving audio response from OpenAI")
            self._response_logged = True
            
            if self.on_response_started:
                await self.on_response_started()
    
    async def _on_response_done(self, response_data):
        """OpenAI response klar"""
        response_time = time.time() - self._response_start_time if self._response_start_time else 0
        logger.info(f"✅ OpenAI response completed in {response_time*1000:.0f}ms")
        
        if hasattr(self, '_response_logged'):
            delattr(self, '_response_logged')
        
        if self.on_response_completed:
            await self.on_response_completed(response_data)
        
        # Återgå till idle efter response
        self.state = VoiceState.IDLE
    
    async def _on_realtime_error(self, error_msg: str):
        """OpenAI Realtime error"""
        logger.error(f"OpenAI Realtime error: {error_msg}")
        await self._handle_error(error_msg)
    
    async def _handle_error(self, error_msg: str):
        """Generisk error handling"""
        self.state = VoiceState.ERROR
        
        if self.on_error:
            await self.on_error(error_msg)
        
        # Försök återställa till idle efter kort delay
        await asyncio.sleep(1)
        if self._is_running:
            self.state = VoiceState.IDLE
    
    def get_status(self) -> Dict[str, Any]:
        """Hämta system status"""
        status = {
            "state": self.state.value,
            "is_running": self._is_running,
            "config": {
                "wake_phrase": self.config.wake_phrase,
                "wake_sensitivity": self.config.wake_sensitivity,
                "use_realtime_api": self.config.use_realtime_api
            }
        }
        
        if self.realtime_client:
            status["realtime_client"] = {
                "connected": self.realtime_client.is_connected(),
                "state": self.realtime_client.get_connection_state().value,
                "usage_stats": self.realtime_client.get_usage_stats()
            }
        
        return status

# Factory function
def create_always_on_voice(config: VoiceConfig = None) -> AlwaysOnVoiceSystem:
    """Skapa always-on voice system med standardkonfiguration"""
    return AlwaysOnVoiceSystem(config or VoiceConfig())