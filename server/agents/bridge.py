"""
Alice Agent Bridge
Brygga mellan OpenAI Realtime API och Alice's befintliga Agent Core system.
Integrerar med gpt-oss:20B via Ollama och Agent Orchestrator.
"""

from __future__ import annotations

import asyncio
import json
import time
import logging
import os
from typing import AsyncGenerator, Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime

import httpx
from pydantic import BaseModel

# Import Alice's existing systems
from core import (
    AgentOrchestrator, WorkflowConfig, WorkflowResult,
    AgentExecutor, AgentCritic, 
    validate_and_execute_tool, is_tool_enabled
)
from core.agent_planner import AgentPlanner
from memory import MemoryStore
from prompts.system_prompts import system_prompt, developer_prompt
from deps import OpenAISettings, get_global_openai_settings

logger = logging.getLogger("alice.agents.bridge")


class StreamChunkType(str):
    """Typer av stream-chunks för SSE-kompatibilitet"""
    CHUNK = "chunk"           # Text-chunk från modell
    TOOL = "tool"            # Tool execution result 
    META = "meta"            # Metadata (verktygsanrop, latency etc)
    DONE = "done"            # Stream slutförd
    ERROR = "error"          # Fel uppstod
    PLANNING = "planning"    # Agent planerar
    EXECUTING = "executing"  # Agent exekverar
    EVALUATING = "evaluating" # Agent utvärderar


@dataclass
class StreamChunk:
    """En chunk i response-streamen"""
    type: str
    content: str = ""
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_sse_format(self) -> str:
        """Konvertera till Server-Sent Events format"""
        payload = {
            "type": self.type,
            "timestamp": self.timestamp.isoformat()
        }
        
        if self.content:
            payload["text"] = self.content
        
        if self.data:
            payload.update(self.data)
        
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


class AgentBridgeRequest(BaseModel):
    """Request för agent bridge"""
    prompt: str
    model: Optional[str] = "gpt-oss:20b"
    provider: Optional[str] = "local"  # 'local' | 'openai' | 'auto'
    context: Optional[Dict[str, Any]] = None
    use_rag: bool = True
    use_tools: bool = True
    use_agent_core: bool = False  # Om Agent Orchestrator ska användas
    language: str = "svenska"
    raw: bool = False  # Skip RAG och context
    workflow_config: Optional[Dict[str, Any]] = None


