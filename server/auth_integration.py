"""
Authentication Integration for Alice FastAPI App
Integrates comprehensive authentication system with existing Alice application
"""
import os
import logging
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import init_database, run_database_maintenance
from auth_router import router as auth_router
from auth_rate_limiter import UserRateLimiter, check_request_rate_limit
from auth_service import AuthService, get_current_user
from auth_models import User, SWEDISH_ERROR_MESSAGES
from deps import get_db_session
from security import configure_secure_app

logger = logging.getLogger("alice.auth_integration")

def setup_authentication(app: FastAPI) -> FastAPI:
    """
    Setup comprehensive authentication for Alice FastAPI application
    
    This function:
    1. Initializes the database and creates tables
    2. Adds authentication middleware
    3. Registers authentication routes
    4. Sets up rate limiting
    5. Configures CORS for auth endpoints
    """
    
    logger.info("Setting up Alice authentication system...")
    
    # Initialize database
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Configure security middleware (this adds CSRF, security headers, etc.)
    app = configure_secure_app(app)
    
    # Add authentication router
    app.include_router(auth_router, prefix="/api")
    
    # Add authentication middleware
    app.add_middleware(AuthenticationMiddleware)
    
    # Add user-aware rate limiting middleware
    app.add_middleware(AuthRateLimitMiddleware)
    
    logger.info("Authentication system setup completed")
    return app

class AuthenticationMiddleware:
    """Authentication middleware to add user context to requests"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Add authentication context to request state
            try:
                # Get database session
                db = next(get_db_session())
                auth_service = AuthService(db)
                
                # Try to get current user from token
                user = None
                auth_header = request.headers.get("authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                    payload = auth_service.verify_token(token)
                    if payload:
                        user = auth_service.get_user_by_id(int(payload["sub"]))
                
                # Add user to request state
                request.state.current_user = user
                request.state.auth_service = auth_service
                request.state.db = db
                
            except Exception as e:
                logger.debug(f"Authentication middleware error: {e}")
                request.state.current_user = None
                request.state.auth_service = None
                request.state.db = None
        
        await self.app(scope, receive, send)

class AuthRateLimitMiddleware:
    """Rate limiting middleware with authentication awareness"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Skip rate limiting for certain paths
            exempt_paths = {"/api/health", "/api/metrics", "/docs", "/openapi.json"}
            if request.url.path in exempt_paths:
                await self.app(scope, receive, send)
                return
            
            # Determine endpoint type for rate limiting
            endpoint_type = "global"
            if request.url.path.startswith("/api/chat"):
                endpoint_type = "chat"
            elif request.url.path.startswith("/api/voice"):
                endpoint_type = "voice"
            elif request.url.path.startswith("/api/auth"):
                endpoint_type = "auth"
            elif request.url.path.startswith("/api/"):
                endpoint_type = "api"
            
            # Check rate limit
            try:
                db = getattr(request.state, 'db', None) or next(get_db_session())
                auth_service = getattr(request.state, 'auth_service', None) or AuthService(db)
                
                allowed, retry_after, stats = check_request_rate_limit(
                    request, endpoint_type, db, auth_service
                )
                
                if not allowed:
                    # Return rate limit exceeded response
                    response_content = {
                        "error": "rate_limit_exceeded",
                        "message": SWEDISH_ERROR_MESSAGES["rate_limit_exceeded"],
                        "retry_after": retry_after,
                        "limit_type": endpoint_type
                    }
                    
                    headers = [
                        (b"content-type", b"application/json"),
                        (b"x-ratelimit-exceeded", b"true")
                    ]
                    
                    if retry_after:
                        headers.append((b"retry-after", str(retry_after).encode()))
                    
                    await send({
                        "type": "http.response.start",
                        "status": 429,
                        "headers": headers
                    })
                    
                    import json
                    await send({
                        "type": "http.response.body",
                        "body": json.dumps(response_content).encode()
                    })
                    return
                
                # Add rate limit info to request state
                request.state.rate_limit_stats = stats
                
            except Exception as e:
                logger.error(f"Rate limiting middleware error: {e}")
        
        await self.app(scope, receive, send)

def get_optional_current_user(request: Request) -> Optional[User]:
    """Get current user from request state (optional, no exception if not authenticated)"""
    return getattr(request.state, 'current_user', None)

