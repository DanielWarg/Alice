"""
Input Processor - Standardizes input from different sources (chat, email, calendar, notifications).
Converts all sources into a unified InputPackage format for the orchestrator.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime
import re

@dataclass
class InputPackage:
    """Standardized input format for the voice pipeline"""
    source_type: str  # chat, email, calendar, notification, command
    text_sv: str     # Original Swedish text
    meta: Dict[str, Any]  # Additional context (sender, urgency, etc.)
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class InputProcessor:
    """Processes different input types into standardized InputPackage format"""
    
    def __init__(self):
        self.max_length = 2000  # Max chars before segmentation
        
    def process_chat(self, text: str, metadata: Optional[Dict] = None) -> InputPackage:
        """Process chat message input"""
        return InputPackage(
            source_type="chat",
            text_sv=self._clean_text(text),
            meta=metadata or {"urgency": "normal", "context": "chat"}
        )
    
    def process_email(self, subject: str, body: str, sender: str = None, metadata: Optional[Dict] = None) -> InputPackage:
        """Process email input - combines subject and body intelligently"""
        # Combine subject and body for context
        if subject and body:
            combined_text = f"Ämne: {subject}\n\n{body}"
        elif subject:
            combined_text = f"Ämne: {subject}"
        else:
            combined_text = body or ""
            
        meta = metadata or {}
        meta.update({
            "subject": subject,
            "sender": sender,
            "urgency": "normal",
            "context": "email",
            "requires_summary": len(combined_text) > 800  # Long emails need TL;DR
        })
        
        return InputPackage(
            source_type="email",
            text_sv=self._clean_text(combined_text),
            meta=meta
        )
    
    def process_calendar(self, title: str, start_time: str, description: str = None, metadata: Optional[Dict] = None) -> InputPackage:
        """Process calendar event/reminder"""
        # Format calendar info for speech
        text_parts = [f"Kalenderhändelse: {title}"]
        if start_time:
            text_parts.append(f"Tid: {start_time}")
        if description:
            text_parts.append(f"Beskrivning: {description}")
            
        combined_text = ". ".join(text_parts)
        
        meta = metadata or {}
        meta.update({
            "title": title,
            "start_time": start_time, 
            "urgency": "high",  # Calendar events are usually time-sensitive
            "context": "calendar"
        })
        
        return InputPackage(
            source_type="calendar",
            text_sv=self._clean_text(combined_text),
            meta=meta
        )
    
    def process_notification(self, text: str, notification_type: str = "system", metadata: Optional[Dict] = None) -> InputPackage:
        """Process system notification"""
        meta = metadata or {}
        meta.update({
            "notification_type": notification_type,
            "urgency": "low",
            "context": "notification"
        })
        
        return InputPackage(
            source_type="notification",
            text_sv=self._clean_text(text),
            meta=meta
        )
    
    def process_command(self, text: str, metadata: Optional[Dict] = None) -> InputPackage:
        """Process direct command input"""
        return InputPackage(
            source_type="command",
            text_sv=self._clean_text(text),
            meta=metadata or {"urgency": "high", "context": "command"}
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text input"""
        if not text:
            return ""
            
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove problematic characters that might break TTS
        text = re.sub(r'[^\w\s\.\,\!\?\:\;\-\(\)\[\]\"\'åäöÅÄÖ]', '', text)
        
        return text
    
    def should_segment(self, input_package: InputPackage) -> bool:
        """Determine if input needs segmentation for long content"""
        return (
            len(input_package.text_sv) > self.max_length or
            input_package.meta.get("requires_summary", False) or
            input_package.source_type == "email"
        )
    
    def get_processing_priority(self, input_package: InputPackage) -> int:
        """Get processing priority (1=highest, 3=lowest)"""
        urgency = input_package.meta.get("urgency", "normal")
        
        priority_map = {
            "high": 1,     # Commands, calendar events
            "normal": 2,   # Chat, regular emails  
            "low": 3       # Notifications, system messages
        }
        
        return priority_map.get(urgency, 2)