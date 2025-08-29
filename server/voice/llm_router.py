"""
LLM Router - Routes translation requests to appropriate LLM based on complexity
Fast 7B model for simple text, full 20B model for complex content.
"""

import time
import asyncio
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Handle relative imports when run as script
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.ollama import OllamaAdapter
from voice.normalizer import analyze_text_complexity

class LLMType(Enum):
    FAST = "7b"    # Fast model for simple translations
    FULL = "20b"   # Full model for complex translations

@dataclass  
class LLMResponse:
    """Response from LLM routing"""
    text: str
    llm_used: LLMType
    response_time: float
    tokens_used: Optional[int] = None
    cache_hit: bool = False
    error: Optional[str] = None

class LLMRouter:
    """Routes translation requests to appropriate LLM based on text complexity"""
    
    def __init__(self):
        # Initialize both LLM adapters
        self.fast_llm = OllamaAdapter(model="llama3:8b")  # Fast 8B model (available)
        self.full_llm = OllamaAdapter(model="gpt-oss:20b") # Full 20B model
        
        # Performance tracking
        self.stats = {
            "fast_requests": 0,
            "full_requests": 0,
            "fast_avg_time": 0.0,
            "full_avg_time": 0.0,
            "fast_errors": 0,
            "full_errors": 0,
            "routing_accuracy": []
        }
        
        # Simple prompts for fast model (minimal overhead)
        self.fast_prompt_template = """Translate Swedish to English. Output only the English text, nothing else.

Swedish: {text}
English:"""
        
        # Full prompt for complex model (same as orchestrator)
        self.full_system_prompt = """Du är Alice's voice orchestrator. Din uppgift är att översätta svensk text till idiomatisk engelska för röstuppläsning.

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
        
        # Connection status
        self._fast_llm_ready = False
        self._full_llm_ready = False
        self._last_health_check = 0
        self._health_check_interval = 300  # 5 minutes
    
    async def initialize(self) -> bool:
        """Initialize and health check both LLMs"""
        
        print("🔧 Initializing LLM Router...")
        
        try:
            # Test fast LLM
            print("  Testing 8B fast model...")
            fast_health = await self.fast_llm.health()
            if fast_health.ok:
                self._fast_llm_ready = True
                print(f"  ✅ 8B model ready (TTFT: {fast_health.tftt_ms:.0f}ms)")
            else:
                print(f"  ❌ 8B model failed: {fast_health.error}")
            
        except Exception as e:
            print(f"  ❌ 8B model error: {e}")
            self._fast_llm_ready = False
        
        try:
            # Test full LLM  
            print("  Testing 20B full model...")
            full_health = await self.full_llm.health()
            if full_health.ok:
                self._full_llm_ready = True
                print(f"  ✅ 20B model ready (TTFT: {full_health.tftt_ms:.0f}ms)")
            else:
                print(f"  ❌ 20B model failed: {full_health.error}")
        
        except Exception as e:
            print(f"  ❌ 20B model error: {e}")
            self._full_llm_ready = False
        
        # Update last health check
        self._last_health_check = time.time()
        
        # Return success if at least one model works
        success = self._fast_llm_ready or self._full_llm_ready
        
        if success:
            print("✅ LLM Router initialized")
        else:
            print("❌ LLM Router initialization failed - no models available")
        
        return success
    
    async def translate(self, swedish_text: str, source_type: str = "chat") -> LLMResponse:
        """Route translation to appropriate LLM based on complexity"""
        
        start_time = time.time()
        
        # Periodic health check
        if time.time() - self._last_health_check > self._health_check_interval:
            await self._background_health_check()
        
        # Analyze text complexity to determine routing
        analysis = analyze_text_complexity(swedish_text)
        use_fast = analysis["use_fast_llm"] and self._fast_llm_ready
        
        # Fallback logic if preferred model not available
        if use_fast and not self._fast_llm_ready:
            use_fast = False  # Fall back to full model
        elif not use_fast and not self._full_llm_ready:
            use_fast = True   # Fall back to fast model
        
        # If neither model available, return error
        if not self._fast_llm_ready and not self._full_llm_ready:
            return LLMResponse(
                text="Translation service temporarily unavailable.",
                llm_used=LLMType.FAST,
                response_time=time.time() - start_time,
                error="No LLM models available"
            )
        
        try:
            if use_fast:
                result = await self._translate_fast(swedish_text, source_type, analysis)
            else:
                result = await self._translate_full(swedish_text, source_type, analysis)
            
            # Update statistics
            self._update_stats(result)
            
            return result
            
        except Exception as e:
            # Fallback to other model on error
            try:
                if use_fast:
                    print(f"⚠️  Fast model failed, falling back to full: {e}")
                    result = await self._translate_full(swedish_text, source_type, analysis)
                else:
                    print(f"⚠️  Full model failed, falling back to fast: {e}")
                    result = await self._translate_fast(swedish_text, source_type, analysis)
                
                result.error = f"Fallback used: {e}"
                self._update_stats(result)
                return result
                
            except Exception as e2:
                return LLMResponse(
                    text=f"Translation failed for: {swedish_text[:50]}...",
                    llm_used=LLMType.FAST if use_fast else LLMType.FULL,
                    response_time=time.time() - start_time,
                    error=f"Both models failed: {e}, {e2}"
                )
    
    async def _translate_fast(self, text: str, source_type: str, analysis: Dict) -> LLMResponse:
        """Translate using fast 7B model with minimal prompt"""
        
        start_time = time.time()
        
        # Simple prompt for fast translation
        prompt = self.fast_prompt_template.format(text=text)
        
        messages = [{"role": "user", "content": prompt}]
        
        # Call fast LLM
        response = await self.fast_llm.chat(messages)
        
        if not response.text:
            raise Exception("Fast LLM returned empty response")
        
        # Fast model returns plain text, not JSON
        english_text = response.text.strip()
        
        # Clean up common artifacts from simple prompt
        if english_text.startswith(("English:", "Translation:")):
            english_text = english_text.split(":", 1)[1].strip()
        
        # Ensure proper sentence ending
        if english_text and not english_text.endswith(('.', '!', '?')):
            english_text += '.'
        
        self.stats["fast_requests"] += 1
        
        return LLMResponse(
            text=english_text,
            llm_used=LLMType.FAST,
            response_time=time.time() - start_time,
            tokens_used=getattr(response, 'tokens_used', None)
        )
    
    async def _translate_full(self, text: str, source_type: str, analysis: Dict) -> LLMResponse:
        """Translate using full 20B model with complete prompt"""
        
        start_time = time.time()
        
        # Build full prompt with context (same as orchestrator)
        source_instructions = {
            "chat": "Casual conversational tone.",
            "email": "Professional but friendly tone.", 
            "calendar": "Clear, time-focused information.",
            "notification": "Brief and direct.",
            "command": "Acknowledge the action clearly."
        }
        
        instruction = source_instructions.get(source_type, "Neutral tone.")
        
        prompt = f"""{self.full_system_prompt}

