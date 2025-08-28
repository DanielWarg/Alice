#!/usr/bin/env python3
"""
Guardian Gate Middleware - Admission Control
============================================

Drop-in middleware som implementerar admission control framför alla LLM-anrop.
Kollar Guardian status var ~250ms och returnerar 429/503 innan vi rör LLM.

Features:
- Cached status checks (250ms TTL)
- 429 för degradation (brownout)
- 503 för complete intake stop
- Request ID tracking
- Guardian mode headers
"""

import time
import asyncio
import httpx
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request

class GuardianGate(BaseHTTPMiddleware):
    """
    Admission control middleware som checkar Guardian status
    innan requests tillåts gå vidare till LLM-lager.
    """
    
    def __init__(self, app, 
                 guardian_url: str = "http://localhost:8787/health",
                 cache_ttl_ms: int = 250,
                 timeout_s: float = 0.25):
        super().__init__(app)
        self.guardian_url = guardian_url
        self.cache_ttl_ms = cache_ttl_ms
        self.timeout_s = timeout_s
        
        # Status cache
        self._cache = None
        self._cache_ts = 0
        
        # Hysteresis för unknown status - förhindra flapping
        self.unknown_streak = 0
        self.unknown_threshold = 3  # Block efter 3 consecutive unknown
        self.last_known_good_mode = 'ok'
        
        # Metrics
        self.requests_total = 0
        self.requests_blocked = 0
        self.requests_degraded = 0
        self.unknown_graceful_passes = 0
        
        self.logger = logging.getLogger("guardian.gate")
        
    async def _get_guardian_status(self) -> dict:
        """
        Hämta Guardian status med caching för performance.
        Returnerar alltid en dict med åtminstone 'mode' key.
        """
        now_ms = time.time() * 1000
        
        # Använd cache om tillgängligt och fräscht
        if self._cache and (now_ms - self._cache_ts) < self.cache_ttl_ms:
            return self._cache
        
        # Hämta ny status från Guardian
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.get(self.guardian_url)
                
                if response.status_code == 200:
                    status_data = response.json()
                    
                    # Extrahera mode från Guardian response
                    # Guardian kan returnera olika format, normalisera till vårt
                    if 'status' in status_data:
                        guardian_status = status_data['status']
                        if guardian_status == 'emergency':
                            mode = 'stop'
                        elif guardian_status == 'degraded':
                            mode = 'degrade'  
                        else:
                            mode = 'ok'
                    else:
                        # Fallback parsing
                        mode = 'ok'
                    
                    # Bygga unified status
                    status = {
                        'mode': mode,
                        'guardian_status': guardian_status if 'status' in status_data else 'unknown',
                        'timestamp': now_ms,
                        'guardian_response': status_data
                    }
                    
                else:
                    # Guardian svarar med felkod
                    self.logger.warning(f"Guardian returned status {response.status_code}")
                    status = {
                        'mode': 'unknown',
                        'guardian_status': 'unreachable',
                        'timestamp': now_ms,
                        'error': f"HTTP {response.status_code}"
                    }
                    
        except asyncio.TimeoutError:
            self.logger.warning(f"Guardian status check timed out ({self.timeout_s}s)")
            status = {
                'mode': 'unknown',
                'guardian_status': 'timeout', 
                'timestamp': now_ms,
                'error': 'timeout'
            }
            
        except Exception as e:
            self.logger.error(f"Guardian status check failed: {e}")
            status = {
                'mode': 'unknown',
                'guardian_status': 'error',
                'timestamp': now_ms, 
                'error': str(e)
            }
        
        # Uppdatera cache
        self._cache = status
        self._cache_ts = now_ms
        
        return status
    
    def _should_block_request(self, request: Request, mode: str) -> tuple[bool, int, str]:
        """
        Avgör om request ska blockeras baserat på Guardian mode och request path.
        
        Returns:
            (should_block, status_code, reason)
        """
        path = request.url.path
        
        # STOP mode - blockera allt utom health checks
        if mode == 'stop':
            if path.startswith(('/health', '/api/health', '/api/metrics')):
                return False, 0, 'health_exempt'
            return True, 503, 'guardian_stop_intake'
        
        # DEGRADE mode - selective blocking
        if mode == 'degrade':
            # Blockera chat/LLM requests för brownout
            if path.startswith(('/api/chat', '/api/v1/llm', '/api/brain')):
                return True, 429, 'guardian_brownout'
            # Låt andra requests passera
            return False, 0, 'degrade_passthrough'
        
        # UNKNOWN mode - graceful degradation med hysteresis
        if mode == 'unknown':
            self.unknown_streak += 1
            
            # Graceful degradation: Allow requests om inte persistent unknown
            if self.unknown_streak < self.unknown_threshold:
                # Log för debugging
                if path.startswith(('/api/chat', '/api/v1/llm')):
                    self.unknown_graceful_passes += 1
                    self.logger.debug(f"Unknown mode graceful pass #{self.unknown_streak} for {path}")
                return False, 0, f'unknown_graceful_pass_{self.unknown_streak}'
            
            # Efter threshold: block LLM requests men låt övrigt passera
            if path.startswith(('/api/chat', '/api/v1/llm')):
                return True, 503, f'guardian_persistent_unknown_{self.unknown_streak}'
            return False, 0, 'unknown_passthrough'
        else:
            # Reset unknown streak när vi får känd status
            if mode in ['ok', 'degrade', 'stop']:
                if self.unknown_streak > 0:
                    self.logger.info(f"Guardian status recovered after {self.unknown_streak} unknown checks")
                self.unknown_streak = 0
                self.last_known_good_mode = mode
        
        # OK mode - släpp igenom allt
        return False, 0, 'ok'
    
    def _create_blocked_response(self, status_code: int, reason: str, 
                               request_id: str, mode: str, 
                               guardian_status: dict) -> JSONResponse:
        """Skapa standardiserad response för blockerade requests."""
        
        message_map = {
            'guardian_stop_intake': 'Guardian har stoppat alla nya requests (system overload)',
            'guardian_brownout': 'Guardian brownout-läge aktivt - försök igen om en stund',
            'guardian_unknown_precaution': 'Guardian status okänd - säkerhetsblockering av LLM requests'
        }
        
        response_data = {
            'error': message_map.get(reason, f'Request blocked: {reason}'),
            'guardian_mode': mode,
            'guardian_status': guardian_status.get('guardian_status', 'unknown'),
            'request_id': request_id,
            'timestamp': time.time(),
            'retry_after': 5 if status_code == 429 else 15  # Seconds
        }
        
        # Lägg till Retry-After header
        headers = {
            'x-guardian-mode': mode,
            'x-guardian-status': guardian_status.get('guardian_status', 'unknown'),
            'x-request-id': request_id,
            'retry-after': str(response_data['retry_after'])
        }
        
        return JSONResponse(
            content=response_data,
            status_code=status_code,
            headers=headers
        )
    
    async def dispatch(self, request: Request, call_next):
        """Main middleware logic - admission control."""
        
        # Generate request ID för tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Uppdatera metrics
        self.requests_total += 1
        
        # Hämta Guardian status
        guardian_status = await self._get_guardian_status()
        mode = guardian_status.get('mode', 'unknown')
        
        # Avgör om request ska blockeras
        should_block, status_code, reason = self._should_block_request(request, mode)
        
        if should_block:
            # Uppdatera metrics
            if status_code == 429:
                self.requests_degraded += 1
            else:
                self.requests_blocked += 1
            
            # Logga blockering
            self.logger.info(f"Blocked request {request_id}: {request.method} {request.url.path} -> {status_code} ({reason})")
            
            # Returnera blocked response
            return self._create_blocked_response(
                status_code, reason, request_id, mode, guardian_status
            )
        
        # Request tillåts - fortsätt till nästa middleware/handler
        try:
            response = await call_next(request)
            
            # Lägg till Guardian headers på successful responses
            response.headers['x-guardian-mode'] = mode
            response.headers['x-guardian-status'] = guardian_status.get('guardian_status', 'unknown')
            response.headers['x-request-id'] = request_id
            
            return response
            
        except Exception as e:
            self.logger.error(f"Request {request_id} failed after admission: {e}")
            raise
    
    def get_metrics(self) -> dict:
        """Returnera admission control metrics."""
        return {
            'requests_total': self.requests_total,
            'requests_blocked': self.requests_blocked, 
            'requests_degraded': self.requests_degraded,
            'block_rate': self.requests_blocked / max(self.requests_total, 1),
            'degrade_rate': self.requests_degraded / max(self.requests_total, 1),
            'cache_age_ms': (time.time() * 1000) - self._cache_ts if self._cache else 0,
            'guardian_url': self.guardian_url,
            'cache_ttl_ms': self.cache_ttl_ms
        }


