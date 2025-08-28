"""
OpenAI adapter with health check and tool call support
"""

import os
import time
import json
import httpx
import logging
from typing import Dict, List, Any, Optional

from .manager import LLM, HealthStatus, LLMResponse

logger = logging.getLogger("alice.llm.openai")

class OpenAIAdapter(LLM):
    """OpenAI LLM adapter with health monitoring"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("FALLBACK_MODEL", "gpt-4o-mini")
        self.name = f"openai:{self.model}"
        self.base_url = "https://api.openai.com/v1"
        self.health_timeout = float(os.getenv("LLM_HEALTH_TIMEOUT_MS", "1500")) / 1000
        self.max_ttft = float(os.getenv("LLM_MAX_TTFT_MS", "1200")) / 1000
        
        # Simple health check messages
        self.health_messages = [{"role": "user", "content": "Hi"}]
        
        if not self.api_key:
            raise ValueError("OpenAI API key required")
            
        logger.info(f"OpenAIAdapter initialized: model={self.model}")
    
    async def health(self) -> HealthStatus:
        """
        Health check with TTFT measurement using minimal request.
        Tests both connectivity and model availability.
        """
        try:
            start_time = time.time()
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": self.health_messages,
                "max_tokens": 5,
                "temperature": 0.1
            }
            
            async with httpx.AsyncClient(timeout=self.health_timeout) as client:
                response = await client.post(f"{self.base_url}/chat/completions", 
                                           json=payload, headers=headers)
                
                ttft_ms = (time.time() - start_time) * 1000
                
                if response.status_code == 401:
                    return HealthStatus(ok=False, error="Invalid API key")
                elif response.status_code == 429:
                    return HealthStatus(ok=False, error="Rate limited")
                elif response.status_code != 200:
                    return HealthStatus(ok=False, error=f"API error: {response.status_code}")
                
                # Check if TTFT is acceptable for FAST path
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
        Send chat request to OpenAI with tool support.
        Handles both regular chat and tool calls.
        """
        try:
            start_time = time.time()
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": float(os.getenv("FALLBACK_TEMPERATURE", "0.6")),
                "max_tokens": int(os.getenv("FAST_PATH_MAX_TOKENS", "150"))
            }
            
            # Add tools if provided
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.base_url}/chat/completions", 
                                           json=payload, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                
                if "choices" not in result or not result["choices"]:
                    raise Exception("No choices in OpenAI response")
                
                choice = result["choices"][0]
                message = choice.get("message", {})
                
                text = message.get("content", "") or ""
                tool_calls = message.get("tool_calls", [])
                
                ttft_ms = (time.time() - start_time) * 1000
                
                logger.debug(f"OpenAI response: {len(text)} chars, {ttft_ms:.1f}ms, {len(tool_calls)} tools")
                
                return LLMResponse(
                    text=text,
                    tool_calls=tool_calls if tool_calls else None,
                    provider=self.name,
                    tftt_ms=ttft_ms
                )
                
        except httpx.HTTPStatusError as e:
            error_text = ""
            try:
                error_data = e.response.json()
                error_text = error_data.get("error", {}).get("message", "")
            except:
                error_text = e.response.text
            
            logger.error(f"OpenAI HTTP error: {e.response.status_code} - {error_text}")
            raise Exception(f"OpenAI request failed: {e.response.status_code} - {error_text}")
        except Exception as e:
            logger.error(f"OpenAI request error: {e}")
            raise