#!/usr/bin/env python3
"""
🔊 Dummy TTS Adapter for Testing
Skapar syntetisk audio för att testa pipeline utan Piper-beroende
Används för att validera TTS-integration och streaming-logik
"""

import asyncio
import logging
import time
import numpy as np
from typing import Optional, Dict, Any, Callable, AsyncIterator
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)

@dataclass
class TTSConfig:
    """TTS configuration parameters"""
    model_path: str = "dummy"
    
    # Audio parameters
    sample_rate: int = 16000  # Match voice pipeline
    channels: int = 1  # Mono
    
    # Streaming parameters  
    chunk_ms: int = 60  # Target chunk duration
    max_text_length: int = 200  # Split long texts
    
    # Performance tuning
    speed: float = 1.0  # Speaking rate
    
    # Phrase splitting for streaming
    sentence_split: bool = True
    split_on_punctuation: list = None
    
    def __post_init__(self):
        if self.split_on_punctuation is None:
            self.split_on_punctuation = ['.', '!', '?', ',', ';', ':']

@dataclass
class TTSResult:
    """TTS generation result"""
    audio_chunk: np.ndarray
    is_final: bool
    chunk_index: int
    total_chunks: int
    generation_ms: float
    text_processed: str
    
    # Performance metrics
    time_to_first_chunk_ms: float = 0.0
    total_generation_time_ms: float = 0.0

class StreamingTTS:
    """Dummy Streaming TTS engine för pipeline testing"""
    
    def __init__(self, config: TTSConfig):
        self.config = config
        self.is_initialized = False
        
        # Performance tracking
        self.stats = {
            "total_requests": 0,
            "total_audio_generated_seconds": 0.0,
            "avg_first_chunk_ms": 0.0,
            "avg_generation_speed": 0.0,  # chars/second
            "model_warm": False,
            "initialization_time_ms": 0.0
        }
        
        # Callbacks
        self.on_chunk: Optional[Callable[[TTSResult], None]] = None
        self.on_complete: Optional[Callable[[TTSResult], None]] = None
        
        logger.info(f"Dummy StreamingTTS initialized")
    
    async def initialize(self) -> None:
        """Initialize TTS model and warm up"""
        start_time = time.time()
        
        try:
            # Simulate initialization delay
            await asyncio.sleep(0.1)
            
            init_time = (time.time() - start_time) * 1000
            self.stats["initialization_time_ms"] = init_time
            self.stats["model_warm"] = True
            self.is_initialized = True
            
            logger.info(f"✅ Dummy TTS initialized in {init_time:.1f}ms")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Dummy TTS: {e}")
            raise
    
    async def generate_speech(self, text: str, session_id: str = "default") -> AsyncIterator[TTSResult]:
        """Generate streaming dummy speech from text"""
        if not self.is_initialized:
            raise RuntimeError("TTS not initialized")
        
        if not text or not text.strip():
            return
        
        start_time = time.time()
        first_chunk_time = None
        
        logger.info(f"🔊 Generating dummy speech for session {session_id}: '{text[:50]}...'")
        
        try:
            # Split text into chunks for streaming
            text_chunks = self._split_text_for_streaming(text.strip())
            
            total_chunks = len(text_chunks)
            logger.debug(f"   Split into {total_chunks} chunks: {[chunk[:20]+'...' for chunk in text_chunks]}")
            
            for chunk_idx, text_chunk in enumerate(text_chunks):
                chunk_start = time.time()
                
                # Generate dummy audio for this chunk
                audio_data = await self._generate_dummy_audio(text_chunk)
                
                if audio_data is not None and len(audio_data) > 0:
                    chunk_time = (time.time() - chunk_start) * 1000
                    
                    if first_chunk_time is None:
                        first_chunk_time = (time.time() - start_time) * 1000
                        logger.info(f"🎯 First TTS chunk in {first_chunk_time:.1f}ms")
                    
                    is_final_chunk = (chunk_idx == total_chunks - 1)
                    
                    result = TTSResult(
                        audio_chunk=audio_data,
                        is_final=is_final_chunk,
                        chunk_index=chunk_idx,
                        total_chunks=total_chunks,
                        generation_ms=chunk_time,
                        text_processed=text_chunk,
                        time_to_first_chunk_ms=first_chunk_time or 0,
                        total_generation_time_ms=(time.time() - start_time) * 1000
                    )
                    
                    # Call callbacks
                    if self.on_chunk:
                        self.on_chunk(result)
                    
                    yield result
                    
                    logger.debug(f"   Chunk {chunk_idx+1}/{total_chunks}: {len(audio_data)} samples, {chunk_time:.1f}ms")
                    
                    # Final chunk callback
                    if is_final_chunk and self.on_complete:
                        self.on_complete(result)
                
                else:
                    logger.warning(f"No dummy audio generated for chunk: '{text_chunk}'")
            
            # Update statistics
            total_time = time.time() - start_time
            self._update_stats(text, first_chunk_time, total_time)
            
            # Final completion callback if we have chunks
            if text_chunks and self.on_complete:
                final_result = TTSResult(
                    audio_chunk=np.array([]),
                    is_final=True,
                    chunk_index=len(text_chunks)-1,
                    total_chunks=len(text_chunks),
                    generation_ms=total_time * 1000,
                    text_processed=text,
                    time_to_first_chunk_ms=first_chunk_time or 0,
                    total_generation_time_ms=total_time * 1000
                )
                self.on_complete(final_result)
            
            logger.info(f"✅ Dummy TTS complete: {len(text)} chars in {total_time*1000:.1f}ms "
                       f"(TTFC={first_chunk_time:.1f}ms)")
                       
        except Exception as e:
            logger.error(f"❌ Dummy TTS generation error: {e}")
            raise
    
    def _split_text_for_streaming(self, text: str) -> list[str]:
        """Split text into chunks suitable for streaming"""
        if not self.config.sentence_split:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split on punctuation for natural pauses
        words = text.split()
        
        for word in words:
            # Check if adding this word would make chunk too long
            test_chunk = current_chunk + " " + word if current_chunk else word
            
            if len(test_chunk) > self.config.max_text_length and current_chunk:
                # Chunk is getting too long, start a new one
                chunks.append(current_chunk.strip())
                current_chunk = word
            else:
                current_chunk = test_chunk
                
            # Check for natural breakpoints
            if any(punct in word for punct in self.config.split_on_punctuation):
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
        
        # Add remaining text
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Ensure we have at least one chunk
        if not chunks:
            chunks = [text]
            
        return chunks
    
    async def _generate_dummy_audio(self, text: str) -> Optional[np.ndarray]:
        """Generate dummy audio data för text"""
        if not text.strip():
            return None
        
        try:
            # Simulate some processing time based on text length
            processing_time = len(text) * 0.002  # ~2ms per character 
            await asyncio.sleep(processing_time)
            
            # Generate dummy audio: simple sine wave based on text
            duration_seconds = len(text) * 0.05  # ~50ms per character
            samples = int(duration_seconds * self.config.sample_rate)
            
            # Create a simple tone based on text hash for variety
            frequency = 200 + (hash(text) % 400)  # 200-600 Hz
            t = np.linspace(0, duration_seconds, samples, False)
            
            # Generate sine wave with envelope for natural sound
            envelope = np.exp(-t * 2)  # Decay envelope
            audio_data = 0.3 * envelope * np.sin(2 * np.pi * frequency * t)
            
            # Add some variation
            if len(text) > 10:
                # Add harmonics for longer text
                audio_data += 0.1 * envelope * np.sin(4 * np.pi * frequency * t)
            
            return audio_data.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error generating dummy audio: {e}")
            return None
    
    def _update_stats(self, text: str, first_chunk_ms: Optional[float], total_time: float) -> None:
        """Update performance statistics"""
        self.stats["total_requests"] += 1
        
        if first_chunk_ms is not None:
            requests = self.stats["total_requests"]
            current_avg = self.stats["avg_first_chunk_ms"]
            self.stats["avg_first_chunk_ms"] = (current_avg * (requests - 1) + first_chunk_ms) / requests
        
        # Update generation speed (chars/second)
        if total_time > 0:
            chars_per_sec = len(text) / total_time
            requests = self.stats["total_requests"]
            current_avg = self.stats["avg_generation_speed"]
            self.stats["avg_generation_speed"] = (current_avg * (requests - 1) + chars_per_sec) / requests
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            **self.stats,
            "is_initialized": self.is_initialized,
            "model_path": "dummy"
        }

