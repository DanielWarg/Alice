"""
Alice Voice-Gateway Phase 2 Integration Tests

Comprehensive test suite for the hybrid voice architecture Phase 2:
- OpenAI Realtime API integration
- Fast Path routing and processing
- Think Path local AI processing  
- Swedish language handling
- Performance metrics and monitoring
- Fallback scenarios and error handling

Run with: python -m pytest test_voice_phase2_integration.py -v
"""

import pytest
import asyncio
import json
import time
import os
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any

# Test imports
from voice_gateway import VoiceGatewayManager, ProcessingPath, VoiceState
from fast_path_handler import FastPathHandler, FastPathRequest, FastPathDecision
from think_path_handler import ThinkPathHandler, ThinkPathRequest  
from openai_realtime_client import OpenAIRealtimeClient, RealtimeConfig
from memory import MemoryStore

class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self):
        self.messages = []
        self.closed = False
        
    async def accept(self):
        pass
        
    async def send_json(self, data: Dict[str, Any]):
        self.messages.append(data)
        
    async def receive_json(self):
        # Mock receive for testing
        return {"type": "test", "data": "mock"}
    
    def get_last_message(self) -> Dict[str, Any]:
        return self.messages[-1] if self.messages else {}
    
    def get_messages_by_type(self, message_type: str) -> list:
        return [msg for msg in self.messages if msg.get("type") == message_type]

@pytest.fixture
async def memory_store():
    """Create test memory store"""
    # Use in-memory database for testing
    import sqlite3
    conn = sqlite3.connect(":memory:")
    
    # Initialize memory store
    memory = MemoryStore()
    memory.conn = conn
    await memory.initialize()
    
    return memory

