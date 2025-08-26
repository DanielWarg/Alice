#!/usr/bin/env python3
"""
🛡️ Network Guard - Strict Privacy Boundary Enforcement
Prevents any no_cloud=true content from reaching OpenAI Realtime API
"""
import logging
import time
import json
import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class GuardDecision(Enum):
    """Guard decision types"""
    ALLOW = "allow"
    BLOCK = "block"
    SANITIZE = "sanitize"

class ViolationType(Enum):
    """Privacy violation types"""
    NO_CLOUD_FLAG = "no_cloud_flag"
    PII_DETECTED = "pii_detected"
    PRIVATE_CONTENT = "private_content"
    RAW_TOOL_RESULT = "raw_tool_result"
    FUNCTION_ARGUMENTS = "function_arguments"

@dataclass
class GuardResult:
    """Result of network guard check"""
    decision: GuardDecision
    violation_type: Optional[ViolationType]
    reason: str
    sanitized_content: Optional[str] = None
    risk_score: float = 0.0
    metadata: Dict[str, Any] = None

class NetworkGuard:
    """
    Strict privacy boundary enforcement for cloud communications
    Prevents any private data from reaching OpenAI Realtime API
    """
    
    def __init__(self):
        self.blocked_patterns = [
            # Email patterns (high confidence)
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            # Phone patterns (more specific)
            r'\b(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}\b',
            # Personal names (very specific - real names only)
            r'\b[A-Z][a-z]{3,}\s+[A-Z][a-z]{3,}(?:\s+[A-Z][a-z]{3,})*\b(?:\s+(?:at|in|from|to|with)\s+[A-Z])',
            # File paths (absolute paths only)
            r'\b(?:/[a-zA-Z0-9_.-]+){2,}/?(?:\.[a-zA-Z0-9]+)?\b',
            r'\b[A-Z]:\\(?:[^\\/:*?"<>|\r\n]+\\)+[^\\/:*?"<>|\r\n]*\b',
            # IP addresses
            r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            # Credit card-like numbers (more specific)
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            # Social security-like patterns
            r'\b\d{3}-?\d{2}-?\d{4}\b'
        ]
        
        self.private_keywords = {
            'password', 'secret', 'private', 'confidential', 'token',
            'key', 'credit', 'ssn', 'social', 'bank', 'account',
            'password', 'lösenord', 'privat', 'hemlig', 'kontonummer'
        }
        
        # Metrics tracking
        self.metrics = {
            'total_checks': 0,
            'blocks': 0,
            'sanitizations': 0,
            'allows': 0,
            'violation_types': {},
            'privacy_leak_attempts': 0
        }
        
        # Audit log for security review
        self.audit_log = []
        
        logger.info("🛡️ Network Guard initialized with strict privacy enforcement")
    
    def check_outbound_message(self, message: Union[Dict, str], 
                             destination: str = "realtime") -> GuardResult:
        """
        Check outbound message for privacy violations before cloud transmission
        
        Args:
            message: Message to check (dict or string)
            destination: Target destination ("realtime", "openai", etc)
            
        Returns:
            GuardResult with decision and details
        """
        start_time = time.time()
        self.metrics['total_checks'] += 1
        
        # Convert message to analyzable format
        if isinstance(message, dict):
            content = json.dumps(message)
            has_no_cloud = message.get('no_cloud', False)
            message_type = message.get('type', 'unknown')
        else:
            content = str(message)
            has_no_cloud = False
            message_type = 'string'
        
        logger.debug(f"🔍 Guard checking {len(content)} chars to {destination}")
        
        # Step 1: Check no_cloud flag
        if has_no_cloud:
            result = GuardResult(
                decision=GuardDecision.BLOCK,
                violation_type=ViolationType.NO_CLOUD_FLAG,
                reason="Message marked with no_cloud=true - blocking cloud transmission",
                risk_score=1.0
            )
            self._log_violation(result, content, destination)
            return result
        
        # Step 2: Check whitelist for safe phrases first
        if self._is_safe_phrase(content):
            processing_time = (time.time() - start_time) * 1000
            result = GuardResult(
                decision=GuardDecision.ALLOW,
                violation_type=None,
                reason="Content on safe phrase whitelist",
                risk_score=0.0,
                metadata={'processing_time_ms': processing_time}
            )
            self.metrics['allows'] += 1
            logger.debug(f"✅ Guard ALLOW (whitelist) in {processing_time:.1f}ms")
            return result
        
        # Step 3: Check for private content patterns
        pii_result = self._check_pii_patterns(content)
        if pii_result.decision == GuardDecision.BLOCK:
            self._log_violation(pii_result, content, destination)
            return pii_result
            
        # Step 4: Check for tool-related content
        if isinstance(message, dict):
            tool_result = self._check_tool_content(message)
            if tool_result.decision == GuardDecision.BLOCK:
                self._log_violation(tool_result, content, destination)
                return tool_result
        
        # Step 5: Check for private keywords
        keyword_result = self._check_private_keywords(content)
        if keyword_result.decision != GuardDecision.ALLOW:
            if keyword_result.decision == GuardDecision.BLOCK:
                self._log_violation(keyword_result, content, destination)
            return keyword_result
        
        # Step 6: Allow safe content
        processing_time = (time.time() - start_time) * 1000
        
        result = GuardResult(
            decision=GuardDecision.ALLOW,
            violation_type=None,
            reason="Content passed all privacy checks",
            risk_score=0.0,
            metadata={'processing_time_ms': processing_time}
        )
        
        self.metrics['allows'] += 1
        logger.debug(f"✅ Guard ALLOW in {processing_time:.1f}ms")
        
        return result
    
    def _is_safe_phrase(self, content: str) -> bool:
        """Check if content is a known safe phrase"""
        safe_phrases = [
            # English safe phrases (output)
            "what time is it",
            "how is the weather today",
            "tell me a joke", 
            "what's 25 + 17",
            "explain quantum physics briefly",
            "i found some information",
            "there are several items",
            "the meeting is scheduled",
            "you have new messages",
            "weather in stockholm",
            "no result",
            "i'll check that locally",
            "processing your request",
            
            # Swedish safe phrases (input)
            "vad är klockan",
            "hur är vädret idag",
            "berätta ett skämt",
            "vad är 25 + 17",
            "förklara kvantfysik kort",
            "jag hittade information",
            "det finns flera objekt",
            "mötet är inbokat",
            "du har nya meddelanden",
            "väder i stockholm",
            "inget resultat",
            "jag kollar det lokalt"
        ]
        
        content_lower = content.lower().strip()
        
        # Direct match
        if content_lower in safe_phrases:
            return True
            
        # Partial match for safe phrases
        for phrase in safe_phrases:
            if phrase in content_lower and len(content_lower) < len(phrase) + 20:
                return True
                
        return False
    
    def _check_pii_patterns(self, content: str) -> GuardResult:
        """Check for PII patterns in content"""
        import re
        
        content_lower = content.lower()
        
        for pattern in self.blocked_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return GuardResult(
                    decision=GuardDecision.BLOCK,
                    violation_type=ViolationType.PII_DETECTED,
                    reason=f"PII pattern detected: {pattern[:50]}...",
                    risk_score=0.9
                )
        
        return GuardResult(
            decision=GuardDecision.ALLOW,
            violation_type=None,
            reason="No PII patterns detected"
        )
    
    def _check_tool_content(self, message: Dict) -> GuardResult:
        """Check for tool-related content that shouldn't go to cloud"""
        
        # Check for function call arguments
        if 'function_call' in message or 'tools' in message:
            return GuardResult(
                decision=GuardDecision.BLOCK,
                violation_type=ViolationType.FUNCTION_ARGUMENTS,
                reason="Function call content not allowed in cloud transmission",
                risk_score=0.95
            )
        
        # Check for raw tool results
        if 'tool_result' in message or 'raw_result' in message:
            return GuardResult(
                decision=GuardDecision.BLOCK,
                violation_type=ViolationType.RAW_TOOL_RESULT,
                reason="Raw tool results not allowed in cloud transmission",
                risk_score=0.95
            )
        
        # Check message type
        msg_type = message.get('type', '')
        if msg_type in ['tool_call', 'function_result', 'raw_data']:
            return GuardResult(
                decision=GuardDecision.BLOCK,
                violation_type=ViolationType.RAW_TOOL_RESULT,
                reason=f"Message type '{msg_type}' not allowed in cloud",
                risk_score=0.9
            )
        
        return GuardResult(
            decision=GuardDecision.ALLOW,
            violation_type=None,
            reason="No tool content violations"
        )
    
    def _check_private_keywords(self, content: str) -> GuardResult:
        """Check for private keywords"""
        content_lower = content.lower()
        
        for keyword in self.private_keywords:
            if keyword in content_lower:
                # Could be sanitized rather than blocked if context allows
                return GuardResult(
                    decision=GuardDecision.BLOCK,
                    violation_type=ViolationType.PRIVATE_CONTENT,
                    reason=f"Private keyword detected: {keyword}",
                    risk_score=0.7
                )
        
        return GuardResult(
            decision=GuardDecision.ALLOW,
            violation_type=None,
            reason="No private keywords detected"
        )
    
    def _log_violation(self, result: GuardResult, content: str, destination: str):
        """Log privacy violation for audit"""
        
        # Hash content for audit without storing actual data
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        violation_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'violation_type': result.violation_type.value if result.violation_type else None,
            'destination': destination,
            'content_hash': content_hash,
            'content_length': len(content),
            'reason': result.reason,
            'risk_score': result.risk_score
        }
        
        self.audit_log.append(violation_entry)
        
        # Keep audit log reasonable size
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-500:]
        
        # Update metrics
        self.metrics['blocks'] += 1
        self.metrics['privacy_leak_attempts'] += 1
        
        if result.violation_type:
            violation_key = result.violation_type.value
            self.metrics['violation_types'][violation_key] = \
                self.metrics['violation_types'].get(violation_key, 0) + 1
        
        logger.warning(f"🚫 Privacy violation blocked: {result.reason} "
                      f"(hash: {content_hash})")
    
    def create_safe_message_for_realtime(self, safe_summary: str, 
                                        session_id: str = None) -> Dict:
        """
        Create a safe message that can be sent to Realtime
        Only contains sanitized summary content
        """
        
        # Double-check the safe summary itself
        guard_result = self.check_outbound_message(safe_summary, "realtime")
        
        if guard_result.decision == GuardDecision.BLOCK:
            logger.error(f"🚫 Safe summary failed guard check: {guard_result.reason}")
            # Return ultra-safe fallback
            safe_summary = "I found some information. Would you like a summary?"
        
        message = {
            'type': 'local_result',
            'content': safe_summary,
            'timestamp': time.time() * 1000,
            'no_cloud': False,  # Explicitly mark as safe for cloud
        }
        
        if session_id:
            message['session_id'] = session_id
        
        # Final guard check on complete message
        final_check = self.check_outbound_message(message, "realtime")
        if final_check.decision != GuardDecision.ALLOW:
            logger.error(f"🚫 Final guard check failed for safe message!")
            return {
                'type': 'local_result',
                'content': "I processed your request.",
                'timestamp': time.time() * 1000,
                'no_cloud': False
            }
        
        return message
    
    def get_metrics(self) -> Dict:
        """Get guard metrics for monitoring"""
        total = self.metrics['total_checks']
        if total == 0:
            return self.metrics
        
        return {
            **self.metrics,
            'block_rate': (self.metrics['blocks'] / total) * 100,
            'allow_rate': (self.metrics['allows'] / total) * 100,
            'privacy_leak_rate': (self.metrics['privacy_leak_attempts'] / total) * 100
        }
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get recent audit log entries"""
        return self.audit_log[-limit:]
    
    def reset_metrics(self):
        """Reset metrics (for testing)"""
        self.metrics = {
            'total_checks': 0,
            'blocks': 0,
            'sanitizations': 0,
            'allows': 0,
            'violation_types': {},
            'privacy_leak_attempts': 0
        }
        self.audit_log = []
        logger.info("📊 Network Guard metrics reset")

# Global guard instance
_network_guard = None

def get_network_guard() -> NetworkGuard:
    """Get global network guard instance"""
    global _network_guard
    if _network_guard is None:
        _network_guard = NetworkGuard()
    return _network_guard

def check_cloud_safety(message: Union[Dict, str], 
                      destination: str = "realtime") -> GuardResult:
    """Convenience function for cloud safety check"""
    guard = get_network_guard()
    return guard.check_outbound_message(message, destination)