#!/usr/bin/env python3
"""
🎙️ Alice Voice Pipeline - Natural Dialog Performance Test
Testar naturlig dialog över tid för att mäta latency och performance patterns.
"""

import os
import sys
import asyncio
import time
import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import statistics

# Add server to path
sys.path.append('server')

from server.voice.input_processor import InputProcessor
from server.voice.orchestrator import VoiceOrchestrator
from server.voice.tts_client import TTSClient

class NaturalDialogTester:
    """Performance tester med naturlig dialog över tid"""
    
    def __init__(self):
        self.input_processor = InputProcessor()
        self.orchestrator = VoiceOrchestrator()
        self.tts_client = None
        
        # Performance tracking
        self.session_results = []
        self.running_stats = {
            "translation_times": [],
            "tts_times": [],
            "total_times": [],
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": []
        }
        
        # Test configuration
        self.test_duration_minutes = 15  # Default test duration
        self.interaction_interval = 30   # Seconds between interactions
        self.warmup_interactions = 3     # Number of warmup interactions
        
        # Check API key
        self.has_api_key = bool(os.getenv("OPENAI_API_KEY") and not os.getenv("OPENAI_API_KEY").startswith("test-"))
    
    def get_natural_dialog_sequences(self) -> List[Tuple[str, str, str]]:
        """
        Naturliga dialogsekvenser som simulerar verklig användning.
        Returnerar (name, source_type, swedish_text)
        """
        
        # Morgon routine
        morning_sequence = [
            ("Morgon hälsning", "chat", "God morgon Alice! Hur mår du idag?"),
            ("Väder kolla", "chat", "Hur blir vädret idag?"),
            ("Dagens agenda", "chat", "Vad har jag för möten idag?"),
            ("Påminnelse sätt", "chat", "Påminn mig om att ringa mamma kl 15"),
        ]
        
        # Arbetsdag interactions
        workday_sequence = [
            ("Email check", "email", "Du har 3 nya mail från kollegan om projektmötet"),
            ("Mötespåminnelse", "calendar", "Möte med designteamet om 10 minuter i konferensrum A"),
            ("Lunch förslag", "chat", "Vad ska jag äta till lunch idag?"),
            ("Telefon påminnelse", "notification", "Ring tandläkaren för bokning"),
            ("Status update", "chat", "Hur går projektet med hemsidan?"),
        ]
        
        # Eftermiddag/kväll
        evening_sequence = [
            ("Trafik kolla", "chat", "Hur är trafiken hem från jobbet?"),
            ("Handlista", "chat", "Lägg till mjölk och bröd på handlistan"),
            ("Väckarklocka", "chat", "Ställ väckarklockan på 7:30 imorgon"),
            ("Podcast förslag", "chat", "Föreslå en bra svensk podcast att lyssna på"),
            ("God natt", "chat", "God natt Alice, vi ses imorgon!"),
        ]
        
        # Varierande interaktioner
        varied_interactions = [
            ("Svenska namn", "chat", "Anna-Lena och Per-Erik kommer på middag på fredag"),
            ("Svenskt datum", "chat", "Boka frisörtid på midsommarafton"),
            ("Svensk plats", "chat", "Hur långt är det från Stockholm till Malmö?"),
            ("Batteriarning", "notification", "Batteri lågt - 12% kvar"),
            ("Systemuppdatering", "notification", "Säkerhetsuppdatering tillgänglig"),
            ("Mötes bekräftelse", "email", "Bekräfta möte med kunden på måndag kl 14:00"),
            ("Påminnelse", "calendar", "Apoteksbesök imorgon kl 16:30 - glöm inte recept"),
            ("Hjälp fråga", "chat", "Kan du hjälpa mig att skriva ett mail på engelska?"),
            ("Tidsfråga", "chat", "Vad är klockan just nu?"),
            ("Tacksägelse", "chat", "Tack så mycket för all hjälp Alice!"),
        ]
        
        return morning_sequence + workday_sequence + evening_sequence + varied_interactions
    
    async def initialize(self):
        """Initialize TTS client and warm up system"""
        
        print("🔧 Initializing Natural Dialog Performance Tester...")
        
        # Test Ollama connection
        try:
            health = await self.orchestrator.llm.health()
            if not health.ok:
                print(f"❌ Ollama connection failed: {health.error}")
                return False
            print(f"✅ Ollama connected (TTFT: {health.tftt_ms:.0f}ms)")
        except Exception as e:
            print(f"❌ Ollama test failed: {e}")
            return False
        
        # Initialize TTS if API key available
        if self.has_api_key:
            try:
                self.tts_client = TTSClient()
                print("✅ TTS client initialized")
                
                # Warm-up TTS
                warmup = await self.tts_client.warm_up()
                print(f"{'✅' if warmup else '⚠️ '} TTS warm-up {'succeeded' if warmup else 'failed'}")
                
            except Exception as e:
                print(f"❌ TTS initialization failed: {e}")
                self.tts_client = None
        else:
            print("⚠️  No OpenAI API key - translation testing only")
        
        return True
    
    async def run_single_interaction(self, name: str, source_type: str, swedish_text: str) -> Dict[str, Any]:
        """Run en enskild interaction och mät performance"""
        
        start_time = time.time()
        result = {
            "name": name,
            "source_type": source_type,
            "swedish_text": swedish_text,
            "timestamp": datetime.now().isoformat(),
            "success": False
        }
        
        try:
            # Stage 1: Input Processing
            stage1_start = time.time()
            if source_type == "chat":
                input_pkg = self.input_processor.process_chat(swedish_text)
            elif source_type == "email":
                input_pkg = self.input_processor.process_email("Test", swedish_text)
            elif source_type == "calendar":
                input_pkg = self.input_processor.process_calendar("Event", "imorgon", swedish_text)
            else:
                input_pkg = self.input_processor.process_notification(swedish_text)
            
            stage1_time = time.time() - stage1_start
            
            # Stage 2: Translation
            stage2_start = time.time()
            voice_output = await self.orchestrator.process(input_pkg)
            stage2_time = time.time() - stage2_start
            
            if voice_output.meta.get("fallback", False):
                result["error"] = voice_output.meta.get("error", "Translation fallback")
                result["fallback"] = True
            else:
                result["english_text"] = voice_output.speak_text_en
                result["translation_time"] = stage2_time
                self.running_stats["translation_times"].append(stage2_time)
            
            # Stage 3: TTS (if available)
            if self.tts_client and not voice_output.meta.get("fallback", False):
                stage3_start = time.time()
                tts_result = await self.tts_client.synthesize(voice_output)
                stage3_time = time.time() - stage3_start
                
                if tts_result["success"] and tts_result.get("audio_file"):
                    audio_path = Path(tts_result["audio_file"])
                    if audio_path.exists():
                        result["audio_file"] = str(audio_path)
                        result["audio_size"] = audio_path.stat().st_size
                        result["tts_time"] = stage3_time
                        result["cached"] = tts_result.get("cached", False)
                        result["provider"] = tts_result.get("provider", "unknown")
                        
                        # Track cache performance
                        if result["cached"]:
                            self.running_stats["cache_hits"] += 1
                        else:
                            self.running_stats["cache_misses"] += 1
                        
                        self.running_stats["tts_times"].append(stage3_time)
                elif tts_result.get("text_only"):
                    result["text_only"] = True
                    result["tts_error"] = tts_result.get("error")
                else:
                    result["tts_failed"] = True
                    result["tts_error"] = tts_result.get("error")
            
            # Calculate total time
            result["total_time"] = time.time() - start_time
            result["processing_stages"] = {
                "input_processing": stage1_time,
                "translation": stage2_time,
                "tts": result.get("tts_time", 0)
            }
            
            if not result.get("fallback", False):
                result["success"] = True
                self.running_stats["total_times"].append(result["total_time"])
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            result["total_time"] = time.time() - start_time
            self.running_stats["errors"].append({
                "name": name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return result
    
    def print_running_stats(self, interaction_num: int, total_interactions: int):
        """Print running statistics"""
        
        print(f"\n📊 RUNNING STATS ({interaction_num}/{total_interactions})")
        print("=" * 60)
        
        # Success rate
        successful = len([r for r in self.session_results if r.get("success", False)])
        success_rate = (successful / len(self.session_results) * 100) if self.session_results else 0
        print(f"✅ Success Rate: {successful}/{len(self.session_results)} ({success_rate:.1f}%)")
        
        # Translation performance
        if self.running_stats["translation_times"]:
            trans_times = self.running_stats["translation_times"]
            avg_trans = statistics.mean(trans_times)
            median_trans = statistics.median(trans_times)
            p95_trans = sorted(trans_times)[int(len(trans_times) * 0.95)] if len(trans_times) > 1 else trans_times[0]
            print(f"🔄 Translation - Avg: {avg_trans:.2f}s | Median: {median_trans:.2f}s | P95: {p95_trans:.2f}s")
        
        # TTS performance
        if self.running_stats["tts_times"]:
            tts_times = self.running_stats["tts_times"]
            avg_tts = statistics.mean(tts_times)
            median_tts = statistics.median(tts_times)
            p95_tts = sorted(tts_times)[int(len(tts_times) * 0.95)] if len(tts_times) > 1 else tts_times[0]
            print(f"🔊 TTS - Avg: {avg_tts:.2f}s | Median: {median_tts:.2f}s | P95: {p95_tts:.2f}s")
            
            # Cache performance
            total_tts = self.running_stats["cache_hits"] + self.running_stats["cache_misses"]
            if total_tts > 0:
                cache_rate = self.running_stats["cache_hits"] / total_tts * 100
                print(f"💾 Cache Hit Rate: {self.running_stats['cache_hits']}/{total_tts} ({cache_rate:.1f}%)")
        
        # Overall performance
        if self.running_stats["total_times"]:
            total_times = self.running_stats["total_times"]
            avg_total = statistics.mean(total_times)
            median_total = statistics.median(total_times)
            p95_total = sorted(total_times)[int(len(total_times) * 0.95)] if len(total_times) > 1 else total_times[0]
            print(f"🎯 Total Time - Avg: {avg_total:.2f}s | Median: {median_total:.2f}s | P95: {p95_total:.2f}s")
        
        # Error rate
        if self.running_stats["errors"]:
            error_rate = len(self.running_stats["errors"]) / len(self.session_results) * 100
            print(f"❌ Error Rate: {len(self.running_stats['errors'])}/{len(self.session_results)} ({error_rate:.1f}%)")
        
        print()
    
    async def run_performance_test(self, duration_minutes: int = None, interaction_interval: int = None):
        """Run natural dialog performance test over time"""
        
        duration = duration_minutes or self.test_duration_minutes
        interval = interaction_interval or self.interaction_interval
        
        print("🎙️ Alice Natural Dialog Performance Test")
        print("=" * 65)
        print(f"Duration: {duration} minutes | Interval: {interval}s")
        print(f"TTS Enabled: {'✅' if self.has_api_key else '❌'}")
        
        # Get dialog sequences
        dialog_sequences = self.get_natural_dialog_sequences()
        
        # Calculate test parameters
        total_interactions = (duration * 60) // interval
        print(f"Planned interactions: ~{total_interactions}")
        print(f"Available dialog patterns: {len(dialog_sequences)}")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration)
        
        print(f"\n🚀 Starting performance test at {start_time.strftime('%H:%M:%S')}")
        print(f"Will run until {end_time.strftime('%H:%M:%S')}")
        print("=" * 65)
        
        interaction_count = 0
        
        # Warmup phase
        print("\n🔥 WARMUP PHASE")
        for i in range(self.warmup_interactions):
            name, source_type, text = random.choice(dialog_sequences)
            print(f"🔥 Warmup {i+1}/{self.warmup_interactions}: {name}")
            result = await self.run_single_interaction(f"Warmup-{i+1}", source_type, text)
            await asyncio.sleep(2)  # Short interval during warmup
        
        print("\n🎯 MAIN PERFORMANCE TEST")
        print("-" * 65)
        
        while datetime.now() < end_time:
            interaction_count += 1
            
            # Select dialog interaction (prefer variety)
            name, source_type, text = random.choice(dialog_sequences)
            
            # Run interaction
            print(f"\n🗣️  Interaction #{interaction_count}: {name}")
            print(f"📱 {source_type}: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            result = await self.run_single_interaction(name, source_type, text)
            self.session_results.append(result)
            
            # Show result
            if result["success"]:
                english = result.get("english_text", "N/A")
                total_time = result["total_time"]
                print(f"✅ '{english}' ({total_time:.2f}s)")
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
            
            # Print running stats every 5 interactions or if performance degrades
            if interaction_count % 5 == 0:
                self.print_running_stats(interaction_count, total_interactions)
            
            # Wait for next interaction
            await asyncio.sleep(interval)
            
            # Check if we should continue
            remaining_time = (end_time - datetime.now()).total_seconds()
            if remaining_time <= 0:
                break
        
        # Final results
        self.print_final_results(interaction_count, duration)
        
        # Save detailed results
        await self.save_results()
        
        return len(self.session_results) > 0
    
    def print_final_results(self, total_interactions: int, duration_minutes: int):
        """Print comprehensive final results"""
        
        print("\n" + "=" * 65)
        print("🏁 FINAL PERFORMANCE RESULTS")
        print("=" * 65)
        
        # Basic stats
        successful = len([r for r in self.session_results if r.get("success", False)])
        success_rate = (successful / len(self.session_results) * 100) if self.session_results else 0
        
        print(f"⏱️  Test Duration: {duration_minutes} minutes")
        print(f"🔢 Total Interactions: {total_interactions}")
        print(f"✅ Success Rate: {successful}/{len(self.session_results)} ({success_rate:.1f}%)")
        
        # Performance analysis
        if self.running_stats["translation_times"]:
            trans_times = self.running_stats["translation_times"]
            print(f"\n📊 TRANSLATION PERFORMANCE:")
            print(f"  • Average: {statistics.mean(trans_times):.2f}s")
            print(f"  • Median: {statistics.median(trans_times):.2f}s")
            print(f"  • Min/Max: {min(trans_times):.2f}s / {max(trans_times):.2f}s")
            print(f"  • Std Dev: {statistics.stdev(trans_times):.2f}s" if len(trans_times) > 1 else "  • Std Dev: N/A")
        
        if self.running_stats["tts_times"]:
            tts_times = self.running_stats["tts_times"]
            print(f"\n🔊 TTS PERFORMANCE:")
            print(f"  • Average: {statistics.mean(tts_times):.2f}s")
            print(f"  • Median: {statistics.median(tts_times):.2f}s")
            print(f"  • Min/Max: {min(tts_times):.2f}s / {max(tts_times):.2f}s")
            print(f"  • Std Dev: {statistics.stdev(tts_times):.2f}s" if len(tts_times) > 1 else "  • Std Dev: N/A")
            
            # Cache analysis
            total_tts = self.running_stats["cache_hits"] + self.running_stats["cache_misses"]
            if total_tts > 0:
                cache_rate = self.running_stats["cache_hits"] / total_tts * 100
                print(f"  • Cache Hits: {self.running_stats['cache_hits']}/{total_tts} ({cache_rate:.1f}%)")
        
        if self.running_stats["total_times"]:
            total_times = self.running_stats["total_times"]
            print(f"\n🎯 OVERALL PERFORMANCE:")
            print(f"  • Average Total: {statistics.mean(total_times):.2f}s")
            print(f"  • Median Total: {statistics.median(total_times):.2f}s")
            print(f"  • 95th Percentile: {sorted(total_times)[int(len(total_times) * 0.95)]:.2f}s" if len(total_times) > 1 else f"  • 95th Percentile: {total_times[0]:.2f}s")
        
        # Error analysis
        if self.running_stats["errors"]:
            print(f"\n❌ ERROR ANALYSIS:")
            error_types = {}
            for error in self.running_stats["errors"]:
                error_msg = error["error"][:50]
                error_types[error_msg] = error_types.get(error_msg, 0) + 1
            
            for error_type, count in error_types.items():
                print(f"  • {error_type}: {count} occurrences")
        
        # Performance assessment
        print(f"\n🏆 PERFORMANCE ASSESSMENT:")
        
        if success_rate >= 95:
            print("  🎉 EXCELLENT - System performing exceptionally well")
        elif success_rate >= 85:
            print("  ✅ GOOD - System performing well with minor issues")
        elif success_rate >= 70:
            print("  ⚠️  FAIR - System functional but needs optimization")
        else:
            print("  🔧 NEEDS WORK - System requires debugging")
        
        # Latency assessment
        if self.running_stats["total_times"]:
            avg_latency = statistics.mean(self.running_stats["total_times"])
            if avg_latency <= 3.0:
                print("  ⚡ FAST - Excellent response times")
            elif avg_latency <= 6.0:
                print("  🟡 MODERATE - Acceptable response times")
            else:
                print("  🐌 SLOW - Response times need optimization")
    
    async def save_results(self):
        """Save detailed results to JSON file"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"voice_performance_results_{timestamp}.json"
        
        results_data = {
            "test_metadata": {
                "timestamp": datetime.now().isoformat(),
                "duration_minutes": self.test_duration_minutes,
                "interaction_interval": self.interaction_interval,
                "tts_enabled": self.has_api_key,
                "total_interactions": len(self.session_results)
            },
            "summary_stats": {
                "success_rate": len([r for r in self.session_results if r.get("success", False)]) / len(self.session_results) * 100 if self.session_results else 0,
                "avg_translation_time": statistics.mean(self.running_stats["translation_times"]) if self.running_stats["translation_times"] else None,
                "avg_tts_time": statistics.mean(self.running_stats["tts_times"]) if self.running_stats["tts_times"] else None,
                "avg_total_time": statistics.mean(self.running_stats["total_times"]) if self.running_stats["total_times"] else None,
                "cache_hit_rate": self.running_stats["cache_hits"] / (self.running_stats["cache_hits"] + self.running_stats["cache_misses"]) * 100 if (self.running_stats["cache_hits"] + self.running_stats["cache_misses"]) > 0 else 0
            },
            "detailed_results": self.session_results,
            "running_stats": self.running_stats
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            print(f"📄 Detailed results saved to: {filename}")
        except Exception as e:
            print(f"⚠️  Could not save results to file: {e}")

async def main():
    """Main function with command line arguments"""
    
    # Parse command line arguments
    duration = 15  # Default 15 minutes
    interval = 30  # Default 30 seconds
    
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print("Invalid duration argument, using default 15 minutes")
    
    if len(sys.argv) > 2:
        try:
            interval = int(sys.argv[2])
        except ValueError:
            print("Invalid interval argument, using default 30 seconds")
    
    print(f"🎙️ Natural Dialog Performance Test")
    print(f"Duration: {duration} minutes | Interval: {interval} seconds")
    
    tester = NaturalDialogTester()
    
    if not await tester.initialize():
        print("❌ Initialization failed")
        return False
    
    try:
        success = await tester.run_performance_test(duration, interval)
        return success
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        tester.print_final_results(len(tester.session_results), duration)
        await tester.save_results()
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        print(f"\n🎙️ Performance Test: {'✅ COMPLETED' if success else '❌ FAILED'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest crashed: {e}")
        sys.exit(1)