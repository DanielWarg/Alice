"""
Pydantic validators for Alice AI Assistant with robust Swedish datetime parsing
"""

import re
from datetime import datetime, date, time
from typing import Any, Optional, Union, Dict, List
from pydantic import BaseModel, Field, validator, ValidationError
from enum import Enum

try:
    import pytz
    from voice_calendar_parser import SwedishDateTimeParser, ParsedDateTime
    SWEDISH_PARSER_AVAILABLE = True
except ImportError:
    SWEDISH_PARSER_AVAILABLE = False
    ParsedDateTime = None

from error_handlers import SwedishDateTimeValidationError


class SwedishDateTimeField(BaseModel):
    """
    Pydantic model for Swedish datetime input validation
    Supports natural Swedish language datetime expressions
    """
    
    raw_input: str = Field(description="Original Swedish datetime string")
    parsed_datetime: Optional[datetime] = Field(default=None, description="Parsed datetime object")
    confidence: Optional[float] = Field(default=0.0, description="Parsing confidence (0.0-1.0)")
    is_relative: bool = Field(default=False, description="Whether input is relative (imorgon, nästa vecka)")
    format_used: Optional[str] = Field(default=None, description="Which parsing format was successful")
    
    class Config:
        arbitrary_types_allowed = True
    
    @validator('raw_input')
    def validate_swedish_datetime_input(cls, v: str) -> str:
        """Validate and parse Swedish datetime expressions"""
        if not v or not v.strip():
            raise ValueError("Datetime input cannot be empty")
        
        # Clean input
        cleaned_input = v.strip().lower()
        
        # Try parsing with SwedishDateTimeParser if available
        if SWEDISH_PARSER_AVAILABLE:
            try:
                parser = SwedishDateTimeParser()
                
                # Try different parsing strategies
                parsed_result = cls._try_parse_swedish(parser, cleaned_input)
                if parsed_result:
                    return v  # Return original input, parsed result stored separately
                    
            except Exception as e:
                pass  # Fall through to pattern matching
        
        # Fallback to pattern-based validation
        if not cls._validate_swedish_patterns(cleaned_input):
            supported_formats = [
                "idag, imorgon, igår",
                "på måndag, på fredag",
                "nästa vecka, kommande måndag", 
                "kl 14:30, halv tre, kvart över fyra",
                "14 januari, 25 december 2024",
                "om en timme, om 30 minuter"
            ]
            raise SwedishDateTimeValidationError(v, supported_formats)
        
        return v
    
    @classmethod
    def _try_parse_swedish(cls, parser: 'SwedishDateTimeParser', input_text: str) -> Optional[ParsedDateTime]:
        """Try parsing with SwedishDateTimeParser using different strategies"""
        
        # Strategy 1: Try as complete datetime expression
        try:
            # Parse as date + time entities (would need NLU integration)
            # For now, implement basic parsing logic
            result = cls._basic_swedish_parse(parser, input_text)
            return result
        except Exception as e:
            logger.error(f"Swedish datetime parsing failed: {e}")
            pass
        
        return None
    
    @classmethod
    def _basic_swedish_parse(cls, parser: 'SwedishDateTimeParser', input_text: str) -> Optional[ParsedDateTime]:
        """Basic Swedish datetime parsing without full NLU"""
        
        now = parser.now()
        
        # Handle common relative dates
        if any(word in input_text for word in ['idag', 'today']):
            return ParsedDateTime(
                datetime=now.replace(hour=9, minute=0, second=0, microsecond=0),
                confidence=0.9,
                is_relative=True,
                original_text=input_text
            )
            
        elif any(word in input_text for word in ['imorgon', 'tomorrow', 'i morgon']):
            tomorrow = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
            return ParsedDateTime(
                datetime=tomorrow,
                confidence=0.9,
                is_relative=True,
                original_text=input_text
            )
            
        elif any(word in input_text for word in ['igår', 'yesterday']):
            yesterday = now.replace(hour=9, minute=0, second=0, microsecond=0) - timedelta(days=1)
            return ParsedDateTime(
                datetime=yesterday,
                confidence=0.9,
                is_relative=True,
                original_text=input_text
            )
        
        # Handle time expressions
        time_match = re.search(r'(?:kl\s*)?(\d{1,2})[:\.](\d{2})', input_text)
        if time_match:
            hour, minute = int(time_match.group(1)), int(time_match.group(2))
            target_date = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return ParsedDateTime(
                datetime=target_date,
                confidence=0.8,
                is_relative=False,
                original_text=input_text
            )
        
        return None
    
    @classmethod
    def _validate_swedish_patterns(cls, input_text: str) -> bool:
        """Pattern-based validation for Swedish datetime expressions"""
        
        # Define Swedish datetime patterns
        patterns = [
            # Relative dates
            r'\b(idag|imorgon|i\s*morgon|igår|förrgår|övermorgon)\b',
            
            # Weekdays  
            r'\bpå\s+(måndag|tisdag|onsdag|torsdag|fredag|lördag|söndag)\b',
            r'\b(nästa|kommande)\s+(måndag|tisdag|onsdag|torsdag|fredag|lördag|söndag)\b',
            
            # Week/month references
            r'\b(nästa|kommande|denna)\s+(vecka|månad)\b',
            r'\bi\s*(nästa|kommande)\s+(vecka|månad)\b',
            
            # Time expressions
            r'\b(?:kl\s*)?(\d{1,2})[:\.](\d{2})\b',
            r'\b(?:kl\s*)?(\d{1,2})\s*(?:på\s*)?(?:morgonen|förmiddagen|eftermiddagen|kvällen)?\b',
            r'\b(halv|kvart)\s+(över|i)\s+(\w+)\b',
            
            # Date expressions
            r'\b(\d{1,2})\s+(januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\b',
            r'\b(\d{1,2})\s+(januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\s+(\d{4})\b',
            
            # Duration/offset
            r'\bom\s+(\d+)\s+(minuter?|timmar?|dagar?)\b',
        ]
        
        for pattern in patterns:
            if re.search(pattern, input_text, re.IGNORECASE):
                return True
        
        return False


