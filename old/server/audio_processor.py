"""
Audio Processing Pipeline for Alice's Hybrid Voice Architecture
Implements both TTS post-processing and Voice-Gateway input processing

Features:
- TTS audio enhancement and normalization
- Voice-Gateway audio chunk processing (PCM16, base64)
- Voice Activity Detection (VAD)
- Audio streaming buffer management
- Real-time audio quality validation
"""

import os
import subprocess
import tempfile
import logging
import base64
import io
import struct
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

import numpy as np

logger = logging.getLogger("alice.audio")

class AudioProcessor:
    """Enhanced audio post-processing for TTS output"""
    
    def __init__(self):
        self.ffmpeg_available = self._check_ffmpeg()
        
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available for audio processing"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("FFmpeg not available - audio post-processing disabled")
            return False
    
    def enhance_audio(self, audio_data: bytes, settings: Dict[str, Any]) -> bytes:
        """Apply audio enhancements based on voice settings"""
        if not self.ffmpeg_available:
            return audio_data
            
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as input_file:
                input_path = input_file.name
                input_file.write(audio_data)
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as output_file:
                output_path = output_file.name
            
            # Build FFmpeg enhancement chain
            filters = self._build_filter_chain(settings)
            
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-af', filters,
                '-c:a', 'pcm_s16le',  # Ensure consistent audio format
                '-ar', '22050',       # Standard sample rate for TTS
                output_path
            ]
            
            # Run FFmpeg processing
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg processing failed: {result.stderr}")
                return audio_data  # Return original on failure
            
            # Read enhanced audio
            with open(output_path, 'rb') as f:
                enhanced_audio = f.read()
            
            # Cleanup
            os.unlink(input_path)
            os.unlink(output_path)
            
            logger.info("Audio enhancement applied successfully")
            return enhanced_audio
            
        except Exception as e:
            logger.error(f"Audio enhancement failed: {e}")
            return audio_data  # Return original on error
    
    def _build_filter_chain(self, settings: Dict[str, Any]) -> str:
        """Build FFmpeg filter chain based on voice settings"""
        filters = []
        
        # Volume normalization and adjustment
        volume = settings.get("volume", 1.0)
        if volume != 1.0:
            filters.append(f"volume={volume}")
        
        # Dynamic range compression for more consistent loudness
        filters.append("acompressor=threshold=-18dB:ratio=3:attack=5:release=50")
        
        # Audio normalization to prevent clipping
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=7")
        
        # Emotion-based EQ adjustments
        emotion = settings.get("emotion", "neutral")
        eq_filter = self._get_emotion_eq(emotion)
        if eq_filter:
            filters.append(eq_filter)
        
        # High-pass filter to remove very low frequencies (room tone)
        filters.append("highpass=f=80")
        
        # Low-pass filter for smoother sound (optional based on quality)
        confidence = settings.get("confidence", 0.8)
        if confidence < 0.9:  # Add slight smoothing for less confident speech
            filters.append("lowpass=f=8000")
        
        # Subtle reverb for more natural sound
        filters.append("aecho=0.8:0.9:40:0.25")
        
        return ",".join(filters)
    
    def _get_emotion_eq(self, emotion: str) -> Optional[str]:
        """Get emotion-specific EQ settings"""
        emotion_eq = {
            "happy": "equalizer=f=2000:width_type=h:width=500:g=2",      # Boost upper mids for brightness
            "confident": "equalizer=f=400:width_type=h:width=200:g=1.5", # Boost lower mids for authority
            "calm": "equalizer=f=1000:width_type=h:width=800:g=-1",      # Slight cut in mids for softness
            "friendly": "equalizer=f=3000:width_type=h:width=600:g=1.5", # Boost presence for warmth
            "neutral": None  # No EQ adjustment
        }
        
        return emotion_eq.get(emotion)
    
    def normalize_audio_levels(self, audio_data: bytes) -> bytes:
        """Quick audio normalization without full enhancement"""
        if not self.ffmpeg_available:
            return audio_data
            
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as input_file:
                input_path = input_file.name
                input_file.write(audio_data)
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as output_file:
                output_path = output_file.name
            
            # Simple normalization
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-af', 'loudnorm=I=-16:TP=-1.5:LRA=7',
                '-c:a', 'pcm_s16le',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                with open(output_path, 'rb') as f:
                    normalized_audio = f.read()
            else:
                normalized_audio = audio_data
            
            # Cleanup
            os.unlink(input_path)
            os.unlink(output_path)
            
            return normalized_audio
            
        except Exception as e:
            logger.error(f"Audio normalization failed: {e}")
            return audio_data

class AudioFormat(Enum):
    """Supported audio formats for Voice-Gateway"""
    PCM16 = "pcm16"
    WEBM = "webm"
    MP3 = "mp3"
    WAV = "wav"

