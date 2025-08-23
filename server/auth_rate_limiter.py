"""
Authentication-aware Rate Limiting for Alice AI Assistant
Implements user-specific rate limiting with tiered access levels
"""
import os
import logging
from typing import Dict, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException, status

from rate_limiter import RateLimitRule, RateLimitAlgorithm, InMemoryRateLimiter
from auth_models import User, APIKey, UserRole, AuditEventType
from auth_service import AuthService

logger = logging.getLogger("alice.auth_rate_limiter")

class UserRateLimiter:
    """User-specific rate limiting with authentication awareness"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.limiter = InMemoryRateLimiter()
        
        # User tier-based rate limiting rules
        self.user_tier_rules = {
            UserRole.ADMIN: {
                "global": RateLimitRule(limit=1000, window_seconds=3600, identifier="user_id"),
                "chat": RateLimitRule(limit=200, window_seconds=3600, identifier="user_id"),
                "voice": RateLimitRule(limit=100, window_seconds=3600, identifier="user_id"),
                "api": RateLimitRule(limit=500, window_seconds=3600, identifier="user_id"),
            },
            UserRole.USER: {
                "global": RateLimitRule(limit=500, window_seconds=3600, identifier="user_id"),
                "chat": RateLimitRule(limit=100, window_seconds=3600, identifier="user_id"),
                "voice": RateLimitRule(limit=50, window_seconds=3600, identifier="user_id"),
                "api": RateLimitRule(limit=200, window_seconds=3600, identifier="user_id"),
            },
            UserRole.READONLY: {
                "global": RateLimitRule(limit=200, window_seconds=3600, identifier="user_id"),
                "chat": RateLimitRule(limit=50, window_seconds=3600, identifier="user_id"),
                "voice": RateLimitRule(limit=20, window_seconds=3600, identifier="user_id"),
                "api": RateLimitRule(limit=100, window_seconds=3600, identifier="user_id"),
            },
            UserRole.GUEST: {
                "global": RateLimitRule(limit=50, window_seconds=3600, identifier="user_id"),
                "chat": RateLimitRule(limit=20, window_seconds=3600, identifier="user_id"),
                "voice": RateLimitRule(limit=5, window_seconds=3600, identifier="user_id"),
                "api": RateLimitRule(limit=30, window_seconds=3600, identifier="user_id"),
            }
        }
        
        # Per-minute limits for burst control
        self.burst_rules = {
            UserRole.ADMIN: {
                "global": RateLimitRule(limit=100, window_seconds=60, identifier="user_id"),
                "chat": RateLimitRule(limit=30, window_seconds=60, identifier="user_id"),
            },
            UserRole.USER: {
                "global": RateLimitRule(limit=60, window_seconds=60, identifier="user_id"),
                "chat": RateLimitRule(limit=20, window_seconds=60, identifier="user_id"),
            },
            UserRole.READONLY: {
                "global": RateLimitRule(limit=30, window_seconds=60, identifier="user_id"),
                "chat": RateLimitRule(limit=10, window_seconds=60, identifier="user_id"),
            },
            UserRole.GUEST: {
                "global": RateLimitRule(limit=10, window_seconds=60, identifier="user_id"),
                "chat": RateLimitRule(limit=3, window_seconds=60, identifier="user_id"),
            }
        }
        
        # API key specific limits
        self.api_key_default_rules = {
            "global": RateLimitRule(limit=1000, window_seconds=3600, identifier="api_key"),
            "burst": RateLimitRule(limit=100, window_seconds=60, identifier="api_key")
        }
        
        # Anonymous/IP-based limits (fallback)
        self.anonymous_rules = {
            "global": RateLimitRule(limit=100, window_seconds=3600, identifier="ip"),
            "chat": RateLimitRule(limit=20, window_seconds=3600, identifier="ip"),
            "voice": RateLimitRule(limit=10, window_seconds=3600, identifier="ip"),
            "burst": RateLimitRule(limit=20, window_seconds=60, identifier="ip")
        }
    
    def check_user_rate_limit(
        self, 
        user: User, 
        endpoint_type: str,
        request: Optional[Request] = None
    ) -> Tuple[bool, Optional[int], Dict[str, Any]]:
        """Check rate limit for authenticated user"""
        user_role = UserRole(user.role)
        user_rules = self.user_tier_rules.get(user_role, self.user_tier_rules[UserRole.USER])
        burst_rules = self.burst_rules.get(user_role, self.burst_rules[UserRole.USER])
        
        # Check hourly limit
        rule = user_rules.get(endpoint_type, user_rules["global"])
        allowed, retry_after, stats = self.limiter.check_rate_limit(
            f"user:{user.id}:{endpoint_type}", rule
        )
        
        if not allowed:
            self._log_rate_limit_exceeded(user.id, endpoint_type, "hourly", request)
            return False, retry_after, stats
        
        # Check burst limit (per minute)
        burst_rule = burst_rules.get(endpoint_type, burst_rules["global"])
        allowed, retry_after, burst_stats = self.limiter.check_rate_limit(
            f"user:{user.id}:{endpoint_type}:burst", burst_rule
        )
        
        if not allowed:
            self._log_rate_limit_exceeded(user.id, endpoint_type, "burst", request)
            return False, retry_after, burst_stats
        
        # Combine stats
        combined_stats = {
            "hourly": stats,
            "burst": burst_stats,
            "user_role": user.role,
            "user_id": user.id
        }
        
        return True, None, combined_stats
    
    def check_api_key_rate_limit(
        self, 
        api_key: APIKey, 
        endpoint_type: str,
        request: Optional[Request] = None
    ) -> Tuple[bool, Optional[int], Dict[str, Any]]:
        """Check rate limit for API key usage"""
        # Use API key specific rate limit if configured
        if api_key.rate_limit:
            custom_rule = RateLimitRule(
                limit=api_key.rate_limit, 
                window_seconds=3600, 
                identifier="api_key"
            )
            allowed, retry_after, stats = self.limiter.check_rate_limit(
                f"api_key:{api_key.id}:{endpoint_type}", custom_rule
            )
        else:
            # Use default API key limits
            rule = self.api_key_default_rules["global"]
            allowed, retry_after, stats = self.limiter.check_rate_limit(
                f"api_key:{api_key.id}:{endpoint_type}", rule
            )
        
        if not allowed:
            self._log_rate_limit_exceeded(api_key.user_id, endpoint_type, "api_key", request)
            return False, retry_after, stats
        
        # Check burst limit
        burst_rule = self.api_key_default_rules["burst"]
        allowed, retry_after, burst_stats = self.limiter.check_rate_limit(
            f"api_key:{api_key.id}:{endpoint_type}:burst", burst_rule
        )
        
        if not allowed:
            self._log_rate_limit_exceeded(api_key.user_id, endpoint_type, "api_key_burst", request)
            return False, retry_after, burst_stats
        
        combined_stats = {
            "hourly": stats,
            "burst": burst_stats,
            "api_key_id": api_key.id,
            "user_id": api_key.user_id
        }
        
        return True, None, combined_stats
    
    def check_anonymous_rate_limit(
        self, 
        client_ip: str, 
        endpoint_type: str,
        request: Optional[Request] = None
    ) -> Tuple[bool, Optional[int], Dict[str, Any]]:
        """Check rate limit for anonymous/unauthenticated requests"""
        rule = self.anonymous_rules.get(endpoint_type, self.anonymous_rules["global"])
        allowed, retry_after, stats = self.limiter.check_rate_limit(
            f"ip:{client_ip}:{endpoint_type}", rule
        )
        
        if not allowed:
            self._log_rate_limit_exceeded(None, endpoint_type, "anonymous", request)
            return False, retry_after, stats
        
        # Check burst limit
        burst_rule = self.anonymous_rules["burst"]
        allowed, retry_after, burst_stats = self.limiter.check_rate_limit(
            f"ip:{client_ip}:{endpoint_type}:burst", burst_rule
        )
        
        if not allowed:
            self._log_rate_limit_exceeded(None, endpoint_type, "anonymous_burst", request)
            return False, retry_after, burst_stats
        
        combined_stats = {
            "hourly": stats,
            "burst": burst_stats,
            "client_ip": client_ip,
            "type": "anonymous"
        }
        
        return True, None, combined_stats
    
    def _log_rate_limit_exceeded(
        self, 
        user_id: Optional[int], 
        endpoint_type: str, 
        limit_type: str,
        request: Optional[Request] = None
    ):
        """Log rate limit exceeded event for security audit"""
        try:
            from auth_models import AuditLog
            
            audit_log = AuditLog(
                user_id=user_id,
                event_type=AuditEventType.RATE_LIMIT_EXCEEDED.value,
                success=False,
                details={
                    "endpoint_type": endpoint_type,
                    "limit_type": limit_type,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            if request:
                audit_log.ip_address = request.client.host if request.client else "unknown"
                audit_log.user_agent = request.headers.get("user-agent", "")[:1000]
            
            self.db.add(audit_log)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log rate limit audit event: {e}")
    
    def get_user_rate_limit_status(self, user: User) -> Dict[str, Any]:
        """Get current rate limit status for user"""
        user_role = UserRole(user.role)
        user_rules = self.user_tier_rules.get(user_role, self.user_tier_rules[UserRole.USER])
        burst_rules = self.burst_rules.get(user_role, self.burst_rules[UserRole.USER])
        
        status = {
            "user_id": user.id,
            "role": user.role,
            "limits": {},
            "usage": {}
        }
        
        # Get limits and current usage for each endpoint type
        for endpoint_type, rule in user_rules.items():
            # Get hourly stats
            _, _, hourly_stats = self.limiter.check_rate_limit(
                f"user:{user.id}:{endpoint_type}", rule
            )
            
            # Get burst stats
            burst_rule = burst_rules.get(endpoint_type)
            burst_stats = None
            if burst_rule:
                _, _, burst_stats = self.limiter.check_rate_limit(
                    f"user:{user.id}:{endpoint_type}:burst", burst_rule
                )
            
            status["limits"][endpoint_type] = {
                "hourly_limit": rule.limit,
                "burst_limit": burst_rule.limit if burst_rule else None
            }
            
            status["usage"][endpoint_type] = {
                "hourly_remaining": hourly_stats.get("remaining", 0),
                "hourly_reset": hourly_stats.get("reset_time", 0),
                "burst_remaining": burst_stats.get("remaining", 0) if burst_stats else None,
                "burst_reset": burst_stats.get("reset_time", 0) if burst_stats else None
            }
        
        return status
    
    def reset_user_rate_limits(self, user_id: int, endpoint_type: Optional[str] = None):
        """Reset rate limits for user (admin function)"""
        if endpoint_type:
            # Reset specific endpoint
            keys_to_remove = []
            for key in self.limiter.buckets.keys():
                if f"user:{user_id}:{endpoint_type}" in key:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del self.limiter.buckets[key]
                
            for key in self.limiter.windows.keys():
                if f"user:{user_id}:{endpoint_type}" in key:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                if key in self.limiter.windows:
                    del self.limiter.windows[key]
        else:
            # Reset all limits for user
            keys_to_remove = []
            for key in self.limiter.buckets.keys():
                if f"user:{user_id}" in key:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del self.limiter.buckets[key]
                
            keys_to_remove = []
            for key in self.limiter.windows.keys():
                if f"user:{user_id}" in key:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del self.limiter.windows[key]
        
        logger.info(f"Reset rate limits for user {user_id}, endpoint: {endpoint_type or 'all'}")
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get overall rate limiting statistics"""
        return {
            "total_buckets": len(self.limiter.buckets),
            "total_windows": len(self.limiter.windows),
            "last_cleanup": self.limiter.last_cleanup,
            "user_tier_rules": {
                role.value: {
                    endpoint: {
                        "limit": rule.limit,
                        "window_seconds": rule.window_seconds,
                        "algorithm": rule.algorithm.value
                    }
                    for endpoint, rule in rules.items()
                }
                for role, rules in self.user_tier_rules.items()
            }
        }

