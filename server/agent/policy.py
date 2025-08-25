"""
Intent routing policy for FAST/DEEP path selection
"""

import os
import re
import logging
from typing import Dict, Any, Literal
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("alice.agent.policy")

class RoutePath(Enum):
    """Available routing paths"""
    FAST = "FAST"   # Quick OpenAI response for simple queries
    DEEP = "DEEP"   # Local AI for complex reasoning/privacy

class PrivacyLevel(Enum):
    """Privacy sensitivity levels"""
    LOW = "LOW"       # Public information, safe for cloud
    MEDIUM = "MEDIUM" # Some personal data
    HIGH = "HIGH"     # Sensitive/private data, local only

@dataclass
class IntentClassification:
    """Intent classification result"""
    intent: str
    need_tools: bool = False
    long_answer: bool = False
    privacy: PrivacyLevel = PrivacyLevel.LOW
    confidence: float = 0.0
    reasoning: str = ""

def routeIntent(nlu: IntentClassification) -> RoutePath:
    """
    Route intent to FAST or DEEP path based on classification.
    
    Args:
        nlu: Intent classification result
        
    Returns:
        RoutePath enum indicating which processing path to use
    """
    
    # High privacy always goes to DEEP (local)
    if nlu.privacy == PrivacyLevel.HIGH:
        logger.debug(f"Routing to DEEP: high privacy requirement")
        return RoutePath.DEEP
    
    # Long answers need DEEP processing
    if nlu.long_answer:
        logger.debug(f"Routing to DEEP: long answer required")
        return RoutePath.DEEP
    
    # Complex tool usage typically needs DEEP
    if nlu.need_tools and nlu.privacy != PrivacyLevel.LOW:
        logger.debug(f"Routing to DEEP: tools with medium+ privacy")
        return RoutePath.DEEP
    
    # Simple tool usage can be FAST if low privacy
    if nlu.need_tools and nlu.privacy == PrivacyLevel.LOW and not nlu.long_answer:
        logger.debug(f"Routing to FAST: simple tools with low privacy")
        return RoutePath.FAST
    
    # Quick conversational responses can be FAST
    if not nlu.need_tools and not nlu.long_answer and nlu.privacy == PrivacyLevel.LOW:
        logger.debug(f"Routing to FAST: simple conversation")
        return RoutePath.FAST
    
    # Default to DEEP for safety
    logger.debug(f"Routing to DEEP: default/safety")
    return RoutePath.DEEP

def classifyIntent(user_input: str) -> IntentClassification:
    """
    Classify user intent for routing decisions.
    
    Args:
        user_input: User's input text
        
    Returns:
        IntentClassification with routing hints
    """
    
    text = user_input.lower().strip()
    
    # Initialize classification
    classification = IntentClassification(
        intent="unknown",
        need_tools=False,
        long_answer=False,
        privacy=PrivacyLevel.LOW,
        confidence=0.5
    )
    
    # Tool requirement detection
    tool_indicators = [
        # Home automation
        r'\b(tänd|släck|sätt på|stäng av|dimma|ljus|lampor|belysning)\b',
        # Music/Spotify
        r'\b(spela|pausa|stoppa|nästa|föregående|musik|låt|spotify)\b',
        # Calendar
        r'\b(boka|skapa|möte|kalendern?|avbokning|tid|imorgon|idag)\b',
        # Email
        r'\b(skicka|e-?mail|mejl|gmail|inbox|meddelande)\b',
        # Weather
        r'\b(väder|temperatur|regn|sol|molnigt|grader)\b'
    ]
    
    for pattern in tool_indicators:
        if re.search(pattern, text):
            classification.need_tools = True
            break
    
    # Privacy level detection
    privacy_high_indicators = [
        r'\b(personlig|privat|hemlig|konfidentiell|lösenord|pin|kod)\b',
        r'\b(bank|konto|pengar|lön|ekonomi|personnummer)\b',
        r'\b(sjuk|hälsa|läkare|medicin|diagnos)\b'
    ]
    
    privacy_medium_indicators = [
        r'\b(namn|adress|telefon|familj|jobb|företag)\b',
        r'\b(kalender|möte|schema|tider)\b'
    ]
    
    for pattern in privacy_high_indicators:
        if re.search(pattern, text):
            classification.privacy = PrivacyLevel.HIGH
            break
    else:
        for pattern in privacy_medium_indicators:
            if re.search(pattern, text):
                classification.privacy = PrivacyLevel.MEDIUM
                break
    
    # Long answer detection
    long_answer_indicators = [
        r'\b(förklara|berätta|redogör|analysera|diskutera|jämför)\b',
        r'\b(hur fungerar|vad betyder|varför|på vilket sätt)\b',
        r'\b(lista|exempel|alternativ|möjligheter)\b'
    ]
    
    for pattern in long_answer_indicators:
        if re.search(pattern, text):
            classification.long_answer = True
            break
    
    # Intent classification based on patterns
    intents = {
        "home_automation": r'\b(tänd|släck|sätt på|stäng av|dimma|ljus|hem)\b',
        "music_control": r'\b(spela|musik|låt|spotify|pausa|stoppa)\b',
        "calendar": r'\b(boka|möte|kalender|tid|schema)\b',
        "email": r'\b(e-?mail|mejl|skicka|gmail)\b',
        "weather": r'\b(väder|temperatur|regn|sol)\b',
        "conversation": r'\b(hej|hallo|tack|bra|hur|vad)\b',
        "question": r'\?|vad|hur|när|var|vem|varför'
    }
    
    for intent, pattern in intents.items():
        if re.search(pattern, text):
            classification.intent = intent
            classification.confidence = 0.8
            break
    
    # Reasoning
    reasons = []
    if classification.need_tools:
        reasons.append("requires tools")
    if classification.privacy != PrivacyLevel.LOW:
        reasons.append(f"{classification.privacy.value} privacy")
    if classification.long_answer:
        reasons.append("long answer")
    
    classification.reasoning = ", ".join(reasons) if reasons else "simple query"
    
    logger.debug(f"Intent classified: {classification.intent} ({classification.reasoning})")
    
    return classification

def shouldUseCache(classification: IntentClassification) -> bool:
    """Determine if response should be cached"""
    
    # Don't cache high privacy or tool-based responses
    if classification.privacy == PrivacyLevel.HIGH or classification.need_tools:
        return False
    
    # Cache simple conversational responses
    if classification.intent in ["conversation", "weather"] and not classification.need_tools:
        return True
    
    return False

def getMaxTokensForPath(path: RoutePath) -> int:
    """Get appropriate max tokens for the routing path"""
    
    if path == RoutePath.FAST:
        return int(os.getenv("FAST_PATH_MAX_TOKENS", "150"))
    else:  # DEEP
        return int(os.getenv("LOCAL_AI_MAX_TOKENS", "2048"))