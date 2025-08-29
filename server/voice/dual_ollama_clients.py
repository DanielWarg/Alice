"""
Dual Ollama Clients - Fast/Deep separation for optimal performance
"""

import asyncio
import aiohttp
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("alice.voice.dual_ollama")

@dataclass
class OllamaResponse:
    """Standardized response from Ollama"""
    text: str
    model: str
    processing_time: float
    success: bool
    error: Optional[str] = None

class DualOllamaClient:
    """
    Dual Ollama client setup:
    - Fast instance (port 11435): 8B model for ≤130 chars
    - Deep instance (port 11434): 20B model for complex cases
    """
    
    def __init__(self):
        # Ollama instance endpoints
        self.fast_host = "http://localhost:11435"
        self.deep_host = "http://localhost:11434"
        
        # Model configurations
        self.fast_model = "gpt-oss:8b"
        self.deep_model = "gpt-oss:20b"
        
        # Optimized parameters for translation
        self.fast_params = {
            "temperature": 0.0,     # Deterministic for cache
            "num_predict": 60,      # Short responses
            "top_k": 40,           # Focused generation
            "top_p": 0.9,          # High probability mass
            "stop": ["\\n\\n", "Swedish:", "English:", "JSON:", "---"],
            "keep_alive": "15m",    # Keep loaded for fast responses
            "num_ctx": 1024,       # Context window
            "repeat_penalty": 1.0   # No creativity penalty
        }
        
        self.deep_params = {
            "temperature": 0.0,     # Still deterministic  
            "num_predict": 320,     # Longer responses allowed
            "top_k": 40,
            "top_p": 0.9,
            "stop": ["\\n\\n", "Swedish:", "English:", "JSON:", "---"],
            "keep_alive": "15m",
            "num_ctx": 1024,
            "repeat_penalty": 1.0
        }
        
        # Connection pooling
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Health tracking
        self.fast_healthy = True
        self.deep_healthy = True
        self.last_health_check = 0
        
    async def _ensure_session(self):
        """Ensure aiohttp session is available"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=5)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def _chat_request(self, host: str, model: str, messages: List[Dict], params: Dict) -> OllamaResponse:
        """Make chat request to specific Ollama instance"""
        
        await self._ensure_session()
        start_time = time.time()
        
        payload = {
            "model": model,
            "messages": messages,
            "options": params,
            "stream": False
        }
        
        try:
            async with self.session.post(f"{host}/api/chat", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    processing_time = time.time() - start_time
                    
                    return OllamaResponse(
                        text=data.get("message", {}).get("content", ""),
                        model=model,
                        processing_time=processing_time,
                        success=True
                    )
                else:
                    error_text = await response.text()
                    logger.error(f"Ollama {host} error {response.status}: {error_text}")
                    
                    return OllamaResponse(
                        text="",
                        model=model, 
                        processing_time=time.time() - start_time,
                        success=False,
                        error=f"HTTP {response.status}: {error_text[:100]}"
                    )
                    
        except asyncio.TimeoutError:
            return OllamaResponse(
                text="",
                model=model,
                processing_time=time.time() - start_time,
                success=False,
                error="Request timeout"
            )
        except Exception as e:
            return OllamaResponse(
                text="",
                model=model,
                processing_time=time.time() - start_time,
                success=False,
                error=f"Connection error: {str(e)}"
            )
    
    async def translate_fast(self, messages: List[Dict]) -> OllamaResponse:
        """Fast translation using 8B model"""
        
        logger.debug(f"Fast translation: {self.fast_model}")
        response = await self._chat_request(
            self.fast_host,
            self.fast_model,
            messages,
            self.fast_params
        )
        
        # Update health status
        self.fast_healthy = response.success
        
        return response
    
    async def translate_deep(self, messages: List[Dict]) -> OllamaResponse:
        """Deep translation using 20B model"""
        
        logger.debug(f"Deep translation: {self.deep_model}")
        response = await self._chat_request(
            self.deep_host,
            self.deep_model,
            messages,
            self.deep_params
        )
        
        # Update health status  
        self.deep_healthy = response.success
        
        return response
    
    async def translate_with_routing(self, messages: List[Dict], text_length: int, has_complex_patterns: bool) -> OllamaResponse:
        """Route translation to appropriate model based on complexity"""
        
        # Enhanced routing logic (matches production config)
        use_fast = (text_length <= 130 and not has_complex_patterns)
        
        if use_fast and self.fast_healthy:
            response = await self.translate_fast(messages)
            if response.success:
                return response
            else:
                logger.warning("Fast model failed, falling back to deep model")
        
        # Use deep model (either by routing or fallback)
        return await self.translate_deep(messages)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of both Ollama instances"""
        
        now = time.time()
        
        # Only check every 30 seconds
        if now - self.last_health_check < 30:
            return {
                "fast_healthy": self.fast_healthy,
                "deep_healthy": self.deep_healthy,
                "cached": True
            }
        
        await self._ensure_session()
        
        # Check fast instance
        try:
            async with self.session.get(f"{self.fast_host}/api/ps") as resp:
                self.fast_healthy = resp.status == 200
        except:
            self.fast_healthy = False
        
        # Check deep instance
        try:
            async with self.session.get(f"{self.deep_host}/api/ps") as resp:
                self.deep_healthy = resp.status == 200
        except:
            self.deep_healthy = False
        
        self.last_health_check = now
        
        return {
            "fast_healthy": self.fast_healthy,
            "deep_healthy": self.deep_healthy,
            "fast_endpoint": self.fast_host,
            "deep_endpoint": self.deep_host,
            "cached": False
        }
    
    async def warmup_models(self) -> Dict[str, Any]:
        """Send warmup requests to both models"""
        
        warmup_messages = [{
            "role": "user",
            "content": "Översätt: Hej Alice!"
        }]
        
        results = {}
        
        # Warmup fast model
        try:
            fast_response = await self.translate_fast(warmup_messages)
            results["fast"] = {
                "success": fast_response.success,
                "time": fast_response.processing_time,
                "error": fast_response.error
            }
        except Exception as e:
            results["fast"] = {"success": False, "error": str(e)}
        
        # Warmup deep model  
        try:
            deep_response = await self.translate_deep(warmup_messages)
            results["deep"] = {
                "success": deep_response.success,
                "time": deep_response.processing_time,
                "error": deep_response.error
            }
        except Exception as e:
            results["deep"] = {"success": False, "error": str(e)}
        
        return results
    
    async def close(self):
        """Clean up resources"""
        if self.session and not self.session.closed:
            await self.session.close()

# Global dual client instance
dual_ollama = DualOllamaClient()