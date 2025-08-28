"""
Alice Intent Router - Hybrid Voice Architecture Phase 1
Intelligent routing between fast responses and deep thinking

Routes Swedish voice commands between OpenAI Realtime (fast) and Local AI (think)
Target latency: <50ms for routing decision
"""

import re
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from core.router import classify

logger = logging.getLogger("alice.intent_router")

class ProcessingPath(Enum):
    FAST = "fast"      # OpenAI Realtime API - simple, quick responses
    THINK = "think"    # Local AI + tools - complex reasoning
    HYBRID = "hybrid"  # Start fast, escalate if needed

class IntentCategory(Enum):
    GREETING = "greeting"
    ACKNOWLEDGMENT = "acknowledgment"
    SIMPLE_QUESTION = "simple_question"
    WEATHER = "weather"
    TIME_DATE = "time_date"
    
    CALENDAR_COMPLEX = "calendar_complex"
    EMAIL_ANALYSIS = "email_analysis"
    TASK_PLANNING = "task_planning"
    SPOTIFY_SEARCH = "spotify_search"
    MULTI_STEP_WORKFLOW = "multi_step_workflow"
    
    GENERAL_CONVERSATION = "general_conversation"
    UNKNOWN = "unknown"

@dataclass
class RouteDecision:
    """Intent routing decision with reasoning"""
    path: ProcessingPath
    reason: str
    confidence: float
    intent_category: IntentCategory
    estimated_latency_ms: float
    slots: Dict[str, Any] = None
    alternatives: List['RouteDecision'] = None

@dataclass
class IntentClassification:
    """Complete intent classification result"""
    intent: str
    category: IntentCategory
    confidence: float
    slots: Dict[str, Any]
    language: str = "sv-SE"
    processing_time_ms: float = 0.0

