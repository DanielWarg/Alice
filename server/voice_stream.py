"""
Alice Streaming Voice API - Real-time Conversational Interface
Hybrid approach: API för snabb konversation, Lokal för tool execution
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime

import httpx
from fastapi import WebSocket, WebSocketDisconnect
import logging

from core.router import classify
from core.tool_registry import validate_and_execute_tool, enabled_tools
from memory import MemoryStore

logger = logging.getLogger("alice.voice")

class VoiceStreamManager:
    """Manages real-time voice conversations with Alice"""
    
    def __init__(self, memory_store: MemoryStore):
        self.memory = memory_store
        self.active_sessions = {}
        self.api_client = httpx.AsyncClient(timeout=5.0)
        
    async def handle_voice_session(self, websocket: WebSocket, session_id: str):
        """Handle a complete voice conversation session"""
        await websocket.accept()
        
        try:
            self.active_sessions[session_id] = {
                "websocket": websocket,
                "start_time": datetime.now(),
                "conversation_context": []
            }
            
            logger.info(f"Voice session started: {session_id}")
            
            while True:
                try:
                    # Receive voice input from browser
                    data = await websocket.receive_json()
                    
                    if data.get("type") == "voice_input":
                        await self._process_voice_input(websocket, session_id, data["text"])
                    elif data.get("type") == "ping":
                        await websocket.send_json({"type": "pong", "timestamp": time.time()})
                        
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Error in voice session {session_id}: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Ett fel uppstod i röstbehandlingen"
                    })
                    
        finally:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            await self.api_client.aclose()
            logger.info(f"Voice session ended: {session_id}")
    
    async def _process_voice_input(self, websocket: WebSocket, session_id: str, text: str, source: str = "browser_api"):
        """Process voice input with enhanced multi-tier response system"""
        
        # 1. INSTANT acknowledgment (send immediately)
        await websocket.send_json({
            "type": "heard",
            "text": text,
            "source": source,  # browser_api eller whisper
            "timestamp": time.time()
        })
        
        # Store user input in conversation context with source info
        session_context = self.active_sessions[session_id]["conversation_context"]
        session_context.append({
            "role": "user", 
            "content": text, 
            "timestamp": time.time(),
            "source": source,
            "processing_method": "fast" if source == "browser_api" else "quality"
        })
        
        # 2. ENHANCED processing baserat på source och quality
        if source == "browser_api":
            # Snabb browser API - prioritera hastighet
            await self._handle_browser_api_input(websocket, session_id, text, session_context)
        elif source == "whisper":
            # Whisper transcription - prioritera kvalitet och lång text
            await self._handle_whisper_input(websocket, session_id, text, session_context)
        else:
            # Fallback till standard processing
            await self._handle_standard_input(websocket, session_id, text, session_context)
    
    async def _handle_browser_api_input(self, websocket: WebSocket, session_id: str, text: str, context: list):
        """Handle browser API input - optimerad för snabba kommandon"""
        
        # Snabb intent classification för kommandon
        intent_result = await self._classify_intent_fast(text)
        
        if intent_result and intent_result.get("is_tool_command"):
            # Tool command - execute locally with privacy
            await self._handle_tool_command(websocket, session_id, intent_result, text)
        else:
            # Kort konversation - browser API är bra för snabba svar
            await self._handle_conversation(websocket, session_id, text, context, response_style="quick")
    
    async def _handle_whisper_input(self, websocket: WebSocket, session_id: str, text: str, context: list):
        """Handle Whisper transcription - optimerad för kvalitet och långa texter"""
        
        # Whisper ger högkvalitativ text, använd för komplexa analyser
        
        # 1. Först kolla om det är en tool command
        intent_result = await self._classify_intent_detailed(text)  # Mer detaljerad analys
        
        if intent_result and intent_result.get("is_tool_command"):
            await self._handle_tool_command(websocket, session_id, intent_result, text)
        else:
            # Längre konversation - Whisper är perfekt för djupare dialog
            await self._handle_conversation(websocket, session_id, text, context, response_style="detailed")
    
    async def _handle_standard_input(self, websocket: WebSocket, session_id: str, text: str, context: list):
        """Fallback standard input handling"""
        intent_result = await self._classify_intent_fast(text)
        
        if intent_result and intent_result.get("is_tool_command"):
            await self._handle_tool_command(websocket, session_id, intent_result, text)
        else:
            await self._handle_conversation(websocket, session_id, text, context)
    
    async def _classify_intent_fast(self, text: str) -> Optional[Dict[str, Any]]:
        """Snabb lokal intent classification"""
        try:
            router_result = classify(text)
            
            if router_result and router_result.get("confidence", 0) >= 0.7:
                return {
                    "is_tool_command": True,
                    "tool": router_result["tool"],
                    "args": router_result["args"],
                    "confidence": router_result["confidence"],
                    "method": "fast"
                }
            
            return {"is_tool_command": False}
            
        except Exception as e:
            logger.error(f"Intent classification error: {e}")
            return {"is_tool_command": False}
    
    async def _classify_intent_detailed(self, text: str) -> Optional[Dict[str, Any]]:
        """Detaljerad intent classification för Whisper text"""
        try:
            # Använd samma system men med lägre threshold för Whisper
            router_result = classify(text)
            
            if router_result and router_result.get("confidence", 0) >= 0.5:  # Lägre threshold
                return {
                    "is_tool_command": True,
                    "tool": router_result["tool"],
                    "args": router_result["args"],
                    "confidence": router_result["confidence"],
                    "method": "detailed"
                }
            
            return {"is_tool_command": False}
            
        except Exception as e:
            logger.error(f"Detailed intent classification error: {e}")
            return {"is_tool_command": False}
    
    async def _handle_tool_command(self, websocket: WebSocket, session_id: str, intent: Dict, original_text: str):
        """Handle tool commands with local execution for privacy"""
        
        tool_name = intent["tool"]
        tool_args = intent["args"]
        
        # Immediate acknowledgment
        confirmations = {
            "PLAY": "Okej, jag startar musiken",
            "PAUSE": "Jag pausar musiken",
            "SET_VOLUME": "Jag ändrar volymen",
            "SEND_EMAIL": "Jag skickar e-posten åt dig",
            "READ_EMAILS": "Jag hämtar dina e-postmeddelanden",
            "DEFAULT": "Okej, jag gör det"
        }
        
        confirmation = confirmations.get(tool_name, confirmations["DEFAULT"])
        
        await websocket.send_json({
            "type": "acknowledge",
            "message": confirmation,
            "executing": tool_name
        })
        
        # Execute tool locally (async, non-blocking)
        asyncio.create_task(self._execute_tool_async(websocket, session_id, tool_name, tool_args))
    
    async def _execute_tool_async(self, websocket: WebSocket, session_id: str, tool_name: str, tool_args: Dict):
        """Execute tool in background and report results"""
        try:
            # Validate tool is enabled
            if tool_name not in enabled_tools():
                await websocket.send_json({
                    "type": "tool_error",
                    "message": f"Verktyget {tool_name} är inte aktiverat"
                })
                return
            
            # Execute the tool
            result = await validate_and_execute_tool(tool_name, tool_args)
            
            if result.get("success"):
                await websocket.send_json({
                    "type": "tool_success",
                    "tool": tool_name,
                    "message": result.get("message", "Klart!"),
                    "result": result.get("data")
                })
                
                # Store successful action in memory
                await self.memory.upsert_text_memory_single(
                    f"Tool executed: {tool_name} with args {tool_args}. Result: {result.get('message', 'Success')}",
                    metadata={"type": "tool_execution", "tool": tool_name, "timestamp": time.time()}
                )
            else:
                await websocket.send_json({
                    "type": "tool_error",
                    "message": result.get("error", "Ett fel uppstod vid verktygsexekvering")
                })
                
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            await websocket.send_json({
                "type": "tool_error", 
                "message": "Ett oväntat fel uppstod"
            })
    
    async def _handle_conversation(self, websocket: WebSocket, session_id: str, text: str, context: list, response_style: str = "balanced"):
        """Handle natural conversation with adaptive response style"""
        
        try:
            # Use OpenAI API for fast conversational responses
            # This could be swapped for Claude or other fast APIs
            
            # Build conversation context
            messages = [
                {"role": "system", "content": self._get_alice_system_prompt()}
            ]
            
            # Add recent conversation context (last 5 exchanges)
            recent_context = context[-10:] if len(context) > 10 else context
            for msg in recent_context:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            # Add current message
            messages.append({"role": "user", "content": text})
            
            # Get relevant memory context
            memory_context = await self.memory.retrieve_text_bm25_recency(text, limit=3)
            if memory_context:
                context_text = "\\n".join([item["content"] for item in memory_context])
                messages.insert(1, {
                    "role": "system", 
                    "content": f"Relevant context from previous conversations:\\n{context_text}"
                })
            
            # Stream response from API med style-anpassning
            await self._stream_api_response(websocket, messages, response_style)
            
        except Exception as e:
            logger.error(f"Conversation error: {e}")
            await websocket.send_json({
                "type": "speak",
                "text": "Ursäkta, jag hade problem med att besvara det just nu. Kan du försöka igen?",
                "final": True
            })
    
    def _get_alice_system_prompt(self) -> str:
        """Get Alice's conversational personality prompt"""
        return """Du är Alice, en supersmart AI-assistent som talar svenska naturligt. 
        Du är hjälpsam, vänlig och konverserar naturligt. Du svarar koncist men informativt.
        Du hjälper användare med frågor, diskussioner och allmän konversation.
        Svara alltid på svenska och håll ett naturligt, vänligt tonläge."""
    
    async def _stream_api_response(self, websocket: WebSocket, messages: list):
        """Stream response from API with real-time chunks"""
        
        # Note: This is a placeholder for API streaming
        # In production, replace with actual OpenAI/Claude API streaming
        
        try:
            # Simulate API streaming response
            response_text = "Jag förstår din fråga. Det är en intressant sak att diskutera."
            
            # Send response in chunks for streaming effect
            words = response_text.split()
            current_chunk = ""
            
            for i, word in enumerate(words):
                current_chunk += word + " "
                
                # Send chunk every 2-3 words for natural flow
                if i % 2 == 1 or i == len(words) - 1:
                    await websocket.send_json({
                        "type": "speak",
                        "text": current_chunk.strip(),
                        "partial": i < len(words) - 1,
                        "final": i == len(words) - 1
                    })
                    current_chunk = ""
                    await asyncio.sleep(0.1)  # Small delay for natural speech rhythm
            
            # Store conversation in memory
            await self.memory.upsert_text_memory_single(
                f"User: {messages[-1]['content']}\\nAlice: {response_text}",
                metadata={"type": "conversation", "timestamp": time.time()}
            )
            
        except Exception as e:
            logger.error(f"API streaming error: {e}")
            await websocket.send_json({
                "type": "speak",
                "text": "Jag hade problem med att svara just nu.",
                "final": True
            })

