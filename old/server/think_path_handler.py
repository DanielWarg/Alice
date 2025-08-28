"""
Think Path Handler - Phase 2 Implementation  
Handles complex queries locally with gpt-oss:20B via Ollama for privacy-first processing

Features:
- Local AI processing for complex queries and tool calls
- RAG integration for Swedish context  
- Streaming responses with chunked TTS
- Confirmation responses while processing ("Okej, kollar...")
- Privacy-first approach (no data to OpenAI)
- Tool calling integration with existing Alice tools
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, List, Callable, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import os
import httpx
from datetime import datetime

from core.tool_registry import validate_and_execute_tool, enabled_tools
from memory import MemoryStore

logger = logging.getLogger("alice.think_path")

class ThinkPathState(Enum):
    IDLE = "idle"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    EXECUTING = "executing"
    RESPONDING = "responding"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class ThinkPathRequest:
    """Request for think path processing"""
    session_id: str
    text: str
    intent: str
    confidence: float
    context: Dict[str, Any] = None
    tools_available: List[str] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.context is None:
            self.context = {}
        if self.tools_available is None:
            self.tools_available = []

@dataclass  
class ThinkPathResponse:
    """Response from think path processing"""
    success: bool
    response_text: str = ""
    tools_used: List[str] = None
    reasoning_steps: List[str] = None
    processing_time_ms: float = 0.0
    confidence: float = 0.0
    requires_followup: bool = False
    error_message: Optional[str] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.tools_used is None:
            self.tools_used = []
        if self.reasoning_steps is None:
            self.reasoning_steps = []

class SwedishContextProvider:
    """Provides Swedish cultural context and localization for responses"""
    
    def __init__(self):
        self.swedish_contexts = {
            "greetings": {
                "morning": ["God morgon", "Morgon", "Hej där"],
                "afternoon": ["God eftermiddag", "Hej", "Tjena"],
                "evening": ["God kväll", "Hej", "Kvällens"],
                "night": ["God natt", "Natti", "Sov gott"]
            },
            "confirmations": [
                "Okej, jag kollar det åt dig.",
                "Absolut, låt mig titta på det.",
                "Ja, jag hjälper dig med det.",
                "Visst, jag undersöker det.",
                "Självklart, ett ögonblick."
            ],
            "thinking_phrases": [
                "Låt mig tänka...",
                "Jag funderar på det här...",
                "Hmm, det här kräver lite reflektion...",
                "Intressant fråga, jag analyserar...",
                "Jag bearbetar informationen..."
            ],
            "working_phrases": [
                "Jag arbetar på det...",
                "Kollar igenom alternativen...",
                "Söker efter den bästa lösningen...",
                "Går igenom möjligheterna...",
                "Bearbetar din förfrågan..."
            ],
            "apologies": [
                "Ursäkta, jag kunde inte...",
                "Tyvärr gick något fel...",
                "Jag beklagar, det uppstod ett problem...",
                "Ledsen, jag kunde inte slutföra..."
            ]
        }
        
        self.time_expressions = {
            "now": "nu", "today": "idag", "tomorrow": "imorgon",
            "yesterday": "igår", "this_week": "den här veckan",
            "next_week": "nästa vecka", "this_month": "den här månaden"
        }
        
        self.date_format = "%d %B %Y"
        self.time_format = "%H:%M"
    
    def get_confirmation_phrase(self) -> str:
        """Get random Swedish confirmation phrase"""
        import random
        return random.choice(self.swedish_contexts["confirmations"])
    
    def get_thinking_phrase(self) -> str:
        """Get random Swedish thinking phrase"""
        import random
        return random.choice(self.swedish_contexts["thinking_phrases"])
    
    def get_working_phrase(self) -> str:
        """Get random Swedish working phrase"""
        import random
        return random.choice(self.swedish_contexts["working_phrases"])
    
    def localize_response(self, response: str) -> str:
        """Localize response to Swedish context"""
        # Replace common English expressions with Swedish equivalents
        localizations = {
            "I'm working on it": "Jag arbetar på det",
            "Let me check": "Låt mig kolla",
            "One moment": "Ett ögonblick",
            "Please wait": "Vänta lite",
            "I understand": "Jag förstår",
            "That's interesting": "Det är intressant",
            "I see": "Jag ser",
            "Of course": "Självklart"
        }
        
        localized = response
        for english, swedish in localizations.items():
            localized = localized.replace(english, swedish)
            
        return localized

class ThinkPathHandler:
    """
    Think Path Handler for complex local AI processing
    
    Handles complex queries, tool calls, and reasoning using local gpt-oss:20B
    while maintaining privacy boundaries and providing Swedish context.
    """
    
    def __init__(self, memory_store: MemoryStore):
        self.memory = memory_store
        self.swedish_context = SwedishContextProvider()
        
        # Ollama client for local AI
        self.ollama_client = httpx.AsyncClient(timeout=30.0)
        
        # Configuration
        self.config = {
            "ollama_host": os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
            "model": os.getenv("LOCAL_MODEL", "gpt-oss:20b"),
            "max_tokens": int(os.getenv("LOCAL_AI_MAX_TOKENS", "2048")),
            "temperature": float(os.getenv("LOCAL_AI_TEMPERATURE", "0.3")),
            "timeout_ms": int(os.getenv("THINK_PATH_TIMEOUT_MS", "15000")),
            "stream_response": True,
            "swedish_optimization": True
        }
        
        # System prompt for Swedish AI assistant
        self.system_prompt = """Du är Alice, en intelligent svensk AI-assistent med djup förståelse för svenska språket och kulturen.

Du hjälper användare med komplexa uppgifter som kräver eftertanke och verktygsanvändning. Du svarar alltid på svenska och anpassar dina svar till svensk kultur och kontext.

Dina huvudfunktioner:
- Komplexa frågor som kräver resonemang
- Verktygsanvändning (kalender, e-post, musik, dokument)
- Kontextuell förståelse baserat på tidigare konversationer
- Svenska språk- och kulturspecifika svar

Riktlinjer:
- Svara alltid på svenska
- Var tydlig och hjälpsam
- Använd svenska uttryck och kulturella referenser
- Förklara dina resonemangssteg när det är relevant
- Använd tillgängliga verktyg när det behövs
- Håll svaren koncisa men informativa

Om du behöver använda verktyg, beskriv först vad du ska göra, utför sedan åtgärden och rapportera resultatet."""

        # Performance metrics
        self.metrics = {
            "requests": 0,
            "successes": 0,
            "tool_calls": 0,
            "errors": 0,
            "total_processing_ms": 0.0,
            "average_confidence": 0.0,
            "reasoning_steps": 0
        }
        
        # Event handlers
        self.on_confirmation: Optional[Callable] = None
        self.on_thinking_update: Optional[Callable] = None
        self.on_tool_execution: Optional[Callable] = None
        self.on_response_chunk: Optional[Callable] = None
        self.on_response_complete: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
    
    async def initialize(self) -> bool:
        """Initialize think path handler and verify local AI connection"""
        try:
            # Test Ollama connection
            response = await self.ollama_client.get(f"{self.config['ollama_host']}/api/tags")
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model["name"] for model in models]
                
                if self.config["model"] in model_names:
                    logger.info(f"Think Path Handler initialized with {self.config['model']}")
                    return True
                else:
                    logger.warning(f"Model {self.config['model']} not found. Available: {model_names}")
                    return False
            else:
                logger.error(f"Ollama connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Think Path Handler initialization failed: {e}")
            return False
    
    async def process_request(self, request: ThinkPathRequest) -> AsyncGenerator[ThinkPathResponse, None]:
        """
        Process request through think path with streaming responses
        
        Args:
            request: ThinkPathRequest with text and context
            
        Yields:
            ThinkPathResponse updates during processing
        """
        start_time = time.time()
        self.metrics["requests"] += 1
        
        try:
            # Send initial confirmation
            confirmation = self.swedish_context.get_confirmation_phrase()
            yield ThinkPathResponse(
                success=True,
                response_text=confirmation,
                confidence=1.0,
                reasoning_steps=["Initial confirmation sent"]
            )
            
            if self.on_confirmation:
                await self.on_confirmation(confirmation)
            
            # Analyze the request
            yield ThinkPathResponse(
                success=True, 
                response_text=self.swedish_context.get_thinking_phrase(),
                reasoning_steps=["Analyzing request complexity and context"]
            )
            
            # Get conversation context
            context = await self._get_conversation_context(request.session_id)
            
            # Determine if tools are needed
            available_tools = enabled_tools()
            needs_tools = await self._analyze_tool_requirements(request.text, available_tools)
            
            if needs_tools:
                yield ThinkPathResponse(
                    success=True,
                    response_text="Jag förbereder de verktyg som behövs...",
                    reasoning_steps=["Identified tool requirements", f"Available tools: {', '.join(needs_tools)}"]
                )
            
            # Generate response using local AI
            async for response_chunk in self._generate_local_response(
                request, context, needs_tools
            ):
                yield response_chunk
            
            # Final processing metrics
            processing_time = (time.time() - start_time) * 1000
            self.metrics["successes"] += 1
            self.metrics["total_processing_ms"] += processing_time
            
            if needs_tools:
                self.metrics["tool_calls"] += len(needs_tools)
            
            logger.info(f"Think path completed: {processing_time:.1f}ms for '{request.text[:50]}'")
            
        except Exception as e:
            error_msg = f"Think path error: {e}"
            logger.error(error_msg)
            self.metrics["errors"] += 1
            
            if self.on_error:
                await self.on_error(error_msg)
            
            yield ThinkPathResponse(
                success=False,
                error_message=error_msg,
                response_text="Tyvärr uppstod ett fel när jag försökte bearbeta din förfrågan."
            )
    
    async def _get_conversation_context(self, session_id: str) -> Dict[str, Any]:
        """Get conversation context from memory"""
        try:
            # Get recent conversation history
            memory_entries = await self.memory.get_recent_memories(session_id, limit=10)
            
            context = {
                "recent_topics": [],
                "user_preferences": {},
                "conversation_history": []
            }
            
            for entry in memory_entries:
                if entry.get("type") == "conversation":
                    context["conversation_history"].append({
                        "role": entry.get("role", "user"),
                        "content": entry.get("content", ""),
                        "timestamp": entry.get("timestamp")
                    })
                elif entry.get("type") == "preference":
                    context["user_preferences"].update(entry.get("data", {}))
            
            return context
            
        except Exception as e:
            logger.warning(f"Failed to get conversation context: {e}")
            return {"conversation_history": [], "user_preferences": {}}
    
    async def _analyze_tool_requirements(self, text: str, available_tools: List[str]) -> List[str]:
        """Analyze if request needs tool execution"""
        text_lower = text.lower()
        needed_tools = []
        
        # Map text patterns to tools
        tool_patterns = {
            "GMAIL": ["email", "mejl", "skicka meddelande", "läs email"],
            "CALENDAR": ["kalender", "möte", "boka", "schemalägg", "tid"],
            "SPOTIFY": ["musik", "spela", "låt", "artist", "album"],
            "WEATHER": ["väder", "temperatur", "regn", "sol", "prognos"],
            "CALCULATOR": ["räkna", "beräkna", "matematik", "plus", "minus"],
            "FILE_OPERATIONS": ["fil", "dokument", "spara", "öppna", "läs fil"],
            "WEB_SEARCH": ["sök", "google", "hitta information", "leta upp"]
        }
        
        for tool, patterns in tool_patterns.items():
            if tool in available_tools:
                if any(pattern in text_lower for pattern in patterns):
                    needed_tools.append(tool)
        
        return needed_tools
    
    async def _generate_local_response(
        self, 
        request: ThinkPathRequest, 
        context: Dict[str, Any], 
        tools_needed: List[str]
    ) -> AsyncGenerator[ThinkPathResponse, None]:
        """Generate response using local gpt-oss:20B model"""
        
        # Build enhanced prompt with context
        enhanced_prompt = self._build_enhanced_prompt(request, context, tools_needed)
        
        # If tools are needed, execute them first
        tool_results = {}
        if tools_needed:
            yield ThinkPathResponse(
                success=True,
                response_text=self.swedish_context.get_working_phrase(),
                reasoning_steps=[f"Executing tools: {', '.join(tools_needed)}"]
            )
            
            tool_results = await self._execute_tools(request, tools_needed)
            
            if self.on_tool_execution:
                await self.on_tool_execution(tool_results)
        
        # Generate AI response
        try:
            ollama_request = {
                "model": self.config["model"],
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": enhanced_prompt}
                ],
                "stream": self.config["stream_response"],
                "options": {
                    "temperature": self.config["temperature"],
                    "num_predict": self.config["max_tokens"]
                }
            }
            
            if self.config["stream_response"]:
                # Stream response from Ollama
                async with self.ollama_client.stream(
                    'POST',
                    f"{self.config['ollama_host']}/api/chat",
                    json=ollama_request,
                    timeout=self.config["timeout_ms"] / 1000.0
                ) as response:
                    
                    full_response = ""
                    reasoning_steps = []
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                chunk_data = json.loads(line)
                                
                                if "message" in chunk_data:
                                    content = chunk_data["message"].get("content", "")
                                    if content:
                                        full_response += content
                                        
                                        # Stream chunk to client
                                        if self.on_response_chunk:
                                            await self.on_response_chunk(content)
                                        
                                        yield ThinkPathResponse(
                                            success=True,
                                            response_text=content,
                                            tools_used=tools_needed,
                                            reasoning_steps=reasoning_steps
                                        )
                                
                                if chunk_data.get("done", False):
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                    
                    # Localize final response
                    localized_response = self.swedish_context.localize_response(full_response)
                    
                    # Include tool results if any
                    if tool_results:
                        tool_summary = self._summarize_tool_results(tool_results)
                        localized_response = f"{localized_response}\n\n{tool_summary}"
                    
                    # Store conversation in memory
                    await self._store_conversation(
                        request.session_id,
                        request.text,
                        localized_response,
                        tools_needed,
                        tool_results
                    )
                    
                    # Final response
                    yield ThinkPathResponse(
                        success=True,
                        response_text=localized_response,
                        tools_used=tools_needed,
                        reasoning_steps=reasoning_steps + ["Response generated and localized"],
                        confidence=0.85,
                        requires_followup=self._check_requires_followup(localized_response)
                    )
                    
                    if self.on_response_complete:
                        await self.on_response_complete(localized_response)
                        
            else:
                # Non-streaming response
                response = await self.ollama_client.post(
                    f"{self.config['ollama_host']}/api/chat",
                    json=ollama_request,
                    timeout=self.config["timeout_ms"] / 1000.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result.get("message", {}).get("content", "")
                    
                    localized_response = self.swedish_context.localize_response(ai_response)
                    
                    if tool_results:
                        tool_summary = self._summarize_tool_results(tool_results)
                        localized_response = f"{localized_response}\n\n{tool_summary}"
                    
                    await self._store_conversation(
                        request.session_id,
                        request.text,
                        localized_response,
                        tools_needed,
                        tool_results
                    )
                    
                    yield ThinkPathResponse(
                        success=True,
                        response_text=localized_response,
                        tools_used=tools_needed,
                        confidence=0.85
                    )
                else:
                    raise Exception(f"Ollama request failed: {response.status_code}")
                    
        except asyncio.TimeoutError:
            yield ThinkPathResponse(
                success=False,
                error_message="Local AI response timeout",
                response_text="Ursäkta, det tog för lång tid att bearbeta din förfrågan."
            )
        except Exception as e:
            yield ThinkPathResponse(
                success=False,
                error_message=f"Local AI error: {e}",
                response_text="Tyvärr kunde jag inte bearbeta din förfrågan med lokal AI."
            )
    
    def _build_enhanced_prompt(
        self, 
        request: ThinkPathRequest, 
        context: Dict[str, Any], 
        tools_needed: List[str]
    ) -> str:
        """Build enhanced prompt with context and tool information"""
        
        prompt_parts = [f"Användarfråga: {request.text}"]
        
        # Add conversation context
        if context.get("conversation_history"):
            prompt_parts.append("\nKonversationskontext:")
            for entry in context["conversation_history"][-3:]:  # Last 3 entries
                role = "Användare" if entry["role"] == "user" else "Alice"
                prompt_parts.append(f"{role}: {entry['content']}")
        
        # Add available tools
        if tools_needed:
            prompt_parts.append(f"\nTillgängliga verktyg: {', '.join(tools_needed)}")
            prompt_parts.append("Använd verktygen när det behövs för att ge ett komplett svar.")
        
        # Add user preferences if available
        if context.get("user_preferences"):
            prompt_parts.append(f"\nAnvändarpreferenser: {json.dumps(context['user_preferences'], ensure_ascii=False)}")
        
        # Add current time context
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        prompt_parts.append(f"\nNuvarande tid: {current_time}")
        
        return "\n".join(prompt_parts)
    
    async def _execute_tools(self, request: ThinkPathRequest, tools_needed: List[str]) -> Dict[str, Any]:
        """Execute required tools and return results"""
        tool_results = {}
        
        for tool in tools_needed:
            try:
                # Extract arguments for tool (simplified)
                args = self._extract_tool_args(request.text, tool)
                
                # Execute tool
                result = await validate_and_execute_tool(tool, args)
                tool_results[tool] = result
                
                logger.debug(f"Tool {tool} executed with result: {result.get('success', False)}")
                
            except Exception as e:
                logger.error(f"Tool {tool} execution failed: {e}")
                tool_results[tool] = {
                    "success": False,
                    "error": str(e),
                    "message": f"Verktyg {tool} kunde inte köras"
                }
        
        return tool_results
    
    def _extract_tool_args(self, text: str, tool: str) -> Dict[str, Any]:
        """Extract arguments for tool from text (simplified implementation)"""
        # This is a simplified implementation
        # In practice, you'd use NLU to extract structured arguments
        
        args = {}
        text_lower = text.lower()
        
        if tool == "WEATHER":
            # Look for location mentions
            if "stockholm" in text_lower:
                args["location"] = "Stockholm"
            elif "göteborg" in text_lower:
                args["location"] = "Göteborg"
            else:
                args["location"] = "Stockholm"  # Default
        
        elif tool == "CALENDAR":
            # Look for time expressions
            if "imorgon" in text_lower:
                args["date"] = "tomorrow"
            elif "idag" in text_lower:
                args["date"] = "today"
        
        elif tool == "SPOTIFY":
            # Look for music requests
            words = text_lower.split()
            if "spela" in words:
                # Find what to play
                spela_index = words.index("spela")
                if spela_index + 1 < len(words):
                    args["query"] = " ".join(words[spela_index + 1:])
        
        return args
    
    def _summarize_tool_results(self, tool_results: Dict[str, Any]) -> str:
        """Summarize tool execution results for user"""
        summary_parts = []
        
        for tool, result in tool_results.items():
            if result.get("success"):
                message = result.get("message", f"Verktyg {tool} kördes framgångsrikt")
                summary_parts.append(f"✅ {message}")
            else:
                error = result.get("error", f"Verktyg {tool} misslyckades")
                summary_parts.append(f"❌ {error}")
        
        if summary_parts:
            return "Verktygsresultat:\n" + "\n".join(summary_parts)
        
        return ""
    
    def _check_requires_followup(self, response: str) -> bool:
        """Check if response suggests a followup is needed"""
        followup_indicators = [
            "vill du", "behöver du", "ska jag", "kan jag hjälpa",
            "mer information", "något annat", "fortsätta"
        ]
        
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in followup_indicators)
    
    async def _store_conversation(
        self, 
        session_id: str, 
        user_input: str, 
        ai_response: str, 
        tools_used: List[str],
        tool_results: Dict[str, Any]
    ):
        """Store conversation in memory"""
        try:
            # Store user input
            await self.memory.store_memory(
                session_id,
                "conversation",
                {
                    "role": "user",
                    "content": user_input,
                    "timestamp": time.time()
                }
            )
            
            # Store AI response with metadata
            await self.memory.store_memory(
                session_id,
                "conversation", 
                {
                    "role": "assistant",
                    "content": ai_response,
                    "tools_used": tools_used,
                    "tool_results": tool_results,
                    "processing_path": "think",
                    "timestamp": time.time()
                }
            )
            
        except Exception as e:
            logger.warning(f"Failed to store conversation: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get think path performance metrics"""
        total_requests = max(self.metrics["requests"], 1)
        
        return {
            "total_requests": self.metrics["requests"],
            "success_rate": self.metrics["successes"] / total_requests,
            "error_rate": self.metrics["errors"] / total_requests,
            "tool_usage_rate": self.metrics["tool_calls"] / total_requests,
            "average_processing_ms": self.metrics["total_processing_ms"] / max(self.metrics["successes"], 1),
            "average_confidence": self.metrics["average_confidence"],
            "total_reasoning_steps": self.metrics["reasoning_steps"]
        }
    
    def reset_metrics(self):
        """Reset performance metrics"""
        self.metrics = {
            "requests": 0,
            "successes": 0,
            "tool_calls": 0,
            "errors": 0,
            "total_processing_ms": 0.0,
            "average_confidence": 0.0,
            "reasoning_steps": 0
        }
    
    async def shutdown(self):
        """Shutdown think path handler"""
        await self.ollama_client.aclose()
        logger.info("Think Path Handler shutdown completed")

# Global think path handler instance
think_path_handler = None

def get_think_path_handler(memory_store: MemoryStore) -> ThinkPathHandler:
    """Get or create think path handler instance"""
    global think_path_handler
    if think_path_handler is None:
        think_path_handler = ThinkPathHandler(memory_store)
    return think_path_handler