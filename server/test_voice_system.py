#!/usr/bin/env python3
"""
Comprehensive Voice System Testing Suite
Tests all components before live deployment
"""

import asyncio
import json
import os
import sys
import time
import websockets
from pathlib import Path

# Add server to path
sys.path.insert(0, str(Path(__file__).parent))

import pytest
import httpx
from fastapi.testclient import TestClient

def test_imports():
    """Test all voice system imports work correctly"""
    print("🧪 Testing voice system imports...")
    
    try:
        # Test core imports
        from voice_stream import VoiceStreamManager, get_voice_manager
        from memory import MemoryStore
        print("✅ Core voice_stream imports OK")
        
        # Test FastAPI app imports with voice
        from app import app
        print("✅ FastAPI app with voice endpoint imports OK")
        
        # Test WebSocket endpoint exists
        routes = [route.path for route in app.routes]
        assert "/ws/voice/{session_id}" in routes, "Voice WebSocket endpoint missing"
        print("✅ Voice WebSocket endpoint registered")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_voice_manager_creation():
    """Test VoiceStreamManager can be created with MemoryStore"""
    print("\n🧪 Testing VoiceStreamManager creation...")
    
    try:
        from voice_stream import VoiceStreamManager
        from memory import MemoryStore
        
        # Create test memory store
        test_db_path = os.path.join(os.path.dirname(__file__), "test_voice.db")
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        memory = MemoryStore(test_db_path)
        voice_manager = VoiceStreamManager(memory)
        
        assert voice_manager.memory == memory
        assert voice_manager.active_sessions == {}
        assert voice_manager.api_client is not None
        
        print("✅ VoiceStreamManager created successfully")
        
        # Cleanup
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        return True
        
    except Exception as e:
        print(f"❌ VoiceStreamManager creation failed: {e}")
        return False

def test_nlu_classification_fast():
    """Test fast intent classification for voice commands"""
    print("\n🧪 Testing fast NLU classification...")
    
    try:
        from voice_stream import VoiceStreamManager
        from memory import MemoryStore
        
        # Create test setup
        test_db_path = os.path.join(os.path.dirname(__file__), "test_voice_nlu.db")
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        # Enable Gmail tools for testing
        original_tools = os.environ.get("ENABLED_TOOLS", "")
        os.environ["ENABLED_TOOLS"] = "PLAY,PAUSE,SET_VOLUME,SEND_EMAIL,READ_EMAILS,SEARCH_EMAILS"
            
        memory = MemoryStore(test_db_path)
        voice_manager = VoiceStreamManager(memory)
        
        # Test command classification
        test_cases = [
            ("spela musik", True),
            ("pausa musiken", True), 
            ("höj volymen", True),
            ("vad tycker du om AC/DC", False),
            ("berätta något kul", False),
            ("skicka mail till chef@företag.se", True)
        ]
        
        results = []
        for text, expected_is_command in test_cases:
            result = asyncio.run(voice_manager._classify_intent_fast(text))
            is_command = result and result.get("is_tool_command", False)
            
            status = "✅" if is_command == expected_is_command else "❌"
            results.append((text, expected_is_command, is_command, status))
            print(f"  {status} '{text}' -> Command: {is_command} (expected: {expected_is_command})")
        
        # Calculate accuracy
        correct = sum(1 for _, expected, actual, _ in results if expected == actual)
        accuracy = correct / len(results) * 100
        
        print(f"✅ NLU Classification Accuracy: {accuracy:.1f}% ({correct}/{len(results)})")
        
        # Restore original tools
        if original_tools:
            os.environ["ENABLED_TOOLS"] = original_tools
        else:
            os.environ.pop("ENABLED_TOOLS", None)
        
        # Cleanup
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        return accuracy >= 90.0  # Require 90% accuracy now with all tools enabled
        
    except Exception as e:
        print(f"❌ NLU classification test failed: {e}")
        return False

