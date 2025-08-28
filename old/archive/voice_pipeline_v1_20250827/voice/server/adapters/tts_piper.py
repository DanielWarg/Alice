#!/usr/bin/env python3
"""
🔊 Piper TTS Streaming Adapter
Real-time text-to-speech with streaming audio generation
Target: ≤150ms first chunk, 40-80ms chunks for voice conversations
"""

import asyncio
import logging
import time
import numpy as np
import tempfile
import wave
import struct
from typing import Optional, Dict, Any, Callable, AsyncIterator
from dataclasses import dataclass
from pathlib import Path
import subprocess
import threading
from queue import Queue, Empty
import io

logger = logging.getLogger(__name__)

@dataclass
class TTSConfig:
    """TTS configuration parameters"""
    model_path: str = "../../../server/models/tts/sv_SE-nst-medium.onnx"
    
    # Audio parameters
    sample_rate: int = 16000  # Match voice pipeline
    channels: int = 1  # Mono
    
    # Streaming parameters  
    chunk_ms: int = 60  # Target chunk duration
    max_text_length: int = 200  # Split long texts
    
    # Performance tuning
    speed: float = 1.0  # Speaking rate
    noise_scale: float = 0.667  # Voice variation
    noise_scale_w: float = 0.8  # Phoneme duration variation
    
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
    """Streaming Piper TTS engine"""
    
    def __init__(self, config: TTSConfig):
        self.config = config
        self.is_initialized = False
        
        # Model path resolution
        self.model_path = Path(config.model_path)
        if not self.model_path.is_absolute():
            # Resolve relative to this file
            current_dir = Path(__file__).parent
            self.model_path = (current_dir / self.model_path).resolve()
        
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
        
        logger.info(f"StreamingTTS initialized: {self.model_path}")
    
    async def initialize(self) -> None:
        """Initialize TTS model and warm up"""
        start_time = time.time()
        
        try:
            # Verify model exists
            if not self.model_path.exists():
                raise FileNotFoundError(f"TTS model not found: {self.model_path}")
            
            # Warm up Piper with a short phrase
            logger.info(f"Warming up Piper TTS model: {self.model_path}")
            
            warmup_text = "Hej"
            warmup_start = time.time()
            
            # Test Piper generation
            result = await self._generate_audio(warmup_text)
            
            if result:
                warmup_time = (time.time() - warmup_start) * 1000
                init_time = (time.time() - start_time) * 1000
                
                self.stats["initialization_time_ms"] = init_time
                self.stats["model_warm"] = True
                self.is_initialized = True
                
                logger.info(f"✅ TTS initialized in {init_time:.1f}ms (warmup: {warmup_time:.1f}ms)")
                logger.info(f"   Generated {len(result):.1f}s of audio")
            else:
                raise RuntimeError("Warmup generation failed")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize TTS: {e}")
            raise
    
    async def generate_speech(self, text: str, session_id: str = "default") -> AsyncIterator[TTSResult]:
        """Generate streaming speech from text"""
        if not self.is_initialized:
            raise RuntimeError("TTS not initialized")
        
        if not text or not text.strip():
            return
        
        start_time = time.time()
        first_chunk_time = None
        
        logger.info(f"🔊 Generating speech for session {session_id}: '{text[:50]}...'")
        
        try:
            # Split text into chunks for streaming
            text_chunks = self._split_text_for_streaming(text.strip())
            
            total_chunks = len(text_chunks)
            logger.debug(f"   Split into {total_chunks} chunks: {[chunk[:20]+'...' for chunk in text_chunks]}")
            
            for chunk_idx, text_chunk in enumerate(text_chunks):
                chunk_start = time.time()
                
                # Generate audio for this chunk
                audio_data = await self._generate_audio(text_chunk)
                
                if audio_data is not None and len(audio_data) > 0:
                    chunk_time = (time.time() - chunk_start) * 1000
                    
                    if first_chunk_time is None:
                        first_chunk_time = (time.time() - start_time) * 1000
                        logger.info(f"🎯 First TTS chunk in {first_chunk_time:.1f}ms")
                    
                    # Convert to numpy array if needed
                    if isinstance(audio_data, (list, tuple)):
                        audio_array = np.array(audio_data, dtype=np.float32)
                    elif isinstance(audio_data, np.ndarray):
                        audio_array = audio_data.astype(np.float32)
                    else:
                        logger.warning(f"Unexpected audio data type: {type(audio_data)}")
                        continue
                    
                    # Ensure audio is in valid range
                    if audio_array.max() > 1.0 or audio_array.min() < -1.0:
                        audio_array = np.clip(audio_array, -1.0, 1.0)
                    
                    is_final_chunk = (chunk_idx == total_chunks - 1)
                    
                    result = TTSResult(
                        audio_chunk=audio_array,
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
                    
                    logger.debug(f"   Chunk {chunk_idx+1}/{total_chunks}: {len(audio_array)} samples, {chunk_time:.1f}ms")
                    
                    # Final chunk callback
                    if is_final_chunk and self.on_complete:
                        self.on_complete(result)
                
                else:
                    logger.warning(f"No audio generated for chunk: '{text_chunk}'")
            
            # Update statistics
            total_time = time.time() - start_time
            self._update_stats(text, first_chunk_time, total_time)
            
            logger.info(f"✅ TTS complete: {len(text)} chars in {total_time*1000:.1f}ms "
                       f"(TTFC={first_chunk_time:.1f}ms)")
                       
        except Exception as e:
            logger.error(f"❌ TTS generation error: {e}")
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
    
    async def _generate_audio(self, text: str) -> Optional[np.ndarray]:
        """Generate audio using Piper TTS"""
        if not text.strip():
            return None
        
        try:
            # Create temporary files for input text and output audio
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as text_file:
                text_file.write(text)
                text_file_path = text_file.name
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as audio_file:
                audio_file_path = audio_file.name
            
            try:
                # Run Piper TTS
                cmd = [
                    'piper',
                    '--model', str(self.model_path),
                    '--output_file', audio_file_path,
                    '--speaker', '0',  # Default speaker
                    '--length_scale', str(1.0 / self.config.speed),  # Speed control
                    '--noise_scale', str(self.config.noise_scale),
                    '--noise_scale_w', str(self.config.noise_scale_w)
                ]
                
                # Run Piper process
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Send text to Piper
                stdout, stderr = await process.communicate(input=text.encode())
                
                if process.returncode != 0:
                    logger.error(f"Piper TTS error: {stderr.decode()}")
                    return None
                
                # Read generated audio
                if Path(audio_file_path).exists():
                    try:
                        with wave.open(audio_file_path, 'rb') as wav_file:
                            frames = wav_file.readframes(wav_file.getnframes())
                            
                            # Convert to numpy array
                            if wav_file.getsampwidth() == 2:  # 16-bit
                                audio_data = np.frombuffer(frames, dtype=np.int16)
                                # Convert to float32 in range [-1, 1]
                                audio_data = audio_data.astype(np.float32) / 32768.0
                            else:
                                logger.warning(f"Unsupported sample width: {wav_file.getsampwidth()}")
                                return None
                            
                            # Ensure mono
                            if wav_file.getnchannels() == 2:
                                audio_data = audio_data[::2]  # Take left channel
                            
                            return audio_data
                            
                    except Exception as e:
                        logger.error(f"Error reading generated audio: {e}")
                        return None
                else:
                    logger.error(f"Audio file not generated: {audio_file_path}")
                    return None
                
            finally:
                # Cleanup temporary files
                Path(text_file_path).unlink(missing_ok=True)
                Path(audio_file_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"Error in Piper TTS generation: {e}")
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
            "model_path": str(self.model_path)
        }

