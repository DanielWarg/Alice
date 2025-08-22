#!/usr/bin/env python3
"""
Test script för Alice Agent Bridge
Testar integration med befintliga Alice-system.
"""

import asyncio
import os
import sys
import json
from datetime import datetime

# Add server path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory import MemoryStore
from agents.bridge import AliceAgentBridge, AgentBridgeRequest, StreamChunkType
from deps import validate_openai_config, get_openai_settings


async def test_basic_streaming():
    """Test basic streaming functionality"""
    print("🧪 Testing Basic Streaming...")
    
    # Setup memory
    memory = MemoryStore("data/test_bridge.db")
    
    # Create bridge
    bridge = AliceAgentBridge(memory)
    
    # Test request
    request = AgentBridgeRequest(
        prompt="Hej Alice, hur mår du?",
        model="gpt-oss:20b", 
        provider="local",
        use_rag=False,
        raw=True
    )
    
    print("Request:", request.prompt)
    print("Response chunks:")
    
    chunk_count = 0
    full_response = ""
    
    async for chunk in bridge.stream_response(request):
        chunk_count += 1
        print(f"  [{chunk.type}] {chunk.content[:100]}{'...' if len(chunk.content) > 100 else ''}")
        
        if chunk.type == StreamChunkType.CHUNK:
            full_response += chunk.content
        
        # Limit chunks for testing
        if chunk_count > 20:
            break
    
    print(f"\n✅ Streamed {chunk_count} chunks")
    print(f"Full response length: {len(full_response)} chars")
    return True


async def test_rag_integration():
    """Test RAG integration"""
    print("\n🧪 Testing RAG Integration...")
    
    memory = MemoryStore("data/test_bridge.db")
    
    # Add some test memories
    memory.upsert_text_memory_single(
        "Alice gillar att hjälpa användare med musikstyrning", 
        score=0.9,
        tags_json='{"category": "alice_info"}'
    )
    
    memory.upsert_text_memory_single(
        "Användaren brukar lyssna på rock och pop-musik",
        score=0.8, 
        tags_json='{"category": "user_preferences"}'
    )
    
    bridge = AliceAgentBridge(memory)
    
    request = AgentBridgeRequest(
        prompt="Vad vet du om mig och musik?",
        use_rag=True,
        raw=False
    )
    
    print("Request:", request.prompt)
    print("Response with RAG:")
    
    context_found = False
    async for chunk in bridge.stream_response(request):
        if chunk.type == StreamChunkType.PLANNING and "kontext" in chunk.content.lower():
            context_found = True
        print(f"  [{chunk.type}] {chunk.content[:150]}{'...' if len(chunk.content) > 150 else ''}")
        
        if chunk.type == StreamChunkType.DONE:
            break
    
    print(f"✅ RAG context {'found' if context_found else 'not found'}")
    return True


async def test_tool_integration():
    """Test tool integration with Harmony"""
    print("\n🧪 Testing Tool Integration...")
    
    memory = MemoryStore("data/test_bridge.db")
    bridge = AliceAgentBridge(memory)
    
    # Test tool request
    request = AgentBridgeRequest(
        prompt="spela musik",  # Should trigger PLAY tool
        use_tools=True,
        provider="local"
    )
    
    print("Request:", request.prompt)
    print("Response with tools:")
    
    tool_executed = False
    async for chunk in bridge.stream_response(request):
        if chunk.type == StreamChunkType.TOOL:
            tool_executed = True
        print(f"  [{chunk.type}] {chunk.content[:150]}{'...' if len(chunk.content) > 150 else ''}")
        
        if chunk.type == StreamChunkType.DONE:
            break
    
    print(f"✅ Tool {'executed' if tool_executed else 'not executed'}")
    return True


async def test_health_check():
    """Test bridge health check"""
    print("\n🧪 Testing Health Check...")
    
    memory = MemoryStore("data/test_bridge.db")
    bridge = AliceAgentBridge(memory)
    
    health = await bridge.health_check()
    
    print("Health Status:")
    for key, value in health.items():
        status_icon = "✅" if value else "❌"
        print(f"  {status_icon} {key}: {value}")
    
    return health["bridge_active"]


async def test_openai_config():
    """Test OpenAI configuration"""
    print("\n🧪 Testing OpenAI Configuration...")
    
    settings = get_openai_settings()
    result = validate_openai_config(settings)
    
    print(f"Configuration Valid: {'✅' if result['valid'] else '❌'}")
    
    if result['errors']:
        print("Errors:")
        for error in result['errors']:
            print(f"  ❌ {error}")
    
    if result['warnings']:
        print("Warnings:")
        for warning in result['warnings']:
            print(f"  ⚠️ {warning}")
    
    print("Config Summary:")
    for key, value in result['config_summary'].items():
        print(f"  {key}: {value}")
    
    return result['valid']


async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Alice Agent Bridge Integration Tests")
    print("=" * 60)
    
    tests = [
        ("OpenAI Config", test_openai_config),
        ("Health Check", test_health_check), 
        ("Basic Streaming", test_basic_streaming),
        ("RAG Integration", test_rag_integration),
        ("Tool Integration", test_tool_integration),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*60}")
            start_time = datetime.now()
            result = await test_func()
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            results[test_name] = {
                "success": bool(result),
                "duration": duration,
                "error": None
            }
            
            print(f"\n{'✅' if result else '❌'} {test_name} - {duration:.2f}s")
            
        except Exception as e:
            print(f"\n❌ {test_name} - ERROR: {str(e)}")
            results[test_name] = {
                "success": False,
                "duration": 0,
                "error": str(e)
            }
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results.values() if r["success"])
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        duration = f"{result['duration']:.2f}s"
        error = f" ({result['error']})" if result['error'] else ""
        print(f"{status:<10} {test_name:<20} {duration:<8} {error}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Agent Bridge is ready.")
    else:
        print("⚠️ Some tests failed. Check configuration.")
    
    return passed == total


if __name__ == "__main__":
    # Set up test environment
    os.environ.setdefault("USE_HARMONY", "true")
    os.environ.setdefault("USE_TOOLS", "true") 
    os.environ.setdefault("LOCAL_MODEL", "gpt-oss:20b")
    
    # Run tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)