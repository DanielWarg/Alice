"""
Standardized error handling for Alice AI Assistant following RFC 7807 (Problem Details for HTTP APIs)
https://tools.ietf.org/html/rfc7807
"""

from typing import Any, Dict, Optional, List, Union
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
from pydantic import BaseModel, Field
import logging
import time
import traceback
from datetime import datetime

logger = logging.getLogger("alice.errors")


class ProblemDetail(BaseModel):
    """
    RFC 7807 Problem Detail model
    Standard structure for HTTP API error responses
    """
    type: str = Field(
        description="A URI reference that identifies the problem type",
        example="https://alice.ai/problems/validation-error"
    )
    title: str = Field(
        description="A short, human-readable summary of the problem type",
        example="Validation Error"
    )
    status: int = Field(
        description="The HTTP status code",
        example=400
    )
    detail: Optional[str] = Field(
        default=None,
        description="A human-readable explanation specific to this occurrence",
        example="The 'query' parameter is required but was not provided"
    )
    instance: Optional[str] = Field(
        default=None,
        description="A URI reference that identifies the specific occurrence",
        example="/api/chat/stream"
    )
    
    # Extension fields for Alice
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="When the error occurred"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Unique request identifier for tracing"
    )
    errors: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Detailed validation errors"
    )


class AliceError(Exception):
    """Base exception for Alice-specific errors"""
    
    def __init__(
        self,
        title: str,
        detail: Optional[str] = None,
        status_code: int = 500,
        error_type: str = "internal-error",
        errors: Optional[List[Dict[str, Any]]] = None
    ):
        self.title = title
        self.detail = detail
        self.status_code = status_code
        self.error_type = error_type
        self.errors = errors
        super().__init__(self.title)
    
    def to_problem_detail(self, instance: Optional[str] = None, request_id: Optional[str] = None) -> ProblemDetail:
        return ProblemDetail(
            type=f"https://alice.ai/problems/{self.error_type}",
            title=self.title,
            status=self.status_code,
            detail=self.detail,
            instance=instance,
            request_id=request_id,
            errors=self.errors
        )


class ValidationError(AliceError):
    """Raised when input validation fails"""
    
    def __init__(self, detail: str, errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            title="Validation Error",
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type="validation-error",
            errors=errors
        )


class SwedishDateTimeValidationError(ValidationError):
    """Raised when Swedish datetime parsing fails"""
    
    def __init__(self, input_text: str, supported_formats: List[str]):
        detail = f"Could not parse Swedish datetime '{input_text}'. Supported formats: {', '.join(supported_formats)}"
        super().__init__(
            detail=detail,
            errors=[{
                "field": "datetime",
                "input": input_text,
                "supported_formats": supported_formats
            }]
        )


class ExternalServiceError(AliceError):
    """Raised when external service calls fail"""
    
    def __init__(self, service_name: str, detail: Optional[str] = None):
        super().__init__(
            title=f"External Service Error: {service_name}",
            detail=detail or f"Failed to communicate with {service_name}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_type="external-service-error"
        )


class CircuitBreakerOpenError(ExternalServiceError):
    """Raised when circuit breaker is open"""
    
    def __init__(self, service_name: str):
        super().__init__(
            service_name=service_name,
            detail=f"Circuit breaker for {service_name} is open - failing fast to protect service"
        )


class AuthenticationError(AliceError):
    """Raised when authentication fails"""
    
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            title="Authentication Error",
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_type="authentication-error"
        )


class AuthorizationError(AliceError):
    """Raised when authorization fails"""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            title="Authorization Error", 
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
            error_type="authorization-error"
        )


class ResourceNotFoundError(AliceError):
    """Raised when requested resource is not found"""
    
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            title="Resource Not Found",
            detail=f"{resource} with id '{resource_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_type="resource-not-found"
        )


class RateLimitError(AliceError):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, limit: int, window: str, retry_after: Optional[int] = None):
        super().__init__(
            title="Rate Limit Exceeded",
            detail=f"Request rate limit of {limit} requests per {window} exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_type="rate-limit-exceeded",
            errors=[{
                "limit": limit,
                "window": window,
                "retry_after": retry_after
            }] if retry_after else None
        )


def generate_request_id() -> str:
    """Generate unique request ID for tracing"""
    return f"alice-{int(time.time() * 1000)}"


