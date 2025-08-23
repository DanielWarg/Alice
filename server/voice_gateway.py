"""
Alice Voice-Gateway - Hybrid Voice Architecture Phase 1
Central orchestration hub for all voice interactions

Combines OpenAI Realtime API with local AI thinking for optimal performance
"""

import asyncio
import json
import time
import base64
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import httpx
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
import logging

from core.router import classify
from core.tool_registry import validate_and_execute_tool, enabled_tools
from memory import MemoryStore

logger = logging.getLogger("alice.voice_gateway")

class VoiceState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"

class ProcessingPath(Enum):
    FAST = "fast"
    THINK = "think"
    HYBRID = "hybrid"

@dataclass
class AudioChunk:
    """Audio chunk with metadata"""
    data: bytes
    timestamp: float
    format: str
    sample_rate: int
    channels: int
    energy_level: float = 0.0

@dataclass
class VoiceActivity:
    """Voice activity detection result"""
    is_speech: bool
    confidence: float
    energy_level: float
    timestamp: float

@dataclass
class IntentResult:
    """Intent classification result"""
    intent: str
    confidence: float
    path: ProcessingPath
    reasoning: str
    slots: Dict[str, Any] = None

@dataclass
class TelemetryData:
    """Telemetry data for UI updates"""
    voice_state: VoiceState
    energy_level: float
    processing_path: Optional[ProcessingPath] = None
    intent_confidence: float = 0.0
    latency_ms: float = 0.0

