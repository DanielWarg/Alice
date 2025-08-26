#!/usr/bin/env python3
"""
🎯 Simple WebRTC Test Server
Tests WebRTC audio track reception without OpenAI complexity
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio
import json
import logging
from typing import Dict, Any
from aiortc import RTCPeerConnection, RTCSessionDescription
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webrtc_test")

app = FastAPI(title="WebRTC Audio Track Test")

# Store active peer connections
peer_connections: Dict[str, RTCPeerConnection] = {}

@app.post("/api/webrtc/offer")
async def handle_webrtc_offer(request: Request):
    """Handle WebRTC offer and return answer"""
    try:
        data = await request.json()
        offer_sdp = data["offer"]
        session_id = data.get("sessionId", "test-session")
        
        logger.info(f"🔄 Received WebRTC offer for session {session_id}")
        
        # Create peer connection
        pc = RTCPeerConnection()
        peer_connections[session_id] = pc
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"🔗 WebRTC connection state: {pc.connectionState}")
            if pc.connectionState == "failed" or pc.connectionState == "closed":
                peer_connections.pop(session_id, None)
        
        @pc.on("track")
        async def on_track(track):
            logger.info(f"🎵 RECEIVED AUDIO TRACK! Kind: {track.kind}, ID: {track.id}")
            
            if track.kind == "audio":
                logger.info("🎤 Starting audio frame processing...")
                frame_count = 0
                
                try:
                    while True:
                        frame = await track.recv()
                        frame_count += 1
                        
                        if frame_count == 1:
                            logger.info(f"🎤 FIRST AUDIO FRAME! Format: {frame.format}, Sample rate: {frame.sample_rate}, Samples: {frame.samples}")
                        
                        if frame_count % 50 == 0:
                            logger.info(f"🎤 Processed {frame_count} audio frames")
                        
                except Exception as e:
                    logger.error(f"❌ Audio processing error: {e}")
        
        # Set remote description (offer)
        await pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))
        logger.info("✅ Set remote description (offer)")
        
        # Create answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        logger.info("✅ Created answer")
        
        return {
            "answer": pc.localDescription.sdp,
            "sessionId": session_id,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"❌ WebRTC offer handling error: {e}")
        return {"error": str(e)}, 500

@app.get("/test")
async def serve_test_page():
    """Serve simple WebRTC test page"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Simple WebRTC Audio Test</title>
</head>
<body>
    <h1>🎙️ WebRTC Audio Track Test</h1>
    <button id="startBtn">Start Audio Test</button>
    <div id="status"></div>
    <div id="log"></div>
    
    <script>
        let pc = null;
        let localStream = null;
        
        document.getElementById('startBtn').onclick = async () => {
            const log = (msg) => {
                console.log(msg);
                document.getElementById('log').innerHTML += msg + '<br>';
            };
            
            try {
                log('🎤 Getting microphone access...');
                localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                log('✅ Got microphone access');
                
                // Create peer connection
                pc = new RTCPeerConnection();
                
                // Add audio track
                localStream.getTracks().forEach(track => {
                    pc.addTrack(track, localStream);
                    log(`📤 Added ${track.kind} track to peer connection`);
                });
                
                // Create and send offer
                const offer = await pc.createOffer();
                await pc.setLocalDescription(offer);
                log('📤 Created offer');
                
                // Send to server
                const response = await fetch('/api/webrtc/offer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        offer: offer.sdp,
                        sessionId: 'browser-test'
                    })
                });
                
                const data = await response.json();
                log('📥 Received answer from server');
                
                // Set answer
                await pc.setRemoteDescription({
                    type: 'answer',
                    sdp: data.answer
                });
                log('✅ WebRTC connection established!');
                
            } catch (e) {
                log(`❌ Error: ${e}`);
            }
        };
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)

if __name__ == "__main__":
    logger.info("🚀 Starting Simple WebRTC Test Server on http://localhost:8002")
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")