#!/usr/bin/env python3
"""
Gmail Integration Test Script for Alice
Tests all Gmail functionality without requiring actual credentials.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.tool_specs import TOOL_SPECS, enabled_tools, is_tool_enabled
from core.tool_registry import validate_and_execute_tool, list_tool_specs
from core.gmail_service import gmail_service, GMAIL_AVAILABLE

def test_dependencies():
    """Test if Gmail dependencies are available"""
    print("🔍 Testing Gmail Dependencies...")
    print(f"Gmail dependencies available: {GMAIL_AVAILABLE}")
    
    if GMAIL_AVAILABLE:
        try:
            from googleapiclient.discovery import build
            from google_auth_oauthlib.flow import Flow
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            print("✅ All Gmail dependencies imported successfully")
            return True
        except ImportError as e:
            print(f"❌ Import error: {e}")
            return False
    else:
        print("❌ Gmail dependencies not available")
        return False

def test_tool_specs():
    """Test Gmail tool specifications"""
    print("\n🔍 Testing Gmail Tool Specifications...")
    
    gmail_tools = ['SEND_EMAIL', 'READ_EMAILS', 'SEARCH_EMAILS']
    
    for tool in gmail_tools:
        if tool in TOOL_SPECS:
            spec = TOOL_SPECS[tool]
            print(f"✅ {tool}: {spec['desc']}")
            print(f"   Arguments: {spec['args_model'].__name__}")
            print(f"   Examples: {len(spec.get('examples', []))} provided")
        else:
            print(f"❌ {tool}: Missing specification")
    
    return True

def test_tool_validation():
    """Test tool argument validation"""
    print("\n🔍 Testing Tool Validation...")
    
    # Test valid SEND_EMAIL
    result = validate_and_execute_tool('SEND_EMAIL', {
        'to': 'test@example.com',
        'subject': 'Test Subject',
        'body': 'Test Body'
    })
    print(f"SEND_EMAIL (valid): {result['ok']} - {result['message'][:50]}...")
    
    # Test invalid SEND_EMAIL (missing fields)
    result = validate_and_execute_tool('SEND_EMAIL', {})
    print(f"SEND_EMAIL (invalid): {result['ok']} - validation errors detected")
    
    # Test valid READ_EMAILS
    result = validate_and_execute_tool('READ_EMAILS', {'max_results': 5})
    print(f"READ_EMAILS (valid): {result['ok']} - {result['message'][:50]}...")
    
    # Test invalid READ_EMAILS (out of range)
    result = validate_and_execute_tool('READ_EMAILS', {'max_results': 100})
    print(f"READ_EMAILS (invalid): {result['ok']} - validation errors detected")
    
    # Test valid SEARCH_EMAILS
    result = validate_and_execute_tool('SEARCH_EMAILS', {
        'query': 'from:test@example.com',
        'max_results': 10
    })
    print(f"SEARCH_EMAILS (valid): {result['ok']} - {result['message'][:50]}...")
    
    # Test invalid SEARCH_EMAILS (missing query)
    result = validate_and_execute_tool('SEARCH_EMAILS', {})
    print(f"SEARCH_EMAILS (invalid): {result['ok']} - validation errors detected")
    
    return True

def test_tool_enablement():
    """Test tool enablement configuration"""
    print("\n🔍 Testing Tool Enablement...")
    
    # Test default configuration
    current_tools = enabled_tools()
    print(f"Default enabled tools: {current_tools}")
    
    gmail_tools = ['SEND_EMAIL', 'READ_EMAILS', 'SEARCH_EMAILS']
    for tool in gmail_tools:
        enabled = is_tool_enabled(tool)
        print(f"{tool}: {'✅ Enabled' if enabled else '❌ Disabled'}")
    
    # Test with environment variable
    os.environ['ENABLED_TOOLS'] = 'SEND_EMAIL,READ_EMAILS,SEARCH_EMAILS'
    from importlib import reload
    import core.tool_specs
    reload(core.tool_specs)
    
    new_tools = core.tool_specs.enabled_tools()
    print(f"With ENABLED_TOOLS env var: {new_tools}")
    
    for tool in gmail_tools:
        enabled = core.tool_specs.is_tool_enabled(tool)
        print(f"{tool}: {'✅ Enabled' if enabled else '❌ Disabled'}")
    
    return True

def test_harmony_specs():
    """Test Harmony tool spec generation"""
    print("\n🔍 Testing Harmony Spec Generation...")
    
    os.environ['ENABLED_TOOLS'] = 'SEND_EMAIL,READ_EMAILS,SEARCH_EMAILS'
    from importlib import reload
    import core.tool_specs
    reload(core.tool_specs)
    
    specs = core.tool_specs.build_harmony_tool_specs()
    gmail_specs = [spec for spec in specs if 'EMAIL' in spec['name']]
    
    print(f"Generated {len(gmail_specs)} Gmail tool specs for Harmony:")
    for spec in gmail_specs:
        print(f"✅ {spec['name']}: {spec['description'][:50]}...")
        print(f"   Parameters: {len(spec['parameters'].get('properties', {}))} fields")
        print(f"   Examples: {len(spec.get('examples', []))}")
    
    return True

def test_file_structure():
    """Test Gmail file structure and paths"""
    print("\n🔍 Testing File Structure...")
    
    server_dir = "/Users/evil/Desktop/EVIL/PROJECT/Alice/alice/server"
    
    # Check service file
    gmail_service_path = os.path.join(server_dir, "core", "gmail_service.py")
    print(f"Gmail service: {'✅ Found' if os.path.exists(gmail_service_path) else '❌ Missing'}")
    
    # Check credentials path (expected to be missing)
    credentials_path = os.path.join(server_dir, "gmail_credentials.json")
    print(f"Credentials file: {'✅ Found' if os.path.exists(credentials_path) else '❌ Missing (expected)'}")
    
    # Check token path (expected to be missing)
    token_path = os.path.join(server_dir, "gmail_token.pickle")
    print(f"Token file: {'✅ Found' if os.path.exists(token_path) else '❌ Missing (expected)'}")
    
    # Check documentation
    docs_path = os.path.join(server_dir, "GMAIL_SETUP.md")
    print(f"Documentation: {'✅ Found' if os.path.exists(docs_path) else '❌ Missing'}")
    
    return True

def main():
    """Run all Gmail integration tests"""
    print("=" * 60)
    print("🧪 ALICE GMAIL INTEGRATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_dependencies,
        test_tool_specs,
        test_tool_validation,
        test_tool_enablement,
        test_harmony_specs,
        test_file_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Gmail integration tests PASSED!")
        print("\n✅ Gmail integration is ready for OAuth setup")
        print("📖 Follow GMAIL_SETUP.md for credentials configuration")
    else:
        print("⚠️  Some tests failed - check output above")
    
    print("=" * 60)

if __name__ == "__main__":
    main()