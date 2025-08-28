"""
Enhanced API Client Manager with Rate Limiting and Graceful Degradation
Production-ready client management for external services (Google, Spotify, etc.)
"""
import asyncio
import httpx
import logging
import time
from typing import Dict, Any, Optional, List, Tuple, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from urllib.parse import urlencode
import json
from contextlib import asynccontextmanager

logger = logging.getLogger("alice.api_client_manager")

class ServiceStatus(Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"

class FallbackStrategy(Enum):
    """Fallback strategies for service failures"""
    FAIL_FAST = "fail_fast"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    CACHED_RESPONSE = "cached_response"
    ALTERNATIVE_SERVICE = "alternative_service"

@dataclass
class ServiceConfig:
    """Configuration for an external service"""
    name: str
    base_url: str
    timeout: int = 30
    max_retries: int = 3
    retry_backoff: float = 1.0
    
    # Rate limiting (per service)
    rate_limit: int = 100  # requests per minute
    burst_limit: int = 120
    
    # Health check
    health_check_url: Optional[str] = None
    health_check_interval: int = 300  # 5 minutes
    
    # Fallback configuration
    fallback_strategy: FallbackStrategy = FallbackStrategy.GRACEFUL_DEGRADATION
    cache_ttl: int = 3600  # 1 hour
    
    # Circuit breaker
    failure_threshold: int = 5  # failures before circuit opens
    recovery_timeout: int = 60  # seconds before trying to close circuit

@dataclass
class ServiceMetrics:
    """Metrics for service monitoring"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    consecutive_failures: int = 0
    status: ServiceStatus = ServiceStatus.HEALTHY

@dataclass
class CircuitBreaker:
    """Circuit breaker for service protection"""
    state: str = "closed"  # closed, open, half_open
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None

class APIClientManager:
    """
    Centralized API client manager with rate limiting, circuit breaking, and graceful degradation
    """
    
    def __init__(self):
        self.services: Dict[str, ServiceConfig] = {}
        self.clients: Dict[str, httpx.AsyncClient] = {}
        self.metrics: Dict[str, ServiceMetrics] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.rate_limiters: Dict[str, Dict] = {}  # Service-specific rate limiters
        self.cache: Dict[str, Dict] = {}  # Simple in-memory cache
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Global configuration
        self.global_timeout = 30
        self.max_concurrent_requests = 100
        self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        # Register default services
        self._register_default_services()
    
    def _register_default_services(self):
        """Register Alice's default external services"""
        
        # Google Services
        self.register_service(ServiceConfig(
            name="google_calendar",
            base_url="https://www.googleapis.com/calendar/v3",
            timeout=15,
            max_retries=2,
            rate_limit=1000,  # Google has generous limits
            burst_limit=1200,
            health_check_url="https://www.googleapis.com/discovery/v1/apis/calendar/v3/rest",
            fallback_strategy=FallbackStrategy.CACHED_RESPONSE,
            cache_ttl=900  # 15 minutes for calendar data
        ))
        
        self.register_service(ServiceConfig(
            name="gmail",
            base_url="https://gmail.googleapis.com/gmail/v1",
            timeout=20,
            max_retries=2,
            rate_limit=250,  # Gmail has stricter limits
            burst_limit=300,
            health_check_url="https://gmail.googleapis.com/discovery/v1/apis/gmail/v1/rest",
            fallback_strategy=FallbackStrategy.GRACEFUL_DEGRADATION,
            cache_ttl=300  # 5 minutes for email data
        ))
        
        # Spotify
        self.register_service(ServiceConfig(
            name="spotify",
            base_url="https://api.spotify.com/v1",
            timeout=10,
            max_retries=2,
            rate_limit=100,  # Conservative limit
            burst_limit=150,
            health_check_url="https://api.spotify.com/v1/browse/categories?limit=1",
            fallback_strategy=FallbackStrategy.CACHED_RESPONSE,
            cache_ttl=1800  # 30 minutes for music data
        ))
        
        # OpenAI (for backup when local models fail)
        self.register_service(ServiceConfig(
            name="openai",
            base_url="https://api.openai.com/v1",
            timeout=60,  # Longer timeout for AI responses
            max_retries=1,  # Don't retry expensive AI calls aggressively
            rate_limit=50,   # Conservative for cost management
            burst_limit=60,
            fallback_strategy=FallbackStrategy.ALTERNATIVE_SERVICE,
            cache_ttl=0  # Don't cache AI responses
        ))
    
    def register_service(self, config: ServiceConfig):
        """Register a new service configuration"""
        self.services[config.name] = config
        self.metrics[config.name] = ServiceMetrics()
        self.circuit_breakers[config.name] = CircuitBreaker()
        self.rate_limiters[config.name] = {
            "requests": [],
            "last_reset": time.time()
        }
        
        # Create HTTP client for service
        self.clients[config.name] = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )
        
        logger.info(f"Registered service: {config.name} ({config.base_url})")
    
    async def request(
        self,
        service: str,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        timeout: Optional[int] = None,
        fallback_response: Optional[Any] = None
    ) -> Tuple[bool, Any, str]:
        """
        Make API request with comprehensive error handling
        
        Returns:
            (success: bool, response_data: Any, error_message: str)
        """
        if service not in self.services:
            return False, None, f"Okänd tjänst: {service}"
        
        config = self.services[service]
        metrics = self.metrics[service]
        circuit_breaker = self.circuit_breakers[service]
        
        # Check circuit breaker
        if not self._can_make_request(circuit_breaker, config):
            error_msg = f"Tjänsten {service} är tillfälligt otillgänglig (circuit breaker öppen)"
            return await self._handle_fallback(service, config, fallback_response, error_msg)
        
        # Check rate limits
        if not self._check_rate_limit(service):
            error_msg = f"Hastighetsbegränsning nådd för tjänst {service}"
            return await self._handle_fallback(service, config, fallback_response, error_msg)
        
        # Acquire concurrency semaphore
        async with self._semaphore:
            return await self._make_request(
                service, config, metrics, circuit_breaker,
                method, path, headers, params, json_data, data,
                timeout or config.timeout, fallback_response
            )
    
    async def _make_request(
        self,
        service: str,
        config: ServiceConfig,
        metrics: ServiceMetrics,
        circuit_breaker: CircuitBreaker,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]],
        params: Optional[Dict[str, Any]],
        json_data: Optional[Dict[str, Any]],
        data: Optional[Any],
        timeout: int,
        fallback_response: Optional[Any]
    ) -> Tuple[bool, Any, str]:
        """Execute the actual API request with retries"""
        
        client = self.clients[service]
        start_time = time.time()
        last_error = ""
        
        for attempt in range(config.max_retries + 1):
            try:
                # Update metrics
                metrics.total_requests += 1
                metrics.last_request_time = datetime.utcnow()
                
                # Make the request
                response = await client.request(
                    method=method,
                    url=path,
                    headers=headers,
                    params=params,
                    json=json_data,
                    data=data,
                    timeout=timeout
                )
                
                # Calculate response time
                response_time = time.time() - start_time
                self._update_response_time(metrics, response_time)
                
                # Handle different response status codes
                if response.status_code < 400:
                    # Success
                    metrics.successful_requests += 1
                    metrics.last_success_time = datetime.utcnow()
                    self._reset_circuit_breaker(circuit_breaker)
                    
                    try:
                        response_data = response.json() if response.content else {}
                    except:
                        response_data = response.text
                    
                    # Cache successful responses if configured
                    if config.cache_ttl > 0:
                        self._cache_response(service, f"{method}:{path}", response_data, config.cache_ttl)
                    
                    return True, response_data, ""
                
                elif response.status_code == 429:
                    # Rate limited by service
                    retry_after = int(response.headers.get("Retry-After", 60))
                    last_error = f"Tjänsten {service} begränsar hastighet. Försök igen om {retry_after} sekunder."
                    
                    if attempt < config.max_retries:
                        await asyncio.sleep(min(retry_after, 60))  # Max 60 seconds wait
                        continue
                
                elif 400 <= response.status_code < 500:
                    # Client error - don't retry
                    last_error = f"Klientfel för {service}: {response.status_code} {response.text[:200]}"
                    break
                
                else:
                    # Server error - retry
                    last_error = f"Serverfel för {service}: {response.status_code}"
                    if attempt < config.max_retries:
                        await asyncio.sleep(config.retry_backoff * (2 ** attempt))
                        continue
                
            except httpx.TimeoutException:
                last_error = f"Tidsgräns överskriden för {service}"
                if attempt < config.max_retries:
                    await asyncio.sleep(config.retry_backoff * (2 ** attempt))
                    continue
                    
            except httpx.ConnectError:
                last_error = f"Kunde inte ansluta till {service}"
                if attempt < config.max_retries:
                    await asyncio.sleep(config.retry_backoff * (2 ** attempt))
                    continue
                    
            except Exception as e:
                last_error = f"Oväntat fel för {service}: {str(e)}"
                if attempt < config.max_retries:
                    await asyncio.sleep(config.retry_backoff * (2 ** attempt))
                    continue
        
        # All attempts failed
        metrics.failed_requests += 1
        metrics.last_failure_time = datetime.utcnow()
        self._record_failure(circuit_breaker, config)
        
        return await self._handle_fallback(service, config, fallback_response, last_error)
    
    def _check_rate_limit(self, service: str) -> bool:
        """Check if service is within rate limits"""
        config = self.services[service]
        rate_limiter = self.rate_limiters[service]
        
        now = time.time()
        window_start = now - 60  # 1 minute window
        
        # Clean old requests
        rate_limiter["requests"] = [
            req_time for req_time in rate_limiter["requests"]
            if req_time > window_start
        ]
        
        # Check limits
        current_count = len(rate_limiter["requests"])
        if current_count >= config.rate_limit:
            return False
        
        # Record this request
        rate_limiter["requests"].append(now)
        return True
    
    def _can_make_request(self, circuit_breaker: CircuitBreaker, config: ServiceConfig) -> bool:
        """Check if circuit breaker allows request"""
        now = datetime.utcnow()
        
        if circuit_breaker.state == "closed":
            return True
        elif circuit_breaker.state == "open":
            if (circuit_breaker.next_attempt_time and 
                now >= circuit_breaker.next_attempt_time):
                circuit_breaker.state = "half_open"
                return True
            return False
        elif circuit_breaker.state == "half_open":
            return True
        
        return False
    
    def _record_failure(self, circuit_breaker: CircuitBreaker, config: ServiceConfig):
        """Record failure and potentially open circuit breaker"""
        circuit_breaker.failure_count += 1
        circuit_breaker.last_failure_time = datetime.utcnow()
        
        if circuit_breaker.failure_count >= config.failure_threshold:
            circuit_breaker.state = "open"
            circuit_breaker.next_attempt_time = (
                datetime.utcnow() + timedelta(seconds=config.recovery_timeout)
            )
            logger.warning(f"Circuit breaker opened for service: {config.name}")
    
    def _reset_circuit_breaker(self, circuit_breaker: CircuitBreaker):
        """Reset circuit breaker after successful request"""
        if circuit_breaker.state != "closed":
            circuit_breaker.state = "closed"
            circuit_breaker.failure_count = 0
            circuit_breaker.next_attempt_time = None
    
    def _update_response_time(self, metrics: ServiceMetrics, response_time: float):
        """Update average response time"""
        if metrics.avg_response_time == 0:
            metrics.avg_response_time = response_time
        else:
            # Exponential moving average
            metrics.avg_response_time = (
                0.9 * metrics.avg_response_time + 0.1 * response_time
            )
    
    def _cache_response(self, service: str, key: str, data: Any, ttl: int):
        """Cache response data"""
        cache_key = f"{service}:{key}"
        self.cache[cache_key] = {
            "data": data,
            "expires_at": time.time() + ttl
        }
    
    def _get_cached_response(self, service: str, key: str) -> Optional[Any]:
        """Get cached response if available and valid"""
        cache_key = f"{service}:{key}"
        cached = self.cache.get(cache_key)
        
        if cached and cached["expires_at"] > time.time():
            return cached["data"]
        
        # Remove expired cache entry
        if cached:
            del self.cache[cache_key]
        
        return None
    
    async def _handle_fallback(
        self,
        service: str,
        config: ServiceConfig,
        fallback_response: Optional[Any],
        error_message: str
    ) -> Tuple[bool, Any, str]:
        """Handle request failure with appropriate fallback strategy"""
        
        if config.fallback_strategy == FallbackStrategy.FAIL_FAST:
            return False, None, error_message
        
        elif config.fallback_strategy == FallbackStrategy.GRACEFUL_DEGRADATION:
            # Return a graceful error response that the application can handle
            graceful_response = {
                "status": "degraded",
                "message": f"Tjänsten {service} är tillfälligt otillgänglig",
                "fallback": True,
                "suggestion": "Försök igen senare eller använd alternativa funktioner"
            }
            return True, graceful_response, f"Försämrad service: {error_message}"
        
        elif config.fallback_strategy == FallbackStrategy.CACHED_RESPONSE:
            # Try to return cached data
            cached = self._get_cached_response(service, "last_success")
            if cached:
                cached["_cached"] = True
                cached["_cache_notice"] = "Data från cache på grund av tjänsteproblem"
                return True, cached, "Använder cachad data"
            
            # No cache available, fall back to degradation
            return await self._handle_fallback(
                service, 
                ServiceConfig(
                    name=config.name,
                    base_url=config.base_url,
                    fallback_strategy=FallbackStrategy.GRACEFUL_DEGRADATION
                ),
                fallback_response,
                error_message
            )
        
        elif config.fallback_strategy == FallbackStrategy.ALTERNATIVE_SERVICE:
            # Return fallback response if provided
            if fallback_response is not None:
                return True, fallback_response, "Använder alternativ tjänst"
            
            # Fall back to graceful degradation
            return await self._handle_fallback(
                service,
                ServiceConfig(
                    name=config.name,
                    base_url=config.base_url,
                    fallback_strategy=FallbackStrategy.GRACEFUL_DEGRADATION
                ),
                fallback_response,
                error_message
            )
        
        return False, None, error_message
    
    def get_service_status(self, service: str) -> Dict[str, Any]:
        """Get comprehensive status of a service"""
        if service not in self.services:
            return {"error": "Tjänst hittades inte"}
        
        config = self.services[service]
        metrics = self.metrics[service]
        circuit_breaker = self.circuit_breakers[service]
        rate_limiter = self.rate_limiters[service]
        
        # Determine overall status
        status = ServiceStatus.HEALTHY
        if circuit_breaker.state == "open":
            status = ServiceStatus.OFFLINE
        elif circuit_breaker.state == "half_open" or metrics.consecutive_failures > 0:
            status = ServiceStatus.DEGRADED
        elif metrics.avg_response_time > config.timeout * 0.8:
            status = ServiceStatus.DEGRADED
        
        # Calculate success rate
        success_rate = 0.0
        if metrics.total_requests > 0:
            success_rate = metrics.successful_requests / metrics.total_requests * 100
        
        # Current rate limit usage
        now = time.time()
        recent_requests = len([
            req for req in rate_limiter["requests"]
            if req > now - 60
        ])
        
        return {
            "name": service,
            "status": status.value,
            "base_url": config.base_url,
            "metrics": {
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "success_rate": round(success_rate, 2),
                "avg_response_time": round(metrics.avg_response_time, 3),
                "last_request": metrics.last_request_time.isoformat() if metrics.last_request_time else None,
                "last_success": metrics.last_success_time.isoformat() if metrics.last_success_time else None,
                "last_failure": metrics.last_failure_time.isoformat() if metrics.last_failure_time else None
            },
            "circuit_breaker": {
                "state": circuit_breaker.state,
                "failure_count": circuit_breaker.failure_count,
                "next_attempt": circuit_breaker.next_attempt_time.isoformat() if circuit_breaker.next_attempt_time else None
            },
            "rate_limit": {
                "limit": config.rate_limit,
                "current_usage": recent_requests,
                "remaining": max(0, config.rate_limit - recent_requests),
                "reset_time": int(now + 60)
            },
            "configuration": {
                "timeout": config.timeout,
                "max_retries": config.max_retries,
                "fallback_strategy": config.fallback_strategy.value,
                "cache_ttl": config.cache_ttl
            }
        }
    
    def get_all_services_status(self) -> Dict[str, Any]:
        """Get status of all registered services"""
        services_status = {}
        
        for service_name in self.services.keys():
            services_status[service_name] = self.get_service_status(service_name)
        
        # Calculate overall system health
        healthy_count = sum(1 for status in services_status.values() 
                          if status.get("status") == "healthy")
        total_count = len(services_status)
        
        overall_health = "healthy"
        if healthy_count == 0:
            overall_health = "critical"
        elif healthy_count < total_count * 0.7:
            overall_health = "degraded"
        
        return {
            "overall_health": overall_health,
            "healthy_services": healthy_count,
            "total_services": total_count,
            "services": services_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def health_check(self, service: Optional[str] = None) -> Dict[str, Any]:
        """Perform health check on services"""
        if service:
            return await self._health_check_service(service)
        
        # Check all services
        results = {}
        for service_name in self.services.keys():
            results[service_name] = await self._health_check_service(service_name)
        
        return results
    
    async def _health_check_service(self, service: str) -> Dict[str, Any]:
        """Perform health check on a specific service"""
        if service not in self.services:
            return {"healthy": False, "error": "Service not found"}
        
        config = self.services[service]
        
        if not config.health_check_url:
            return {"healthy": True, "note": "No health check URL configured"}
        
        try:
            start_time = time.time()
            success, response, error = await self.request(
                service=service,
                method="GET",
                path=config.health_check_url.replace(config.base_url, ""),
                timeout=10
            )
            
            response_time = time.time() - start_time
            
            return {
                "healthy": success,
                "response_time": round(response_time, 3),
                "error": error if not success else None,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self._health_check_task:
            self._health_check_task.cancel()
        
        # Close all HTTP clients
        for client in self.clients.values():
            await client.aclose()
        
        # Clear caches
        self.cache.clear()

# Global instance
api_client_manager = APIClientManager()

# Convenience functions for common operations
async def google_calendar_request(
    method: str,
    path: str,
    access_token: str,
    **kwargs
) -> Tuple[bool, Any, str]:
    """Make Google Calendar API request with authentication"""
    headers = kwargs.get("headers", {})
    headers["Authorization"] = f"Bearer {access_token}"
    kwargs["headers"] = headers
    
    return await api_client_manager.request(
        service="google_calendar",
        method=method,
        path=path,
        **kwargs
    )

async def gmail_request(
    method: str,
    path: str,
    access_token: str,
    **kwargs
) -> Tuple[bool, Any, str]:
    """Make Gmail API request with authentication"""
    headers = kwargs.get("headers", {})
    headers["Authorization"] = f"Bearer {access_token}"
    kwargs["headers"] = headers
    
    return await api_client_manager.request(
        service="gmail",
        method=method,
        path=path,
        **kwargs
    )

async def spotify_request(
    method: str,
    path: str,
    access_token: str,
    **kwargs
) -> Tuple[bool, Any, str]:
    """Make Spotify API request with authentication"""
    headers = kwargs.get("headers", {})
    headers["Authorization"] = f"Bearer {access_token}"
    kwargs["headers"] = headers
    
    return await api_client_manager.request(
        service="spotify",
        method=method,
        path=path,
        **kwargs
    )

async def openai_request(
    method: str,
    path: str,
    api_key: str,
    **kwargs
) -> Tuple[bool, Any, str]:
    """Make OpenAI API request with authentication"""
    headers = kwargs.get("headers", {})
    headers["Authorization"] = f"Bearer {api_key}"
    kwargs["headers"] = headers
    
    return await api_client_manager.request(
        service="openai",
        method=method,
        path=path,
        **kwargs
    )

# Health check endpoint helper
async def get_services_health() -> Dict[str, Any]:
    """Get health status of all services for monitoring"""
    return api_client_manager.get_all_services_status()