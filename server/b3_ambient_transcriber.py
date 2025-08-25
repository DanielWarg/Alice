"""
B3 Ambient Transcriber - Real-time ASR for ambient voice processing
Integrates with ImportanceScorer and MemoryIngestion for B3 system
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import base64
import io
import wave
import numpy as np

from pydantic import BaseModel

logger = logging.getLogger("alice.b3_transcriber")

# Import privacy hooks and metrics
try:
    from b3_privacy_hooks import get_b3_privacy_hooks
except ImportError:
    logger.warning("Privacy hooks not available")
    get_b3_privacy_hooks = None

try:
    from b3_metrics import record_asr_latency, record_error
except ImportError:
    logger.warning("B3 metrics not available")
    record_asr_latency = lambda *args, **kwargs: None
    record_error = lambda *args, **kwargs: None

class TranscriptionSegment(BaseModel):
    """Single transcription segment"""
    text: str
    confidence: float
    start_time: float
    end_time: float
    speaker: str = "user"
    language: str = "sv-SE"
    
class ImportanceResult(BaseModel):
    """Result from importance scoring"""
    score: int
    reasons: List[str]
    should_store: bool

class AmbientChunk(BaseModel):
    """Ambient memory chunk for storage"""
    text: str
    ts: str  # ISO timestamp
    conf: float
    speaker: str = "user"
    source: str = "ambient"
    importance: Optional[Dict[str, Any]] = None

class B3AmbientTranscriber:
    """
    Real-time transcriber for B3 ambient voice system
    Handles Swedish speech recognition and integration with importance scoring
    """
    
    def __init__(self):
        self.is_active = False
        self.audio_buffer = []
        self.transcription_buffer = []
        
        # Swedish ASR configuration
        self.language = "sv-SE"
        self.sample_rate = 16000
        self.confidence_threshold = 0.6
        
        # Processing parameters
        self.segment_duration_ms = 2000  # Process every 2 seconds
        self.max_buffer_duration_ms = 30000  # 30 second max buffer
        
        # Import existing importance scorer
        try:
            from web.src.voice.importance import scoreImportance
            self.importance_scorer = scoreImportance
            logger.info("ImportanceScorer loaded successfully")
        except ImportError:
            logger.warning("Could not import ImportanceScorer, using fallback")
            self.importance_scorer = self._fallback_importance_scorer
        
        # Initialize privacy hooks
        self.privacy_hooks = get_b3_privacy_hooks() if get_b3_privacy_hooks else None
            
        # Import ambient memory service
        try:
            from services.ambient_memory import ingest_raw_chunks
            self.memory_ingestor = ingest_raw_chunks
            logger.info("AmbientMemory ingestor loaded successfully")
        except ImportError:
            logger.warning("Could not import AmbientMemory, using mock")
            self.memory_ingestor = self._mock_memory_ingestor
    
    async def start(self):
        """Start ambient transcription"""
        if self.is_active:
            return
            
        self.is_active = True
        self.audio_buffer.clear()
        self.transcription_buffer.clear()
        
        logger.info("B3 Ambient Transcriber started")
        
        # Start processing loop
        asyncio.create_task(self._processing_loop())
    
    async def stop(self):
        """Stop ambient transcription"""
        self.is_active = False
        
        # Process any remaining buffer
        if self.audio_buffer:
            await self._process_accumulated_audio()
        
        logger.info("B3 Ambient Transcriber stopped")
    
    async def process_audio_frame(self, frame_data: np.ndarray, timestamp: float) -> Optional[Dict[str, Any]]:
        """
        Process single audio frame for transcription
        Returns partial transcription result if available
        """
        if not self.is_active:
            return None
            
        # Add frame to buffer with timestamp
        self.audio_buffer.append({
            'data': frame_data,
            'timestamp': timestamp
        })
        
        # Remove old frames to manage memory
        current_time = timestamp
        cutoff_time = current_time - (self.max_buffer_duration_ms / 1000)
        self.audio_buffer = [
            frame for frame in self.audio_buffer 
            if frame['timestamp'] > cutoff_time
        ]
        
        # Check if we have enough audio to process
        if self._get_buffer_duration_ms() >= self.segment_duration_ms:
            return await self._process_accumulated_audio()
        
        return None
    
    async def _processing_loop(self):
        """Background processing loop for transcription"""
        while self.is_active:
            try:
                if len(self.audio_buffer) > 0:
                    await self._process_accumulated_audio()
                
                # Wait before next processing cycle
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in transcription processing loop: {e}")
                await asyncio.sleep(2.0)
    
    async def _process_accumulated_audio(self) -> Optional[Dict[str, Any]]:
        """Process accumulated audio buffer for transcription"""
        if not self.audio_buffer:
            return None
            
        try:
            # Combine audio frames
            audio_data = self._combine_audio_frames()
            
            # Perform transcription
            transcription_result = await self._transcribe_audio(audio_data)
            
            if transcription_result and transcription_result.confidence >= self.confidence_threshold:
                # Check for privacy/forget commands
                if self.privacy_hooks:
                    is_forget_command = await self.privacy_hooks.check_content_for_forget_commands(transcription_result.text)
                    if is_forget_command:
                        logger.info("Forget command detected - processing privacy request")
                        # TODO: Process forget command automatically
                        # For now just flag it
                        transcription_result.text = f"[PRIVACY COMMAND DETECTED] {transcription_result.text}"
                
                # Score importance
                importance_result = await self._score_importance(transcription_result.text)
                
                # Create ambient chunk for memory storage
                if importance_result.should_store:
                    await self._store_ambient_chunk(transcription_result, importance_result)
                
                # Clear processed audio (keep some overlap)
                self._clear_processed_audio()
                
                return {
                    'type': 'transcription_result',
                    'text': transcription_result.text,
                    'confidence': transcription_result.confidence,
                    'importance_score': importance_result.score,
                    'importance_reasons': importance_result.reasons,
                    'will_store': importance_result.should_store,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error processing accumulated audio: {e}")
        
        return None
    
    def _combine_audio_frames(self) -> np.ndarray:
        """Combine audio frames into single array"""
        if not self.audio_buffer:
            return np.array([])
            
        # Concatenate all frame data
        combined = np.concatenate([frame['data'] for frame in self.audio_buffer])
        return combined
    
    async def _transcribe_audio(self, audio_data: np.ndarray) -> Optional[TranscriptionSegment]:
        """
        Transcribe audio data to text using OpenAI Whisper API
        """
        if len(audio_data) == 0:
            return None
            
        try:
            # Calculate audio properties
            duration = len(audio_data) / self.sample_rate
            energy = np.sqrt(np.mean(audio_data ** 2))
            
            # Simple voice activity detection
            if energy < 0.01:  # Too quiet, likely silence
                return None
                
            # Skip very short audio segments
            if duration < 0.5:  # Less than 500ms
                return None
                
            # Try OpenAI Whisper API first
            whisper_result = await self._transcribe_with_openai_whisper(audio_data, duration)
            if whisper_result:
                return whisper_result
                
            # Fallback to local Whisper (if available)
            local_result = await self._transcribe_with_local_whisper(audio_data, duration)
            if local_result:
                return local_result
                
            # Final fallback to mock transcription (for development)
            return await self._mock_transcribe_audio(audio_data, duration, energy)
            
        except Exception as e:
            logger.error(f"Error in transcription: {e}")
            return None
    
    async def _transcribe_with_openai_whisper(self, audio_data: np.ndarray, duration: float) -> Optional[TranscriptionSegment]:
        """Transcribe using OpenAI Whisper API"""
        start_time = time.time()
        try:
            import os
            import tempfile
            import wave
            import httpx
            
            # Check if OpenAI API key is available
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return None
                
            # Convert numpy array to WAV file in memory
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                # Write WAV file
                with wave.open(temp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(self.sample_rate)
                    
                    # Convert float32 to int16
                    audio_int16 = (audio_data * 32767).astype(np.int16)
                    wav_file.writeframes(audio_int16.tobytes())
                
                # Send to OpenAI Whisper API
                async with httpx.AsyncClient(timeout=10.0) as client:
                    with open(temp_file.name, 'rb') as audio_file:
                        files = {
                            'file': ('audio.wav', audio_file, 'audio/wav'),
                            'model': (None, 'whisper-1'),
                            'language': (None, 'sv'),  # Swedish
                            'response_format': (None, 'json'),
                            'temperature': (None, '0.2')  # Low temperature for better accuracy
                        }
                        
                        headers = {
                            'Authorization': f'Bearer {api_key}'
                        }
                        
                        response = await client.post(
                            'https://api.openai.com/v1/audio/transcriptions',
                            files=files,
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            text = result.get('text', '').strip()
                            
                            if text and len(text) > 1:  # Valid transcription
                                # Estimate confidence based on text characteristics
                                confidence = self._estimate_transcription_confidence(text, duration)
                                
                                # Determine speaker (simple heuristic for now)
                                speaker = self._identify_speaker(text)
                                
                                # Record metrics
                                latency_ms = (time.time() - start_time) * 1000
                                record_asr_latency(latency_ms, "sv")
                                
                                return TranscriptionSegment(
                                    text=text,
                                    confidence=confidence,
                                    start_time=self.audio_buffer[0]['timestamp'] if self.audio_buffer else 0,
                                    end_time=self.audio_buffer[-1]['timestamp'] if self.audio_buffer else duration,
                                    speaker=speaker,
                                    language=self.language
                                )
                        else:
                            logger.warning(f"OpenAI Whisper API error: {response.status_code} - {response.text}")
                            return None
                
                # Clean up temp file
                os.unlink(temp_file.name)
                
        except Exception as e:
            logger.error(f"Error with OpenAI Whisper API: {e}")
            return None
    
    async def _transcribe_with_local_whisper(self, audio_data: np.ndarray, duration: float) -> Optional[TranscriptionSegment]:
        """Transcribe using local Whisper (if available)"""
        try:
            # Try to import whisper
            import whisper
            
            # Load model (cache it)
            if not hasattr(self, '_whisper_model'):
                logger.info("Loading local Whisper model...")
                self._whisper_model = whisper.load_model("base")
                
            # Transcribe audio
            result = self._whisper_model.transcribe(
                audio_data, 
                language='sv',
                task='transcribe',
                temperature=0.2
            )
            
            text = result.get('text', '').strip()
            if text and len(text) > 1:
                # Get confidence from segments if available
                segments = result.get('segments', [])
                avg_confidence = 0.8  # Default confidence
                if segments:
                    confidences = [seg.get('no_speech_prob', 0) for seg in segments]
                    avg_confidence = 1.0 - (sum(confidences) / len(confidences))
                
                speaker = self._identify_speaker(text)
                
                return TranscriptionSegment(
                    text=text,
                    confidence=avg_confidence,
                    start_time=self.audio_buffer[0]['timestamp'] if self.audio_buffer else 0,
                    end_time=self.audio_buffer[-1]['timestamp'] if self.audio_buffer else duration,
                    speaker=speaker,
                    language=self.language
                )
                
        except ImportError:
            logger.debug("Local whisper not available")
            return None
        except Exception as e:
            logger.error(f"Error with local Whisper: {e}")
            return None
    
    async def _mock_transcribe_audio(self, audio_data: np.ndarray, duration: float, energy: float) -> TranscriptionSegment:
        """Mock transcription for development/testing"""
        mock_phrases = [
            "Hej Alice, kan du hjälpa mig?",
            "Vad är klockan just nu?",
            "Påminn mig om mötet imorgon",
            "Spela lite musik tack",
            "Hur blir vädret idag?",
            "Lägg till mjölk på inköpslistan",
            "Ring mamma senare",
            "Boka tid hos tandläkaren"
        ]
        
        # Select mock phrase based on energy level
        phrase_index = int(energy * 10) % len(mock_phrases)
        mock_text = mock_phrases[phrase_index]
        
        mock_confidence = min(0.95, max(0.6, energy * 10))
        
        return TranscriptionSegment(
            text=f"[MOCK] {mock_text}",
            confidence=mock_confidence,
            start_time=self.audio_buffer[0]['timestamp'] if self.audio_buffer else 0,
            end_time=self.audio_buffer[-1]['timestamp'] if self.audio_buffer else duration,
            speaker="user",
            language=self.language
        )
    
    def _estimate_transcription_confidence(self, text: str, duration: float) -> float:
        """Estimate transcription confidence based on text characteristics"""
        confidence = 0.8  # Base confidence
        
        # Longer text generally more reliable
        if len(text) > 20:
            confidence += 0.1
        elif len(text) < 5:
            confidence -= 0.2
            
        # Check for Swedish-specific patterns
        swedish_words = ['är', 'och', 'att', 'det', 'som', 'för', 'på', 'av', 'med', 'till']
        swedish_count = sum(1 for word in swedish_words if word in text.lower())
        if swedish_count > 0:
            confidence += 0.05 * swedish_count
            
        # Duration vs text length ratio
        words_per_second = len(text.split()) / max(duration, 0.1)
        if 1 <= words_per_second <= 4:  # Reasonable speaking rate
            confidence += 0.05
            
        return min(0.98, max(0.3, confidence))
    
    def _identify_speaker(self, text: str) -> str:
        """Simple speaker identification (to be enhanced)"""
        # Look for first-person indicators
        first_person_indicators = ['jag', 'mig', 'min', 'mitt', 'mina', 'kommer', 'ska']
        
        if any(indicator in text.lower() for indicator in first_person_indicators):
            return "user"
            
        # Look for Alice-directed speech
        alice_indicators = ['alice', 'hej alice', 'tack alice']
        if any(indicator in text.lower() for indicator in alice_indicators):
            return "user"
            
        return "user"  # Default to user for now
    
    async def _score_importance(self, text: str) -> ImportanceResult:
        """Score importance of transcribed text"""
        try:
            if callable(self.importance_scorer):
                # Use imported importance scorer from TypeScript/JavaScript equivalent
                result = self.importance_scorer(text)
                
                return ImportanceResult(
                    score=result.get('score', 0),
                    reasons=result.get('reasons', []),
                    should_store=result.get('score', 0) >= 2  # Store if score >= 2
                )
            else:
                # Fallback scoring
                return self._fallback_importance_scorer(text)
                
        except Exception as e:
            logger.error(f"Error scoring importance: {e}")
            return ImportanceResult(score=0, reasons=['error'], should_store=False)
    
    async def _store_ambient_chunk(self, transcription: TranscriptionSegment, importance: ImportanceResult):
        """Store ambient chunk in memory system"""
        try:
            chunk = AmbientChunk(
                text=transcription.text,
                ts=datetime.now().isoformat(),
                conf=transcription.confidence,
                speaker=transcription.speaker,
                source="ambient_b3",
                importance={
                    'score': importance.score,
                    'reasons': importance.reasons,
                    'stored_at': datetime.now().isoformat()
                }
            )
            
            # Store in ambient memory
            if callable(self.memory_ingestor):
                await self.memory_ingestor([chunk])
                logger.info(f"Stored ambient chunk: score={importance.score}, text='{transcription.text[:50]}...'")
            else:
                logger.warning("Memory ingestor not available")
                
        except Exception as e:
            logger.error(f"Error storing ambient chunk: {e}")
    
    def _clear_processed_audio(self):
        """Clear processed audio frames, keeping some overlap"""
        if len(self.audio_buffer) > 10:
            # Keep last 10 frames for overlap
            self.audio_buffer = self.audio_buffer[-10:]
    
    def _get_buffer_duration_ms(self) -> float:
        """Get current buffer duration in milliseconds"""
        if len(self.audio_buffer) < 2:
            return 0
            
        start_time = self.audio_buffer[0]['timestamp']
        end_time = self.audio_buffer[-1]['timestamp']
        return (end_time - start_time) * 1000
    
    def _fallback_importance_scorer(self, text: str) -> ImportanceResult:
        """Fallback importance scorer if main one is not available"""
        score = 0
        reasons = []
        
        # Basic heuristics
        if len(text) > 20:
            score += 1
            reasons.append('sufficient_length')
            
        # Check for numbers, names, etc.
        if any(char.isdigit() for char in text):
            score += 1
            reasons.append('contains_numbers')
            
        # Check for Swedish action words
        action_words = ['ska', 'kommer', 'behöver', 'måste', 'planerar', 'tänker']
        if any(word in text.lower() for word in action_words):
            score += 1
            reasons.append('action_words')
        
        return ImportanceResult(
            score=min(3, score),
            reasons=reasons,
            should_store=score >= 2
        )
    
    async def _real_memory_ingestor(self, chunks: List[AmbientChunk]):
        """Real memory ingestor - stores important chunks in database"""
        try:
            from services.ambient_memory import get_ambient_memory_service
            memory_service = get_ambient_memory_service()
            
            stored_count = 0
            for chunk in chunks:
                if chunk.importance and chunk.importance.get('should_store', False):
                    try:
                        await memory_service.store_ambient_chunk({
                            'text': chunk.text,
                            'timestamp': chunk.timestamp.isoformat(),
                            'importance_score': chunk.importance.get('score', 0),
                            'reasons': chunk.importance.get('reasons', []),
                            'source': 'b3_ambient'
                        })
                        stored_count += 1
                        logger.debug(f"Stored chunk: {chunk.text[:50]}... (score: {chunk.importance.get('score')})")
                    except Exception as e:
                        logger.warning(f"Failed to store chunk: {e}")
            
            logger.info(f"Memory ingestor: stored {stored_count}/{len(chunks)} chunks")
            
        except ImportError:
            logger.warning("Ambient memory service not available, using fallback storage")
            # Fallback to simple logging for now
            logger.info(f"Fallback memory ingestor: would store {len(chunks)} chunks")
            for chunk in chunks:
                if chunk.importance and chunk.importance.get('should_store', False):
                    logger.info(f"Important: {chunk.text[:50]}... (score: {chunk.importance.get('score')})")
                    
        except Exception as e:
            logger.error(f"Memory ingestion failed: {e}")
            # Don't crash, just log the error

# Global instance
_ambient_transcriber = None

def get_b3_ambient_transcriber():
    """Get singleton B3 ambient transcriber"""
    global _ambient_transcriber
    if _ambient_transcriber is None:
        _ambient_transcriber = B3AmbientTranscriber()
    return _ambient_transcriber