class ChatMessage(BaseModel):
    """Validated chat message with optional Swedish datetime parsing"""
    
    content: str = Field(min_length=1, max_length=2000, description="Message content")
    swedish_datetime: Optional[SwedishDateTimeField] = Field(default=None, description="Parsed Swedish datetime if present")
    
    @validator('content')
    def validate_content(cls, v: str) -> str:
        """Validate message content"""
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        
        # Basic content validation
        stripped = v.strip()
        if len(stripped) < 1:
            raise ValueError("Message must contain at least one character")
        
        return stripped
    
    @validator('swedish_datetime', pre=True, always=True)
    def extract_swedish_datetime(cls, v, values):
        """Extract Swedish datetime from content if present"""
        if v is not None:
            return v  # Already provided
        
        content = values.get('content', '')
        if not content:
            return None
        
        # Check if content contains datetime patterns
        datetime_indicators = [
            'idag', 'imorgon', 'igår', 'kl ', 'på måndag', 'på tisdag', 'på onsdag', 
            'på torsdag', 'på fredag', 'på lördag', 'på söndag', 'nästa vecka',
            'kommande vecka', 'om ', 'januari', 'februari', 'mars', 'april',
            'maj', 'juni', 'juli', 'augusti', 'september', 'oktober', 'november', 'december'
        ]
        
        content_lower = content.lower()
        if any(indicator in content_lower for indicator in datetime_indicators):
            try:
                return SwedishDateTimeField(raw_input=content)
            except (ValueError, SwedishDateTimeValidationError):
                # Datetime parsing failed but message is still valid
                return None
        
        return None


class CalendarEventRequest(BaseModel):
    """Validated calendar event creation request"""
    
    title: str = Field(min_length=1, max_length=200, description="Event title")
    start_time: SwedishDateTimeField = Field(description="Event start time in Swedish")
    end_time: Optional[SwedishDateTimeField] = Field(default=None, description="Event end time in Swedish")
    description: Optional[str] = Field(default=None, max_length=1000, description="Event description")
    location: Optional[str] = Field(default=None, max_length=200, description="Event location")
    
    @validator('title')
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Event title cannot be empty")
        return v.strip()
    
    @validator('end_time')
    def validate_end_after_start(cls, v, values):
        """Ensure end time is after start time"""
        if v is None:
            return v
            
        start_time = values.get('start_time')
        if start_time and start_time.parsed_datetime and v.parsed_datetime:
            if v.parsed_datetime <= start_time.parsed_datetime:
                raise ValueError("End time must be after start time")
        
        return v


class SpotifySearchRequest(BaseModel):
    """Validated Spotify search request"""
    
    query: str = Field(min_length=1, max_length=500, description="Search query")
    search_type: str = Field(default="track", pattern="^(track|playlist|album|artist)$", description="Search type")
    limit: int = Field(default=10, ge=1, le=50, description="Number of results")
    
    @validator('query')
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Search query cannot be empty")
        return v.strip()


# Import required for basic_swedish_parse
from datetime import timedelta


def validate_swedish_datetime_string(v: str) -> SwedishDateTimeField:
    """
    Standalone function to validate Swedish datetime strings
    Can be used in FastAPI endpoints or other validation contexts
    """
    try:
        return SwedishDateTimeField(raw_input=v)
    except ValidationError as e:
        # Convert to our custom error
        raise SwedishDateTimeValidationError(
            v, 
            ["idag, imorgon, på fredag", "kl 14:30, halv tre", "14 januari 2024"]
        ) from e


def create_swedish_datetime_validator(field_name: str = "datetime"):
    """
    Factory function to create Swedish datetime validators for Pydantic models
    
    Usage:
        class MyModel(BaseModel):
            when: str
            
            _validate_when = validator('when', allow_reuse=True)(
                create_swedish_datetime_validator('when')
            )
    """
    
    def validator_func(cls, v):
        if isinstance(v, str):
            return validate_swedish_datetime_string(v).raw_input
        return v
    
    return validator_func


# Example usage models
class ExampleChatRequest(BaseModel):
    """Example chat request with Swedish datetime support"""
    message: ChatMessage
    context: Optional[Dict[str, Any]] = Field(default=None)
    
    class Config:
        schema_extra = {
            "example": {
                "message": {
                    "content": "Skapa ett möte imorgon kl 14:30",
                    "swedish_datetime": {
                        "raw_input": "imorgon kl 14:30"
                    }
                },
                "context": {"user_timezone": "Europe/Stockholm"}
            }
        }


class ExampleSearchRequest(BaseModel):
    """Example search with datetime constraints"""
    query: str = Field(description="Search query")
    date_filter: Optional[SwedishDateTimeField] = Field(default=None, description="Date filter in Swedish")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "möten med teamet",
                "date_filter": {
                    "raw_input": "nästa vecka"
                }
            }
        }