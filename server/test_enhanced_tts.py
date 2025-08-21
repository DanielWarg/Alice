#!/usr/bin/env python3
"""
Test script for Enhanced Alice TTS System
Demonstrates all new TTS features and improvements
"""

import asyncio
import json
import base64
import time
from typing import Dict, Any
import httpx

class TTSTestSuite:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = httpx.AsyncClient()
    
    async def test_basic_tts(self):
        """Test basic TTS functionality"""
        print("🔊 Testing Basic TTS...")
        
        response = await self.session.post(
            f"{self.base_url}/api/tts/synthesize",
            json={
                "text": "Hej! Detta är ett grundläggande TTS-test.",
                "voice": "sv_SE-nst-medium"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Basic TTS: {data.get('success', False)}")
            print(f"   Voice: {data.get('voice', 'unknown')}")
            print(f"   Audio size: {len(data.get('audio_data', '')) // 1000}KB")
        else:
            print(f"❌ Basic TTS failed: {response.status_code}")
    
    async def test_enhanced_tts_personalities(self):
        """Test all personality types"""
        print("\n🎭 Testing Personality System...")
        
        personalities = ["alice", "formal", "casual"]
        test_text = "Hej! Jag visar olika personligheter i min röst."
        
        for personality in personalities:
            response = await self.session.post(
                f"{self.base_url}/api/tts/synthesize",
                json={
                    "text": f"{test_text} Detta är {personality} personlighet.",
                    "personality": personality,
                    "cache": True
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                settings = data.get('settings', {})
                print(f"✅ {personality.upper()}: speed={settings.get('speed', 0):.2f}, "
                      f"emotion={settings.get('emotion', 'unknown')}")
            else:
                print(f"❌ {personality} failed")
    
    async def test_emotional_range(self):
        """Test all emotional tones"""
        print("\n😊 Testing Emotional Range...")
        
        emotions = ["neutral", "happy", "calm", "confident", "friendly"]
        
        for emotion in emotions:
            response = await self.session.post(
                f"{self.base_url}/api/tts/synthesize",
                json={
                    "text": f"Jag pratar med {emotion} känsla nu.",
                    "emotion": emotion,
                    "personality": "alice",
                    "cache": True
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                quality = data.get('quality_score', 0)
                print(f"✅ {emotion.upper()}: kvalitet={quality}/10, "
                      f"cached={data.get('cached', False)}")
            else:
                print(f"❌ {emotion} failed")
    
    async def test_voice_quality_levels(self):
        """Test different voice quality levels"""
        print("\n🎯 Testing Voice Quality Levels...")
        
        voices = ["sv_SE-nst-medium", "sv_SE-nst-high", "sv_SE-lisa-medium"]
        
        for voice in voices:
            response = await self.session.post(
                f"{self.base_url}/api/tts/synthesize",
                json={
                    "text": f"Detta är {voice.split('-')[2]} kvalitet.",
                    "voice": voice,
                    "personality": "alice"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {voice}: tillgänglig")
            else:
                error_data = response.json()
                available = error_data.get('available', [])
                print(f"❌ {voice}: inte tillgänglig. Finns: {available}")
    
    async def test_caching_performance(self):
        """Test caching performance improvements"""
        print("\n⚡ Testing Cache Performance...")
        
        test_text = "Detta är ett cache-test för prestanda."
        
        # First request (no cache)
        start_time = time.time()
        response1 = await self.session.post(
            f"{self.base_url}/api/tts/synthesize",
            json={
                "text": test_text,
                "personality": "alice",
                "cache": True
            }
        )
        first_duration = time.time() - start_time
        
        # Second request (with cache)
        start_time = time.time()
        response2 = await self.session.post(
            f"{self.base_url}/api/tts/synthesize",
            json={
                "text": test_text,
                "personality": "alice",
                "cache": True
            }
        )
        second_duration = time.time() - start_time
        
        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()
            
            speedup = first_duration / second_duration if second_duration > 0 else 0
            
            print(f"✅ Cache test:")
            print(f"   First request: {first_duration:.3f}s (cached: {data1.get('cached', False)})")
            print(f"   Second request: {second_duration:.3f}s (cached: {data2.get('cached', False)})")
            print(f"   Speedup: {speedup:.1f}x")
        else:
            print("❌ Cache test failed")
    
    async def test_voice_info_endpoints(self):
        """Test voice information endpoints"""
        print("\n📋 Testing Voice Info Endpoints...")
        
        # Test voices endpoint
        response = await self.session.get(f"{self.base_url}/api/tts/voices")
        if response.status_code == 200:
            data = response.json()
            voices = data.get('voices', [])
            print(f"✅ Voices endpoint: {len(voices)} röster tillgängliga")
            
            for voice in voices[:2]:  # Show first 2
                print(f"   - {voice.get('name', 'unknown')}: "
                      f"{voice.get('quality', 'unknown')} kvalitet, "
                      f"naturalness {voice.get('naturalness', 0)}/10")
        else:
            print("❌ Voices endpoint failed")
        
        # Test personality endpoint
        response = await self.session.get(f"{self.base_url}/api/tts/personality/alice")
        if response.status_code == 200:
            data = response.json()
            settings = data.get('settings', {})
            print(f"✅ Alice personlighet: speed={settings.get('speed', 0)}, "
                  f"emotion_bias={settings.get('emotion_bias', 'unknown')}")
        else:
            print("❌ Personality endpoint failed")
    
    async def test_streaming_tts(self):
        """Test streaming TTS endpoint"""
        print("\n🌊 Testing Streaming TTS...")
        
        start_time = time.time()
        response = await self.session.post(
            f"{self.base_url}/api/tts/stream",
            json={
                "text": "Detta är ett streaming TTS-test för snabbare respons.",
                "personality": "alice",
                "emotion": "confident"
            }
        )
        
        if response.status_code == 200:
            audio_size = len(response.content)
            duration = time.time() - start_time
            
            print(f"✅ Streaming TTS:")
            print(f"   Response time: {duration:.3f}s")
            print(f"   Audio size: {audio_size // 1000}KB")
            print(f"   Content type: {response.headers.get('content-type', 'unknown')}")
        else:
            print(f"❌ Streaming TTS failed: {response.status_code}")
    
    async def test_fallback_system(self):
        """Test fallback system with invalid requests"""
        print("\n🛡️ Testing Fallback System...")
        
        # Test with non-existent voice
        response = await self.session.post(
            f"{self.base_url}/api/tts/synthesize",
            json={
                "text": "Test med ogiltig röst.",
                "voice": "non_existent_voice"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('fallback'):
                print("✅ Fallback system fungerar")
            elif data.get('error'):
                print(f"✅ Felhantering fungerar: {data.get('error', 'unknown')}")
        else:
            print("❌ Fallback test failed")
    
    async def run_comprehensive_test(self):
        """Run all TTS tests"""
        print("🚀 Starting Comprehensive Alice TTS Test Suite")
        print("=" * 60)
        
        try:
            await self.test_basic_tts()
            await self.test_enhanced_tts_personalities()
            await self.test_emotional_range()
            await self.test_voice_quality_levels()
            await self.test_caching_performance()
            await self.test_voice_info_endpoints()
            await self.test_streaming_tts()
            await self.test_fallback_system()
            
            print("\n" + "=" * 60)
            print("🎉 Test Suite Completed!")
            print("\n💡 För att testa frontend-integration:")
            print("   1. Öppna Alice i webbläsaren")
            print("   2. Gå till Voice/TTS-sektionen")
            print("   3. Klicka på 'Test TTS' knappen")
            print("   4. Prova olika personligheter och känslor")
            
        except Exception as e:
            print(f"\n❌ Test suite error: {e}")
        
        finally:
            await self.session.aclose()

async def main():
    """Main test runner"""
    test_suite = TTSTestSuite()
    await test_suite.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())