# Integration with FastAPI request context
def get_rate_limiter_for_request(
    request: Request,
    db: Session,
    auth_service: AuthService
) -> Tuple[UserRateLimiter, str, Optional[Union[User, APIKey]]]:
    """
    Determine appropriate rate limiter configuration for request
    Returns: (rate_limiter, identifier_type, user_or_api_key)
    """
    rate_limiter = UserRateLimiter(db)
    
    # Try to get authentication from request
    auth_header = request.headers.get("authorization")
    api_key_header = request.headers.get("x-api-key")
    
    if auth_header and auth_header.startswith("Bearer "):
        # JWT authentication
        token = auth_header[7:]
        payload = auth_service.verify_token(token)
        if payload:
            user = auth_service.get_user_by_id(int(payload["sub"]))
            if user:
                return rate_limiter, "user", user
    
    if api_key_header:
        # API key authentication
        user = auth_service.verify_api_key(api_key_header)
        if user:
            # Find the API key object
            api_key = db.query(APIKey).filter(
                APIKey.user_id == user.id,
                APIKey.is_active == True
            ).first()
            if api_key and api_key.verify_key(api_key_header):
                return rate_limiter, "api_key", api_key
    
    # Fall back to IP-based rate limiting
    return rate_limiter, "anonymous", None