def get_required_current_user(request: Request) -> User:
    """Get current user from request state (required, raises exception if not authenticated)"""
    user = getattr(request.state, 'current_user', None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=SWEDISH_ERROR_MESSAGES["invalid_token"],
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

def require_admin_role(request: Request) -> User:
    """Require admin role for endpoint access"""
    user = get_required_current_user(request)
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=SWEDISH_ERROR_MESSAGES["permission_denied"]
        )
    return user

# Environment variable setup for authentication
def setup_auth_environment():
    """Setup authentication environment variables and configuration"""
    
    # Check for required environment variables
    required_vars = [
        "JWT_SECRET_KEY",
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"Missing authentication environment variables: {missing_vars}")
        
        # Generate JWT secret if missing
        if "JWT_SECRET_KEY" in missing_vars:
            import secrets
            jwt_secret = secrets.token_urlsafe(64)
            os.environ["JWT_SECRET_KEY"] = jwt_secret
            logger.warning("Generated temporary JWT_SECRET_KEY. Set a permanent one in production!")
    
    # Optional OAuth configuration check
    oauth_configs = {
        "Google": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
        "GitHub": ["GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"]
    }
    
    for provider, vars in oauth_configs.items():
        if all(os.getenv(var) for var in vars):
            logger.info(f"{provider} OAuth configured")
        else:
            logger.info(f"{provider} OAuth not configured (optional)")

# Startup tasks for authentication
async def auth_startup_tasks():
    """Run authentication-related startup tasks"""
    logger.info("Running authentication startup tasks...")
    
    # Setup environment
    setup_auth_environment()
    
    # Run database maintenance if needed
    if os.getenv("RUN_DB_MAINTENANCE", "0") == "1":
        try:
            run_database_maintenance()
        except Exception as e:
            logger.error(f"Database maintenance failed: {e}")
    
    logger.info("Authentication startup tasks completed")

# Shutdown tasks for authentication
async def auth_shutdown_tasks():
    """Run authentication-related shutdown tasks"""
    logger.info("Running authentication shutdown tasks...")
    
    # Close database connections, cleanup, etc.
    try:
        from database import engine
        engine.dispose()
    except Exception as e:
        logger.error(f"Database cleanup failed: {e}")
    
    logger.info("Authentication shutdown tasks completed")

# Utility functions for integration with existing Alice endpoints

def protect_endpoint(endpoint_func):
    """Decorator to protect existing endpoints with authentication"""
    from functools import wraps
    
    @wraps(endpoint_func)
    async def wrapper(*args, **kwargs):
        # Extract request from args/kwargs
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if request:
            user = get_required_current_user(request)
            kwargs['current_user'] = user
        
        return await endpoint_func(*args, **kwargs)
    
    return wrapper

def add_user_context(endpoint_func):
    """Decorator to add optional user context to existing endpoints"""
    from functools import wraps
    
    @wraps(endpoint_func)
    async def wrapper(*args, **kwargs):
        # Extract request from args/kwargs
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if request:
            user = get_optional_current_user(request)
            kwargs['current_user'] = user
        
        return await endpoint_func(*args, **kwargs)
    
    return wrapper

# Health check endpoint with authentication stats
def get_auth_health_info() -> dict:
    """Get authentication system health information"""
    try:
        from database import check_database_health, get_database_stats
        
        db_healthy = check_database_health()
        db_stats = get_database_stats() if db_healthy else {}
        
        return {
            "database_healthy": db_healthy,
            "database_stats": db_stats,
            "jwt_configured": bool(os.getenv("JWT_SECRET_KEY")),
            "oauth_providers": {
                "google": bool(os.getenv("GOOGLE_CLIENT_ID")),
                "github": bool(os.getenv("GITHUB_CLIENT_ID"))
            }
        }
    except Exception as e:
        logger.error(f"Auth health check failed: {e}")
        return {"error": str(e)}

# Export main setup function
__all__ = [
    'setup_authentication',
    'get_optional_current_user', 
    'get_required_current_user',
    'require_admin_role',
    'protect_endpoint',
    'add_user_context',
    'auth_startup_tasks',
    'auth_shutdown_tasks',
    'get_auth_health_info'
]