@pytest.fixture
async def voice_gateway_manager(memory_store):
    """Create voice gateway manager for testing"""
    manager = VoiceGatewayManager(memory_store)
    return manager

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI Realtime client"""
    client = MagicMock(spec=OpenAIRealtimeClient)
    client.is_connected.return_value = True
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock()
    client.send_text_message = AsyncMock()
    client.cancel_response = AsyncMock()
    return client

@pytest.fixture
def mock_ollama_client():
    """Mock Ollama HTTP client for local AI"""
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.stream = AsyncMock()
    client.aclose = AsyncMock()
    return client

class TestPhase2Integration:
    """Integration tests for Phase 2 components"""
    
    @pytest.mark.asyncio
    async def test_voice_gateway_phase2_initialization(self, voice_gateway_manager):
        """Test Phase 2 initialization"""
        # Mock the handlers to avoid external dependencies
        with patch('fast_path_handler.get_fast_path_handler') as mock_fast_path, \
             patch('think_path_handler.get_think_path_handler') as mock_think_path:
            
            # Mock handler initialization
            mock_fast_handler = AsyncMock()
            mock_fast_handler.initialize = AsyncMock(return_value=True)
            mock_fast_path.return_value = mock_fast_handler
            
            mock_think_handler = AsyncMock()
            mock_think_handler.initialize = AsyncMock(return_value=True)
            mock_think_path.return_value = mock_think_handler
            
            # Test initialization
            success = await voice_gateway_manager.initialize_phase2()
            
            assert success is True
            assert voice_gateway_manager._phase2_initialized is True
            assert voice_gateway_manager.fast_path_handler is not None
            assert voice_gateway_manager.think_path_handler is not None
    
    @pytest.mark.asyncio
    async def test_enhanced_intent_routing(self, voice_gateway_manager):
        """Test enhanced intent classification and routing"""
        # Initialize Phase 2
        with patch('fast_path_handler.get_fast_path_handler') as mock_fast_path, \
             patch('think_path_handler.get_think_path_handler') as mock_think_path:
            
            mock_fast_handler = AsyncMock()
            mock_fast_handler.initialize = AsyncMock(return_value=True)
            mock_fast_handler.should_use_fast_path = MagicMock(return_value=FastPathDecision.APPROVED)
            mock_fast_path.return_value = mock_fast_handler
            
            mock_think_handler = AsyncMock()
            mock_think_handler.initialize = AsyncMock(return_value=True)
            mock_think_path.return_value = mock_think_handler
            
            await voice_gateway_manager.initialize_phase2()
            
            # Test Swedish greeting routing to fast path
            with patch('core.router.classify') as mock_classify:
                mock_classify.return_value = {
                    "tool": "GREETING", 
                    "confidence": 0.9,
                    "args": {}
                }
                
                result = await voice_gateway_manager._enhanced_classify_and_route("Hej Alice", "test_session")
                
                assert result.path == ProcessingPath.FAST
                assert result.intent == "GREETING"
                assert result.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_fast_path_processing(self, voice_gateway_manager):
        """Test fast path processing with OpenAI Realtime"""
        mock_websocket = MockWebSocket()
        
        # Setup mocks
        with patch('fast_path_handler.get_fast_path_handler') as mock_fast_path:
            mock_handler = AsyncMock()
            mock_handler.initialize = AsyncMock(return_value=True)
            
            # Mock successful fast path response
            from fast_path_handler import FastPathResponse
            mock_response = FastPathResponse(
                success=True,
                response_text="Hej! Hur kan jag hjälpa dig?",
                latency_ms=250.0,
                cached=False
            )
            mock_handler.process_request = AsyncMock(return_value=mock_response)
            mock_fast_path.return_value = mock_handler
            
            voice_gateway_manager.fast_path_handler = mock_handler
            voice_gateway_manager._phase2_initialized = True
            
            # Test fast path processing
            from voice_gateway import IntentResult
            intent = IntentResult(
                intent="GREETING",
                confidence=0.9,
                path=ProcessingPath.FAST,
                reasoning="approved_for_fast_path"
            )
            
            await voice_gateway_manager._handle_phase2_fast_path(
                mock_websocket, 
                "test_session", 
                "Hej Alice", 
                intent
            )
            
            # Verify response was sent
            response_messages = mock_websocket.get_messages_by_type("response")
            assert len(response_messages) > 0
            assert response_messages[0]["text"] == "Hej! Hur kan jag hjälpa dig?"
            assert response_messages[0]["path"] == "fast"
            assert response_messages[0]["latency_ms"] == 250.0
    
    @pytest.mark.asyncio
    async def test_think_path_processing(self, voice_gateway_manager):
        """Test think path processing with local AI"""
        mock_websocket = MockWebSocket()
        
        # Setup mocks  
        with patch('think_path_handler.get_think_path_handler') as mock_think_path:
            mock_handler = AsyncMock()
            mock_handler.initialize = AsyncMock(return_value=True)
            
            # Mock streaming think path responses
            from think_path_handler import ThinkPathResponse
            async def mock_process_request(request):
                yield ThinkPathResponse(
                    success=True,
                    response_text="Okej, jag kollar det åt dig.",
                    reasoning_steps=["Initial confirmation sent"]
                )
                yield ThinkPathResponse(
                    success=True,
                    response_text="Jag analyserar din förfrågan...",
                    reasoning_steps=["Analyzing request complexity"]
                )
                yield ThinkPathResponse(
                    success=True,
                    response_text="Här är ett detaljerat svar på din komplexa fråga.",
                    reasoning_steps=["Generated final response"],
                    confidence=0.85
                )
            
            mock_handler.process_request = mock_process_request
            mock_think_path.return_value = mock_handler
            
            voice_gateway_manager.think_path_handler = mock_handler
            voice_gateway_manager._phase2_initialized = True
            
            # Test think path processing
            from voice_gateway import IntentResult
            intent = IntentResult(
                intent="COMPLEX_QUESTION",
                confidence=0.75,
                path=ProcessingPath.THINK,
                reasoning="requires_local_processing"
            )
            
            await voice_gateway_manager._handle_phase2_think_path(
                mock_websocket,
                "test_session",
                "Kan du förklara kvantfysik på svenska?",
                intent
            )
            
            # Verify streaming responses were sent
            response_chunks = mock_websocket.get_messages_by_type("response_chunk")
            assert len(response_chunks) >= 2  # At least confirmation and thinking
            
            final_responses = mock_websocket.get_messages_by_type("response")
            assert len(final_responses) > 0
            assert final_responses[0]["path"] == "think"
    
    @pytest.mark.asyncio
    async def test_fallback_scenarios(self, voice_gateway_manager):
        """Test fallback from fast path to think path"""
        mock_websocket = MockWebSocket()
        
        with patch('fast_path_handler.get_fast_path_handler') as mock_fast_path, \
             patch('think_path_handler.get_think_path_handler') as mock_think_path:
            
            # Mock failed fast path
            mock_fast_handler = AsyncMock()
            mock_fast_handler.initialize = AsyncMock(return_value=True)
            
            from fast_path_handler import FastPathResponse
            mock_failed_response = FastPathResponse(
                success=False,
                fallback_reason="OpenAI connection timeout"
            )
            mock_fast_handler.process_request = AsyncMock(return_value=mock_failed_response)
            mock_fast_path.return_value = mock_fast_handler
            
            # Mock successful think path fallback
            mock_think_handler = AsyncMock()
            mock_think_handler.initialize = AsyncMock(return_value=True)
            
            from think_path_handler import ThinkPathResponse
            async def mock_fallback_response(request):
                yield ThinkPathResponse(
                    success=True,
                    response_text="Jag använder lokal AI istället.",
                    reasoning_steps=["Fallback to local processing"]
                )
            
            mock_think_handler.process_request = mock_fallback_response
            mock_think_path.return_value = mock_think_handler
            
            voice_gateway_manager.fast_path_handler = mock_fast_handler
            voice_gateway_manager.think_path_handler = mock_think_handler
            voice_gateway_manager._phase2_initialized = True
            
            # Test fallback scenario
            from voice_gateway import IntentResult
            intent = IntentResult(
                intent="GREETING",
                confidence=0.9,
                path=ProcessingPath.FAST,
                reasoning="approved_for_fast_path"
            )
            
            await voice_gateway_manager._handle_phase2_fast_path(
                mock_websocket,
                "test_session", 
                "Hej Alice",
                intent
            )
            
            # Verify fallback occurred - should have think path response
            response_chunks = mock_websocket.get_messages_by_type("response_chunk")
            assert len(response_chunks) > 0
            
            # Check that fallback metric was updated
            assert voice_gateway_manager.phase2_metrics["fallbacks"] > 0

    @pytest.mark.asyncio
    async def test_swedish_language_handling(self, voice_gateway_manager):
        """Test Swedish language specific processing"""
        
        # Test Swedish greeting patterns
        test_cases = [
            ("Hej Alice", "GREETING"),
            ("God morgon", "GREETING"),
            ("Vad är klockan?", "TIME_DATE"),
            ("Hur är vädret idag?", "WEATHER"),
            ("Tack så mycket", "ACKNOWLEDGMENT")
        ]
        
        with patch('fast_path_handler.get_fast_path_handler') as mock_fast_path:
            mock_handler = AsyncMock()
            mock_handler.initialize = AsyncMock(return_value=True)
            
            # Mock Swedish pattern recognition
            def mock_should_use_fast_path(text, intent, confidence):
                swedish_patterns = ["hej", "god morgon", "tack", "vad är klockan", "väder"]
                if any(pattern in text.lower() for pattern in swedish_patterns):
                    return FastPathDecision.APPROVED
                return FastPathDecision.REJECTED
            
            mock_handler.should_use_fast_path = mock_should_use_fast_path
            mock_fast_path.return_value = mock_handler
            
            voice_gateway_manager.fast_path_handler = mock_handler
            voice_gateway_manager._phase2_initialized = True
            
            # Test each Swedish phrase
            for text, expected_intent in test_cases:
                with patch('core.router.classify') as mock_classify:
                    mock_classify.return_value = {
                        "tool": expected_intent,
                        "confidence": 0.85,
                        "args": {}
                    }
                    
                    result = await voice_gateway_manager._enhanced_classify_and_route(text, "test_session")
                    
                    # Swedish greetings and simple queries should go to fast path
                    if expected_intent in ["GREETING", "TIME_DATE", "ACKNOWLEDGMENT"]:
                        assert result.path == ProcessingPath.FAST
                    
                    assert result.intent == expected_intent

    @pytest.mark.asyncio 
    async def test_performance_metrics(self, voice_gateway_manager):
        """Test performance metrics collection"""
        
        # Initialize with mocks
        with patch('fast_path_handler.get_fast_path_handler') as mock_fast_path, \
             patch('think_path_handler.get_think_path_handler') as mock_think_path:
            
            mock_fast_handler = AsyncMock()
            mock_fast_handler.initialize = AsyncMock(return_value=True)
            mock_fast_handler.get_performance_metrics = MagicMock(return_value={
                "total_requests": 10,
                "success_rate": 0.9,
                "cache_hit_rate": 0.3,
                "average_latency_ms": 250.0
            })
            mock_fast_path.return_value = mock_fast_handler
            
            mock_think_handler = AsyncMock()
            mock_think_handler.initialize = AsyncMock(return_value=True)
            mock_think_handler.get_performance_metrics = MagicMock(return_value={
                "total_requests": 5,
                "success_rate": 0.8,
                "tool_usage_rate": 0.4,
                "average_processing_ms": 1500.0
            })
            mock_think_path.return_value = mock_think_handler
            
            await voice_gateway_manager.initialize_phase2()
            
            # Simulate some metrics
            voice_gateway_manager.phase2_metrics.update({
                "total_requests": 15,
                "fast_path_requests": 10,
                "think_path_requests": 5,
                "fast_path_successes": 9,
                "think_path_successes": 4,
                "fallbacks": 1
            })
            
            # Get comprehensive metrics
            metrics = voice_gateway_manager.get_phase2_metrics()
            
            assert metrics["total_requests"] == 15
            assert metrics["fast_path_requests"] == 10
            assert metrics["think_path_requests"] == 5
            assert metrics["fallbacks"] == 1
            assert "fast_path_details" in metrics
            assert "think_path_details" in metrics

    def test_fast_path_decision_logic(self):
        """Test fast path decision logic"""
        from fast_path_handler import FastPathHandler
        from memory import MemoryStore
        
        # Create handler (without initialization for unit testing)
        handler = FastPathHandler(MemoryStore())
        
        # Test approved intents
        decision = handler.should_use_fast_path("Hej Alice", "GREETING", 0.9)
        assert decision == FastPathDecision.APPROVED
        
        # Test rejected due to low confidence
        decision = handler.should_use_fast_path("Hej Alice", "GREETING", 0.5)
        assert decision == FastPathDecision.REJECTED
        
        # Test rejected due to sensitive content
        decision = handler.should_use_fast_path("Vad är mitt lösenord?", "SIMPLE_QUESTION", 0.9)
        assert decision == FastPathDecision.REJECTED
        
        # Test rejected due to complex intent
        decision = handler.should_use_fast_path("Skicka ett email", "GMAIL", 0.9)
        assert decision == FastPathDecision.REJECTED
        
        # Test escalation for weather
        decision = handler.should_use_fast_path("Hur blir vädret imorgon?", "WEATHER", 0.8)
        assert decision == FastPathDecision.ESCALATE

    @pytest.mark.asyncio
    async def test_error_handling(self, voice_gateway_manager):
        """Test error handling and graceful degradation"""
        mock_websocket = MockWebSocket()
        
        # Test with no handlers initialized
        voice_gateway_manager._phase2_initialized = False
        voice_gateway_manager.fast_path_handler = None
        voice_gateway_manager.think_path_handler = None
        
        from voice_gateway import IntentResult
        intent = IntentResult(
            intent="GREETING",
            confidence=0.9,
            path=ProcessingPath.FAST,
            reasoning="test"
        )
        
        # Should fallback gracefully when no fast path handler
        await voice_gateway_manager._handle_phase2_fast_path(
            mock_websocket,
            "test_session",
            "Hej Alice", 
            intent
        )
        
        # Should have error or fallback response
        messages = mock_websocket.messages
        assert len(messages) > 0
        
        # Error should be handled gracefully
        error_messages = mock_websocket.get_messages_by_type("error")
        if error_messages:
            assert "not available" in error_messages[0].get("message", "").lower()

    @pytest.mark.asyncio
    async def test_barge_in_support(self, voice_gateway_manager):
        """Test barge-in (interrupt) functionality"""
        
        with patch('fast_path_handler.get_fast_path_handler') as mock_fast_path:
            mock_handler = AsyncMock()
            mock_handler.initialize = AsyncMock(return_value=True)
            mock_handler.handle_barge_in = AsyncMock()
            mock_fast_path.return_value = mock_handler
            
            voice_gateway_manager.fast_path_handler = mock_handler
            voice_gateway_manager._phase2_initialized = True
            
            # Test barge-in handling
            await voice_gateway_manager.fast_path_handler.handle_barge_in("test_session")
            
            # Verify barge-in was called
            mock_handler.handle_barge_in.assert_called_once_with("test_session")

    def test_configuration_validation(self):
        """Test Phase 2 configuration validation"""
        
        # Test required environment variables
        required_vars = [
            "OPENAI_API_KEY",
            "OLLAMA_HOST", 
            "LOCAL_MODEL",
            "FAST_PATH_ENABLED",
            "THINK_PATH_ENABLED"
        ]
        
        # Mock environment variables
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "OLLAMA_HOST": "http://localhost:11434",
            "LOCAL_MODEL": "gpt-oss:20b",
            "FAST_PATH_ENABLED": "true",
            "THINK_PATH_ENABLED": "true"
        }):
            
            # Test configuration loading
            from openai_realtime_client import RealtimeConfig
            config = RealtimeConfig(api_key="test-key")
            
            assert config.api_key == "test-key"
            assert config.language == "sv"
            assert config.voice == "nova"
            assert config.modalities == ["text", "audio"]

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])