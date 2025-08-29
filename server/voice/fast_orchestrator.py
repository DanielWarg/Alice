"""
Fast Voice Orchestrator - Priority queue + dual Ollama for optimal performance
"""

import json
import time
import re
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from .input_processor import InputPackage
from .simple_normalizer import pre_normalize_sv, post_normalize_en, make_cache_key
from .production_config import ProductionVoiceConfig
from .priority_queue import voice_priority_queue
from .dual_ollama_clients import dual_ollama

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

class FastVoiceOrchestrator:
    """
    High-performance voice orchestrator with:
    - Priority queue processing
    - Dual Ollama routing (fast/deep)
    - Single-flight deduplication
    - Guardian fast-lane integration
    """
    
    def __init__(self):
        self.max_segment_length = 320  # Characters per segment
        self.max_total_length = 2000   # Before requiring summary
        self.config = ProductionVoiceConfig()
        
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
        Main processing method - uses priority queue for optimal scheduling
        """
        
        # Submit to priority queue with automatic routing
        result = await voice_priority_queue.submit(
            text=input_package.text_sv,
            source_type=input_package.source_type,
            processor_coro=self._process_with_priority
        )
        
        return result
    
    async def _process_with_priority(self, text_sv: str, source_type: str) -> VoiceOutput:
        """Process single request through fast-lane pipeline"""
        
        start_time = time.time()
        
        # Determine if segmentation is needed
        needs_segmentation = (
            len(text_sv) > self.max_total_length or
            source_type == "email"
        )
        
        if needs_segmentation:
            return await self._process_with_segmentation(text_sv, source_type, start_time)
        else:
            return await self._process_single(text_sv, source_type, start_time)
    
    async def _process_single(self, text_sv: str, source_type: str, start_time: float) -> VoiceOutput:
        """Process short text using dual Ollama routing"""
        
        # 1. Pre-normalize Swedish text
        pre_normalized = pre_normalize_sv(text_sv)
        
        # 2. Determine complexity for routing
        text_length = len(pre_normalized)
        has_complex_patterns = any(
            indicator in pre_normalized.lower() 
            for indicator in self.config.ROUTER_COMPLEX_INDICATORS
        )
        
        # 3. Build prompt
        prompt = self._build_prompt(pre_normalized, source_type)
        messages = [{"role": "user", "content": prompt}]
        
        try:
            # 4. Route to appropriate Ollama instance
            response = await dual_ollama.translate_with_routing(
                messages, text_length, has_complex_patterns
            )
            
            if not response.success or not response.text:
                raise Exception(f"LLM failed: {response.error}")
            
            # 5. Parse and validate response
            voice_data = self._parse_llm_response(response.text)
            
            # 6. Post-normalize for cache consistency
            normalized_english = post_normalize_en(voice_data["speak_text_en"])
            
            # 7. Apply production style/rate settings
            style_rate = self.config.get_style_rate(source_type)
            
            # 8. Create final output
            voice_output = VoiceOutput(
                speak_text_en=normalized_english,
                screen_text_sv=text_sv,
                style=style_rate["style"],
                rate=style_rate["rate"],
                meta={
                    "processing_time": time.time() - start_time,
                    "llm_time": response.processing_time,
                    "source_type": source_type,
                    "char_count": len(normalized_english),
                    "model_used": response.model,
                    "fast_lane": True,
                    "pre_normalized": pre_normalized != text_sv,
                    "post_normalized": normalized_english != voice_data["speak_text_en"]
                }
            )
            
            # 9. Validate output
            self._validate_output(voice_output)
            
            return voice_output
            
        except Exception as e:
            return self._create_fallback_output(text_sv, source_type, str(e), start_time)
    
    async def _process_with_segmentation(self, text_sv: str, source_type: str, start_time: float) -> VoiceOutput:
        """Process long content with TL;DR first approach"""
        
        pre_normalized = pre_normalize_sv(text_sv)
        
        # Create summary for immediate playback (email TL;DR)
        summary_prompt = self._build_summary_prompt(pre_normalized, source_type)
        messages = [{"role": "user", "content": summary_prompt}]
        
        try:
            # Get TL;DR using fast routing
            response = await dual_ollama.translate_with_routing(
                messages, len(summary_prompt), False  # Summaries usually not complex
            )
            
            if not response.success or not response.text:
                raise Exception(f"Summary failed: {response.error}")
            
            summary_data = self._parse_llm_response(response.text)
            normalized_summary = post_normalize_en(summary_data["speak_text_en"])
            
            # Create segments for background processing
            segments = self._create_segments(pre_normalized)
            
            voice_output = VoiceOutput(
                speak_text_en=normalized_summary,
                screen_text_sv=text_sv,
                style=summary_data.get("style", "formal"),
                rate=summary_data.get("rate", 1.0),
                segments=segments,
                is_summary=True,
                meta={
                    "processing_time": time.time() - start_time,
                    "llm_time": response.processing_time,
                    "source_type": source_type,
                    "model_used": response.model,
                    "has_segments": len(segments) > 0,
                    "total_segments": len(segments),
                    "fast_lane": True
                }
            )
            
            self._validate_output(voice_output)
            return voice_output
            
        except Exception as e:
            return self._create_fallback_output(text_sv, source_type, str(e), start_time)
    
    def _build_prompt(self, swedish_text: str, source_type: str) -> str:
        """Build translation prompt with context"""
        
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
        """Build prompt for TL;DR generation"""
        
        return f"""{self.system_prompt}

