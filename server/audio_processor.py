"""
Audio post-processing for enhanced TTS quality
Implements audio normalization, filtering, and enhancement for Alice's voice
"""

import os
import subprocess
import tempfile
import logging
from typing import Optional, Dict, Any

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

# Global audio processor instance
audio_processor = AudioProcessor()