#!/usr/bin/env python3
"""
🔀 LLM Router - Hybrid Talk-lane vs Tool-lane Routing
Intelligent routing between OpenAI Realtime (fast talk) and local gpt-oss (private tools)
"""
import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

class RouteType(Enum):
    """Route types for hybrid processing"""
    REALTIME = "realtime"  # OpenAI Realtime for fast talk
    LOCAL = "local"        # Local gpt-oss for private/complex
    
class IntentTag(Enum):
    """Intent classification tags"""
    # Simple talk-lane intents (safe for Realtime)
    SMALL_TALK = "SMALL_TALK"
    WEATHER_GENERAL = "WEATHER_GENERAL" 
    TIME_QUERY = "TIME_QUERY"
    GENERAL_QUESTION = "GENERAL_QUESTION"
    
    # Private tool-lane intents (local only)
    EMAIL_LOOKUP = "EMAIL_LOOKUP"
    CALENDAR_QUERY = "CALENDAR_QUERY"
    FILE_ACCESS = "FILE_ACCESS"
    DOCUMENT_READ = "DOCUMENT_READ"
    CONTACT_SEARCH = "CONTACT_SEARCH"
    
    # Complex reasoning (local only)
    TOOL_PLANNING = "TOOL_PLANNING"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    PRIVATE_RAG = "PRIVATE_RAG"

@dataclass
class RouteDecision:
    """Routing decision with metadata"""
    route: RouteType
    intent: IntentTag
    confidence: float
    latency_budget_ms: int
    privacy_level: str  # "public", "private", "sensitive"
    reasoning: str
    no_cloud: bool = False  # Flag to prevent cloud routing

