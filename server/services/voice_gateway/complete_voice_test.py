#!/usr/bin/env python3
"""
🎙️ Komplett Alice Rösttest - WebRTC + OpenAI Realtime API
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
logger = logging.getLogger("complete_voice")

app = FastAPI(title="Alice Complete Voice Test")

# Store connections
peer_connections: Dict[str, RTCPeerConnection] = {}
openai_connections: Dict[str, Any] = {}

class VoiceSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.openai_ws = None
        self.audio_buffer = []
        self.is_processing = False

async def connect_to_openai(session: VoiceSession):
    """Anslut till OpenAI Realtime API"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Försök läsa från .env
        try:
            with open("/Users/evil/Desktop/EVIL/PROJECT/Alice/.env") as f:
                for line in f:
                    if line.startswith("OPENAI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
        except:
            pass
    
    if not api_key:
        logger.error("❌ Ingen OpenAI API key hittad!")
        return False
    
    try:
        url = f"wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        session.openai_ws = await websockets.connect(url, additional_headers=headers)
        logger.info("✅ Ansluten till OpenAI Realtime API")
        
        # Vänta på session.created
        msg = await session.openai_ws.recv()
        data = json.loads(msg)
        if data['type'] == 'session.created':
            logger.info(f"✅ OpenAI session skapad: {data['session']['id']}")
            
            # Konfigurera session för svenska input, engelsk röst
            session_update = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "voice": "alloy",
                    "instructions": "Du är Alice. Svara på svenska kort och naturligt på vad användaren säger.",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "turn_detection": None  # Manuell kontroll
                }
            }
            
            await session.openai_ws.send(json.dumps(session_update))
            msg = await session.openai_ws.recv()
            data = json.loads(msg)
            logger.info(f"📤 Session uppdaterad: {data['type']}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ OpenAI anslutning misslyckades: {e}")
        return False

async def send_audio_to_openai(session: VoiceSession, audio_data: bytes):
    """Skicka audio till OpenAI och få röstsvar"""
    if not session.openai_ws:
        return
    
    try:
        # Rensa buffer först
        clear_msg = {"type": "input_audio_buffer.clear"}
        await session.openai_ws.send(json.dumps(clear_msg))
        
        # Vänta på clear confirmation
        while True:
            msg = await session.openai_ws.recv()
            data = json.loads(msg)
            if data['type'] == 'input_audio_buffer.cleared':
                break
        
        # Skicka audio data
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        audio_msg = {
            "type": "input_audio_buffer.append",
            "audio": audio_b64
        }
        
        await session.openai_ws.send(json.dumps(audio_msg))
        logger.info(f"📤 Skickade {len(audio_data)} bytes audio till OpenAI")
        
        # Commit buffer
        commit_msg = {"type": "input_audio_buffer.commit"}
        await session.openai_ws.send(json.dumps(commit_msg))
        
        # Vänta på commit confirmation
        while True:
            msg = await session.openai_ws.recv()
            data = json.loads(msg)
            if data['type'] == 'input_audio_buffer.committed':
                logger.info("✅ Audio buffer committed")
                break
        
        # Begär response
        response_create = {
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
                "instructions": "Svara på svenska på det du hörde."
            }
        }
        await session.openai_ws.send(json.dumps(response_create))
        logger.info("📤 Begärde response från OpenAI")
        
        # Samla audio response
        audio_chunks = []
        text_response = ""
        
        while True:
            msg = await asyncio.wait_for(session.openai_ws.recv(), timeout=15.0)
            data = json.loads(msg)
            msg_type = data['type']
            
            if msg_type == 'response.audio.delta':
                audio_chunk = base64.b64decode(data.get('delta', ''))
                audio_chunks.append(audio_chunk)
                
            elif msg_type == 'response.audio_transcript.delta':
                text_response += data.get('delta', '')
                
            elif msg_type == 'response.audio.done':
                logger.info("✅ Audio response klar!")
                full_audio = b''.join(audio_chunks)
                logger.info(f"🔊 Fick {len(full_audio)} bytes audio response")
                logger.info(f"💬 Text response: {text_response}")
                return full_audio, text_response
                
            elif msg_type == 'response.done':
                logger.info("✅ Response klar!")
                break
                
            elif msg_type == 'error':
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                logger.error(f"❌ OpenAI error: {error_msg}")
                return None, None
        
        if audio_chunks:
            full_audio = b''.join(audio_chunks)
            return full_audio, text_response
            
    except Exception as e:
        logger.error(f"❌ Error sending audio to OpenAI: {e}")
        return None, None