async def test_websocket_connection():
    """Test WebSocket connection to voice endpoint"""
    print("\n🧪 Testing WebSocket connection...")
    
    try:
        # Start test client
        from app import app
        
        # Test WebSocket endpoint exists and is callable
        client = TestClient(app)
        
        # Try to connect to WebSocket endpoint
        session_id = "test_session_123"
        
        # Since TestClient doesn't support WebSocket directly, test the handler function
        from voice_stream import get_voice_manager
        from memory import MemoryStore
        
        test_db_path = os.path.join(os.path.dirname(__file__), "test_voice_ws.db")
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        memory = MemoryStore(test_db_path)
        voice_mgr = get_voice_manager(memory)
        
        assert voice_mgr is not None
        assert hasattr(voice_mgr, 'handle_voice_session')
        
        print("✅ WebSocket handler accessible")
        
        # Test mock WebSocket message processing
        mock_data = {
            "type": "voice_input",
            "text": "spela musik",
            "timestamp": time.time()
        }
        
        # Test voice input processing logic
        intent_result = await voice_mgr._classify_intent_fast("spela musik")
        assert intent_result is not None
        assert intent_result.get("is_tool_command") == True
        
        print("✅ Voice input processing works")
        
        # Cleanup
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        return True
        
    except Exception as e:
        print(f"❌ WebSocket connection test failed: {e}")
        return False

async def test_tool_execution_simulation():
    """Test tool execution workflow for voice commands"""
    print("\n🧪 Testing tool execution simulation...")
    
    try:
        from voice_stream import VoiceStreamManager
        from memory import MemoryStore
        from core import enabled_tools
        
        test_db_path = os.path.join(os.path.dirname(__file__), "test_voice_tools.db")
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        memory = MemoryStore(test_db_path)
        voice_manager = VoiceStreamManager(memory)
        
        # Enable Gmail tools for testing
        original_tools = os.environ.get("ENABLED_TOOLS", "")
        os.environ["ENABLED_TOOLS"] = "PLAY,PAUSE,SET_VOLUME,SEND_EMAIL,READ_EMAILS,SEARCH_EMAILS"
        
        # Check enabled tools
        tools = enabled_tools()
        print(f"  Enabled tools: {list(tools)}")
        
        # Test tool command detection
        test_commands = [
            "spela musik",
            "pausa musiken", 
            "höj volymen",
            "skicka mail"
        ]
        
        tool_results = []
        for command in test_commands:
            intent = await voice_manager._classify_intent_fast(command)
            if intent and intent.get("is_tool_command"):
                tool_name = intent.get("tool")
                tool_args = intent.get("args", {})
                
                print(f"  ✅ '{command}' -> Tool: {tool_name}, Args: {tool_args}")
                tool_results.append((command, tool_name, tool_args))
            else:
                print(f"  ❌ '{command}' -> No tool detected")
        
        print(f"✅ Tool detection: {len(tool_results)}/{len(test_commands)} commands mapped to tools")
        
        # Restore original tools
        if original_tools:
            os.environ["ENABLED_TOOLS"] = original_tools
        else:
            os.environ.pop("ENABLED_TOOLS", None)
        
        # Cleanup
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        return len(tool_results) >= 3  # At least 3 commands should map to tools now
        
    except Exception as e:
        print(f"❌ Tool execution test failed: {e}")
        return False

async def test_conversation_simulation():
    """Test conversation handling for non-command inputs"""
    print("\n🧪 Testing conversation simulation...")
    
    try:
        from voice_stream import VoiceStreamManager
        from memory import MemoryStore
        
        test_db_path = os.path.join(os.path.dirname(__file__), "test_voice_conv.db")
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        memory = MemoryStore(test_db_path)
        voice_manager = VoiceStreamManager(memory)
        
        # Test conversation inputs (should NOT trigger tools)
        conversation_inputs = [
            "vad tycker du om AC/DC",
            "berätta något intressant",
            "hur mår du idag",
            "vad kan du hjälpa mig med"
        ]
        
        conv_results = []
        for text in conversation_inputs:
            intent = await voice_manager._classify_intent_fast(text)
            is_tool_command = intent and intent.get("is_tool_command", False)
            
            if not is_tool_command:
                print(f"  ✅ '{text}' -> Conversation (not tool)")
                conv_results.append(text)
            else:
                print(f"  ❌ '{text}' -> Incorrectly detected as tool command")
        
        print(f"✅ Conversation detection: {len(conv_results)}/{len(conversation_inputs)} correctly identified")
        
        # Test system prompt retrieval
        system_prompt = voice_manager._get_alice_system_prompt()
        assert "Alice" in system_prompt
        assert "svenska" in system_prompt.lower()
        
        print("✅ Alice system prompt configured correctly")
        
        # Cleanup
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        return len(conv_results) >= 3  # At least 3 should be conversation
        
    except Exception as e:
        print(f"❌ Conversation test failed: {e}")
        return False

