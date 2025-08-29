"""
Production Voice Configuration - Go-live settings for optimal performance
"""

import os
from typing import Dict, Any, List

class ProductionVoiceConfig:
    """Production-ready configuration for voice pipeline"""
    
    # Go-live checklist settings
    ALWAYS_SPEAK_SOURCES = {"chat", "notification"}  # Always generate TTS for these
    TL_DR_FIRST_SOURCES = {"email"}  # TL;DR first, then segments
    
    # Router optimization - increased threshold for better fast-path usage
    ROUTER_SIMPLE_THRESHOLD = 130  # characters (increased from 80)
    ROUTER_COMPLEX_INDICATORS = [
        "imorgon", "idag", "igår", "måndag", "tisdag", "onsdag", "torsdag", "fredag", "lördag", "söndag",
        "klockan", "kl", "minuter", "timmar", "dagar", "veckor", "månader", "år",
        "midsommarafton", "julafton", "nyår"
    ]
    
    # Ollama optimization for maximum cache hits
    OLLAMA_FAST_PARAMS = {
        "num_predict": 60,      # Shorter responses
        "temperature": 0.0,     # Deterministic for cache
        "top_k": 1,            # Most predictable
        "top_p": 1.0,          # No sampling
        "repeat_penalty": 1.0   # No creativity penalty
    }
    
    OLLAMA_FULL_PARAMS = {
        "num_predict": 320,     # Longer responses allowed
        "temperature": 0.0,     # Still deterministic
        "top_k": 1,
        "top_p": 1.0,
        "repeat_penalty": 1.0
    }
    
    # Style and rate mapping per source type
    STYLE_RATE_MAP = {
        "chat": {"style": "neutral", "rate": 1.0},
        "notification": {"style": "cheerful", "rate": 1.08},
        "email": {"style": "formal", "rate": 1.0},  # For TL;DR
        "calendar": {"style": "neutral", "rate": 1.0},
        "command": {"style": "neutral", "rate": 1.0}
    }
    
    # Performance targets (for monitoring)
    PERFORMANCE_TARGETS = {
        "ttfa_chat_p95_ms": 3000,      # Time To First Audio for chat
        "ttfa_email_tldr_p95_ms": 3500,  # Time To First Audio for email TL;DR
        "llm_short_p95_ms": 2500,       # LLM time for short texts
        "tts_error_rate_max_pct": 2.0,  # Max TTS error rate
        "cache_hit_rate_min_pct": 45.0  # Min cache hit rate after 7 days
    }
    
    # Phrase bank for pre-caching common responses
    COMMON_PHRASES = [
        # Greetings and responses
        "Hi Alice!",
        "Hello there!",
        "Good morning!",
        "Thank you!",
        "You're welcome.",
        "I'm here to help.",
        
        # Common questions
        "What time is it?",
        "What's the weather like?",
        "What's on my calendar?",
        "Any new messages?",
        
        # Notifications
        "Battery low.",
        "New message received.",
        "Reminder set.",
        "Task completed.",
        "Update available.",
        
        # Status responses
        "Done.",
        "Got it.",
        "Processing...",
        "Working on it.",
        "One moment please."
    ]
    
    # Swedish pronunciation hints (for TTS improvement)
    SWEDISH_PRONUNCIATION_MAP = {
        "Göteborg": "YEH-teh-bor-y",
        "Västerås": "VEST-er-aws", 
        "Malmö": "MAL-meu",
        "Linköping": "lin-CHEU-ping",
        "Ann-Christin": "AHN kris-TEEN",
        "Per-Erik": "PAIR eh-rik",
        "Anna-Lena": "AH-nah LEH-nah",
        "Hogia": "HOH-gee-ah"
    }
    
    # TTS optimization settings
    TTS_CONFIG = {
        "pre_warm_interval_hours": 1.0,  # Pre-warm TTS every hour
        "mp3_bitrate": "48k",           # 48-64 kbps for faster TTFA
        "timeout_seconds": 4.0,         # Quick timeout for fallback
        "retry_attempts": 2,            # Quick retries
        "max_concurrent": 2,            # Queue management
        "cache_size_mb": 500           # Generous cache
    }
    
    # Enhanced normalization patterns
    ENHANCED_PRE_PATTERNS = [
        # Extended time patterns
        (r'\bom\s+en\s+kvart\b', 'in 15 minutes'),
        (r'\bom\s+(?:en\s+)?halvtimme\b', 'in 30 minutes'),
        (r'\bom\s+(?:en\s+)?timme\b', 'in 1 hour'),
        
        # Month names
        (r'\bjanuari\b', 'January'),
        (r'\bfebruari\b', 'February'), 
        (r'\bmars\b', 'March'),
        (r'\bapril\b', 'April'),
        (r'\bmaj\b', 'May'),
        (r'\bjuni\b', 'June'),
        (r'\bjuli\b', 'July'),
        (r'\baugusti\b', 'August'),
        (r'\bseptember\b', 'September'),
        (r'\boktober\b', 'October'),
        (r'\bnovember\b', 'November'),
        (r'\bdecember\b', 'December'),
        
        # Holiday patterns
        (r'\bjulafton\b', 'Christmas Eve'),
        (r'\bnyårsafton\b', 'New Year\'s Eve'),
        (r'\bvalborg\b', 'Walpurgis Night'),
    ]
    
    # Number words 0-99 for consistent digitization
    EXTENDED_NUMBER_WORDS = {
        "noll": "0",
        # ... (would include all Swedish numbers)
    }
    
    @classmethod
    def get_ollama_params(cls, is_simple: bool) -> Dict[str, Any]:
        """Get optimized Ollama parameters based on text complexity"""
        return cls.OLLAMA_FAST_PARAMS if is_simple else cls.OLLAMA_FULL_PARAMS
    
    @classmethod
    def get_style_rate(cls, source_type: str) -> Dict[str, Any]:
        """Get style and rate for source type"""
        return cls.STYLE_RATE_MAP.get(source_type, {"style": "neutral", "rate": 1.0})
    
    @classmethod
    def should_always_speak(cls, source_type: str) -> bool:
        """Check if source type should always generate TTS"""
        return source_type in cls.ALWAYS_SPEAK_SOURCES
    
    @classmethod
    def should_tldr_first(cls, source_type: str) -> bool:
        """Check if source type should do TL;DR first approach"""
        return source_type in cls.TL_DR_FIRST_SOURCES
    
    @classmethod
    def get_performance_target(cls, metric: str) -> float:
        """Get performance target for monitoring"""
        return cls.PERFORMANCE_TARGETS.get(metric, 0.0)