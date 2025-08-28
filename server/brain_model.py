#!/usr/bin/env python3
"""
Brain Model API - Dynamic Model Switching för Brownout
======================================================

API endpoints som Guardian kan använda för att switchat modell och parametrar 
under brownout-conditions. Implementerar BRAIN_MODEL_PRIMARY/BROWNOUT pattern.

Features:
- Model switching (gpt-oss:20b ↔ gpt-oss:7b)
- Context window adjustment (8 → 3)
- RAG top_k reduction (8 → 3)
- Tool disabling (heavy toolchains)
- State persistence & validation
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from log_json import jlog, rlog
import httpx

router = APIRouter(prefix="/api/brain")

# Global brain state - i produktion skulle detta vara i databas eller Redis
BRAIN_STATE = {
    # Model configuration  
    "model": "gpt-oss:20b",
    "model_primary": "gpt-oss:20b", 
    "model_brownout": "gpt-oss:7b",
    "mode": "normal",  # normal | brownout | emergency
    
    # Context & RAG settings
    "context_window": 8,
    "context_window_normal": 8,
    "context_window_brownout": 3,
    "rag_top_k": 8,
    "rag_top_k_normal": 8,
    "rag_top_k_brownout": 3,
    
    # Tool configuration
    "tools_heavy": True,  # Code interpreter, file search, etc
    "tools_enabled": ["search", "calculator", "weather", "calendar", "code_interpreter"],
    "tools_essential": ["search", "calculator", "weather"],  # Keep during brownout
    
    # Performance settings
    "max_tokens": 4096,
    "max_tokens_normal": 4096,
    "max_tokens_brownout": 1024,
    "temperature": 0.7,
    "temperature_brownout": 0.5,  # More deterministic during stress
    
    # Metadata
    "last_switch": time.time(),
    "switch_reason": "startup",
    "switch_count": 0
}

# Request models
class ModelSwitchRequest(BaseModel):
    model: Optional[str] = Field(None, description="Target model name")
    mode: Optional[str] = Field(None, description="Operating mode: normal|brownout|emergency")
    reason: Optional[str] = Field("api_request", description="Reason for switch")

class ContextRequest(BaseModel):
    context_window: int = Field(..., ge=1, le=32, description="Context window size")
    reason: Optional[str] = Field("api_request", description="Reason for change")

class RAGRequest(BaseModel):
    top_k: int = Field(..., ge=1, le=20, description="RAG top_k results")
    reason: Optional[str] = Field("api_request", description="Reason for change")

class ToolsRequest(BaseModel):
    enabled: Optional[List[str]] = Field(None, description="List of enabled tools")
    heavy_tools: Optional[bool] = Field(None, description="Enable/disable heavy tools")
    reason: Optional[str] = Field("api_request", description="Reason for change")

class BrownoutRequest(BaseModel):
    activate: bool = Field(..., description="Activate or deactivate brownout mode")
    level: Optional[str] = Field("moderate", description="Brownout level: light|moderate|heavy")
    reason: Optional[str] = Field("api_request", description="Reason for brownout change")


# Helper functions
def validate_model(model: str) -> bool:
    """Validate that model name is supported."""
    supported_models = ["gpt-oss:20b", "gpt-oss:7b", "llama3:8b"]
    return model in supported_models

def apply_brownout_settings(level: str = "moderate"):
    """Apply brownout settings based on level."""
    global BRAIN_STATE
    
    if level == "light":
        BRAIN_STATE.update({
            "context_window": 6,
            "rag_top_k": 6,
            "max_tokens": 2048,
            "temperature": 0.6
        })
    elif level == "moderate":
        BRAIN_STATE.update({
            "context_window": BRAIN_STATE["context_window_brownout"],
            "rag_top_k": BRAIN_STATE["rag_top_k_brownout"],
            "max_tokens": BRAIN_STATE["max_tokens_brownout"],
            "temperature": BRAIN_STATE["temperature_brownout"]
        })
    elif level == "heavy":
        BRAIN_STATE.update({
            "context_window": 2,
            "rag_top_k": 2,
            "max_tokens": 512,
            "temperature": 0.3,
            "tools_heavy": False
        })

def apply_normal_settings():
    """Restore normal operational settings."""
    global BRAIN_STATE
    BRAIN_STATE.update({
        "model": BRAIN_STATE["model_primary"],
        "context_window": BRAIN_STATE["context_window_normal"],
        "rag_top_k": BRAIN_STATE["rag_top_k_normal"],
        "max_tokens": BRAIN_STATE["max_tokens_normal"],
        "temperature": 0.7,
        "tools_heavy": True,
        "mode": "normal"
    })

async def notify_ollama_model_switch(model: str) -> bool:
    """Notify Ollama to preload/switch to target model."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Attempt to generate empty completion to load model
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": "",  # Empty prompt to just load model
                    "stream": False,
                    "options": {"num_predict": 1}
                }
            )
            
            if response.status_code == 200:
                jlog("brain.ollama_preload", model=model, success=True)
                return True
            else:
                jlog("brain.ollama_preload", model=model, success=False, 
                     status_code=response.status_code, level="WARN")
                return False
                
    except Exception as e:
        jlog("brain.ollama_preload", model=model, success=False, 
             error=str(e), level="ERROR")
        return False


# API Endpoints
@router.get("/status")
async def get_brain_status():
    """Get current brain state and configuration."""
    return {
        "brain_state": BRAIN_STATE.copy(),
        "timestamp": time.time(),
        "uptime_seconds": time.time() - BRAIN_STATE["last_switch"]
    }

@router.post("/model/switch")
async def switch_model(request: ModelSwitchRequest):
    """
    Switch AI model dynamically.
    Används av Guardian för att växla mellan gpt-oss:20b och 7b under brownout.
    """
    global BRAIN_STATE
    
    # Determine target model
    if request.model:
        target_model = request.model
    elif request.mode == "brownout":
        target_model = BRAIN_STATE["model_brownout"]
    elif request.mode == "normal":
        target_model = BRAIN_STATE["model_primary"]
    else:
        raise HTTPException(400, "Must specify either model or mode")
    
    # Validate model
    if not validate_model(target_model):
        raise HTTPException(400, f"Unsupported model: {target_model}")
    
    old_model = BRAIN_STATE["model"]
    old_mode = BRAIN_STATE["mode"]
    
    # Update state
    BRAIN_STATE.update({
        "model": target_model,
        "mode": request.mode or BRAIN_STATE["mode"],
        "last_switch": time.time(),
        "switch_reason": request.reason,
        "switch_count": BRAIN_STATE["switch_count"] + 1
    })
    
    # Apply mode-specific settings
    if request.mode == "brownout":
        apply_brownout_settings()
    elif request.mode == "normal":
        apply_normal_settings()
    
    # Log model switch
    rlog("brain.model_switch", 
         old_model=old_model, new_model=target_model,
         old_mode=old_mode, new_mode=request.mode,
         reason=request.reason, level="INFO")
    
    # Notify Ollama (async, don't wait for completion)
    asyncio.create_task(notify_ollama_model_switch(target_model))
    
    return {
        "success": True,
        "old_model": old_model,
        "new_model": target_model,
        "mode": BRAIN_STATE["mode"],
        "timestamp": BRAIN_STATE["last_switch"]
    }

@router.post("/context/set")
async def set_context_window(request: ContextRequest):
    """Set context window size."""
    global BRAIN_STATE
    
    old_context = BRAIN_STATE["context_window"]
    BRAIN_STATE["context_window"] = request.context_window
    
    rlog("brain.context_change",
         old_context=old_context, new_context=request.context_window,
         reason=request.reason)
    
    return {
        "success": True,
        "old_context_window": old_context,
        "new_context_window": request.context_window
    }

@router.post("/rag/set")
async def set_rag_params(request: RAGRequest):
    """Set RAG parameters."""
    global BRAIN_STATE
    
    old_top_k = BRAIN_STATE["rag_top_k"]
    BRAIN_STATE["rag_top_k"] = request.top_k
    
    rlog("brain.rag_change",
         old_top_k=old_top_k, new_top_k=request.top_k,
         reason=request.reason)
    
    return {
        "success": True,
        "old_rag_top_k": old_top_k,
        "new_rag_top_k": request.top_k
    }

@router.post("/tools/disable")
async def disable_tools(request: ToolsRequest):
    """Disable heavy tools during brownout."""
    global BRAIN_STATE
    
    old_heavy = BRAIN_STATE["tools_heavy"]
    old_enabled = BRAIN_STATE["tools_enabled"].copy()
    
    if request.heavy_tools is not None:
        BRAIN_STATE["tools_heavy"] = request.heavy_tools
    
    if request.enabled is not None:
        BRAIN_STATE["tools_enabled"] = request.enabled
    elif request.heavy_tools == False:
        # Disable heavy tools, keep essentials
        BRAIN_STATE["tools_enabled"] = BRAIN_STATE["tools_essential"].copy()
    
    rlog("brain.tools_change",
         old_heavy=old_heavy, new_heavy=BRAIN_STATE["tools_heavy"],
         old_enabled=old_enabled, new_enabled=BRAIN_STATE["tools_enabled"],
         reason=request.reason)
    
    return {
        "success": True,
        "tools_heavy": BRAIN_STATE["tools_heavy"],
        "tools_enabled": BRAIN_STATE["tools_enabled"]
    }