@dataclass
class AudioChunk:
    """Audio chunk with metadata for Voice-Gateway processing"""
    data: bytes
    timestamp: float
    format: AudioFormat
    sample_rate: int = 24000
    channels: int = 1
    energy_level: float = 0.0
    is_speech: bool = False
    confidence: float = 0.0

@dataclass 
class VADResult:
    """Voice Activity Detection result"""
    is_speech: bool
    confidence: float
    energy_level: float
    timestamp: float
    duration_ms: float

class VoiceGatewayAudioProcessor:
    """Audio processor specifically for Voice-Gateway input handling"""
    
    def __init__(self):
        self.ffmpeg_available = self._check_ffmpeg()
        
        # VAD configuration
        self.vad_config = {
            "energy_threshold": 0.01,           # Minimum energy to consider as potential speech
            "speech_threshold": 0.6,            # Confidence threshold for speech detection
            "hangover_frames": 10,              # Frames to continue after speech ends
            "trigger_frames": 3,                # Frames needed to trigger speech
            "sample_rate": 24000,
            "frame_size_ms": 100               # 100ms frames
        }
        
        # Audio processing configuration
        self.processing_config = {
            "target_sample_rate": 24000,
            "target_channels": 1,
            "target_format": AudioFormat.PCM16,
            "max_chunk_size": 8192,            # Maximum bytes per chunk
            "noise_gate_threshold": -40,        # dB threshold for noise gate
            "pre_emphasis_alpha": 0.97          # Pre-emphasis filter coefficient
        }
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("FFmpeg not available - some audio processing disabled")
            return False
    
    def process_audio_chunk(self, chunk_data: str, chunk_format: str = "pcm16", 
                           metadata: Optional[Dict[str, Any]] = None) -> AudioChunk:
        """
        Process incoming audio chunk from Voice-Gateway client
        
        Args:
            chunk_data: Base64 encoded audio data or raw bytes
            chunk_format: Audio format (pcm16, webm, etc.)
            metadata: Optional metadata (timestamp, sample_rate, etc.)
            
        Returns:
            AudioChunk with processed data and analysis
        """
        try:
            # Decode base64 if needed
            if isinstance(chunk_data, str):
                audio_bytes = base64.b64decode(chunk_data)
            else:
                audio_bytes = chunk_data
            
            # Create audio chunk
            chunk = AudioChunk(
                data=audio_bytes,
                timestamp=metadata.get('timestamp', time.time()) if metadata else time.time(),
                format=AudioFormat(chunk_format),
                sample_rate=metadata.get('sample_rate', 24000) if metadata else 24000,
                channels=metadata.get('channels', 1) if metadata else 1
            )
            
            # Validate and convert audio format if needed
            chunk = self._validate_and_convert_format(chunk)
            
            # Calculate energy level
            chunk.energy_level = self._calculate_energy_level(chunk)
            
            # Perform Voice Activity Detection
            vad_result = self._perform_vad(chunk)
            chunk.is_speech = vad_result.is_speech
            chunk.confidence = vad_result.confidence
            
            # Apply noise reduction if needed
            if chunk.energy_level > 0 and chunk.is_speech:
                chunk = self._apply_input_enhancement(chunk)
            
            return chunk
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            # Return empty chunk on error
            return AudioChunk(
                data=b"",
                timestamp=time.time(),
                format=AudioFormat.PCM16,
                sample_rate=24000,
                channels=1
            )
    
    def _validate_and_convert_format(self, chunk: AudioChunk) -> AudioChunk:
        """Validate and convert audio format to target format"""
        target_format = self.processing_config["target_format"]
        target_sample_rate = self.processing_config["target_sample_rate"]
        target_channels = self.processing_config["target_channels"]
        
        # If already in target format, just validate
        if (chunk.format == target_format and 
            chunk.sample_rate == target_sample_rate and 
            chunk.channels == target_channels):
            return chunk
        
        # Convert format if FFmpeg available
        if self.ffmpeg_available and len(chunk.data) > 0:
            try:
                converted_data = self._convert_audio_format(
                    chunk.data, chunk.format, target_format, 
                    chunk.sample_rate, target_sample_rate, target_channels
                )
                
                chunk.data = converted_data
                chunk.format = target_format
                chunk.sample_rate = target_sample_rate
                chunk.channels = target_channels
                
            except Exception as e:
                logger.warning(f"Audio format conversion failed: {e}")
        
        return chunk
    
    def _convert_audio_format(self, audio_data: bytes, source_format: AudioFormat, 
                             target_format: AudioFormat, source_rate: int, 
                             target_rate: int, target_channels: int) -> bytes:
        """Convert audio format using FFmpeg"""
        with tempfile.NamedTemporaryFile(delete=False) as input_file:
            input_path = input_file.name
            input_file.write(audio_data)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as output_file:
            output_path = output_file.name
        
        try:
            # Build FFmpeg command
            cmd = [
                'ffmpeg', '-y',
                '-f', self._get_ffmpeg_format(source_format),
                '-ar', str(source_rate),
                '-i', input_path,
                '-f', self._get_ffmpeg_format(target_format),
                '-ar', str(target_rate),
                '-ac', str(target_channels),
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg conversion failed: {result.stderr}")
            
            with open(output_path, 'rb') as f:
                converted_data = f.read()
            
            return converted_data
            
        finally:
            os.unlink(input_path)
            os.unlink(output_path)
    
    def _get_ffmpeg_format(self, audio_format: AudioFormat) -> str:
        """Get FFmpeg format string"""
        format_map = {
            AudioFormat.PCM16: 's16le',
            AudioFormat.WEBM: 'webm',
            AudioFormat.MP3: 'mp3',
            AudioFormat.WAV: 'wav'
        }
        return format_map.get(audio_format, 's16le')
    
    def _calculate_energy_level(self, chunk: AudioChunk) -> float:
        """Calculate RMS energy level of audio chunk"""
        try:
            if len(chunk.data) == 0:
                return 0.0
            
            # Convert PCM16 bytes to numpy array
            if chunk.format == AudioFormat.PCM16:
                samples = np.frombuffer(chunk.data, dtype=np.int16)
            else:
                # For other formats, try to decode first
                samples = self._decode_audio_samples(chunk)
            
            if len(samples) == 0:
                return 0.0
            
            # Calculate RMS energy
            rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
            
            # Normalize to 0-1 range
            normalized_energy = min(1.0, rms / 32768.0) if chunk.format == AudioFormat.PCM16 else min(1.0, rms)
            
            return float(normalized_energy)
            
        except Exception as e:
            logger.warning(f"Energy calculation failed: {e}")
            return 0.0
    
    def _decode_audio_samples(self, chunk: AudioChunk) -> np.ndarray:
        """Decode audio samples from various formats"""
        try:
            if chunk.format == AudioFormat.PCM16:
                return np.frombuffer(chunk.data, dtype=np.int16)
            else:
                # For other formats, use FFmpeg to decode to PCM16
                if self.ffmpeg_available:
                    pcm_data = self._convert_audio_format(
                        chunk.data, chunk.format, AudioFormat.PCM16,
                        chunk.sample_rate, chunk.sample_rate, chunk.channels
                    )
                    return np.frombuffer(pcm_data, dtype=np.int16)
                else:
                    return np.array([], dtype=np.int16)
        except:
            return np.array([], dtype=np.int16)
    
    def _perform_vad(self, chunk: AudioChunk) -> VADResult:
        """
        Perform Voice Activity Detection on audio chunk
        Uses energy-based VAD with spectral features
        """
        energy = chunk.energy_level
        timestamp = chunk.timestamp
        
        # Simple energy-based VAD
        energy_speech = energy > self.vad_config["energy_threshold"]
        
        # Enhanced VAD with spectral features if we have enough data
        spectral_speech = False
        spectral_confidence = 0.0
        
        try:
            samples = self._decode_audio_samples(chunk)
            if len(samples) >= 1024:  # Need minimum samples for spectral analysis
                spectral_speech, spectral_confidence = self._spectral_vad(samples, chunk.sample_rate)
        except Exception as e:
            logger.debug(f"Spectral VAD failed: {e}")
        
        # Combine energy and spectral VAD
        is_speech = energy_speech or spectral_speech
        confidence = max(min(energy * 2.0, 1.0), spectral_confidence)
        
        # Calculate chunk duration
        if len(chunk.data) > 0 and chunk.format == AudioFormat.PCM16:
            duration_ms = (len(chunk.data) / 2 / chunk.channels / chunk.sample_rate) * 1000
        else:
            duration_ms = 100  # Default chunk duration
        
        return VADResult(
            is_speech=is_speech,
            confidence=confidence,
            energy_level=energy,
            timestamp=timestamp,
            duration_ms=duration_ms
        )
    
    def _spectral_vad(self, samples: np.ndarray, sample_rate: int) -> Tuple[bool, float]:
        """
        Spectral-based Voice Activity Detection
        Analyzes frequency content to distinguish speech from noise
        """
        try:
            # Apply pre-emphasis filter
            pre_emphasis = self.processing_config["pre_emphasis_alpha"]
            emphasized = np.append(samples[0], samples[1:] - pre_emphasis * samples[:-1])
            
            # Windowing
            window_size = min(1024, len(emphasized))
            if window_size < 256:
                return False, 0.0
            
            windowed = emphasized[:window_size] * np.hanning(window_size)
            
            # FFT
            fft = np.fft.fft(windowed)
            magnitude = np.abs(fft[:window_size//2])
            
            # Calculate spectral features
            freq_bins = np.fft.fftfreq(window_size, 1/sample_rate)[:window_size//2]
            
            # Speech typically has energy in 300-3000 Hz range
            speech_band_start = int(300 * window_size / sample_rate)
            speech_band_end = int(3000 * window_size / sample_rate)
            
            speech_energy = np.sum(magnitude[speech_band_start:speech_band_end])
            total_energy = np.sum(magnitude)
            
            if total_energy == 0:
                return False, 0.0
            
            speech_ratio = speech_energy / total_energy
            
            # Speech detection based on spectral characteristics
            is_speech = speech_ratio > 0.4 and total_energy > 1000
            confidence = min(1.0, speech_ratio * 2.0)
            
            return is_speech, confidence
            
        except Exception as e:
            logger.debug(f"Spectral VAD analysis failed: {e}")
            return False, 0.0
    
    def _apply_input_enhancement(self, chunk: AudioChunk) -> AudioChunk:
        """Apply enhancement to input audio chunk"""
        try:
            samples = self._decode_audio_samples(chunk)
            if len(samples) == 0:
                return chunk
            
            # Apply noise gate
            noise_threshold = self.processing_config["noise_gate_threshold"]
            rms_db = 20 * np.log10(np.sqrt(np.mean(samples.astype(np.float32) ** 2)) / 32768.0 + 1e-10)
            
            if rms_db < noise_threshold:
                # Apply gentle noise gate
                gate_factor = max(0.1, (rms_db - noise_threshold) / 10 + 1)
                samples = (samples * gate_factor).astype(np.int16)
            
            # Convert back to bytes
            if chunk.format == AudioFormat.PCM16:
                chunk.data = samples.tobytes()
            
            return chunk
            
        except Exception as e:
            logger.warning(f"Input enhancement failed: {e}")
            return chunk
    
    def combine_audio_chunks(self, chunks: List[AudioChunk]) -> bytes:
        """Combine multiple audio chunks into single audio buffer"""
        if not chunks:
            return b""
        
        try:
            # Ensure all chunks are in same format
            target_format = AudioFormat.PCM16
            combined_data = b""
            
            for chunk in chunks:
                if chunk.format == target_format:
                    combined_data += chunk.data
                else:
                    # Convert chunk if needed
                    converted_chunk = self._validate_and_convert_format(chunk)
                    combined_data += converted_chunk.data
            
            return combined_data
            
        except Exception as e:
            logger.error(f"Error combining audio chunks: {e}")
            return b""
    
    def validate_audio_quality(self, chunk: AudioChunk) -> Dict[str, Any]:
        """Validate audio quality and return metrics"""
        try:
            samples = self._decode_audio_samples(chunk)
            
            if len(samples) == 0:
                return {
                    "valid": False,
                    "reason": "no_audio_data",
                    "energy_level": 0.0,
                    "snr_estimate": 0.0,
                    "quality_score": 0.0
                }
            
            # Calculate quality metrics
            energy_level = chunk.energy_level
            
            # Estimate SNR (very basic)
            signal_power = np.var(samples.astype(np.float32))
            
            # Estimate noise floor from quietest 10% of samples
            sorted_samples = np.sort(np.abs(samples))
            noise_floor_idx = int(len(sorted_samples) * 0.1)
            noise_power = np.var(sorted_samples[:noise_floor_idx].astype(np.float32))
            
            snr_estimate = 10 * np.log10(signal_power / (noise_power + 1e-10))
            
            # Quality score (0-1)
            quality_score = min(1.0, max(0.0, (snr_estimate - 5) / 20))  # 5-25 dB SNR maps to 0-1
            
            is_valid = (
                energy_level > 0.005 and  # Minimum energy
                len(chunk.data) > 100 and  # Minimum data size
                snr_estimate > 0          # Positive SNR
            )
            
            return {
                "valid": is_valid,
                "reason": "quality_ok" if is_valid else "poor_audio_quality",
                "energy_level": energy_level,
                "snr_estimate": snr_estimate,
                "quality_score": quality_score,
                "sample_count": len(samples),
                "duration_ms": (len(samples) / chunk.sample_rate) * 1000 if chunk.sample_rate > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Audio quality validation failed: {e}")
            return {
                "valid": False,
                "reason": "validation_error",
                "error": str(e)
            }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get audio processing statistics"""
        return {
            "vad_config": self.vad_config,
            "processing_config": self.processing_config,
            "ffmpeg_available": self.ffmpeg_available,
            "supported_formats": [fmt.value for fmt in AudioFormat]
        }

# Global audio processor instances
audio_processor = AudioProcessor()
voice_gateway_audio_processor = VoiceGatewayAudioProcessor()