class SwedishIntentClassifier:
    """Swedish language intent classifier optimized for voice commands"""
    
    def __init__(self):
        # Fast path patterns (simple responses suitable for OpenAI Realtime)
        self.fast_patterns = {
            IntentCategory.GREETING: [
                r'\b(hej|halla|hallå|godmorgon|god morgon|god kväll|godkväll|god natt|godnatt|tjena|tjabba|tja|yo|hallå där)\b',
                r'\b(hi|hello|hey|good morning|good evening|good night)\b',
                r'\b(alice|vad heter du|vem är du)\b'
            ],
            IntentCategory.ACKNOWLEDGMENT: [
                r'\b(okej|ok|bra|jättebra|perfekt|tack|tack så mycket|tackar|thanks|thank you)\b',
                r'\b(yes|ja|nej|no|kanske|maybe|absolut|självklart)\b',
                r'\b(mm|mmm|mhm|aha|jaha|såja|jasså)\b'
            ],
            IntentCategory.SIMPLE_QUESTION: [
                r'\b(vad är|vad betyder|vad heter|vad gör|vad säger|vad tycker|vad tror)\b',
                r'\b(hur är|hur mår|hur går|hur funkar|hur fungerar)\b',
                r'\b(när|var|vem|varför|vilket|vilken|vilka)\b.*\?'
            ],
            IntentCategory.WEATHER: [
                r'\b(väder|vädret|temperatur|regn|regnar|snö|snöar|sol|soligt|molnigt|blåsigt)\b',
                r'\b(weather|temperature|rain|snow|sun|sunny|cloudy|windy)\b',
                r'\b(hur är vädret|vad är det för väder|kommer det regna|blir det sol)\b'
            ],
            IntentCategory.TIME_DATE: [
                r'\b(vad är klockan|vilken tid|hur mycket är klockan|tiden)\b',
                r'\b(what time|time is|what\'s the time)\b',
                r'\b(idag|imorgon|igår|vilken dag|vilket datum|vad är det för dag)\b',
                r'\b(today|tomorrow|yesterday|what day|date)\b'
            ]
        }
        
        # Think path patterns (complex operations requiring local AI)
        self.think_patterns = {
            IntentCategory.CALENDAR_COMPLEX: [
                r'\b(boka|skapa|planera|schemalägg|lägg in).*\b(möte|träff|event|aktivitet|tid)\b',
                r'\b(flytta|ändra|uppdatera|ta bort|avboka).*\b(möte|träff|event)\b',
                r'\b(hitta|sök|leta).*\b(möte|träff|event).*\b(med|tillsammans|nästa|kommande)\b',
                r'\b(schemalägg|planera).*\b(med|tillsammans med|för|åt)\b.*\b(person|people|team)\b',
                r'\b(konflikt|dubbelboka|överlappa|kollidera).*\b(tid|möte|schema)\b'
            ],
            IntentCategory.EMAIL_ANALYSIS: [
                r'\b(analyser|sammanfatta|granska|kolla).*\b(mail|e-post|meddelande|inbox)\b',
                r'\b(prioritera|sortera|filtrera).*\b(mail|e-post|meddelanden)\b',
                r'\b(sök|hitta|leta).*\b(mail|e-post).*\b(från|om|med|innehåll)\b',
                r'\b(skicka|skriv|komponera).*\b(mail|e-post).*\b(till|för|om|angående)\b'
            ],
            IntentCategory.TASK_PLANNING: [
                r'\b(planera|organisera|strukturera|bryt ner).*\b(projekt|uppgift|arbete|plan)\b',
                r'\b(steg|fas|etapp|del).*\b(för att|till|mot|av)\b',
                r'\b(prioritera|rangordna|sortera).*\b(uppgifter|tasks|aktiviteter)\b',
                r'\b(deadline|tidsgräns|leverans|klart till)\b'
            ],
            IntentCategory.SPOTIFY_SEARCH: [
                r'\b(spela|sätt på|starta).*\b(musik|låt|album|playlist|artist)\b',
                r'\b(hitta|sök|leta).*\b(musik|låt|album|artist|band)\b',
                r'\b(lägg till|ta bort|skapa).*\b(playlist|spellista)\b',
                r'\b(som låter som|liknande|i stil med).*\b(artist|band|låt)\b'
            ]
        }
        
        # Swedish command patterns for better recognition
        self.swedish_commands = {
            'calendar_keywords': ['möte', 'träff', 'event', 'boka', 'schemalägg', 'planera', 'kalender'],
            'email_keywords': ['mail', 'e-post', 'meddelande', 'inbox', 'skicka', 'skriv'],
            'music_keywords': ['musik', 'låt', 'spela', 'spotify', 'artist', 'album'],
            'time_keywords': ['tid', 'klockan', 'datum', 'idag', 'imorgon', 'igår'],
            'question_words': ['vad', 'hur', 'när', 'var', 'vem', 'varför', 'vilket', 'vilken'],
            'greeting_words': ['hej', 'halla', 'godmorgon', 'godkväll', 'tjena', 'alice']
        }
        
    def classify_intent_fast(self, text: str) -> IntentClassification:
        """Fast intent classification optimized for <25ms latency"""
        start_time = time.time()
        
        text_lower = text.lower().strip()
        
        # Quick pattern matching for fast path intents
        for category, patterns in self.fast_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    processing_time = (time.time() - start_time) * 1000
                    
                    return IntentClassification(
                        intent=category.value,
                        category=category,
                        confidence=0.9,  # High confidence for pattern matches
                        slots=self._extract_slots(text, category),
                        processing_time_ms=processing_time
                    )
        
        # Quick check for think path intents
        for category, patterns in self.think_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    processing_time = (time.time() - start_time) * 1000
                    
                    return IntentClassification(
                        intent=category.value,
                        category=category,
                        confidence=0.8,
                        slots=self._extract_slots(text, category),
                        processing_time_ms=processing_time
                    )
        
        # Fallback to keyword-based classification
        category = self._classify_by_keywords(text_lower)
        processing_time = (time.time() - start_time) * 1000
        
        return IntentClassification(
            intent=category.value,
            category=category,
            confidence=0.6,
            slots={},
            processing_time_ms=processing_time
        )
    
    def _classify_by_keywords(self, text: str) -> IntentCategory:
        """Fallback keyword-based classification"""
        # Check for calendar-related keywords
        if any(keyword in text for keyword in self.swedish_commands['calendar_keywords']):
            return IntentCategory.CALENDAR_COMPLEX
            
        # Check for email-related keywords
        if any(keyword in text for keyword in self.swedish_commands['email_keywords']):
            return IntentCategory.EMAIL_ANALYSIS
            
        # Check for music-related keywords
        if any(keyword in text for keyword in self.swedish_commands['music_keywords']):
            return IntentCategory.SPOTIFY_SEARCH
            
        # Check for time-related keywords
        if any(keyword in text for keyword in self.swedish_commands['time_keywords']):
            return IntentCategory.TIME_DATE
            
        # Check for greeting keywords
        if any(keyword in text for keyword in self.swedish_commands['greeting_words']):
            return IntentCategory.GREETING
            
        # Check for question words
        if any(word in text for word in self.swedish_commands['question_words']):
            return IntentCategory.SIMPLE_QUESTION
            
        # Default to general conversation
        return IntentCategory.GENERAL_CONVERSATION
    
    def _extract_slots(self, text: str, category: IntentCategory) -> Dict[str, Any]:
        """Extract slot values from text based on intent category"""
        slots = {}
        text_lower = text.lower()
        
        if category == IntentCategory.CALENDAR_COMPLEX:
            # Extract time patterns
            time_patterns = [
                (r'\b(\d{1,2}):(\d{2})\b', 'time'),
                (r'\bkl\s*(\d{1,2})(?::(\d{2}))?\b', 'time'),
                (r'\b(imorgon|idag|igår|måndag|tisdag|onsdag|torsdag|fredag|lördag|söndag)\b', 'date'),
                (r'\b(nästa|kommande)\s+(vecka|månad|år)\b', 'relative_date'),
                (r'\bmed\s+(\w+)\b', 'participant')
            ]
            
            for pattern, slot_name in time_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    slots[slot_name] = match.group()
        
        elif category == IntentCategory.SPOTIFY_SEARCH:
            # Extract music-related entities
            music_patterns = [
                (r'\bartist[:\s]+([^,\.]+)', 'artist'),
                (r'\balbum[:\s]+([^,\.]+)', 'album'),
                (r'\blåt[:\s]+([^,\.]+)', 'song'),
                (r'\bspela\s+([^,\.]+)', 'query')
            ]
            
            for pattern, slot_name in music_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    slots[slot_name] = match.group(1).strip()
        
        return slots

