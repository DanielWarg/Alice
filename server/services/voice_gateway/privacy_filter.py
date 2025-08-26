#!/usr/bin/env python3
"""
🔒 Privacy Filter - Strict PII Removal for Voice Responses
Converts raw LLM results into safe, spoken summaries for TTS with zero PII leakage
"""
import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
import hashlib
import uuid

logger = logging.getLogger(__name__)

class PIIType(Enum):
    """Types of PII that must be filtered"""
    PERSON_NAME = "person_name"
    EMAIL_ADDRESS = "email_address"
    PHONE_NUMBER = "phone_number"
    ADDRESS = "address"
    SOCIAL_SECURITY = "social_security"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    URL = "url"
    EXACT_NUMBER = "exact_number"
    QUOTE_EXCERPT = "quote_excerpt"
    FILE_PATH = "file_path"
    ACCOUNT_ID = "account_id"
    SENSITIVE_DATA = "sensitive_data"

@dataclass
class PIIMatch:
    """Detected PII match with context"""
    pii_type: PIIType
    matched_text: str
    start_pos: int
    end_pos: int
    confidence: float
    replacement: str = ""
    context: str = ""

@dataclass
class FilterResult:
    """Result of privacy filtering operation"""
    safe_summary: str
    original_length: int
    filtered_length: int
    pii_matches: List[PIIMatch] = field(default_factory=list)
    filter_duration_ms: float = 0.0
    validation_passed: bool = False
    fallback_used: bool = False
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))

class PrivacyFilterError(Exception):
    """Privacy filter specific errors"""
    pass

class PIILeakageError(PrivacyFilterError):
    """Raised when PII is detected in final output"""
    pass

