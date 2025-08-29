#!/usr/bin/env python3
"""
🎙️ Alice Voice Pipeline - Complete Live Test
Testar hela pipeline: Swedish → English → MP3 Audio med detaljerad logging
"""

import os
import sys
import asyncio
import time
import logging
from pathlib import Path
from typing import Dict, Any
import json

# Setup comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('voice_pipeline_test.log')
    ]
)
logger = logging.getLogger("VoicePipelineTest")

# Add server to Python path
sys.path.append('server')

# Check if we have OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("test-"):
    print("⚠️  WARNING: No real OpenAI API key found!")
    print("   Set OPENAI_API_KEY environment variable for full TTS testing")
    print("   Current testing: Translation only")
    HAS_REAL_API_KEY = False
else:
    print(f"✅ OpenAI API key found: {OPENAI_API_KEY[:10]}...")
    HAS_REAL_API_KEY = True

class VoicePipelineCompleteTest:
    """Complete voice pipeline tester with detailed logging"""
    
    def __init__(self):
        self.input_processor = None
        self.orchestrator = None
        self.tts_client = None
        
        # Test results storage
        self.test_results = []
        self.audio_files_generated = []
        
        # Performance metrics
        self.total_tests = 0
        self.successful_tests = 0
        self.failed_tests = 0
        
        self.translation_times = []
        self.tts_times = []
        self.total_times = []
        
        print("🎙️ Initializing Complete Voice Pipeline Test")
        print("=" * 60)
        
    async def initialize_components(self):
        """Initialize all voice pipeline components"""
        
        try:
            print("📦 Loading voice pipeline components...")
            
            # Import components
            from server.voice.input_processor import InputProcessor
            from server.voice.orchestrator import VoiceOrchestrator
            
            self.input_processor = InputProcessor()
            self.orchestrator = VoiceOrchestrator()
            
            logger.info("✅ Input processor and orchestrator loaded")
            
            # Load TTS client if API key available
            if HAS_REAL_API_KEY:
                try:
                    from server.voice.tts_client import TTSClient
                    self.tts_client = TTSClient()
                    logger.info("✅ TTS client loaded with real API key")
                    
                    # Test TTS warm-up
                    print("🔥 Warming up TTS client...")
                    warmup_success = await self.tts_client.warm_up()
                    if warmup_success:
                        logger.info("✅ TTS client warmed up successfully")
                    else:
                        logger.warning("⚠️  TTS warm-up failed - continuing anyway")
                        
                except Exception as e:
                    logger.error(f"❌ TTS client failed to load: {e}")
                    self.tts_client = None
            else:
                logger.info("⚠️  TTS client skipped - no API key")
            
            # Test Ollama connection
            print("🔗 Testing Ollama connection...")
            try:
                health = await self.orchestrator.llm.health()
                if health.ok:
                    logger.info(f"✅ Ollama connected - TTFT: {health.tftt_ms:.1f}ms")
                else:
                    logger.error(f"❌ Ollama health check failed: {health.error}")
                    return False
            except Exception as e:
                logger.error(f"❌ Ollama connection failed: {e}")
                return False
            
            print("🚀 All components initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Component initialization failed: {e}")
            return False
    
    async def run_translation_test(self, test_name: str, source_type: str, swedish_text: str) -> Dict[str, Any]:
        """Run a single translation test with detailed metrics"""
        
        logger.info(f"🧪 Starting test: {test_name}")
        start_time = time.time()
        
        result = {
            "test_name": test_name,
            "source_type": source_type,
            "swedish_text": swedish_text,
            "success": False,
            "stages": {},
            "errors": []
        }
        
        try:
            # Stage 1: Input Processing
            stage_start = time.time()
            
            if source_type == "chat":
                input_pkg = self.input_processor.process_chat(swedish_text)
            elif source_type == "email":
                # Handle email format
                if "Ämne:" in swedish_text:
                    lines = swedish_text.split("\n", 2)
                    subject = lines[0].replace("Ämne: ", "")
                    body = lines[2] if len(lines) > 2 else ""
                else:
                    subject = "Test Email"
                    body = swedish_text
                input_pkg = self.input_processor.process_email(subject, body)
            elif source_type == "calendar":
                input_pkg = self.input_processor.process_calendar("Test Event", "imorgon", swedish_text)
            else:  # notification
                input_pkg = self.input_processor.process_notification(swedish_text)
            
            result["stages"]["input_processing"] = {
                "duration": time.time() - stage_start,
                "success": True
            }
            
            logger.info(f"✅ Input processed: {input_pkg.source_type}")
            
            # Stage 2: Translation
            stage_start = time.time()
            voice_output = await self.orchestrator.process(input_pkg)
            translation_duration = time.time() - stage_start
            
            # Check if translation succeeded
            is_fallback = voice_output.meta.get("fallback", False)
            
            result["stages"]["translation"] = {
                "duration": translation_duration,
                "success": not is_fallback,
                "output_text": voice_output.speak_text_en,
                "style": voice_output.style,
                "rate": voice_output.rate
            }
            
            if is_fallback:
                error_msg = voice_output.meta.get("error", "Translation fallback")
                result["errors"].append(f"Translation failed: {error_msg}")
                logger.error(f"❌ Translation failed: {error_msg}")
                result["total_time"] = time.time() - start_time
                return result
            else:
                logger.info(f"✅ Translation success: '{voice_output.speak_text_en}'")
                self.translation_times.append(translation_duration)
            
            # Stage 3: TTS (if available)
            if self.tts_client:
                stage_start = time.time()
                logger.info("🔊 Generating TTS audio...")
                
                try:
                    tts_result = await self.tts_client.synthesize(voice_output)
                    tts_duration = time.time() - stage_start
                    
                    result["stages"]["tts"] = {
                        "duration": tts_duration,
                        "success": tts_result["success"],
                        "provider": tts_result.get("provider", "unknown"),
                        "cached": tts_result.get("cached", False),
                        "audio_file": tts_result.get("audio_file"),
                        "text_only": tts_result.get("text_only", False)
                    }
                    
                    if tts_result["success"] and tts_result.get("audio_file"):
                        audio_path = Path(tts_result["audio_file"])
                        if audio_path.exists():
                            file_size = audio_path.stat().st_size
                            logger.info(f"✅ Audio generated: {audio_path.name} ({file_size} bytes)")
                            self.audio_files_generated.append(str(audio_path))
                            self.tts_times.append(tts_duration)
                        else:
                            result["errors"].append("Audio file not found after generation")
                            logger.error("❌ Audio file missing after generation")
                    elif tts_result.get("text_only"):
                        logger.warning("⚠️  TTS fell back to text-only mode")
                    else:
                        error_msg = tts_result.get("error", "TTS failed")
                        result["errors"].append(f"TTS failed: {error_msg}")
                        logger.error(f"❌ TTS failed: {error_msg}")
                        
                except Exception as e:
                    result["stages"]["tts"] = {
                        "duration": time.time() - stage_start,
                        "success": False,
                        "error": str(e)
                    }
                    result["errors"].append(f"TTS exception: {str(e)}")
                    logger.error(f"❌ TTS exception: {e}")
            else:
                result["stages"]["tts"] = {
                    "duration": 0,
                    "success": True,
                    "skipped": "No API key available"
                }
                logger.info("⚠️  TTS skipped - no API key")
            
            # Calculate total time and success
            result["total_time"] = time.time() - start_time
            result["success"] = all(
                stage["success"] for stage in result["stages"].values()
            )
            
            if result["success"]:
                logger.info(f"✅ Test '{test_name}' PASSED in {result['total_time']:.2f}s")
                self.successful_tests += 1
            else:
                logger.error(f"❌ Test '{test_name}' FAILED")
                self.failed_tests += 1
            
            self.total_times.append(result["total_time"])
            return result
            
        except Exception as e:
            result["total_time"] = time.time() - start_time
            result["errors"].append(f"Test exception: {str(e)}")
            logger.error(f"❌ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests += 1
            return result
    
    async def run_comprehensive_test_suite(self):
        """Run complete test suite with various Swedish inputs"""
        
        test_cases = [
            # Basic chat tests
            ("chat_greeting", "chat", "Hej Alice, hur mår du idag?"),
            ("chat_thanks", "chat", "Tack så mycket för hjälpen!"),
            ("chat_question", "chat", "Vad är klockan nu?"),
            ("chat_help", "chat", "Jag behöver hjälp med datorn"),
            
            # Email tests
            ("email_meeting", "email", "Ämne: Möte imorgon\n\nHej Anna,\n\nVi behöver flytta mötet från 10:00 till 14:00. Passar det dig?\n\nTack!\nJonas"),
            ("email_simple", "email", "Kan vi ses imorgon för att diskutera projektet?"),
            
            # Calendar tests
            ("calendar_dentist", "calendar", "Tandläkare imorgon kl 15:30 på Folktandvården Göteborg"),
            ("calendar_meeting", "calendar", "Projektstatus-möte på måndag kl 10:00 i konferensrummet"),
            
            # Notification tests
            ("notification_battery", "notification", "Batteri lågt - 15% kvar"),
            ("notification_update", "notification", "Ny systemuppdatering tillgänglig"),
            
            # Complex tests
            ("complex_email", "email", """Ämne: Projektrapport Q4 2024
            
Hej team,

Jag vill sammanfatta vårt arbete under Q4:

1. E-handelsplattform - 25% ökning av försäljning
2. Kundtjänst - 4.2/5.0 i kundnöjdhet  
3. Mobilapp - 40% fler användare

Nästa steg:
- Lansera nya funktioner i januari
- Expandera till Norge och Danmark
- Implementera AI-chat

Möte måndag kl 10:00 för att diskutera detaljer.

Mvh,
Sarah"""),
            
            # Swedish names and places
            ("swedish_places", "chat", "Jag reser från Stockholm till Göteborg via Västerås imorgon"),
            ("swedish_names", "chat", "Anna-Lena och Per-Erik kommer till middag på lördag"),
        ]
        
        print(f"\n🧪 Starting comprehensive test suite - {len(test_cases)} tests")
        print("=" * 60)
        
        for test_name, source_type, swedish_text in test_cases:
            self.total_tests += 1
            
            print(f"\n🔸 Test {self.total_tests}: {test_name}")
            print(f"   Type: {source_type}")
            print(f"   Input: '{swedish_text[:60]}{'...' if len(swedish_text) > 60 else ''}'")
            
            result = await self.run_translation_test(test_name, source_type, swedish_text)
            self.test_results.append(result)
            
            # Short delay between tests
            await asyncio.sleep(0.5)
        
        # Generate final report
        self.generate_final_report()
    
    def generate_final_report(self):
        """Generate comprehensive test report"""
        
        print("\n" + "=" * 80)
        print("🎙️ VOICE PIPELINE COMPLETE TEST REPORT")
        print("=" * 80)
        
        # Overall statistics
        success_rate = (self.successful_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"  Total Tests: {self.total_tests}")
        print(f"  Passed: {self.successful_tests} ✅")
        print(f"  Failed: {self.failed_tests} ❌")
        print(f"  Success Rate: {success_rate:.1f}%")
        
        # Performance metrics
        if self.total_times:
            avg_total = sum(self.total_times) / len(self.total_times)
            p95_total = sorted(self.total_times)[int(len(self.total_times) * 0.95)]
            
            print(f"\n⚡ PERFORMANCE METRICS:")
            print(f"  Average Total Time: {avg_total:.2f}s")
            print(f"  P95 Total Time: {p95_total:.2f}s")
            print(f"  Target <1.5s: {'✅' if avg_total < 1.5 else '❌'}")
            
            if self.translation_times:
                avg_trans = sum(self.translation_times) / len(self.translation_times)
                print(f"  Average Translation: {avg_trans:.2f}s")
            
            if self.tts_times:
                avg_tts = sum(self.tts_times) / len(self.tts_times)
                print(f"  Average TTS: {avg_tts:.2f}s")
        
        # Audio generation stats
        if self.audio_files_generated:
            total_size = sum(Path(f).stat().st_size for f in self.audio_files_generated if Path(f).exists())
            print(f"\n🔊 AUDIO GENERATION:")
            print(f"  Files Generated: {len(self.audio_files_generated)}")
            print(f"  Total Size: {total_size / 1024:.1f} KB")
            print(f"  Files: {', '.join(Path(f).name for f in self.audio_files_generated[-3:])}")
        else:
            print(f"\n🔊 AUDIO GENERATION: No audio files generated (no API key)")
        
        # Detailed test results
        print(f"\n📝 DETAILED TEST RESULTS:")
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            time_info = f"{result['total_time']:.2f}s"
            
            print(f"  {result['test_name']:20} {status} {time_info}")
            
            if result["errors"]:
                for error in result["errors"]:
                    print(f"    ⚠️  {error}")
            
            # Show translation result for passed tests
            if result["success"] and "translation" in result["stages"]:
                english_text = result["stages"]["translation"]["output_text"]
                print(f"    🗣️  '{english_text}'")
        
        # Save detailed results to file
        report_file = Path("voice_pipeline_test_report.json")
        with open(report_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": self.total_tests,
                    "successful_tests": self.successful_tests,
                    "failed_tests": self.failed_tests,
                    "success_rate": success_rate
                },
                "performance": {
                    "avg_total_time": avg_total if self.total_times else 0,
                    "p95_total_time": p95_total if self.total_times else 0,
                    "avg_translation_time": sum(self.translation_times) / len(self.translation_times) if self.translation_times else 0,
                    "avg_tts_time": sum(self.tts_times) / len(self.tts_times) if self.tts_times else 0
                },
                "audio_stats": {
                    "files_generated": len(self.audio_files_generated),
                    "total_size_bytes": sum(Path(f).stat().st_size for f in self.audio_files_generated if Path(f).exists())
                },
                "detailed_results": self.test_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
        
        # Final assessment
        print(f"\n🏆 FINAL ASSESSMENT:")
        if success_rate >= 90 and (not self.total_times or avg_total < 3.0):
            print("  🎉 VOICE PIPELINE READY FOR PRODUCTION!")
        elif success_rate >= 80:
            print("  ⚡ PIPELINE WORKS - NEEDS PERFORMANCE TUNING")
        else:
            print("  🔧 PIPELINE NEEDS DEBUGGING")
        
        print("\n" + "=" * 80)

async def main():
    """Main test runner"""
    
    print("🎙️ Alice Voice Pipeline - Complete Live Test")
    print("Testing full Swedish → English → MP3 pipeline")
    print("=" * 60)
    
    # Initialize test suite
    test_suite = VoicePipelineCompleteTest()
    
    # Initialize components
    if not await test_suite.initialize_components():
        print("❌ Failed to initialize components - aborting test")
        return False
    
    # Run comprehensive tests
    await test_suite.run_comprehensive_test_suite()
    
    return test_suite.successful_tests > 0

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)