class LLMRouter:
    """Smart router for hybrid talk/tool lane processing"""
    
    def __init__(self):
        # Private keywords that force local routing
        self.private_keywords = {
            "email", "emails", "inbox", "mejl", "epost",
            "calendar", "meeting", "appointment", "kalender", "möte",
            "file", "document", "folder", "dokument", "fil",
            "contact", "person", "kontakt", "phone", "telefon",
            "password", "secret", "private", "privat", "lösenord",
            "bank", "credit", "payment", "bank", "kredit", "betalning"
        }
        
        # Simple talk patterns (safe for Realtime)
        self.simple_patterns = [
            r"what time is it",
            r"how are you",
            r"hello|hi|hej",
            r"thanks|thank you|tack",
            r"weather.*general|general.*weather",
            r"tell me about|berätta om.*[^@\.]",  # General topics, not files
            r"what is|vad är.*[^@\.]",
            r"explain|förklara.*[^@\.]"
        ]
        
        # Complex/private patterns (force local)
        self.private_patterns = [
            r"email.*from|emails.*from|mejl.*från",
            r"calendar.*today|meeting.*today|möte.*idag", 
            r"file.*contain|document.*about|fil.*innehåll",
            r"contact.*named|person.*called|kontakt.*som",
            r"password|secret|private|lösenord|privat",
            r"bank|credit|payment|bank|kredit",
            r"@.*\.|\.com|\.se",  # Email addresses or domains
            r"\b(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}\b",  # Phone numbers
            r"call.*me.*at|ring.*mig.*på|telefon.*nummer"  # Phone contexts
        ]
        
        self.metrics = {
            "total_routes": 0,
            "realtime_routes": 0,
            "local_routes": 0,
            "privacy_blocks": 0
        }
    
    def route_request(self, user_input: str, context_flags: Dict = None, 
                     latency_budget_ms: int = 500) -> RouteDecision:
        """
        Route user request to appropriate processing lane
        
        Args:
            user_input: User's transcribed text
            context_flags: Additional context like session state
            latency_budget_ms: Target latency budget
            
        Returns:
            RouteDecision with routing information
        """
        start_time = time.time()
        context_flags = context_flags or {}
        
        # Normalize input for analysis
        input_lower = user_input.lower().strip()
        
        logger.info(f"🔀 Routing request: '{user_input[:50]}...'")
        
        # Step 1: Privacy screening - force local if private content detected
        privacy_level, has_private = self._assess_privacy(input_lower)
        
        if has_private:
            decision = RouteDecision(
                route=RouteType.LOCAL,
                intent=self._classify_private_intent(input_lower),
                confidence=0.95,
                latency_budget_ms=latency_budget_ms * 2,  # More time for private processing
                privacy_level=privacy_level,
                reasoning="Private content detected - forced local routing",
                no_cloud=True
            )
            self.metrics["privacy_blocks"] += 1
            logger.info(f"🔒 Privacy block: {decision.intent.value}")
            return decision
        
        # Step 2: Pattern-based intent classification
        intent = self._classify_intent(input_lower)
        
        # Step 3: Route based on intent and latency budget
        if intent in [IntentTag.SMALL_TALK, IntentTag.TIME_QUERY, 
                     IntentTag.WEATHER_GENERAL, IntentTag.GENERAL_QUESTION]:
            
            # Simple queries can use fast Realtime path
            route = RouteType.REALTIME
            confidence = 0.85
            reasoning = f"Simple {intent.value} - using fast Realtime"
            
        elif intent in [IntentTag.EMAIL_LOOKUP, IntentTag.CALENDAR_QUERY,
                       IntentTag.FILE_ACCESS, IntentTag.DOCUMENT_READ]:
            
            # Tool operations require local processing
            route = RouteType.LOCAL
            confidence = 0.90
            reasoning = f"Tool operation {intent.value} - using local processing"
            
        else:
            # Default to local for complex/unknown
            route = RouteType.LOCAL
            confidence = 0.75
            reasoning = f"Complex/unknown intent - defaulting to local"
        
        # Step 4: Latency budget adjustment
        if latency_budget_ms < 300 and route == RouteType.LOCAL:
            # Very tight budget - try Realtime if not explicitly private
            if privacy_level == "public":
                route = RouteType.REALTIME
                reasoning += " (latency override)"
                
        decision = RouteDecision(
            route=route,
            intent=intent,
            confidence=confidence,
            latency_budget_ms=latency_budget_ms,
            privacy_level=privacy_level,
            reasoning=reasoning,
            no_cloud=(route == RouteType.LOCAL and privacy_level != "public")
        )
        
        # Update metrics
        self.metrics["total_routes"] += 1
        if route == RouteType.REALTIME:
            self.metrics["realtime_routes"] += 1
        else:
            self.metrics["local_routes"] += 1
            
        processing_ms = (time.time() - start_time) * 1000
        logger.info(f"✅ Route decision: {route.value} ({intent.value}) in {processing_ms:.0f}ms")
        
        return decision
    
    def _assess_privacy(self, input_lower: str) -> tuple[str, bool]:
        """Assess privacy level of input"""
        
        # Check for private keywords
        for keyword in self.private_keywords:
            if keyword in input_lower:
                return "private", True
                
        # Check for private patterns
        for pattern in self.private_patterns:
            if re.search(pattern, input_lower):
                return "sensitive", True
                
        # Check for email addresses, file paths, etc
        if ("@" in input_lower and "." in input_lower) or \
           ("/" in input_lower and ("." in input_lower)):
            return "sensitive", True
            
        return "public", False
    
    def _classify_intent(self, input_lower: str) -> IntentTag:
        """Classify intent from user input"""
        
        # Simple patterns first
        for pattern in self.simple_patterns:
            if re.search(pattern, input_lower):
                if "time" in pattern:
                    return IntentTag.TIME_QUERY
                elif "weather" in pattern:
                    return IntentTag.WEATHER_GENERAL  
                elif any(greeting in pattern for greeting in ["hello", "hi", "hej"]):
                    return IntentTag.SMALL_TALK
                else:
                    return IntentTag.GENERAL_QUESTION
                    
        # Private patterns
        for pattern in self.private_patterns:
            if re.search(pattern, input_lower):
                if "email" in pattern or "mejl" in pattern:
                    return IntentTag.EMAIL_LOOKUP
                elif "calendar" in pattern or "meeting" in pattern:
                    return IntentTag.CALENDAR_QUERY
                elif "file" in pattern or "document" in pattern:
                    return IntentTag.FILE_ACCESS
                elif "contact" in pattern or "person" in pattern:
                    return IntentTag.CONTACT_SEARCH
                    
        # Default classification based on keywords
        if any(word in input_lower for word in ["email", "mejl", "inbox"]):
            return IntentTag.EMAIL_LOOKUP
        elif any(word in input_lower for word in ["calendar", "meeting", "möte"]):
            return IntentTag.CALENDAR_QUERY
        elif any(word in input_lower for word in ["file", "document", "fil"]):
            return IntentTag.FILE_ACCESS
        elif any(word in input_lower for word in ["analyze", "plan", "tool"]):
            return IntentTag.TOOL_PLANNING
        else:
            return IntentTag.SMALL_TALK
    
    def _classify_private_intent(self, input_lower: str) -> IntentTag:
        """Classify intent for private content (forced local)"""
        
        if any(word in input_lower for word in ["email", "mejl", "inbox"]):
            return IntentTag.EMAIL_LOOKUP
        elif any(word in input_lower for word in ["calendar", "meeting", "möte"]):
            return IntentTag.CALENDAR_QUERY
        elif any(word in input_lower for word in ["file", "document", "fil"]):
            return IntentTag.DOCUMENT_READ
        elif any(word in input_lower for word in ["contact", "person", "kontakt"]):
            return IntentTag.CONTACT_SEARCH
        else:
            return IntentTag.PRIVATE_RAG
    
    def get_metrics(self) -> Dict:
        """Get routing metrics"""
        total = self.metrics["total_routes"]
        if total == 0:
            return self.metrics
            
        return {
            **self.metrics,
            "realtime_percentage": (self.metrics["realtime_routes"] / total) * 100,
            "local_percentage": (self.metrics["local_routes"] / total) * 100,
            "privacy_block_rate": (self.metrics["privacy_blocks"] / total) * 100
        }

# Global router instance
_router_instance = None

def get_llm_router() -> LLMRouter:
    """Get global LLM router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
        logger.info("✅ LLM router initialized")
    return _router_instance