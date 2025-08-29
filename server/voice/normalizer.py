"""
Voice Text Normalizer - Pre/Post processing for Swedish→English translation
Handles time expressions, canonicalization, and cache optimization.
"""

import re
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class NormalizationResult:
    """Result from text normalization"""
    text: str
    changes_made: bool
    changed_patterns: list

class SwedishPreNormalizer:
    """Pre-processes Swedish text before LLM translation"""
    
    def __init__(self):
        # Time expression patterns (Swedish → English)
        self.time_patterns = [
            # Relative time
            (r'\bom (\d+) minuter?\b', r'in \1 minutes'),
            (r'\bom (\d+) minut\b', r'in \1 minute'),
            (r'\bom (\d+) timmar?\b', r'in \1 hours'), 
            (r'\bom (\d+) timme\b', r'in \1 hour'),
            (r'\bom (\d+) dagar?\b', r'in \1 days'),
            (r'\bom (\d+) dag\b', r'in \1 day'),
            (r'\bom (\d+) veckor?\b', r'in \1 weeks'),
            (r'\bom (\d+) vecka\b', r'in \1 week'),
            
            # Absolute time references
            (r'\bimorgon\b', r'tomorrow'),
            (r'\bidag\b', r'today'),
            (r'\bigår\b', r'yesterday'),
            (r'\binatt\b', r'tonight'),
            (r'\bi kväll\b', r'tonight'),
            (r'\bi morse\b', r'this morning'),
            (r'\bi förmiddags\b', r'this morning'),
            (r'\bi eftermiddag\b', r'this afternoon'),
            
            # Weekdays
            (r'\bmåndag\b', r'Monday'),
            (r'\btisdag\b', r'Tuesday'), 
            (r'\bonsdag\b', r'Wednesday'),
            (r'\btorsdag\b', r'Thursday'),
            (r'\bfredag\b', r'Friday'),
            (r'\blördag\b', r'Saturday'),
            (r'\bsöndag\b', r'Sunday'),
            
            # Months
            (r'\bjanuari\b', r'January'),
            (r'\bfebruari\b', r'February'),
            (r'\bmars\b', r'March'), 
            (r'\bapril\b', r'April'),
            (r'\bmaj\b', r'May'),
            (r'\bjuni\b', r'June'),
            (r'\bjuli\b', r'July'),
            (r'\baugusti\b', r'August'),
            (r'\bseptember\b', r'September'),
            (r'\boktober\b', r'October'),
            (r'\bnovember\b', r'November'),
            (r'\bdecember\b', r'December'),
            
            # Time formats
            (r'\bkl\.?\s*(\d{1,2}):(\d{2})\b', r'at \1:\2'),
            (r'\bklockan\s+(\d{1,2}):(\d{2})\b', r'at \1:\2'),
            (r'\bklockan\s+(\d{1,2})\b', r'at \1:00'),
        ]
        
        # Common Swedish→English word mappings that help translation
        self.word_mappings = [
            (r'\bmöte\b', r'meeting'),
            (r'\bmöten\b', r'meetings'),
            (r'\bbatteri\b', r'battery'),
            (r'\buppdatering\b', r'update'),
            (r'\btillgänglig\b', r'available'),
            (r'\binstallation\b', r'installation'),
            (r'\bprojekt\b', r'project'),
            (r'\bkollega\b', r'colleague'),
            (r'\bkollegor\b', r'colleagues'),
            (r'\bmail\b', r'email'),  # Normalize to "email"
        ]
    
    def normalize(self, swedish_text: str) -> NormalizationResult:
        """Pre-normalize Swedish text for better LLM translation"""
        
        original_text = swedish_text
        text = swedish_text.strip()
        changes_made = []
        
        # Apply time patterns first (most important for accuracy)
        for pattern, replacement in self.time_patterns:
            new_text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            if new_text != text:
                changes_made.append(f"Time: {pattern}")
                text = new_text
        
        # Apply word mappings (helps with consistency)
        for pattern, replacement in self.word_mappings:
            new_text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            if new_text != text:
                changes_made.append(f"Word: {pattern}")
                text = new_text
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return NormalizationResult(
            text=text,
            changes_made=len(changes_made) > 0,
            changed_patterns=changes_made
        )

