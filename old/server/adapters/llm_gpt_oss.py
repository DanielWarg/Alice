#!/usr/bin/env python3
"""
🧠 GPT-OSS LLM Streaming Adapter
Real-time language model with streaming response generation
Target: ≤300ms first token, optimized for voice conversations
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, Callable, AsyncIterator
from dataclasses import dataclass
import ollama
from ollama import AsyncClient
import threading
from queue import Queue, Empty

logger = logging.getLogger(__name__)

@dataclass
class LLMConfig:
    """LLM configuration parameters"""
    model_name: str = "gpt-oss:20b"  # Available model
    base_url: str = "http://localhost:11434"  # Ollama default
    
    # Generation parameters optimized for voice
    max_tokens: int = 60  # Short responses for voice
    temperature: float = 0.3  # Slightly creative but focused
    top_p: float = 0.9
    top_k: int = 40
    
    # Performance tuning
    num_ctx: int = 2048  # Context window
    num_predict: int = 60  # Max prediction length
    
    # Voice-specific settings
    stop_sequences: list = None  # Will be set in __post_init__
    system_prompt: str = "You are Alice, a helpful AI assistant. Give concise, conversational responses suitable for voice interaction. Keep responses under 2-3 sentences."
    
    def __post_init__(self):
        if self.stop_sequences is None:
            self.stop_sequences = ["\n\n", "User:", "Human:", "Assistant:"]

@dataclass
class LLMResult:
    """LLM generation result"""
    token: str
    is_final: bool
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    time_to_first_token_ms: float
    generation_speed_tokens_per_sec: float
    full_response: str = ""  # Complete response so far

class StreamingLLM:
    """Streaming GPT-OSS LLM engine"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client: Optional[AsyncClient] = None
        self.is_initialized = False
        
        # Conversation state
        self.conversation_history = []
        self.current_response = ""
        
        # Performance tracking
        self.stats = {
            "total_requests": 0,
            "total_tokens_generated": 0,
            "avg_ttft_ms": 0.0,  # Time to first token
            "avg_tokens_per_sec": 0.0,
            "model_warm": False,
            "initialization_time_ms": 0.0
        }
        
        # Callbacks
        self.on_token: Optional[Callable[[LLMResult], None]] = None
        self.on_complete: Optional[Callable[[LLMResult], None]] = None
        
        logger.info(f"StreamingLLM initialized: {config.model_name}")
    
    async def initialize(self) -> None:
        """Initialize LLM client and warm up model"""
        start_time = time.time()
        
        try:
            # Create async Ollama client
            self.client = AsyncClient(host=self.config.base_url)
            
            # Test connection and warm up model
            logger.info(f"Warming up model: {self.config.model_name}")
            
            warmup_prompt = "Hello"
            warmup_start = time.time()
            
            response = await self.client.generate(
                model=self.config.model_name,
                prompt=warmup_prompt,
                options={
                    'num_predict': 10,
                    'temperature': 0.0,
                    'top_p': 1.0,
                    'stop': self.config.stop_sequences
                },
                stream=False  # Simple warmup
            )
            
            warmup_time = (time.time() - warmup_start) * 1000
            
            init_time = (time.time() - start_time) * 1000
            self.stats["initialization_time_ms"] = init_time
            self.stats["model_warm"] = True
            
            self.is_initialized = True
            
            logger.info(f"✅ LLM initialized in {init_time:.1f}ms (warmup: {warmup_time:.1f}ms)")
            logger.info(f"   Warmup response: '{response['response'][:50]}...'")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM: {e}")
            raise
    
    async def generate_response(self, prompt: str, session_id: str = "default") -> AsyncIterator[LLMResult]:
        """Generate streaming response to prompt"""
        if not self.is_initialized:
            raise RuntimeError("LLM not initialized")
        
        start_time = time.time()
        first_token_time = None
        total_tokens = 0
        prompt_tokens = len(prompt.split())  # Rough estimate
        self.current_response = ""
        
        try:
            # Prepare full prompt with system message and conversation history
            full_prompt = self._build_prompt(prompt)
            
            logger.info(f"🧠 Generating response for session {session_id}")
            logger.debug(f"   Prompt: '{prompt}'")
            
            # Generate streaming response
            stream = await self.client.generate(
                model=self.config.model_name,
                prompt=full_prompt,
                options={
                    'num_predict': self.config.num_predict,
                    'temperature': self.config.temperature,
                    'top_p': self.config.top_p,
                    'top_k': self.config.top_k,
                    'stop': self.config.stop_sequences,
                    'num_ctx': self.config.num_ctx
                },
                stream=True
            )
            
            async for chunk in stream:
                if chunk.get('done', False):
                    # Final chunk with metadata
                    generation_time = time.time() - start_time
                    tokens_per_sec = total_tokens / generation_time if generation_time > 0 else 0
                    
                    # Update conversation history
                    self._update_conversation_history(prompt, self.current_response)
                    
                    # Update statistics
                    self._update_stats(first_token_time, tokens_per_sec, total_tokens)
                    
                    final_result = LLMResult(
                        token="",
                        is_final=True,
                        total_tokens=total_tokens,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=total_tokens,
                        time_to_first_token_ms=first_token_time or 0,
                        generation_speed_tokens_per_sec=tokens_per_sec,
                        full_response=self.current_response
                    )
                    
                    if self.on_complete:
                        self.on_complete(final_result)
                    
                    yield final_result
                    
                    logger.info(f"✅ Response complete: {total_tokens} tokens, "
                               f"TTFT={first_token_time:.1f}ms, "
                               f"{tokens_per_sec:.1f} tokens/sec")
                    break
                
                else:
                    # Token chunk
                    token = chunk.get('response', '')
                    if token:
                        if first_token_time is None:
                            first_token_time = (time.time() - start_time) * 1000
                            logger.info(f"🎯 First token in {first_token_time:.1f}ms")
                        
                        self.current_response += token
                        total_tokens += 1
                        
                        current_time = time.time()
                        generation_time = current_time - start_time
                        tokens_per_sec = total_tokens / generation_time if generation_time > 0 else 0
                        
                        result = LLMResult(
                            token=token,
                            is_final=False,
                            total_tokens=total_tokens,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=total_tokens,
                            time_to_first_token_ms=first_token_time or 0,
                            generation_speed_tokens_per_sec=tokens_per_sec,
                            full_response=self.current_response
                        )
                        
                        if self.on_token:
                            self.on_token(result)
                        
                        yield result
                        
                        # Log first few tokens for debugging
                        if total_tokens <= 5:
                            logger.debug(f"Token {total_tokens}: '{token}' (response so far: '{self.current_response}')")
        
        except Exception as e:
            logger.error(f"❌ LLM generation error: {e}")
            raise
    
    def _build_prompt(self, user_input: str) -> str:
        """Build full prompt with system message and conversation history"""
        # Start with system prompt
        full_prompt = f"System: {self.config.system_prompt}\n\n"
        
        # Add recent conversation history (keep it short for voice)
        max_history = 4  # Last 2 exchanges
        recent_history = self.conversation_history[-max_history:] if self.conversation_history else []
        
        for entry in recent_history:
            full_prompt += f"Human: {entry['human']}\nAssistant: {entry['assistant']}\n\n"
        
        # Add current user input
        full_prompt += f"Human: {user_input}\nAssistant:"
        
        return full_prompt
    
    def _update_conversation_history(self, human_input: str, assistant_response: str) -> None:
        """Update conversation history with new exchange"""
        self.conversation_history.append({
            'human': human_input,
            'assistant': assistant_response,
            'timestamp': time.time()
        })
        
        # Keep only recent history (memory management)
        max_history = 10
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
    
    def _update_stats(self, ttft_ms: Optional[float], tokens_per_sec: float, total_tokens: int) -> None:
        """Update performance statistics"""
        self.stats["total_requests"] += 1
        self.stats["total_tokens_generated"] += total_tokens
        
        # Update average TTFT
        if ttft_ms is not None:
            requests = self.stats["total_requests"]
            current_avg_ttft = self.stats["avg_ttft_ms"]
            self.stats["avg_ttft_ms"] = (current_avg_ttft * (requests - 1) + ttft_ms) / requests
        
        # Update average tokens per second
        requests = self.stats["total_requests"]
        current_avg_tps = self.stats["avg_tokens_per_sec"]
        self.stats["avg_tokens_per_sec"] = (current_avg_tps * (requests - 1) + tokens_per_sec) / requests
    
    def clear_conversation_history(self) -> None:
        """Clear conversation history for new session"""
        self.conversation_history = []
        logger.info("🧹 Conversation history cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            **self.stats,
            "conversation_turns": len(self.conversation_history),
            "is_initialized": self.is_initialized
        }

