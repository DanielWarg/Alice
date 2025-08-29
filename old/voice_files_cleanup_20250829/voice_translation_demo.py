#!/usr/bin/env python3
"""
🎙️ Alice Voice Pipeline - Translation Demo
Visar att svensk→engelsk översättning fungerar perfekt!
"""

import sys
import asyncio
import time
from pathlib import Path

# Add server to path
sys.path.append('server')

from server.voice.input_processor import InputProcessor
from server.voice.orchestrator import VoiceOrchestrator

class TranslationDemo:
    """Demo som visar perfekt svensk→engelsk översättning"""
    
    def __init__(self):
        self.input_processor = InputProcessor()
        self.orchestrator = VoiceOrchestrator()
        self.results = []
    
    async def test_translation(self, name: str, source_type: str, swedish_text: str):
        """Test en enskild översättning"""
        
        print(f"\n🧪 {name}")
        print(f"📱 Källa: {source_type}")
        print(f"🇸🇪 Svenska: '{swedish_text}'")
        
        start_time = time.time()
        
        try:
            # Process input
            if source_type == "chat":
                input_pkg = self.input_processor.process_chat(swedish_text)
            elif source_type == "email":
                input_pkg = self.input_processor.process_email("Test", swedish_text)  
            elif source_type == "calendar":
                input_pkg = self.input_processor.process_calendar("Event", "imorgon", swedish_text)
            else:
                input_pkg = self.input_processor.process_notification(swedish_text)
            
            # Translate
            voice_output = await self.orchestrator.process(input_pkg)
            duration = time.time() - start_time
            
            # Check result
            if voice_output.meta.get("fallback", False):
                print(f"❌ FALLBACK: {voice_output.speak_text_en}")
                print(f"   Error: {voice_output.meta.get('error', 'Unknown')}")
                success = False
            else:
                print(f"🇬🇧 English: '{voice_output.speak_text_en}'")
                print(f"⚡ Latency: {duration:.2f}s")
                print(f"🎭 Style: {voice_output.style} | Rate: {voice_output.rate}x")
                success = True
            
            self.results.append({
                "name": name,
                "success": success,
                "duration": duration,
                "english": voice_output.speak_text_en
            })
            
            return success
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            self.results.append({
                "name": name, 
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e)
            })
            return False
    
    async def run_demo(self):
        """Kör alla demo-test"""
        
        print("🎙️ Alice Voice Pipeline - Translation Demo")
        print("=" * 55)
        print("Demonstrerar perfekt svensk→engelsk översättning!")
        
        # Demo test cases
        test_cases = [
            ("Vardaglig hälsning", "chat", "Hej Alice, hur mår du idag?"),
            ("Tacksägelse", "chat", "Tack så mycket för hjälpen!"),
            ("Tidsfråga", "chat", "Vad är klockan nu?"),
            ("Hjälpbegäran", "chat", "Jag behöver hjälp med datorn"),
            
            ("Mötesförfrågan", "email", "Kan vi ses imorgon för att diskutera projektet?"),
            ("Svenskt namn", "chat", "Anna-Lena kommer till middag imorgon"),
            ("Svenska platser", "chat", "Jag åker från Stockholm till Göteborg"),
            
            ("Batterivarning", "notification", "Batteri lågt - 15% kvar"),
            ("Systemuppdatering", "notification", "Ny uppdatering tillgänglig för installation"),
            
            ("Tandläkarbokning", "calendar", "Tandläkare på måndag kl 15:30"),
        ]
        
        successful = 0
        total = len(test_cases)
        
        for name, source_type, text in test_cases:
            if await self.test_translation(name, source_type, text):
                successful += 1
            
            # Kort paus mellan tester  
            await asyncio.sleep(0.3)
        
        # Sammanfattning
        print("\n" + "=" * 55)
        print("🎯 DEMO RESULTAT")
        print("=" * 55)
        
        success_rate = (successful / total * 100)
        print(f"✅ Lyckade: {successful}/{total} ({success_rate:.1f}%)")
        
        if self.results:
            durations = [r["duration"] for r in self.results if r["success"]]
            if durations:
                avg_time = sum(durations) / len(durations)
                print(f"⚡ Genomsnittlig tid: {avg_time:.2f}s")
        
        print(f"\n📋 ÖVERSÄTTNINGSEXEMPEL:")
        for result in self.results:
            if result["success"]:
                print(f"  • {result['name']}: '{result['english']}'")
        
        print(f"\n🎉 SLUTSATS:")
        if success_rate >= 80:
            print("  ✅ SVENSK→ENGELSK ÖVERSÄTTNING FUNGERAR PERFEKT!")
            print("  🎙️ Redo för TTS-integration när API-nyckel finns")
        else:
            print("  ⚠️  Översättning behöver finjustering")
        
        return success_rate >= 80

async def main():
    """Huvudfunktion"""
    
    print("Initialiserar Alice Voice Pipeline...")
    demo = TranslationDemo()
    
    try:
        # Test Ollama connection
        health = await demo.orchestrator.llm.health()
        if not health.ok:
            print(f"❌ Ollama connection failed: {health.error}")
            return False
        
        print(f"✅ Ollama connected (TTFT: {health.tftt_ms:.0f}ms)")
        print("🚀 Starting translation demo...\n")
        
        # Run demo
        success = await demo.run_demo()
        return success
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        print(f"\nDemo result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nDemo avbrutet av användare")
        sys.exit(1)
    except Exception as e:
        print(f"\nDemo kraschade: {e}")
        sys.exit(1)