class EnglishPostNormalizer:
    """Post-processes English text from LLM for cache optimization and consistency"""
    
    def __init__(self):
        # Number word to digit mappings (for cache consistency)
        self.number_words = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
            'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13',
            'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 
            'seventeen': '17', 'eighteen': '18', 'nineteen': '19',
            'twenty': '20', 'thirty': '30', 'forty': '40', 'fifty': '50',
            'sixty': '60', 'seventy': '70', 'eighty': '80', 'ninety': '90',
            'hundred': '100', 'thousand': '1000'
        }
        
        # Standardize common terms for cache consistency
        self.standardizations = [
            # Email standardization
            (r'\bemail\b', 'email'),
            (r'\be-mail\b', 'email'), 
            (r'\bEmail\b', 'email'),
            (r'\bE-mail\b', 'email'),
            (r'\bmails\b', 'emails'),
            (r'\be-mails\b', 'emails'),
            
            # Meeting standardization
            (r'\bMeeting\b', 'meeting'),
            (r'\bmeetings\b', 'meetings'),
            (r'\bMeetings\b', 'meetings'),
            
            # Time standardizations
            (r'\bAM\b', 'AM'),
            (r'\bPM\b', 'PM'),
            (r'\ba\.m\.\b', 'AM'),
            (r'\bp\.m\.\b', 'PM'),
            
            # Percentage standardization
            (r'(\d+)\s*percent', r'\1%'),
            (r'(\d+)\s*per cent', r'\1%'),
        ]
    
    def normalize(self, english_text: str) -> NormalizationResult:
        """Post-normalize English text for cache optimization"""
        
        original_text = english_text
        text = english_text.strip()
        changes_made = []
        
        # 1. Convert number words to digits (most important for cache)
        for word, digit in self.number_words.items():
            # Pattern: word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(word) + r'\b'
            new_text = re.sub(pattern, digit, text, flags=re.IGNORECASE)
            if new_text != text:
                changes_made.append(f"Number: {word}→{digit}")
                text = new_text
        
        # 2. Handle compound numbers (twenty-one → 21, etc.)
        compound_patterns = [
            (r'\btwenty[- ](\w+)\b', lambda m: f"2{self.number_words.get(m.group(1), m.group(1))}"),
            (r'\bthirty[- ](\w+)\b', lambda m: f"3{self.number_words.get(m.group(1), m.group(1))}"),
            (r'\bforty[- ](\w+)\b', lambda m: f"4{self.number_words.get(m.group(1), m.group(1))}"),
            (r'\bfifty[- ](\w+)\b', lambda m: f"5{self.number_words.get(m.group(1), m.group(1))}"),
            (r'\bsixty[- ](\w+)\b', lambda m: f"6{self.number_words.get(m.group(1), m.group(1))}"),
            (r'\bseventy[- ](\w+)\b', lambda m: f"7{self.number_words.get(m.group(1), m.group(1))}"),
            (r'\beighty[- ](\w+)\b', lambda m: f"8{self.number_words.get(m.group(1), m.group(1))}"),
            (r'\bninety[- ](\w+)\b', lambda m: f"9{self.number_words.get(m.group(1), m.group(1))}"),
        ]
        
        for pattern, replacement in compound_patterns:
            new_text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            if new_text != text:
                changes_made.append("Compound number")
                text = new_text
        
        # 3. Apply standardizations
        for pattern, replacement in self.standardizations:
            new_text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            if new_text != text:
                changes_made.append(f"Standard: {pattern}")
                text = new_text
        
        # 4. Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 5. Ensure proper sentence ending
        if text and not text.endswith(('.', '!', '?')):
            text += '.'
            changes_made.append("Added period")
        
        # 6. Capitalize first letter
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
            changes_made.append("Capitalized")
        
        return NormalizationResult(
            text=text,
            changes_made=len(changes_made) > 0,
            changed_patterns=changes_made
        )

