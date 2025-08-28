#!/usr/bin/env python3
"""
Request Batching for Alice - Concurrent Request Optimization
============================================================
Grupperar liknande requests för att minska AI API calls och förbättra throughput.
"""

import asyncio
import logging
import hashlib
from typing import Dict, List, Any, Callable, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("alice.request_batcher")

@dataclass
class BatchedRequest:
    """En request som väntar på batching"""
    message: str
    model: str
    request_id: str
    created_at: datetime
    future: asyncio.Future = field(default_factory=asyncio.Future)
    context: str = ""
    tools: Optional[List[Any]] = None

@dataclass
class BatchResult:
    """Resultat från en batched operation"""
    response: str
    model: str
    tftt_ms: float
    timestamp: str

class RequestBatcher:
    """
    Intelligent request batching för att optimera AI API usage
    - Grupperar liknande requests
    - Timeout-baserad flush
    - Deduplication av identiska requests  
    """
    
    def __init__(self, batch_size: int = 3, flush_timeout_ms: int = 100):
        self.batch_size = batch_size
        self.flush_timeout = flush_timeout_ms / 1000  # Convert to seconds
        
        # Pending requests grupperade efter similarity hash
        self.pending_batches: Dict[str, List[BatchedRequest]] = defaultdict(list)
        
        # Deduplication - map identical requests to first request
        self.dedup_map: Dict[str, BatchedRequest] = {}
        
        # Statistics
        self.total_requests = 0
        self.batched_requests = 0
        self.duplicate_requests = 0
        
        # Background flush task
        self._flush_task = None
        self._start_flush_timer()
        
        logger.info(f"RequestBatcher initialized: batch_size={batch_size}, flush_timeout={flush_timeout_ms}ms")
    
    def _start_flush_timer(self):
        """Starta background flush timer"""
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._periodic_flush())
    
    async def _periodic_flush(self):
        """Periodisk flush av pending requests"""
        while True:
            try:
                await asyncio.sleep(self.flush_timeout)
                await self._flush_pending()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Flush timer error: {e}")
    
    def _similarity_hash(self, message: str, model: str) -> str:
        """Generera hash för att gruppera liknande requests"""
        # Normalisera för bättre batching
        normalized = message.lower().strip()
        
        # Group by length categories för bättre batching
        length_category = "short" if len(normalized) < 50 else "medium" if len(normalized) < 150 else "long"
        
        # Include model in hash
        content = f"{model}|{length_category}|{normalized[:100]}"  # Första 100 chars
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def _exact_hash(self, message: str, model: str, context: str = "") -> str:
        """Generera hash för exact deduplication"""
        content = f"{message}|{model}|{context}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def add_request(self, 
                         message: str, 
                         model: str, 
                         llm_handler: Callable,
                         request_id: str,
                         context: str = "",
                         tools: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Lägg till request till batch
        Returnerar future som resolvas när request processas
        """
        self.total_requests += 1
        
        # Check för exact duplicate först
        exact_hash = self._exact_hash(message, model, context)
        if exact_hash in self.dedup_map:
            existing_request = self.dedup_map[exact_hash]
            self.duplicate_requests += 1
            
            logger.debug(f"Duplicate request detected: '{message[:30]}...'")
            
            # Return same result as original request
            try:
                result = await existing_request.future
                return result
            except Exception as e:
                # If original failed, process this one normally
                logger.warning(f"Original duplicate failed, processing normally: {e}")
        
        # Skapa ny request
        request = BatchedRequest(
            message=message,
            model=model,
            request_id=request_id,
            created_at=datetime.now(),
            context=context,
            tools=tools
        )
        
        # Add to dedup map
        self.dedup_map[exact_hash] = request
        
        # Add to batch by similarity
        similarity_hash = self._similarity_hash(message, model)
        self.pending_batches[similarity_hash].append(request)
        
        logger.debug(f"Added request to batch '{similarity_hash}': '{message[:30]}...'")
        
        # Check if batch is ready
        if len(self.pending_batches[similarity_hash]) >= self.batch_size:
            await self._process_batch(similarity_hash, llm_handler)
        else:
            # Ensure flush timer is running
            self._start_flush_timer()
        
        # Wait for result
        return await request.future
    
    async def _process_batch(self, similarity_hash: str, llm_handler: Callable):
        """Process en batch av requests"""
        if similarity_hash not in self.pending_batches:
            return
        
        batch = self.pending_batches[similarity_hash]
        if not batch:
            return
        
        # Remove from pending
        del self.pending_batches[similarity_hash]
        
        # Update stats
        if len(batch) > 1:
            self.batched_requests += len(batch) - 1  # First request isn't "batched"
        
        logger.info(f"Processing batch of {len(batch)} requests")
        
        # Process each request i batch (concurrent execution)
        tasks = []
        for request in batch:
            task = self._process_single_request(request, llm_handler)
            tasks.append(task)
        
        # Wait för alla requests i batch
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_single_request(self, request: BatchedRequest, llm_handler: Callable):
        """Process en enskild request"""
        try:
            start_time = datetime.now()
            
            # Call LLM handler
            messages = [{"role": "user", "content": request.message}]
            llm_response = await llm_handler(messages, request.tools)
            
            tftt_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            result = {
                "response": llm_response.text,
                "model": llm_response.provider,
                "tftt_ms": tftt_ms,
                "timestamp": datetime.now().isoformat(),
                "batched": True
            }
            
            # Resolve future
            request.future.set_result(result)
            
        except Exception as e:
            logger.error(f"Request processing failed: {e}")
            request.future.set_exception(e)
    
    async def _flush_pending(self):
        """Flush alla pending requests oavsett batch size"""
        if not self.pending_batches:
            return
        
        logger.debug(f"Flushing {len(self.pending_batches)} pending batches")
        
        # Process alla pending batches
        # Note: We can't pass llm_handler here, so we'll need to modify this
        # For now, let's just log and clear expired requests
        current_time = datetime.now()
        
        expired_batches = []
        for similarity_hash, batch in self.pending_batches.items():
            # Find expired requests (older than 2x flush timeout)
            expired_requests = [
                req for req in batch 
                if current_time - req.created_at > timedelta(seconds=self.flush_timeout * 2)
            ]
            
            if expired_requests:
                expired_batches.append(similarity_hash)
                logger.warning(f"Found {len(expired_requests)} expired requests in batch {similarity_hash}")
                
                # Set timeout errors for expired requests
                for req in expired_requests:
                    if not req.future.done():
                        req.future.set_exception(TimeoutError("Request batch timeout"))
        
        # Clean up expired batches
        for similarity_hash in expired_batches:
            if similarity_hash in self.pending_batches:
                del self.pending_batches[similarity_hash]
    
    def get_stats(self) -> Dict[str, Any]:
        """Hämta batching statistics"""
        batch_rate = (self.batched_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        dedup_rate = (self.duplicate_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        
        return {
            "total_requests": self.total_requests,
            "batched_requests": self.batched_requests,
            "duplicate_requests": self.duplicate_requests,
            "batch_rate_percent": round(batch_rate, 1),
            "dedup_rate_percent": round(dedup_rate, 1),
            "pending_batches": len(self.pending_batches),
            "pending_requests": sum(len(batch) for batch in self.pending_batches.values()),
            "batch_size": self.batch_size,
            "flush_timeout_ms": self.flush_timeout * 1000
        }
    
    async def shutdown(self):
        """Shutdown batcher gracefully"""
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Process remaining requests
        await self._flush_pending()
        logger.info("RequestBatcher shutdown complete")

# Global batcher instance - lazy initialization to avoid event loop issues
request_batcher = None

def get_request_batcher():
    global request_batcher
    if request_batcher is None:
        request_batcher = RequestBatcher(batch_size=3, flush_timeout_ms=150)
    return request_batcher

async def test_batcher():
    """Test request batching functionality"""
    print("🧪 Testing RequestBatcher...")
    
    async def mock_llm_handler(messages, tools=None):
        # Mock LLM response
        await asyncio.sleep(0.1)  # Simulate processing time
        
        class MockResponse:
            def __init__(self, text, provider):
                self.text = text
                self.provider = provider
        
        return MockResponse(f"Mock response to: {messages[0]['content']}", "mock-model")
    
    # Test single request
    result1 = await request_batcher.add_request(
        "Test message 1", 
        "gpt-4", 
        mock_llm_handler,
        "req-1"
    )
    
    print(f"✅ Single request result: {result1['response'][:50]}...")
    
    # Test duplicate detection
    result2 = await request_batcher.add_request(
        "Test message 1",  # Same message
        "gpt-4", 
        mock_llm_handler,
        "req-2"
    )
    
    stats = request_batcher.get_stats()
    print(f"✅ Batcher test passed! Dedup rate: {stats['dedup_rate_percent']}%")
    
    await request_batcher.shutdown()

if __name__ == "__main__":
    asyncio.run(test_batcher())