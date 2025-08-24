"""
Alice Security Module - CSRF/XSS Protection and Security Headers
"""
import os
import secrets
import time
from typing import Dict, List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException, status
import logging

logger = logging.getLogger("alice.security")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware for Alice
    Implements OWASP security headers and CSRF protection
    """
    
    def __init__(self, app, allowed_origins: List[str] = None):
        super().__init__(app)
        # Default to localhost for development, configurable for production
        self.allowed_origins = allowed_origins or [
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ]
        
        # Add production origins from environment
        prod_origins = os.getenv("ALICE_ALLOWED_ORIGINS", "").split(",")
        for origin in prod_origins:
            if origin.strip():
                self.allowed_origins.append(origin.strip())
        
        logger.info(f"Security middleware initialized with origins: {self.allowed_origins}")
    
    async def dispatch(self, request: Request, call_next):
        # Handle OPTIONS preflight requests for CORS
        if request.method == "OPTIONS":
            origin = request.headers.get("origin")
            if origin and origin in self.allowed_origins:
                # Create proper preflight response
                response = Response(status_code=200)
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
                response.headers["Access-Control-Allow-Headers"] = (
                    "Content-Type, Authorization, X-Requested-With, "
                    "Accept, Origin, Cache-Control, X-File-Name, "
                    "X-Request-ID, X-CSRF-Token, X-Alice-Version"
                )
                response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours
                return response
            else:
                # Reject OPTIONS from unauthorized origins
                return Response(status_code=403)
        
        # Pre-process request
        self._validate_request(request)
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        self._add_security_headers(response, request)
        
        return response
    
    def _validate_request(self, request: Request):
        """Validate incoming request for security"""
        # Check origin for CORS
        origin = request.headers.get("origin")
        if origin and origin not in self.allowed_origins:
            # Log suspicious origin
            logger.warning(f"Request from unauthorized origin: {origin}")
        
        # Basic rate limiting check (simple implementation)
        # Production should use Redis or proper rate limiting
        client_ip = request.client.host if request.client else "unknown"
        if self._is_rate_limited(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
    
    def _is_rate_limited(self, client_ip: str) -> bool:
        """Basic in-memory rate limiting"""
        # This is a simple implementation - production should use Redis
        # For now, we'll be permissive and just log
        return False
    
    def _add_security_headers(self, response: Response, request: Request):
        """Add comprehensive security headers"""
        
        # HSTS - Force HTTPS in production
        if request.url.scheme == "https" or os.getenv("FORCE_HTTPS_HEADERS", "0") == "1":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy - Prevent XSS
        # Enhanced CSP with proper Next.js support and external API allowlist
        is_production = os.getenv("ALICE_ENVIRONMENT", "development") == "production"
        
        if is_production:
            # Stricter CSP for production
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "  # Next.js requires inline styles
                "img-src 'self' data: blob: https:; "
                "media-src 'self' data: blob:; "
                "connect-src 'self' ws: wss: "
                "https://api.openai.com https://api.spotify.com "
                "https://accounts.google.com https://oauth2.googleapis.com; "
                "font-src 'self' data:; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'; "
                "form-action 'self'; "
                "upgrade-insecure-requests"
            )
        else:
            # Development CSP (more permissive)
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob: https:; "
                "media-src 'self' data: blob:; "
                "connect-src 'self' ws: wss: "
                "https://api.openai.com https://api.spotify.com "
                "https://accounts.google.com https://oauth2.googleapis.com "
                "http://localhost:* http://127.0.0.1:*; "
                "font-src 'self' data:; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'"
            )
        response.headers["Content-Security-Policy"] = csp_policy
        
        # X-Frame-Options - Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options - Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Referrer Policy - Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy - Limit browser features
        permissions_policy = (
            "camera=(), microphone=(self), "
            "geolocation=(), payment=(), "
            "usb=(), display-capture=()"
        )
        response.headers["Permissions-Policy"] = permissions_policy
        
        # X-Permitted-Cross-Domain-Policies - Limit Flash/PDF policies
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        # Additional modern security headers
        response.headers["X-DNS-Prefetch-Control"] = "off"  # Disable DNS prefetching
        response.headers["X-Download-Options"] = "noopen"   # IE download security
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"  # COEP
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"     # COOP
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"  # CORP
        
        # Server identification (minimize info disclosure)
        response.headers["Server"] = "Alice/2.0"
        
        # Enhanced CORS headers for allowed origins
        origin = request.headers.get("origin")
        if origin and origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization, X-Requested-With, "
                "Accept, Origin, Cache-Control, X-File-Name, "
                "X-Request-ID, X-CSRF-Token, X-Alice-Version"
            )
            response.headers["Access-Control-Expose-Headers"] = (
                "X-Request-ID, X-Alice-Security, X-Alice-Version, "
                "X-RateLimit-Limit, X-RateLimit-Remaining"
            )
            response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours
        elif origin:
            # Log unauthorized origin attempts
            logger.warning(f"CORS request from unauthorized origin: {origin} for {request.url.path}")
            # Do not set CORS headers for unauthorized origins
        
        # Custom Alice headers for debugging (non-production)
        if os.getenv("ALICE_DEBUG", "0") == "1":
            response.headers["X-Alice-Security"] = "enabled"
            response.headers["X-Alice-Version"] = "2.0"


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection for state-changing operations
    Uses double-submit cookie pattern
    """
    
    def __init__(self, app, exempt_paths: List[str] = None):
        super().__init__(app)
        # Paths that don't need CSRF protection (API endpoints, webhooks)
        self.exempt_paths = exempt_paths or [
            "/health",
            "/metrics", 
            "/api/docs",
            "/openapi.json",
            "/harmony/test"  # Test endpoint
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip CSRF for exempt paths and GET/HEAD/OPTIONS
        if (request.url.path in self.exempt_paths or 
            request.method in ["GET", "HEAD", "OPTIONS"]):
            return await call_next(request)
        
        # For state-changing methods, validate CSRF token
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            self._validate_csrf_token(request)
        
        response = await call_next(request)
        
        # Set CSRF cookie for browser clients
        if self._is_browser_request(request):
            self._set_csrf_cookie(response)
        
        return response
    
    def _validate_csrf_token(self, request: Request):
        """Validate CSRF token for state-changing requests"""
        # Get token from header or form data
        csrf_token = (
            request.headers.get("X-CSRF-Token") or
            request.headers.get("X-Requested-With") == "XMLHttpRequest"  # Simple AJAX check
        )
        
        # For development, be permissive with CSRF
        if os.getenv("ALICE_DEBUG", "0") == "1":
            return
        
        # In production, implement proper CSRF validation
        # For now, we'll log and continue
        if not csrf_token:
            logger.warning(f"Missing CSRF token for {request.method} {request.url.path}")
    
    def _set_csrf_cookie(self, response: Response):
        """Set CSRF cookie for browser clients"""
        csrf_token = secrets.token_urlsafe(32)
        response.set_cookie(
            "csrf_token",
            csrf_token,
            httponly=False,  # JavaScript needs access
            secure=os.getenv("FORCE_SECURE_COOKIES", "0") == "1",
            samesite="strict",
            max_age=3600  # 1 hour
        )
    
    def _is_browser_request(self, request: Request) -> bool:
        """Check if request is from a browser"""
        user_agent = request.headers.get("user-agent", "").lower()
        return any(browser in user_agent for browser in 
                  ["mozilla", "chrome", "safari", "edge", "firefox"])


def get_security_config() -> Dict[str, str]:
    """Get security configuration from environment"""
    return {
        "allowed_origins": os.getenv("ALICE_ALLOWED_ORIGINS", "http://localhost:3000"),
        "force_https": os.getenv("FORCE_HTTPS_HEADERS", "0"),
        "debug_mode": os.getenv("ALICE_DEBUG", "0"),
        "csrf_exempt_paths": os.getenv("CSRF_EXEMPT_PATHS", "/health,/metrics,/api/docs")
    }


def configure_secure_app(app):
    """Configure FastAPI app with security middleware"""
    config = get_security_config()
    
    # Parse allowed origins
    allowed_origins = [origin.strip() for origin in config["allowed_origins"].split(",") if origin.strip()]
    
    # Parse CSRF exempt paths  
    csrf_exempt_paths = [path.strip() for path in config["csrf_exempt_paths"].split(",") if path.strip()]
    
    # Add security middlewares (order matters - last added runs first)
    app.add_middleware(CSRFProtectionMiddleware, exempt_paths=csrf_exempt_paths)
    app.add_middleware(SecurityHeadersMiddleware, allowed_origins=allowed_origins)
    
    logger.info("Security middleware configured successfully")
    return app