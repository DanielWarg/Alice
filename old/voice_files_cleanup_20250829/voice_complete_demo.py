#!/usr/bin/env python3
"""
🎙️ Alice Voice Pipeline - Complete Demo med TTS
Testar hela pipeline: Swedish → English → MP3 Audio
"""

import os
import sys
import asyncio
import time
from pathlib import Path

# Add server to path
sys.path.append('server')

from server.voice.input_processor import InputProcessor
from server.voice.orchestrator import VoiceOrchestrator
from server.voice.tts_client import TTSClient

class CompleteVoiceDemo:
    """Complete demo med TTS och MP3-generering"""
    
    def __init__(self):
        self.input_processor = InputProcessor()
        self.orchestrator = VoiceOrchestrator()
        self.tts_client = None
        self.results = []
        
        # Check if we have API key
        self.has_api_key = bool(os.getenv("OPENAI_API_KEY") and not os.getenv("OPENAI_API_KEY").startswith("test-"))
    
    async def initialize(self):
        """Initialize TTS client if API key available"""
        
        if self.has_api_key:
            try:
                self.tts_client = TTSClient()
                print("✅ TTS client initialized with OpenAI API")
                
                # Test warm-up
                print("🔥 Warming up TTS...")
                warmup = await self.tts_client.warm_up()
                print(f"{'✅' if warmup else '⚠️ '} TTS warm-up {'succeeded' if warmup else 'failed'}")
                
                return True
            except Exception as e:
                print(f"❌ TTS client failed: {e}")
                return False
        else:
            print("⚠️  No OpenAI API key - translation only")
            return True
    
    async def test_complete_pipeline(self, name: str, source_type: str, swedish_text: str):
        """Test complete pipeline med TTS"""
        
        print(f"\n🧪 {name}")
        print(f"📱 Källa: {source_type}")
        print(f"🇸🇪 Svenska: '{swedish_text}'")
        
        total_start = time.time()
        result = {"name": name, "success": False}
        
        try:
            # Step 1: Process input
            if source_type == "chat":
                input_pkg = self.input_processor.process_chat(swedish_text)
            elif source_type == "email":
                input_pkg = self.input_processor.process_email("Test", swedish_text)
            elif source_type == "calendar":
                input_pkg = self.input_processor.process_calendar("Event", "imorgon", swedish_text)
            else:
                input_pkg = self.input_processor.process_notification(swedish_text)
            
            # Step 2: Translation
            trans_start = time.time()
            voice_output = await self.orchestrator.process(input_pkg)
            trans_time = time.time() - trans_start
            
            if voice_output.meta.get("fallback", False):
                print(f"❌ Translation failed: {voice_output.meta.get('error')}")
                return result
            
            print(f"🇬🇧 English: '{voice_output.speak_text_en}'")
            print(f"⚡ Translation: {trans_time:.2f}s")
            
            result["english_text"] = voice_output.speak_text_en
            result["translation_time"] = trans_time
            
            # Step 3: TTS (if available)
            if self.tts_client:
                tts_start = time.time()
                print("🔊 Generating audio...")
                
                tts_result = await self.tts_client.synthesize(voice_output)
                tts_time = time.time() - tts_start
                
                if tts_result["success"] and tts_result.get("audio_file"):
                    audio_path = Path(tts_result["audio_file"])
                    if audio_path.exists():
                        file_size = audio_path.stat().st_size
                        duration = tts_result.get("duration", 0)
                        provider = tts_result.get("provider", "unknown")
                        cached = tts_result.get("cached", False)
                        
                        print(f"🎵 Audio: {audio_path.name} ({file_size} bytes)")
                        print(f"🔊 Provider: {provider} | Cached: {'✅' if cached else '❌'}")
                        print(f"⏱️  TTS: {tts_time:.2f}s | Est. duration: {duration:.1f}s")
                        
                        result["audio_file"] = str(audio_path)
                        result["audio_size"] = file_size
                        result["tts_time"] = tts_time
                        result["audio_duration"] = duration
                        result["cached"] = cached
                        result["provider"] = provider
                        
                    else:
                        print("❌ Audio file not found")
                        return result
                        
                elif tts_result.get("text_only"):
                    print(f"⚠️  TTS fallback to text-only: {tts_result.get('error')}")
                    result["text_only"] = True
                else:
                    print(f"❌ TTS failed: {tts_result.get('error')}")
                    return result
            else:
                print("⚠️  TTS skipped - no API key")
                result["tts_skipped"] = True
            
            # Calculate total time
            result["total_time"] = time.time() - total_start
            result["success"] = True
            
            print(f"🎯 Total time: {result['total_time']:.2f}s")
            
            self.results.append(result)
            return result
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            result["error"] = str(e)
            result["total_time"] = time.time() - total_start
            self.results.append(result)
            return result
    
    async def run_complete_demo(self):
        """Run complete demo med alla test cases"""
        
        print("🎙️ Alice Voice Pipeline - Complete Demo")
        print("=" * 55)
        print("Testing Swedish → English → MP3 Audio")
        
        # Initialize
        if not await self.initialize():
            print("❌ Initialization failed")
            return False
        
        # Demo test cases - fokus på olika typer
        test_cases = [
            ("Enkel hälsning", "chat", "Hej Alice!"),
            ("Fråga om tid", "chat", "Vad är klockan nu?"),
            ("Svenska namn", "chat", "Anna-Lena kommer imorgon"),
            ("Mötesbokning", "email", "Kan vi ses på måndag kl 14:00?"),
            ("Batteriarning", "notification", "Batteri lågt - 15% kvar"),
        ]
        
        print(f"\n🚀 Running {len(test_cases)} complete pipeline tests...\n")
        
        successful = 0
        
        for name, source_type, text in test_cases:
            result = await self.test_complete_pipeline(name, source_type, text)
            
            if result["success"]:
                successful += 1
            
            # Paus mellan tester
            await asyncio.sleep(1)
        
        # Generate summary
        print("\n" + "=" * 55)
        print("🎯 COMPLETE DEMO SUMMARY")  
        print("=" * 55)
        
        success_rate = (successful / len(test_cases) * 100) if test_cases else 0
        print(f"✅ Successful: {successful}/{len(test_cases)} ({success_rate:.1f}%)")
        
        # Performance stats
        if self.results:
            successful_results = [r for r in self.results if r["success"]]
            
            if successful_results:
                # Translation stats
                trans_times = [r["translation_time"] for r in successful_results if "translation_time" in r]
                if trans_times:
                    avg_trans = sum(trans_times) / len(trans_times)
                    print(f"⚡ Avg Translation Time: {avg_trans:.2f}s")
                
                # TTS stats
                tts_times = [r["tts_time"] for r in successful_results if "tts_time" in r]
                if tts_times:
                    avg_tts = sum(tts_times) / len(tts_times)
                    print(f"🔊 Avg TTS Time: {avg_tts:.2f}s")
                
                # Total stats
                total_times = [r["total_time"] for r in successful_results]
                avg_total = sum(total_times) / len(total_times)
                print(f"🎯 Avg Total Time: {avg_total:.2f}s")
                
                # Audio stats
                audio_files = [r for r in successful_results if "audio_file" in r]
                if audio_files:
                    total_size = sum(r["audio_size"] for r in audio_files)
                    cached_count = sum(1 for r in audio_files if r.get("cached"))
                    print(f"🎵 Audio Files: {len(audio_files)} generated ({total_size/1024:.1f} KB)")
                    print(f"💾 Cache Hit Rate: {cached_count}/{len(audio_files)} ({cached_count/len(audio_files)*100:.1f}%)")
        
        # Show examples
        print(f"\n📋 TRANSLATION EXAMPLES:")
        for result in self.results:
            if result["success"] and "english_text" in result:
                print(f"  • {result['name']}: '{result['english_text']}'")
        
        # Final assessment
        print(f"\n🏆 FINAL ASSESSMENT:")
        if success_rate >= 80:
            if self.has_api_key and any("audio_file" in r for r in self.results if r["success"]):
                print("  🎉 COMPLETE VOICE PIPELINE WORKING!")
                print("  🔊 Swedish → English → MP3 Audio ✅")
                print("  🚀 Ready for integration!")
            else:
                print("  ✅ TRANSLATION PERFECT - TTS NEEDS API KEY")
        else:
            print("  🔧 PIPELINE NEEDS DEBUGGING")
        
        return success_rate >= 80

async def main():
    """Main demo function"""
    
    demo = CompleteVoiceDemo()
    
    # Test Ollama connection
    try:
        health = await demo.orchestrator.llm.health()
        if not health.ok:
            print(f"❌ Ollama connection failed: {health.error}")
            return False
        
        print(f"✅ Ollama connected (TTFT: {health.tftt_ms:.0f}ms)")
        
        # Run demo
        success = await demo.run_complete_demo()
        return success
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        print(f"\n🎙️ Complete Demo: {'✅ SUCCESS' if success else '❌ FAILED'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nDemo interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nDemo crashed: {e}")
        sys.exit(1)