class TextComplexityAnalyzer:
    """Analyzes text complexity to route to appropriate LLM"""
    
    def __init__(self):
        # Patterns that indicate complexity requiring full LLM
        self.complex_patterns = [
            r'\b(datum|tid|klockan|möte|schema|bokning)\b',  # Time/scheduling
            r'\b(projekt|rapport|presentation|dokument)\b',   # Work context  
            r'\b(namn|personer|företag|adress)\b',           # Proper nouns
            r'\b(email|mail|meddelande|brev)\b',            # Communications
            r'\b(beräkna|räkna|analysera|jämför)\b',        # Analysis
            r'[A-ZÅÄÖ][a-zåäö]*-[A-ZÅÄÖ][a-zåäö]*',       # Hyphenated names
            r'\b[A-ZÅÄÖ][a-zåäö]*\s+[A-ZÅÄÖ][a-zåäö]*\b', # Proper names
            r'\d{1,2}:\d{2}',                               # Time formats
            r'\b\d{1,2}/\d{1,2}\b',                        # Date formats
        ]
        
        # Simple patterns that can use fast LLM
        self.simple_indicators = [
            r'^\w+\s+(är|har|kan|ska|vill|behöver)\b',      # Simple questions
            r'^(hej|hallå|tack|okej|bra|dåligt)\b',        # Greetings/simple
            r'^(ja|nej|kanske|säkert)\b',                   # Yes/no responses
        ]
    
    def analyze(self, swedish_text: str) -> Dict[str, any]:
        """Analyze text complexity for LLM routing"""
        
        text = swedish_text.lower()
        char_count = len(text)
        word_count = len(text.split())
        
        # Check for complex patterns
        complexity_score = 0
        complex_matches = []
        
        for pattern in self.complex_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                complexity_score += 1
                complex_matches.append(pattern)
        
        # Check for simple indicators
        simple_score = 0
        simple_matches = []
        
        for pattern in self.simple_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                simple_score += 1
                simple_matches.append(pattern)
        
        # Decision logic
        use_fast_llm = (
            char_count <= 80 and 
            word_count <= 12 and
            complexity_score == 0 and
            simple_score > 0
        ) or (
            char_count <= 50 and
            complexity_score <= 1
        )
        
        return {
            "char_count": char_count,
            "word_count": word_count, 
            "complexity_score": complexity_score,
            "simple_score": simple_score,
            "use_fast_llm": use_fast_llm,
            "complex_patterns": complex_matches,
            "simple_patterns": simple_matches,
            "reason": self._get_routing_reason(use_fast_llm, char_count, complexity_score, simple_score)
        }
    
    def _get_routing_reason(self, use_fast: bool, chars: int, complex: int, simple: int) -> str:
        """Get human-readable routing reason"""
        if use_fast:
            if chars <= 50:
                return f"Short text ({chars} chars)"
            elif complex == 0 and simple > 0:
                return f"Simple pattern detected ({simple} indicators)"
            else:
                return "Low complexity"
        else:
            if chars > 80:
                return f"Long text ({chars} chars)"
            elif complex > 0:
                return f"Complex patterns ({complex} detected)"
            else:
                return "Default to full LLM"

# Convenience functions for orchestrator
def pre_normalize_swedish(text: str) -> Tuple[str, bool, list]:
    """Pre-normalize Swedish text before LLM"""
    normalizer = SwedishPreNormalizer()
    result = normalizer.normalize(text)
    return result.text, result.changes_made, result.changed_patterns

def post_normalize_english(text: str) -> Tuple[str, bool, list]:
    """Post-normalize English text after LLM"""  
    normalizer = EnglishPostNormalizer()
    result = normalizer.normalize(text)
    return result.text, result.changes_made, result.changed_patterns

def analyze_text_complexity(text: str) -> Dict[str, any]:
    """Analyze text to determine LLM routing"""
    analyzer = TextComplexityAnalyzer()
    return analyzer.analyze(text)

# Test function
def test_normalization():
    """Test the normalization functions"""
    
    test_cases = [
        "Möte med Anna-Lena om 15 minuter",
        "Batteri lågt - three procent kvar", 
        "Du har two nya mail från kollegan",
        "Boka frisörtid på måndag kl 14:30",
        "Hej Alice hur mår du idag",
        "Påminn mig imorgon att ringa",
    ]
    
    print("🧪 Testing Normalization")
    print("=" * 50)
    
    pre_normalizer = SwedishPreNormalizer()
    post_normalizer = EnglishPostNormalizer() 
    analyzer = TextComplexityAnalyzer()
    
    for text in test_cases:
        print(f"\n🇸🇪 Original: '{text}'")
        
        # Pre-normalize
        pre_result = pre_normalizer.normalize(text)
        print(f"🔧 Pre-norm: '{pre_result.text}'")
        if pre_result.changes_made:
            print(f"   Changes: {pre_result.changed_patterns}")
        
        # Analyze complexity
        analysis = analyzer.analyze(text)
        llm_choice = "7B (fast)" if analysis["use_fast_llm"] else "20B (full)"
        print(f"🧠 LLM Route: {llm_choice} - {analysis['reason']}")
        
        # Simulate English output and post-normalize
        if "batteri" in text.lower():
            english_sim = "Battery low - three percent remaining"
        elif "mail" in text.lower():
            english_sim = "You have two new emails from colleague"
        else:
            english_sim = f"Simulated translation of: {pre_result.text}"
        
        post_result = post_normalizer.normalize(english_sim)
        print(f"🇬🇧 Post-norm: '{post_result.text}'")
        if post_result.changes_made:
            print(f"   Changes: {post_result.changed_patterns}")

if __name__ == "__main__":
    test_normalization()