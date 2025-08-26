#!/usr/bin/env python3
"""
🎙️ LiveKit-Style Real-time Voice Engine
Implementerar verklig real-time streaming voice pipeline med:
- Stabil partial detection (250ms)
- Streaming TTS micro-chunks  
- Persistent WebSocket-session
- Sub-700ms Time-To-First-Audio
"""

import asyncio
import json
import time
import base64
import io
import wave
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator
from collections import deque

import requests
import httpx
from pydantic import BaseModel

# TTS imports
try:
    import piper
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False

class VoiceMessage(BaseModel):
    type: str
    transcript: Optional[str] = None
    is_final: Optional[bool] = None
    confidence: Optional[float] = None
    audio_data: Optional[str] = None  # base64
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    text_fragment: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class StablePartialDetector:
    """
    Detekterar stabila partials enligt LiveKit-modellen:
    - Håller transcript stabil i 250ms → triggar processing
    - Hög confidence + tillräcklig längd
    """
    
    def __init__(self, stability_threshold_ms: int = 250, min_confidence: float = 0.85, min_length: int = 8):
        self.stability_threshold_ms = stability_threshold_ms
        self.min_confidence = min_confidence  
        self.min_length = min_length
        
        self.last_transcript = ""
        self.last_change_time = 0
        self.is_processing = False
        
    def should_trigger(self, transcript: str, confidence: float, is_final: bool = False) -> bool:
        """
        Returnerar True om vi ska trigga processing baserat på stabil partial
        """
        current_time = time.time() * 1000  # ms
        
        # Alltid trigga på final
        if is_final:
            return True
            
        # Skippa om redan processing
        if self.is_processing:
            return False
            
        # Skippa om för kort eller låg confidence
        if len(transcript) < self.min_length or confidence < self.min_confidence:
            return False
            
        # Kolla stabilitet
        if transcript != self.last_transcript:
            self.last_transcript = transcript
            self.last_change_time = current_time
            return False
            
        # Stabil tillräckligt länge?
        time_stable = current_time - self.last_change_time
        if time_stable >= self.stability_threshold_ms:
            return True
            
        return False
    
    def set_processing(self, processing: bool):
        """Markerar om vi för närvarande processar"""
        self.is_processing = processing
        
    def reset(self):
        """Återställer detector-state"""
        self.last_transcript = ""
        self.last_change_time = 0
        self.is_processing = False