async def test_memory_integration():
    """Test memory system integration with voice"""
    print("\n🧪 Testing memory integration...")
    
    try:
        from voice_stream import VoiceStreamManager
        from memory import MemoryStore
        
        test_db_path = os.path.join(os.path.dirname(__file__), "test_voice_memory.db")
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        memory = MemoryStore(test_db_path)
        voice_manager = VoiceStreamManager(memory)
        
        # Test memory storage
        test_text = "User asked about music preferences. Alice recommended jazz."
        
        # Store memory entry
        memory_id = memory.upsert_text_memory_single(
            test_text,
            tags_json=json.dumps({"type": "conversation", "timestamp": time.time()})
        )
        
        assert memory_id is not None
        print(f"  ✅ Memory stored with ID: {memory_id}")
        
        # Test memory retrieval
        memories = memory.retrieve_text_bm25_recency("music", limit=3)
        assert len(memories) > 0
        
        print(f"  Retrieved memories: {len(memories)}")
        for i, mem in enumerate(memories):
            print(f"    Memory {i}: {mem}")
        
        found_memory = any("music" in str(mem).lower() for mem in memories)
        if not found_memory:
            # Try different field names
            found_memory = any("music" in mem.get("text", "").lower() for mem in memories)
        
        print(f"  Found music memory: {found_memory}")
        assert found_memory, "Memory retrieval failed"
        
        print("✅ Memory storage and retrieval working")
        
        # Cleanup
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        return True
        
    except Exception as e:
        print(f"❌ Memory integration test failed: {e}")
        return False

def test_frontend_voice_client():
    """Test frontend voice client JavaScript"""
    print("\n🧪 Testing frontend voice client...")
    
    try:
        # Check if voice client exists
        voice_client_path = Path("../web/public/lib/voice-client.js")
        
        if not voice_client_path.exists():
            print(f"❌ Voice client not found at {voice_client_path}")
            return False
        
        # Read and validate voice client code
        with open(voice_client_path, 'r') as f:
            content = f.read()
        
        # Check for key components
        required_components = [
            "class AliceVoiceClient",
            "webkitSpeechRecognition",
            "speechSynthesis",
            "WebSocket",
            "connect()",
            "startListening()",
            "speak("
        ]
        
        missing_components = []
        for component in required_components:
            if component not in content:
                missing_components.append(component)
        
        if missing_components:
            print(f"❌ Missing components in voice client: {missing_components}")
            return False
        
        print("✅ Voice client JavaScript has all required components")
        
        # Check React component
        react_component_path = Path("../web/components/VoiceInterface.jsx")
        
        if not react_component_path.exists():
            print(f"❌ React voice component not found at {react_component_path}")
            return False
        
        with open(react_component_path, 'r') as f:
            react_content = f.read()
        
        react_requirements = [
            "const VoiceInterface",
            "useState",
            "useEffect",
            "handleConnect",
            "handleToggleListening",
            "AliceVoiceClient"
        ]
        
        missing_react = []
        for req in react_requirements:
            if req not in react_content:
                missing_react.append(req)
        
        if missing_react:
            print(f"❌ Missing React components: {missing_react}")
            return False
        
        print("✅ React VoiceInterface component properly structured")
        
        return True
        
    except Exception as e:
        print(f"❌ Frontend voice client test failed: {e}")
        return False

