"""
HTTP TTS Client - Handles OpenAI TTS API calls with caching and fallback chain.
Supports SSML phoneme tags for Swedish pronunciation.
"""

import os
import json
import hashlib
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import httpx
import logging

from .voice_cache import VoiceCache
from .orchestrator import VoiceOutput

logger = logging.getLogger("alice.voice.tts")

class TTSClient:
    """HTTP TTS client with caching and fallback support"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
            
        self.base_url = "https://api.openai.com/v1/audio/speech"
        self.timeout = 4.0  # Seconds for HTTP request
        self.retry_attempts = 2
        
        # Load configuration
        config_path = Path(__file__).parent / "voice_capabilities.json"
        with open(config_path) as f:
            self.config = json.load(f)
        
        # Initialize cache
        self.cache = VoiceCache(self.config["settings"]["cache_size"])
        
        # Audio storage
        self.audio_dir = Path(__file__).parent / "audio"
        self.audio_dir.mkdir(exist_ok=True)
        
        # SSML pronunciation support
        self.pronunciation_map = self.config.get("swedish_pronunciation", {})
        
        logger.info(f"TTSClient initialized with cache size {self.cache.max_size}")
    
    async def synthesize(self, voice_output: VoiceOutput) -> Dict[str, Any]:
        """
        Main synthesis method - handles caching, SSML, and fallback chain.
        Returns audio file path and metadata.
        """
        start_time = time.time()
        
        # Prepare text with SSML if needed
        processed_text = self._apply_ssml_pronunciation(voice_output.speak_text_en)
        
        # Create cache key
        cache_key = self._create_cache_key(processed_text, voice_output)
        
        # Check cache first
        cached_result = self.cache.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for key: {cache_key[:16]}...")
            return {
                "success": True,
                "audio_file": cached_result["audio_file"],
                "duration": cached_result["duration"], 
                "cached": True,
                "processing_time": time.time() - start_time
            }
        
        # Not in cache - synthesize new audio
        try:
            result = await self._synthesize_with_openai(processed_text, voice_output)
            
            if result["success"]:
                # Cache the result
                self.cache.put(cache_key, {
                    "audio_file": result["audio_file"],
                    "duration": result["duration"],
                    "created_at": time.time()
                })
                
                result["cached"] = False
                result["processing_time"] = time.time() - start_time
                return result
            else:
                # Primary TTS failed - try fallback chain
                return await self._try_fallback_chain(processed_text, voice_output, start_time)
                
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return await self._try_fallback_chain(processed_text, voice_output, start_time)
    
    async def _synthesize_with_openai(self, text: str, voice_output: VoiceOutput) -> Dict[str, Any]:
        """Synthesize using OpenAI TTS API"""
        
        # Select voice based on content and quality needs
        voice_name = self._select_voice(voice_output)
        model = self.config["voices"][voice_name]["model"]
        
        # Adjust speed if needed
        speed = voice_output.rate * self.config["voices"][voice_name].get("speed", 1.0)
        speed = max(0.25, min(4.0, speed))  # OpenAI limits
        
        request_data = {
            "model": model,
            "input": text,
            "voice": voice_name.split("-")[0],  # "nova-hd" -> "nova"
            "speed": speed,
            "response_format": "mp3"
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    json=request_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    # Save audio file
                    audio_filename = f"tts_{int(time.time() * 1000)}.mp3"
                    audio_path = self.audio_dir / audio_filename
                    
                    with open(audio_path, "wb") as f:
                        f.write(response.content)
                    
                    # Estimate duration (rough calculation)
                    char_count = len(text)
                    estimated_duration = char_count / 180 * speed  # ~180 chars per second baseline
                    
                    logger.info(f"OpenAI TTS success: {audio_filename} ({char_count} chars)")
                    
                    return {
                        "success": True,
                        "audio_file": str(audio_path),
                        "duration": estimated_duration,
                        "provider": "openai",
                        "voice": voice_name,
                        "model": model
                    }
                else:
                    error_msg = f"OpenAI TTS API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {"success": False, "error": error_msg}
                    
        except httpx.TimeoutException:
            error_msg = f"OpenAI TTS timeout after {self.timeout}s"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"OpenAI TTS request failed: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def _try_fallback_chain(self, text: str, voice_output: VoiceOutput, start_time: float) -> Dict[str, Any]:
        """Try fallback methods when primary TTS fails"""
        
        # Fallback 1: Piper local TTS
        try:
            piper_result = await self._synthesize_with_piper(text, voice_output)
            if piper_result["success"]:
                piper_result["processing_time"] = time.time() - start_time
                return piper_result
        except Exception as e:
            logger.error(f"Piper fallback failed: {e}")
        
        # Fallback 2: Text-only response
        logger.warning("All TTS methods failed - returning text-only response")
        return {
            "success": True,
            "audio_file": None,
            "duration": 0,
            "text_only": True,
            "provider": "fallback",
            "processing_time": time.time() - start_time,
            "text": text
        }
    
    async def _synthesize_with_piper(self, text: str, voice_output: VoiceOutput) -> Dict[str, Any]:
        """Fallback synthesis using local Piper TTS"""
        
        from .piper_fallback import PiperTTSFallback
        
        piper = PiperTTSFallback()
        
        if not piper.available:
            return {"success": False, "error": "Piper TTS not available"}
        
        # Use Piper to synthesize
        result = await piper.synthesize(text, voice_output.meta)
        
        if result["success"]:
            logger.info(f"Piper fallback success: {result['audio_file']}")
        
        return result
    
    def _apply_ssml_pronunciation(self, text: str) -> str:
        """Apply SSML phoneme tags for Swedish names/places"""
        
        processed_text = text
        
        for swedish_word, pronunciation in self.pronunciation_map.items():
            if swedish_word in processed_text:
                phoneme_tag = f'<phoneme alphabet="{pronunciation["alphabet"]}" ph="{pronunciation["phoneme"]}">{swedish_word}</phoneme>'
                processed_text = processed_text.replace(swedish_word, phoneme_tag)
        
        # Wrap in SSML speak tag if we added phonemes
        if "<phoneme" in processed_text:
            processed_text = f"<speak>{processed_text}</speak>"
            
        return processed_text
    
    def _select_voice(self, voice_output: VoiceOutput) -> str:
        """Select appropriate voice based on content and quality needs"""
        
        # Use HD voice for longer content or important sources
        use_hd = (
            voice_output.meta.get("source_type") in ["email", "calendar"] or
            len(voice_output.speak_text_en) > 100 or
            voice_output.style == "formal"
        )
        
        if use_hd and "nova-hd" in self.config["voices"]:
            return "nova-hd"
        else:
            return self.config["default_voice"]
    
    def _create_cache_key(self, text: str, voice_output: VoiceOutput) -> str:
        """Create unique cache key for text + voice settings"""
        
        voice_name = self._select_voice(voice_output)
        
        # Include relevant parameters that affect audio output
        cache_input = {
            "text": text,
            "voice": voice_name,
            "rate": voice_output.rate,
            "style": voice_output.style
        }
        
        cache_string = json.dumps(cache_input, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()
    
    async def warm_up(self) -> bool:
        """Warm up the TTS API with a test request"""
        
        try:
            test_text = "Hello, this is a test."
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            request_data = {
                "model": "tts-1",
                "input": test_text,
                "voice": "nova"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    json=request_data,
                    headers=headers
                )
                
                success = response.status_code == 200
                logger.info(f"TTS warm-up: {'success' if success else 'failed'}")
                return success
                
        except Exception as e:
            logger.error(f"TTS warm-up failed: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        return self.cache.get_stats()