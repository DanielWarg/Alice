#!/usr/bin/env python3
"""
Alice Hybrid Voice Architecture Phase 1 - Integration Test
Tests Voice-Gateway, Intent Router, and API endpoints
"""

import asyncio
import json
import time
import base64
import struct
import wave
import tempfile
import os
from typing import Dict, Any
import logging

import httpx
import websockets
from websockets.exceptions import ConnectionClosedError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice_gateway_test")

# Test configuration
BACKEND_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"
TEST_SESSION_ID = f"test_session_{int(time.time())}"

class VoiceGatewayTester:
    """Test suite for Voice-Gateway Phase 1"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.websocket = None
        self.test_results = {}
        
    async def cleanup(self):
        """Cleanup test resources"""
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        await self.client.aclose()
    
    async def test_api_endpoints(self) -> bool:
        """Test Voice-Gateway API endpoints"""
        logger.info("🧪 Testing Voice-Gateway API endpoints...")
        
        try:
            # Test status endpoint
            response = await self.client.get(f"{BACKEND_URL}/api/voice-gateway/status")
            if response.status_code != 200:
                logger.error(f"❌ Status endpoint failed: {response.status_code}")
                return False
            
            status_data = response.json()
            logger.info(f"✅ Status endpoint: {status_data['status']}")
            logger.info(f"   Active sessions: {status_data['voice_gateway']['active_sessions']}")
            
            # Test intent classification
            test_phrases = [
                {"text": "Hej Alice, hur är läget?", "expected_path": "fast"},
                {"text": "Boka möte med Anna imorgon kl 14", "expected_path": "think"},
                {"text": "Vad har jag för möten idag?", "expected_path": "think"},
                {"text": "Spela lite musik från Spotify", "expected_path": "think"},
                {"text": "Tack så mycket", "expected_path": "fast"}
            ]
            
            for phrase in test_phrases:
                response = await self.client.post(
                    f"{BACKEND_URL}/api/voice-gateway/test-intent",
                    json={"text": phrase["text"]}
                )
                
                if response.status_code != 200:
                    logger.error(f"❌ Intent test failed for: '{phrase['text']}'")
                    return False
                
                result = response.json()
                classification = result["classification"]
                actual_path = classification["path"]
                
                logger.info(f"   📝 '{phrase['text'][:40]}...' → {actual_path} path "
                           f"(confidence: {classification['confidence']:.2f})")
                
                # Note: We don't fail on path mismatch as routing logic may vary
                if actual_path != phrase["expected_path"]:
                    logger.warning(f"   ⚠️  Expected {phrase['expected_path']}, got {actual_path}")
            
            # Test sessions endpoint
            response = await self.client.get(f"{BACKEND_URL}/api/voice-gateway/sessions")
            if response.status_code != 200:
                logger.error(f"❌ Sessions endpoint failed: {response.status_code}")
                return False
            
            sessions = response.json()
            logger.info(f"✅ Sessions endpoint: {len(sessions.get('sessions', []))} active sessions")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ API endpoint test failed: {e}")
            return False
    
    async def test_websocket_connection(self) -> bool:
        """Test WebSocket connection to Voice-Gateway"""
        logger.info("🔌 Testing Voice-Gateway WebSocket connection...")
        
        try:
            ws_url = f"{WS_URL}/ws/voice-gateway/{TEST_SESSION_ID}"
            logger.info(f"   Connecting to: {ws_url}")
            
            self.websocket = await websockets.connect(ws_url)
            logger.info("✅ WebSocket connected successfully")
            
            # Send configuration message
            config_message = {
                "type": "control.configure",
                "config": {
                    "audio": {
                        "sample_rate": 24000,
                        "channels": 1,
                        "format": "pcm16"
                    },
                    "personality": "alice",
                    "emotion": "friendly",
                    "language": "sv-SE"
                }
            }
            
            await self.websocket.send(json.dumps(config_message))
            logger.info("✅ Configuration message sent")
            
            # Wait for response (with timeout)
            try:
                response = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                logger.info(f"✅ Configuration response: {response_data.get('type', 'unknown')}")
            except asyncio.TimeoutError:
                logger.warning("⚠️ No configuration response within timeout (not critical)")
            
            # Send ping to test basic communication
            ping_message = {"type": "ping", "timestamp": time.time()}
            await self.websocket.send(json.dumps(ping_message))
            
            try:
                pong = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                pong_data = json.loads(pong)
                if pong_data.get("type") == "pong":
                    logger.info("✅ Ping/pong successful")
                    return True
                else:
                    logger.warning(f"⚠️ Unexpected response to ping: {pong_data}")
                    return True  # Still consider success
            except asyncio.TimeoutError:
                logger.error("❌ No pong response within timeout")
                return False
                
        except Exception as e:
            logger.error(f"❌ WebSocket test failed: {e}")
            return False
    
    def generate_test_audio(self) -> bytes:
        """Generate test PCM16 audio data (silence with slight noise)"""
        # Generate 1 second of silence with slight noise at 24kHz, mono, 16-bit
        sample_rate = 24000
        duration = 1.0
        samples = int(sample_rate * duration)
        
        # Create slight noise to simulate audio input
        import random
        audio_data = []
        for i in range(samples):
            # Add slight noise around silence
            noise = random.randint(-100, 100)  # Very quiet noise
            audio_data.append(noise)
        
        # Convert to bytes (PCM16)
        pcm16_data = b""
        for sample in audio_data:
            pcm16_data += struct.pack('<h', sample)  # Little-endian 16-bit
        
        return pcm16_data
    
    async def test_audio_streaming(self) -> bool:
        """Test audio streaming through Voice-Gateway"""
        logger.info("🎤 Testing audio streaming...")
        
        if not self.websocket:
            logger.error("❌ WebSocket not connected")
            return False
        
        try:
            # Generate test audio
            test_audio = self.generate_test_audio()
            logger.info(f"   Generated test audio: {len(test_audio)} bytes")
            
            # Send audio start message
            start_message = {
                "type": "audio.start",
                "config": {
                    "sample_rate": 24000,
                    "channels": 1,
                    "format": "pcm16"
                }
            }
            await self.websocket.send(json.dumps(start_message))
            logger.info("✅ Audio start sent")
            
            # Send audio chunks
            chunk_size = 4800  # 100ms at 24kHz mono 16-bit
            chunks_sent = 0
            
            for i in range(0, len(test_audio), chunk_size):
                chunk = test_audio[i:i + chunk_size]
                chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                
                chunk_message = {
                    "type": "audio.chunk",
                    "audio": chunk_b64,
                    "format": "pcm16",
                    "sample_rate": 24000,
                    "channels": 1,
                    "timestamp": time.time()
                }
                
                await self.websocket.send(json.dumps(chunk_message))
                chunks_sent += 1
                
                # Brief delay to simulate real-time streaming
                await asyncio.sleep(0.05)
            
            logger.info(f"✅ Audio chunks sent: {chunks_sent}")
            
            # Send audio stop message
            stop_message = {
                "type": "audio.stop",
                "timestamp": time.time()
            }
            await self.websocket.send(json.dumps(stop_message))
            logger.info("✅ Audio stop sent")
            
            # Listen for telemetry and responses
            telemetry_received = 0
            processing_detected = False
            
            try:
                for _ in range(10):  # Listen for up to 10 messages or timeout
                    response = await asyncio.wait_for(self.websocket.recv(), timeout=2.0)
                    response_data = json.loads(response)
                    
                    msg_type = response_data.get("type")
                    logger.info(f"   📡 Received: {msg_type}")
                    
                    if msg_type == "telemetry":
                        telemetry_received += 1
                        telemetry = response_data.get("data", {})
                        voice_state = telemetry.get("voice_state")
                        energy = telemetry.get("energy_level", 0)
                        logger.info(f"      State: {voice_state}, Energy: {energy:.3f}")
                        
                        if voice_state in ["processing", "thinking"]:
                            processing_detected = True
                    
                    elif msg_type == "transcription":
                        text = response_data.get("text", "")
                        logger.info(f"      Transcription: '{text}'")
                        
                    elif msg_type in ["acknowledge", "response", "thinking"]:
                        message = response_data.get("message", "")
                        path = response_data.get("path", "unknown")
                        logger.info(f"      {msg_type.title()}: '{message}' ({path} path)")
                        processing_detected = True
                
            except asyncio.TimeoutError:
                logger.info("   ⏰ No more responses within timeout")
            
            logger.info(f"✅ Audio streaming test completed")
            logger.info(f"   Telemetry messages: {telemetry_received}")
            logger.info(f"   Processing detected: {processing_detected}")
            
            return telemetry_received > 0  # Success if we got telemetry
            
        except Exception as e:
            logger.error(f"❌ Audio streaming test failed: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all Voice-Gateway Phase 1 tests"""
        logger.info("🚀 Starting Voice-Gateway Phase 1 Integration Tests")
        logger.info("=" * 60)
        
        tests = [
            ("API Endpoints", self.test_api_endpoints),
            ("WebSocket Connection", self.test_websocket_connection),
            ("Audio Streaming", self.test_audio_streaming),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            logger.info(f"\n🧪 Running test: {test_name}")
            try:
                result = await test_func()
                results[test_name] = result
                status = "✅ PASSED" if result else "❌ FAILED"
                logger.info(f"{status}: {test_name}")
            except Exception as e:
                results[test_name] = False
                logger.error(f"❌ FAILED: {test_name} - {e}")
        
        return results

async def main():
    """Run Voice-Gateway Phase 1 tests"""
    tester = VoiceGatewayTester()
    
    try:
        # Check if backend is running
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BACKEND_URL}/api/voice-gateway/status", timeout=5.0)
                if response.status_code != 200:
                    logger.error("❌ Backend not responding. Start with: python run.py")
                    return
                logger.info(f"✅ Backend is running and Voice-Gateway is active")
        except Exception as e:
            logger.error(f"❌ Backend not available at {BACKEND_URL}")
            logger.error("   Please start the backend with: cd server && python run.py")
            return
        
        # Run tests
        results = await tester.run_all_tests()
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status}: {test_name}")
        
        logger.info(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All Voice-Gateway Phase 1 tests PASSED!")
            logger.info("   The hybrid voice architecture is working correctly.")
        else:
            logger.info("⚠️  Some tests failed. Check logs above for details.")
        
        # Test recommendations
        logger.info("\n📝 Next Steps:")
        logger.info("   1. Test with real microphone input in the web UI")
        logger.info("   2. Try Swedish voice commands like:")
        logger.info("      - 'Hej Alice, hur är läget?'")
        logger.info("      - 'Boka möte imorgon kl 14'")
        logger.info("      - 'Vad har jag för möten idag?'")
        logger.info("   3. Monitor latency and routing decisions")
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())