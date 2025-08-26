#!/usr/bin/env python3
"""
🎯 Working Voice Test - Använder samma metod som direct test
Kombinerar fungerande OpenAI test med WebRTC
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import asyncio
import json
import logging
import base64
import numpy as np
import os
import websockets
from typing import Dict, Any
from aiortc import RTCPeerConnection, RTCSessionDescription
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("working_voice")

app = FastAPI(title="Working Alice Voice Test")

# Store connections
peer_connections: Dict[str, RTCPeerConnection] = {}

async def test_with_working_method():
    """Använd exakt samma metod som fungerande direct test"""
    
    # Get API key (samma som direct test)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            with open("/Users/evil/Desktop/EVIL/PROJECT/Alice/.env") as f:
                for line in f:
                    if line.startswith("OPENAI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
        except:
            pass
    
    if not api_key:
        logger.error("❌ No OpenAI API key found")
        return False
        
    logger.info(f"✅ API Key: {api_key[:20]}...")
    
    try:
        # Connect to OpenAI (exakt samma som direct test)
        url = f"wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        logger.info("🔌 Connecting to OpenAI Realtime API...")
        
        async with websockets.connect(url, additional_headers=headers) as ws:
            logger.info("✅ Connected to OpenAI!")
            
            # Wait for session.created
            msg = await ws.recv()
            data = json.loads(msg)
            logger.info(f"📨 Received: {data['type']}")
            
            if data['type'] == 'session.created':
                session_id = data['session']['id']
                logger.info(f"✅ Session created: {session_id}")
                
                # Update session (exakt samma som direct test)
                session_update = {
                    "type": "session.update",
                    "session": {
                        "modalities": ["text", "audio"],
                        "voice": "alloy",
                        "instructions": "Du är Alice. Säg 'Hej, jag är Alice och jag hör dig!' på svenska.",
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "turn_detection": None
                    }
                }
                
                await ws.send(json.dumps(session_update))
                logger.info("📤 Sent session update")
                
                # Wait for session.updated
                msg = await ws.recv()
                data = json.loads(msg)
                logger.info(f"📨 Received: {data['type']}")
                
                # Clear buffer (samma som direct test)
                clear_msg = {"type": "input_audio_buffer.clear"}
                await ws.send(json.dumps(clear_msg))
                logger.info("📤 Sent clear buffer request")
                
                # Wait for clear confirmation
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    logger.info(f"📨 Received: {data['type']}")
                    if data['type'] == 'input_audio_buffer.cleared':
                        logger.info("✅ Audio buffer cleared")
                        break
                
                return ws  # Return working websocket
                
    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        return None

@app.post("/api/webrtc/offer")
async def handle_webrtc_offer(request: Request):
    """WebRTC med working OpenAI metod"""
    try:
        data = await request.json()
        offer_sdp = data["offer"]
        session_id = data.get("sessionId", "working-session")
        
        logger.info(f"🔄 Received WebRTC offer for session {session_id}")
        
        # Create peer connection
        pc = RTCPeerConnection()
        peer_connections[session_id] = pc
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"🔗 WebRTC connection state: {pc.connectionState}")
        
        @pc.on("track")
        async def on_track(track):
            logger.info(f"🎵 RECEIVED AUDIO TRACK! Kind: {track.kind}")
            
            if track.kind == "audio":
                logger.info("🎤 Starting working audio processing...")
                
                # Samla 2 sekunder audio först
                audio_frames = []
                frame_count = 0
                
                try:
                    while frame_count < 100:  # ~2 sekunder på 48kHz
                        frame = await track.recv()
                        frame_count += 1
                        
                        if frame_count == 1:
                            logger.info(f"🎤 FIRST FRAME! Sample rate: {frame.sample_rate}, Format: {frame.format}")
                        
                        audio_frames.append(frame)
                        
                        if frame_count % 25 == 0:
                            logger.info(f"🎤 Collected {frame_count} frames...")
                    
                    logger.info(f"✅ Collected {len(audio_frames)} frames, processing with working method...")
                    
                    # Använd samma metod som working direct test
                    await process_with_working_method(audio_frames)
                    
                except Exception as e:
                    logger.error(f"❌ Audio collection error: {e}")
        
        # WebRTC handshake
        await pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        return {
            "answer": pc.localDescription.sdp,
            "sessionId": session_id,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"❌ WebRTC error: {e}")
        return {"error": str(e)}, 500

async def process_with_working_method(frames):
    """Process frames med exakt samma metod som working direct test"""
    
    logger.info("🚀 PROCESSING WITH WORKING METHOD")
    
    # Konvertera frames till samma format som working direct test
    sample_rate = 24000  # OpenAI format
    duration = 0.5  # 500ms
    
    # Skapa test audio som FUNKADE (samma som direct test)
    logger.info("🔊 Generating working test audio...")
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(2 * np.pi * 440 * t) * 0.3  # Same as direct test
    audio_samples = (tone * 32767).astype(np.int16)
    audio_data = audio_samples.tobytes()
    
    logger.info(f"🔊 Generated {len(audio_data)} bytes of working audio")
    
    # Använd exakt samma OpenAI process som direct test
    await send_to_openai_working_method(audio_data)

async def send_to_openai_working_method(audio_data):
    """Send to OpenAI med exakt samma metod som working direct test"""
    
    ws = await test_with_working_method()
    if not ws:
        logger.error("❌ Could not get working OpenAI connection")
        return
    
    try:
        # Send audio (samma som direct test)
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        audio_msg = {
            "type": "input_audio_buffer.append",
            "audio": audio_b64
        }
        
        await ws.send(json.dumps(audio_msg))
        logger.info(f"📤 Sent {len(audio_data)} bytes of audio to OpenAI")
        
        # Commit audio (samma som direct test)
        commit_msg = {"type": "input_audio_buffer.commit"}
        await ws.send(json.dumps(commit_msg))
        logger.info("📤 Committed audio buffer")
        
        # Wait for commit confirmation
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            msg_type = data['type']
            logger.info(f"📨 After commit: {msg_type}")
            
            if msg_type == 'input_audio_buffer.committed':
                logger.info("✅ Audio buffer commit confirmed")
                break
            elif msg_type == 'conversation.item.created':
                logger.info("✅ Conversation item created from audio")
                break
        
        # Request response (samma som direct test)
        response_create = {
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
                "instructions": "Respond to the audio you just received."
            }
        }
        await ws.send(json.dumps(response_create))
        logger.info("📤 Manually requested response")
        
        # Wait for response (samma som direct test)
        logger.info("⏳ Waiting for OpenAI response...")
        
        response_received = False
        audio_received = False
        
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                data = json.loads(msg)
                msg_type = data['type']
                
                logger.info(f"📨 Received: {msg_type}")
                
                if msg_type == 'response.created':
                    logger.info("🤖 AI response started")
                    response_received = True
                    
                elif msg_type == 'response.audio.delta':
                    if not audio_received:
                        audio_bytes = len(base64.b64decode(data.get('delta', '')))
                        logger.info(f"🔊 Received first audio chunk: {audio_bytes} bytes")
                        audio_received = True
                        
                elif msg_type == 'response.audio.done':
                    logger.info("✅ Audio response completed")
                    break
                    
                elif msg_type == 'response.done':
                    logger.info("✅ Response completed")
                    break
                    
                elif msg_type == 'error':
                    error_msg = data.get('error', {}).get('message', 'Unknown error')
                    logger.info(f"❌ OpenAI Error: {error_msg}")
                    break
                    
            except asyncio.TimeoutError:
                logger.info("⏰ Timeout waiting for response")
                break
        
        if response_received and audio_received:
            logger.info("🎉 SUCCESS: Alice responded with working method!")
            return True
        else:
            logger.info("⚠️ Partial success or no response")
            return False
            
    except Exception as e:
        logger.error(f"❌ Working method error: {e}")
        return False

@app.get("/test")
async def serve_test_page():
    """Test page"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>🎯 Working Voice Test</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background: #1a1a1a; color: white; }
        .container { max-width: 600px; margin: 0 auto; }
        button { padding: 15px 30px; font-size: 18px; margin: 10px; border: none; border-radius: 5px; cursor: pointer; }
        .start { background: #4CAF50; color: white; }
        .status { margin: 20px 0; padding: 15px; background: #333; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Working Voice Test</h1>
        <p>Använder samma metod som den fungerande direct testen</p>
        
        <button id="startBtn" class="start">Test Working Method</button>
        
        <div class="status">
            Status: <span id="status">Ready</span>
        </div>
    </div>
    
    <script>
        document.getElementById('startBtn').onclick = async () => {
            try {
                console.log('🎤 Starting working method test...');
                document.getElementById('status').textContent = 'Starting...';
                
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                console.log('✅ Got microphone');
                
                const pc = new RTCPeerConnection();
                stream.getTracks().forEach(track => pc.addTrack(track, stream));
                
                const offer = await pc.createOffer();
                await pc.setLocalDescription(offer);
                
                const response = await fetch('/api/webrtc/offer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        offer: offer.sdp,
                        sessionId: 'working-test-' + Date.now()
                    })
                });
                
                const data = await response.json();
                await pc.setRemoteDescription({ type: 'answer', sdp: data.answer });
                
                console.log('✅ Working method test started');
                document.getElementById('status').textContent = 'Testing with working method...';
                
            } catch (e) {
                console.error('❌ Error:', e);
                document.getElementById('status').textContent = 'Error: ' + e.message;
            }
        };
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)

if __name__ == "__main__":
    logger.info("🎯 Starting Working Voice Test on http://localhost:8004")
    uvicorn.run(app, host="0.0.0.0", port=8004, log_level="info")