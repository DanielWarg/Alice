"""
Professional HTTP client with timeouts, retries, and circuit breaker patterns
for Alice AI Assistant external API integrations.
"""

import asyncio
import time
import logging
from typing import Any, Dict, Optional, Union, List
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum

import httpx
from httpx import Response, RequestError, TimeoutException, HTTPStatusError

logger = logging.getLogger("alice.http_client")


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Circuit is open, requests fail fast
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern"""
    failure_threshold: int = 5  # Number of failures to open circuit
    recovery_timeout: int = 60  # Seconds to wait before trying half-open
    success_threshold: int = 2  # Successes needed in half-open to close
    timeout_seconds: float = 10.0  # Request timeout


@dataclass 
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    backoff_factor: float = 1.0  # Exponential backoff multiplier
    backoff_max: float = 60.0   # Maximum backoff delay
    retry_on_status: List[int] = field(default_factory=lambda: [429, 502, 503, 504])


class CircuitBreaker:
    """Circuit breaker implementation for external API calls"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        
    def can_execute(self) -> bool:
        """Check if request should be allowed"""
        if self.state == CircuitState.CLOSED:
            return True
            
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit breaker {self.name}: OPEN -> HALF_OPEN")
                return True
            return False
            
        # HALF_OPEN state
        return True
    
    def record_success(self):
        """Record successful request"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker {self.name}: HALF_OPEN -> CLOSED")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED and self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name}: CLOSED -> OPEN ({self.failure_count} failures)")
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name}: HALF_OPEN -> OPEN (recovery failed)")


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class AliceHTTPClient:
    """Professional HTTP client with retry and circuit breaker patterns"""
    
    def __init__(self, service_name: str = "default"):
        self.service_name = service_name
        self.circuit_breaker = CircuitBreaker(
            service_name, 
            CircuitBreakerConfig()
        )
        self.retry_config = RetryConfig()
        
        # Default timeout configuration
        self.default_timeout = httpx.Timeout(
            connect=5.0,    # Connection timeout
            read=30.0,      # Read timeout  
            write=10.0,     # Write timeout
            pool=5.0        # Pool timeout
        )
    
    async def _execute_with_retries(
        self,
        method: str,
        url: str,
        retry_config: Optional[RetryConfig] = None,
        **kwargs
    ) -> Response:
        """Execute HTTP request with retry logic"""
        
        config = retry_config or self.retry_config
        last_exception = None
        
        for attempt in range(config.max_retries + 1):
            try:
                timeout = kwargs.get('timeout', self.default_timeout)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    
                    # Make the request
                    response = await client.request(method, url, **kwargs)
                    
                    # Check if we should retry on this status
                    if response.status_code in config.retry_on_status and attempt < config.max_retries:
                        backoff_delay = min(
                            config.backoff_factor * (2 ** attempt),
                            config.backoff_max
                        )
                        logger.warning(
                            f"HTTP {response.status_code} for {url}, "
                            f"retrying in {backoff_delay}s (attempt {attempt + 1}/{config.max_retries})"
                        )
                        await asyncio.sleep(backoff_delay)
                        continue
                    
                    # Success or non-retryable status
                    return response
                    
            except (RequestError, TimeoutException) as e:
                last_exception = e
                if attempt < config.max_retries:
                    backoff_delay = min(
                        config.backoff_factor * (2 ** attempt),
                        config.backoff_max
                    )
                    logger.warning(
                        f"Request failed: {str(e)}, "
                        f"retrying in {backoff_delay}s (attempt {attempt + 1}/{config.max_retries})"
                    )
                    await asyncio.sleep(backoff_delay)
                    continue
                else:
                    break
        
        # All retries exhausted
        if last_exception:
            raise last_exception
        else:
            # Should not happen, but just in case
            raise RuntimeError(f"All retries exhausted for {method} {url}")
    
    async def request(
        self,
        method: str,
        url: str,
        *,
        circuit_breaker: bool = True,
        retry_config: Optional[RetryConfig] = None,
        **kwargs
    ) -> Response:
        """Make HTTP request with circuit breaker and retry logic"""
        
        # Check circuit breaker
        if circuit_breaker and not self.circuit_breaker.can_execute():
            raise CircuitBreakerError(
                f"Circuit breaker {self.service_name} is OPEN - failing fast"
            )
        
        try:
            response = await self._execute_with_retries(
                method, url, retry_config, **kwargs
            )
            
            # Record success for circuit breaker
            if circuit_breaker:
                self.circuit_breaker.record_success()
            
            return response
            
        except Exception as e:
            # Record failure for circuit breaker
            if circuit_breaker:
                self.circuit_breaker.record_failure()
            raise
    
    # Convenience methods
    async def get(self, url: str, **kwargs) -> Response:
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> Response:
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> Response:
        return await self.request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> Response:
        return await self.request("DELETE", url, **kwargs)
    
    async def patch(self, url: str, **kwargs) -> Response:
        return await self.request("PATCH", url, **kwargs)


# Service-specific client instances
spotify_client = AliceHTTPClient("spotify")
ollama_client = AliceHTTPClient("ollama") 
openai_client = AliceHTTPClient("openai")
google_client = AliceHTTPClient("google")
weather_client = AliceHTTPClient("weather")


@asynccontextmanager
async def resilient_http_client(
    service_name: str = "default",
    timeout_seconds: float = 10.0,
    max_retries: int = 3
):
    """
    Context manager for creating resilient HTTP client
    
    Usage:
        async with resilient_http_client("spotify", timeout_seconds=5.0) as client:
            response = await client.get("https://api.spotify.com/v1/me")
    """
    
    client = AliceHTTPClient(service_name)
    client.retry_config.max_retries = max_retries
    client.default_timeout = httpx.Timeout(timeout_seconds)
    
    try:
        yield client
    finally:
        # Any cleanup if needed
        pass


async def safe_external_call(
    service_name: str,
    method: str,
    url: str,
    timeout: float = 10.0,
    max_retries: int = 3,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Safe wrapper for external API calls with full error handling
    Returns None on failure instead of raising exceptions
    """
    
    try:
        async with resilient_http_client(service_name, timeout, max_retries) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                return response.json()
            except ValueError:
                # Return text response if not JSON
                return {"text": response.text, "status": response.status_code}
                
    except CircuitBreakerError as e:
        logger.error(f"Circuit breaker open for {service_name}: {e}")
        return None
        
    except HTTPStatusError as e:
        logger.error(f"HTTP error for {service_name}: {e.response.status_code}")
        return None
        
    except (RequestError, TimeoutException) as e:
        logger.error(f"Request error for {service_name}: {str(e)}")
        return None
        
    except Exception as e:
        logger.error(f"Unexpected error for {service_name}: {str(e)}")
        return None


# Example Swedish time parsing integration helper
async def robust_datetime_api_call(
    service_name: str,
    url: str,
    datetime_params: Dict[str, Any],
    timeout: float = 5.0
) -> Optional[Dict[str, Any]]:
    """
    Robust API call with Swedish datetime parameter handling
    Handles timezone conversion and formatting
    """
    
    try:
        # Convert Swedish datetime formats to ISO
        processed_params = {}
        for key, value in datetime_params.items():
            if isinstance(value, str) and any(word in value.lower() for word in ["idag", "imorgon", "kl"]):
                # Would integrate with Swedish datetime parser here
                processed_params[key] = value  # Placeholder
            else:
                processed_params[key] = value
        
        return await safe_external_call(
            service_name=service_name,
            method="GET",
            url=url,
            timeout=timeout,
            params=processed_params
        )
        
    except Exception as e:
        logger.error(f"DateTime API call failed: {e}")
        return None