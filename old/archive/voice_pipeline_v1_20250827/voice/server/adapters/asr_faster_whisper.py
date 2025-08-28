#!/usr/bin/env python3
"""
🎙️ Faster-Whisper ASR Streaming Adapter
Real-time speech-to-text with partial/final transcription
Target: ≤200ms partial, ≤250ms final on silence
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
import numpy as np
from faster_whisper import WhisperModel
import threading
from queue import Queue, Empty
from collections import deque

logger = logging.getLogger(__name__)

@dataclass
class ASRConfig:
    """ASR configuration parameters"""
    model_size: str = "tiny"  # tiny for speed, base for accuracy
    device: str = "cpu"  # cpu, cuda
    compute_type: str = "int8"  # int8, float16, float32
    
    # Streaming parameters
    chunk_ms: int = 160  # Smaller chunks for faster response (8 frames @ 20ms)
    stabilize_ms: int = 200  # Shorter silence for faster final
    sample_rate: int = 16000
    
    # Whisper parameters optimized for speed
    beam_size: int = 1  # Fast decoding
    no_speech_threshold: float = 0.1  # Very low threshold for synthetic audio testing
    temperature: float = 0.0  # Deterministic
    patience: float = 0.5  # Faster decoding
    suppress_blank: bool = False  # Allow blanks for testing
    vad_filter: bool = False  # Disable VAD for now
    
    # Performance tuning
    min_partial_words: int = 1  # Allow single words for responsiveness
    max_buffer_ms: int = 3000  # Smaller buffer for lower latency

@dataclass
class ASRResult:
    """ASR transcription result"""
    text: str
    confidence: float
    is_partial: bool
    timestamp_start: float
    timestamp_end: float
    session_id: str
    processing_ms: float = 0.0

class AudioBuffer:
    """Circular audio buffer with VAD support"""
    
    def __init__(self, max_duration_ms: int = 5000, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.max_samples = int(max_duration_ms * sample_rate / 1000)
        self.buffer = np.zeros(self.max_samples, dtype=np.float32)
        self.write_pos = 0
        self.total_samples = 0
        self.silence_samples = 0
        self.lock = threading.Lock()
        
    def add_audio(self, samples: np.ndarray) -> None:
        """Add audio samples to buffer"""
        with self.lock:
            samples_len = len(samples)
            
            # Handle buffer wraparound
            if self.write_pos + samples_len <= self.max_samples:
                self.buffer[self.write_pos:self.write_pos + samples_len] = samples
            else:
                # Split across buffer end
                first_part = self.max_samples - self.write_pos
                self.buffer[self.write_pos:] = samples[:first_part]
                self.buffer[:samples_len - first_part] = samples[first_part:]
                
            self.write_pos = (self.write_pos + samples_len) % self.max_samples
            self.total_samples += samples_len
            
            # Simple silence detection
            energy = np.mean(samples ** 2)
            if energy < 0.001:  # Silence threshold
                self.silence_samples += samples_len
            else:
                self.silence_samples = 0
    
    def get_audio(self, duration_ms: int) -> np.ndarray:
        """Get last N milliseconds of audio"""
        with self.lock:
            samples_needed = int(duration_ms * self.sample_rate / 1000)
            samples_available = min(samples_needed, self.total_samples, self.max_samples)
            
            if samples_available == 0:
                return np.array([], dtype=np.float32)
                
            # Calculate start position
            start_pos = (self.write_pos - samples_available) % self.max_samples
            
            if start_pos + samples_available <= self.max_samples:
                # Continuous segment
                return self.buffer[start_pos:start_pos + samples_available].copy()
            else:
                # Wrapped segment
                first_part = self.max_samples - start_pos
                result = np.zeros(samples_available, dtype=np.float32)
                result[:first_part] = self.buffer[start_pos:]
                result[first_part:] = self.buffer[:samples_available - first_part]
                return result
    
    def get_silence_duration_ms(self) -> float:
        """Get current silence duration in milliseconds"""
        return (self.silence_samples / self.sample_rate) * 1000
    
    def clear(self) -> None:
        """Clear buffer"""
        with self.lock:
            self.write_pos = 0
            self.total_samples = 0
            self.silence_samples = 0

class StreamingASR:
    """Streaming faster-whisper ASR engine"""
    
    def __init__(self, config: ASRConfig):
        self.config = config
        self.model: Optional[WhisperModel] = None
        self.audio_buffer = AudioBuffer(
            max_duration_ms=config.max_buffer_ms,
            sample_rate=config.sample_rate
        )
        
        # Processing state
        self.last_partial = ""
        self.last_partial_time = 0.0
        self.processing_queue = Queue()
        self.is_running = False
        self.processing_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self.on_partial: Optional[Callable[[ASRResult], None]] = None
        self.on_final: Optional[Callable[[ASRResult], None]] = None
        
        # Performance tracking
        self.stats = {
            "total_requests": 0,
            "partial_emissions": 0,
            "final_emissions": 0,
            "avg_processing_ms": 0.0,
            "model_load_time": 0.0
        }
        
        logger.info(f"StreamingASR initialized: {config.model_size} model, {config.device}")
    
    async def initialize(self) -> None:
        """Initialize and load Whisper model"""
        start_time = time.time()
        
        try:
            logger.info(f"Loading Whisper model: {self.config.model_size}")
            self.model = WhisperModel(
                self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type
            )
            
            # Pre-warm with silence
            silence = np.zeros(int(0.1 * self.config.sample_rate), dtype=np.float32)
            list(self.model.transcribe(silence, beam_size=1))
            
            load_time = (time.time() - start_time) * 1000
            self.stats["model_load_time"] = load_time
            
            logger.info(f"✅ Whisper model loaded and pre-warmed in {load_time:.1f}ms")
            
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            raise
    
    def start_processing(self) -> None:
        """Start background processing thread"""
        if self.processing_thread and self.processing_thread.is_alive():
            return
            
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        logger.info("🎯 ASR processing thread started")
    
    def stop_processing(self) -> None:
        """Stop background processing"""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
            self.processing_thread = None
        logger.info("🛑 ASR processing stopped")
    
    def add_audio_frame(self, session_id: str, samples: np.ndarray) -> None:
        """Add audio frame for processing"""
        # Add to buffer
        self.audio_buffer.add_audio(samples)
        
        # Queue for processing
        timestamp = time.time()
        self.processing_queue.put({
            "session_id": session_id,
            "timestamp": timestamp,
            "frame_size": len(samples)
        })
    
    def _processing_loop(self) -> None:
        """Background processing loop"""
        logger.info("🔄 ASR processing loop started")
        
        while self.is_running:
            try:
                # Get processing request
                try:
                    request = self.processing_queue.get(timeout=0.1)
                except Empty:
                    continue
                
                # Process audio
                self._process_audio_chunk(request)
                self.processing_queue.task_done()
                
            except Exception as e:
                logger.error(f"❌ Processing loop error: {e}")
                continue
    
    def _process_audio_chunk(self, request: Dict[str, Any]) -> None:
        """Process audio chunk for transcription"""
        session_id = request["session_id"]
        request_time = request["timestamp"]
        
        start_time = time.time()
        
        try:
            # Get audio for transcription - use smaller buffer for faster response
            audio_data = self.audio_buffer.get_audio(self.config.chunk_ms * 2)  # 2x chunk for context
            
            if len(audio_data) < self.config.sample_rate * 0.04:  # Minimum 40ms for testing
                return
            
            # Transcribe with faster-whisper
            segments, info = self.model.transcribe(
                audio_data,
                beam_size=self.config.beam_size,
                temperature=self.config.temperature,
                patience=self.config.patience,
                no_speech_threshold=self.config.no_speech_threshold,
                suppress_blank=self.config.suppress_blank,
                vad_filter=self.config.vad_filter,
                word_timestamps=False  # Disable for speed
            )
            
            # Collect transcription
            segments_list = list(segments)
            if not segments_list:
                return
            
            # Combine segments
            text = " ".join(segment.text.strip() for segment in segments_list)
            confidence = sum(segment.no_speech_prob for segment in segments_list) / len(segments_list)
            confidence = 1.0 - confidence  # Convert no_speech_prob to confidence
            
            processing_ms = (time.time() - start_time) * 1000
            self.stats["total_requests"] += 1
            
            # Update average processing time
            current_avg = self.stats["avg_processing_ms"]
            total_requests = self.stats["total_requests"]
            self.stats["avg_processing_ms"] = (current_avg * (total_requests - 1) + processing_ms) / total_requests
            
            # Determine if partial or final
            silence_ms = self.audio_buffer.get_silence_duration_ms()
            is_final = silence_ms >= self.config.stabilize_ms
            
            # Filter partial results
            words = text.split()
            if len(words) < self.config.min_partial_words and not is_final:
                return
            
            # Avoid duplicate partials
            if not is_final and text == self.last_partial:
                return
            
            # Create result
            result = ASRResult(
                text=text,
                confidence=confidence,
                is_partial=not is_final,
                timestamp_start=request_time - (len(audio_data) / self.config.sample_rate),
                timestamp_end=request_time,
                session_id=session_id,
                processing_ms=processing_ms
            )
            
            # Emit result
            if is_final:
                self.stats["final_emissions"] += 1
                if self.on_final:
                    self.on_final(result)
                self.audio_buffer.clear()  # Clear buffer after final
                self.last_partial = ""
                logger.info(f"🎯 FINAL: '{text}' ({processing_ms:.1f}ms, conf={confidence:.3f})")
            else:
                self.stats["partial_emissions"] += 1
                if self.on_partial:
                    self.on_partial(result)
                self.last_partial = text
                self.last_partial_time = time.time()
                logger.debug(f"📝 partial: '{text}' ({processing_ms:.1f}ms)")
            
        except Exception as e:
            logger.error(f"❌ Transcription error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            **self.stats,
            "buffer_size_ms": (self.audio_buffer.total_samples / self.config.sample_rate) * 1000,
            "silence_ms": self.audio_buffer.get_silence_duration_ms(),
            "queue_size": self.processing_queue.qsize()
        }

# Factory function
def create_streaming_asr(
    on_partial: Optional[Callable[[ASRResult], None]] = None,
    on_final: Optional[Callable[[ASRResult], None]] = None,
    config: Optional[ASRConfig] = None
) -> StreamingASR:
    """Create and configure streaming ASR"""
    if config is None:
        config = ASRConfig()
    
    asr = StreamingASR(config)
    asr.on_partial = on_partial
    asr.on_final = on_final
    
    return asr

# Test function
async def test_streaming_asr():
    """Test streaming ASR with synthetic audio"""
    results = []
    
    def on_partial(result: ASRResult):
        results.append(f"PARTIAL: {result.text} ({result.processing_ms:.1f}ms)")
    
    def on_final(result: ASRResult):
        results.append(f"FINAL: {result.text} ({result.processing_ms:.1f}ms)")
    
    # Create ASR
    config = ASRConfig(model_size="base", chunk_ms=200)
    asr = create_streaming_asr(on_partial, on_final, config)
    
    # Initialize and start
    await asr.initialize()
    asr.start_processing()
    
    try:
        # Simulate audio frames (silence for test)
        for i in range(10):
            samples = np.random.normal(0, 0.01, 320).astype(np.float32)  # 20ms @ 16kHz
            asr.add_audio_frame(f"test_session", samples)
            await asyncio.sleep(0.02)  # 20ms between frames
        
        # Wait for processing
        await asyncio.sleep(2.0)
        
        # Print results
        print("🧪 ASR Test Results:")
        for result in results:
            print(f"   {result}")
        
        # Print stats
        stats = asr.get_stats()
        print(f"\n📊 Performance Stats:")
        print(f"   Model load time: {stats['model_load_time']:.1f}ms")
        print(f"   Avg processing: {stats['avg_processing_ms']:.1f}ms")
        print(f"   Total requests: {stats['total_requests']}")
        print(f"   Partial/Final: {stats['partial_emissions']}/{stats['final_emissions']}")
        
    finally:
        asr.stop_processing()

if __name__ == "__main__":
    asyncio.run(test_streaming_asr())