def check_request_rate_limit(
    request: Request,
    endpoint_type: str,
    db: Session,
    auth_service: AuthService
) -> Tuple[bool, Optional[int], Dict[str, Any]]:
    """
    Check rate limit for incoming request
    Returns: (allowed, retry_after, stats)
    """
    rate_limiter, identifier_type, auth_object = get_rate_limiter_for_request(
        request, db, auth_service
    )
    
    client_ip = request.client.host if request.client else "unknown"
    
    if identifier_type == "user" and isinstance(auth_object, User):
        return rate_limiter.check_user_rate_limit(auth_object, endpoint_type, request)
    elif identifier_type == "api_key" and isinstance(auth_object, APIKey):
        return rate_limiter.check_api_key_rate_limit(auth_object, endpoint_type, request)
    else:
        return rate_limiter.check_anonymous_rate_limit(client_ip, endpoint_type, request)

# Swedish error messages for rate limiting
SWEDISH_RATE_LIMIT_MESSAGES = {
    "rate_limit_exceeded": "Begränsning av antalet förfrågningar överskriden",
    "too_many_requests": "För många förfrågningar. Försök igen senare",
    "quota_exceeded": "Din kvot har överskridits",
    "burst_limit_exceeded": "För många förfrågningar på kort tid",
    "api_quota_exceeded": "API-kvoten har överskridits",
    "upgrade_required": "Uppgradering krävs för högre gränser"
}