"""
ModelManager - LLM abstraction with health check and circuit breaker
"""

import os
import time
import logging
from typing import Any, Dict, List, Optional, Protocol
from dataclasses import dataclass

logger = logging.getLogger("alice.llm")

@dataclass
class HealthStatus:
    ok: bool
    tftt_ms: Optional[float] = None
    error: Optional[str] = None

@dataclass
class LLMResponse:
    text: str
    tool_calls: Optional[List[Any]] = None
    provider: str = ""
    tftt_ms: Optional[float] = None

class LLM(Protocol):
    """LLM interface for adapters"""
    name: str
    
    async def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Any]] = None) -> LLMResponse:
        """Send chat request and return response"""
        ...
    
    async def health(self) -> HealthStatus:
        """Check health and measure time-to-first-token"""
        ...

class ModelManager:
    """
    Manages primary and fallback LLM providers with circuit breaker pattern.
    Automatically routes requests based on health and failure count.
    """
    
    def __init__(self, primary: LLM, fallback: LLM):
        self.primary = primary
        self.fallback = fallback
        self.failure_count = 0
        self.circuit_breaker_threshold = int(os.getenv("LLM_CIRCUIT_BREAKER_FAILS", "3"))
        self.last_health_check = 0
        self.health_cache_duration = 30  # seconds
        self.cached_health: Optional[HealthStatus] = None
        
        logger.info(f"ModelManager initialized with primary={primary.name}, fallback={fallback.name}")
    
    async def _is_primary_healthy(self) -> bool:
        """Check if primary provider is healthy (with caching)"""
        now = time.time()
        
        # Use cached health if recent
        if (self.cached_health and 
            now - self.last_health_check < self.health_cache_duration):
            return self.cached_health.ok
        
        # Perform fresh health check
        try:
            health = await self.primary.health()
            self.cached_health = health
            self.last_health_check = now
            
            if health.ok:
                logger.debug(f"Primary {self.primary.name} healthy (TTFT: {health.tftt_ms}ms)")
            else:
                logger.warning(f"Primary {self.primary.name} unhealthy: {health.error}")
                
            return health.ok
            
        except Exception as e:
            logger.error(f"Health check failed for {self.primary.name}: {e}")
            self.cached_health = HealthStatus(ok=False, error=str(e))
            self.last_health_check = now
            return False
    
    async def _should_use_primary(self) -> bool:
        """Determine if we should use primary provider based on health and circuit breaker"""
        # Circuit breaker: too many recent failures
        if self.failure_count >= self.circuit_breaker_threshold:
            logger.info(f"Circuit breaker OPEN: {self.failure_count} failures >= {self.circuit_breaker_threshold}")
            return False
        
        # Health check
        is_healthy = await self._is_primary_healthy()
        if not is_healthy:
            logger.info(f"Primary {self.primary.name} is unhealthy, using fallback")
            return False
            
        return True
    
    async def ask(self, messages: List[Dict[str, Any]], tools: Optional[List[Any]] = None) -> LLMResponse:
        """
        Send request to appropriate provider with automatic failover.
        Returns response with provider information.
        """
        use_primary = await self._should_use_primary()
        target = self.primary if use_primary else self.fallback
        
        logger.debug(f"Routing request to {target.name} (primary_healthy={use_primary})")
        
        try:
            start_time = time.time()
            response = await target.chat(messages, tools)
            
            # Success - reset failure counter if we used primary
            if target == self.primary:
                if self.failure_count > 0:
                    logger.info(f"Primary {self.primary.name} recovered, resetting failure count")
                    self.failure_count = 0
            
            # Add metadata
            response.provider = target.name
            if not response.tftt_ms:
                response.tftt_ms = (time.time() - start_time) * 1000
            
            logger.debug(f"Response from {target.name}: {len(response.text)} chars, {response.tftt_ms:.1f}ms")
            return response
            
        except Exception as e:
            logger.error(f"Request failed with {target.name}: {e}")
            
            # If primary failed, increment failure counter and try fallback
            if target == self.primary:
                self.failure_count += 1
                logger.warning(f"Primary failure count: {self.failure_count}/{self.circuit_breaker_threshold}")
                
                # Hard failover to fallback
                try:
                    logger.info(f"Attempting hard failover to {self.fallback.name}")
                    start_time = time.time()
                    response = await self.fallback.chat(messages, tools)
                    response.provider = f"{self.fallback.name} (failover)"
                    response.tftt_ms = (time.time() - start_time) * 1000
                    return response
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
                    raise Exception(f"Both providers failed. Primary: {e}, Fallback: {fallback_error}")
            
            # If fallback failed, re-raise
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status for monitoring/UI"""
        return {
            "primary": {
                "name": self.primary.name,
                "failure_count": self.failure_count,
                "circuit_breaker_open": self.failure_count >= self.circuit_breaker_threshold,
                "last_health_check": self.last_health_check,
                "health_status": self.cached_health.__dict__ if self.cached_health else None
            },
            "fallback": {
                "name": self.fallback.name
            },
            "threshold": self.circuit_breaker_threshold
        }
    
    def reset_circuit_breaker(self):
        """Manually reset circuit breaker (for admin/testing)"""
        old_count = self.failure_count
        self.failure_count = 0
        self.cached_health = None  # Force fresh health check
        logger.info(f"Circuit breaker reset manually (was {old_count} failures)")