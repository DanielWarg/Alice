#!/usr/bin/env python3
"""
Request Timeout Middleware - HTTP Layer Protection
==================================================

Enkelt timeout middleware som förhindrar att HTTP-sockets hänger.
Kompletterar Guardian's 45s LLM timeout med 10-15s HTTP timeout.
"""

import asyncio
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request

class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    HTTP request timeout middleware.
    
    Wraps all requests with asyncio.wait_for() för att förhindra
    att sockets hänger vid långsamma LLM-operationer.
    """
    
    def __init__(self, app, timeout_seconds: float = 15.0):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger("timeout.middleware")
        
        # Metrics
        self.requests_total = 0
        self.requests_timeout = 0
        self.total_timeout_time = 0.0
        
    async def dispatch(self, request: Request, call_next):
        """Apply timeout to request processing."""
        
        self.requests_total += 1
        start_time = time.time()
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        try:
            # Wrap request i timeout
            response = await asyncio.wait_for(
                call_next(request), 
                timeout=self.timeout_seconds
            )
            
            # Log slow requests (80% av timeout)
            elapsed = time.time() - start_time
            if elapsed > (self.timeout_seconds * 0.8):
                self.logger.warning(
                    f"Slow request {request_id}: {request.method} {request.url.path} "
                    f"took {elapsed:.2f}s (timeout: {self.timeout_seconds}s)"
                )
            
            return response
            
        except asyncio.TimeoutError:
            # Request timed out
            self.requests_timeout += 1
            elapsed = time.time() - start_time  
            self.total_timeout_time += elapsed
            
            self.logger.error(
                f"Request timeout {request_id}: {request.method} {request.url.path} "
                f"exceeded {self.timeout_seconds}s"
            )
            
            # Return timeout response
            return JSONResponse(
                content={
                    'error': f'Request timed out after {self.timeout_seconds}s',
                    'timeout_seconds': self.timeout_seconds,
                    'request_id': request_id,
                    'timestamp': time.time(),
                    'suggestion': 'Try again or contact support if this persists'
                },
                status_code=504,
                headers={
                    'x-timeout': str(self.timeout_seconds),
                    'x-request-id': request_id,
                    'retry-after': '10'  # Suggest retry after 10 seconds
                }
            )
            
        except Exception as e:
            # Other errors - log but re-raise
            elapsed = time.time() - start_time
            self.logger.error(f"Request error {request_id} after {elapsed:.2f}s: {e}")
            raise
    
    def get_metrics(self) -> dict:
        """Return timeout middleware metrics."""
        return {
            'requests_total': self.requests_total,
            'requests_timeout': self.requests_timeout,
            'timeout_rate': self.requests_timeout / max(self.requests_total, 1),
            'timeout_seconds': self.timeout_seconds,
            'total_timeout_time': self.total_timeout_time,
            'avg_timeout_time': (self.total_timeout_time / max(self.requests_timeout, 1)) if self.requests_timeout > 0 else 0
        }


# Path-specific timeout middleware
class PathTimeoutMiddleware(BaseHTTPMiddleware):
    """
    Advanced timeout middleware med path-specific timeouts.
    
    Tillåter olika timeout-värden för olika endpoints:
    - /api/chat/* - 30s (LLM generation)
    - /api/brain/* - 15s (Model switching)
    - /* - 10s (Standard requests)
    """
    
    def __init__(self, app, timeout_config: dict = None):
        super().__init__(app)
        
        # Default timeout configuration  
        self.timeout_config = timeout_config or {
            '/api/chat': 30.0,      # LLM generation requests
            '/api/brain': 15.0,     # Model/brain operations
            '/api/agent': 25.0,     # Agent toolchain requests
            '/api/voice': 20.0,     # Voice processing
            '/api/upload': 45.0,    # File uploads
            'default': 10.0         # Everything else
        }
        
        self.logger = logging.getLogger("path_timeout.middleware")
        
        # Per-path metrics
        self.path_metrics = {}
        
    def _get_timeout_for_path(self, path: str) -> float:
        """Get timeout value for specific path."""
        
        # Check for exact matches first
        if path in self.timeout_config:
            return self.timeout_config[path]
        
        # Check for prefix matches
        for pattern, timeout in self.timeout_config.items():
            if pattern != 'default' and path.startswith(pattern):
                return timeout
        
        # Return default
        return self.timeout_config.get('default', 10.0)
    
    def _get_path_key(self, path: str) -> str:
        """Get metrics key for path (group similar paths)."""
        
        # Group paths för metrics
        if path.startswith('/api/chat'):
            return '/api/chat/*'
        elif path.startswith('/api/brain'):
            return '/api/brain/*'  
        elif path.startswith('/api/agent'):
            return '/api/agent/*'
        elif path.startswith('/api/voice'):
            return '/api/voice/*'
        elif path.startswith('/api/'):
            return '/api/*'
        else:
            return '/*'
    
    async def dispatch(self, request: Request, call_next):
        """Apply path-specific timeout to request."""
        
        path = request.url.path
        timeout = self._get_timeout_for_path(path)
        path_key = self._get_path_key(path)
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        # Initialize path metrics if needed
        if path_key not in self.path_metrics:
            self.path_metrics[path_key] = {
                'total': 0,
                'timeouts': 0,
                'total_time': 0.0
            }
        
        metrics = self.path_metrics[path_key]
        metrics['total'] += 1
        
        start_time = time.time()
        
        try:
            response = await asyncio.wait_for(call_next(request), timeout=timeout)
            
            elapsed = time.time() - start_time
            metrics['total_time'] += elapsed
            
            # Add timeout info to response headers
            response.headers['x-timeout-allowed'] = str(timeout)
            response.headers['x-timeout-used'] = f"{elapsed:.3f}"
            
            return response
            
        except asyncio.TimeoutError:
            metrics['timeouts'] += 1
            elapsed = time.time() - start_time
            
            self.logger.error(
                f"Path timeout {request_id}: {request.method} {path} "
                f"exceeded {timeout}s (path-specific)"
            )
            
            return JSONResponse(
                content={
                    'error': f'Request timed out after {timeout}s',
                    'path': path,
                    'timeout_seconds': timeout,
                    'request_id': request_id,
                    'timestamp': time.time()
                },
                status_code=504,
                headers={
                    'x-timeout-path': path_key,
                    'x-timeout': str(timeout),
                    'x-request-id': request_id
                }
            )
    
    def get_metrics(self) -> dict:
        """Return detailed path-based timeout metrics."""
        
        summary = {
            'timeout_config': self.timeout_config,
            'paths': {}
        }
        
        for path_key, metrics in self.path_metrics.items():
            summary['paths'][path_key] = {
                'total_requests': metrics['total'],
                'timeouts': metrics['timeouts'],  
                'timeout_rate': metrics['timeouts'] / max(metrics['total'], 1),
                'avg_response_time': metrics['total_time'] / max(metrics['total'], 1)
            }
        
        return summary


# Factory functions
def create_simple_timeout_middleware(app, timeout_seconds: float = 15.0):
    """Create and register simple timeout middleware."""
    app.add_middleware(TimeoutMiddleware, timeout_seconds=timeout_seconds)

def create_path_timeout_middleware(app, timeout_config: dict = None):
    """Create and register path-specific timeout middleware."""
    app.add_middleware(PathTimeoutMiddleware, timeout_config=timeout_config)


if __name__ == "__main__":
    # Test timeout middleware
    from fastapi import FastAPI
    import time
    
    app = FastAPI()
    app.add_middleware(TimeoutMiddleware, timeout_seconds=2.0)  # 2s för test
    
    @app.get("/fast")
    async def fast_endpoint():
        return {"message": "Fast response"}
    
    @app.get("/slow")
    async def slow_endpoint():
        await asyncio.sleep(5)  # Detta kommer timeout:a
        return {"message": "Slow response"}
    
    print("Testing timeout middleware...")
    print("Run: uvicorn mw_timeout:app --host 127.0.0.1 --port 8002")
    print("Test with:")
    print("  curl http://localhost:8002/fast   # Should work")
    print("  curl http://localhost:8002/slow   # Should timeout")