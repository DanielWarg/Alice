"""
Professional rate limiting middleware for Alice AI Assistant
Implements token bucket and sliding window algorithms with Redis fallback
"""

import time
import asyncio
import logging
from typing import Dict, Optional, Tuple, Any
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from error_handlers import RateLimitError

logger = logging.getLogger("alice.rate_limiter")


class RateLimitAlgorithm(Enum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration"""
    limit: int                          # Max requests
    window_seconds: int                 # Time window  
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    burst_limit: Optional[int] = None   # Burst allowance for token bucket
    identifier: str = "ip"              # ip, user_id, api_key, etc.


@dataclass
class TokenBucket:
    """Token bucket for rate limiting"""
    capacity: int
    tokens: float
    refill_rate: float  # tokens per second
    last_refill: float = field(default_factory=time.time)
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket"""
        now = time.time()
        
        # Refill tokens based on elapsed time
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now
        
        # Try to consume tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


@dataclass
class SlidingWindow:
    """Sliding window for rate limiting"""
    limit: int
    window_seconds: int
    requests: deque = field(default_factory=deque)
    
    def can_proceed(self) -> bool:
        """Check if request can proceed"""
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Remove old requests
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        
        # Check if under limit
        if len(self.requests) < self.limit:
            self.requests.append(now)
            return True
        return False
    
    def get_reset_time(self) -> float:
        """Get when the next token will be available"""
        if not self.requests:
            return 0
        return self.requests[0] + self.window_seconds


class InMemoryRateLimiter:
    """In-memory rate limiter with cleanup"""
    
    def __init__(self):
        self.buckets: Dict[str, TokenBucket] = {}
        self.windows: Dict[str, SlidingWindow] = {}
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
    
    def _cleanup_old_entries(self):
        """Clean up old/expired entries"""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        # Clean up token buckets (remove if not used in 30 minutes)
        old_buckets = []
        for key, bucket in self.buckets.items():
            if now - bucket.last_refill > 1800:  # 30 minutes
                old_buckets.append(key)
        
        for key in old_buckets:
            del self.buckets[key]
        
        # Clean up sliding windows (remove if no recent requests)
        old_windows = []
        for key, window in self.windows.items():
            if not window.requests or (window.requests and now - window.requests[-1] > 1800):
                old_windows.append(key)
        
        for key in old_windows:
            del self.windows[key]
        
        self.last_cleanup = now
        if old_buckets or old_windows:
            logger.info(f"Rate limiter cleanup: removed {len(old_buckets)} buckets, {len(old_windows)} windows")
    
    def check_rate_limit(
        self, 
        identifier: str, 
        rule: RateLimitRule
    ) -> Tuple[bool, Optional[int], Optional[Dict[str, Any]]]:
        """
        Check if request should be rate limited
        
        Returns:
            (allowed, retry_after_seconds, stats)
        """
        self._cleanup_old_entries()
        
        key = f"{rule.identifier}:{identifier}:{rule.limit}:{rule.window_seconds}"
        
        if rule.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return self._check_token_bucket(key, rule)
        elif rule.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            return self._check_sliding_window(key, rule)
        else:
            # Default to token bucket
            return self._check_token_bucket(key, rule)
    
    def _check_token_bucket(self, key: str, rule: RateLimitRule) -> Tuple[bool, Optional[int], Dict[str, Any]]:
        """Check token bucket rate limit"""
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(
                capacity=rule.burst_limit or rule.limit,
                tokens=rule.burst_limit or rule.limit,
                refill_rate=rule.limit / rule.window_seconds
            )
        
        bucket = self.buckets[key]
        allowed = bucket.consume(1)
        
        stats = {
            "algorithm": "token_bucket",
            "limit": rule.limit,
            "window_seconds": rule.window_seconds,
            "remaining": int(bucket.tokens),
            "reset_time": time.time() + (rule.window_seconds if bucket.tokens == 0 else 0)
        }
        
        retry_after = None if allowed else rule.window_seconds
        return allowed, retry_after, stats
    
    def _check_sliding_window(self, key: str, rule: RateLimitRule) -> Tuple[bool, Optional[int], Dict[str, Any]]:
        """Check sliding window rate limit"""
        if key not in self.windows:
            self.windows[key] = SlidingWindow(
                limit=rule.limit,
                window_seconds=rule.window_seconds
            )
        
        window = self.windows[key]
        allowed = window.can_proceed()
        
        stats = {
            "algorithm": "sliding_window",
            "limit": rule.limit,
            "window_seconds": rule.window_seconds,
            "remaining": rule.limit - len(window.requests),
            "reset_time": window.get_reset_time()
        }
        
        retry_after = None
        if not allowed and window.requests:
            retry_after = int(window.get_reset_time() - time.time())
        
        return allowed, retry_after, stats


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Professional rate limiting middleware with configurable rules
    """
    
    def __init__(self, app, rules: Optional[Dict[str, RateLimitRule]] = None):
        super().__init__(app)
        self.limiter = InMemoryRateLimiter()
        
        # Default rules if none provided
        self.rules = rules or {
            "/api/chat": RateLimitRule(limit=30, window_seconds=60, identifier="ip"),
            "/api/v2/chat": RateLimitRule(limit=30, window_seconds=60, identifier="ip"),
            "/api/tts": RateLimitRule(limit=20, window_seconds=60, identifier="ip"),
            "/api/spotify": RateLimitRule(limit=100, window_seconds=60, identifier="ip"),
            "/api/calendar": RateLimitRule(limit=50, window_seconds=60, identifier="ip"),
            "global": RateLimitRule(limit=200, window_seconds=60, identifier="ip"),  # Global limit
        }
        
        # Exempt paths (health checks, metrics, etc.)
        self.exempt_paths = {
            "/api/health",
            "/api/metrics", 
            "/docs",
            "/openapi.json",
            "/favicon.ico"
        }
        
        logger.info(f"Rate limiting initialized with {len(self.rules)} rules")
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting logic"""
        
        # Skip exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Get client identifier
        client_ip = self._get_client_ip(request)
        
        # Apply rate limiting rules
        try:
            self._check_all_limits(request, client_ip)
        except RateLimitError as e:
            return self._create_rate_limit_response(e)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        self._add_rate_limit_headers(response, request, client_ip)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP with proxy support"""
        # Check X-Forwarded-For header (reverse proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _check_all_limits(self, request: Request, client_ip: str):
        """Check all applicable rate limits"""
        
        # Check global limit first
        global_rule = self.rules.get("global")
        if global_rule:
            allowed, retry_after, stats = self.limiter.check_rate_limit(client_ip, global_rule)
            if not allowed:
                raise RateLimitError(
                    limit=global_rule.limit,
                    window=f"{global_rule.window_seconds}s",
                    retry_after=retry_after
                )
        
        # Check path-specific limits
        path = request.url.path
        
        # Find matching rule (longest prefix match)
        matching_rule = None
        matching_path = ""
        
        for rule_path, rule in self.rules.items():
            if rule_path != "global" and path.startswith(rule_path):
                if len(rule_path) > len(matching_path):
                    matching_rule = rule
                    matching_path = rule_path
        
        if matching_rule:
            allowed, retry_after, stats = self.limiter.check_rate_limit(
                f"{matching_path}:{client_ip}", 
                matching_rule
            )
            if not allowed:
                raise RateLimitError(
                    limit=matching_rule.limit,
                    window=f"{matching_rule.window_seconds}s",
                    retry_after=retry_after
                )
    
    def _add_rate_limit_headers(self, response: Response, request: Request, client_ip: str):
        """Add rate limit information to response headers"""
        
        # Add global rate limit info
        global_rule = self.rules.get("global")
        if global_rule:
            _, _, stats = self.limiter.check_rate_limit(client_ip, global_rule)
            response.headers["X-RateLimit-Limit"] = str(global_rule.limit)
            response.headers["X-RateLimit-Remaining"] = str(stats.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(int(stats.get("reset_time", 0)))
        
        # Add path-specific info if available
        path = request.url.path
        for rule_path, rule in self.rules.items():
            if rule_path != "global" and path.startswith(rule_path):
                _, _, stats = self.limiter.check_rate_limit(f"{rule_path}:{client_ip}", rule)
                response.headers[f"X-RateLimit-{rule_path.replace('/', '-')}-Limit"] = str(rule.limit)
                response.headers[f"X-RateLimit-{rule_path.replace('/', '-')}-Remaining"] = str(stats.get("remaining", 0))
                break
    
    def _create_rate_limit_response(self, error: RateLimitError) -> Response:
        """Create rate limit exceeded response"""
        
        # Use our error handling system
        from fastapi.responses import JSONResponse
        from error_handlers import generate_request_id
        
        request_id = generate_request_id()
        problem = error.to_problem_detail(request_id=request_id)
        
        headers = {"Content-Type": "application/problem+json"}
        if error.errors and len(error.errors) > 0 and "retry_after" in error.errors[0]:
            headers["Retry-After"] = str(error.errors[0]["retry_after"])
        
        return JSONResponse(
            status_code=error.status_code,
            content=problem.dict(),
            headers=headers
        )


# Pre-configured rate limiter instances
def create_alice_rate_limiter() -> RateLimitMiddleware:
    """Create Alice-specific rate limiter with appropriate rules"""
    
    rules = {
        # Chat endpoints (most sensitive)
        "/api/chat": RateLimitRule(
            limit=30, 
            window_seconds=60, 
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            burst_limit=40
        ),
        "/api/v2/chat": RateLimitRule(
            limit=30, 
            window_seconds=60,
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            burst_limit=40
        ),
        "/api/agent": RateLimitRule(
            limit=20,
            window_seconds=60,
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW
        ),
        
        # TTS/Voice endpoints
        "/api/tts": RateLimitRule(limit=20, window_seconds=60),
        "/api/voice": RateLimitRule(limit=15, window_seconds=60),
        
        # External service endpoints
        "/api/spotify": RateLimitRule(limit=100, window_seconds=60),
        "/api/calendar": RateLimitRule(limit=50, window_seconds=60),
        "/api/gmail": RateLimitRule(limit=30, window_seconds=60),
        
        # Upload endpoints
        "/api/upload": RateLimitRule(limit=10, window_seconds=60),
        
        # Global fallback
        "global": RateLimitRule(
            limit=300, 
            window_seconds=60,
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            burst_limit=400
        ),
    }
    
    return RateLimitMiddleware(None, rules)


# Utility functions for manual rate limit checks
async def check_rate_limit_for_user(
    user_id: str, 
    endpoint: str, 
    limiter: InMemoryRateLimiter
) -> Tuple[bool, Optional[int]]:
    """
    Manually check rate limit for a specific user and endpoint
    Useful for business logic rate limiting
    """
    
    rule = RateLimitRule(limit=100, window_seconds=3600, identifier="user_id")  # Example rule
    allowed, retry_after, _ = limiter.check_rate_limit(f"user:{user_id}:{endpoint}", rule)
    
    return allowed, retry_after


def get_rate_limit_stats(
    identifier: str, 
    rule: RateLimitRule,
    limiter: InMemoryRateLimiter
) -> Dict[str, Any]:
    """Get current rate limit statistics"""
    
    _, _, stats = limiter.check_rate_limit(identifier, rule)
    return stats