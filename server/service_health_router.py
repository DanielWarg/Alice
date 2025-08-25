"""
Service Health Monitoring Router
API endpoints for monitoring external service health, rate limits, and error statistics
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from database import get_db
from deps import get_current_user
from auth_models import User
from api_client_manager import api_client_manager, ServiceStatus
from external_service_errors import external_service_error_handler
from rate_limiter import RateLimitRule, RateLimitAlgorithm

logger = logging.getLogger("alice.service_health_router")

router = APIRouter(prefix="/api/v1/health", tags=["Service Health"])

# Pydantic models for API responses
class ServiceHealthResponse(BaseModel):
    name: str
    status: str
    base_url: str
    metrics: Dict[str, Any]
    circuit_breaker: Dict[str, Any]
    rate_limit: Dict[str, Any]
    configuration: Dict[str, Any]

class SystemHealthResponse(BaseModel):
    overall_health: str
    healthy_services: int
    total_services: int
    services: Dict[str, ServiceHealthResponse]
    timestamp: str

class ServiceErrorStats(BaseModel):
    total_errors: int
    error_types: Dict[str, int]
    services: Dict[str, Dict[str, Any]]
    recent_errors: int

class HealthCheckResult(BaseModel):
    healthy: bool
    response_time: Optional[float] = None
    error: Optional[str] = None
    timestamp: str
    note: Optional[str] = None

@router.get("/status", response_model=SystemHealthResponse)
async def get_system_health(
    include_details: bool = True
):
    """
    Get overall system health including all external services
    """
    try:
        health_status = api_client_manager.get_all_services_status()
        
        if not include_details:
            # Return simplified status
            return {
                "overall_health": health_status["overall_health"],
                "healthy_services": health_status["healthy_services"],
                "total_services": health_status["total_services"],
                "services": {},
                "timestamp": health_status["timestamp"]
            }
        
        return SystemHealthResponse(**health_status)
        
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kunde inte hämta systemhälsa"
        )

@router.get("/service/{service_name}", response_model=ServiceHealthResponse)
async def get_service_health(
    service_name: str
):
    """
    Get detailed health information for a specific service
    """
    try:
        service_status = api_client_manager.get_service_status(service_name)
        
        if "error" in service_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tjänst '{service_name}' hittades inte"
            )
        
        return ServiceHealthResponse(**service_status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get service health for {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kunde inte hämta hälsostatus för tjänst {service_name}"
        )

@router.post("/service/{service_name}/check")
async def check_service_health(
    service_name: str,
    background_tasks: BackgroundTasks
):
    """
    Perform active health check on a specific service
    """
    try:
        # Run health check in background to avoid blocking
        health_result = await api_client_manager.health_check(service_name)
        
        if service_name not in health_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tjänst '{service_name}' hittades inte"
            )
        
        result = health_result[service_name]
        return HealthCheckResult(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed for {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hälsokontroll misslyckades för tjänst {service_name}"
        )

@router.get("/errors", response_model=ServiceErrorStats)
async def get_error_statistics(
    service_name: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get error statistics for all services or a specific service
    Requires authentication to prevent information disclosure
    """
    try:
        error_stats = external_service_error_handler.get_error_statistics(service_name)
        return ServiceErrorStats(**error_stats)
        
    except Exception as e:
        logger.error(f"Failed to get error statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kunde inte hämta felstatistik"
        )

@router.get("/rate-limits")
async def get_rate_limit_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get current rate limit status for all services
    """
    try:
        services_status = api_client_manager.get_all_services_status()
        rate_limit_info = {}
        
        for service_name, service_data in services_status.get("services", {}).items():
            if "rate_limit" in service_data:
                rate_limit_info[service_name] = service_data["rate_limit"]
        
        return {
            "services": rate_limit_info,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Rate limits är per minut och nollställs varje minut"
        }
        
    except Exception as e:
        logger.error(f"Failed to get rate limit status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kunde inte hämta rate limit-status"
        )

@router.get("/circuit-breakers")
async def get_circuit_breaker_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get circuit breaker status for all services
    """
    try:
        services_status = api_client_manager.get_all_services_status()
        circuit_breaker_info = {}
        
        for service_name, service_data in services_status.get("services", {}).items():
            if "circuit_breaker" in service_data:
                cb_data = service_data["circuit_breaker"]
                circuit_breaker_info[service_name] = {
                    "state": cb_data["state"],
                    "failure_count": cb_data["failure_count"],
                    "next_attempt": cb_data.get("next_attempt"),
                    "description": {
                        "closed": "Normal operation - requests allowed",
                        "open": "Service disabled due to failures",
                        "half_open": "Testing if service has recovered"
                    }.get(cb_data["state"], "Unknown state")
                }
        
        return {
            "circuit_breakers": circuit_breaker_info,
            "timestamp": datetime.utcnow().isoformat(),
            "total_open": len([cb for cb in circuit_breaker_info.values() if cb["state"] == "open"])
        }
        
    except Exception as e:
        logger.error(f"Failed to get circuit breaker status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kunde inte hämta circuit breaker-status"
        )

