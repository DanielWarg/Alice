"""
Real Whisper ASR Implementation
==============================

Production-ready Whisper ASR med svenska stöd och optimerad prestanda.
Ersätter simulate_whisper_asr() med riktig OpenAI Whisper inference.

🔐 SÄKERHET: Denna modul använder lokalt Whisper - inga API-nycklar i kod!
"""

import asyncio
import logging
import tempfile
import time
import wave
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import whisper
import torch
import numpy as np
from io import BytesIO

logger = logging.getLogger("alice.whisper")

class WhisperASR:
    """Production Whisper ASR Engine"""
    
    def __init__(self, model_size: str = "base", device: Optional[str] = None):
        self.model_size = model_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu") 
        self.model = None
        self._model_loading = False
        self._load_lock = asyncio.Lock()
        
        logger.info(f"Whisper ASR initialized: model={model_size}, device={self.device}")
    
    async def load_model(self) -> bool:
        """Load Whisper model (async to avoid blocking)"""
        async with self._load_lock:
            if self.model is not None:
                return True
                
            if self._model_loading:
                # Wait for concurrent load
                while self._model_loading:
                    await asyncio.sleep(0.1)
                return self.model is not None
                
            try:
                self._model_loading = True
                logger.info(f"Loading Whisper model: {self.model_size}")
                
                # Load in thread pool to avoid blocking event loop
                loop = asyncio.get_event_loop()
                self.model = await loop.run_in_executor(
                    None, 
                    lambda: whisper.load_model(self.model_size, device=self.device)
                )
                
                logger.info(f"✅ Whisper model loaded successfully")
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to load Whisper model: {e}")
                return False
            finally:
                self._model_loading = False
    
    async def transcribe_audio(
        self, 
        audio_data: bytes, 
        language: str = "sv",
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Transcribe audio with real Whisper
        
        Args:
            audio_data: Raw audio bytes (PCM 16-bit, 16kHz expected)
            language: Language code ("sv" for Swedish)
            temperature: Whisper temperature (0.0 = deterministic)
            
        Returns:
            Dict with transcription results
        """
        start_time = time.time()
        
        # Ensure model is loaded
        if not await self.load_model():
            raise Exception("Failed to load Whisper model")
        
        try:
            # Convert raw bytes to numpy array for Whisper
            audio_np = await self._prepare_audio(audio_data)
            if audio_np is None:
                raise Exception("Failed to process audio data")
            
            # Run Whisper inference in thread pool (CPU intensive)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._run_whisper_inference,
                audio_np,
                language,
                temperature
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            # Extract results
            text = result.get("text", "").strip()
            confidence = self._calculate_confidence(result)
            detected_language = result.get("language", language)
            
            logger.info(f"Whisper transcription: '{text}' ({processing_time:.1f}ms, conf={confidence:.2f})")
            
            return {
                "text": text,
                "language": detected_language,
                "confidence": confidence,
                "processing_time_ms": processing_time,
                "audio_duration_ms": len(audio_data) / 2 / 16,  # 16-bit PCM, 16kHz
                "engine": "whisper",
                "model": self.model_size,
                "device": self.device
            }
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"Whisper transcription failed: {e}")
            
            return {
                "text": "",
                "language": language,
                "confidence": 0.0,
                "processing_time_ms": processing_time,
                "audio_duration_ms": len(audio_data) / 2 / 16,
                "engine": "whisper",
                "model": self.model_size,
                "device": self.device,
                "error": str(e)
            }
    
    async def _prepare_audio(self, audio_data: bytes) -> Optional[np.ndarray]:
        """Convert raw audio bytes to numpy array for Whisper"""
        try:
            # Whisper expects float32 audio normalized to [-1, 1]
            # Assuming input is 16-bit PCM, 16kHz mono
            
            # Convert bytes to int16 array
            audio_int16 = np.frombuffer(audio_data, dtype=np.int16)
            
            # Convert to float32 and normalize to [-1, 1]
            audio_float = audio_int16.astype(np.float32) / 32768.0
            
            # Whisper expects 16kHz - if different sample rate, would need resampling here
            # For now, assume input is already 16kHz as specified in ASR config
            
            logger.debug(f"Audio prepared: {len(audio_float)} samples, range=[{audio_float.min():.3f}, {audio_float.max():.3f}]")
            
            return audio_float
            
        except Exception as e:
            logger.error(f"Audio preparation failed: {e}")
            return None
    
    def _run_whisper_inference(
        self, 
        audio_np: np.ndarray, 
        language: str, 
        temperature: float
    ) -> Dict[str, Any]:
        """Run Whisper inference (synchronous, CPU-intensive)"""
        
        # Whisper inference options
        options = {
            "language": language,
            "temperature": temperature,
            "no_speech_threshold": 0.6,
            "logprob_threshold": -1.0,
            "verbose": False
        }
        
        # Run inference
        result = self.model.transcribe(audio_np, **options)
        
        return result
    
    def _calculate_confidence(self, whisper_result: Dict[str, Any]) -> float:
        """Calculate confidence score from Whisper result"""
        
        # Whisper doesn't directly provide confidence, but we can estimate from:
        # 1. no_speech_prob (lower = more confident)
        # 2. avg_logprob (higher = more confident) 
        # 3. compression_ratio (around 2.4 is normal speech)
        
        segments = whisper_result.get("segments", [])
        if not segments:
            return 0.5  # Neutral confidence if no segments
        
        # Average confidence across segments
        confidences = []
        for segment in segments:
            # Use average log probability as confidence proxy
            avg_logprob = segment.get("avg_logprob", -1.0)
            # Convert log prob to [0, 1] confidence
            # avg_logprob typically ranges from -1.0 (good) to -3.0+ (bad)
            confidence = max(0.0, min(1.0, (avg_logprob + 3.0) / 2.0))
            confidences.append(confidence)
        
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        # Apply no_speech penalty
        no_speech_prob = whisper_result.get("language_probs", {}).get("no", 0.0)
        if no_speech_prob > 0.6:
            overall_confidence *= 0.5  # Reduce confidence if likely no speech
        
        return round(overall_confidence, 3)
    
    def get_health(self) -> Dict[str, Any]:
        """Get ASR engine health status"""
        return {
            "engine": "whisper",
            "model": self.model_size,
            "device": self.device,
            "loaded": self.model is not None,
            "loading": self._model_loading,
            "cuda_available": torch.cuda.is_available()
        }


# Global Whisper instance
_whisper_asr: Optional[WhisperASR] = None


def get_whisper_asr(model_size: str = "base") -> WhisperASR:
    """Get global Whisper ASR instance (singleton pattern)"""
    global _whisper_asr
    
    if _whisper_asr is None or _whisper_asr.model_size != model_size:
        _whisper_asr = WhisperASR(model_size=model_size)
    
    return _whisper_asr


async def real_whisper_asr(
    audio_data: bytes, 
    language: str = "sv", 
    model_size: str = "base"
) -> Dict[str, Any]:
    """
    Main entry point for real Whisper ASR
    
    Replacement for simulate_whisper_asr() in asr.py
    """
    
    whisper_engine = get_whisper_asr(model_size)
    return await whisper_engine.transcribe_audio(audio_data, language)


# Health check
async def whisper_health() -> Dict[str, Any]:
    """Whisper system health check"""
    
    engine = get_whisper_asr()
    health = engine.get_health()
    
    return {
        "service": "whisper_asr",
        "status": "healthy" if not health["loading"] else "loading",
        **health
    }


# Test function
async def test_whisper_asr():
    """Test Whisper ASR with dummy audio"""
    
    # Create dummy 16-bit PCM audio (1 second of silence)
    sample_rate = 16000
    duration = 1.0
    samples = int(sample_rate * duration)
    
    # Generate some test audio (sine wave for basic test)
    t = np.linspace(0, duration, samples, False)
    audio_float = 0.1 * np.sin(2 * np.pi * 440 * t)  # 440Hz sine wave
    audio_int16 = (audio_float * 32767).astype(np.int16)
    audio_bytes = audio_int16.tobytes()
    
    print("Testing Whisper ASR...")
    result = await real_whisper_asr(audio_bytes, language="sv")
    
    print(f"Result: {result}")
    return result


if __name__ == "__main__":
    # Test script
    asyncio.run(test_whisper_asr())