class StreamingTTSEngine:
    """
    Streaming TTS som genererar micro-chunks (3-5 ord) i realtid
    Använder amerikansk engelska röst för Alice
    """
    
    def __init__(self, voice_model: str = "en_US-amy-medium"):
        self.voice_model = voice_model  # Amerikansk kvinnlig röst
        self.piper_model = None
        self._initialize_piper()
        
    def _initialize_piper(self):
        """Initialiserar Piper TTS om tillgängligt"""
        if not PIPER_AVAILABLE:
            print("⚠️  Piper ej tillgängligt - använder HTTP TTS fallback")
            return
            
        try:
            # TODO: Ladda Piper-modell för amerikansk engelska
            # self.piper_model = piper.PiperVoice.load(f"models/tts/{self.voice_model}.onnx")
            print(f"✅ Piper TTS-motor initialiserad med {self.voice_model}")
        except Exception as e:
            print(f"⚠️  Kunde ej ladda Piper-modell: {e}")
            
    def split_into_chunks(self, text: str, chunk_size: int = 4) -> list[str]:
        """Delar text i smådelar för progressiv TTS"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
            
        return chunks
        
    async def generate_streaming_audio(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Genererar audio-chunks progressivt
        Första chunken inom ~200ms för snabb TTFA
        """
        chunks = self.split_into_chunks(text)
        
        for i, chunk in enumerate(chunks):
            start_time = time.time()
            
            try:
                if self.piper_model:
                    # Piper streaming (om tillgängligt)
                    audio_bytes = await self._generate_piper_audio(chunk)
                else:
                    # HTTP TTS fallback
                    audio_bytes = await self._generate_http_tts_audio(chunk)
                
                generation_time = (time.time() - start_time) * 1000
                print(f"🎵 TTS chunk {i+1}/{len(chunks)}: '{chunk[:30]}...' ({generation_time:.0f}ms)")
                
                yield audio_bytes
                
                # Kort paus mellan chunks för naturlig rytm
                if i < len(chunks) - 1:
                    await asyncio.sleep(0.02)  # 20ms
                    
            except Exception as e:
                print(f"❌ TTS-fel för chunk '{chunk}': {e}")
                continue
                
    async def _generate_piper_audio(self, text: str) -> bytes:
        """Genererar audio med Piper (om tillgängligt)"""
        # TODO: Implementera Piper TTS streaming
        # audio = self.piper_model.synthesize(text)
        # return audio.tobytes()
        return b""  # Placeholder
        
    async def _generate_http_tts_audio(self, text: str) -> bytes:
        """Fallback till HTTP TTS API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/api/tts/synthesize",
                    json={"text": text, "voice": self.voice_model},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    # TTS API returnerar JSON med base64 audio_data
                    data = response.json()
                    if data.get("success") and "audio_data" in data:
                        # Avkoda base64 för att få rå audio bytes
                        return base64.b64decode(data["audio_data"])
                    else:
                        print(f"⚠️  TTS API fel: {data}")
                        return b""
                else:
                    print(f"⚠️  TTS API fel: {response.status_code}")
                    return b""
                    
        except Exception as e:
            print(f"❌ HTTP TTS fel: {e}")
            return b""

class RealtimeVoiceEngine:
    """
    Huvudmotor för real-time voice processing
    Hanterar persistent session, stabil partial detection och streaming TTS
    """
    
    def __init__(self):
        self.partial_detector = StablePartialDetector()
        self.tts_engine = StreamingTTSEngine()
        self.session_start_time = time.time()
        self.metrics = {
            'total_requests': 0,
            'avg_ttfa_ms': 0,
            'partial_triggers': 0,
            'final_triggers': 0
        }
        
        # Pre-warm Ollama connection
        asyncio.create_task(self._prewarm_llm())
        
    async def _prewarm_llm(self):
        """Pre-warmar LLM-anslutning för snabbare svar"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "gpt-oss:20b", 
                        "prompt": "test",
                        "options": {"num_predict": 1}
                    },
                    timeout=10.0
                )
            print("🔥 LLM pre-warmed")
        except Exception as e:
            print(f"⚠️  LLM pre-warm fel: {e}")
            
    async def process_voice_input(self, transcript: str, confidence: float, is_final: bool = False) -> AsyncGenerator[VoiceMessage, None]:
        """
        Huvudfunktion för voice processing
        Returnerar streaming response med audio chunks
        """
        # Kolla om vi ska trigga processing
        should_process = self.partial_detector.should_trigger(transcript, confidence, is_final)
        
        if not should_process:
            return
            
        print(f"🎯 Triggar processing: '{transcript}' (confidence: {confidence:.2f}, final: {is_final})")
        
        # Markera som processing
        self.partial_detector.set_processing(True)
        start_time = time.time()
        
        try:
            # Skicka processing_started event
            yield VoiceMessage(
                type="processing_started",
                transcript=transcript,
                metadata={
                    'trigger_type': 'final' if is_final else 'stable_partial',
                    'confidence': confidence
                }
            )
            
            # Få LLM-respons (använd fast path för enkla frågor)
            response_text = await self._get_llm_response(transcript)
            
            if not response_text:
                yield VoiceMessage(type="error", metadata={'error': 'Inget svar från LLM'})
                return
                
            print(f"🧠 LLM svar: '{response_text[:50]}...'")
            
            # Streama TTS-audio
            chunk_count = 0
            async for audio_chunk in self.tts_engine.generate_streaming_audio(response_text):
                if audio_chunk:
                    chunk_count += 1
                    
                    # Första chunk = TTFA-metrik
                    if chunk_count == 1:
                        ttfa_ms = (time.time() - start_time) * 1000
                        self.metrics['avg_ttfa_ms'] = ttfa_ms
                        print(f"⚡ TTFA: {ttfa_ms:.0f}ms")
                    
                    # Skicka audio chunk
                    yield VoiceMessage(
                        type="audio_chunk",
                        audio_data=base64.b64encode(audio_chunk).decode(),
                        chunk_index=chunk_count,
                        metadata={'ttfa_ms': ttfa_ms if chunk_count == 1 else None}
                    )
                    
            # Slutligt meddelande
            yield VoiceMessage(
                type="response_complete",
                transcript=response_text,
                metadata={
                    'total_chunks': chunk_count,
                    'total_time_ms': (time.time() - start_time) * 1000
                }
            )
            
            # Uppdatera metrics
            self.metrics['total_requests'] += 1
            if is_final:
                self.metrics['final_triggers'] += 1
            else:
                self.metrics['partial_triggers'] += 1
                
        except Exception as e:
            print(f"❌ Voice processing fel: {e}")
            yield VoiceMessage(type="error", metadata={'error': str(e)})
            
        finally:
            # Frigör processing-lock
            self.partial_detector.set_processing(False)
            
    async def _get_llm_response(self, prompt: str) -> str:
        """
        Få LLM-respons med smart routing (fast path för enkla frågor)
        """
        # Simple commands som kan få snabba svar
        fast_path_keywords = ['väder', 'tid', 'datum', 'hej', 'tack', 'vad', 'när']
        is_fast_path = any(keyword in prompt.lower() for keyword in fast_path_keywords)
        
        try:
            if is_fast_path and len(prompt) < 50:
                # Fast path: OpenAI för snabba svar
                return await self._get_openai_response(prompt)
            else:
                # Think path: Ollama för komplexa svar
                return await self._get_ollama_response(prompt)
                
        except Exception as e:
            print(f"⚠️  LLM-fel: {e}")
            return "Ursäkta, jag hade problem att processa din fråga."
            
    async def _get_ollama_response(self, prompt: str) -> str:
        """Ollama-respons för komplexa queries"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "gpt-oss:20b",
                        "prompt": f"You are Alice, a Swedish AI assistant. Always respond in English, even when the user speaks Swedish. User said: {prompt}. Respond briefly in English:",
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 100,  # Begränsa svar-längd för snabbhet
                            "top_p": 0.9
                        }
                    },
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', '').strip()
                    
        except Exception as e:
            print(f"❌ Ollama-fel: {e}")
            raise
            
    async def _get_openai_response(self, prompt: str) -> str:
        """OpenAI-respons för snabba queries"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._get_openai_key()}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": "You are Alice, a Swedish AI assistant. Always respond in English, even if the user speaks Swedish. Keep responses short and natural."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 80,
                        "temperature": 0.2
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content'].strip()
                    
        except Exception as e:
            print(f"❌ OpenAI-fel: {e}")
            raise
            
    def _get_openai_key(self) -> str:
        """Hämta OpenAI API key från miljövariabel"""
        import os
        return os.getenv('OPENAI_API_KEY', '')
        
    def get_metrics(self) -> dict:
        """Returnera aktuella performance-metrics"""
        uptime = time.time() - self.session_start_time
        return {
            **self.metrics,
            'uptime_seconds': uptime,
            'session_start': datetime.fromtimestamp(self.session_start_time).isoformat()
        }
        
    def reset_session(self):
        """Återställ session för ny användare/konversation"""
        self.partial_detector.reset()
        self.session_start_time = time.time()
        print("🔄 Voice session reset")

# Singleton instance för global användning
voice_engine = RealtimeVoiceEngine()

async def handle_voice_message(message: dict) -> AsyncGenerator[dict, None]:
    """
    Wrapper-funktion för att hantera voice messages från WebSocket
    """
    try:
        # Parse inkommande meddelande
        msg_type = message.get('type', '')
        
        if msg_type == 'partial_transcript':
            transcript = message.get('transcript', '')
            confidence = message.get('confidence', 0.0)
            is_final = message.get('is_final', False)
            
            # Processa med voice engine
            async for response in voice_engine.process_voice_input(transcript, confidence, is_final):
                yield response.dict()
                
        elif msg_type == 'get_metrics':
            yield {
                'type': 'metrics',
                'data': voice_engine.get_metrics()
            }
            
        elif msg_type == 'reset_session':
            voice_engine.reset_session()
            yield {
                'type': 'session_reset',
                'status': 'ok'
            }
            
    except Exception as e:
        yield {
            'type': 'error', 
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }