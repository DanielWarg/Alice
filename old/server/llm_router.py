"""
FastAPI router for LLM coordination endpoints
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import logging

from llm_coordinator import LLMCoordinator

logger = logging.getLogger("alice.llm_router")
router = APIRouter(prefix="/api/v1/llm", tags=["llm"])

# Global coordinator instance
coordinator: Optional[LLMCoordinator] = None

def get_coordinator() -> LLMCoordinator:
    """Get or create coordinator instance"""
    global coordinator
    if coordinator is None:
        coordinator = LLMCoordinator()
    return coordinator

class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., description="User message")
    history: Optional[List[Dict[str, str]]] = Field(None, description="Conversation history")
    force_path: Optional[str] = Field(None, description="Force routing path (FAST/DEEP)")

class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    provider: str
    path: str
    classification: Dict[str, Any]
    tools_used: List[str]
    timing: Dict[str, float]

@router.post("/chat", response_model=Dict[str, Any])
async def chat(request: ChatRequest):
    """
    Process chat request with intelligent routing.
    
    Returns response with provider information and timing.
    """
    try:
        coord = get_coordinator()
        result = await coord.process_request(
            user_input=request.message,
            history=request.history,
            force_path=request.force_path
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Chat request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {e}")

@router.get("/status")
async def get_status():
    """
    Get LLM coordinator and model status.
    
    Returns status information for monitoring.
    """
    try:
        coord = get_coordinator()
        status = coord.get_status()
        return status
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/health")
async def health_check():
    """
    Perform comprehensive health check.
    
    Tests model connectivity and basic functionality.
    """
    try:
        coord = get_coordinator()
        health = await coord.health_check()
        
        if health["status"] != "healthy":
            raise HTTPException(status_code=503, detail=health)
            
        return health
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {e}")

@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker():
    """
    Reset circuit breaker for manual recovery.
    
    Admin endpoint for troubleshooting.
    """
    try:
        coord = get_coordinator()
        if coord.model_manager:
            coord.model_manager.reset_circuit_breaker()
            return {"status": "reset", "message": "Circuit breaker reset successfully"}
        else:
            return {"status": "error", "message": "Model manager not initialized"}
            
    except Exception as e:
        logger.error(f"Circuit breaker reset failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reset failed: {e}")

@router.get("/models/available")
async def list_available_models():
    """
    List available models and their status.
    
    Returns model information for UI/debugging.
    """
    try:
        coord = get_coordinator()
        
        if not coord.model_manager:
            return {"models": [], "message": "Model manager not initialized"}
        
        status = coord.model_manager.get_status()
        
        models = [
            {
                "name": status["primary"]["name"],
                "type": "primary",
                "healthy": not status["primary"]["circuit_breaker_open"],
                "failure_count": status["primary"]["failure_count"]
            },
            {
                "name": status["fallback"]["name"], 
                "type": "fallback",
                "healthy": True  # Assume fallback is always available
            }
        ]
        
        return {"models": models, "status": status}
        
    except Exception as e:
        logger.error(f"Model listing failed: {e}")
        return {"models": [], "error": str(e)}

@router.post("/test/simple")
async def simple_test():
    """
    Run simple test to verify system functionality.
    
    Useful for integration testing and debugging.
    """
    test_cases = [
        {"message": "Hej Alice", "expected_path": "FAST"},
        {"message": "Tänd lampan i köket", "expected_path": "DEEP"},
        {"message": "Vad är väder idag?", "expected_path": "FAST"}
    ]
    
    results = []
    coord = get_coordinator()
    
    for test in test_cases:
        try:
            result = await coord.process_request(test["message"])
            
            results.append({
                "test": test["message"],
                "expected_path": test["expected_path"],
                "actual_path": result.get("path", "unknown"),
                "provider": result.get("provider", "unknown"),
                "success": True,
                "response_length": len(result.get("response", ""))
            })
            
        except Exception as e:
            results.append({
                "test": test["message"],
                "expected_path": test["expected_path"],
                "success": False,
                "error": str(e)
            })
    
    return {"test_results": results}

# Include router in main app
def setup_router(app):
    """Setup LLM router in FastAPI app"""
    app.include_router(router)