# Convenience function för enkel setup
def create_guardian_gate_middleware(app, **kwargs) -> GuardianGate:
    """Factory function för att skapa och registrera GuardianGate middleware."""
    middleware = GuardianGate(app, **kwargs)
    app.add_middleware(GuardianGate, **kwargs)
    return middleware


# Test endpoint för manual verification
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/guardian-gate/status")
async def guardian_gate_status(request: Request):
    """Endpoint för att visa Guardian Gate metrics och status."""
    
    # Hitta GuardianGate middleware instance
    gate_middleware = None
    for middleware in request.app.middleware_stack:
        if hasattr(middleware, 'cls') and middleware.cls == GuardianGate:
            # FastAPI wrapping gör det lite tricky att komma åt instance
            # Vi kommer implementera detta mer elegantly senare
            break
    
    return {
        'guardian_gate': 'active',
        'endpoint': '/api/guardian-gate/status',
        'middleware_active': gate_middleware is not None,
        'request_id': getattr(request.state, 'request_id', None)
    }


if __name__ == "__main__":
    # Test Guardian Gate lokalt
    import asyncio
    from fastapi import FastAPI
    
    app = FastAPI()
    app.add_middleware(GuardianGate)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "Test endpoint reached"}
    
    @app.get("/api/chat/test")
    async def chat_test():
        return {"message": "Chat endpoint reached"}
    
    print("Testing Guardian Gate middleware...")
    print("Start Guardian daemon first: cd server && python -m guardian.guardian")
    print("Then run: uvicorn mw_guardian_gate:app --host 127.0.0.1 --port 8001")