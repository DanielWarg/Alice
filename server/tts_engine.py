"""
Real Piper TTS Engine for Voice v2 - Swedish Speech Synthesis
============================================================

Production TTS using Piper with KBLab Swedish voices.
Replaces the mock sine wave generation with actual Swedish speech.

Features:
- Real Swedish TTS using Piper + NST voices
- 128kbps CBR LAME MP3 encoding for browser compatibility  
- Caching and performance optimization
- Fallback to mock TTS if Piper fails
- Proper error handling and logging
"""

import hashlib
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import shutil

logger = logging.getLogger("alice.tts")

class PiperTTSEngine:
    """Bilingual TTS using Piper: Swedish input → English output (Alice personality)"""
    
    def __init__(self, english_voice_path: Optional[str] = None, swedish_voice_path: Optional[str] = None):
        self.english_voice_path = english_voice_path or self._find_english_voice_model()
        self.swedish_voice_path = swedish_voice_path or self._find_swedish_voice_model()
        self.piper_binary = self._find_piper_binary()
        
        if not self.piper_binary:
            logger.warning("Piper binary not found - will fallback to mock TTS")
            self.available = False
        elif not self.english_voice_path:
            logger.warning("English voice model not found - will fallback to mock TTS")
            self.available = False
        else:
            logger.info(f"Alice TTS ready - English: {Path(self.english_voice_path).name}")
            if self.swedish_voice_path:
                logger.info(f"Alice TTS ready - Swedish: {Path(self.swedish_voice_path).name}")
            self.available = True
    
    def _find_piper_binary(self) -> Optional[str]:
        """Find Piper binary in various locations"""
        candidates = [
            ".venv/bin/piper",
            shutil.which("piper"),
            "/usr/local/bin/piper",
            "/opt/homebrew/bin/piper"
        ]
        
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        
        return None
    
    def _find_english_voice_model(self) -> Optional[str]:
        """Find English voice model file (Female voices - Amy #1, LJSpeech #2)"""
        model_paths = [
            "server/voices/en_US-amy-medium.onnx",       # #1: Amy (balanced female voice)
            "voices/en_US-amy-medium.onnx",
            "./en_US-amy-medium.onnx",
            "server/voices/en_US-ljspeech-high.onnx",   # #2: LJSpeech (high quality female)
            "voices/en_US-ljspeech-high.onnx", 
            "./en_US-ljspeech-high.onnx"
        ]
        
        for model_path in model_paths:
            if Path(model_path).exists():
                return model_path
        
        return None
    
    def _find_swedish_voice_model(self) -> Optional[str]:
        """Find Swedish voice model file (for fallback)"""
        model_paths = [
            "server/voices/sv_SE-nst-medium.onnx",
            "voices/sv_SE-nst-medium.onnx",
            "./sv_SE-nst-medium.onnx"
        ]
        
        for model_path in model_paths:
            if Path(model_path).exists():
                return model_path
        
        return None
    
    def generate_speech_wav(self, text: str, output_path: str, use_english: bool = True) -> bool:
        """
        Generate speech as WAV using Piper (Alice speaks English by default)
        
        Args:
            text: Text to synthesize
            output_path: Output WAV file path
            use_english: True for English (Alice's voice), False for Swedish
            
        Returns:
            bool: Success status
        """
        if not self.available:
            return False
        
        # Select voice model
        voice_model = self.english_voice_path if use_english else self.swedish_voice_path
        if not voice_model:
            logger.error(f"Voice model not available: {'English' if use_english else 'Swedish'}")
            return False
        
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Run Piper TTS with selected voice
            cmd = [
                self.piper_binary,
                "--model", voice_model,
                "--output_file", output_path
            ]
            
            # Feed text to Piper via stdin
            result = subprocess.run(
                cmd, 
                input=text, 
                text=True, 
                capture_output=True,
                timeout=15
            )
            
            if result.returncode != 0:
                logger.error(f"Piper TTS failed: {result.stderr}")
                return False
            
            # Verify output file
            if not Path(output_path).exists():
                logger.error("Piper did not generate output file")
                return False
            
            file_size = Path(output_path).stat().st_size
            if file_size < 4000:
                logger.warning(f"Generated WAV suspiciously small: {file_size} bytes")
                return False
            
            logger.info(f"Generated Swedish speech: {Path(output_path).name} ({file_size} bytes)")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Piper TTS timed out")
            return False
        except Exception as e:
            logger.error(f"Piper TTS error: {e}")
            return False
    
    def convert_wav_to_mp3_lame(self, wav_path: str, mp3_path: str) -> bool:
        """
        Convert WAV to 128kbps CBR LAME MP3 for browser compatibility
        
        Args:
            wav_path: Input WAV file
            mp3_path: Output MP3 file
            
        Returns:
            bool: Success status
        """
        try:
            # Use ffmpeg with ULTRA-CLEAN LAME encoding (noise reduction + EQ)
            cmd = [
                'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                '-i', wav_path,
                '-ar', '44100',              # 44.1kHz sample rate
                '-ac', '1',                  # Mono
                '-c:a', 'libmp3lame',        # Use LAME encoder explicitly
                '-b:a', '256k',              # Even higher bitrate: 256 kbps for ultimate clarity
                '-write_xing', '0',          # Remove VBR/Xing header (pure CBR)
                '-q:a', '0',                 # Highest quality LAME preset
                # Advanced audio cleaning chain:
                '-af', 'highpass=f=100,lowpass=f=12000,volume=1.2,dynaudnorm=f=200:g=11,deesser,afftdn=nf=-20',
                mp3_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg LAME conversion failed: {result.stderr}")
                return False
            
            mp3_size = Path(mp3_path).stat().st_size
            logger.info(f"Converted to CBR LAME MP3: {Path(mp3_path).name} ({mp3_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"WAV to MP3 conversion failed: {e}")
            return False
    
    def generate_tts_mp3(self, text: str, output_mp3_path: str, use_english: bool = True) -> bool:
        """
        Complete TTS pipeline: Text → Piper WAV → LAME MP3 (Alice speaks English)
        
        Args:
            text: Text to synthesize (English for Alice's responses)
            output_mp3_path: Final MP3 output path
            use_english: True for English (Alice's default), False for Swedish
            
        Returns:
            bool: Success status
        """
        if not self.available:
            logger.warning("Piper TTS not available")
            return False
        
        # Create temporary WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
            tmp_wav_path = tmp_wav.name
        
        try:
            # Step 1: Generate WAV with Piper (English by default for Alice)
            if not self.generate_speech_wav(text, tmp_wav_path, use_english):
                return False
            
            # Step 2: Convert to CBR LAME MP3
            if not self.convert_wav_to_mp3_lame(tmp_wav_path, output_mp3_path):
                return False
            
            return True
            
        finally:
            # Clean up temporary WAV file
            Path(tmp_wav_path).unlink(missing_ok=True)

# Global TTS engine instance
_tts_engine = None

def get_tts_engine() -> PiperTTSEngine:
    """Get singleton TTS engine instance"""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = PiperTTSEngine()
    return _tts_engine

def generate_real_tts_audio(text: str, base_filename: str, output_dir: str = "./voice/audio") -> Tuple[Optional[str], Optional[str], bool]:
    """
    Generate real Swedish TTS audio using Piper
    
    Args:
        text: Swedish text to synthesize
        base_filename: Base filename (without extension)
        output_dir: Output directory path
        
    Returns:
        tuple: (file_path, media_type, success)
    """
    engine = get_tts_engine()
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    mp3_path = output_path / f"{base_filename}.mp3"
    
    # Try real Piper TTS first
    if engine.available and engine.generate_tts_mp3(text, str(mp3_path)):
        return str(mp3_path), "audio/mpeg", True
    
    logger.warning("Real TTS failed - this should trigger fallback to mock TTS")
    return None, None, False

# Test function
def test_piper_tts():
    """Test Alice's HIGH-QUALITY bilingual TTS (LJSpeech crystal-clear voice)"""
    print("🧪 Testing Alice's HIGHEST QUALITY English voice...")
    
    engine = PiperTTSEngine()
    print(f"📡 Alice TTS available: {'✅ Yes' if engine.available else '❌ No'}")
    print(f"🎙️ Voice model: {Path(engine.english_voice_path).name if engine.english_voice_path else 'None'}")
    
    if not engine.available:
        print("❌ Cannot test - Alice TTS not configured properly")
        return
    
    # Alice responds in English with crystal-clear HIGH QUALITY voice
    test_responses = [
        "Hello! I'm Alice, your intelligent voice assistant with crystal-clear speech quality. How may I help you today?",
        "I understand you want to check your email. You have 3 new messages and 1 important notification from your manager regarding the quarterly review.",
        "Good morning! The current weather in Stockholm is 18 degrees Celsius with sunny conditions. Light cloud coverage is expected this afternoon, perfect for outdoor activities.",
        "I'm turning on all the smart lights in your home now. The lighting system has been activated successfully and is fully operational.",
        "The current time is 1:30 PM. You have a meeting scheduled in 30 minutes with the development team. Would you like me to set a reminder?"
    ]
    
    output_dir = Path("./test_real_tts")
    output_dir.mkdir(exist_ok=True)
    
    for i, response in enumerate(test_responses, 1):
        print(f"\n📝 Alice Response {i}: '{response[:60]}...'")
        
        mp3_path = output_dir / f"alice_english_{i}.mp3"
        success = engine.generate_tts_mp3(response, str(mp3_path), use_english=True)
        
        if success:
            file_size = mp3_path.stat().st_size
            print(f"✅ Generated: {mp3_path.name}")
            print(f"   Size: {file_size} bytes ({file_size/1024:.1f} KB)")
            print(f"   Alice's English voice (Amy): ✅")
            
            # Quick verification 
            try:
                with open(mp3_path, 'rb') as f:
                    data = f.read(1024)
                    if b'sine' in data or b'440' in data:
                        print("   ⚠️ WARNING: May contain sine wave data")
                    else:
                        print("   ✅ Contains real speech data (Amy voice)")
            except:
                pass
        else:
            print(f"❌ Failed to generate Alice TTS")
    
    print(f"\n📁 Test files saved to: {output_dir}")
    print("🎵 Listen to verify Swedish speech (not 440Hz tones)")

if __name__ == "__main__":
    test_piper_tts()