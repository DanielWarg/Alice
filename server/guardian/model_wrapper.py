#!/usr/bin/env python3
"""
Alice Model Wrapper - Deterministisk request hantering
=====================================================

Ansvar:
- Timeout protection (45s hard limit)
- Request queuing med concurrency limit
- Circuit breaker pattern
- Guardian integration (intake blocking)

INGEN AI-logik - bara deterministiska mönster.
"""

import os
import time
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import httpx
import json
from datetime import datetime, timedelta

# Simple queue implementation
class RequestQueue:
    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self.current_concurrent = 0
        self.queue: List[asyncio.Future] = []
        self.lock = asyncio.Lock()
    
    async def set_max_concurrent(self, value: int):
        """Ändra max samtidighet (från Guardian degrade)"""
        async with self.lock:
            self.max_concurrent = max(1, value)
    
    async def acquire(self):
        """Vänta på ledig plats i kön"""
        while True:
            async with self.lock:
                if self.current_concurrent < self.max_concurrent:
                    self.current_concurrent += 1
                    return
            await asyncio.sleep(0.1)
    
    async def release(self):
        """Frigör plats i kön"""
        async with self.lock:
            self.current_concurrent = max(0, self.current_concurrent - 1)

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, reject requests  
    HALF_OPEN = "half_open" # Testing if recovered

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5          # Failures innan open
    recovery_timeout_s: int = 10        # Tid innan half_open test
    timeout_s: int = 45                 # Request timeout
    success_threshold: int = 2          # Successes för att stänga

class CircuitBreaker:
    """Deterministisk circuit breaker - inga AI-beslut"""
    
    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.logger = logging.getLogger("wrapper.circuit_breaker")
    
    def can_execute(self) -> bool:
        """Deterministisk check om request ska köras"""
        now = datetime.now()
        
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if (self.last_failure_time and 
                now - self.last_failure_time > timedelta(seconds=self.config.recovery_timeout_s)):
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                self.logger.info("Circuit breaker: OPEN → HALF_OPEN")
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Registrera lyckad request"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.logger.info("Circuit breaker: HALF_OPEN → CLOSED")
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Registrera misslyckad request"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                self.logger.warning(f"Circuit breaker: CLOSED → OPEN (failures: {self.failure_count})")
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.logger.warning("Circuit breaker: HALF_OPEN → OPEN")

class ModelWrapper:
    """Huvudklass för säker modell-kommunikation"""
    
    def __init__(self, 
                 ollama_base_url: str = "http://localhost:11434",
                 alice_base_url: str = "http://localhost:3000",
                 model: str = "gpt-oss:20b"):
        
        self.ollama_base_url = ollama_base_url
        self.alice_base_url = alice_base_url  
        self.model = model
        
        self.queue = RequestQueue(max_concurrent=2)
        self.circuit_breaker = CircuitBreaker()
        self.logger = logging.getLogger("wrapper")
        
        # Intake blocking från Guardian
        self._intake_blocked = False
        
    async def check_intake_status(self) -> bool:
        """Kontrollera om Guardian har blockerat intake"""
        try:
            url = f"{self.alice_base_url}/api/guard/stop-intake"
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    self._intake_blocked = data.get("intakeBlocked", False)
                return self._intake_blocked
        except:
            return self._intake_blocked  # Fallback till cached value
    
    async def ollama_generate(self, prompt: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Säker kommunikation med Ollama med alla skydd aktiverade
        """
        # 1. Check intake blocking
        if await self.check_intake_status():
            raise Exception("Request blocked by Guardian (system overload)")
        
        # 2. Check circuit breaker  
        if not self.circuit_breaker.can_execute():
            raise Exception(f"Circuit breaker {self.circuit_breaker.state.value} - too many failures")
        
        # 3. Acquire queue slot
        await self.queue.acquire()
        
        try:
            # 4. Execute with timeout
            start_time = time.time()
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "15m",  # Längre för test-scenarion
                "options": options or {
                    "temperature": 0.7,
                    "num_predict": 200  # Reasonable limit
                }
            }
            
            timeout = self.circuit_breaker.config.timeout_s
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Record metrics
                duration_ms = (time.time() - start_time) * 1000
                response_text = result.get("response", "")
                
                self.logger.info(f"Success: {len(response_text)} chars, {duration_ms:.0f}ms")
                
                # Circuit breaker success
                self.circuit_breaker.record_success()
                
                return {
                    "response": response_text,
                    "model": self.model,
                    "duration_ms": duration_ms,
                    "success": True
                }
                
        except Exception as e:
            # Circuit breaker failure
            self.circuit_breaker.record_failure()
            
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            self.logger.error(f"Failed: {error_msg} ({duration_ms:.0f}ms)")
            
            raise Exception(f"Model request failed: {error_msg}")
            
        finally:
            # 5. Always release queue slot
            await self.queue.release()
    
    async def degrade(self) -> Dict[str, Any]:
        """Minska samtidighet (kallad av Guardian)"""
        current = self.queue.max_concurrent
        new_value = max(1, current - 1)
        await self.queue.set_max_concurrent(new_value)
        
        self.logger.warning(f"Degraded: concurrency {current} → {new_value}")
        return {"concurrency": new_value, "degraded": True}
    
    async def get_status(self) -> Dict[str, Any]:
        """Status för monitoring"""
        return {
            "model": self.model,
            "queue": {
                "max_concurrent": self.queue.max_concurrent,
                "current_concurrent": self.queue.current_concurrent
            },
            "circuit_breaker": {
                "state": self.circuit_breaker.state.value,
                "failure_count": self.circuit_breaker.failure_count,
                "success_count": self.circuit_breaker.success_count
            },
            "intake_blocked": self._intake_blocked
        }

# Global instance (för enkel integration)
_model_wrapper = None

def get_model_wrapper() -> ModelWrapper:
    """Singleton access"""
    global _model_wrapper
    if _model_wrapper is None:
        _model_wrapper = ModelWrapper()
    return _model_wrapper

# Convenience functions för Alice integration
async def safe_generate(prompt: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    """Säker generation genom wrapper"""
    wrapper = get_model_wrapper()
    return await wrapper.ollama_generate(prompt, options)

async def degrade_concurrency() -> Dict[str, Any]:
    """Minska samtidighet (kallad av Guardian)"""
    wrapper = get_model_wrapper()
    return await wrapper.degrade()

async def get_wrapper_status() -> Dict[str, Any]:
    """Status för monitoring"""
    wrapper = get_model_wrapper()
    return await wrapper.get_status()

# Test script
async def test_wrapper():
    """Test av wrapper funktionalitet"""
    print("🧪 Testing Model Wrapper...")
    
    wrapper = ModelWrapper()
    
    # Test basic generation
    try:
        result = await wrapper.ollama_generate("Hej, vad heter du?")
        print(f"✅ Basic test: {result['response'][:50]}...")
    except Exception as e:
        print(f"❌ Basic test failed: {e}")
    
    # Test concurrency degradation  
    status_before = await wrapper.get_status()
    await wrapper.degrade()
    status_after = await wrapper.get_status()
    
    print(f"📉 Concurrency: {status_before['queue']['max_concurrent']} → {status_after['queue']['max_concurrent']}")
    
    # Test status
    status = await wrapper.get_status()
    print(f"📊 Status: {json.dumps(status, indent=2)}")

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_wrapper())