@router.post("/service/{service_name}/reset-circuit-breaker")
async def reset_circuit_breaker(
    service_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Manually reset circuit breaker for a service (admin only)
    """
    # Check if user has admin privileges
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administratörsbehörighet krävs för att återställa circuit breakers"
        )
    
    try:
        # Get current service status
        service_status = api_client_manager.get_service_status(service_name)
        
        if "error" in service_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tjänst '{service_name}' hittades inte"
            )
        
        # Reset circuit breaker
        if service_name in api_client_manager.circuit_breakers:
            circuit_breaker = api_client_manager.circuit_breakers[service_name]
            circuit_breaker.state = "closed"
            circuit_breaker.failure_count = 0
            circuit_breaker.next_attempt_time = None
            
            logger.info(f"Circuit breaker reset for service {service_name} by user {current_user.username}")
            
            return {
                "success": True,
                "message": f"Circuit breaker för {service_name} har återställts",
                "service": service_name,
                "previous_state": service_status.get("circuit_breaker", {}).get("state"),
                "new_state": "closed"
            }
        else:
            return {
                "success": False,
                "message": f"Circuit breaker hittades inte för tjänst {service_name}"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset circuit breaker for {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kunde inte återställa circuit breaker för {service_name}"
        )

@router.get("/metrics")
async def get_service_metrics(
    service_name: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed metrics for service monitoring and alerting
    """
    try:
        services_status = api_client_manager.get_all_services_status()
        
        if service_name:
            # Return metrics for specific service
            if service_name not in services_status.get("services", {}):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tjänst '{service_name}' hittades inte"
                )
            
            service_data = services_status["services"][service_name]
            return {
                "service": service_name,
                "metrics": service_data.get("metrics", {}),
                "status": service_data.get("status"),
                "timestamp": services_status["timestamp"]
            }
        
        # Return aggregated metrics for all services
        total_requests = 0
        total_successful = 0
        total_failed = 0
        avg_response_times = []
        service_metrics = {}
        
        for svc_name, svc_data in services_status.get("services", {}).items():
            metrics = svc_data.get("metrics", {})
            
            total_requests += metrics.get("total_requests", 0)
            total_successful += metrics.get("successful_requests", 0)
            total_failed += metrics.get("failed_requests", 0)
            
            if metrics.get("avg_response_time", 0) > 0:
                avg_response_times.append(metrics["avg_response_time"])
            
            service_metrics[svc_name] = {
                "status": svc_data.get("status"),
                "requests": metrics.get("total_requests", 0),
                "success_rate": metrics.get("success_rate", 0),
                "avg_response_time": metrics.get("avg_response_time", 0)
            }
        
        overall_success_rate = 0
        if total_requests > 0:
            overall_success_rate = (total_successful / total_requests) * 100
        
        overall_avg_response_time = 0
        if avg_response_times:
            overall_avg_response_time = sum(avg_response_times) / len(avg_response_times)
        
        return {
            "overall_metrics": {
                "total_requests": total_requests,
                "successful_requests": total_successful,
                "failed_requests": total_failed,
                "overall_success_rate": round(overall_success_rate, 2),
                "overall_avg_response_time": round(overall_avg_response_time, 3)
            },
            "service_metrics": service_metrics,
            "system_health": services_status["overall_health"],
            "timestamp": services_status["timestamp"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get service metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kunde inte hämta tjänstemetriker"
        )

@router.get("/dashboard")
async def get_health_dashboard(
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive dashboard data for service health monitoring
    """
    try:
        # Get all health data in parallel
        services_status = api_client_manager.get_all_services_status()
        error_stats = external_service_error_handler.get_error_statistics()
        
        # Calculate dashboard metrics
        dashboard_data = {
            "summary": {
                "overall_health": services_status["overall_health"],
                "healthy_services": services_status["healthy_services"],
                "total_services": services_status["total_services"],
                "total_errors": error_stats["total_errors"],
                "recent_errors": error_stats["recent_errors"]
            },
            "services": {},
            "alerts": [],
            "recommendations": []
        }
        
        # Process each service
        for service_name, service_data in services_status.get("services", {}).items():
            dashboard_data["services"][service_name] = {
                "name": service_name,
                "status": service_data.get("status"),
                "success_rate": service_data.get("metrics", {}).get("success_rate", 0),
                "avg_response_time": service_data.get("metrics", {}).get("avg_response_time", 0),
                "circuit_breaker_state": service_data.get("circuit_breaker", {}).get("state"),
                "rate_limit_remaining": service_data.get("rate_limit", {}).get("remaining", 0)
            }
            
            # Generate alerts for problematic services
            if service_data.get("status") == "offline":
                dashboard_data["alerts"].append({
                    "severity": "critical",
                    "service": service_name,
                    "message": f"Tjänst {service_name} är offline"
                })
            elif service_data.get("status") == "degraded":
                dashboard_data["alerts"].append({
                    "severity": "warning", 
                    "service": service_name,
                    "message": f"Tjänst {service_name} har försämrad prestanda"
                })
            
            # Check for high error rates
            success_rate = service_data.get("metrics", {}).get("success_rate", 100)
            if success_rate < 95:
                dashboard_data["alerts"].append({
                    "severity": "warning",
                    "service": service_name,
                    "message": f"Låg framgångsfrekvens för {service_name}: {success_rate}%"
                })
            
            # Check for high response times
            avg_response_time = service_data.get("metrics", {}).get("avg_response_time", 0)
            if avg_response_time > 5.0:  # 5 seconds
                dashboard_data["alerts"].append({
                    "severity": "warning",
                    "service": service_name,
                    "message": f"Hög svarstid för {service_name}: {avg_response_time:.1f}s"
                })
        
        # Generate recommendations
        if error_stats["recent_errors"] > 10:
            dashboard_data["recommendations"].append(
                "Många fel rapporterade senaste timmen - kontrollera tjänstestatus"
            )
        
        if services_status["healthy_services"] < services_status["total_services"]:
            dashboard_data["recommendations"].append(
                "Vissa tjänster har problem - kontrollera circuit breakers och rate limits"
            )
        
        dashboard_data["timestamp"] = services_status["timestamp"]
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Failed to get health dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kunde inte hämta hälsodashboard"
        )

# Simplified health check for external monitoring systems
@router.get("/simple")
async def simple_health_check():
    """
    Simple health check endpoint for load balancers and monitoring systems
    Returns 200 OK if system is healthy, 503 if degraded/unhealthy
    """
    try:
        services_status = api_client_manager.get_all_services_status()
        overall_health = services_status.get("overall_health", "critical")
        
        if overall_health == "healthy":
            return {"status": "ok", "health": overall_health}
        elif overall_health == "degraded":
            return {"status": "degraded", "health": overall_health}
        else:
            # Return 503 for critical health issues
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="System health is critical"
            )
            
    except HTTPException:
        raise
    except Exception:
        # If we can't determine health, assume critical
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to determine system health"
        )