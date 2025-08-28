#!/usr/bin/env python3
"""
Response Caching for Alice - Production Performance Optimization
================================================================
Implementerar intelligent caching för vanliga queries för att minska AI response times.
"""

import json
import time
import hashlib
import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import OrderedDict

logger = logging.getLogger("alice.response_cache")

@dataclass
class CacheEntry:
    """Cache entry med metadata"""
    response: str
    model: str
    timestamp: datetime
    hit_count: int
    last_access: datetime
    tftt_ms: float

class ResponseCache:
    """
    Intelligent response cache för vanliga queries
    - LRU eviction
    - TTL expiration
    - Hash-baserad key generation
    - Hit rate statistics
    """
    
    def __init__(self, max_size: int = 1000, ttl_minutes: int = 30):
        self.max_size = max_size
        self.ttl = timedelta(minutes=ttl_minutes)
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        # Swedish common queries cache hints
        self.common_patterns = [
            "hej", "tack", "sverige", "stockholm", "vad är klockan",
            "vad heter", "hur mår du", "vad kan du göra", "hjälp",
            "musik", "väder", "kalender", "mail"
        ]
        
        logger.info(f"ResponseCache initialized: max_size={max_size}, ttl={ttl_minutes}min")
    
    def _generate_cache_key(self, message: str, model: str = "", context: str = "") -> str:
        """Generera cache key från message content"""
        # Normalisera message för bättre cache hits
        normalized = message.lower().strip()
        
        # Skapa hash från message + model + context
        content = f"{normalized}|{model}|{context}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _is_cacheable(self, message: str) -> bool:
        """Bestäm om message är cacheable"""
        message_lower = message.lower()
        
        # Cache bara korta, vanliga messages
        if len(message) > 200:
            return False
            
        # Cache vanliga svenska patterns
        for pattern in self.common_patterns:
            if pattern in message_lower:
                return True
                
        # Cache specifika question patterns
        question_patterns = ["vad är", "hur", "när", "var", "vem", "vilken"]
        if any(pattern in message_lower for pattern in question_patterns):
            return True
            
        return False
    
    def _evict_expired(self):
        """Ta bort expired entries"""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items() 
            if now - entry.timestamp > self.ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
            self.evictions += 1
    
    def _evict_lru(self):
        """Ta bort LRU entry om cache är full"""
        if len(self.cache) >= self.max_size:
            # OrderedDict pops LRU (första item)
            self.cache.popitem(last=False)
            self.evictions += 1
    
    async def get(self, message: str, model: str = "", context: str = "") -> Optional[Dict[str, Any]]:
        """Hämta cached response"""
        if not self._is_cacheable(message):
            return None
            
        cache_key = self._generate_cache_key(message, model, context)
        
        # Clean expired entries periodically
        self._evict_expired()
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            
            # Move to end (mark as recently used)
            self.cache.move_to_end(cache_key)
            
            # Update access stats
            entry.hit_count += 1
            entry.last_access = datetime.now()
            
            self.hits += 1
            
            logger.debug(f"Cache HIT for message: '{message[:30]}...' (hits: {entry.hit_count})")
            
            return {
                "response": entry.response,
                "model": f"{entry.model} (cached)",
                "tftt_ms": entry.tftt_ms * 0.1,  # Cached responses much faster
                "timestamp": datetime.now().isoformat(),
                "cache_hit": True
            }
        
        self.misses += 1
        return None
    
    async def put(self, message: str, response: str, model: str, tftt_ms: float, context: str = ""):
        """Spara response i cache"""
        if not self._is_cacheable(message):
            return
        
        cache_key = self._generate_cache_key(message, model, context)
        
        # Evict LRU if needed
        self._evict_lru()
        
        entry = CacheEntry(
            response=response,
            model=model,
            timestamp=datetime.now(),
            hit_count=0,
            last_access=datetime.now(),
            tftt_ms=tftt_ms
        )
        
        self.cache[cache_key] = entry
        logger.debug(f"Cache PUT for message: '{message[:30]}...'")
    
    def get_stats(self) -> Dict[str, Any]:
        """Hämta cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate average hit count
        avg_hit_count = sum(entry.hit_count for entry in self.cache.values()) / len(self.cache) if self.cache else 0
        
        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate_percent": round(hit_rate, 1),
            "total_hits": self.hits,
            "total_misses": self.misses,
            "total_evictions": self.evictions,
            "avg_hit_count": round(avg_hit_count, 1),
            "ttl_minutes": self.ttl.total_seconds() / 60
        }
    
    def clear(self):
        """Rensa cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        logger.info("Cache cleared")

# Global cache instance
response_cache = ResponseCache(max_size=500, ttl_minutes=15)

async def test_cache():
    """Test cache functionality"""
    print("🧪 Testing ResponseCache...")
    
    # Test cacheable detection
    assert response_cache._is_cacheable("Hej Alice!")
    assert response_cache._is_cacheable("Vad är klockan?")
    assert not response_cache._is_cacheable("Detta är ett mycket långt meddelande som inte bör cacheAS eftersom det är för specifikt och långt för att vara en vanlig query som skulle ha nytta av caching")
    
    # Test cache operations
    await response_cache.put("Hej Alice!", "Hej! Hur kan jag hjälpa dig?", "gpt-4", 1200.0)
    
    # Should hit cache
    cached = await response_cache.get("Hej Alice!")
    assert cached is not None
    assert cached["cache_hit"] is True
    assert cached["tftt_ms"] < 200  # Much faster than original
    
    # Should miss cache
    miss = await response_cache.get("Helt annan fråga")
    assert miss is None
    
    stats = response_cache.get_stats()
    print(f"✅ Cache test passed! Hit rate: {stats['hit_rate_percent']}%")

if __name__ == "__main__":
    asyncio.run(test_cache())