# Factory function
def create_streaming_llm(
    on_token: Optional[Callable[[LLMResult], None]] = None,
    on_complete: Optional[Callable[[LLMResult], None]] = None,
    config: Optional[LLMConfig] = None
) -> StreamingLLM:
    """Create and configure streaming LLM"""
    if config is None:
        config = LLMConfig()
    
    llm = StreamingLLM(config)
    llm.on_token = on_token
    llm.on_complete = on_complete
    
    return llm

# Test function
async def test_streaming_llm():
    """Test streaming LLM with sample prompts"""
    logger.info("🧪 Testing Streaming LLM...")
    
    tokens_received = []
    
    def on_token(result: LLMResult):
        tokens_received.append(result.token)
        logger.info(f"Token: '{result.token}' (TTFT={result.time_to_first_token_ms:.1f}ms, "
                   f"{result.generation_speed_tokens_per_sec:.1f} tokens/sec)")
    
    def on_complete(result: LLMResult):
        logger.info(f"Complete: '{result.full_response}' "
                   f"({result.total_tokens} tokens, TTFT={result.time_to_first_token_ms:.1f}ms)")
    
    # Create LLM
    config = LLMConfig(max_tokens=40)  # Short test response
    llm = create_streaming_llm(on_token, on_complete, config)
    
    try:
        # Initialize
        await llm.initialize()
        
        # Test prompts
        test_prompts = [
            "Hello, how are you?",
            "What is the weather like?",
            "Tell me a short joke"
        ]
        
        for prompt in test_prompts:
            logger.info(f"\n🔸 Testing prompt: '{prompt}'")
            tokens_received.clear()
            
            async for result in llm.generate_response(prompt, "test_session"):
                if result.is_final:
                    break
            
            logger.info(f"   Received {len(tokens_received)} tokens")
        
        # Print final stats
        stats = llm.get_stats()
        logger.info(f"\n📊 Final Stats:")
        logger.info(f"   Total requests: {stats['total_requests']}")
        logger.info(f"   Total tokens: {stats['total_tokens_generated']}")
        logger.info(f"   Avg TTFT: {stats['avg_ttft_ms']:.1f}ms")
        logger.info(f"   Avg tokens/sec: {stats['avg_tokens_per_sec']:.1f}")
        
    except Exception as e:
        logger.error(f"❌ Test error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(test_streaming_llm())