class AliceAgentBridge:
    """
    Brygga som integrerar Alice's befintliga gpt-oss:20b system
    med OpenAI Realtime API patterns och Agent Core.
    """
    
    def __init__(self, 
                 memory_store: MemoryStore,
                 orchestrator: Optional[AgentOrchestrator] = None,
                 openai_settings: Optional[OpenAISettings] = None):
        self.memory = memory_store
        self.orchestrator = orchestrator or self._create_default_orchestrator()
        self.openai_settings = openai_settings or get_global_openai_settings()
        
        # Alice's existing patterns
        self.ollama_url = "http://127.0.0.1:11434/api/generate"
        self.use_harmony = os.getenv("USE_HARMONY", "true").lower() == "true"
        self.use_tools = os.getenv("USE_TOOLS", "true").lower() == "true"
        self.harmony_temperature = float(os.getenv("HARMONY_TEMPERATURE_COMMANDS", "0.15"))
        
        # Track active streams
        self.active_streams: Dict[str, bool] = {}
    
    def _create_default_orchestrator(self) -> AgentOrchestrator:
        """Skapa standard Agent Orchestrator"""
        planner = AgentPlanner()
        executor = AgentExecutor()
        critic = AgentCritic()
        
        config = WorkflowConfig(
            max_iterations=2,
            auto_improve=True,
            min_success_score=0.7,
            enable_ai_planning=False,  # Använd Alice's befintliga system
            enable_ai_criticism=False
        )
        
        return AgentOrchestrator(planner, executor, critic, config)
    
    async def stream_response(self, request: AgentBridgeRequest) -> AsyncGenerator[StreamChunk, None]:
        """
        Huvudmetod för att strömma svar från Alice's agent system.
        Kombinerar RAG, verktyg, Agent Core och streaming.
        """
        stream_id = f"stream_{int(time.time() * 1000)}"
        self.active_streams[stream_id] = True
        
        try:
            # === RAG Context Building ===
            if request.use_rag and not request.raw:
                yield StreamChunk(type=StreamChunkType.PLANNING, content="Hämtar relevant kontext...")
                contexts = await self._get_rag_context(request.prompt)
                context_text = self._format_context(contexts, request.context)
            else:
                contexts = []
                context_text = ""
            
            # === Prompt Building ===
            full_prompt = self._build_prompt(
                user_prompt=request.prompt,
                context_text=context_text,
                raw=request.raw,
                language=request.language
            )
            
            # === Agent Core Integration ===
            if request.use_agent_core:
                async for chunk in self._stream_via_agent_core(full_prompt, request):
                    if not self.active_streams.get(stream_id, False):
                        break
                    yield chunk
            else:
                # === Direct Model Streaming ===  
                async for chunk in self._stream_via_model(full_prompt, request):
                    if not self.active_streams.get(stream_id, False):
                        break
                    yield chunk
            
            # === Final Memory Storage ===
            yield StreamChunk(type=StreamChunkType.DONE, 
                            data={"stream_id": stream_id, "contexts_used": len(contexts)})
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield StreamChunk(type=StreamChunkType.ERROR, 
                            content=f"Fel uppstod: {str(e)}")
        finally:
            self.active_streams.pop(stream_id, None)
    
    async def _get_rag_context(self, query: str) -> List[Dict[str, Any]]:
        """Hämta RAG-kontext från Alice's memory system"""
        try:
            # Använd Alice's befintliga retrieval system
            contexts = self.memory.retrieve_text_memories(query, limit=5)
            if not contexts:
                # Fallback till BM25 
                contexts = self.memory.retrieve_text_bm25_recency(query, limit=5)
            return contexts or []
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
            return []
    
    def _format_context(self, contexts: List[Dict[str, Any]], 
                       additional_context: Optional[Dict[str, Any]] = None) -> str:
        """Formatera kontext för prompten (Alice's befintliga format)"""
        context_parts = []
        
        # System/HUD context
        if additional_context:
            if additional_context.get('weather'):
                context_parts.append(f"Aktuellt väder: {additional_context['weather']}")
            if additional_context.get('location'):
                context_parts.append(f"Plats: {additional_context['location']}")
            if additional_context.get('time'):
                context_parts.append(f"Tid: {additional_context['time']}")
            if additional_context.get('systemMetrics'):
                metrics = additional_context['systemMetrics']
                context_parts.append(f"System: CPU {metrics.get('cpu', 0)}%, "
                                   f"RAM {metrics.get('mem', 0)}%, "
                                   f"Nätverk {metrics.get('net', 0)}%")
        
        # RAG memories
        memory_text = "\n".join([f"- {ctx.get('text', '')}" 
                               for ctx in contexts if ctx.get('text')])
        
        # Combine contexts
        result = ""
        if context_parts:
            result += "Aktuell systeminfo:\n" + "\n".join(f"- {part}" for part in context_parts) + "\n\n"
        if memory_text:
            result += f"Relevanta minnen:\n{memory_text}\n\n"
        
        return result
    
    def _build_prompt(self, user_prompt: str, context_text: str, 
                     raw: bool = False, language: str = "svenska") -> str:
        """Bygg komplett prompt i Alice's format"""
        if raw:
            return f"Besvara på {language}.\n\nFråga: {user_prompt}\nSvar:"
        
        base_prompt = context_text if context_text else ""
        base_prompt += f"Använd relevant kontext ovan vid behov. Besvara på {language}.\n\n"
        base_prompt += f"Fråga: {user_prompt}\nSvar:"
        
        return base_prompt
    
    async def _stream_via_agent_core(self, prompt: str, 
                                   request: AgentBridgeRequest) -> AsyncGenerator[StreamChunk, None]:
        """Strömma via Agent Orchestrator (experimentell)"""
        yield StreamChunk(type=StreamChunkType.PLANNING, 
                         content="Startar Agent Core workflow...")
        
        # Konvertera workflow_config om provided
        workflow_config = WorkflowConfig()
        if request.workflow_config:
            for key, value in request.workflow_config.items():
                if hasattr(workflow_config, key):
                    setattr(workflow_config, key, value)
        
        # Progress callback för streaming updates
        async def progress_callback(progress_info: Dict[str, Any]):
            status = progress_info.get("status", "")
            message = progress_info.get("message", "")
            
            if status == "planning":
                yield StreamChunk(type=StreamChunkType.PLANNING, content=message)
            elif status == "executing":
                yield StreamChunk(type=StreamChunkType.EXECUTING, content=message)  
            elif status == "evaluating":
                yield StreamChunk(type=StreamChunkType.EVALUATING, content=message)
        
        try:
            # Exekvera workflow
            result = await self.orchestrator.execute_workflow(
                goal=prompt,
                context={"language": request.language, "user_prompt": request.prompt},
                config_override=workflow_config,
                progress_callback=progress_callback
            )
            
            # Stream resultatet
            if result.success and result.final_execution:
                # Extrahera text från execution results
                final_text = self._extract_text_from_workflow(result)
                
                # Stream som chunks för naturlig respons
                for chunk in self._chunk_text(final_text):
                    yield StreamChunk(type=StreamChunkType.CHUNK, content=chunk)
            else:
                yield StreamChunk(type=StreamChunkType.ERROR, 
                                content="Agent Core kunde inte slutföra uppgiften")
                
        except Exception as e:
            yield StreamChunk(type=StreamChunkType.ERROR, 
                            content=f"Agent Core error: {str(e)}")
    
    async def _stream_via_model(self, prompt: str, 
                              request: AgentBridgeRequest) -> AsyncGenerator[StreamChunk, None]:
        """Strömma direkt via gpt-oss:20b (Alice's huvudsystem)"""
        if request.provider == "openai":
            async for chunk in self._stream_openai(prompt, request):
                yield chunk
        else:
            # Local/Ollama (Alice's huvudsystem)
            async for chunk in self._stream_ollama(prompt, request):
                yield chunk
    
    async def _stream_ollama(self, prompt: str, 
                           request: AgentBridgeRequest) -> AsyncGenerator[StreamChunk, None]:
        """Strömma från Ollama (gpt-oss:20b) - Alice's befintliga implementation"""
        try:
            # Förbered Harmony-formaterad prompt om enabled
            if self.use_harmony:
                formatted_prompt = (
                    f"System: {system_prompt()}\n"
                    f"Developer: {developer_prompt()}\n"
                    f"User: {prompt}\nSvar: "
                )
            else:
                formatted_prompt = (
                    f"System: Du heter Alice och är en svensk AI-assistent. "
                    f"Du är INTE ChatGPT. Presentera dig alltid som Alice. "
                    f"Svara på svenska.\n\n"
                    f"User: {prompt}\nAlice:"
                )
            
            payload = {
                "model": request.model or os.getenv("LOCAL_MODEL", "gpt-oss:20b"),
                "prompt": formatted_prompt,
                "stream": True,
                "options": {
                    "num_predict": 256,
                    "temperature": self.harmony_temperature if self.use_harmony else 0.5,
                    "stop": ["User:", "System:", "Developer:"]
                }
            }
            
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", self.ollama_url, json=payload) as response:
                    if response.status_code != 200:
                        yield StreamChunk(type=StreamChunkType.ERROR, 
                                        content=f"Ollama error: {response.status_code}")
                        return
                    
                    buffer_text = ""
                    final_started = False
                    final_ended = False
                    
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        try:
                            data = json.loads(line)
                            raw_text = data.get("response", "")
                            
                            if not raw_text:
                                continue
                            
                            # Harmony filtering för [FINAL]...[/FINAL] tags
                            if self.use_harmony:
                                buffer_text += raw_text
                                
                                # Kolla för tool calls först
                                if self.use_tools and "[TOOL_CALL]" in buffer_text and "}" in buffer_text:
                                    tool_result = await self._handle_harmony_tool(buffer_text, request)
                                    if tool_result:
                                        yield tool_result
                                        continue
                                
                                # Extrahera FINAL content
                                output_chunk = self._extract_harmony_content(buffer_text)
                                if output_chunk:
                                    yield StreamChunk(type=StreamChunkType.CHUNK, content=output_chunk)
                                    buffer_text = ""
                            else:
                                # Direkt streaming utan Harmony
                                yield StreamChunk(type=StreamChunkType.CHUNK, content=raw_text)
                            
                            if data.get("done", False):
                                break
                                
                        except json.JSONDecodeError:
                            continue
                    
                    # Slutföra eventuellt kvarvarande buffer content
                    if self.use_harmony and buffer_text:
                        remaining = self._extract_harmony_content(buffer_text, force_extract=True)
                        if remaining:
                            yield StreamChunk(type=StreamChunkType.CHUNK, content=remaining)
                            
        except Exception as e:
            yield StreamChunk(type=StreamChunkType.ERROR, 
                            content=f"Streaming error: {str(e)}")
    
    async def _stream_openai(self, prompt: str, 
                           request: AgentBridgeRequest) -> AsyncGenerator[StreamChunk, None]:
        """Strömma från OpenAI API"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            yield StreamChunk(type=StreamChunkType.ERROR, 
                            content="OpenAI API key saknas")
            return
        
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            
            # Formatera meddelanden enligt OpenAI format
            if self.use_harmony:
                messages = [
                    {"role": "system", "content": system_prompt()},
                    {"role": "developer", "content": developer_prompt()}, 
                    {"role": "user", "content": prompt}
                ]
            else:
                messages = [
                    {"role": "system", "content": "Du är Alice. Svara på svenska."},
                    {"role": "user", "content": prompt}
                ]
            
            payload = {
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": messages,
                "temperature": self.harmony_temperature if self.use_harmony else 0.5,
                "stream": True,
                "max_tokens": 256
            }
            
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", "https://api.openai.com/v1/chat/completions", 
                                       headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        yield StreamChunk(type=StreamChunkType.ERROR, 
                                        content=f"OpenAI error: {response.status_code}")
                        return
                    
                    async for line in response.aiter_lines():
                        if not line.strip() or not line.startswith("data: "):
                            continue
                        
                        data_part = line[6:].strip()  # Remove "data: "
                        if data_part == "[DONE]":
                            break
                        
                        try:
                            data = json.loads(data_part)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                yield StreamChunk(type=StreamChunkType.CHUNK, content=content)
                                
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            yield StreamChunk(type=StreamChunkType.ERROR, 
                            content=f"OpenAI streaming error: {str(e)}")
    
    def _extract_harmony_content(self, buffer_text: str, force_extract: bool = False) -> str:
        """Extrahera content mellan [FINAL]...[/FINAL] tags"""
        if not self.use_harmony:
            return buffer_text
        
        start_tag = "[FINAL]"
        end_tag = "[/FINAL]" 
        
        start_idx = buffer_text.find(start_tag)
        if start_idx == -1:
            return "" if not force_extract else buffer_text
        
        content_start = start_idx + len(start_tag)
        end_idx = buffer_text.find(end_tag, content_start)
        
        if end_idx == -1:
            return "" if not force_extract else buffer_text[content_start:]
        
        return buffer_text[content_start:end_idx]
    
    async def _handle_harmony_tool(self, buffer_text: str, 
                                 request: AgentBridgeRequest) -> Optional[StreamChunk]:
        """Hantera Harmony tool calls"""
        if not self.use_tools or "[TOOL_CALL]" not in buffer_text:
            return None
        
        try:
            # Parse tool call using Alice's helper method
            tool_call = self._maybe_parse_tool_call(buffer_text)
            if not tool_call:
                return None
            
            tool_name = str(tool_call.get("tool", "")).upper()
            tool_args = tool_call.get("args", {})
            
            if not is_tool_enabled(tool_name):
                return None
            
            # Execute tool
            start_time = time.time()
            result = validate_and_execute_tool(tool_name, tool_args, self.memory)
            execution_time = (time.time() - start_time) * 1000
            
            # Format bekräftelse (Alice's format)
            if result.get("ok"):
                confirmation = f"✅ {tool_name}: {self._format_tool_confirmation(tool_name, tool_args)}"
                
                return StreamChunk(
                    type=StreamChunkType.TOOL,
                    content=confirmation,
                    data={
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result,
                        "execution_time_ms": execution_time,
                        "success": True
                    }
                )
            else:
                return StreamChunk(
                    type=StreamChunkType.ERROR,
                    content=f"❌ Verktyg {tool_name} misslyckades: {result.get('error', 'Okänt fel')}",
                    data={
                        "tool": tool_name,
                        "args": tool_args,
                        "error": result.get('error'),
                        "success": False
                    }
                )
                
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return StreamChunk(
                type=StreamChunkType.ERROR,
                content=f"Verktygsfel: {str(e)}"
            )
    
    def _maybe_parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """Detektera ett verktygsanrop i modellens svar (Alice's format)"""
        try:
            if not text:
                return None
            s = text.strip()
            # 1) [TOOL_CALL]{json}
            if s.startswith("[TOOL_CALL]"):
                s = s[len("[TOOL_CALL]"):].lstrip()
            # Försök att hitta ett JSON-objekt
            import re as _re
            m = _re.search(r"\{[\s\S]*\}", s)
            if not m:
                return None
            candidate = json.loads(m.group(0))
            if isinstance(candidate, dict) and isinstance(candidate.get("tool"), str):
                args = candidate.get("args") or {}
                if isinstance(args, dict):
                    return {"tool": candidate["tool"], "args": args}
        except Exception:
            return None
        return None

    def _format_tool_confirmation(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Formatera verktygsbekräftelse (Alice's exact format)"""
        n = (tool_name or "").upper()
        a = args or {}
        if n == "PLAY":
            return "Spelar upp."
        if n == "PAUSE":
            return "Pausar."
        if n == "SET_VOLUME":
            if isinstance(a.get("level"), int):
                return f"Volym satt till {a['level']}%."
            if isinstance(a.get("delta"), int):
                d = a['delta']
                return f"Volym {'höjd' if d>0 else 'sänkt'} med {abs(d)}%."
            return "Volym uppdaterad."
        if n == "SAY":
            return str(a.get("text") or "")
        if n == "DISPLAY":
            return str(a.get("text") or "")
        return "Klart."
    
    def _extract_text_from_workflow(self, result: WorkflowResult) -> str:
        """Extrahera text från Agent Orchestrator result"""
        if not result.final_execution or not result.final_execution.results:
            return "Agent Core slutförde uppgiften men gav inget textsvar."
        
        # Sammanställ text från execution results
        texts = []
        for exec_result in result.final_execution.results.values():
            if exec_result.result and "text" in exec_result.result:
                texts.append(exec_result.result["text"])
        
        return " ".join(texts) if texts else "Uppgiften utförd."
    
    def _chunk_text(self, text: str, chunk_size: int = 50) -> List[str]:
        """Dela upp text i chunks för streaming"""
        words = text.split()
        chunks = []
        current_chunk = []
        
        for word in words:
            current_chunk.append(word)
            if len(" ".join(current_chunk)) >= chunk_size:
                chunks.append(" ".join(current_chunk) + " ")
                current_chunk = []
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def cancel_stream(self, stream_id: str):
        """Avbryt en aktiv stream"""
        self.active_streams[stream_id] = False
    
    def get_active_streams(self) -> List[str]:
        """Hämta aktiva streams"""
        return [sid for sid, active in self.active_streams.items() if active]
    
    async def health_check(self) -> Dict[str, Any]:
        """Hälsokontroll för bridge-systemet"""
        status = {
            "bridge_active": True,
            "ollama_available": False,
            "openai_available": bool(os.getenv("OPENAI_API_KEY")),
            "memory_connected": self.memory is not None,
            "orchestrator_ready": self.orchestrator is not None,
            "active_streams": len(self.active_streams),
            "harmony_enabled": self.use_harmony,
            "tools_enabled": self.use_tools
        }
        
        # Test Ollama connection
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://127.0.0.1:11434/api/version")
                status["ollama_available"] = response.status_code == 200
        except:
            status["ollama_available"] = False
        
        return status


# Convenience functions för enkel integration
async def create_alice_bridge(memory_store: MemoryStore) -> AliceAgentBridge:
    """Skapa en Alice Agent Bridge med standardinställningar"""
    return AliceAgentBridge(memory_store)


async def stream_alice_response(prompt: str, memory_store: MemoryStore, 
                              **kwargs) -> AsyncGenerator[str, None]:
    """Enkel streaming function för integration med befintliga endpoints"""
    bridge = await create_alice_bridge(memory_store)
    request = AgentBridgeRequest(prompt=prompt, **kwargs)
    
    async for chunk in bridge.stream_response(request):
        if chunk.type == StreamChunkType.CHUNK:
            yield chunk.content
        elif chunk.type == StreamChunkType.TOOL:
            yield chunk.content
        elif chunk.type == StreamChunkType.ERROR:
            yield f"Fel: {chunk.content}"