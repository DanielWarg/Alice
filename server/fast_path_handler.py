"""
Fast Path Handler - Phase 2 Implementation
Routes simple queries to OpenAI Realtime API for <300ms responses

Features:
- Route greetings, weather, time queries to OpenAI Realtime
- Response caching for common Swedish phrases
- Streaming TTS responses from OpenAI
- Latency monitoring and optimization
- Fallback to Think Path on failures
- Privacy boundaries (only simple intents)
"""

import asyncio
import time
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import os
from datetime import datetime

from openai_realtime_client import OpenAIRealtimeClient, RealtimeConfig, create_realtime_client
from memory import MemoryStore

logger = logging.getLogger("alice.fast_path")

class FastPathDecision(Enum):
    APPROVED = "approved"       # Route to fast path
    REJECTED = "rejected"       # Route to think path
    ESCALATE = "escalate"       # Start fast, escalate if needed

@dataclass
class FastPathRequest:
    """Request for fast path processing"""
    session_id: str
    text: str
    intent: str
    confidence: float
    audio_data: Optional[bytes] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class FastPathResponse:
    """Response from fast path processing"""
    success: bool
    response_text: str = ""
    response_audio: Optional[bytes] = None
    latency_ms: float = 0.0
    tokens_used: int = 0
    cached: bool = False
    fallback_reason: Optional[str] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class ResponseCache:
    """Cache for fast path responses to reduce latency and costs"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.access_times = {}
        
    def _generate_key(self, text: str, intent: str) -> str:
        """Generate cache key from text and intent"""
        return f"{intent}:{hash(text.lower().strip())}"
    
    def get(self, text: str, intent: str) -> Optional[FastPathResponse]:
        """Get cached response if available and not expired"""
        key = self._generate_key(text, intent)
        
        if key not in self.cache:
            return None
            
        cached_response, cached_time = self.cache[key]
        
        # Check if expired
        if time.time() - cached_time > self.ttl_seconds:
            del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
            return None
        
        # Update access time for LRU
        self.access_times[key] = time.time()
        
        # Return cached response
        response = FastPathResponse(**cached_response)
        response.cached = True
        return response
    
    def set(self, text: str, intent: str, response: FastPathResponse):
        """Cache response"""
        if response.success:  # Only cache successful responses
            key = self._generate_key(text, intent)
            
            # Remove oldest entry if cache is full
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.access_times.keys(), key=self.access_times.get)
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            # Cache the response (excluding audio to save memory)
            cached_data = {
                "success": response.success,
                "response_text": response.response_text,
                "tokens_used": response.tokens_used,
                "latency_ms": response.latency_ms
            }
            
            self.cache[key] = (cached_data, time.time())
            self.access_times[key] = time.time()
            
            logger.debug(f"Cached fast path response for intent: {intent}")
    
    def clear(self):
        """Clear all cached responses"""
        self.cache.clear()
        self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": getattr(self, "_hit_count", 0) / max(getattr(self, "_total_requests", 1), 1),
            "ttl_seconds": self.ttl_seconds
        }

class FastPathHandler:
    """
    Fast Path Handler for blixtsnabb voice responses via OpenAI Realtime API
    
    Routes simple queries (greetings, weather, time) to OpenAI for <300ms responses
    while maintaining privacy boundaries and cost monitoring.
    """
    
    def __init__(self, memory_store: MemoryStore):
        self.memory = memory_store
        self.realtime_client: Optional[OpenAIRealtimeClient] = None
        self.response_cache = ResponseCache()
        
        # Fast path configuration
        self.config = {
            "target_latency_ms": int(os.getenv("FAST_PATH_TIMEOUT_MS", "300")),
            "max_tokens": int(os.getenv("FAST_PATH_MAX_TOKENS", "150")),
            "temperature": float(os.getenv("FAST_PATH_TEMPERATURE", "0.6")),
            "cache_enabled": os.getenv("FAST_PATH_CACHE_ENABLED", "true").lower() == "true",
            "fallback_enabled": os.getenv("FAST_PATH_FALLBACK_ENABLED", "true").lower() == "true"
        }
        
        # Approved intents for fast path (privacy-safe)
        self.approved_intents = {
            "GREETING": {"confidence_threshold": 0.7, "priority": "high"},
            "ACKNOWLEDGMENT": {"confidence_threshold": 0.8, "priority": "high"},
            "SIMPLE_QUESTION": {"confidence_threshold": 0.75, "priority": "medium"},
            "WEATHER": {"confidence_threshold": 0.8, "priority": "medium"},
            "TIME_DATE": {"confidence_threshold": 0.85, "priority": "high"},
            "SMALL_TALK": {"confidence_threshold": 0.7, "priority": "low"},
            "GOODBYE": {"confidence_threshold": 0.75, "priority": "high"}
        }
        
        # Swedish phrase patterns for quick responses
        self.swedish_patterns = {
            "greetings": ["hej", "hejsan", "hallå", "godmorgon", "god kväll", "god dag"],
            "thanks": ["tack", "tackar", "tack så mycket", "tusen tack"],
            "yes_no": ["ja", "nej", "kanske", "absolut", "verkligen"],
            "weather": ["väder", "regn", "sol", "snö", "temperatur", "grader"],
            "time": ["tid", "klocka", "datum", "idag", "imorgon", "igår"]
        }
        
        # Performance monitoring
        self.metrics = {
            "requests": 0,
            "successes": 0,
            "cache_hits": 0,
            "fallbacks": 0,
            "total_latency_ms": 0.0,
            "openai_costs_usd": 0.0
        }
        
        # Event handlers
        self.on_response_ready: Optional[Callable] = None
        self.on_audio_chunk: Optional[Callable] = None
        self.on_fallback_required: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
    
    async def initialize(self) -> bool:
        """Initialize OpenAI Realtime client"""
        try:
            # Create realtime client with Swedish configuration
            self.realtime_client = create_realtime_client(
                voice="nova",  # Best for Swedish
                language="sv",
                instructions="""Du är Alice, en svensk AI-assistent. 
                               Svara kort och naturligt på svenska. 
                               Du hanterar endast enkla frågor som hälsningar, väder, tid och småprat.
                               Håll svaren under 2 meningar."""
            )
            
            # Set up event handlers
            self._setup_realtime_handlers()
            
            # Connect to OpenAI
            connected = await self.realtime_client.connect()
            
            if connected:
                logger.info("Fast Path Handler initialized with OpenAI Realtime API")
                return True
            else:
                logger.error("Failed to connect to OpenAI Realtime API")
                return False
                
        except Exception as e:
            logger.error(f"Fast Path Handler initialization failed: {e}")
            return False
    
    def _setup_realtime_handlers(self):
        """Setup event handlers for OpenAI Realtime client"""
        if not self.realtime_client:
            return
        
        # Handle streaming audio responses
        self.realtime_client.on_response_audio_delta = self._handle_audio_delta
        self.realtime_client.on_response_audio_done = self._handle_audio_done
        
        # Handle text transcriptions
        self.realtime_client.on_response_audio_transcript_delta = self._handle_transcript_delta
        self.realtime_client.on_response_audio_transcript_done = self._handle_transcript_done
        
        # Handle response completion
        self.realtime_client.on_response_done = self._handle_response_done
        
        # Handle errors
        self.realtime_client.on_error = self._handle_realtime_error
    
    async def _handle_audio_delta(self, audio_delta: str):
        """Handle streaming audio chunks from OpenAI"""
        if self.on_audio_chunk:
            import base64
            audio_bytes = base64.b64decode(audio_delta)
            await self.on_audio_chunk(audio_bytes)
    
    async def _handle_audio_done(self):
        """Handle audio response completion"""
        logger.debug("OpenAI audio response completed")
    
    async def _handle_transcript_delta(self, delta: str):
        """Handle streaming transcript from OpenAI"""
        logger.debug(f"Transcript delta: {delta}")
    
    async def _handle_transcript_done(self, transcript: str):
        """Handle complete transcript from OpenAI"""
        logger.debug(f"Complete transcript: {transcript}")
        
        if self.on_response_ready:
            await self.on_response_ready(transcript)
    
    async def _handle_response_done(self, response_data: Dict[str, Any]):
        """Handle response completion with usage data"""
        usage = response_data.get("usage", {})
        if usage:
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            
            # Estimate cost (adjust based on actual OpenAI pricing)
            cost = (input_tokens * 0.000002) + (output_tokens * 0.000006)
            self.metrics["openai_costs_usd"] += cost
            
            logger.debug(f"OpenAI usage - Input: {input_tokens}, Output: {output_tokens}, Cost: ${cost:.6f}")
    
    async def _handle_realtime_error(self, error: str):
        """Handle OpenAI Realtime API errors"""
        logger.error(f"OpenAI Realtime error: {error}")
        if self.on_error:
            await self.on_error(f"Fast path error: {error}")
    
    def should_use_fast_path(self, text: str, intent: str, confidence: float) -> FastPathDecision:
        """
        Determine if request should use fast path
        
        Args:
            text: User input text
            intent: Classified intent
            confidence: Intent confidence score
            
        Returns:
            FastPathDecision indicating routing decision
        """
        # Check if intent is approved for fast path
        if intent not in self.approved_intents:
            logger.debug(f"Intent {intent} not approved for fast path")
            return FastPathDecision.REJECTED
        
        intent_config = self.approved_intents[intent]
        
        # Check confidence threshold
        if confidence < intent_config["confidence_threshold"]:
            logger.debug(f"Confidence {confidence} below threshold for {intent}")
            return FastPathDecision.REJECTED
        
        # Check for privacy-sensitive content
        if self._contains_sensitive_info(text):
            logger.debug("Text contains sensitive information, routing to think path")
            return FastPathDecision.REJECTED
        
        # Check text length (fast path for short queries only)
        if len(text.split()) > 15:  # More than 15 words
            logger.debug("Text too long for fast path")
            return FastPathDecision.REJECTED
        
        # Check for Swedish patterns that work well with fast path
        if self._matches_swedish_patterns(text):
            return FastPathDecision.APPROVED
        
        # High confidence simple questions can be approved
        if intent in ["GREETING", "ACKNOWLEDGMENT", "TIME_DATE", "GOODBYE"] and confidence > 0.85:
            return FastPathDecision.APPROVED
        
        # For medium confidence or complex simple questions, escalate
        if intent in ["WEATHER", "SIMPLE_QUESTION"] and confidence > 0.75:
            return FastPathDecision.ESCALATE
        
        return FastPathDecision.REJECTED
    
    def _contains_sensitive_info(self, text: str) -> bool:
        """Check if text contains privacy-sensitive information"""
        sensitive_keywords = [
            "password", "lösenord", "pin", "kod", "säkerhet",
            "email", "mejl", "adress", "telefon", "nummer",
            "konto", "bank", "kort", "betalning", "personnummer",
            "hemlig", "privat", "konfidentiell", "dokument"
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in sensitive_keywords)
    
    def _matches_swedish_patterns(self, text: str) -> bool:
        """Check if text matches common Swedish patterns suitable for fast path"""
        text_lower = text.lower()
        
        for pattern_type, patterns in self.swedish_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return True
        
        return False
    
    async def process_request(self, request: FastPathRequest) -> FastPathResponse:
        """
        Process request through fast path
        
        Args:
            request: FastPathRequest with text and metadata
            
        Returns:
            FastPathResponse with result
        """
        start_time = time.time()
        self.metrics["requests"] += 1
        
        try:
            # Check cache first
            if self.config["cache_enabled"]:
                cached_response = self.response_cache.get(request.text, request.intent)
                if cached_response:
                    self.metrics["cache_hits"] += 1
                    logger.debug(f"Fast path cache hit for: {request.text[:50]}")
                    return cached_response
            
            # Ensure realtime client is connected
            if not self.realtime_client or not self.realtime_client.is_connected():
                if not await self.initialize():
                    return self._create_fallback_response("OpenAI connection failed")
            
            # Send text to OpenAI Realtime
            await self.realtime_client.send_text_message(request.text)
            
            # Wait for response with timeout
            response_text = ""
            response_audio = b""
            
            # Set up response collection
            collected_text = []
            collected_audio = []
            
            def collect_text(text):
                collected_text.append(text)
            
            def collect_audio(audio_chunk):
                collected_audio.append(audio_chunk)
            
            # Temporarily set handlers
            original_text_handler = self.on_response_ready
            original_audio_handler = self.on_audio_chunk
            
            self.on_response_ready = collect_text
            self.on_audio_chunk = collect_audio
            
            try:
                # Wait for response with timeout
                await asyncio.wait_for(
                    self._wait_for_response_completion(),
                    timeout=self.config["target_latency_ms"] / 1000.0
                )
                
                response_text = " ".join(collected_text)
                response_audio = b"".join(collected_audio)
                
            finally:
                # Restore original handlers
                self.on_response_ready = original_text_handler
                self.on_audio_chunk = original_audio_handler
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Create successful response
            response = FastPathResponse(
                success=True,
                response_text=response_text,
                response_audio=response_audio if response_audio else None,
                latency_ms=latency_ms,
                tokens_used=len(response_text.split())  # Rough estimate
            )
            
            # Cache successful response
            if self.config["cache_enabled"]:
                self.response_cache.set(request.text, request.intent, response)
            
            # Update metrics
            self.metrics["successes"] += 1
            self.metrics["total_latency_ms"] += latency_ms
            
            logger.info(f"Fast path success: {latency_ms:.1f}ms for '{request.text[:50]}'")
            
            return response
            
        except asyncio.TimeoutError:
            logger.warning(f"Fast path timeout for: {request.text[:50]}")
            return self._create_fallback_response("Response timeout")
            
        except Exception as e:
            logger.error(f"Fast path processing error: {e}")
            return self._create_fallback_response(f"Processing error: {e}")
    
    async def _wait_for_response_completion(self):
        """Wait for OpenAI response to complete"""
        # This is a simplified implementation
        # In practice, you'd wait for the specific response completion event
        await asyncio.sleep(0.1)  # Give time for response to start
        
        # Wait for response to complete (implementation depends on OpenAI Realtime protocol)
        # For now, we'll use a simple delay
        await asyncio.sleep(0.2)
    
    def _create_fallback_response(self, reason: str) -> FastPathResponse:
        """Create fallback response when fast path fails"""
        self.metrics["fallbacks"] += 1
        
        return FastPathResponse(
            success=False,
            fallback_reason=reason,
            latency_ms=self.config["target_latency_ms"]  # Use target as fallback latency
        )
    
    async def handle_barge_in(self, session_id: str):
        """Handle user interruption (barge-in)"""
        if self.realtime_client and self.realtime_client.is_connected():
            try:
                await self.realtime_client.cancel_response()
                logger.debug(f"Cancelled OpenAI response for session {session_id}")
            except Exception as e:
                logger.error(f"Error cancelling OpenAI response: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get fast path performance metrics"""
        total_requests = max(self.metrics["requests"], 1)
        
        return {
            "total_requests": self.metrics["requests"],
            "success_rate": self.metrics["successes"] / total_requests,
            "cache_hit_rate": self.metrics["cache_hits"] / total_requests,
            "fallback_rate": self.metrics["fallbacks"] / total_requests,
            "average_latency_ms": self.metrics["total_latency_ms"] / max(self.metrics["successes"], 1),
            "total_cost_usd": self.metrics["openai_costs_usd"],
            "cache_stats": self.response_cache.get_stats(),
            "approved_intents": list(self.approved_intents.keys())
        }
    
    def reset_metrics(self):
        """Reset performance metrics"""
        self.metrics = {
            "requests": 0,
            "successes": 0,
            "cache_hits": 0,
            "fallbacks": 0,
            "total_latency_ms": 0.0,
            "openai_costs_usd": 0.0
        }
    
    async def shutdown(self):
        """Shutdown fast path handler"""
        if self.realtime_client:
            await self.realtime_client.disconnect()
            
        self.response_cache.clear()
        logger.info("Fast Path Handler shutdown completed")

# Global fast path handler instance
fast_path_handler = None

def get_fast_path_handler(memory_store: MemoryStore) -> FastPathHandler:
    """Get or create fast path handler instance"""
    global fast_path_handler
    if fast_path_handler is None:
        fast_path_handler = FastPathHandler(memory_store)
    return fast_path_handler