class IntentRouter:
    """Main intent router implementing the hybrid architecture"""
    
    def __init__(self):
        self.classifier = SwedishIntentClassifier()
        
        # Routing configuration
        self.config = {
            # Confidence thresholds
            "fast_confidence_threshold": 0.85,
            "think_confidence_threshold": 0.5,
            
            # Latency targets
            "max_fast_latency_ms": 300,
            "max_think_latency_ms": 2000,
            "routing_timeout_ms": 50,
            
            # Intent category mappings
            "fast_categories": {
                IntentCategory.GREETING,
                IntentCategory.ACKNOWLEDGMENT,
                IntentCategory.SIMPLE_QUESTION,
                IntentCategory.WEATHER,
                IntentCategory.TIME_DATE
            },
            
            "think_categories": {
                IntentCategory.CALENDAR_COMPLEX,
                IntentCategory.EMAIL_ANALYSIS,
                IntentCategory.TASK_PLANNING,
                IntentCategory.SPOTIFY_SEARCH,
                IntentCategory.MULTI_STEP_WORKFLOW
            }
        }
    
    async def route_intent(self, text: str, audio_features: Optional[Dict[str, Any]] = None) -> RouteDecision:
        """
        Main intent routing with <50ms latency target
        
        Args:
            text: Transcribed text
            audio_features: Optional audio metadata (duration, confidence, etc.)
        
        Returns:
            RouteDecision with path, reasoning, and confidence
        """
        start_time = time.time()
        
        try:
            # Fast intent classification
            intent_classification = self.classifier.classify_intent_fast(text)
            
            # Integrate with existing router for tool commands
            existing_result = classify(text)
            
            # Make routing decision
            route_decision = self._make_routing_decision(
                intent_classification, existing_result, audio_features
            )
            
            # Add processing time
            total_time_ms = (time.time() - start_time) * 1000
            route_decision.estimated_latency_ms = total_time_ms
            
            # Log routing decision
            logger.info(f"Intent routed: '{text[:50]}...' -> {route_decision.path.value} "
                       f"({route_decision.confidence:.2f}, {total_time_ms:.1f}ms)")
            
            return route_decision
            
        except Exception as e:
            logger.error(f"Error in intent routing: {e}")
            
            # Failsafe: route to think path for safety
            return RouteDecision(
                path=ProcessingPath.THINK,
                reason="routing_error_safety_fallback",
                confidence=0.0,
                intent_category=IntentCategory.UNKNOWN,
                estimated_latency_ms=(time.time() - start_time) * 1000
            )
    
    def _make_routing_decision(self, intent_classification: IntentClassification, 
                              existing_result: Optional[Dict[str, Any]],
                              audio_features: Optional[Dict[str, Any]]) -> RouteDecision:
        """Make intelligent routing decision based on multiple factors"""
        
        category = intent_classification.category
        confidence = intent_classification.confidence
        
        # Factor in existing router result if available
        if existing_result and existing_result.get("confidence", 0) > confidence:
            confidence = existing_result["confidence"]
        
        # High confidence and fast category -> Fast path
        if (confidence >= self.config["fast_confidence_threshold"] and 
            category in self.config["fast_categories"]):
            return RouteDecision(
                path=ProcessingPath.FAST,
                reason="high_confidence_simple_intent",
                confidence=confidence,
                intent_category=category,
                estimated_latency_ms=self.config["max_fast_latency_ms"],
                slots=intent_classification.slots
            )
        
        # Complex category always goes to think path regardless of confidence
        if category in self.config["think_categories"]:
            return RouteDecision(
                path=ProcessingPath.THINK,
                reason="complex_intent_requires_local_processing",
                confidence=confidence,
                intent_category=category,
                estimated_latency_ms=self.config["max_think_latency_ms"],
                slots=intent_classification.slots
            )
        
        # Medium confidence -> Think path for safety
        if confidence >= self.config["think_confidence_threshold"]:
            return RouteDecision(
                path=ProcessingPath.THINK,
                reason="medium_confidence_safety_routing",
                confidence=confidence,
                intent_category=category,
                estimated_latency_ms=self.config["max_think_latency_ms"],
                slots=intent_classification.slots
            )
        
        # Low confidence -> Think path with local processing
        return RouteDecision(
            path=ProcessingPath.THINK,
            reason="low_confidence_needs_local_analysis",
            confidence=confidence,
            intent_category=category,
            estimated_latency_ms=self.config["max_think_latency_ms"],
            slots=intent_classification.slots
        )
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update routing configuration"""
        self.config.update(new_config)
        logger.info("Intent router configuration updated")
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            "config": self.config,
            "fast_categories": [cat.value for cat in self.config["fast_categories"]],
            "think_categories": [cat.value for cat in self.config["think_categories"]],
            "classifier_patterns": {
                "fast_patterns": len(sum(self.classifier.fast_patterns.values(), [])),
                "think_patterns": len(sum(self.classifier.think_patterns.values(), []))
            }
        }

# Global router instance
intent_router = None

def get_intent_router() -> IntentRouter:
    """Get or create intent router instance"""
    global intent_router
    if intent_router is None:
        intent_router = IntentRouter()
    return intent_router

# Convenience functions for backward compatibility
async def classify_and_route_intent(text: str, audio_features: Optional[Dict[str, Any]] = None) -> RouteDecision:
    """Classify intent and get routing decision"""
    router = get_intent_router()
    return await router.route_intent(text, audio_features)

def classify_intent_swedish(text: str) -> IntentClassification:
    """Fast Swedish intent classification"""
    classifier = SwedishIntentClassifier()
    return classifier.classify_intent_fast(text)