@router.post("/tools/enable-all")
async def enable_all_tools():
    """Re-enable all tools after brownout recovery."""
    global BRAIN_STATE
    
    BRAIN_STATE["tools_heavy"] = True
    BRAIN_STATE["tools_enabled"] = ["search", "calculator", "weather", "calendar", 
                                  "code_interpreter", "file_search", "image_generation"]
    
    rlog("brain.tools_restored", all_tools=True, reason="recovery")
    
    return {
        "success": True,
        "tools_heavy": True,
        "tools_enabled": BRAIN_STATE["tools_enabled"]
    }

@router.post("/brownout")
async def control_brownout(request: BrownoutRequest):
    """
    High-level brownout control.
    Aktiverar/deaktiverar brownout-läge med alla relaterade inställningar.
    """
    global BRAIN_STATE
    
    old_mode = BRAIN_STATE["mode"]
    
    if request.activate:
        # Activate brownout
        BRAIN_STATE["mode"] = "brownout"
        BRAIN_STATE["model"] = BRAIN_STATE["model_brownout"]
        apply_brownout_settings(request.level)
        
        rlog("brain.brownout_activated", 
             level=request.level, reason=request.reason, level="WARN")
        
        # Notify Ollama of model switch
        asyncio.create_task(notify_ollama_model_switch(BRAIN_STATE["model"]))
        
        return {
            "success": True,
            "brownout_active": True,
            "level": request.level,
            "model": BRAIN_STATE["model"],
            "settings": {
                "context_window": BRAIN_STATE["context_window"],
                "rag_top_k": BRAIN_STATE["rag_top_k"],
                "max_tokens": BRAIN_STATE["max_tokens"],
                "tools_heavy": BRAIN_STATE["tools_heavy"]
            }
        }
    else:
        # Deactivate brownout
        apply_normal_settings()
        
        rlog("brain.brownout_deactivated", 
             old_mode=old_mode, reason=request.reason)
        
        # Notify Ollama of model switch back
        asyncio.create_task(notify_ollama_model_switch(BRAIN_STATE["model"]))
        
        return {
            "success": True,
            "brownout_active": False,
            "model": BRAIN_STATE["model"],
            "mode": "normal"
        }

@router.get("/models/available")  
async def get_available_models():
    """List available models for switching."""
    return {
        "models": ["gpt-oss:20b", "gpt-oss:7b", "llama3:8b"],
        "current": BRAIN_STATE["model"],
        "primary": BRAIN_STATE["model_primary"],
        "brownout": BRAIN_STATE["model_brownout"]
    }

@router.post("/emergency/reset")
async def emergency_reset():
    """Emergency reset to safe defaults."""
    global BRAIN_STATE
    
    old_state = BRAIN_STATE.copy()
    
    # Reset to conservative settings
    BRAIN_STATE.update({
        "model": "gpt-oss:7b",  # Safe smaller model
        "mode": "emergency",
        "context_window": 2,
        "rag_top_k": 2,
        "max_tokens": 256,
        "temperature": 0.3,
        "tools_heavy": False,
        "tools_enabled": ["search"],  # Minimal tools
        "last_switch": time.time(),
        "switch_reason": "emergency_reset"
    })
    
    rlog("brain.emergency_reset", old_state=old_state, level="CRITICAL")
    
    # Notify Ollama
    asyncio.create_task(notify_ollama_model_switch("gpt-oss:7b"))
    
    return {
        "success": True,
        "mode": "emergency",
        "message": "Brain reset to emergency safe mode"
    }


# Helper function för andra moduler
def get_current_brain_config() -> Dict[str, Any]:
    """Get current brain configuration för användning i chat handlers etc."""
    return BRAIN_STATE.copy()

def is_brownout_active() -> bool:
    """Check if system is in brownout mode."""
    return BRAIN_STATE["mode"] in ["brownout", "emergency"]

def get_model_for_request() -> str:
    """Get appropriate model för current request."""
    return BRAIN_STATE["model"]

def get_context_window() -> int:
    """Get current context window setting."""
    return BRAIN_STATE["context_window"]

def get_rag_top_k() -> int:
    """Get current RAG top_k setting."""
    return BRAIN_STATE["rag_top_k"]

def are_heavy_tools_enabled() -> bool:
    """Check if heavy tools are currently enabled."""
    return BRAIN_STATE["tools_heavy"]

def get_enabled_tools() -> List[str]:
    """Get list of currently enabled tools."""
    return BRAIN_STATE["tools_enabled"].copy()


if __name__ == "__main__":
    # Test brain model API
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    
    print("Testing Brain Model API...")
    print("Start with: uvicorn brain_model:app --host 127.0.0.1 --port 8003")
    print("")
    print("Test endpoints:")
    print("  GET  /api/brain/status")  
    print("  POST /api/brain/model/switch {'mode': 'brownout'}")
    print("  POST /api/brain/brownout {'activate': true, 'level': 'moderate'}")
    print("  POST /api/brain/emergency/reset")