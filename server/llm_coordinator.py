"""
LLM Coordinator - Main interface for model management and routing
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional

from llm import ModelManager, OllamaAdapter, OpenAIAdapter, harmonyWrap
from llm.harmony import create_system_prompt, create_developer_prompt, extract_harmony_sections
from agent import routeIntent, classifyIntent, IntentClassification
from agent.tools import extractToolCalls, executeToolCall

logger = logging.getLogger("alice.llm_coordinator")

class LLMCoordinator:
    """
    Central coordinator for LLM operations with hybrid routing.
    Manages model selection, tool execution, and response formatting.
    """
    
    def __init__(self):
        self.model_manager = None
        self._initialize_models()
        
        # Cache for frequently used prompts
        self.system_prompt = create_system_prompt()
        self.developer_prompt = create_developer_prompt()
        
        logger.info("LLMCoordinator initialized")
    
    def _initialize_models(self):
        """Initialize primary and fallback models"""
        try:
            # Primary model (Ollama)
            ollama_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
            ollama_model = os.getenv("LLM_MODEL", "gpt-oss:20b")
            primary = OllamaAdapter(base_url=ollama_url, model=ollama_model)
            
            # Fallback model (OpenAI)
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                logger.warning("No OpenAI API key found - using mock fallback")
                fallback = MockOpenAIAdapter()
            else:
                fallback_model = os.getenv("FALLBACK_MODEL", "gpt-4o-mini")
                fallback = OpenAIAdapter(api_key=openai_api_key, model=fallback_model)
            
            self.model_manager = ModelManager(primary=primary, fallback=fallback)
            
        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            # Create mock manager for development
            self.model_manager = MockModelManager()
    
    async def process_request(
        self, 
        user_input: str, 
        history: Optional[List[Dict[str, str]]] = None,
        force_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process user request with intelligent routing.
        
        Args:
            user_input: User's input text
            history: Conversation history
            force_path: Force specific path ("FAST" or "DEEP")
            
        Returns:
            Dict with response and metadata
        """
        try:
            # Classify intent
            classification = classifyIntent(user_input)
            
            # Determine routing path
            if force_path:
                path = force_path
            else:
                route = routeIntent(classification)
                path = route.value
            
            logger.info(f"Processing request via {path} path: {classification.intent}")
            
            # Build messages
            messages = harmonyWrap(
                system=self.system_prompt,
                developer=self.developer_prompt,
                user=user_input,
                history=history
            )
            
            # Get model response
            start_time = asyncio.get_event_loop().time()
            response = await self.model_manager.ask(messages)
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Extract structured sections
            sections = extract_harmony_sections(response.text)
            
            # Handle tool calls if present
            tool_results = []
            if response.tool_calls:
                tool_results = await self._execute_tools(response.tool_calls)
            
            # Extract tool calls from commentary if Harmony format
            elif sections.get("commentary"):
                harmony_tools = extractToolCalls(sections["commentary"])
                if harmony_tools:
                    tool_results = await self._execute_tools(harmony_tools)
            
            # If we executed tools, get final response
            final_text = sections.get("final", response.text)
            if tool_results:
                # Re-query with tool results
                tool_responses = [{"tool": tr.tool, "content": tr.content} for tr in tool_results]
                
                final_messages = harmonyWrap(
                    system=self.system_prompt,
                    user=user_input,
                    history=history,
                    tool_responses=tool_responses
                )
                
                final_response = await self.model_manager.ask(final_messages)
                final_sections = extract_harmony_sections(final_response.text)
                final_text = final_sections.get("final", final_response.text)
            
            return {
                "response": final_text,
                "provider": response.provider,
                "path": path,
                "classification": {
                    "intent": classification.intent,
                    "privacy": classification.privacy.value,
                    "need_tools": classification.need_tools,
                    "reasoning": classification.reasoning
                },
                "tools_used": [tr.tool for tr in tool_results],
                "sections": sections,
                "timing": {
                    "total_ms": processing_time,
                    "ttft_ms": response.tftt_ms
                }
            }
            
        except Exception as e:
            logger.error(f"Request processing failed: {e}")
            return {
                "response": f"Ursäkta, jag stötte på ett fel: {str(e)}",
                "provider": "error",
                "path": "ERROR",
                "error": str(e)
            }
    
    async def _execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[Any]:
        """Execute tool calls and return results"""
        results = []
        
        for tool_call in tool_calls:
            try:
                result = await executeToolCall(tool_call)
                results.append(result)
                logger.debug(f"Tool {result.tool} executed: {'success' if result.success else 'failed'}")
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                results.append({
                    "tool": tool_call.get("function", {}).get("name", "unknown"),
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get coordinator status for monitoring"""
        status = {
            "coordinator": "active",
            "models": self.model_manager.get_status() if self.model_manager else {"error": "not initialized"}
        }
        return status
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components"""
        if not self.model_manager:
            return {"status": "error", "message": "Model manager not initialized"}
        
        try:
            # Test simple request
            test_response = await self.process_request("Hej Alice")
            
            return {
                "status": "healthy",
                "test_response_length": len(test_response.get("response", "")),
                "provider": test_response.get("provider", "unknown"),
                "models": self.model_manager.get_status()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": str(e),
                "models": self.model_manager.get_status() if self.model_manager else None
            }

# Mock implementations for development/testing
class MockOpenAIAdapter:
    """Mock OpenAI adapter for development without API key"""
    
    def __init__(self):
        self.name = "mock-openai"
    
    async def health(self):
        from llm.manager import HealthStatus
        return HealthStatus(ok=False, error="Mock fallback - no API key")
    
    async def chat(self, messages, tools=None):
        from llm.manager import LLMResponse
        return LLMResponse(
            text="Mock OpenAI response - API key not configured",
            provider="mock-openai"
        )

class MockModelManager:
    """Mock model manager for development"""
    
    def __init__(self):
        self.name = "mock-manager"
    
    async def ask(self, messages, tools=None):
        from llm.manager import LLMResponse
        return LLMResponse(
            text="Mock response - models not properly configured",
            provider="mock"
        )
    
    def get_status(self):
        return {"status": "mock", "message": "Development mode - models not configured"}