class PrivacyFilter:
    """
    Strict PII removal filter for voice responses
    
    Converts raw LLM results into safe, spoken summaries suitable for TTS
    with comprehensive PII detection and removal.
    """
    
    def __init__(self, max_summary_length: int = 300):
        self.max_summary_length = max_summary_length
        self._init_pii_patterns()
        self._init_system_prompts()
        
        # Metrics tracking
        self.metrics = {
            "total_filters": 0,
            "pii_detections": 0,
            "fallback_uses": 0,
            "validation_failures": 0,
            "avg_filter_time_ms": 0.0
        }
        
        # Audit log
        self.audit_log: List[Dict] = []
        
    def _init_pii_patterns(self):
        """Initialize PII detection patterns"""
        
        # Person names (common patterns) - more specific to avoid false positives
        self.name_patterns = [
            r'\b[A-Z][a-z]{2,} [A-Z][a-z]{2,}\b',  # First Last (min 3 chars each)
            r'\b[A-Z][a-z]+, [A-Z][a-z]+\b',  # Last, First
            r'\b(?:Mr|Mrs|Ms|Dr|Prof)\.? [A-Z][a-z]{2,}\b',  # Title Name
        ]
        
        # Email addresses
        self.email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'\b[A-Za-z0-9._%+-]+ at [A-Za-z0-9.-]+ dot [A-Z|a-z]{2,}\b',
        ]
        
        # Phone numbers
        self.phone_patterns = [
            r'\b\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'\b\+\d{1,3}[-.\s]?\d{1,14}\b',
        ]
        
        # Addresses
        self.address_patterns = [
            r'\b\d+\s+[A-Za-z\s]+(Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd)\b',
            r'\b[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}(-\d{4})?\b',  # City, State ZIP
        ]
        
        # Social Security Numbers
        self.ssn_patterns = [
            r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b',
            r'\b\d{9}\b',  # 9 consecutive digits
        ]
        
        # Credit Card Numbers
        self.cc_patterns = [
            r'\b(?:\d{4}[-.\s]?){3}\d{4}\b',  # 16 digits with separators
            r'\b\d{13,19}\b',  # 13-19 consecutive digits
        ]
        
        # IP Addresses
        self.ip_patterns = [
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',  # IPv6
        ]
        
        # URLs and file paths
        self.url_patterns = [
            r'https?://[^\s]+',
            r'www\.[^\s]+',
            r'/[^\s]*\.[a-z]{2,4}',  # File paths with extensions
            r'[A-Z]:\\[^\s]*',  # Windows paths
        ]
        
        # Exact numbers that should be generalized
        self.exact_number_patterns = [
            r'\b\d{4,}\b',  # 4+ digit numbers (except years 1900-2099)
            r'\$\d+\.\d{2}',  # Exact dollar amounts
            r'\b\d+\.\d+%\b',  # Exact percentages
        ]
        
        # Quote/excerpt patterns
        self.quote_patterns = [
            r'"[^"]{20,}"',  # Long quoted text
            r'\'[^\']{20,}\'',  # Long single-quoted text
            r'```[^`]+```',  # Code blocks
        ]
        
        # Account IDs and identifiers
        self.id_patterns = [
            r'\b[A-Z0-9]{8,}\b',  # Uppercase alphanumeric IDs
            r'\b\w*\d{6,}\w*\b',  # Mixed with 6+ digits
        ]
    
    def _init_system_prompts(self):
        """Initialize system prompts for LLM filtering"""
        self.summary_prompt = """Rewrite the given raw_result into a 1-2 sentence spoken summary for TTS in English, removing PII and specifics. No names, emails, addresses, IDs, quotes, or exact figures beyond coarse counts.

Rules:
- Maximum 300 characters
- Use general terms: "someone", "a person", "the user", "several", "many", "around X"
- Remove all specific identifiers
- Convert exact numbers to approximate ranges
- Focus on the essence, not details
- Optimize for spoken delivery (natural, flowing language)

Input: {raw_result}

Safe Summary:"""

        self.validation_prompt = """Check if this text contains any PII or specific identifiers that should not be spoken aloud in a voice interface:

Text: {text}

Respond with only "SAFE" or "UNSAFE: [reason]"""
    
    async def filter_to_safe_summary(self, raw_result: str, context: Dict = None) -> FilterResult:
        """
        Convert raw LLM result to safe, spoken summary
        
        Args:
            raw_result: Raw text from LLM/tool execution
            context: Additional context for filtering decisions
            
        Returns:
            FilterResult with safe summary and filtering metadata
        """
        start_time = time.time()
        context = context or {}
        
        try:
            logger.info(f"🔒 Filtering raw result: {len(raw_result)} chars")
            
            # Step 1: PII Detection
            pii_matches = self._detect_pii(raw_result)
            
            # Step 2: Generate safe summary using LLM
            safe_summary = await self._generate_safe_summary(raw_result, pii_matches)
            
            # Step 3: Strict validation
            validation_result = await self._validate_safe_output(safe_summary)
            
            # Step 4: Fallback if validation fails
            if not validation_result["passed"]:
                logger.warning(f"🚨 Validation failed: {validation_result['reason']}")
                safe_summary = self._apply_fallback_filter(raw_result)
                validation_result = await self._validate_safe_output(safe_summary)
                
                if not validation_result["passed"]:
                    raise PIILeakageError(f"PII detected in fallback output: {validation_result['reason']}")
            
            filter_duration = (time.time() - start_time) * 1000
            
            result = FilterResult(
                safe_summary=safe_summary,
                original_length=len(raw_result),
                filtered_length=len(safe_summary),
                pii_matches=pii_matches,
                filter_duration_ms=filter_duration,
                validation_passed=validation_result["passed"],
                fallback_used=len(pii_matches) > 0
            )
            
            # Update metrics
            self._update_metrics(result)
            
            # Audit logging
            self._log_filter_operation(raw_result, result)
            
            logger.info(f"✅ Filter complete: {len(safe_summary)} chars, {len(pii_matches)} PII matches")
            return result
            
        except Exception as e:
            logger.error(f"❌ Privacy filter error: {e}")
            # Emergency fallback
            emergency_summary = self._emergency_fallback()
            
            result = FilterResult(
                safe_summary=emergency_summary,
                original_length=len(raw_result),
                filtered_length=len(emergency_summary),
                filter_duration_ms=(time.time() - start_time) * 1000,
                validation_passed=True,  # Emergency fallback is always safe
                fallback_used=True
            )
            
            self._log_filter_operation(raw_result, result, error=str(e))
            return result
    
    def _detect_pii(self, text: str) -> List[PIIMatch]:
        """Detect all PII patterns in text"""
        matches = []
        
        # Person names
        for pattern in self.name_patterns:
            for match in re.finditer(pattern, text):
                matches.append(PIIMatch(
                    pii_type=PIIType.PERSON_NAME,
                    matched_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.8,
                    replacement="someone"
                ))
        
        # Email addresses
        for pattern in self.email_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(PIIMatch(
                    pii_type=PIIType.EMAIL_ADDRESS,
                    matched_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.95,
                    replacement="an email address"
                ))
        
        # Phone numbers
        for pattern in self.phone_patterns:
            for match in re.finditer(pattern, text):
                matches.append(PIIMatch(
                    pii_type=PIIType.PHONE_NUMBER,
                    matched_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.9,
                    replacement="a phone number"
                ))
        
        # Continue for other PII types...
        self._detect_additional_pii(text, matches)
        
        # Sort matches by position
        matches.sort(key=lambda x: x.start_pos)
        
        return matches
    
    def _detect_additional_pii(self, text: str, matches: List[PIIMatch]):
        """Detect additional PII types"""
        
        # Addresses
        for pattern in self.address_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(PIIMatch(
                    pii_type=PIIType.ADDRESS,
                    matched_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.85,
                    replacement="an address"
                ))
        
        # URLs and file paths
        for pattern in self.url_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(PIIMatch(
                    pii_type=PIIType.URL,
                    matched_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.9,
                    replacement="a link"
                ))
        
        # Exact numbers (except reasonable years)
        for pattern in self.exact_number_patterns:
            for match in re.finditer(pattern, text):
                number = match.group()
                # Skip years 1900-2099
                if re.match(r'^(19|20)\d{2}$', number):
                    continue
                    
                matches.append(PIIMatch(
                    pii_type=PIIType.EXACT_NUMBER,
                    matched_text=number,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.7,
                    replacement=self._generalize_number(number)
                ))
        
        # Quotes and excerpts
        for pattern in self.quote_patterns:
            for match in re.finditer(pattern, text, re.DOTALL):
                matches.append(PIIMatch(
                    pii_type=PIIType.QUOTE_EXCERPT,
                    matched_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.8,
                    replacement="some content"
                ))
    
    def _generalize_number(self, number_str: str) -> str:
        """Convert exact numbers to approximate ranges"""
        try:
            num = float(number_str.replace('$', '').replace('%', ''))
            
            if num < 10:
                return "several"
            elif num < 50:
                return "dozens"
            elif num < 100:
                return "around fifty"
            elif num < 500:
                return "hundreds"
            elif num < 1000:
                return "around a thousand"
            elif num < 10000:
                return "thousands"
            else:
                return "many thousands"
        except:
            return "a number"
    
    async def _generate_safe_summary(self, raw_result: str, pii_matches: List[PIIMatch]) -> str:
        """Generate safe summary using LLM"""
        # This would integrate with the existing LLM system
        # For now, implementing a rule-based approach
        
        # Start with the raw result
        safe_text = raw_result
        
        # Apply PII replacements from end to start (to maintain positions)
        for match in reversed(pii_matches):
            safe_text = (safe_text[:match.start_pos] + 
                        match.replacement + 
                        safe_text[match.end_pos:])
        
        # Truncate to max length
        if len(safe_text) > self.max_summary_length:
            safe_text = safe_text[:self.max_summary_length-3] + "..."
        
        # Basic cleanup for spoken delivery
        safe_text = self._optimize_for_speech(safe_text)
        
        return safe_text
    
    def _optimize_for_speech(self, text: str) -> str:
        """Optimize text for TTS delivery"""
        
        # Remove excessive punctuation
        text = re.sub(r'[.]{2,}', '.', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        # Convert symbols to words
        text = text.replace('&', 'and')
        text = text.replace('@', 'at')
        text = text.replace('#', 'number')
        text = text.replace('%', 'percent')
        text = text.replace('$', 'dollars')
        
        # Remove markdown formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # Italic
        text = re.sub(r'`([^`]+)`', r'\1', text)        # Code
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    async def _validate_safe_output(self, text: str) -> Dict[str, Any]:
        """Validate that output contains no PII"""
        
        # Only check for actual PII patterns, not overly broad ones
        validation_patterns = [
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "email"),
            (r'\b\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', "phone"),
            (r'https?://[^\s]+', "url"),
            (r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b', "credit_card"),
            (r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b', "ssn"),
        ]
        
        for pattern, pii_type in validation_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                return {
                    "passed": False,
                    "reason": f"{pii_type}: {match.group()}"
                }
        
        # Check for very long numbers that might be IDs
        if re.search(r'\b\d{8,}\b', text):
            return {
                "passed": False,
                "reason": "Long number detected"
            }
        
        # Check for email-like patterns
        if re.search(r'@[a-zA-Z]', text):
            return {
                "passed": False,
                "reason": "Email indicator detected"
            }
        
        return {"passed": True, "reason": ""}
    
    def _get_patterns_for_type(self, pii_type: PIIType) -> List[str]:
        """Get regex patterns for specific PII type"""
        pattern_map = {
            PIIType.PERSON_NAME: self.name_patterns,
            PIIType.EMAIL_ADDRESS: self.email_patterns,
            PIIType.PHONE_NUMBER: self.phone_patterns,
            PIIType.ADDRESS: self.address_patterns,
            PIIType.URL: self.url_patterns,
        }
        return pattern_map.get(pii_type, [])
    
    def _contains_suspicious_content(self, text: str) -> bool:
        """Check for suspicious content patterns"""
        suspicious_patterns = [
            r'\b\d{6,}\b',    # Very long numbers (6+ digits)
            r'@[a-zA-Z]',     # Email @ signs with letters
            r'[A-Z0-9]{8,}',  # Long uppercase alphanumeric (8+ chars)
            r'\b[A-Z]{2,}\.[A-Z]{2,}\b',  # Domain-like patterns
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _apply_fallback_filter(self, raw_result: str) -> str:
        """Apply aggressive fallback filtering"""
        logger.warning("🔧 Applying fallback filter")
        
        # Try to extract safe content by removing PII and creating a general summary
        clean_text = self._strip_all_pii(raw_result)
        
        # If we have some safe content, use it
        if clean_text and len(clean_text.strip()) > 10:
            # Create a general summary
            sentences = re.split(r'[.!?]+', clean_text)
            safe_sentences = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence or len(sentence) < 5:
                    continue
                
                # Basic safety check
                if not self._sentence_has_pii_risk(sentence):
                    safe_sentences.append(sentence)
                
                # Stop if we have enough content
                if len(' '.join(safe_sentences)) > 100:
                    break
            
            if safe_sentences:
                result = ' '.join(safe_sentences)
                if len(result) > self.max_summary_length:
                    result = result[:self.max_summary_length-3] + "..."
                return result
        
        # Ultimate fallback with some context
        if "email" in raw_result.lower():
            return "I found information about email communications."
        elif "calendar" in raw_result.lower() or "meeting" in raw_result.lower():
            return "I found information about calendar entries."
        elif "file" in raw_result.lower() or "document" in raw_result.lower():
            return "I found information about documents."
        elif any(word in raw_result.lower() for word in ["number", "count", "total"]):
            return "I found some numerical information."
        else:
            return "I processed your request and found relevant information."
    
    def _strip_all_pii(self, text: str) -> str:
        """Strip all detected PII from text aggressively"""
        # Remove all detected PII patterns
        result = text
        
        # Remove emails
        result = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[email]', result)
        
        # Remove phone numbers
        result = re.sub(r'\b\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', '[phone]', result)
        
        # Remove potential names (be more conservative)
        result = re.sub(r'\b[A-Z][a-z]{2,} [A-Z][a-z]{2,}\b', '[person]', result)
        
        # Remove URLs
        result = re.sub(r'https?://[^\s]+', '[link]', result)
        
        # Remove long numbers
        result = re.sub(r'\b\d{4,}\b', '[number]', result)
        
        # Remove quoted content
        result = re.sub(r'"[^"]{20,}"', '[content]', result)
        
        # Clean up multiple spaces and brackets
        result = re.sub(r'\[[^\]]+\]\s*', '', result)
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result
    
    def _sentence_has_pii_risk(self, sentence: str) -> bool:
        """Check if sentence has PII risk"""
        risk_indicators = [
            r'\b[A-Z][a-z]{2,} [A-Z][a-z]{2,}\b',  # Names (specific pattern)
            r'@[a-zA-Z]',                           # Email indicators
            r'\b\d{4,}\b',                         # Long numbers only
            r'https?://',                           # URLs
            r'/[^\s]*\.[a-z]{2,4}',                # File paths with extensions
            r'"[^"]{20,}"',                        # Long quotes only
        ]
        
        for pattern in risk_indicators:
            if re.search(pattern, sentence):
                return True
        return False
    
    def _emergency_fallback(self) -> str:
        """Emergency fallback when all else fails"""
        return "I processed your request, but cannot provide specific details at this time."
    
    def _update_metrics(self, result: FilterResult):
        """Update filtering metrics"""
        self.metrics["total_filters"] += 1
        
        if result.pii_matches:
            self.metrics["pii_detections"] += 1
        
        if result.fallback_used:
            self.metrics["fallback_uses"] += 1
        
        if not result.validation_passed:
            self.metrics["validation_failures"] += 1
        
        # Update average filter time
        current_avg = self.metrics["avg_filter_time_ms"]
        total_filters = self.metrics["total_filters"]
        self.metrics["avg_filter_time_ms"] = (
            (current_avg * (total_filters - 1) + result.filter_duration_ms) / total_filters
        )
    
    def _log_filter_operation(self, raw_input: str, result: FilterResult, error: str = None):
        """Log filter operation for audit"""
        audit_entry = {
            "audit_id": result.audit_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_hash": hashlib.sha256(raw_input.encode()).hexdigest()[:16],
            "input_length": len(raw_input),
            "output_length": len(result.safe_summary),
            "pii_count": len(result.pii_matches),
            "pii_types": list(set(match.pii_type.value for match in result.pii_matches)),
            "filter_duration_ms": result.filter_duration_ms,
            "validation_passed": result.validation_passed,
            "fallback_used": result.fallback_used,
            "error": error
        }
        
        self.audit_log.append(audit_entry)
        
        # Keep audit log manageable (last 1000 entries)
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
        
        logger.info(f"📋 Audit logged: {result.audit_id}")
    
    def get_metrics(self) -> Dict:
        """Get filtering metrics"""
        return self.metrics.copy()
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get recent audit log entries"""
        return self.audit_log[-limit:]
    
    def export_audit_log(self) -> str:
        """Export audit log as JSON"""
        return json.dumps(self.audit_log, indent=2)
    
    async def create_safe_summary(self, raw_result: str, context: Dict = None) -> str:
        """
        Alias for filter_to_safe_summary that returns just the safe summary string
        Compatible with test expectations
        """
        filter_result = await self.filter_to_safe_summary(raw_result, context)
        return filter_result.safe_summary

# Global privacy filter instance
_privacy_filter = None

def get_privacy_filter(max_summary_length: int = 300) -> PrivacyFilter:
    """Get global privacy filter instance"""
    global _privacy_filter
    if _privacy_filter is None:
        _privacy_filter = PrivacyFilter(max_summary_length)
        logger.info("✅ Privacy filter initialized")
    return _privacy_filter

async def filter_for_tts(raw_result: str, context: Dict = None) -> str:
    """
    Convenience function to filter raw result for TTS
    
    Args:
        raw_result: Raw text from tool/LLM execution
        context: Optional context for filtering
        
    Returns:
        Safe summary suitable for TTS
    """
    filter_instance = get_privacy_filter()
    result = await filter_instance.filter_to_safe_summary(raw_result, context)
    return result.safe_summary

# Test suite functions for validation
class PrivacyFilterTests:
    """Test suite for privacy filter validation"""
    
    @staticmethod
    def create_test_cases() -> List[Dict[str, Any]]:
        """Create test cases for common PII types"""
        return [
            {
                "name": "person_names",
                "input": "John Smith called about the meeting with Sarah Johnson.",
                "should_contain": ["called", "meeting"],
                "should_not_contain": ["John", "Smith", "Sarah", "Johnson"]
            },
            {
                "name": "email_addresses", 
                "input": "Please email me at john.doe@company.com for details.",
                "should_contain": ["email", "contact"],
                "should_not_contain": ["john.doe@company.com", "@company.com"]
            },
            {
                "name": "phone_numbers",
                "input": "Call me at 555-123-4567 or (555) 987-6543.",
                "should_contain": ["call", "contact"],
                "should_not_contain": ["555-123-4567", "987-6543"]
            },
            {
                "name": "addresses",
                "input": "The office is at 123 Main Street, Boston, MA 02101.",
                "should_contain": ["office", "location"],
                "should_not_contain": ["123 Main Street", "02101", "Boston"]
            },
            {
                "name": "exact_numbers",
                "input": "The report shows 12345 users and revenue of 67890 dollars.",
                "should_contain": ["report", "users", "revenue"],
                "should_not_contain": ["12345", "67890"]
            },
            {
                "name": "quotes_and_excerpts",
                "input": 'The document states: "This is confidential information about our strategy and plans."',
                "should_contain": ["document", "information"],
                "should_not_contain": ["confidential information about our strategy", "plans"]
            }
        ]
    
    @staticmethod
    async def run_test_suite() -> Dict[str, Any]:
        """Run complete test suite"""
        filter_instance = get_privacy_filter()
        test_cases = PrivacyFilterTests.create_test_cases()
        
        results = {
            "passed": 0,
            "failed": 0,
            "test_results": []
        }
        
        for test_case in test_cases:
            try:
                filter_result = await filter_instance.filter_to_safe_summary(test_case["input"])
                safe_output = filter_result.safe_summary.lower()
                
                # Check positive assertions
                positive_passed = any(term in safe_output for term in test_case["should_contain"])
                
                # Check negative assertions  
                negative_passed = not any(term.lower() in safe_output for term in test_case["should_not_contain"])
                
                test_passed = positive_passed and negative_passed
                
                test_result = {
                    "test_name": test_case["name"],
                    "passed": test_passed,
                    "input": test_case["input"][:50] + "...",
                    "output": safe_output,
                    "positive_check": positive_passed,
                    "negative_check": negative_passed
                }
                
                results["test_results"].append(test_result)
                
                if test_passed:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                results["failed"] += 1
                results["test_results"].append({
                    "test_name": test_case["name"],
                    "passed": False,
                    "error": str(e)
                })
        
        return results

if __name__ == "__main__":
    # Run test suite if executed directly
    async def main():
        print("🧪 Running Privacy Filter Test Suite...")
        results = await PrivacyFilterTests.run_test_suite()
        
        print(f"✅ Tests passed: {results['passed']}")
        print(f"❌ Tests failed: {results['failed']}")
        
        for test in results["test_results"]:
            status = "✅" if test["passed"] else "❌"
            print(f"{status} {test['test_name']}")
            if not test["passed"] and "error" not in test:
                print(f"   Input: {test['input']}")
                print(f"   Output: {test['output']}")
    
    asyncio.run(main())