SPECIELL UPPGIFT: Skapa en KORT sammanfattning (1-2 meningar, max 160 tecken).
Detta är första ljudet användaren hör - gör det informativt och koncist.

KONTEXT: {source_type} - behöver snabb sammanfattning

SVENSK TEXT:
{swedish_text}

JSON OUTPUT (kort sammanfattning):"""

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate LLM JSON response"""
        
        # Clean response
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        try:
            data = json.loads(cleaned)
            
            if "speak_text_en" not in data:
                raise ValueError("Missing speak_text_en field")
            
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
        """Validate final voice output"""
        
        text = voice_output.speak_text_en
        
        # Check length
        if len(text) > self.max_segment_length and not voice_output.is_summary:
            raise ValueError(f"Output too long: {len(text)} > {self.max_segment_length}")
        
        # Check for Swedish content
        swedish_indicators = ["jag", "och", "är", "det", "på", "med", "för", "till", "av", "om"]
        text_lower = text.lower()
        if any(word in text_lower.split() for word in swedish_indicators):
            raise ValueError(f"Output contains Swedish words: {text}")
        
        # Ensure ends with punctuation
        if not text.strip().endswith(('.', '!', '?')):
            voice_output.speak_text_en = text.strip() + "."
    
    def _create_segments(self, text: str) -> List[str]:
        """Split long text into segments"""
        
        sentences = re.split(r'[.!?]+', text)
        segments = []
        current_segment = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(current_segment + sentence) > self.max_segment_length and current_segment:
                segments.append(current_segment.strip())
                current_segment = sentence
            else:
                current_segment += " " + sentence if current_segment else sentence
        
        if current_segment.strip():
            segments.append(current_segment.strip())
            
        return segments[:5]  # Max 5 segments
    
    def _create_fallback_output(self, text_sv: str, source_type: str, error: str, start_time: float) -> VoiceOutput:
        """Create fallback output when translation fails"""
        
        fallback_text = f"I received a {source_type} message in Swedish."
        
        return VoiceOutput(
            speak_text_en=fallback_text,
            screen_text_sv=text_sv,
            style="neutral",
            rate=1.0,
            meta={
                "processing_time": time.time() - start_time,
                "source_type": source_type,
                "error": error,
                "fallback": True,
                "fast_lane": True
            }
        )

    async def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        
        queue_stats = await voice_priority_queue.get_stats()
        health = await dual_ollama.health_check()
        
        return {
            "queue": queue_stats,
            "ollama_health": health,
            "fast_lane_enabled": True
        }

# Global fast orchestrator instance
fast_voice_orchestrator = FastVoiceOrchestrator()