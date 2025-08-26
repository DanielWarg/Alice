#!/usr/bin/env python3
"""
🧠 LLM Token Streaming Manager for Alice Voice Gateway
GPT-5 Day 2: Real-time token streaming with OpenAI/Anthropic/Local providers
"""
import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, AsyncGenerator, Any
import openai

# Optional import for Anthropic
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    anthropic = None
    HAS_ANTHROPIC = False

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """Supported LLM providers for streaming"""
    OPENAI_GPT4 = "openai_gpt4"
    OPENAI_GPT4O = "openai_gpt4o"  
    ANTHROPIC_CLAUDE = "anthropic_claude"
    LOCAL_LLAMA = "local_llama"

@dataclass
class LLMConfig:
    """Configuration for LLM streaming"""
    provider: LLMProvider = LLMProvider.OPENAI_GPT4O
    model_name: str = "gpt-4o"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    
    # Streaming parameters
    stream_chunk_size: int = 10  # tokens per chunk
    stream_delay_ms: int = 50    # delay between chunks
    
    # Alice-specific parameters
    system_prompt: str = field(default_factory=lambda: """Du är Alice, en svensk AI-assistent med personlighet. 
Du svarar naturligt och engagerat på svenska. Håll svar kortfattade för röstkonversation.""")
    
    # Performance targets (GPT-5 Day 2)
    first_token_target_ms: int = 200    # Time to first token
    tokens_per_second_target: int = 50  # Token generation rate

@dataclass
class LLMToken:
    """Single LLM token with metadata"""
    text: str
    token_id: Optional[int] = None
    logprob: Optional[float] = None
    timestamp: float = field(default_factory=lambda: time.time() * 1000)
    is_final: bool = False
    provider: Optional[LLMProvider] = None

@dataclass  
class LLMResponse:
    """Complete or partial LLM response"""
    text: str
    tokens: List[LLMToken] = field(default_factory=list)
    is_complete: bool = False
    session_id: str = ""
    provider: Optional[LLMProvider] = None
    
    # Performance metrics
    first_token_latency_ms: Optional[float] = None
    total_tokens: int = 0
    tokens_per_second: float = 0.0
    
    # Alice context
    conversation_id: Optional[str] = None
    user_utterance: str = ""