# Factory function
def create_streaming_tts(
    on_chunk: Optional[Callable[[TTSResult], None]] = None,
    on_complete: Optional[Callable[[TTSResult], None]] = None,
    config: Optional[TTSConfig] = None
) -> StreamingTTS:
    """Create and configure dummy streaming TTS"""
    if config is None:
        config = TTSConfig()
    
    tts = StreamingTTS(config)
    tts.on_chunk = on_chunk
    tts.on_complete = on_complete
    
    return tts

# Test function
async def test_dummy_tts():
    """Test dummy streaming TTS"""
    logger.info("🧪 Testing Dummy Streaming TTS...")
    
    chunks_received = []
    
    def on_chunk(result: TTSResult):
        chunks_received.append(result)
        logger.info(f"Dummy TTS Chunk {result.chunk_index+1}/{result.total_chunks}: "
                   f"{len(result.audio_chunk)} samples, {result.generation_ms:.1f}ms")
    
    def on_complete(result: TTSResult):
        logger.info(f"Dummy TTS Complete: '{result.text_processed}' "
                   f"(TTFC={result.time_to_first_chunk_ms:.1f}ms, "
                   f"Total={result.total_generation_time_ms:.1f}ms)")
    
    # Create TTS
    config = TTSConfig()
    tts = create_streaming_tts(on_chunk, on_complete, config)
    
    try:
        # Initialize
        await tts.initialize()
        
        # Test phrases
        test_phrases = [
            "Hej Alice, hur mår du idag?",
            "Det här är ett test av dummy text-till-tal systemet.",
            "Kan du generera syntetiskt ljud från denna text på svenska?"
        ]
        
        for phrase in test_phrases:
            logger.info(f"\n🔸 Testing phrase: '{phrase}'")
            chunks_received.clear()
            
            async for result in tts.generate_speech(phrase, "test_session"):
                if result.is_final:
                    break
            
            logger.info(f"   Received {len(chunks_received)} dummy chunks")
        
        # Print final stats
        stats = tts.get_stats()
        logger.info(f"\n📊 Final Dummy Stats:")
        logger.info(f"   Total requests: {stats['total_requests']}")
        logger.info(f"   Avg first chunk: {stats['avg_first_chunk_ms']:.1f}ms")
        logger.info(f"   Avg generation speed: {stats['avg_generation_speed']:.1f} chars/sec")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Dummy test error: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(test_dummy_tts())