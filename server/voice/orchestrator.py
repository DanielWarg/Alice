"""
Voice Orchestrator - Translates Swedish input to English speech text using GPT-OSS.
Handles segmentation for long content and enforces strict output contract.
"""

import json
import time
import re
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from .input_processor import InputPackage
from ..llm.ollama import OllamaAdapter

@dataclass
class VoiceOutput:
    """Structured output from orchestrator"""
    speak_text_en: str      # English text for TTS
    screen_text_sv: str     # Swedish text for HUD display  
    style: str              # neutral, cheerful, formal
    rate: float             # Speech rate multiplier (0.8-1.2)
    segments: List[str] = None  # For long content
    is_summary: bool = False    # True if this is a TL;DR
    meta: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.segments is None:
            self.segments = []
        if self.meta is None:
            self.meta = {}

class VoiceOrchestrator:
    """
    Orchestrator that translates Swedish to English using local GPT-OSS.
    Enforces strict output contract and handles segmentation for long content.
    """
    
    def __init__(self):
        self.llm = OllamaAdapter()
        self.max_segment_length = 320  # Characters per segment
        self.max_total_length = 2000   # Before requiring summary
        
        # Translation prompts
        self.system_prompt = """Du är Alice's voice orchestrator. Din uppgift är att översätta svensk text till idiomatisk engelska för röstuppläsning.

REGLER (VIKTIGT - följ exakt):
1. Översätt ALLTID till engelska - ingen svensk text i output
2. Behåll namn, datum, siffror precis som i originalet
3. Använd korta, kompletta meningar som slutar med punkt
4. Max 320 tecken per segment för snabb TTS
5. Ingen förklaring eller kommentarer - bara översättning
6. Gör texten talvänlig (undvik parenteser, komplexa bisatser)

OUTPUT FORMAT (JSON):
{
  "speak_text_en": "Exact English text for TTS",
  "style": "neutral|cheerful|formal", 
  "rate": 1.0
}

Exempel:
Svensk input: "Hej! Möte med Anna imorgon kl 14:00 om budget."
Output: {"speak_text_en": "Hi! Meeting with Anna tomorrow at 2 PM about budget.", "style": "neutral", "rate": 1.0}"""

    async def process(self, input_package: InputPackage) -> VoiceOutput:
        """
        Main processing method - translates Swedish input to English voice output.
        Handles segmentation for long content automatically.
        """
        start_time = time.time()
        
        # Import performance monitor
        from .performance_monitor import performance_monitor
        
        # Determine if segmentation is needed
        needs_segmentation = (
            len(input_package.text_sv) > self.max_total_length or
            input_package.source_type == "email"
        )
        
        if needs_segmentation:
            return await self._process_with_segmentation(input_package, start_time)
        else:
            return await self._process_single(input_package, start_time)
    
    async def _process_single(self, input_package: InputPackage, start_time: float) -> VoiceOutput:
        """Process short text in single request"""
        
        # Build prompt with context
        prompt = self._build_prompt(input_package.text_sv, input_package.source_type)
        
        try:
            # Call GPT-OSS for translation
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.chat(messages)
            
            if not response.text:
                raise Exception(f"LLM returned empty response")
            
            # Parse and validate response
            voice_data = self._parse_llm_response(response.text)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create final output
            voice_output = VoiceOutput(
                speak_text_en=voice_data["speak_text_en"],
                screen_text_sv=input_package.text_sv,
                style=voice_data.get("style", "neutral"),
                rate=voice_data.get("rate", 1.0),
                meta={
                    "processing_time": processing_time,
                    "source_type": input_package.source_type,
                    "char_count": len(voice_data["speak_text_en"])
                }
            )
            
            # Validate output
            self._validate_output(voice_output)
            
            # Record performance metric
            performance_monitor.record_voice_request(
                source_type=input_package.source_type,
                text_length=len(input_package.text_sv),
                processing_stages={"translation": processing_time},
                total_latency=processing_time,
                success=True,
                meta={"stage": "translation_only"}
            )
            
            return voice_output
            
        except Exception as e:
            # Record failed metric
            performance_monitor.record_voice_request(
                source_type=input_package.source_type,
                text_length=len(input_package.text_sv),
                processing_stages={"translation": time.time() - start_time},
                total_latency=time.time() - start_time,
                success=False,
                error=str(e),
                meta={"stage": "translation_failed"}
            )
            # Fallback to simple translation if LLM fails
            return self._create_fallback_output(input_package, str(e), start_time)
    
    async def _process_with_segmentation(self, input_package: InputPackage, start_time: float) -> VoiceOutput:
        """Process long content with summary + segmentation"""
        
        # First, create a summary for immediate playback
        summary_prompt = self._build_summary_prompt(input_package.text_sv, input_package.source_type)
        
        try:
            # Get summary first (highest priority)
            messages = [{"role": "user", "content": summary_prompt}]
            summary_response = await self.llm.chat(messages)
            
            if not summary_response.text:
                raise Exception(f"Summary failed: empty response")
            
            summary_data = self._parse_llm_response(summary_response.text)
            
            # Create segments for the rest (we'll process these later if needed)
            segments = self._create_segments(input_package.text_sv)
            
            voice_output = VoiceOutput(
                speak_text_en=summary_data["speak_text_en"],
                screen_text_sv=input_package.text_sv,
                style=summary_data.get("style", "neutral"),
                rate=summary_data.get("rate", 1.0),
                segments=segments,
                is_summary=True,
                meta={
                    "processing_time": time.time() - start_time,
                    "source_type": input_package.source_type,
                    "has_segments": len(segments) > 0,
                    "total_segments": len(segments)
                }
            )
            
            self._validate_output(voice_output)
            return voice_output
            
        except Exception as e:
            return self._create_fallback_output(input_package, str(e), start_time)
    
    def _build_prompt(self, swedish_text: str, source_type: str) -> str:
        """Build translation prompt with context"""
        
        # Add source-specific instructions
        source_instructions = {
            "chat": "Casual conversational tone.",
            "email": "Professional but friendly tone.", 
            "calendar": "Clear, time-focused information.",
            "notification": "Brief and direct.",
            "command": "Acknowledge the action clearly."
        }
        
        instruction = source_instructions.get(source_type, "Neutral tone.")
        
        return f"""{self.system_prompt}

KONTEXT: {source_type} - {instruction}

SVENSK TEXT:
{swedish_text}

JSON OUTPUT:"""

    def _build_summary_prompt(self, swedish_text: str, source_type: str) -> str:
        """Build prompt for summary/TL;DR generation"""
        
        return f"""{self.system_prompt}

SPECIELL UPPGIFT: Skapa en KORT sammanfattning (1-2 meningar, max 200 tecken).
Detta är första ljudet användaren hör - gör det informativt och koncist.

KONTEXT: {source_type} - behöver snabb sammanfattning

SVENSK TEXT:
{swedish_text}

JSON OUTPUT (kort sammanfattning):"""

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate LLM JSON response"""
        
        # Clean response - remove markdown blocks if present
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        try:
            data = json.loads(cleaned)
            
            # Validate required fields
            if "speak_text_en" not in data:
                raise ValueError("Missing speak_text_en field")
            
            # Validate field types
            speak_text = data["speak_text_en"]
            if not isinstance(speak_text, str) or len(speak_text.strip()) == 0:
                raise ValueError("speak_text_en must be non-empty string")
            
            # Set defaults
            data.setdefault("style", "neutral")
            data.setdefault("rate", 1.0)
            
            return data
            
        except (json.JSONDecodeError, ValueError) as e:
            raise Exception(f"Failed to parse LLM response: {e}. Response: {response_text[:100]}...")
    
    def _validate_output(self, voice_output: VoiceOutput) -> None:
        """Validate final voice output meets requirements"""
        
        text = voice_output.speak_text_en
        
        # Check length
        if len(text) > self.max_segment_length and not voice_output.is_summary:
            raise ValueError(f"Output too long: {len(text)} > {self.max_segment_length}")
        
        # Check for Swedish content (basic check)
        swedish_indicators = ["jag", "och", "är", "det", "på", "med", "för", "till", "av", "om"]
        text_lower = text.lower()
        if any(word in text_lower.split() for word in swedish_indicators):
            raise ValueError(f"Output contains Swedish words: {text}")
        
        # Check ends with punctuation
        if not text.strip().endswith(('.', '!', '?')):
            voice_output.speak_text_en = text.strip() + "."
    
    def _create_segments(self, text: str) -> List[str]:
        """Split long text into segments for later processing"""
        
        # Simple sentence-based segmentation
        sentences = re.split(r'[.!?]+', text)
        segments = []
        current_segment = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # If adding this sentence would exceed limit, save current and start new
            if len(current_segment + sentence) > self.max_segment_length and current_segment:
                segments.append(current_segment.strip())
                current_segment = sentence
            else:
                current_segment += " " + sentence if current_segment else sentence
        
        # Add final segment
        if current_segment.strip():
            segments.append(current_segment.strip())
            
        return segments[:5]  # Max 5 segments to avoid too much processing
    
    def _create_fallback_output(self, input_package: InputPackage, error: str, start_time: float) -> VoiceOutput:
        """Create fallback output when translation fails"""
        
        # Simple fallback - acknowledge the input in English
        fallback_text = f"I received a {input_package.source_type} message in Swedish."
        
        return VoiceOutput(
            speak_text_en=fallback_text,
            screen_text_sv=input_package.text_sv,
            style="neutral",
            rate=1.0,
            meta={
                "processing_time": time.time() - start_time,
                "source_type": input_package.source_type,
                "error": error,
                "fallback": True
            }
        )

    async def process_segment(self, segment_text: str, context: Dict[str, Any]) -> str:
        """Process individual segment from a larger text"""
        
        prompt = self._build_prompt(segment_text, context.get("source_type", "text"))
        
        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.chat(messages)
            if response.text:
                data = self._parse_llm_response(response.text)
                return data["speak_text_en"]
            else:
                return f"Segment in Swedish: {segment_text[:50]}..."
        except Exception:
            return f"Segment processing failed."