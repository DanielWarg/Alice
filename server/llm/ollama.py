"""
Ollama adapter with health check and TTFT measurement
"""

import os
import time
import json
import httpx
import logging
import asyncio
from typing import Dict, List, Any, Optional
from asyncio import Semaphore

from .manager import LLM, HealthStatus, LLMResponse

logger = logging.getLogger("alice.llm.ollama")

class OllamaAdapter(LLM):
    """Ollama LLM adapter with health monitoring and concurrency control"""
    
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("LLM_MODEL", "gpt-oss:20b")
        self.name = f"ollama:{self.model}"
        self.health_timeout = float(os.getenv("LLM_HEALTH_TIMEOUT_MS", "3000")) / 1000  # Increased for gpt-oss:20b
        self.max_ttft = float(os.getenv("LLM_MAX_TTFT_MS", "1200")) / 1000
        
        # Concurrency control - limit concurrent requests to prevent overload
        self.max_concurrent = int(os.getenv("OLLAMA_MAX_CONCURRENT", "3"))
        self._request_semaphore = Semaphore(self.max_concurrent)
        
        # Context window optimization
        self.context_window = int(os.getenv("OLLAMA_CONTEXT_WINDOW", "4096"))  # Reduced from 8192
        
        # Minimal health check prompt
        self.health_prompt = "Hej"
        
        logger.info(f"OllamaAdapter initialized: {self.base_url}, model={self.model}")
    
    async def health(self) -> HealthStatus:
        """
        Health check with TTFT measurement using minimal prompt.
        Returns ok=False if service down or TTFT > threshold.
        """
        try:
            start_time = time.time()
            
            # Test basic connectivity first
            async with httpx.AsyncClient(timeout=self.health_timeout) as client:
                # Quick ping to /api/tags
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    return HealthStatus(ok=False, error=f"Service unavailable: {response.status_code}")
                
                # Check if our model is available
                tags_data = response.json()
                models = [m.get("name", "") for m in tags_data.get("models", [])]
                if self.model not in models:
                    return HealthStatus(ok=False, error=f"Model {self.model} not found. Available: {models}")
                
                # TTFT test with minimal prompt
                ttft_start = time.time()
                generate_payload = {
                    "model": self.model,
                    "prompt": self.health_prompt,
                    "stream": False,
                    "keep_alive": os.getenv("LLM_KEEP_ALIVE", "10m"),  # Keep warm during health checks
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 5  # Very short response
                    }
                }
                
                response = await client.post(f"{self.base_url}/api/generate", json=generate_payload)
                ttft_ms = (time.time() - ttft_start) * 1000
                
                if response.status_code != 200:
                    return HealthStatus(ok=False, error=f"Generate failed: {response.status_code}")
                
                # Check if TTFT is acceptable
                if ttft_ms > self.max_ttft * 1000:
                    return HealthStatus(ok=False, tftt_ms=ttft_ms, 
                                      error=f"TTFT {ttft_ms:.0f}ms > {self.max_ttft*1000:.0f}ms threshold")
                
                return HealthStatus(ok=True, tftt_ms=ttft_ms)
                
        except httpx.TimeoutException:
            return HealthStatus(ok=False, error="Health check timeout")
        except Exception as e:
            return HealthStatus(ok=False, error=f"Health check error: {e}")
    
    async def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Any]] = None) -> LLMResponse:
        """
        Send chat request to Ollama with concurrency control.
        Converts messages to Ollama format and handles tool calls.
        """
        # Acquire semaphore to limit concurrent requests
        async with self._request_semaphore:
            try:
                start_time = time.time()
                
                # Convert messages to Ollama prompt format
                prompt = self._messages_to_prompt(messages)
                
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": os.getenv("LLM_KEEP_ALIVE", "15m"),  # Increased från 10m for better performance
                    "options": {
                        "temperature": float(os.getenv("LOCAL_AI_TEMPERATURE", "0.3")),
                        "num_predict": int(os.getenv("LOCAL_AI_MAX_TOKENS", "2048")),
                        "num_ctx": self.context_window  # Reduced context window för memory optimization
                    }
                }
                
                # Exponential backoff retry for 500 errors
                max_retries = 3
                base_delay = 1.0
                
                for attempt in range(max_retries + 1):
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            response = await client.post(f"{self.base_url}/api/generate", json=payload)
                            
                            # If 500 error and retries left, wait and retry
                            if response.status_code >= 500 and attempt < max_retries:
                                delay = base_delay * (2 ** attempt)  # Exponential backoff
                                logger.warning(f"Ollama 500 error, retry {attempt + 1}/{max_retries} after {delay}s")
                                await asyncio.sleep(delay)
                                continue
                            
                            response.raise_for_status()
                            result = response.json()
                            break  # Success, exit retry loop
                            
                    except httpx.RequestError as e:
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"Ollama connection error, retry {attempt + 1}/{max_retries} after {delay}s: {e}")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise  # Last attempt failed
                            
                text = result.get("response", "")
                
                # Extract tool calls if present
                tool_calls = self._extract_tool_calls(text)
                
                ttft_ms = (time.time() - start_time) * 1000
                
                logger.debug(f"Ollama response: {len(text)} chars, {ttft_ms:.1f}ms")
                
                return LLMResponse(
                    text=text,
                    tool_calls=tool_calls,
                    provider=self.name,
                    tftt_ms=ttft_ms
                )
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
                raise Exception(f"Ollama request failed: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Ollama request error: {e}")
                raise
    
    def _messages_to_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """Convert OpenAI-style messages to Ollama prompt"""
        prompt_parts = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "developer":
                prompt_parts.append(f"Developer: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
            elif role == "tool":
                tool_name = msg.get("name", "unknown")
                prompt_parts.append(f"Tool {tool_name} result: {content}")
        
        # Add assistant prefix for generation
        prompt_parts.append("Assistant:")
        
        return "\n\n".join(prompt_parts)
    
    def _extract_tool_calls(self, text: str) -> Optional[List[Any]]:
        """
        Extract tool calls from response text.
        Looks for both Harmony-style and legacy formats.
        """
        tool_calls = []
        
        # Try to find JSON blocks that might contain tool calls
        import re
        
        # Look for tool_calls in JSON format
        json_pattern = r'```json\s*(\{.*?\})\s*```|(\{[^}]*"tool_calls"[^}]*\})'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            json_text = match[0] or match[1]
            try:
                parsed = json.loads(json_text)
                if "tool_calls" in parsed:
                    tool_calls.extend(parsed["tool_calls"])
            except:
                continue
        
        # Look for individual tool calls
        tool_pattern = r'"tool_calls":\s*\[(.*?)\]'
        tool_matches = re.findall(tool_pattern, text, re.DOTALL)
        
        for match in tool_matches:
            try:
                calls = json.loads(f"[{match}]")
                tool_calls.extend(calls)
            except:
                continue
        
        return tool_calls if tool_calls else None