async def alice_exception_handler(request: Request, exc: AliceError) -> JSONResponse:
    """Handle Alice-specific exceptions"""
    
    request_id = getattr(request.state, "request_id", generate_request_id())
    instance = str(request.url.path)
    
    problem = exc.to_problem_detail(instance=instance, request_id=request_id)
    
    # Log error
    logger.error(
        f"Alice error: {exc.title} - {exc.detail} "
        f"[{request_id}] {request.method} {instance}",
        extra={
            "request_id": request_id,
            "error_type": exc.error_type,
            "status_code": exc.status_code,
            "path": instance,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.dict(),
        headers={"Content-Type": "application/problem+json"}
    )


async def http_exception_problem_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Convert HTTPException to Problem Details format"""
    
    request_id = getattr(request.state, "request_id", generate_request_id())
    instance = str(request.url.path)
    
    # Map common HTTP status codes to problem types
    type_mapping = {
        400: "validation-error",
        401: "authentication-error",
        403: "authorization-error", 
        404: "resource-not-found",
        405: "method-not-allowed",
        409: "conflict",
        422: "validation-error",
        429: "rate-limit-exceeded",
        500: "internal-error",
        502: "bad-gateway",
        503: "service-unavailable",
        504: "gateway-timeout"
    }
    
    error_type = type_mapping.get(exc.status_code, "http-error")
    
    problem = ProblemDetail(
        type=f"https://alice.ai/problems/{error_type}",
        title=exc.detail if isinstance(exc.detail, str) else "HTTP Error",
        status=exc.status_code,
        detail=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        instance=instance,
        request_id=request_id
    )
    
    # Log non-client errors
    if exc.status_code >= 500:
        logger.error(
            f"HTTP {exc.status_code}: {exc.detail} "
            f"[{request_id}] {request.method} {instance}",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "path": instance,
                "method": request.method
            }
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.dict(),
        headers={"Content-Type": "application/problem+json"}
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic ValidationError with Problem Details format"""
    
    request_id = getattr(request.state, "request_id", generate_request_id())
    instance = str(request.url.path)
    
    # Extract validation errors
    errors = []
    if hasattr(exc, 'errors'):
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            })
    
    problem = ProblemDetail(
        type="https://alice.ai/problems/validation-error",
        title="Validation Error",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="One or more validation errors occurred",
        instance=instance,
        request_id=request_id,
        errors=errors
    )
    
    logger.warning(
        f"Validation error: {len(errors)} validation errors "
        f"[{request_id}] {request.method} {instance}",
        extra={
            "request_id": request_id,
            "validation_errors": len(errors),
            "path": instance,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem.dict(),
        headers={"Content-Type": "application/problem+json"}
    )


async def internal_server_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected internal server errors"""
    
    request_id = getattr(request.state, "request_id", generate_request_id())
    instance = str(request.url.path)
    
    # Log full traceback for internal errors
    logger.error(
        f"Internal server error: {str(exc)} "
        f"[{request_id}] {request.method} {instance}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "exception_type": type(exc).__name__,
            "path": instance,
            "method": request.method
        }
    )
    
    problem = ProblemDetail(
        type="https://alice.ai/problems/internal-error",
        title="Internal Server Error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred while processing your request",
        instance=instance,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem.dict(),
        headers={"Content-Type": "application/problem+json"}
    )


def setup_error_handlers(app):
    """Configure FastAPI app with standardized error handlers"""
    
    # Alice-specific errors
    app.add_exception_handler(AliceError, alice_exception_handler)
    
    # HTTPException -> Problem Details
    app.add_exception_handler(HTTPException, http_exception_problem_handler)
    
    # Pydantic validation errors
    try:
        from pydantic import ValidationError as PydanticValidationError
        app.add_exception_handler(PydanticValidationError, validation_exception_handler)
    except ImportError:
        pass
    
    # Catch-all for unexpected errors
    app.add_exception_handler(Exception, internal_server_error_handler)
    
    logger.info("Standardized error handlers configured")


# Request ID middleware
class RequestIDMiddleware:
    """Add request ID to all requests for tracing"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Generate request ID
            request_id = generate_request_id()
            
            # Add to scope
            scope["state"] = getattr(scope, "state", {})
            scope["state"]["request_id"] = request_id
            
            # Add response header
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    headers[b"x-request-id"] = request_id.encode()
                    message["headers"] = list(headers.items())
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)