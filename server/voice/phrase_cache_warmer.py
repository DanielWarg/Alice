"""
Phrase Cache Warmer - Pre-caches common phrases at startup for instant responses
"""

import asyncio
import logging
from typing import List
from pathlib import Path
import time

try:
    from .orchestrator import VoiceOrchestrator
    from .input_processor import InputPackage
    from .production_config import ProductionVoiceConfig
except ImportError:
    # Handle relative import when run as standalone
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    
    from voice.orchestrator import VoiceOrchestrator
    from voice.input_processor import InputPackage
    from voice.production_config import ProductionVoiceConfig

logger = logging.getLogger("alice.voice.cache_warmer")

class PhraseCacheWarmer:
    """Pre-caches common phrases at startup for instant response times"""
    
    def __init__(self):
        self.orchestrator = VoiceOrchestrator()
        self.config = ProductionVoiceConfig()
        
    async def warm_common_phrases(self) -> int:
        """Warm up cache with common phrases from production config"""
        
        logger.info("🔥 Starting phrase cache warming...")
        start_time = time.time()
        warmed_count = 0
        
        # Get common phrases from production config
        phrases_to_warm = self.config.COMMON_PHRASES
        
        # Convert English phrases to Swedish for testing
        swedish_test_phrases = [
            "Hej Alice!",
            "Hej där!",
            "God morgon!",
            "Tack så mycket!",
            "Ingen orsak.",
            "Jag är här för att hjälpa.",
            "Vad är klockan?",
            "Hur är vädret?",
            "Vad står på kalendern?",
            "Några nya meddelanden?",
            "Batterivarning.",
            "Nytt meddelande mottaget.",
            "Påminnelse inställd.",
            "Uppgift slutförd.",
            "Uppdatering tillgänglig.",
            "Klart.",
            "Jag förstår.",
            "Bearbetar...",
            "Jobbar på det.",
            "Ett ögonblick tack."
        ]
        
        # Pre-cache these phrases
        for phrase in swedish_test_phrases:
            try:
                input_package = InputPackage(
                    text_sv=phrase,
                    source_type="chat"
                )
                
                # Process through voice pipeline (this will cache the result)
                result = await self.orchestrator.process(input_package)
                
                if result:
                    warmed_count += 1
                    logger.debug(f"Cached: '{phrase}' -> '{result.speak_text_en}'")
                    
            except Exception as e:
                logger.warning(f"Failed to warm phrase '{phrase}': {e}")
                continue
                
            # Small delay to avoid overwhelming system
            await asyncio.sleep(0.1)
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Cache warming complete: {warmed_count}/{len(swedish_test_phrases)} phrases cached in {elapsed:.1f}s")
        
        return warmed_count
    
    async def warm_startup_cache(self) -> dict:
        """Complete startup cache warming with metrics"""
        
        start_time = time.time()
        
        # Warm common phrases
        phrases_warmed = await self.warm_common_phrases()
        
        # Summary metrics
        total_time = time.time() - start_time
        
        metrics = {
            "phrases_warmed": phrases_warmed,
            "total_time_seconds": round(total_time, 2),
            "avg_time_per_phrase": round(total_time / phrases_warmed if phrases_warmed > 0 else 0, 3),
            "phrases_per_second": round(phrases_warmed / total_time if total_time > 0 else 0, 1)
        }
        
        logger.info(f"🎯 Cache warmer metrics: {metrics}")
        
        return metrics

# Global warmer instance  
phrase_warmer = PhraseCacheWarmer()

async def warm_voice_cache_at_startup():
    """Convenience function for startup cache warming"""
    return await phrase_warmer.warm_startup_cache()