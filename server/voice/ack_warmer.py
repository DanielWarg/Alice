"""
Ack Warmer - Pre-cache common acknowledgment phrases at startup
"""

import asyncio
import aiofiles
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any
import aiohttp

logger = logging.getLogger("alice.voice.ack_warmer")

class AckWarmer:
    """Pre-cache acknowledgment phrases for instant voice responses"""
    
    def __init__(self, tts_endpoint: str = "http://localhost:8000/api/tts"):
        self.tts_endpoint = tts_endpoint
        self.ack_catalog_path = Path(__file__).parent / "ack_catalog.json"
        self.voice = "nova"  # Consistent voice across all acks
        self.rate = 1.0      # Standard rate
        
    async def load_ack_catalog(self) -> Dict[str, List[str]]:
        """Load acknowledgment catalog from JSON file"""
        
        try:
            async with aiofiles.open(self.ack_catalog_path, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to load ack catalog: {e}")
            return {"default": ["Let me check that for you..."]}
    
    def substitute_common_params(self, phrase: str) -> List[str]:
        """Generate variations with common parameter substitutions"""
        
        variations = [phrase]  # Original phrase always included
        
        # Common substitutions
        if "{city}" in phrase:
            cities = ["Stockholm", "Göteborg", "Malmö", "Uppsala"]
            variations.extend([phrase.replace("{city}", city) for city in cities])
            
        if "{duration}" in phrase:
            durations = ["5 minutes", "10 minutes", "15 minutes", "30 minutes", "1 hour"]
            variations.extend([phrase.replace("{duration}", duration) for duration in durations])
            
        if "{name}" in phrase:
            names = ["Anna", "Erik", "Maria", "Johan"]
            variations.extend([phrase.replace("{name}", name) for name in names])
        
        return variations
    
    async def warm_phrase(self, phrase: str) -> Dict[str, Any]:
        """Pre-cache a single phrase via TTS endpoint"""
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": phrase,
                    "voice": self.voice,
                    "rate": self.rate
                }
                
                async with session.post(self.tts_endpoint, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "phrase": phrase,
                            "success": True,
                            "cached": result.get("cached", False),
                            "url": result.get("url", ""),
                            "processing_time": result.get("processing_time_ms", 0)
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "phrase": phrase,
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text[:100]}"
                        }
        except Exception as e:
            return {
                "phrase": phrase,
                "success": False,
                "error": str(e)
            }
    
    async def warm_catalog(self, max_concurrent: int = 5) -> Dict[str, Any]:
        """Pre-cache all phrases in the acknowledgment catalog"""
        
        start_time = time.time()
        logger.info("🔥 Starting ack catalog warming...")
        
        # Load catalog
        catalog = await self.load_ack_catalog()
        
        # Collect all phrases to warm
        phrases_to_warm = set()
        
        for intent, phrase_list in catalog.items():
            for phrase in phrase_list:
                # Add original phrase
                phrases_to_warm.add(phrase)
                
                # Add variations with parameter substitutions
                variations = self.substitute_common_params(phrase)
                phrases_to_warm.update(variations)
        
        phrases_list = list(phrases_to_warm)
        logger.info(f"Found {len(phrases_list)} unique phrases to pre-cache")
        
        # Warm phrases with concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def warm_with_semaphore(phrase: str):
            async with semaphore:
                return await self.warm_phrase(phrase)
        
        # Execute all warmups
        results = await asyncio.gather(*[
            warm_with_semaphore(phrase) for phrase in phrases_list
        ])
        
        # Analyze results
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        cached_hits = [r for r in results if r.get("cached", False)]
        
        total_time = time.time() - start_time
        avg_time = sum(r.get("processing_time", 0) for r in successful) / len(successful) if successful else 0
        
        summary = {
            "total_phrases": len(phrases_list),
            "successful": len(successful),
            "failed": len(failed),
            "already_cached": len(cached_hits),
            "newly_cached": len(successful) - len(cached_hits),
            "success_rate": len(successful) / len(phrases_list) * 100 if phrases_list else 0,
            "total_time_seconds": round(total_time, 2),
            "avg_generation_time_ms": round(avg_time, 0),
            "phrases_per_second": round(len(phrases_list) / total_time, 1) if total_time > 0 else 0
        }
        
        logger.info(f"✅ Ack warming complete: {summary['successful']}/{summary['total_phrases']} phrases cached")
        logger.info(f"   Success rate: {summary['success_rate']:.1f}%")
        logger.info(f"   Total time: {summary['total_time_seconds']}s")
        logger.info(f"   Processing rate: {summary['phrases_per_second']} phrases/second")
        
        if failed:
            logger.warning(f"❌ Failed to cache {len(failed)} phrases:")
            for failure in failed[:5]:  # Log first 5 failures
                logger.warning(f"   '{failure['phrase'][:50]}...': {failure['error']}")
        
        return summary
    
    async def warm_high_priority_phrases(self) -> Dict[str, Any]:
        """Warm only the most commonly used phrases for faster startup"""
        
        high_priority = [
            "Let me check that for you...",
            "One moment...",
            "Got it. Checking now...",
            "Working on it...",
            "Let me check your inbox for a second...",
            "Checking your email now...",
            "Let me pull up your schedule for today...",
            "Checking your meetings...",
            "Let me check the weather in Stockholm...",
            "Setting a timer for 10 minutes...",
            "Done!",
            "All set!"
        ]
        
        logger.info(f"🚀 Warming {len(high_priority)} high-priority phrases...")
        
        start_time = time.time()
        results = await asyncio.gather(*[
            self.warm_phrase(phrase) for phrase in high_priority
        ])
        
        successful = [r for r in results if r["success"]]
        total_time = time.time() - start_time
        
        summary = {
            "total_phrases": len(high_priority),
            "successful": len(successful),
            "success_rate": len(successful) / len(high_priority) * 100,
            "total_time_seconds": round(total_time, 2)
        }
        
        logger.info(f"✅ High-priority warming: {len(successful)}/{len(high_priority)} phrases cached in {total_time:.1f}s")
        
        return summary

# Global warmer instance
ack_warmer = AckWarmer()

# Convenience functions
async def warm_ack_catalog(max_concurrent: int = 5) -> Dict[str, Any]:
    """Warm complete acknowledgment catalog"""
    return await ack_warmer.warm_catalog(max_concurrent)

async def warm_high_priority_acks() -> Dict[str, Any]:
    """Warm high-priority acknowledgment phrases only"""
    return await ack_warmer.warm_high_priority_phrases()