@app.post("/api/webrtc/offer")
async def handle_webrtc_offer(request: Request):
    """Hantera WebRTC offer"""
    try:
        data = await request.json()
        offer_sdp = data["offer"]
        session_id = data.get("sessionId", "test-session")
        
        logger.info(f"🔄 Mottog WebRTC offer för session {session_id}")
        
        # Skapa voice session
        session = VoiceSession(session_id)
        openai_connections[session_id] = session
        
        # Anslut till OpenAI
        await connect_to_openai(session)
        
        # Skapa peer connection
        pc = RTCPeerConnection()
        peer_connections[session_id] = pc
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"🔗 WebRTC tillstånd: {pc.connectionState}")
            if pc.connectionState in ["failed", "closed"]:
                peer_connections.pop(session_id, None)
                openai_connections.pop(session_id, None)
        
        @pc.on("track")
        async def on_track(track):
            logger.info(f"🎵 AUDIO TRACK MOTTAGEN! Kind: {track.kind}")
            
            if track.kind == "audio":
                logger.info("🎤 Börjar lyssna på mikrofon...")
                
                try:
                    audio_buffer = []
                    frame_count = 0
                    sample_rate = None
                    
                    while True:
                        frame = await track.recv()
                        frame_count += 1
                        
                        if frame_count == 1:
                            sample_rate = frame.sample_rate
                            logger.info(f"🎤 FÖRSTA FRAME! Sample rate: {sample_rate}, Format: {frame.format}")
                        
                        # Konvertera WebRTC frame till PCM16 för OpenAI
                        try:
                            # Få raw audio data från frame
                            audio_array = frame.to_ndarray()
                            
                            # Debug log första frame
                            if frame_count == 1:
                                logger.info(f"🔍 Audio array shape: {audio_array.shape}, dtype: {audio_array.dtype}, min/max: {audio_array.min():.3f}/{audio_array.max():.3f}")
                            
                            # Hantera multichannel -> mono
                            if len(audio_array.shape) > 1 and audio_array.shape[1] > 1:
                                audio_array = audio_array.mean(axis=1)  # Stereo -> Mono
                            elif len(audio_array.shape) > 1:
                                audio_array = audio_array.flatten()
                            
                            # Normalisera till [-1, 1] intervall om nödvändigt
                            if audio_array.dtype == np.int16:
                                audio_array = audio_array.astype(np.float32) / 32767.0
                            elif audio_array.dtype == np.int32:
                                audio_array = audio_array.astype(np.float32) / 2147483647.0
                            
                            # Resample till 24kHz för OpenAI
                            if sample_rate != 24000:
                                target_length = int(len(audio_array) * 24000 / sample_rate)
                                if target_length > 0:
                                    audio_array = np.interp(
                                        np.linspace(0, len(audio_array), target_length),
                                        np.arange(len(audio_array)),
                                        audio_array
                                    )
                            
                            # Konvertera till 16-bit PCM bytes
                            audio_pcm = (audio_array * 32767).astype(np.int16).tobytes()
                            
                            if len(audio_pcm) > 0:
                                audio_buffer.append(audio_pcm)
                                if frame_count == 1:
                                    logger.info(f"✅ Första PCM chunk: {len(audio_pcm)} bytes")
                            else:
                                logger.warning(f"⚠️ Tom PCM chunk för frame {frame_count}")
                        
                        except Exception as e:
                            logger.error(f"❌ Frame conversion error på frame {frame_count}: {e}")
                            continue
                        
                        # Skicka efter 2 sekunder audio (ca 100 frames)
                        if frame_count > 0 and frame_count % 100 == 0:
                            logger.info(f"📤 Skickar {frame_count} frames till OpenAI...")
                            
                            if not session.is_processing:
                                session.is_processing = True
                                
                                # Samla all audio data
                                full_audio = b''.join(audio_buffer)
                                audio_buffer = []  # Rensa buffer
                                
                                # Skicka till OpenAI i bakgrunden
                                asyncio.create_task(process_audio_async(session, full_audio))
                        
                except Exception as e:
                    logger.error(f"❌ Audio processing error: {e}")
        
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

