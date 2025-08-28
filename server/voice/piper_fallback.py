"""
Piper Local TTS Fallback - Provides offline TTS when OpenAI API fails.
Fast, lightweight speech synthesis for reliability.
"""

import os
import subprocess
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import shutil

logger = logging.getLogger("alice.voice.piper")

class PiperTTSFallback:
    """Local TTS fallback using Piper for offline speech synthesis"""
    
    def __init__(self):
        self.piper_executable = self._find_piper_executable()
        self.voice_model_path = None
        self.audio_dir = Path(__file__).parent / "audio"
        
        # Try to locate a suitable English voice model
        self._locate_voice_model()
        
        self.available = self.piper_executable is not None and self.voice_model_path is not None
        
        if self.available:
            logger.info(f"Piper TTS available: {self.piper_executable} with model {self.voice_model_path}")
        else:
            logger.warning("Piper TTS not available - install piper-tts for offline fallback")
    
    def _find_piper_executable(self) -> Optional[str]:
        """Locate piper executable in system PATH or common locations"""
        
        # Check if piper is in PATH
        piper_path = shutil.which("piper")
        if piper_path:
            return piper_path
        
        # Check common installation locations
        common_paths = [
            "/usr/local/bin/piper",
            "/opt/homebrew/bin/piper",
            "~/bin/piper",
            "./piper/piper"  # Local installation
        ]
        
        for path in common_paths:
            expanded_path = Path(path).expanduser()
            if expanded_path.exists() and expanded_path.is_file():
                return str(expanded_path)
        
        return None
    
    def _locate_voice_model(self) -> None:
        """Find suitable English voice model for Piper"""
        
        # Common voice model locations
        model_search_paths = [
            Path("~/models/piper").expanduser(),
            Path("./models/piper"),
            Path("/usr/local/share/piper/models"),
            Path("/opt/homebrew/share/piper/models")
        ]
        
        # Look for English models (prefer female voices for consistency with Nova)
        preferred_models = [
            "en_US-amy-medium.onnx",
            "en_US-lessac-medium.onnx", 
            "en_US-ljspeech-medium.onnx",
            "en_US-amy-low.onnx",
            "en_GB-alba-medium.onnx"
        ]
        
        for search_path in model_search_paths:
            if not search_path.exists():
                continue
                
            for model_name in preferred_models:
                model_path = search_path / model_name
                if model_path.exists():
                    self.voice_model_path = str(model_path)
                    logger.debug(f"Found Piper voice model: {model_path}")
                    return
        
        # If no preferred models found, look for any English model
        for search_path in model_search_paths:
            if not search_path.exists():
                continue
                
            for model_file in search_path.glob("en_*-*.onnx"):
                self.voice_model_path = str(model_file)
                logger.debug(f"Using fallback Piper model: {model_file}")
                return
    
    async def synthesize(self, text: str, voice_output_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize speech using Piper TTS"""
        
        if not self.available:
            return {
                "success": False,
                "error": "Piper TTS not available - executable or voice model missing"
            }
        
        start_time = time.time()
        
        # Generate output filename
        timestamp = int(time.time() * 1000)
        output_file = self.audio_dir / f"piper_{timestamp}.wav"
        
        try:
            # Build Piper command
            # piper --model <model.onnx> --output_file <output.wav>
            command = [
                self.piper_executable,
                "--model", self.voice_model_path,
                "--output_file", str(output_file)
            ]
            
            # Add speed control if supported
            rate = voice_output_meta.get("rate", 1.0)
            if rate != 1.0 and self._supports_speed_control():
                command.extend(["--length_scale", str(1.0 / rate)])
            
            logger.debug(f"Running Piper TTS: {' '.join(command)}")
            
            # Run Piper with text input
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send text to stdin and wait for completion
            stdout, stderr = await process.communicate(text.encode('utf-8'))
            
            if process.returncode == 0 and output_file.exists():
                # Estimate duration (rough calculation)
                file_size = output_file.stat().st_size
                estimated_duration = file_size / 32000  # Rough estimate for 16kHz mono
                
                logger.info(f"Piper TTS success: {output_file.name} ({len(text)} chars)")
                
                return {
                    "success": True,
                    "audio_file": str(output_file),
                    "duration": estimated_duration,
                    "provider": "piper",
                    "model": Path(self.voice_model_path).name,
                    "processing_time": time.time() - start_time
                }
            else:
                error_msg = f"Piper failed with return code {process.returncode}"
                if stderr:
                    error_msg += f": {stderr.decode()}"
                
                logger.error(error_msg)
                
                # Clean up failed output file
                if output_file.exists():
                    output_file.unlink()
                
                return {
                    "success": False,
                    "error": error_msg,
                    "processing_time": time.time() - start_time
                }
                
        except asyncio.TimeoutError:
            error_msg = "Piper TTS timeout"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "processing_time": time.time() - start_time
            }
        except Exception as e:
            error_msg = f"Piper TTS error: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "processing_time": time.time() - start_time
            }
    
    def _supports_speed_control(self) -> bool:
        """Check if Piper version supports speed control"""
        
        try:
            # Run piper --help to check available options
            result = subprocess.run(
                [self.piper_executable, "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            return "length_scale" in result.stdout
        except Exception:
            return False
    
    def test_installation(self) -> Dict[str, Any]:
        """Test Piper installation and return diagnostic info"""
        
        info = {
            "executable_found": self.piper_executable is not None,
            "executable_path": self.piper_executable,
            "voice_model_found": self.voice_model_path is not None,
            "voice_model_path": self.voice_model_path,
            "available": self.available,
            "supports_speed": False
        }
        
        if self.available:
            info["supports_speed"] = self._supports_speed_control()
            
            # Try a quick test synthesis
            try:
                test_result = asyncio.run(self._quick_test_synthesis())
                info["test_synthesis"] = test_result
            except Exception as e:
                info["test_synthesis"] = {"success": False, "error": str(e)}
        
        return info
    
    async def _quick_test_synthesis(self) -> Dict[str, Any]:
        """Quick test to verify Piper can synthesize speech"""
        
        test_text = "Test."
        test_meta = {"rate": 1.0}
        
        result = await self.synthesize(test_text, test_meta)
        
        # Clean up test file if created
        if result.get("success") and result.get("audio_file"):
            try:
                Path(result["audio_file"]).unlink(missing_ok=True)
            except Exception:
                pass
        
        return {
            "success": result.get("success", False),
            "error": result.get("error"),
            "processing_time": result.get("processing_time", 0)
        }
    
    def get_installation_instructions(self) -> str:
        """Get instructions for installing Piper TTS"""
        
        return """
Piper TTS Installation Instructions:

1. Install Piper:
   macOS (Homebrew): brew install piper-tts
   Linux: pip install piper-tts
   Manual: Download from https://github.com/rhasspy/piper

2. Download English voice models:
   - Create directory: mkdir -p ~/models/piper
   - Download model: wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
   - Download config: wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

3. Verify installation:
   Run: python -c "from server.voice.piper_fallback import PiperTTSFallback; print(PiperTTSFallback().test_installation())"
"""