# Global voice manager instance
voice_manager = None

def get_voice_manager(memory_store: MemoryStore) -> VoiceStreamManager:
    """Get or create voice manager instance"""
    global voice_manager
    if voice_manager is None:
        voice_manager = VoiceStreamManager(memory_store)
    return voice_manager


async def process_whisper_transcription(websocket: WebSocket, session_id: str, transcription_data: dict, memory_store: MemoryStore):
    """Process Whisper transcription with enhanced quality handling"""
    voice_manager = get_voice_manager(memory_store)
    
    # Extract high-quality text from Whisper result
    text = transcription_data.get('text', '').strip()
    confidence = transcription_data.get('language_probability', 1.0)
    duration = transcription_data.get('duration', 0)
    
    if not text:
        await websocket.send_json({
            "type": "error",
            "message": "Tom transkription mottagen"
        })
        return
    
    # Enhanced processing för Whisper med kvalitetsinfo
    await websocket.send_json({
        "type": "whisper_received",
        "text": text,
        "confidence": confidence,
        "duration": duration,
        "quality": transcription_data.get('audio_quality', {}),
        "timestamp": time.time()
    })
    
    # Process med Whisper-specifik hantering
    await voice_manager._process_voice_input(websocket, session_id, text, source="whisper")
    
    logger.info(f"Whisper transcription processed: {len(text)} chars, confidence: {confidence:.2f}")