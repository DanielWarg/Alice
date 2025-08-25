from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import json
import asyncio
import logging

from agent.proactive_trigger import proactive_trigger
from agent.pattern_recognizer import pattern_recognizer
from proactive_shadow import shadow
from logger_config import get_logger

router = APIRouter(prefix="/api/proactive", tags=["proactive"])
logger = get_logger("proactive_router")

class FeedbackRequest(BaseModel):
    action: str  # accept, decline, snooze
    pattern_id: str
    metadata: Optional[Dict[str, Any]] = None

class ProactiveSettingsRequest(BaseModel):
    level: Optional[str] = None  # off, minimal, standard, eager
    quiet_hours_start: Optional[int] = None
    quiet_hours_end: Optional[int] = None
    max_prompts_per_day: Optional[int] = None
    shadow_mode: Optional[bool] = None
    show_banners_only: Optional[bool] = None

@router.post("/feedback")
async def record_feedback(request: FeedbackRequest):
    """Record user feedback on proactive suggestions"""
    try:
        await proactive_trigger.record_suggestion_response(
            request.action, request.pattern_id, request.metadata
        )
        
        return {
            "status": "ok",
            "message": f"Feedback '{request.action}' recorded for pattern {request.pattern_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_proactive_status():
    """Get current proactive system status"""
    try:
        status = await proactive_trigger.get_proactive_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get proactive status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_suggestion_history(limit: int = 50):
    """Get recent suggestion history"""
    try:
        history = await proactive_trigger.get_suggestion_history(limit)
        return {
            "status": "ok",
            "history": history
        }
    except Exception as e:
        logger.error(f"Failed to get suggestion history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/shadow/report")
async def generate_shadow_report(days: int = 7):
    """Generate and export shadow mode report"""
    try:
        report_path = shadow.export_shadow_report(days)
        
        return {
            "status": "ok",
            "message": f"Shadow report generated for {days} days",
            "report_path": report_path
        }
        
    except Exception as e:
        logger.error(f"Failed to generate shadow report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/shadow/kpis")
async def get_shadow_kpis(date: Optional[str] = None):
    """Get shadow mode KPIs for a specific date"""
    try:
        kpis = shadow.calculate_daily_kpis(date)
        shadow.store_daily_kpis(kpis)
        
        return {
            "status": "ok",
            "kpis": kpis
        }
        
    except Exception as e:
        logger.error(f"Failed to get shadow KPIs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settings")
async def update_proactive_settings(request: ProactiveSettingsRequest):
    """Update proactive system settings"""
    try:
        # Filter out None values
        settings_update = {
            k: v for k, v in request.dict().items() 
            if v is not None
        }
        
        if not settings_update:
            return {"status": "ok", "message": "No settings to update"}
        
        proactive_trigger.update_settings(settings_update)
        
        return {
            "status": "ok",
            "message": f"Updated settings: {list(settings_update.keys())}",
            "updated_settings": settings_update
        }
        
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/patterns/analyze")
async def trigger_pattern_analysis(lookback_days: int = 7):
    """Manually trigger pattern analysis"""
    try:
        patterns = await pattern_recognizer.analyze_ambient_summaries(lookback_days)
        
        return {
            "status": "ok",
            "patterns_found": len(patterns),
            "patterns": [
                {
                    "id": p.id,
                    "type": p.pattern_type.value,
                    "description": p.description,
                    "confidence": p.confidence,
                    "occurrences": p.occurrences
                }
                for p in patterns
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patterns")
async def get_patterns(min_confidence: float = 0.3):
    """Get current patterns"""
    try:
        patterns = await pattern_recognizer.get_patterns_for_triggering(min_confidence)
        
        return {
            "status": "ok",
            "patterns": [
                {
                    "id": p.id,
                    "type": p.pattern_type.value,
                    "description": p.description,
                    "confidence": p.confidence,
                    "occurrences": p.occurrences,
                    "last_seen": p.last_seen.isoformat(),
                    "first_seen": p.first_seen.isoformat(),
                    "pattern_data": p.pattern_data
                }
                for p in patterns
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/proactive")
async def proactive_websocket(websocket: WebSocket):
    """WebSocket endpoint for proactive suggestions"""
    await websocket.accept()
    await proactive_trigger.add_websocket(websocket)
    
    logger.info("Proactive WebSocket connected")
    
    try:
        # Send initial status
        status = await proactive_trigger.get_proactive_status()
        await websocket.send_text(json.dumps({
            "type": "status",
            "data": status
        }))
        
        # Listen for client messages (responses to suggestions)
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                if data.get("type") == "suggestion_response":
                    # Handle user response to suggestion
                    suggestion_id = data.get("suggestion_id")
                    action = data.get("action")  # accept, decline, snooze
                    metadata = data.get("metadata", {})
                    
                    if suggestion_id and action:
                        await proactive_trigger.record_suggestion_response(
                            suggestion_id, action, metadata
                        )
                        
                        # Send acknowledgment
                        await websocket.send_text(json.dumps({
                            "type": "response_ack",
                            "suggestion_id": suggestion_id,
                            "action": action
                        }))
                
                elif data.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": proactive_trigger._get_current_timestamp()
                    }))
                    
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received on proactive WebSocket")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                logger.error(f"Error processing proactive WebSocket message: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info("Proactive WebSocket disconnected")
    except Exception as e:
        logger.error(f"Proactive WebSocket error: {e}")
    finally:
        await proactive_trigger.remove_websocket(websocket)

# Start proactive monitoring when router is imported
async def start_proactive_system():
    """Start the proactive monitoring system"""
    try:
        asyncio.create_task(proactive_trigger.start_monitoring())
        logger.info("Proactive system started successfully")
    except Exception as e:
        logger.error(f"Failed to start proactive system: {e}")

# Add a utility method to proactive_trigger for timestamps
if not hasattr(proactive_trigger, '_get_current_timestamp'):
    from datetime import datetime
    def _get_current_timestamp():
        return datetime.now().isoformat()
    proactive_trigger._get_current_timestamp = _get_current_timestamp