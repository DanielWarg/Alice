"""
Brain Mail Count API - Simple stub for Voice v2 demo
"""

import asyncio
import random
from typing import Dict, Any
from fastapi import APIRouter, Query
from pydantic import BaseModel
import logging

logger = logging.getLogger("alice.brain.mail")

router = APIRouter(prefix="/api/brain", tags=["brain"])

class MailCountResponse(BaseModel):
    count: int
    status: str = "ok"
    processing_time_ms: float = 0.0

@router.get("/mail-count", response_model=MailCountResponse)
async def get_mail_count(
    demo: int = Query(None, description="Demo mode - return specific count"),
    user_id: str = Query(None, description="User ID (for future use)")
):
    """
    Get unread mail count - currently a stub for Voice v2 demo
    
    TODO: Replace with real adapter:
    - Gmail API integration
    - IMAP connection
    - Exchange/Outlook integration
    """
    
    start_time = asyncio.get_event_loop().time()
    
    # Demo mode - return specific count if provided
    if demo is not None:
        count = max(0, demo)  # Ensure non-negative
    else:
        # Simulate realistic mail count (0-15, weighted toward lower numbers)
        count = random.choices([0, 1, 2, 3, 4, 5, 7, 10, 15], 
                             weights=[20, 25, 20, 15, 10, 5, 3, 1, 1])[0]
    
    # Simulate minimal processing time (realistic for cached mail count)
    await asyncio.sleep(random.uniform(0.1, 0.3))
    
    processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
    
    logger.info(f"Mail count requested: {count} ({processing_time:.0f}ms)")
    
    return MailCountResponse(
        count=count,
        processing_time_ms=processing_time
    )

@router.get("/mail-count/health")
async def mail_count_health():
    """Health check for mail count service"""
    
    return {
        "service": "mail-count",
        "status": "healthy",
        "mode": "stub",
        "note": "This is a demo stub. Replace with real mail adapter."
    }

# Additional mail-related endpoints for future expansion
@router.get("/mail-summary")
async def get_mail_summary(limit: int = Query(5, le=20)):
    """
    Get mail summary - placeholder for future implementation
    """
    
    return {
        "status": "not_implemented",
        "message": "Mail summary endpoint - coming soon",
        "todo": [
            "Integrate Gmail API",
            "Add IMAP support", 
            "Implement mail parsing",
            "Add privacy filtering"
        ]
    }

@router.post("/mail-mark-read")
async def mark_mail_read(mail_ids: list[str]):
    """
    Mark emails as read - placeholder for future implementation
    """
    
    return {
        "status": "not_implemented", 
        "message": "Mark read endpoint - coming soon",
        "received_ids": len(mail_ids)
    }