# Factory function
def create_streaming_tts(
    on_chunk: Optional[Callable[[TTSResult], None]] = None,
    on_complete: Optional[Callable[[TTSResult], None]] = None,
    config: Optional[TTSConfig] = None
) -> StreamingTTS:
    """Create and configure streaming TTS"""
    if config is None:
        config = TTSConfig()
    
    tts = StreamingTTS(config)
    tts.on_chunk = on_chunk
    tts.on_complete = on_complete
    
    return tts

# Test function
async def test_streaming_tts():
    """Test streaming TTS with sample text"""
    logger.info("🧪 Testing Streaming TTS...")
    
    chunks_received = []
    
    def on_chunk(result: TTSResult):
        chunks_received.append(result)
        logger.info(f"TTS Chunk {result.chunk_index+1}/{result.total_chunks}: "
                   f"{len(result.audio_chunk)} samples, {result.generation_ms:.1f}ms")
    
    def on_complete(result: TTSResult):
        logger.info(f"TTS Complete: '{result.text_processed}' "
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
            "Det här är ett test av text-till-tal systemet.",
            "Kan du generera ljud från denna text på svenska?"
        ]
        
        for phrase in test_phrases:
            logger.info(f"\n🔸 Testing phrase: '{phrase}'")
            chunks_received.clear()
            
            async for result in tts.generate_speech(phrase, "test_session"):
                if result.is_final:
                    break
            
            logger.info(f"   Received {len(chunks_received)} chunks")
        
        # Print final stats
        stats = tts.get_stats()
        logger.info(f"\n📊 Final Stats:")
        logger.info(f"   Total requests: {stats['total_requests']}")
        logger.info(f"   Avg first chunk: {stats['avg_first_chunk_ms']:.1f}ms")
        logger.info(f"   Avg generation speed: {stats['avg_generation_speed']:.1f} chars/sec")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(test_streaming_tts())