async def test_full_voice_flow_simulation():
    """Simulate complete voice interaction flow"""
    print("\n🧪 Testing complete voice flow simulation...")
    
    try:
        from voice_stream import VoiceStreamManager
        from memory import MemoryStore
        
        test_db_path = os.path.join(os.path.dirname(__file__), "test_voice_flow.db")
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        # Enable Gmail tools for testing
        original_tools = os.environ.get("ENABLED_TOOLS", "")
        os.environ["ENABLED_TOOLS"] = "PLAY,PAUSE,SET_VOLUME,SEND_EMAIL,READ_EMAILS,SEARCH_EMAILS"
        
        memory = MemoryStore(test_db_path)
        voice_manager = VoiceStreamManager(memory)
        
        # Simulate voice session
        session_id = "test_session_flow"
        session_context = []
        
        # Test scenarios
        scenarios = [
            {
                "input": "spela musik", 
                "expected_type": "tool_command",
                "description": "Music playback command"
            },
            {
                "input": "vad tycker du om jazz",
                "expected_type": "conversation", 
                "description": "Music discussion"
            },
            {
                "input": "höj volymen lite",
                "expected_type": "tool_command",
                "description": "Volume control"
            },
            {
                "input": "berätta mer om Miles Davis",
                "expected_type": "conversation",
                "description": "Artist information request"
            }
        ]
        
        results = []
        for scenario in scenarios:
            text = scenario["input"]
            expected = scenario["expected_type"]
            description = scenario["description"]
            
            print(f"  Testing: {description}")
            print(f"  Input: '{text}'")
            
            # Classify intent
            intent = await voice_manager._classify_intent_fast(text)
            
            if intent and intent.get("is_tool_command"):
                actual_type = "tool_command"
                tool_name = intent.get("tool")
                print(f"  Result: Tool command -> {tool_name}")
            else:
                actual_type = "conversation"
                print(f"  Result: Conversation")
            
            success = actual_type == expected
            status = "✅" if success else "❌"
            print(f"  {status} Expected: {expected}, Got: {actual_type}")
            
            results.append({
                "input": text,
                "expected": expected,
                "actual": actual_type,
                "success": success,
                "description": description
            })
            
            # Add to session context for memory testing
            session_context.append({
                "role": "user",
                "content": text,
                "timestamp": time.time()
            })
            
            print()
        
        # Calculate success rate
        successful = sum(1 for r in results if r["success"])
        success_rate = successful / len(results) * 100
        
        print(f"✅ Voice flow simulation: {success_rate:.1f}% success rate ({successful}/{len(results)})")
        
        # Test session context handling
        assert len(session_context) == len(scenarios)
        print("✅ Session context tracking working")
        
        # Restore original tools
        if original_tools:
            os.environ["ENABLED_TOOLS"] = original_tools
        else:
            os.environ.pop("ENABLED_TOOLS", None)
        
        # Cleanup
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        return success_rate >= 90.0  # Require 90% success rate with all fixes
        
    except Exception as e:
        print(f"❌ Voice flow simulation failed: {e}")
        return False

def run_all_tests():
    """Run complete voice system test suite"""
    print("🚀 Alice Voice System - Comprehensive Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_imports,
        test_voice_manager_creation,
        test_nlu_classification_fast,
        test_websocket_connection,
        test_tool_execution_simulation,
        test_conversation_simulation,
        test_memory_integration,
        test_frontend_voice_client,
        test_full_voice_flow_simulation
    ]
    
    results = []
    
    for test_func in test_functions:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = asyncio.run(test_func())
            else:
                result = test_func()
            results.append((test_func.__name__, result))
        except Exception as e:
            print(f"❌ {test_func.__name__} crashed: {e}")
            results.append((test_func.__name__, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    success_rate = passed / total * 100
    print(f"\n🏆 Overall Success: {success_rate:.1f}% ({passed}/{total})")
    
    if success_rate >= 90:
        print("🎉 EXCELLENT! Voice system ready for deployment!")
    elif success_rate >= 75:
        print("⚠️  GOOD! Minor issues to address before deployment")
    else:
        print("🚨 CRITICAL! Major issues must be fixed before deployment")
    
    return success_rate >= 75.0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)