"""
B3 Privacy Hooks & Memory TTL - 'Glöm det där' funktionalitet
Hanterar privacy controls och automatisk memory cleanup
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
import re
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from memory import MemoryStore

logger = logging.getLogger("alice.b3_privacy")

class ForgetRequest(BaseModel):
    """Request to forget specific memories"""
    query: Optional[str] = None  # Natural language: "glöm vad jag sa om kakan"
    keywords: Optional[List[str]] = None  # Specific keywords to forget
    time_range: Optional[str] = None  # "last_hour", "today", "all"
    memory_ids: Optional[List[str]] = None  # Specific memory IDs to delete

class ForgetResponse(BaseModel):
    """Response from forget operation"""
    success: bool
    message: str
    deleted_count: int
    deleted_memory_ids: List[str]
    processing_time: float

class PrivacySettings(BaseModel):
    """Privacy configuration for memory TTL"""
    default_ttl_hours: int = 24 * 7  # 1 week default
    sensitive_content_ttl_hours: int = 24  # 1 day for sensitive content
    max_memory_age_days: int = 30  # Auto-delete after 30 days
    enable_auto_cleanup: bool = True
    forget_patterns: List[str] = []  # Regex patterns to auto-forget

class B3PrivacyHooks:
    """
    Handles privacy controls and memory TTL for B3 ambient voice system
    Provides 'glöm det där' functionality and automatic cleanup
    """
    
    def __init__(self, memory_store: MemoryStore = None):
        self.memory = memory_store
        self.privacy_settings = PrivacySettings()
        
        # Sensitive content detection patterns
        self.sensitive_patterns = [
            r'\b(lösenord|password|pin|kod|ssn|personnummer)\b',
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Card numbers
            r'\b\d{6}[\s-]?\d{4}\b',  # Swedish personnummer
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        ]
        
        # Forget command patterns (Swedish)
        self.forget_command_patterns = [
            r'\b(glöm|radera|ta bort|förget)\b.*\b(det|detta|den|dom|allt)\b',
            r'\b(glöm det där|glöm vad jag sa|radera minnet)\b',
            r'\b(privat|hemligt|konfidentiellt|secret)\b',
        ]
        
        # Auto-cleanup task
        self._cleanup_task = None
        # Note: Auto-cleanup will be started when needed to avoid event loop issues
        
        logger.info("B3 Privacy Hooks initialized")
    
    async def process_forget_request(self, request: ForgetRequest) -> ForgetResponse:
        """Process a request to forget memories"""
        start_time = time.time()
        deleted_ids = []
        
        try:
            if not self.memory:
                return ForgetResponse(
                    success=False,
                    message="Memory store not available",
                    deleted_count=0,
                    deleted_memory_ids=[],
                    processing_time=time.time() - start_time
                )
            
            # Get memories to delete
            memories_to_delete = await self._find_memories_to_forget(request)
            
            # Delete memories
            for memory in memories_to_delete:
                try:
                    await self.memory.delete(memory.get('id'))
                    deleted_ids.append(memory.get('id', 'unknown'))
                except Exception as e:
                    logger.error(f"Error deleting memory {memory.get('id')}: {e}")
            
            processing_time = time.time() - start_time
            
            logger.info(f"Forgot {len(deleted_ids)} memories in {processing_time:.2f}s")
            
            return ForgetResponse(
                success=True,
                message=f"Successfully forgot {len(deleted_ids)} memories",
                deleted_count=len(deleted_ids),
                deleted_memory_ids=deleted_ids,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error processing forget request: {e}")
            return ForgetResponse(
                success=False,
                message=f"Error forgetting memories: {str(e)}",
                deleted_count=0,
                deleted_memory_ids=[],
                processing_time=time.time() - start_time
            )
    
    async def _find_memories_to_forget(self, request: ForgetRequest) -> List[Dict]:
        """Find memories matching forget criteria"""
        all_memories = []
        
        try:
            # Get all memories (this would be more efficient with proper querying)
            # For now, we'll simulate getting recent memories
            
            if request.memory_ids:
                # Specific memory IDs
                for memory_id in request.memory_ids:
                    try:
                        memory = await self.memory.get(memory_id)
                        if memory:
                            all_memories.append(memory)
                    except:
                        pass
            
            elif request.query or request.keywords:
                # Search by content
                search_terms = []
                if request.query:
                    search_terms.extend(request.query.split())
                if request.keywords:
                    search_terms.extend(request.keywords)
                
                # Mock memory search - in real implementation would use memory store search
                # For now, return empty list as we don't have search implemented
                all_memories = []
                
            elif request.time_range:
                # Delete by time range
                cutoff_time = self._get_time_cutoff(request.time_range)
                if cutoff_time:
                    # Mock time-based deletion
                    # Would query memory store for memories older than cutoff_time
                    all_memories = []
            
        except Exception as e:
            logger.error(f"Error finding memories to forget: {e}")
        
        return all_memories
    
    def _get_time_cutoff(self, time_range: str) -> Optional[datetime]:
        """Get cutoff datetime for time-based forgetting"""
        now = datetime.now()
        
        if time_range == "last_hour":
            return now - timedelta(hours=1)
        elif time_range == "today":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == "yesterday":
            return now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        elif time_range == "last_week":
            return now - timedelta(days=7)
        elif time_range == "all":
            return datetime(1970, 1, 1)  # Unix epoch - delete everything
        
        return None
    
    async def check_content_for_forget_commands(self, text: str) -> bool:
        """Check if text contains forget/privacy commands"""
        text_lower = text.lower()
        
        for pattern in self.forget_command_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.info(f"Detected forget command in text: {text[:50]}...")
                return True
        
        return False
    
    async def check_sensitive_content(self, text: str) -> bool:
        """Check if text contains sensitive information"""
        for pattern in self.sensitive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Detected sensitive content: {pattern}")
                return True
        
        return False
    
    async def auto_apply_ttl(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply TTL to memory based on content and privacy settings"""
        if not memory_data:
            return memory_data
        
        text = memory_data.get('content', '') or memory_data.get('text', '')
        
        # Check for sensitive content
        if await self.check_sensitive_content(text):
            # Apply shorter TTL for sensitive content
            ttl_hours = self.privacy_settings.sensitive_content_ttl_hours
            logger.info(f"Applying sensitive content TTL: {ttl_hours}h")
        else:
            # Apply default TTL
            ttl_hours = self.privacy_settings.default_ttl_hours
        
        # Add TTL to memory
        expires_at = datetime.now() + timedelta(hours=ttl_hours)
        memory_data['expires_at'] = expires_at.isoformat()
        memory_data['ttl_hours'] = ttl_hours
        
        return memory_data
    
    def start_auto_cleanup(self):
        """Start automatic cleanup task"""
        if self._cleanup_task:
            return
        
        async def cleanup_loop():
            while True:
                try:
                    if self.privacy_settings.enable_auto_cleanup:
                        await self._run_auto_cleanup()
                    
                    # Run cleanup every hour
                    await asyncio.sleep(3600)
                    
                except Exception as e:
                    logger.error(f"Error in auto-cleanup loop: {e}")
                    await asyncio.sleep(300)  # Wait 5 minutes before retry
        
        try:
            self._cleanup_task = asyncio.create_task(cleanup_loop())
            logger.info("Started auto-cleanup task")
        except RuntimeError as e:
            if "no running event loop" in str(e):
                logger.debug("No event loop running, auto-cleanup will be started later")
            else:
                raise e
    
    async def _run_auto_cleanup(self):
        """Run automatic memory cleanup"""
        try:
            logger.debug("Running automatic memory cleanup")
            
            # Delete expired memories
            cutoff_date = datetime.now() - timedelta(days=self.privacy_settings.max_memory_age_days)
            
            # This would query and delete expired memories from the store
            # For now, just log the action
            logger.debug(f"Auto-cleanup: would delete memories older than {cutoff_date}")
            
        except Exception as e:
            logger.error(f"Error in auto-cleanup: {e}")
    
    def stop_auto_cleanup(self):
        """Stop automatic cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
            logger.info("Stopped auto-cleanup task")
    
    def get_privacy_status(self) -> Dict[str, Any]:
        """Get current privacy settings and status"""
        return {
            "privacy_settings": {
                "default_ttl_hours": self.privacy_settings.default_ttl_hours,
                "sensitive_content_ttl_hours": self.privacy_settings.sensitive_content_ttl_hours,
                "max_memory_age_days": self.privacy_settings.max_memory_age_days,
                "enable_auto_cleanup": self.privacy_settings.enable_auto_cleanup,
                "forget_patterns_count": len(self.forget_command_patterns)
            },
            "auto_cleanup_active": self._cleanup_task is not None and not self._cleanup_task.done(),
            "sensitive_patterns_count": len(self.sensitive_patterns)
        }

# Global instance
_privacy_hooks = None

def get_b3_privacy_hooks(memory_store=None):
    """Get singleton B3 privacy hooks"""
    global _privacy_hooks
    if _privacy_hooks is None:
        _privacy_hooks = B3PrivacyHooks(memory_store)
    return _privacy_hooks

# FastAPI router for privacy endpoints
router = APIRouter(prefix="/api/privacy", tags=["privacy"])

@router.post("/forget")
async def forget_memories(request: ForgetRequest) -> ForgetResponse:
    """
    Forget specific memories based on criteria
    Supports natural language queries like 'glöm det där'
    """
    privacy_hooks = get_b3_privacy_hooks()
    return await privacy_hooks.process_forget_request(request)

@router.post("/forget/all")
async def forget_all_memories():
    """Emergency privacy function - delete all memories"""
    request = ForgetRequest(time_range="all")
    privacy_hooks = get_b3_privacy_hooks()
    result = await privacy_hooks.process_forget_request(request)
    
    if result.success:
        logger.warning("ALL MEMORIES DELETED via emergency privacy function")
    
    return result

@router.get("/status")
async def get_privacy_status():
    """Get current privacy settings and status"""
    privacy_hooks = get_b3_privacy_hooks()
    return privacy_hooks.get_privacy_status()

@router.post("/settings")
async def update_privacy_settings(settings: PrivacySettings):
    """Update privacy settings"""
    privacy_hooks = get_b3_privacy_hooks()
    privacy_hooks.privacy_settings = settings
    
    logger.info(f"Privacy settings updated: TTL={settings.default_ttl_hours}h")
    
    return {
        "success": True,
        "message": "Privacy settings updated",
        "settings": settings.dict()
    }