class VoiceGatewayManager:
    """
    Central orchestration hub for Alice's hybrid voice architecture.
    
    Manages WebSocket connections, audio processing, intent routing,
    and coordination between fast responses and local AI thinking.
    """
    
    def __init__(self, memory_store: MemoryStore):
        self.memory = memory_store
        self.active_sessions = {}
        self.api_client = httpx.AsyncClient(timeout=30.0)
        
        # Audio processing configuration
        self.audio_config = {
            "sample_rate": 24000,
            "channels": 1,
            "format": "pcm16",
            "chunk_size_ms": 100,
            "buffer_size_ms": 500
        }
        
        # VAD configuration
        self.vad_config = {
            "energy_threshold": 0.01,
            "speech_threshold": 0.6,
            "silence_duration_ms": 800,
            "min_speech_duration_ms": 300
        }
        
        # Intent routing thresholds
        self.routing_config = {
            "fast_confidence_threshold": 0.85,
            "think_confidence_threshold": 0.5,
            "max_fast_latency_ms": 300,
            "max_think_latency_ms": 2000
        }
        
        # Audio buffers and state
        self.audio_buffers = {}
        self.vad_states = {}
        
    async def handle_voice_gateway_session(self, websocket: WebSocket, session_id: str):
        """Handle Voice-Gateway WebSocket session with enhanced features"""
        await websocket.accept()
        
        try:
            # Initialize session
            self.active_sessions[session_id] = {
                "websocket": websocket,
                "start_time": datetime.now(),
                "voice_state": VoiceState.IDLE,
                "audio_buffer": [],
                "conversation_context": [],
                "processing_path": None,
                "current_intent": None
            }
            
            # Initialize audio buffer and VAD state
            self.audio_buffers[session_id] = AudioBuffer(
                max_duration_ms=self.audio_config["buffer_size_ms"]
            )
            self.vad_states[session_id] = VADState()
            
            logger.info(f"Voice Gateway session started: {session_id}")
            
            # Send initial status
            await self._send_telemetry(websocket, session_id, VoiceState.IDLE, 0.0)
            
            while True:
                try:
                    # Receive message from frontend
                    data = await websocket.receive_json()
                    
                    # Route message based on type
                    await self._handle_gateway_message(websocket, session_id, data)
                    
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Error in voice gateway session {session_id}: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Ett fel uppstod i voice gateway",
                        "details": str(e)
                    })
                    
        finally:
            # Cleanup session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            if session_id in self.audio_buffers:
                del self.audio_buffers[session_id]
            if session_id in self.vad_states:
                del self.vad_states[session_id]
            
            await self.api_client.aclose()
            logger.info(f"Voice Gateway session ended: {session_id}")
    
    async def _handle_gateway_message(self, websocket: WebSocket, session_id: str, data: Dict[str, Any]):
        """Handle incoming messages from frontend Voice Gateway Client"""
        message_type = data.get("type")
        
        if message_type == "audio.start":
            await self._handle_audio_start(websocket, session_id, data)
            
        elif message_type == "audio.chunk":
            await self._handle_audio_chunk(websocket, session_id, data)
            
        elif message_type == "audio.stop":
            await self._handle_audio_stop(websocket, session_id, data)
            
        elif message_type == "control.interrupt":
            await self._handle_interrupt(websocket, session_id, data)
            
        elif message_type == "control.configure":
            await self._handle_configure(websocket, session_id, data)
            
        elif message_type == "ping":
            await websocket.send_json({"type": "pong", "timestamp": time.time()})
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
            await websocket.send_json({
                "type": "error",
                "message": f"Okänd meddelandetyp: {message_type}"
            })
    
    async def _handle_audio_start(self, websocket: WebSocket, session_id: str, data: Dict[str, Any]):
        """Handle audio stream start"""
        session = self.active_sessions[session_id]
        session["voice_state"] = VoiceState.LISTENING
        
        # Reset audio buffer
        self.audio_buffers[session_id].clear()
        self.vad_states[session_id].reset()
        
        # Send telemetry update
        await self._send_telemetry(websocket, session_id, VoiceState.LISTENING, 0.0)
        
        logger.info(f"Audio stream started for session {session_id}")
    
    async def _handle_audio_chunk(self, websocket: WebSocket, session_id: str, data: Dict[str, Any]):
        """Handle incoming audio chunk with VAD and processing"""
        try:
            # Decode audio data
            audio_data = base64.b64decode(data.get("audio", ""))
            timestamp = data.get("timestamp", time.time())
            
            # Create audio chunk
            chunk = AudioChunk(
                data=audio_data,
                timestamp=timestamp,
                format=data.get("format", "pcm16"),
                sample_rate=data.get("sample_rate", 24000),
                channels=data.get("channels", 1)
            )
            
            # Calculate energy level for telemetry
            energy_level = self._calculate_energy_level(chunk)
            chunk.energy_level = energy_level
            
            # Add to buffer
            self.audio_buffers[session_id].add_chunk(chunk)
            
            # Perform Voice Activity Detection
            vad_result = self._perform_vad(chunk, self.vad_states[session_id])
            
            # Send energy telemetry for UI ring animation
            await self._send_telemetry(websocket, session_id, VoiceState.LISTENING, energy_level)
            
            # Check if speech detected and enough audio accumulated
            if vad_result.is_speech and self.audio_buffers[session_id].has_sufficient_audio():
                await self._process_speech_detection(websocket, session_id, vad_result)
            
        except Exception as e:
            logger.error(f"Error handling audio chunk: {e}")
            await websocket.send_json({
                "type": "error",
                "message": "Fel vid behandling av audio chunk"
            })
    
    async def _handle_audio_stop(self, websocket: WebSocket, session_id: str, data: Dict[str, Any]):
        """Handle audio stream stop and process accumulated audio"""
        session = self.active_sessions[session_id]
        session["voice_state"] = VoiceState.PROCESSING
        
        # Send processing telemetry
        await self._send_telemetry(websocket, session_id, VoiceState.PROCESSING, 0.0)
        
        # Process accumulated audio buffer
        if self.audio_buffers[session_id].has_audio():
            await self._process_accumulated_audio(websocket, session_id)
        else:
            # No audio to process, return to idle
            session["voice_state"] = VoiceState.IDLE
            await self._send_telemetry(websocket, session_id, VoiceState.IDLE, 0.0)
        
        logger.info(f"Audio stream stopped for session {session_id}")
    
    async def _handle_interrupt(self, websocket: WebSocket, session_id: str, data: Dict[str, Any]):
        """Handle barge-in interrupt (stop current TTS/processing)"""
        session = self.active_sessions[session_id]
        
        # Stop any current processing or speaking
        if session["voice_state"] in [VoiceState.SPEAKING, VoiceState.THINKING]:
            session["voice_state"] = VoiceState.IDLE
            
            await websocket.send_json({
                "type": "interrupted",
                "message": "Avbruten av användare",
                "timestamp": time.time()
            })
            
            await self._send_telemetry(websocket, session_id, VoiceState.IDLE, 0.0)
            
        logger.info(f"Interrupt handled for session {session_id}")
    
    async def _handle_configure(self, websocket: WebSocket, session_id: str, data: Dict[str, Any]):
        """Handle configuration updates"""
        config = data.get("config", {})
        
        # Update audio configuration if provided
        if "audio" in config:
            self.audio_config.update(config["audio"])
            
        # Update VAD configuration if provided
        if "vad" in config:
            self.vad_config.update(config["vad"])
            
        # Update routing configuration if provided
        if "routing" in config:
            self.routing_config.update(config["routing"])
            
        await websocket.send_json({
            "type": "configured",
            "config": {
                "audio": self.audio_config,
                "vad": self.vad_config,
                "routing": self.routing_config
            }
        })
        
        logger.info(f"Configuration updated for session {session_id}")
    
    def _calculate_energy_level(self, chunk: AudioChunk) -> float:
        """Calculate audio energy level for VAD and telemetry"""
        try:
            # Convert PCM16 bytes to numpy array
            audio_samples = np.frombuffer(chunk.data, dtype=np.int16)
            
            # Calculate RMS energy
            if len(audio_samples) > 0:
                rms = np.sqrt(np.mean(audio_samples.astype(np.float32) ** 2))
                # Normalize to 0-1 range
                normalized_energy = min(1.0, rms / 32768.0)
                return normalized_energy
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating energy level: {e}")
            return 0.0
    
    def _perform_vad(self, chunk: AudioChunk, vad_state: 'VADState') -> VoiceActivity:
        """Perform Voice Activity Detection on audio chunk"""
        energy = chunk.energy_level
        
        # Simple energy-based VAD
        is_speech = energy > self.vad_config["energy_threshold"]
        
        # Update VAD state
        vad_state.update(is_speech, energy, chunk.timestamp)
        
        # Determine final speech decision based on continuity
        final_is_speech = vad_state.is_stable_speech(
            self.vad_config["speech_threshold"],
            self.vad_config["min_speech_duration_ms"]
        )
        
        return VoiceActivity(
            is_speech=final_is_speech,
            confidence=min(1.0, energy * 2.0),  # Simple confidence score
            energy_level=energy,
            timestamp=chunk.timestamp
        )
    
    async def _process_speech_detection(self, websocket: WebSocket, session_id: str, vad_result: VoiceActivity):
        """Process detected speech and start intent classification"""
        session = self.active_sessions[session_id]
        session["voice_state"] = VoiceState.PROCESSING
        
        # Send processing telemetry
        await self._send_telemetry(websocket, session_id, VoiceState.PROCESSING, vad_result.energy_level)
        
        # Get accumulated audio for transcription
        audio_data = self.audio_buffers[session_id].get_combined_audio()
        
        # Process in background
        asyncio.create_task(self._transcribe_and_process(websocket, session_id, audio_data))
    
    async def _process_accumulated_audio(self, websocket: WebSocket, session_id: str):
        """Process accumulated audio when stream stops"""
        audio_data = self.audio_buffers[session_id].get_combined_audio()
        
        if len(audio_data) > 0:
            # Process in background
            asyncio.create_task(self._transcribe_and_process(websocket, session_id, audio_data))
    
    async def _transcribe_and_process(self, websocket: WebSocket, session_id: str, audio_data: bytes):
        """Transcribe audio and process through intent routing"""
        try:
            start_time = time.time()
            
            # Transcribe audio (placeholder - integrate with existing Whisper/STT)
            transcription = await self._transcribe_audio(audio_data)
            
            if not transcription.strip():
                # No speech detected, return to idle
                session = self.active_sessions[session_id]
                session["voice_state"] = VoiceState.IDLE
                await self._send_telemetry(websocket, session_id, VoiceState.IDLE, 0.0)
                return
            
            # Send transcription to frontend
            await websocket.send_json({
                "type": "transcription",
                "text": transcription,
                "timestamp": time.time(),
                "latency_ms": (time.time() - start_time) * 1000
            })
            
            # Perform intent classification and routing
            intent_result = await self._classify_and_route_intent(transcription)
            
            # Update session state
            session = self.active_sessions[session_id]
            session["current_intent"] = intent_result
            session["processing_path"] = intent_result.path
            
            # Send routing decision telemetry
            await self._send_telemetry(
                websocket, session_id, 
                VoiceState.THINKING if intent_result.path == ProcessingPath.THINK else VoiceState.PROCESSING,
                0.0, intent_result.path, intent_result.confidence
            )
            
            # Route to appropriate processing path
            if intent_result.path == ProcessingPath.FAST:
                await self._handle_fast_path(websocket, session_id, transcription, intent_result)
            elif intent_result.path == ProcessingPath.THINK:
                await self._handle_think_path(websocket, session_id, transcription, intent_result)
            else:  # HYBRID
                await self._handle_hybrid_path(websocket, session_id, transcription, intent_result)
                
        except Exception as e:
            logger.error(f"Error in transcription and processing: {e}")
            await websocket.send_json({
                "type": "error",
                "message": "Fel vid transkribering och bearbetning"
            })
            
            # Return to idle state
            session = self.active_sessions[session_id]
            session["voice_state"] = VoiceState.IDLE
            await self._send_telemetry(websocket, session_id, VoiceState.IDLE, 0.0)
    
    async def _transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio using existing Whisper integration"""
        try:
            from voice_stt import get_whisper_model
            import tempfile
            import os
            
            # Check if we have a Whisper model available
            model = get_whisper_model()
            if model is None:
                logger.warning("Whisper model not available, skipping transcription")
                return ""
            
            # Check if audio_data is valid
            if not audio_data or len(audio_data) < 1000:  # Less than ~50ms at 24kHz PCM16
                return ""
            
            # Create temporary WAV file from PCM16 audio data
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                # Write PCM16 data as simple WAV file
                import struct
                import wave
                
                # Create WAV file header for PCM16, mono, 24kHz
                with wave.open(temp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit = 2 bytes
                    wav_file.setframerate(24000)  # 24kHz sample rate
                    wav_file.writeframes(audio_data)
                
                temp_filename = temp_file.name
            
            try:
                # Transcribe with Swedish optimizations
                segments, info = model.transcribe(
                    temp_filename,
                    language="sv",
                    beam_size=3,  # Lower beam size for speed
                    temperature=0.0,
                    condition_on_previous_text=False,  # Disable for short clips
                    initial_prompt="Svenskt tal med kommandon till Alice AI-assistenten."
                )
                
                # Extract text from segments
                transcription_text = ""
                for segment in segments:
                    clean_text = segment.text.strip()
                    if clean_text:
                        transcription_text += clean_text + " "
                
                result = transcription_text.strip()
                
                # Log successful transcription
                if result:
                    logger.info(f"Voice-Gateway transcription: '{result[:50]}...' ({len(result)} chars)")
                
                return result
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_filename)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Voice-Gateway transcription error: {e}")
            return ""
    
    async def _classify_and_route_intent(self, text: str) -> IntentResult:
        """Classify intent and determine processing path"""
        # Use existing classification system
        router_result = classify(text)
        
        if router_result and router_result.get("confidence", 0) >= self.routing_config["fast_confidence_threshold"]:
            # High confidence - route to fast path for simple responses
            if router_result["tool"] in ["GREETING", "ACKNOWLEDGMENT", "SIMPLE_QUESTION", "WEATHER", "TIME_DATE"]:
                return IntentResult(
                    intent=router_result["tool"],
                    confidence=router_result["confidence"],
                    path=ProcessingPath.FAST,
                    reasoning="high_confidence_simple_intent",
                    slots=router_result.get("args", {})
                )
            else:
                # High confidence but complex tool - route to think path
                return IntentResult(
                    intent=router_result["tool"],
                    confidence=router_result["confidence"],
                    path=ProcessingPath.THINK,
                    reasoning="high_confidence_complex_intent",
                    slots=router_result.get("args", {})
                )
        
        elif router_result and router_result.get("confidence", 0) >= self.routing_config["think_confidence_threshold"]:
            # Medium confidence - route to think path for safety
            return IntentResult(
                intent=router_result.get("tool", "GENERAL"),
                confidence=router_result["confidence"],
                path=ProcessingPath.THINK,
                reasoning="medium_confidence_safety_routing",
                slots=router_result.get("args", {})
            )
        
        else:
            # Low or no confidence - route to think path for local processing
            return IntentResult(
                intent="GENERAL",
                confidence=router_result.get("confidence", 0.0) if router_result else 0.0,
                path=ProcessingPath.THINK,
                reasoning="low_confidence_local_processing",
                slots={}
            )
    
    async def _handle_fast_path(self, websocket: WebSocket, session_id: str, text: str, intent: IntentResult):
        """Handle fast path processing (simple responses)"""
        session = self.active_sessions[session_id]
        session["voice_state"] = VoiceState.SPEAKING
        
        # Send acknowledgment immediately
        await websocket.send_json({
            "type": "acknowledge",
            "message": "Okej, jag hjälper dig",
            "path": "fast",
            "intent": intent.intent,
            "confidence": intent.confidence
        })
        
        # Generate simple response (placeholder)
        response_text = await self._generate_fast_response(text, intent)
        
        # Send response
        await websocket.send_json({
            "type": "response",
            "text": response_text,
            "path": "fast",
            "final": True
        })
        
        # Return to idle
        session["voice_state"] = VoiceState.IDLE
        await self._send_telemetry(websocket, session_id, VoiceState.IDLE, 0.0)
    
    async def _handle_think_path(self, websocket: WebSocket, session_id: str, text: str, intent: IntentResult):
        """Handle think path processing (local AI + tools)"""
        session = self.active_sessions[session_id]
        session["voice_state"] = VoiceState.THINKING
        
        # Send thinking status
        await websocket.send_json({
            "type": "thinking",
            "message": "Alice tänker...",
            "path": "think",
            "intent": intent.intent,
            "confidence": intent.confidence
        })
        
        # Process with local AI (integrate with existing voice_stream.py logic)
        response_text = await self._generate_think_response(text, intent, session_id)
        
        # Send response
        await websocket.send_json({
            "type": "response", 
            "text": response_text,
            "path": "think",
            "final": True
        })
        
        # Return to idle
        session["voice_state"] = VoiceState.IDLE
        await self._send_telemetry(websocket, session_id, VoiceState.IDLE, 0.0)
    
    async def _handle_hybrid_path(self, websocket: WebSocket, session_id: str, text: str, intent: IntentResult):
        """Handle hybrid path processing (start fast, escalate if needed)"""
        # Start with fast path
        await self._handle_fast_path(websocket, session_id, text, intent)
        
        # TODO: Add logic to escalate to think path if fast response is insufficient
    
    async def _generate_fast_response(self, text: str, intent: IntentResult) -> str:
        """Generate fast response for simple intents"""
        # Placeholder for fast response generation
        responses = {
            "GREETING": "Hej! Hur kan jag hjälpa dig?",
            "ACKNOWLEDGMENT": "Okej, jag förstår.",
            "SIMPLE_QUESTION": "Det är en intressant fråga.",
            "DEFAULT": "Jag hör vad du säger."
        }
        
        return responses.get(intent.intent, responses["DEFAULT"])
    
    async def _generate_think_response(self, text: str, intent: IntentResult, session_id: str) -> str:
        """Generate response using local AI and tools"""
        # Integrate with existing voice_stream.py logic
        try:
            # Check if it's a tool command
            if intent.intent in enabled_tools():
                # Execute tool locally
                result = await validate_and_execute_tool(intent.intent, intent.slots or {})
                
                if result.get("success"):
                    return result.get("message", "Kommandot utfört!")
                else:
                    return result.get("error", "Ett fel uppstod vid verktygsexekvering.")
            
            # Otherwise, generate conversational response
            return "Jag bearbetar din begäran och kommer tillbaka med ett svar."
            
        except Exception as e:
            logger.error(f"Error in think response generation: {e}")
            return "Ursäkta, jag hade problem med att behandla din begäran."
    
    async def _send_telemetry(self, websocket: WebSocket, session_id: str, voice_state: VoiceState, 
                            energy_level: float, processing_path: Optional[ProcessingPath] = None, 
                            intent_confidence: float = 0.0, latency_ms: float = 0.0):
        """Send telemetry data for UI updates"""
        telemetry = TelemetryData(
            voice_state=voice_state,
            energy_level=energy_level,
            processing_path=processing_path,
            intent_confidence=intent_confidence,
            latency_ms=latency_ms
        )
        
        await websocket.send_json({
            "type": "telemetry",
            "data": {
                "voice_state": voice_state.value,
                "energy_level": energy_level,
                "processing_path": processing_path.value if processing_path else None,
                "intent_confidence": intent_confidence,
                "latency_ms": latency_ms,
                "timestamp": time.time()
            }
        })


class AudioBuffer:
    """Audio buffer for accumulating audio chunks"""
    
    def __init__(self, max_duration_ms: int = 5000):
        self.chunks: List[AudioChunk] = []
        self.max_duration_ms = max_duration_ms
        
    def add_chunk(self, chunk: AudioChunk):
        """Add audio chunk to buffer"""
        self.chunks.append(chunk)
        
        # Remove old chunks if buffer is too long
        if len(self.chunks) > 0:
            oldest_time = self.chunks[-1].timestamp - (self.max_duration_ms / 1000.0)
            self.chunks = [c for c in self.chunks if c.timestamp >= oldest_time]
    
    def clear(self):
        """Clear audio buffer"""
        self.chunks = []
    
    def has_audio(self) -> bool:
        """Check if buffer has any audio"""
        return len(self.chunks) > 0
    
    def has_sufficient_audio(self, min_duration_ms: int = 300) -> bool:
        """Check if buffer has sufficient audio for processing"""
        if not self.chunks:
            return False
            
        duration_ms = (self.chunks[-1].timestamp - self.chunks[0].timestamp) * 1000
        return duration_ms >= min_duration_ms
    
    def get_combined_audio(self) -> bytes:
        """Get combined audio data from all chunks"""
        if not self.chunks:
            return b""
            
        return b"".join(chunk.data for chunk in self.chunks)


class VADState:
    """Voice Activity Detection state tracker"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset VAD state"""
        self.speech_frames = []
        self.last_speech_time = 0.0
        self.consecutive_speech = 0
        self.consecutive_silence = 0
    
    def update(self, is_speech: bool, energy: float, timestamp: float):
        """Update VAD state with new frame"""
        self.speech_frames.append({
            "is_speech": is_speech,
            "energy": energy,
            "timestamp": timestamp
        })
        
        # Keep only recent frames (last 2 seconds)
        cutoff_time = timestamp - 2.0
        self.speech_frames = [f for f in self.speech_frames if f["timestamp"] >= cutoff_time]
        
        # Update counters
        if is_speech:
            self.consecutive_speech += 1
            self.consecutive_silence = 0
            self.last_speech_time = timestamp
        else:
            self.consecutive_silence += 1
            self.consecutive_speech = 0
    
    def is_stable_speech(self, threshold: float = 0.6, min_duration_ms: int = 300) -> bool:
        """Check if we have stable speech activity"""
        if not self.speech_frames:
            return False
        
        # Check if we have minimum duration
        if len(self.speech_frames) == 0:
            return False
            
        duration_ms = (self.speech_frames[-1]["timestamp"] - self.speech_frames[0]["timestamp"]) * 1000
        if duration_ms < min_duration_ms:
            return False
        
        # Check speech ratio
        speech_count = sum(1 for f in self.speech_frames if f["is_speech"])
        speech_ratio = speech_count / len(self.speech_frames)
        
        return speech_ratio >= threshold


# Global voice gateway manager instance
voice_gateway_manager = None

def get_voice_gateway_manager(memory_store: MemoryStore) -> VoiceGatewayManager:
    """Get or create voice gateway manager instance"""
    global voice_gateway_manager
    if voice_gateway_manager is None:
        voice_gateway_manager = VoiceGatewayManager(memory_store)
    return voice_gateway_manager