class LLMStreamBase(ABC):
    """Base class for LLM streaming implementations"""
    
    def __init__(self, config: LLMConfig, session_id: str):
        self.config = config
        self.session_id = session_id
        self.conversation_history: List[Dict[str, str]] = []
        
        # Callbacks for streaming events
        self.on_token: Optional[Callable[[LLMToken], None]] = None
        self.on_response_start: Optional[Callable[[str], None]] = None  
        self.on_response_complete: Optional[Callable[[LLMResponse], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
        # Performance tracking
        self.start_time: Optional[float] = None
        self.first_token_time: Optional[float] = None
        self.token_count = 0
        
    @abstractmethod
    async def generate_streaming_response(self, user_input: str) -> AsyncGenerator[LLMToken, None]:
        """Generate streaming response tokens"""
        pass
        
    async def add_to_conversation(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
        # Keep conversation history manageable (last 10 exchanges)
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def _build_messages(self, user_input: str) -> List[Dict[str, str]]:
        """Build message list for API call"""
        messages = [{"role": "system", "content": self.config.system_prompt}]
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": user_input})
        return messages

class OpenAILLMStream(LLMStreamBase):
    """OpenAI GPT streaming implementation"""
    
    def __init__(self, config: LLMConfig, session_id: str):
        super().__init__(config, session_id)
        self.client = openai.AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
        
    async def generate_streaming_response(self, user_input: str) -> AsyncGenerator[LLMToken, None]:
        """Generate streaming response using OpenAI API"""
        try:
            self.start_time = time.time() * 1000
            self.token_count = 0
            
            if self.on_response_start:
                self.on_response_start(user_input)
            
            messages = self._build_messages(user_input)
            
            stream = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stream=True
            )
            
            accumulated_text = ""
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    accumulated_text += content
                    
                    # Track first token timing
                    if self.first_token_time is None:
                        self.first_token_time = time.time() * 1000
                        first_token_latency = self.first_token_time - self.start_time
                        logger.debug(f"🚀 First token: {first_token_latency:.0f}ms (target: <200ms)")
                    
                    token = LLMToken(
                        text=content,
                        provider=self.config.provider,
                        is_final=False
                    )
                    
                    self.token_count += 1
                    
                    if self.on_token:
                        self.on_token(token)
                    
                    yield token
            
            # Final token
            final_token = LLMToken(
                text="",
                provider=self.config.provider, 
                is_final=True
            )
            yield final_token
            
            # Add to conversation history
            await self.add_to_conversation("user", user_input)
            await self.add_to_conversation("assistant", accumulated_text)
            
            # Calculate performance metrics
            total_time = time.time() * 1000 - self.start_time
            tokens_per_second = (self.token_count / total_time) * 1000 if total_time > 0 else 0
            
            response = LLMResponse(
                text=accumulated_text,
                is_complete=True,
                session_id=self.session_id,
                provider=self.config.provider,
                first_token_latency_ms=self.first_token_time - self.start_time if self.first_token_time else None,
                total_tokens=self.token_count,
                tokens_per_second=tokens_per_second,
                user_utterance=user_input
            )
            
            if self.on_response_complete:
                self.on_response_complete(response)
                
        except Exception as e:
            logger.error(f"❌ OpenAI streaming error: {e}")
            if self.on_error:
                self.on_error(e)
            raise

class AnthropicLLMStream(LLMStreamBase):
    """Anthropic Claude streaming implementation"""
    
    def __init__(self, config: LLMConfig, session_id: str):
        super().__init__(config, session_id)
        if not HAS_ANTHROPIC:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        self.client = anthropic.AsyncAnthropic(
            api_key=config.api_key
        )
        
    async def generate_streaming_response(self, user_input: str) -> AsyncGenerator[LLMToken, None]:
        """Generate streaming response using Anthropic API"""
        try:
            self.start_time = time.time() * 1000
            self.token_count = 0
            
            if self.on_response_start:
                self.on_response_start(user_input)
            
            # Build conversation for Claude (no system role in messages)
            messages = []
            for msg in self.conversation_history:
                if msg["role"] != "system":
                    messages.append(msg)
            messages.append({"role": "user", "content": user_input})
            
            stream = await self.client.messages.create(
                model="claude-3-sonnet-20240229",  # Default Claude model
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=self.config.system_prompt,
                messages=messages,
                stream=True
            )
            
            accumulated_text = ""
            
            async for chunk in stream:
                if chunk.type == "content_block_delta" and hasattr(chunk.delta, 'text'):
                    content = chunk.delta.text
                    accumulated_text += content
                    
                    # Track first token timing
                    if self.first_token_time is None:
                        self.first_token_time = time.time() * 1000
                        first_token_latency = self.first_token_time - self.start_time
                        logger.debug(f"🚀 First token: {first_token_latency:.0f}ms (target: <200ms)")
                    
                    token = LLMToken(
                        text=content,
                        provider=self.config.provider,
                        is_final=False
                    )
                    
                    self.token_count += 1
                    
                    if self.on_token:
                        self.on_token(token)
                    
                    yield token
            
            # Final token
            final_token = LLMToken(
                text="",
                provider=self.config.provider,
                is_final=True
            )
            yield final_token
            
            # Add to conversation history
            await self.add_to_conversation("user", user_input)
            await self.add_to_conversation("assistant", accumulated_text)
            
            # Calculate performance metrics
            total_time = time.time() * 1000 - self.start_time
            tokens_per_second = (self.token_count / total_time) * 1000 if total_time > 0 else 0
            
            response = LLMResponse(
                text=accumulated_text,
                is_complete=True,
                session_id=self.session_id,
                provider=self.config.provider,
                first_token_latency_ms=self.first_token_time - self.start_time if self.first_token_time else None,
                total_tokens=self.token_count,
                tokens_per_second=tokens_per_second,
                user_utterance=user_input
            )
            
            if self.on_response_complete:
                self.on_response_complete(response)
                
        except Exception as e:
            logger.error(f"❌ Anthropic streaming error: {e}")
            if self.on_error:
                self.on_error(e)
            raise

class LLMStreamManager:
    """Manages LLM streaming sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, LLMStreamBase] = {}
        self.config = self._load_config()
        
    def _load_config(self) -> LLMConfig:
        """Load LLM configuration from environment"""
        import os
        
        provider_name = os.getenv("LLM_PROVIDER", "openai_gpt4o").upper()
        try:
            provider = LLMProvider[provider_name]
        except KeyError:
            logger.warning(f"Unknown LLM provider: {provider_name}, using OpenAI GPT-4o")
            provider = LLMProvider.OPENAI_GPT4O
            
        return LLMConfig(
            provider=provider,
            api_key=os.getenv("OPENAI_API_KEY") if provider.name.startswith("OPENAI") else os.getenv("ANTHROPIC_API_KEY"),
            model_name=os.getenv("LLM_MODEL", "gpt-4o"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000"))
        )
    
    async def create_session(self, session_id: str) -> LLMStreamBase:
        """Create new LLM streaming session"""
        if session_id in self.sessions:
            logger.info(f"🔄 Reusing existing LLM session: {session_id}")
            return self.sessions[session_id]
            
        if self.config.provider in [LLMProvider.OPENAI_GPT4, LLMProvider.OPENAI_GPT4O]:
            llm_stream = OpenAILLMStream(self.config, session_id)
        elif self.config.provider == LLMProvider.ANTHROPIC_CLAUDE:
            if not HAS_ANTHROPIC:
                logger.warning("Anthropic not available, falling back to OpenAI")
                llm_stream = OpenAILLMStream(self.config, session_id)
            else:
                llm_stream = AnthropicLLMStream(self.config, session_id)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.provider}")
        
        self.sessions[session_id] = llm_stream
        logger.info(f"✅ LLM session created: {session_id} (provider: {self.config.provider.value})")
        return llm_stream
    
    async def remove_session(self, session_id: str):
        """Remove LLM streaming session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"🔌 LLM session removed: {session_id}")
    
    def get_session(self, session_id: str) -> Optional[LLMStreamBase]:
        """Get existing LLM session"""
        return self.sessions.get(session_id)
    
    def get_session_count(self) -> int:
        """Get number of active LLM sessions"""
        return len(self.sessions)

# Global LLM manager instance
_llm_manager = LLMStreamManager()

def get_llm_manager() -> LLMStreamManager:
    """Get global LLM stream manager"""
    return _llm_manager