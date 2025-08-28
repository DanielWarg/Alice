"""
Enhanced Error Handling for External Service Failures
Production-ready error management for Google, Spotify, OpenAI, and other external APIs
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from fastapi import HTTPException, status
from contextlib import asynccontextmanager

from error_handlers import AliceError, ProblemDetail
from api_client_manager import ServiceStatus

logger = logging.getLogger("alice.external_service_errors")

class ServiceErrorType(Enum):
    """Types of external service errors"""
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    TIMEOUT_ERROR = "timeout_error"
    CONNECTION_ERROR = "connection_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INVALID_REQUEST = "invalid_request"
    RESOURCE_NOT_FOUND = "resource_not_found"
    PERMISSION_DENIED = "permission_denied"
    SERVICE_DEGRADED = "service_degraded"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"

class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    REFRESH_TOKEN = "refresh_token"
    REAUTHORIZE = "reauthorize"
    WAIT_AND_RETRY = "wait_and_retry"
    FALLBACK_SERVICE = "fallback_service"
    CACHED_RESPONSE = "cached_response"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    FAIL_IMMEDIATELY = "fail_immediately"

@dataclass
class ServiceErrorDetails:
    """Detailed information about a service error"""
    service_name: str
    error_type: ServiceErrorType
    original_error: str
    recovery_strategy: RecoveryStrategy
    retry_after: Optional[int] = None
    user_message_sv: Optional[str] = None
    user_message_en: Optional[str] = None
    technical_details: Optional[Dict[str, Any]] = None
    suggested_actions: Optional[List[str]] = None

class ExternalServiceError(AliceError):
    """Enhanced error class for external service failures"""
    
    def __init__(
        self,
        service_name: str,
        error_type: ServiceErrorType,
        title: str,
        detail: Optional[str] = None,
        status_code: int = 503,
        recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY_WITH_BACKOFF,
        retry_after: Optional[int] = None,
        original_error: Optional[Exception] = None,
        technical_details: Optional[Dict[str, Any]] = None
    ):
        self.service_name = service_name
        self.error_type_enum = error_type
        self.recovery_strategy = recovery_strategy
        self.retry_after = retry_after
        self.original_error = original_error
        self.technical_details = technical_details or {}
        
        # Generate appropriate user messages
        self.user_message_sv, self.user_message_en = self._generate_user_messages(
            service_name, error_type, detail
        )
        
        super().__init__(
            title=title,
            detail=self.user_message_sv,
            status_code=status_code,
            error_type=f"external-service-{error_type.value}",
            errors=[{
                "service": service_name,
                "error_type": error_type.value,
                "recovery_strategy": recovery_strategy.value,
                "retry_after": retry_after,
                "technical_details": technical_details
            }]
        )
    
    def _generate_user_messages(
        self,
        service_name: str,
        error_type: ServiceErrorType,
        detail: Optional[str]
    ) -> Tuple[str, str]:
        """Generate user-friendly messages in Swedish and English"""
        
        service_names_sv = {
            "google_calendar": "Google Kalender",
            "gmail": "Gmail",
            "spotify": "Spotify",
            "openai": "AI-assistenten",
            "google": "Google-tjänster"
        }
        
        service_display_sv = service_names_sv.get(service_name, service_name)
        
        messages = {
            ServiceErrorType.AUTHENTICATION_ERROR: (
                f"Kunde inte autentisera med {service_display_sv}. Vänligen logga in igen.",
                f"Failed to authenticate with {service_name}. Please log in again."
            ),
            ServiceErrorType.AUTHORIZATION_ERROR: (
                f"Du saknar behörighet att komma åt {service_display_sv}. Kontrollera dina inställningar.",
                f"You don't have permission to access {service_name}. Please check your settings."
            ),
            ServiceErrorType.RATE_LIMIT_ERROR: (
                f"{service_display_sv} begränsar antalet förfrågningar. Alice kommer att försöka igen senare.",
                f"{service_name} is rate limiting requests. Alice will retry later."
            ),
            ServiceErrorType.QUOTA_EXCEEDED: (
                f"Daglig kvot för {service_display_sv} har överskridits. Försök igen imorgon.",
                f"Daily quota for {service_name} has been exceeded. Please try again tomorrow."
            ),
            ServiceErrorType.TIMEOUT_ERROR: (
                f"{service_display_sv} svarar långsamt. Alice försöker igen med längre timeout.",
                f"{service_name} is responding slowly. Alice will retry with longer timeout."
            ),
            ServiceErrorType.CONNECTION_ERROR: (
                f"Kunde inte ansluta till {service_display_sv}. Kontrollera din internetanslutning.",
                f"Could not connect to {service_name}. Please check your internet connection."
            ),
            ServiceErrorType.SERVICE_UNAVAILABLE: (
                f"{service_display_sv} är tillfälligt otillgänglig. Alice kommer att försöka igen senare.",
                f"{service_name} is temporarily unavailable. Alice will try again later."
            ),
            ServiceErrorType.INVALID_REQUEST: (
                f"Ogiltig förfrågan till {service_display_sv}. Detta kan vara ett tillfälligt problem.",
                f"Invalid request to {service_name}. This may be a temporary issue."
            ),
            ServiceErrorType.RESOURCE_NOT_FOUND: (
                f"Den begärda resursen hittades inte i {service_display_sv}.",
                f"The requested resource was not found in {service_name}."
            ),
            ServiceErrorType.PERMISSION_DENIED: (
                f"Åtkomst nekad till {service_display_sv}. Kontrollera dina behörigheter.",
                f"Access denied to {service_name}. Please check your permissions."
            ),
            ServiceErrorType.SERVICE_DEGRADED: (
                f"{service_display_sv} har begränsad funktionalitet. Vissa funktioner kanske inte fungerar.",
                f"{service_name} has limited functionality. Some features may not work."
            ),
            ServiceErrorType.CIRCUIT_BREAKER_OPEN: (
                f"{service_display_sv} är tillfälligt avstängd på grund av upprepade fel. Försöker igen snart.",
                f"{service_name} is temporarily disabled due to repeated errors. Will retry soon."
            )
        }
        
        default_messages = (
            f"Ett oväntat fel uppstod med {service_display_sv}. {detail or ''}",
            f"An unexpected error occurred with {service_name}. {detail or ''}"
        )
        
        return messages.get(error_type, default_messages)
    
    def get_recovery_instructions(self) -> Dict[str, List[str]]:
        """Get recovery instructions for different error types"""
        
        instructions = {
            RecoveryStrategy.RETRY_WITH_BACKOFF: [
                "Alice försöker igen automatiskt",
                "Vänta några sekunder och försök igen",
                "Kontakta support om problemet kvarstår"
            ],
            RecoveryStrategy.REFRESH_TOKEN: [
                "Alice försöker förnya åtkomst-token automatiskt",
                "Om problemet kvarstår, logga ut och in igen",
                "Kontrollera att ditt konto fortfarande är anslutet"
            ],
            RecoveryStrategy.REAUTHORIZE: [
                "Du behöver ansluta ditt konto igen",
                "Gå till Inställningar > Kontoanslutningar",
                "Följ instruktionerna för att återansluta tjänsten"
            ],
            RecoveryStrategy.WAIT_AND_RETRY: [
                "Tjänsten är tillfälligt otillgänglig",
                f"Försök igen om {self.retry_after or 60} sekunder",
                "Alice kommer att försöka igen automatiskt"
            ],
            RecoveryStrategy.FALLBACK_SERVICE: [
                "Alice använder en alternativ tjänst",
                "Vissa funktioner kan vara begränsade",
                "Normal funktionalitet återställs när tjänsten är tillgänglig"
            ],
            RecoveryStrategy.CACHED_RESPONSE: [
                "Alice visar senast kända information",
                "Data kan vara något föråldrad",
                "Ny data hämtas när tjänsten är tillgänglig"
            ],
            RecoveryStrategy.GRACEFUL_DEGRADATION: [
                "Vissa funktioner är tillfälligt otillgängliga",
                "Alice fortsätter fungera med begränsad funktionalitet",
                "Alla funktioner återställs när tjänsten är tillgänglig"
            ],
            RecoveryStrategy.FAIL_IMMEDIATELY: [
                "Denna åtgärd kunde inte slutföras",
                "Kontrollera dina inställningar och försök igen",
                "Kontakta support om problemet kvarstår"
            ]
        }
        
        return {
            "sv": instructions.get(self.recovery_strategy, []),
            "en": [
                # Add English translations if needed for international users
            ]
        }
    
    def to_problem_detail(self, instance: Optional[str] = None, request_id: Optional[str] = None) -> ProblemDetail:
        """Convert to RFC 7807 Problem Detail with additional service information"""
        problem = super().to_problem_detail(instance, request_id)
        
        # Add service-specific extensions
        problem.service_name = self.service_name
        problem.error_category = "external_service"
        problem.recovery_strategy = self.recovery_strategy.value
        problem.retry_after = self.retry_after
        problem.recovery_instructions = self.get_recovery_instructions()
        problem.technical_details = self.technical_details
        
        return problem

class ExternalServiceErrorHandler:
    """Centralized error handling for external services"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.last_error_times: Dict[str, datetime] = {}
        self.recovery_strategies: Dict[ServiceErrorType, RecoveryStrategy] = {
            ServiceErrorType.AUTHENTICATION_ERROR: RecoveryStrategy.REFRESH_TOKEN,
            ServiceErrorType.AUTHORIZATION_ERROR: RecoveryStrategy.REAUTHORIZE,
            ServiceErrorType.RATE_LIMIT_ERROR: RecoveryStrategy.WAIT_AND_RETRY,
            ServiceErrorType.QUOTA_EXCEEDED: RecoveryStrategy.WAIT_AND_RETRY,
            ServiceErrorType.TIMEOUT_ERROR: RecoveryStrategy.RETRY_WITH_BACKOFF,
            ServiceErrorType.CONNECTION_ERROR: RecoveryStrategy.RETRY_WITH_BACKOFF,
            ServiceErrorType.SERVICE_UNAVAILABLE: RecoveryStrategy.GRACEFUL_DEGRADATION,
            ServiceErrorType.INVALID_REQUEST: RecoveryStrategy.FAIL_IMMEDIATELY,
            ServiceErrorType.RESOURCE_NOT_FOUND: RecoveryStrategy.FAIL_IMMEDIATELY,
            ServiceErrorType.PERMISSION_DENIED: RecoveryStrategy.REAUTHORIZE,
            ServiceErrorType.SERVICE_DEGRADED: RecoveryStrategy.FALLBACK_SERVICE,
            ServiceErrorType.CIRCUIT_BREAKER_OPEN: RecoveryStrategy.WAIT_AND_RETRY,
        }
    
    def classify_error(
        self,
        service_name: str,
        status_code: Optional[int],
        error_message: str,
        headers: Optional[Dict[str, str]] = None
    ) -> ServiceErrorType:
        """Classify an error based on status code and message"""
        
        headers = headers or {}
        error_msg_lower = error_message.lower()
        
        # Check status codes first
        if status_code:
            if status_code == 401:
                return ServiceErrorType.AUTHENTICATION_ERROR
            elif status_code == 403:
                if "quota" in error_msg_lower or "limit" in error_msg_lower:
                    return ServiceErrorType.QUOTA_EXCEEDED
                return ServiceErrorType.AUTHORIZATION_ERROR
            elif status_code == 429:
                return ServiceErrorType.RATE_LIMIT_ERROR
            elif status_code == 404:
                return ServiceErrorType.RESOURCE_NOT_FOUND
            elif 500 <= status_code < 600:
                return ServiceErrorType.SERVICE_UNAVAILABLE
        
        # Check error message patterns
        if any(word in error_msg_lower for word in ["timeout", "timed out"]):
            return ServiceErrorType.TIMEOUT_ERROR
        elif any(word in error_msg_lower for word in ["connection", "network", "resolve"]):
            return ServiceErrorType.CONNECTION_ERROR
        elif any(word in error_msg_lower for word in ["quota", "usage limit"]):
            return ServiceErrorType.QUOTA_EXCEEDED
        elif any(word in error_msg_lower for word in ["rate limit", "too many requests"]):
            return ServiceErrorType.RATE_LIMIT_ERROR
        elif any(word in error_msg_lower for word in ["permission", "access denied"]):
            return ServiceErrorType.PERMISSION_DENIED
        elif "circuit breaker" in error_msg_lower:
            return ServiceErrorType.CIRCUIT_BREAKER_OPEN
        
        # Default classification
        return ServiceErrorType.SERVICE_UNAVAILABLE
    
    def create_service_error(
        self,
        service_name: str,
        original_error: Exception,
        status_code: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        technical_details: Optional[Dict[str, Any]] = None
    ) -> ExternalServiceError:
        """Create a standardized service error from an exception"""
        
        error_message = str(original_error)
        error_type = self.classify_error(service_name, status_code, error_message, headers)
        recovery_strategy = self.recovery_strategies.get(error_type, RecoveryStrategy.RETRY_WITH_BACKOFF)
        
        # Determine retry delay based on headers and error type
        retry_after = None
        if headers and "retry-after" in headers:
            try:
                retry_after = int(headers["retry-after"])
            except ValueError:
                pass
        elif error_type == ServiceErrorType.RATE_LIMIT_ERROR:
            retry_after = 60  # Default 1 minute for rate limits
        elif error_type == ServiceErrorType.QUOTA_EXCEEDED:
            retry_after = 3600  # 1 hour for quota exceeded
        
        # Track error frequency
        error_key = f"{service_name}:{error_type.value}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        self.last_error_times[error_key] = datetime.utcnow()
        
        # Determine appropriate HTTP status code
        http_status = status_code or self._get_default_status_code(error_type)
        
        return ExternalServiceError(
            service_name=service_name,
            error_type=error_type,
            title=f"External Service Error: {service_name}",
            detail=error_message,
            status_code=http_status,
            recovery_strategy=recovery_strategy,
            retry_after=retry_after,
            original_error=original_error,
            technical_details=technical_details
        )
    
    def _get_default_status_code(self, error_type: ServiceErrorType) -> int:
        """Get default HTTP status code for error type"""
        status_mapping = {
            ServiceErrorType.AUTHENTICATION_ERROR: status.HTTP_401_UNAUTHORIZED,
            ServiceErrorType.AUTHORIZATION_ERROR: status.HTTP_403_FORBIDDEN,
            ServiceErrorType.PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
            ServiceErrorType.RATE_LIMIT_ERROR: status.HTTP_429_TOO_MANY_REQUESTS,
            ServiceErrorType.QUOTA_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
            ServiceErrorType.RESOURCE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
            ServiceErrorType.INVALID_REQUEST: status.HTTP_400_BAD_REQUEST,
            ServiceErrorType.TIMEOUT_ERROR: status.HTTP_504_GATEWAY_TIMEOUT,
            ServiceErrorType.CONNECTION_ERROR: status.HTTP_502_BAD_GATEWAY,
            ServiceErrorType.SERVICE_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
            ServiceErrorType.SERVICE_DEGRADED: status.HTTP_503_SERVICE_UNAVAILABLE,
            ServiceErrorType.CIRCUIT_BREAKER_OPEN: status.HTTP_503_SERVICE_UNAVAILABLE,
        }
        
        return status_mapping.get(error_type, status.HTTP_503_SERVICE_UNAVAILABLE)
    
    def get_error_statistics(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        now = datetime.utcnow()
        stats = {
            "total_errors": sum(self.error_counts.values()),
            "error_types": {},
            "services": {},
            "recent_errors": 0  # Last hour
        }
        
        for error_key, count in self.error_counts.items():
            service, error_type = error_key.split(":", 1)
            
            # Filter by service if specified
            if service_name and service != service_name:
                continue
            
            # Count recent errors (last hour)
            last_error = self.last_error_times.get(error_key)
            if last_error and (now - last_error).total_seconds() < 3600:
                stats["recent_errors"] += 1
            
            # Error type statistics
            if error_type not in stats["error_types"]:
                stats["error_types"][error_type] = 0
            stats["error_types"][error_type] += count
            
            # Service statistics
            if service not in stats["services"]:
                stats["services"][service] = {
                    "total_errors": 0,
                    "error_types": {}
                }
            stats["services"][service]["total_errors"] += count
            if error_type not in stats["services"][service]["error_types"]:
                stats["services"][service]["error_types"][error_type] = 0
            stats["services"][service]["error_types"][error_type] += count
        
        return stats
    
    def should_circuit_break(self, service_name: str, error_threshold: int = 10) -> bool:
        """Determine if service should be circuit broken"""
        now = datetime.utcnow()
        recent_errors = 0
        
        # Count errors in the last 5 minutes
        for error_key, last_error_time in self.last_error_times.items():
            if error_key.startswith(f"{service_name}:") and last_error_time:
                if (now - last_error_time).total_seconds() < 300:  # 5 minutes
                    recent_errors += self.error_counts.get(error_key, 0)
        
        return recent_errors >= error_threshold

# Global error handler instance
external_service_error_handler = ExternalServiceErrorHandler()

# Context manager for handling external service calls
@asynccontextmanager
async def handle_service_call(
    service_name: str,
    operation: str = "unknown",
    reraise: bool = True
):
    """Context manager that automatically handles external service errors"""
    try:
        yield
    except ExternalServiceError:
        # Already handled, just re-raise
        if reraise:
            raise
    except Exception as e:
        # Convert to standardized service error
        service_error = external_service_error_handler.create_service_error(
            service_name=service_name,
            original_error=e,
            technical_details={"operation": operation}
        )
        
        logger.error(
            f"External service error in {service_name}.{operation}: {e}",
            extra={
                "service_name": service_name,
                "operation": operation,
                "error_type": service_error.error_type_enum.value,
                "recovery_strategy": service_error.recovery_strategy.value
            }
        )
        
        if reraise:
            raise service_error

# Convenience functions for common service error patterns
def google_service_error(original_error: Exception, service: str = "google") -> ExternalServiceError:
    """Create Google service-specific error"""
    return external_service_error_handler.create_service_error(
        service_name=service,
        original_error=original_error,
        technical_details={"provider": "google"}
    )

def spotify_service_error(original_error: Exception) -> ExternalServiceError:
    """Create Spotify service-specific error"""
    return external_service_error_handler.create_service_error(
        service_name="spotify",
        original_error=original_error,
        technical_details={"provider": "spotify"}
    )

def openai_service_error(original_error: Exception) -> ExternalServiceError:
    """Create OpenAI service-specific error"""
    return external_service_error_handler.create_service_error(
        service_name="openai", 
        original_error=original_error,
        technical_details={"provider": "openai"}
    )