KONTEXT: {source_type} - {instruction}

SVENSK TEXT:
{text}

JSON OUTPUT:"""
        
        messages = [{"role": "user", "content": prompt}]
        
        response = await self.full_llm.chat(messages)
        
        if not response.text:
            raise Exception("Full LLM returned empty response")
        
        # Parse JSON response (same as orchestrator)
        try:
            import json
            
            # Clean response
            cleaned = response.text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            data = json.loads(cleaned)
            
            if "speak_text_en" not in data:
                raise ValueError("Missing speak_text_en field")
            
            english_text = data["speak_text_en"]
            
            if not isinstance(english_text, str) or len(english_text.strip()) == 0:
                raise ValueError("speak_text_en must be non-empty string")
            
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: try to extract text content
            english_text = response.text.strip()
            if '"speak_text_en"' in english_text:
                # Try to extract from malformed JSON
                try:
                    match = re.search(r'"speak_text_en":\s*"([^"]+)"', english_text)
                    if match:
                        english_text = match.group(1)
                    else:
                        raise Exception(f"Could not parse JSON response: {e}")
                except:
                    raise Exception(f"Could not parse JSON response: {e}")
            else:
                # Use as plain text
                pass
        
        self.stats["full_requests"] += 1
        
        return LLMResponse(
            text=english_text,
            llm_used=LLMType.FULL,
            response_time=time.time() - start_time,
            tokens_used=getattr(response, 'tokens_used', None)
        )
    
    async def _background_health_check(self):
        """Background health check for both models"""
        
        self._last_health_check = time.time()
        
        # Check fast model
        try:
            health = await asyncio.wait_for(self.fast_llm.health(), timeout=5.0)
            self._fast_llm_ready = health.ok
        except:
            self._fast_llm_ready = False
        
        # Check full model
        try:
            health = await asyncio.wait_for(self.full_llm.health(), timeout=5.0)
            self._full_llm_ready = health.ok
        except:
            self._full_llm_ready = False
    
    def _update_stats(self, response: LLMResponse):
        """Update performance statistics"""
        
        if response.llm_used == LLMType.FAST:
            # Update fast model stats
            current_avg = self.stats["fast_avg_time"]
            count = self.stats["fast_requests"]
            
            if count > 1:
                new_avg = ((current_avg * (count - 1)) + response.response_time) / count
                self.stats["fast_avg_time"] = new_avg
            else:
                self.stats["fast_avg_time"] = response.response_time
            
            if response.error:
                self.stats["fast_errors"] += 1
                
        else:
            # Update full model stats
            current_avg = self.stats["full_avg_time"]
            count = self.stats["full_requests"]
            
            if count > 1:
                new_avg = ((current_avg * (count - 1)) + response.response_time) / count
                self.stats["full_avg_time"] = new_avg
            else:
                self.stats["full_avg_time"] = response.response_time
            
            if response.error:
                self.stats["full_errors"] += 1
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        
        total_requests = self.stats["fast_requests"] + self.stats["full_requests"]
        
        return {
            "models_available": {
                "fast_7b": self._fast_llm_ready,
                "full_20b": self._full_llm_ready
            },
            "request_distribution": {
                "fast_requests": self.stats["fast_requests"],
                "full_requests": self.stats["full_requests"],
                "fast_percentage": (self.stats["fast_requests"] / total_requests * 100) if total_requests > 0 else 0
            },
            "performance": {
                "fast_avg_time": self.stats["fast_avg_time"],
                "full_avg_time": self.stats["full_avg_time"],
                "speed_improvement": (self.stats["full_avg_time"] / self.stats["fast_avg_time"]) if self.stats["fast_avg_time"] > 0 else 0
            },
            "reliability": {
                "fast_error_rate": (self.stats["fast_errors"] / self.stats["fast_requests"] * 100) if self.stats["fast_requests"] > 0 else 0,
                "full_error_rate": (self.stats["full_errors"] / self.stats["full_requests"] * 100) if self.stats["full_requests"] > 0 else 0
            }
        }

# Convenience function for orchestrator
async def route_translation(text: str, source_type: str = "chat", router: Optional[LLMRouter] = None) -> LLMResponse:
    """Route translation request to appropriate LLM"""
    
    if router is None:
        # Create and initialize router if not provided
        router = LLMRouter()
        await router.initialize()
    
    return await router.translate(text, source_type)

# Test function
async def test_llm_router():
    """Test the LLM router with various text complexities"""
    
    print("🧪 Testing LLM Router")
    print("=" * 50)
    
    router = LLMRouter()
    
    if not await router.initialize():
        print("❌ Router initialization failed")
        return
    
    test_cases = [
        # Simple cases (should use 7B)
        ("Simple greeting", "chat", "Hej Alice!"),
        ("Simple question", "chat", "Vad är klockan?"),
        ("Simple thanks", "chat", "Tack så mycket!"),
        
        # Complex cases (should use 20B)  
        ("Swedish names", "chat", "Anna-Lena och Per-Erik kommer imorgon"),
        ("Meeting scheduling", "email", "Kan vi boka möte på måndag kl 14:00?"),
        ("Calendar event", "calendar", "Möte med designteamet om 10 minuter i konferensrum A"),
    ]
    
    for name, source_type, text in test_cases:
        print(f"\n🧪 Testing: {name}")
        print(f"📝 Text: '{text}'")
        
        start_time = time.time()
        response = await router.translate(text, source_type)
        
        if response.error:
            print(f"❌ Error: {response.error}")
        else:
            model_name = "7B (fast)" if response.llm_used == LLMType.FAST else "20B (full)"
            print(f"🧠 Model: {model_name}")
            print(f"🇬🇧 Result: '{response.text}'")
            print(f"⚡ Time: {response.response_time:.2f}s")
    
    # Print performance stats
    stats = router.get_performance_stats()
    print(f"\n📊 PERFORMANCE STATS:")
    print(f"Fast requests: {stats['request_distribution']['fast_requests']}")
    print(f"Full requests: {stats['request_distribution']['full_requests']}")
    print(f"Fast avg time: {stats['performance']['fast_avg_time']:.2f}s")
    print(f"Full avg time: {stats['performance']['full_avg_time']:.2f}s")
    
    if stats['performance']['speed_improvement'] > 0:
        print(f"Speed improvement: {stats['performance']['speed_improvement']:.1f}x faster with routing")

if __name__ == "__main__":
    import re
    asyncio.run(test_llm_router())