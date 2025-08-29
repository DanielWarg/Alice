"""
Voice Priority Queue - Fast-lane processing with semafores and coalescing
"""

import asyncio
import time
import heapq
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any
import logging

logger = logging.getLogger("alice.voice.queue")

@dataclass(order=True)
class QueueItem:
    """Priority queue item for voice processing"""
    priority: int
    timestamp: float = field(compare=False)
    text: str = field(compare=False)
    source_type: str = field(compare=False)
    future: asyncio.Future = field(compare=False)
    normalized_key: str = field(compare=False)

class VoicePriorityQueue:
    """
    Priority queue for voice processing with:
    - Priority ordering (0=highest)
    - Single-flight deduplication 
    - Per-priority semafores
    """
    
    def __init__(self):
        self._heap = []
        self._lock = asyncio.Lock()
        
        # Semafores per priority level
        self._semafores = {
            0: asyncio.Semaphore(1),  # Notifications/chat - single flight
            1: asyncio.Semaphore(1),  # Email TL;DR - single flight  
            2: asyncio.Semaphore(1),  # Email parts - single flight when idle
        }
        
        # Single-flight deduplication
        self._inflight: Dict[str, tuple] = {}  # key -> (timestamp, future)
        self._dedup_ttl = 2.0  # seconds
        
    def _get_priority(self, source_type: str, text_length: int) -> int:
        """Determine priority based on source type and text length"""
        
        if source_type in ("notification", "chat") and text_length <= 130:
            return 0  # Highest priority - short interactive
        elif source_type == "email" and text_length <= 200:
            return 1  # Email TL;DR
        elif source_type == "email":
            return 2  # Email segments
        else:
            return 1  # Default medium priority
            
    def _create_dedup_key(self, text: str, source_type: str) -> str:
        """Create normalized deduplication key"""
        normalized = f"{source_type}:{text.lower().strip()}"
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
    
    async def submit(self, text: str, source_type: str, processor_coro: Callable) -> Any:
        """
        Submit voice processing task with automatic priority and deduplication
        """
        
        text_length = len(text)
        priority = self._get_priority(source_type, text_length)
        dedup_key = self._create_dedup_key(text, source_type)
        
        # Check for existing in-flight request (single-flight)
        now = time.time()
        if dedup_key in self._inflight:
            timestamp, existing_future = self._inflight[dedup_key]
            if now - timestamp < self._dedup_ttl and not existing_future.done():
                logger.debug(f"Coalescing request: {text[:50]}...")
                return await existing_future
        
        # Create new processing task
        future = asyncio.get_event_loop().create_future()
        
        # Add to priority queue
        async with self._lock:
            item = QueueItem(
                priority=priority,
                timestamp=now,
                text=text,
                source_type=source_type, 
                future=future,
                normalized_key=dedup_key
            )
            heapq.heappush(self._heap, item)
        
        # Register in single-flight tracker
        self._inflight[dedup_key] = (now, future)
        
        # Start processing task
        asyncio.create_task(self._process_item(item, processor_coro))
        
        logger.debug(f"Queued priority {priority}: {source_type} - {text[:50]}...")
        
        return await future
    
    async def _process_item(self, item: QueueItem, processor_coro: Callable):
        """Process a single queue item with priority semafore"""
        
        # Acquire semafore for this priority level
        semaphore = self._semafores.get(item.priority, self._semafores[1])
        
        try:
            async with semaphore:
                logger.debug(f"Processing priority {item.priority}: {item.source_type}")
                
                # Execute the actual processing
                result = await processor_coro(item.text, item.source_type)
                
                # Complete the future
                if not item.future.done():
                    item.future.set_result(result)
                    
        except Exception as e:
            logger.error(f"Processing failed for {item.source_type}: {e}")
            if not item.future.done():
                item.future.set_exception(e)
        finally:
            # Clean up single-flight tracker
            if item.normalized_key in self._inflight:
                del self._inflight[item.normalized_key]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        
        async with self._lock:
            queue_length = len(self._heap)
            
            # Count by priority
            priority_counts = {}
            for item in self._heap:
                priority_counts[item.priority] = priority_counts.get(item.priority, 0) + 1
        
        return {
            "total_queued": queue_length,
            "by_priority": priority_counts,
            "inflight_dedup": len(self._inflight),
            "semaphore_availability": {
                p: sem._value for p, sem in self._semafores.items()
            }
        }

# Global priority queue instance
voice_priority_queue = VoicePriorityQueue()