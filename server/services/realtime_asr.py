from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import json
import asyncio
import logging
from typing import Dict, Any
import base64
import numpy as np

router = APIRouter()
logger = logging.getLogger(__name__)

class MockRealtimeASR:
    """Mock implementation av OpenAI Realtime API för utveckling"""
    
    def __init__(self):
        self.session_config = None
        self.audio_buffer = bytearray()
        self.is_speaking = False
        self.speech_start_time = None
        
    async def handle_event(self, websocket: WebSocket, event: Dict[str, Any]) -> None:
        event_type = event.get('type')
        
        if event_type == 'session.update':
            self.session_config = event.get('session', {})
            await self.send_event(websocket, {
                'type': 'session.updated',
                'session': self.session_config
            })
            
        elif event_type == 'input_audio_buffer.append':
            audio_data = event.get('audio', '')
            if audio_data:
                # Decode base64 audio
                try:
                    audio_bytes = base64.b64decode(audio_data)
                    self.audio_buffer.extend(audio_bytes)
                    
                    # Mock speech detection baserat på audio nivå
                    await self.process_audio_chunk(websocket, audio_bytes)
                    
                except Exception as e:
                    logger.error(f"Failed to process audio: {e}")
                    
        elif event_type == 'input_audio_buffer.commit':
            # Finalize current audio buffer
            if self.audio_buffer:
                await self.finalize_transcription(websocket)
                
        elif event_type == 'response.create':
            # Trigger response generation
            await self.create_response(websocket)
            
    async def process_audio_chunk(self, websocket: WebSocket, audio_bytes: bytes):
        """Simulera speech detection och partial transcription"""
        # Enkel volym-baserad speech detection
        if len(audio_bytes) >= 2:
            # Convert PCM16 to amplitude
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            
            # Threshold för speech detection (justeras efter miljö)
            speech_threshold = 500  
            
            if rms > speech_threshold and not self.is_speaking:
                self.is_speaking = True
                self.speech_start_time = asyncio.get_event_loop().time()
                await self.send_event(websocket, {
                    'type': 'input_audio_buffer.speech_started'
                })
                
            elif rms <= speech_threshold and self.is_speaking:
                # Vänta lite innan vi säger att talet slutat
                await asyncio.sleep(0.5)
                if self.is_speaking:  # Kontrollera igen efter delay
                    self.is_speaking = False
                    await self.send_event(websocket, {
                        'type': 'input_audio_buffer.speech_stopped'
                    })
                    
        # Mock partial transcription efter lite data
        if len(self.audio_buffer) > 16000 * 2:  # ~2 sekunder audio
            await self.generate_partial_transcription(websocket)
            
    async def generate_partial_transcription(self, websocket: WebSocket):
        """Mock partial transcription - skulle använda riktig ASR"""
        mock_partials = [
            "hej",
            "hej alice", 
            "hej alice kan du",
            "hej alice kan du hjälpa mig",
            "hej alice kan du hjälpa mig med"
        ]
        
        # Välj baserat på bufferstorlek
        buffer_seconds = len(self.audio_buffer) // (16000 * 2)
        partial_index = min(buffer_seconds - 2, len(mock_partials) - 1)
        
        if partial_index >= 0:
            await self.send_event(websocket, {
                'type': 'conversation.item.input_audio_transcription.completed',
                'transcript': mock_partials[partial_index]
            })
            
    async def finalize_transcription(self, websocket: WebSocket):
        """Skapa final transcription från audio buffer"""
        # I riktigt system: skicka till Whisper eller annan ASR
        mock_finals = [
            "hej alice kan du hjälpa mig med något",
            "vad är klockan just nu", 
            "påminn mig om mötet imorgon",
            "jag behöver handla mjölk och bröd",
            "spela min favoritmusik tack"
        ]
        
        # Välj baserat på bufferstorlek eller slumpmässigt
        import random
        final_text = random.choice(mock_finals)
        
        await self.send_event(websocket, {
            'type': 'response.audio_transcript.done',
            'transcript': final_text
        })
        
        # Rensa buffer
        self.audio_buffer.clear()
        
    async def create_response(self, websocket: WebSocket):
        """Mock response creation"""
        await self.send_event(websocket, {
            'type': 'response.created',
            'response': {
                'id': 'resp_mock_123',
                'status': 'completed'
            }
        })
        
    async def send_event(self, websocket: WebSocket, event: Dict[str, Any]):
        """Skicka event till klient"""
        try:
            await websocket.send_text(json.dumps(event))
        except Exception as e:
            logger.error(f"Failed to send event: {e}")

@router.websocket("/ws/realtime-asr")
async def realtime_asr_websocket(websocket: WebSocket):
    """Mock WebSocket endpoint för OpenAI Realtime API"""
    await websocket.accept()
    asr = MockRealtimeASR()
    
    logger.info("Realtime ASR client connected (mock)")
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                event = json.loads(data)
                await asr.handle_event(websocket, event)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data[:100]}")
                await websocket.send_text(json.dumps({
                    'type': 'error',
                    'error': {'message': 'Invalid JSON format'}
                }))
                
    except WebSocketDisconnect:
        logger.info("Realtime ASR client disconnected")
    except Exception as e:
        logger.error(f"Realtime ASR error: {e}")
        await websocket.close()

# Export
__all__ = ['router']