async def process_audio_async(session: VoiceSession, audio_data: bytes):
    """Process audio med OpenAI i bakgrunden"""
    try:
        logger.info("🤖 Bearbetar audio med Alice...")
        audio_response, text_response = await send_audio_to_openai(session, audio_data)
        
        if audio_response:
            logger.info("🎉 ALICE SVARADE!")
            logger.info(f"💬 Text: {text_response}")
            logger.info(f"🔊 Audio: {len(audio_response)} bytes")
            
            # TODO: Spela upp audio_response via WebRTC
            
        session.is_processing = False
        
    except Exception as e:
        logger.error(f"❌ Processing error: {e}")
        session.is_processing = False

@app.get("/test")
async def serve_test_page():
    """Komplett Alice rösttest sida"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>🎙️ Alice Complete Voice Test</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background: #1a1a1a; color: white; }
        .container { max-width: 600px; margin: 0 auto; }
        button { padding: 15px 30px; font-size: 18px; margin: 10px; border: none; border-radius: 5px; cursor: pointer; }
        .start { background: #4CAF50; color: white; }
        .stop { background: #f44336; color: white; }
        .status { margin: 20px 0; padding: 15px; background: #333; border-radius: 5px; }
        .log { background: #222; padding: 10px; border-radius: 5px; height: 300px; overflow-y: scroll; font-family: monospace; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ Alice Complete Voice Test</h1>
        <p>Klicka "Starta Alice" och prata sedan. Alice kommer att svara dig med röst!</p>
        
        <button id="startBtn" class="start">Starta Alice</button>
        <button id="stopBtn" class="stop" disabled>Stoppa</button>
        
        <div class="status">
            Status: <span id="status">Redo att starta</span>
        </div>
        
        <div id="log" class="log"></div>
    </div>
    
    <script>
        let pc = null;
        let localStream = null;
        let isRecording = false;
        
        const log = (msg) => {
            const timestamp = new Date().toLocaleTimeString();
            const logEl = document.getElementById('log');
            logEl.innerHTML += `[${timestamp}] ${msg}<br>`;
            logEl.scrollTop = logEl.scrollHeight;
            console.log(msg);
        };
        
        const updateStatus = (status) => {
            document.getElementById('status').textContent = status;
        };
        
        document.getElementById('startBtn').onclick = async () => {
            try {
                log('🎤 Startar Alice...');
                updateStatus('Startar...');
                
                // Get microphone
                localStream = await navigator.mediaDevices.getUserMedia({ 
                    audio: { 
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true,
                        sampleRate: 48000
                    } 
                });
                log('✅ Mikrofon åtkomst OK');
                
                // Create peer connection
                pc = new RTCPeerConnection({
                    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
                });
                
                // Add tracks
                localStream.getTracks().forEach(track => {
                    pc.addTrack(track, localStream);
                    log(`📤 Lade till ${track.kind} track`);
                });
                
                // Create offer
                const offer = await pc.createOffer();
                await pc.setLocalDescription(offer);
                log('📤 Skapade WebRTC offer');
                
                // Send to server
                const response = await fetch('/api/webrtc/offer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        offer: offer.sdp,
                        sessionId: 'alice-session-' + Date.now()
                    })
                });
                
                const data = await response.json();
                log('📥 Mottog answer från server');
                
                // Set answer
                await pc.setRemoteDescription({
                    type: 'answer',
                    sdp: data.answer
                });
                
                log('🎉 Alice är redo! Säg något...');
                updateStatus('Alice lyssnar - säg något!');
                
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
                isRecording = true;
                
            } catch (e) {
                log(`❌ Error: ${e.message}`);
                updateStatus('Error');
            }
        };
        
        document.getElementById('stopBtn').onclick = () => {
            if (localStream) {
                localStream.getTracks().forEach(track => track.stop());
                localStream = null;
            }
            if (pc) {
                pc.close();
                pc = null;
            }
            
            log('⏹️ Alice stoppad');
            updateStatus('Stoppad');
            
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            isRecording = false;
        };
        
        // Auto-scroll log
        setInterval(() => {
            if (isRecording) {
                log(`🎤 Lyssnar... (Alice är aktiv)`);
            }
        }, 5000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)

if __name__ == "__main__":
    logger.info("🚀 Startar Alice Complete Voice Test på http://localhost:8003")
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")