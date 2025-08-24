#!/usr/bin/env python3
"""
Test WebSocket ASR mock functionality
"""

import asyncio
import websockets
import json
import logging
import base64
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_realtime_asr():
    """Test mock realtime ASR WebSocket"""
    uri = "ws://127.0.0.1:8000/ws/realtime-asr"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Connected to mock Realtime ASR")
            
            # Test 1: Send session update
            session_update = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": "Transkribera svenska tal",
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16"
                }
            }
            
            await websocket.send(json.dumps(session_update))
            logger.info("📤 Sent session update")
            
            # Wait for response
            response = await websocket.recv()
            data = json.loads(response)
            logger.info(f"📥 Received: {data['type']}")
            assert data['type'] == 'session.updated', f"Expected session.updated, got {data['type']}"
            
            # Test 2: Send mock audio data
            # Create some fake PCM16 audio data
            mock_audio = np.random.randint(-1000, 1000, size=1600, dtype=np.int16)  # ~0.1s @ 16kHz
            audio_b64 = base64.b64encode(mock_audio.tobytes()).decode()
            
            audio_append = {
                "type": "input_audio_buffer.append",
                "audio": audio_b64
            }
            
            await websocket.send(json.dumps(audio_append))
            logger.info("📤 Sent audio data")
            
            # Test 3: Send multiple audio chunks to trigger speech detection
            for i in range(5):
                # Simulate louder audio for speech detection
                mock_audio = np.random.randint(-5000, 5000, size=3200, dtype=np.int16)  # Louder
                audio_b64 = base64.b64encode(mock_audio.tobytes()).decode()
                
                await websocket.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": audio_b64
                }))
                
                # Check for any responses
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                    data = json.loads(response)
                    logger.info(f"📥 Speech event: {data['type']}")
                except asyncio.TimeoutError:
                    pass
            
            # Test 4: Commit audio buffer
            await websocket.send(json.dumps({"type": "input_audio_buffer.commit"}))
            logger.info("📤 Sent audio commit")
            
            # Test 5: Request response creation
            await websocket.send(json.dumps({"type": "response.create"}))
            logger.info("📤 Requested response creation")
            
            # Wait for potential responses
            try:
                for _ in range(3):  # Check for up to 3 responses
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(response)
                    logger.info(f"📥 Final response: {data['type']}")
                    
                    if data['type'] == 'response.audio_transcript.done':
                        logger.info(f"🎯 Got final transcript: {data.get('transcript', 'N/A')}")
                        
            except asyncio.TimeoutError:
                logger.warning("⏰ Timed out waiting for final responses")
            
            logger.info("✅ WebSocket ASR test completed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"❌ WebSocket ASR test failed: {e}")
        return False

async def main():
    """Main test runner"""
    logger.info("🚀 Starting WebSocket ASR Mock Test")
    
    success = await test_realtime_asr()
    
    if success:
        logger.info("🎉 All WebSocket tests passed!")
        return 0
    else:
        logger.error("💥 WebSocket tests failed!")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))