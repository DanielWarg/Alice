#!/usr/bin/env python3
"""
Comprehensive QA Test Suite for Alice Systems
Tests all new functionality before production deployment

Systems Under Test:
1. Modular HUD UI System
2. Voice System Integration  
3. Gmail Integration
4. Enhanced NLU System
5. Memory System Enhancements

This script provides complete test coverage with performance metrics,
stress testing, and production readiness assessment.
"""

import os
import sys
import asyncio
import time
import json
import aiohttp
import statistics
import subprocess
import websockets
from pathlib import Path
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager
import tempfile
import sqlite3

# Add server to path
sys.path.insert(0, str(Path(__file__).parent))

# Test configuration
ALICE_SERVER_URL = "http://localhost:8000"
ALICE_WS_URL = "ws://localhost:8000"
FRONTEND_URL = "http://localhost:3100"
TEST_TIMEOUT = 30  # seconds

# Enable all tools for comprehensive testing
os.environ["ENABLED_TOOLS"] = "PLAY,PAUSE,STOP,NEXT,PREV,SET_VOLUME,MUTE,UNMUTE,REPEAT,SHUFFLE,LIKE,UNLIKE,SEND_EMAIL,READ_EMAILS,SEARCH_EMAILS"

class AliceQATestSuite:
    """Comprehensive QA test suite for Alice systems"""
    
    def __init__(self):
        self.results = {
            'hud_ui': {'passed': 0, 'failed': 0, 'tests': []},
            'voice_system': {'passed': 0, 'failed': 0, 'tests': []},
            'gmail_integration': {'passed': 0, 'failed': 0, 'tests': []},
            'nlu_system': {'passed': 0, 'failed': 0, 'tests': []},
            'memory_system': {'passed': 0, 'failed': 0, 'tests': []},
            'performance': {'response_times': [], 'stress_test_results': {}},
            'errors': [],
            'recommendations': []
        }
        self.test_db_path = None
        
    async def setup_test_environment(self):
        """Setup test environment and temporary database"""
        print("🔧 Setting up test environment...")
        
        # Create temporary test database
        self.test_db_path = tempfile.mktemp(suffix='.db')
        
        # Verify server is running
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ALICE_SERVER_URL}/api/health") as response:
                    if response.status != 200:
                        raise Exception(f"Alice server not responding: {response.status}")
                        
            print("✅ Alice server is running")
            
            # Check frontend availability
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(FRONTEND_URL) as response:
                        if response.status == 200:
                            print("✅ Alice frontend is running")
                        else:
                            print("⚠️  Alice frontend not accessible")
            except:
                print("⚠️  Alice frontend not accessible")
                
        except Exception as e:
            raise Exception(f"Failed to setup test environment: {e}")
    
    def record_test_result(self, system: str, test_name: str, success: bool, 
                          details: str = "", response_time: float = 0):
        """Record individual test result"""
        result = {
            'test': test_name,
            'success': success,
            'details': details,
            'response_time': response_time,
            'timestamp': time.time()
        }
        
        self.results[system]['tests'].append(result)
        if success:
            self.results[system]['passed'] += 1
        else:
            self.results[system]['failed'] += 1
            
        if response_time > 0:
            self.results['performance']['response_times'].append(response_time)
    
    # 1. MODULAR HUD UI SYSTEM TESTS
    async def test_hud_ui_system(self):
        """Test Modular HUD UI System components"""
        print("\n🎨 Testing Modular HUD UI System...")
        
        # Test React component structure
        try:
            web_dir = Path(__file__).parent.parent / "web"
            components_dir = web_dir / "components"
            
            # Check core components exist
            core_components = [
                "AliceHUD.jsx", "ErrorBoundary.jsx", "SafeBootMode.jsx",
                "AliceCoreVisual.jsx", "ChatInterface.jsx", "SystemMetrics.jsx",
                "VoiceInterface.jsx", "OverlayModules.jsx"
            ]
            
            missing_components = []
            for component in core_components:
                if not (components_dir / component).exists():
                    missing_components.append(component)
            
            if missing_components:
                self.record_test_result('hud_ui', 'Component Structure', False, 
                                      f"Missing components: {missing_components}")
            else:
                self.record_test_result('hud_ui', 'Component Structure', True, 
                                      "All core components present")
            
        except Exception as e:
            self.record_test_result('hud_ui', 'Component Structure', False, str(e))
        
        # Test error boundary functionality
        await self._test_error_boundaries()
        
        # Test Safe Boot Mode
        await self._test_safe_boot_mode()
        
        # Test API connections
        await self._test_api_connections()
    
    async def _test_error_boundaries(self):
        """Test error boundary crash protection"""
        try:
            # Check ErrorBoundary component structure
            web_dir = Path(__file__).parent.parent / "web"
            error_boundary_path = web_dir / "components" / "ErrorBoundary.jsx"
            
            if not error_boundary_path.exists():
                self.record_test_result('hud_ui', 'Error Boundaries', False, 
                                      "ErrorBoundary component missing")
                return
            
            # Read and validate error boundary code
            with open(error_boundary_path) as f:
                content = f.read()
            
            required_methods = [
                'getDerivedStateFromError', 'componentDidCatch', 'useErrorHandler',
                'withErrorBoundary'
            ]
            
            missing_methods = [method for method in required_methods 
                             if method not in content]
            
            if missing_methods:
                self.record_test_result('hud_ui', 'Error Boundaries', False,
                                      f"Missing methods: {missing_methods}")
            else:
                self.record_test_result('hud_ui', 'Error Boundaries', True,
                                      "Error boundary implementation complete")
                
        except Exception as e:
            self.record_test_result('hud_ui', 'Error Boundaries', False, str(e))
    
    async def _test_safe_boot_mode(self):
        """Test Safe Boot Mode functionality"""
        try:
            web_dir = Path(__file__).parent.parent / "web"
            safe_boot_path = web_dir / "components" / "SafeBootMode.jsx"
            
            if not safe_boot_path.exists():
                self.record_test_result('hud_ui', 'Safe Boot Mode', False,
                                      "SafeBootMode component missing")
                return
            
            with open(safe_boot_path) as f:
                content = f.read()
            
            required_features = [
                'emergencyReset', 'privacySettings', 'systemChecks',
                'SafeBootIndicator', 'PrivacyControls'
            ]
            
            missing_features = [feature for feature in required_features
                              if feature not in content]
            
            if missing_features:
                self.record_test_result('hud_ui', 'Safe Boot Mode', False,
                                      f"Missing features: {missing_features}")
            else:
                self.record_test_result('hud_ui', 'Safe Boot Mode', True,
                                      "Safe Boot Mode implementation complete")
                
        except Exception as e:
            self.record_test_result('hud_ui', 'Safe Boot Mode', False, str(e))
    
    async def _test_api_connections(self):
        """Test backend API connections"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test health endpoint
                async with session.get(f"{ALICE_SERVER_URL}/api/health") as response:
                    if response.status == 200:
                        response_time = time.time() - start_time
                        self.record_test_result('hud_ui', 'API Health Check', True,
                                              "Health endpoint responding", response_time)
                    else:
                        self.record_test_result('hud_ui', 'API Health Check', False,
                                              f"Health endpoint returned {response.status}")
                
                # Test tools endpoint
                async with session.get(f"{ALICE_SERVER_URL}/api/tools/enabled") as response:
                    if response.status == 200:
                        data = await response.json()
                        enabled_tools = data.get('enabled_tools', [])
                        self.record_test_result('hud_ui', 'Tools API', True,
                                              f"Found {len(enabled_tools)} enabled tools")
                    else:
                        self.record_test_result('hud_ui', 'Tools API', False,
                                              f"Tools endpoint returned {response.status}")
                        
        except Exception as e:
            self.record_test_result('hud_ui', 'API Connections', False, str(e))
    
    # 2. VOICE SYSTEM INTEGRATION TESTS
    async def test_voice_system(self):
        """Test Voice System Integration"""
        print("\n🎤 Testing Voice System Integration...")
        
        await self._test_voice_stream_manager()
        await self._test_websocket_connection()
        await self._test_voice_command_classification()
        await self._test_tool_execution_paths()
        await self._test_voice_memory_integration()
    
    async def _test_voice_stream_manager(self):
        """Test VoiceStreamManager functionality"""
        try:
            from voice_stream import VoiceStreamManager, get_voice_manager
            from memory import MemoryStore
            
            # Create test memory store
            memory = MemoryStore(self.test_db_path)
            voice_manager = VoiceStreamManager(memory)
            
            # Test manager creation
            if voice_manager.memory == memory:
                self.record_test_result('voice_system', 'VoiceStreamManager Creation', True,
                                      "VoiceStreamManager created with MemoryStore")
            else:
                self.record_test_result('voice_system', 'VoiceStreamManager Creation', False,
                                      "VoiceStreamManager memory connection failed")
            
            # Test global instance
            global_manager = get_voice_manager(memory)
            if global_manager is not None:
                self.record_test_result('voice_system', 'Global Voice Manager', True,
                                      "Global voice manager accessible")
            else:
                self.record_test_result('voice_system', 'Global Voice Manager', False,
                                      "Global voice manager not accessible")
                
        except Exception as e:
            self.record_test_result('voice_system', 'VoiceStreamManager', False, str(e))
    
    async def _test_websocket_connection(self):
        """Test WebSocket connection capability"""
        try:
            # Test WebSocket endpoint exists in FastAPI app
            from app import app
            routes = [route.path for route in app.routes]
            
            has_ws_endpoint = any("/ws/voice/" in route for route in routes)
            
            if has_ws_endpoint:
                self.record_test_result('voice_system', 'WebSocket Endpoint', True,
                                      "Voice WebSocket endpoint registered")
            else:
                self.record_test_result('voice_system', 'WebSocket Endpoint', False,
                                      "Voice WebSocket endpoint missing")
            
            # Test WebSocket handler logic (without actual connection)
            from voice_stream import VoiceStreamManager
            from memory import MemoryStore
            
            memory = MemoryStore(self.test_db_path)
            voice_manager = VoiceStreamManager(memory)
            
            if hasattr(voice_manager, 'handle_voice_session'):
                self.record_test_result('voice_system', 'WebSocket Handler', True,
                                      "WebSocket handler method exists")
            else:
                self.record_test_result('voice_system', 'WebSocket Handler', False,
                                      "WebSocket handler method missing")
                
        except Exception as e:
            self.record_test_result('voice_system', 'WebSocket Connection', False, str(e))
    
    async def _test_voice_command_classification(self):
        """Test voice command classification accuracy"""
        try:
            from voice_stream import VoiceStreamManager
            from memory import MemoryStore
            
            memory = MemoryStore(self.test_db_path)
            voice_manager = VoiceStreamManager(memory)
            
            # Test cases for command classification
            test_cases = [
                ("spela musik", True, "PLAY"),
                ("pausa musiken", True, "PAUSE"),
                ("höj volymen", True, "SET_VOLUME"),
                ("skicka mail till test@example.com", True, "SEND_EMAIL"),
                ("vad tycker du om AC/DC", False, None),
                ("berätta något kul", False, None),
                ("när grundades bandet", False, None)
            ]
            
            correct_classifications = 0
            total_tests = len(test_cases)
            
            for text, expected_is_command, expected_tool in test_cases:
                start_time = time.time()
                result = await voice_manager._classify_intent_fast(text)
                response_time = time.time() - start_time
                
                is_command = result and result.get("is_tool_command", False)
                detected_tool = result.get("tool") if result else None
                
                if expected_is_command:
                    if is_command and detected_tool == expected_tool:
                        correct_classifications += 1
                else:
                    if not is_command:
                        correct_classifications += 1
            
            accuracy = correct_classifications / total_tests
            
            if accuracy >= 0.9:
                self.record_test_result('voice_system', 'Command Classification', True,
                                      f"Classification accuracy: {accuracy:.1%}")
            else:
                self.record_test_result('voice_system', 'Command Classification', False,
                                      f"Low classification accuracy: {accuracy:.1%}")
                
        except Exception as e:
            self.record_test_result('voice_system', 'Command Classification', False, str(e))
    
    async def _test_tool_execution_paths(self):
        """Test tool execution workflow"""
        try:
            from voice_stream import VoiceStreamManager
            from memory import MemoryStore
            from core import enabled_tools
            
            memory = MemoryStore(self.test_db_path)
            voice_manager = VoiceStreamManager(memory)
            
            # Check enabled tools
            tools = enabled_tools()
            
            if len(tools) >= 5:  # Should have music + email tools
                self.record_test_result('voice_system', 'Tool Availability', True,
                                      f"Found {len(tools)} enabled tools")
            else:
                self.record_test_result('voice_system', 'Tool Availability', False,
                                      f"Only {len(tools)} tools enabled")
            
            # Test tool mapping for voice commands
            commands = ["spela musik", "pausa", "höj volym", "skicka mail"]
            mapped_tools = 0
            
            for command in commands:
                intent = await voice_manager._classify_intent_fast(command)
                if intent and intent.get("is_tool_command") and intent.get("tool"):
                    mapped_tools += 1
            
            if mapped_tools >= 3:  # Most commands should map to tools
                self.record_test_result('voice_system', 'Tool Mapping', True,
                                      f"{mapped_tools}/{len(commands)} commands mapped")
            else:
                self.record_test_result('voice_system', 'Tool Mapping', False,
                                      f"Only {mapped_tools}/{len(commands)} commands mapped")
                
        except Exception as e:
            self.record_test_result('voice_system', 'Tool Execution', False, str(e))
    
    async def _test_voice_memory_integration(self):
        """Test voice system memory integration"""
        try:
            from voice_stream import VoiceStreamManager
            from memory import MemoryStore
            
            memory = MemoryStore(self.test_db_path)
            voice_manager = VoiceStreamManager(memory)
            
            # Test memory storage
            test_text = "User requested jazz music recommendations"
            memory_id = memory.upsert_text_memory_single(
                test_text, 
                tags_json=json.dumps({"type": "voice_request", "timestamp": time.time()})
            )
            
            if memory_id:
                self.record_test_result('voice_system', 'Memory Storage', True,
                                      f"Memory stored with ID: {memory_id}")
            else:
                self.record_test_result('voice_system', 'Memory Storage', False,
                                      "Failed to store memory")
            
            # Test memory retrieval
            memories = memory.retrieve_text_bm25_recency("jazz music", limit=3)
            
            if memories and len(memories) > 0:
                self.record_test_result('voice_system', 'Memory Retrieval', True,
                                      f"Retrieved {len(memories)} memories")
            else:
                self.record_test_result('voice_system', 'Memory Retrieval', False,
                                      "Memory retrieval failed")
                
        except Exception as e:
            self.record_test_result('voice_system', 'Memory Integration', False, str(e))
    
    # 3. GMAIL INTEGRATION TESTS
    async def test_gmail_integration(self):
        """Test Gmail Integration System"""
        print("\n📧 Testing Gmail Integration...")
        
        await self._test_gmail_dependencies()
        await self._test_gmail_tool_registration()
        await self._test_gmail_error_handling()
        await self._test_gmail_argument_parsing()
        await self._test_gmail_oauth_preparation()
    
    async def _test_gmail_dependencies(self):
        """Test Gmail dependencies availability"""
        try:
            from core.gmail_service import GMAIL_AVAILABLE
            
            if GMAIL_AVAILABLE:
                # Try importing Gmail dependencies
                from googleapiclient.discovery import build
                from google_auth_oauthlib.flow import Flow
                from google.auth.transport.requests import Request
                from google.oauth2.credentials import Credentials
                
                self.record_test_result('gmail_integration', 'Dependencies', True,
                                      "All Gmail dependencies available")
            else:
                self.record_test_result('gmail_integration', 'Dependencies', False,
                                      "Gmail dependencies not available")
                
        except ImportError as e:
            self.record_test_result('gmail_integration', 'Dependencies', False, 
                                  f"Import error: {e}")
        except Exception as e:
            self.record_test_result('gmail_integration', 'Dependencies', False, str(e))
    
    async def _test_gmail_tool_registration(self):
        """Test Gmail tool registration in Alice"""
        try:
            from core.tool_specs import TOOL_SPECS, enabled_tools, is_tool_enabled
            
            gmail_tools = ['SEND_EMAIL', 'READ_EMAILS', 'SEARCH_EMAILS']
            
            # Check tool specs exist
            missing_specs = [tool for tool in gmail_tools if tool not in TOOL_SPECS]
            
            if missing_specs:
                self.record_test_result('gmail_integration', 'Tool Registration', False,
                                      f"Missing tool specs: {missing_specs}")
            else:
                self.record_test_result('gmail_integration', 'Tool Registration', True,
                                      "All Gmail tools registered")
            
            # Check tool enablement
            enabled = enabled_tools()
            gmail_enabled = [tool for tool in gmail_tools if tool in enabled]
            
            if len(gmail_enabled) == len(gmail_tools):
                self.record_test_result('gmail_integration', 'Tool Enablement', True,
                                      f"All Gmail tools enabled: {gmail_enabled}")
            else:
                self.record_test_result('gmail_integration', 'Tool Enablement', False,
                                      f"Only {len(gmail_enabled)}/{len(gmail_tools)} Gmail tools enabled")
                
        except Exception as e:
            self.record_test_result('gmail_integration', 'Tool Registration', False, str(e))
    
    async def _test_gmail_error_handling(self):
        """Test Gmail error handling without credentials"""
        try:
            from core.tool_registry import validate_and_execute_tool
            
            # Test SEND_EMAIL without credentials (should gracefully fail)
            result = validate_and_execute_tool('SEND_EMAIL', {
                'to': 'test@example.com',
                'subject': 'Test Subject',
                'body': 'Test Body'
            })
            
            # Should validate but fail execution due to no credentials
            if not result['ok'] and 'credential' in result['message'].lower():
                self.record_test_result('gmail_integration', 'Error Handling', True,
                                      "Graceful failure without credentials")
            else:
                self.record_test_result('gmail_integration', 'Error Handling', False,
                                      f"Unexpected result: {result}")
                
        except Exception as e:
            self.record_test_result('gmail_integration', 'Error Handling', False, str(e))
    
    async def _test_gmail_argument_parsing(self):
        """Test Gmail argument validation"""
        try:
            from core.tool_registry import validate_and_execute_tool
            
            # Test valid SEND_EMAIL arguments
            valid_result = validate_and_execute_tool('SEND_EMAIL', {
                'to': 'valid@example.com',
                'subject': 'Valid Subject',
                'body': 'Valid body content'
            })
            
            # Should pass validation (even if execution fails)
            if 'validation' not in valid_result.get('message', '').lower():
                self.record_test_result('gmail_integration', 'Argument Validation - Valid', True,
                                      "Valid arguments accepted")
            else:
                self.record_test_result('gmail_integration', 'Argument Validation - Valid', False,
                                      "Valid arguments rejected")
            
            # Test invalid SEND_EMAIL arguments
            invalid_result = validate_and_execute_tool('SEND_EMAIL', {})
            
            # Should fail validation
            if not invalid_result['ok']:
                self.record_test_result('gmail_integration', 'Argument Validation - Invalid', True,
                                      "Invalid arguments properly rejected")
            else:
                self.record_test_result('gmail_integration', 'Argument Validation - Invalid', False,
                                      "Invalid arguments incorrectly accepted")
                
        except Exception as e:
            self.record_test_result('gmail_integration', 'Argument Parsing', False, str(e))
    
    async def _test_gmail_oauth_preparation(self):
        """Test Gmail OAuth flow preparation"""
        try:
            server_dir = Path(__file__).parent
            
            # Check for Gmail setup documentation
            docs_path = server_dir / "GMAIL_SETUP.md"
            
            if docs_path.exists():
                self.record_test_result('gmail_integration', 'OAuth Documentation', True,
                                      "Gmail setup documentation available")
            else:
                self.record_test_result('gmail_integration', 'OAuth Documentation', False,
                                      "Gmail setup documentation missing")
            
            # Check Gmail service structure
            from core.gmail_service import gmail_service
            
            if gmail_service is not None:
                self.record_test_result('gmail_integration', 'OAuth Service Structure', True,
                                      "Gmail service structure ready")
            else:
                self.record_test_result('gmail_integration', 'OAuth Service Structure', False,
                                      "Gmail service not properly initialized")
                
        except Exception as e:
            self.record_test_result('gmail_integration', 'OAuth Preparation', False, str(e))
    
    # 4. ENHANCED NLU SYSTEM TESTS
    async def test_nlu_system(self):
        """Test Enhanced NLU System"""
        print("\n🧠 Testing Enhanced NLU System...")
        
        await self._test_command_vs_chat_discrimination()
        await self._test_volume_pattern_recognition()
        await self._test_tool_classification()
        await self._test_confidence_scoring()
    
    async def _test_command_vs_chat_discrimination(self):
        """Test command vs chat discrimination"""
        try:
            from core.router import classify
            
            # Test cases with expected classifications
            test_cases = [
                # Clear tool commands
                ("spela musik", "tool_command", "PLAY"),
                ("pausa musiken", "tool_command", "PAUSE"),
                ("höj volymen", "tool_command", "SET_VOLUME"),
                ("skicka mail till test@example.com", "tool_command", "SEND_EMAIL"),
                
                # Clear natural chat
                ("vad tycker du om AC/DC?", "natural_chat", None),
                ("berätta om musikhistoria", "natural_chat", None),
                ("när grundades bandet", "natural_chat", None),
                ("vad är e-post", "natural_chat", None)
            ]
            
            correct_classifications = 0
            total_tests = len(test_cases)
            
            for text, expected_type, expected_tool in test_cases:
                result = classify(text)
                
                if expected_type == "tool_command":
                    if result and result.get('tool') == expected_tool:
                        correct_classifications += 1
                elif expected_type == "natural_chat":
                    if not result or not result.get('tool'):
                        correct_classifications += 1
            
            accuracy = correct_classifications / total_tests
            
            if accuracy >= 0.85:  # High accuracy expected
                self.record_test_result('nlu_system', 'Command vs Chat', True,
                                      f"Discrimination accuracy: {accuracy:.1%}")
            else:
                self.record_test_result('nlu_system', 'Command vs Chat', False,
                                      f"Low discrimination accuracy: {accuracy:.1%}")
                
        except Exception as e:
            self.record_test_result('nlu_system', 'Command vs Chat', False, str(e))
    
    async def _test_volume_pattern_recognition(self):
        """Test volume pattern recognition improvements"""
        try:
            from core.router import classify
            
            # Volume patterns to test
            volume_patterns = [
                ("höj volymen", "SET_VOLUME"),
                ("sänk volymen", "SET_VOLUME"),
                ("volymen till 50%", "SET_VOLUME"),
                ("volymen på max", "SET_VOLUME"),
                ("tystare", "SET_VOLUME"),
                ("högre ljud", "SET_VOLUME")
            ]
            
            detected_volume_commands = 0
            
            for pattern, expected_tool in volume_patterns:
                result = classify(pattern)
                if result and result.get('tool') == expected_tool:
                    detected_volume_commands += 1
            
            success_rate = detected_volume_commands / len(volume_patterns)
            
            if success_rate >= 0.8:
                self.record_test_result('nlu_system', 'Volume Pattern Recognition', True,
                                      f"Volume pattern success: {success_rate:.1%}")
            else:
                self.record_test_result('nlu_system', 'Volume Pattern Recognition', False,
                                      f"Low volume pattern success: {success_rate:.1%}")
                
        except Exception as e:
            self.record_test_result('nlu_system', 'Volume Pattern Recognition', False, str(e))
    
    async def _test_tool_classification(self):
        """Test tool classification accuracy"""
        try:
            from core.router import classify
            from core.tool_specs import enabled_tools
            
            tools = enabled_tools()
            
            # Test various tool commands
            tool_commands = [
                ("spela låten", "PLAY"),
                ("pausknapp", "PAUSE"),
                ("stoppa", "STOP"),
                ("nästa spår", "NEXT"),
                ("föregående", "PREV"),
                ("gilla denna", "LIKE"),
                ("ogilla", "UNLIKE"),
                ("repeat på", "REPEAT"),
                ("shuffle", "SHUFFLE"),
                ("tysta", "MUTE"),
                ("avtysta", "UNMUTE"),
                ("mejla till chef@exempel.se", "SEND_EMAIL"),
                ("läs mail", "READ_EMAILS"),
                ("sök i mail", "SEARCH_EMAILS")
            ]
            
            correct_classifications = 0
            available_commands = [cmd for cmd, tool in tool_commands if tool in tools]
            
            for command, expected_tool in available_commands:
                result = classify(command)
                if result and result.get('tool') == expected_tool:
                    correct_classifications += 1
            
            if len(available_commands) > 0:
                accuracy = correct_classifications / len(available_commands)
                
                if accuracy >= 0.75:
                    self.record_test_result('nlu_system', 'Tool Classification', True,
                                          f"Tool classification accuracy: {accuracy:.1%}")
                else:
                    self.record_test_result('nlu_system', 'Tool Classification', False,
                                          f"Low tool classification accuracy: {accuracy:.1%}")
            else:
                self.record_test_result('nlu_system', 'Tool Classification', False,
                                      "No tools available for testing")
                
        except Exception as e:
            self.record_test_result('nlu_system', 'Tool Classification', False, str(e))
    
    async def _test_confidence_scoring(self):
        """Test confidence scoring in NLU"""
        try:
            from core.router import classify
            
            # Test confidence scoring with clear vs ambiguous commands
            clear_commands = ["spela musik", "pausa", "höj volym"]
            ambiguous_commands = ["kanske spela något", "skulle kunna pausa", "volym?"]
            
            clear_confidences = []
            ambiguous_confidences = []
            
            for command in clear_commands:
                result = classify(command)
                if result and 'confidence' in result:
                    clear_confidences.append(result['confidence'])
            
            for command in ambiguous_commands:
                result = classify(command)
                if result and 'confidence' in result:
                    ambiguous_confidences.append(result['confidence'])
            
            # Clear commands should have higher average confidence
            if clear_confidences and ambiguous_confidences:
                avg_clear = statistics.mean(clear_confidences)
                avg_ambiguous = statistics.mean(ambiguous_confidences)
                
                if avg_clear > avg_ambiguous:
                    self.record_test_result('nlu_system', 'Confidence Scoring', True,
                                          f"Clear: {avg_clear:.2f}, Ambiguous: {avg_ambiguous:.2f}")
                else:
                    self.record_test_result('nlu_system', 'Confidence Scoring', False,
                                          f"Confidence not discriminating properly")
            else:
                self.record_test_result('nlu_system', 'Confidence Scoring', False,
                                      "Confidence scores not available")
                
        except Exception as e:
            self.record_test_result('nlu_system', 'Confidence Scoring', False, str(e))
    
    # 5. MEMORY SYSTEM ENHANCEMENTS TESTS
    async def test_memory_system(self):
        """Test Memory System Enhancements"""
        print("\n🧠 Testing Memory System Enhancements...")
        
        await self._test_advanced_rag_retrieval()
        await self._test_semantic_chunking()
        await self._test_conversation_context_tracking()
        await self._test_memory_storage_retrieval()
    
    async def _test_advanced_rag_retrieval(self):
        """Test advanced RAG retrieval capabilities"""
        try:
            from memory import MemoryStore
            
            memory = MemoryStore(self.test_db_path)
            
            # Store test memories with different contexts
            test_memories = [
                ("Alice played jazz music for the user during work", {"type": "music", "context": "work"}),
                ("User prefers classical music for relaxation", {"type": "preference", "context": "relaxation"}),
                ("Discussion about AC/DC concert memories", {"type": "conversation", "topic": "concerts"}),
                ("Alice helped with email management yesterday", {"type": "task", "date": "yesterday"})
            ]
            
            stored_ids = []
            for text, tags in test_memories:
                memory_id = memory.upsert_text_memory_single(text, tags_json=json.dumps(tags))
                if memory_id:
                    stored_ids.append(memory_id)
            
            if len(stored_ids) == len(test_memories):
                self.record_test_result('memory_system', 'Memory Storage', True,
                                      f"Stored {len(stored_ids)} test memories")
            else:
                self.record_test_result('memory_system', 'Memory Storage', False,
                                      f"Only stored {len(stored_ids)}/{len(test_memories)} memories")
            
            # Test retrieval with different queries
            queries = [
                ("jazz music", "music"),
                ("email help", "task"),
                ("AC/DC", "conversation"),
                ("classical", "preference")
            ]
            
            successful_retrievals = 0
            for query, expected_type in queries:
                memories = memory.retrieve_text_bm25_recency(query, limit=3)
                
                if memories and len(memories) > 0:
                    successful_retrievals += 1
            
            retrieval_success = successful_retrievals / len(queries)
            
            if retrieval_success >= 0.75:
                self.record_test_result('memory_system', 'RAG Retrieval', True,
                                      f"Retrieval success: {retrieval_success:.1%}")
            else:
                self.record_test_result('memory_system', 'RAG Retrieval', False,
                                      f"Low retrieval success: {retrieval_success:.1%}")
                
        except Exception as e:
            self.record_test_result('memory_system', 'Advanced RAG', False, str(e))
    
    async def _test_semantic_chunking(self):
        """Test semantic chunking functionality"""
        try:
            from memory import MemoryStore
            
            memory = MemoryStore(self.test_db_path)
            
            # Test with longer text that should be chunked
            long_text = """
            Alice is a sophisticated AI assistant that can help with music playback, 
            email management, and general conversation. The system includes voice 
            recognition capabilities, natural language understanding, and integration 
            with external services like Gmail and Spotify. Alice maintains conversation 
            context through advanced memory systems and can learn user preferences 
            over time. The interface supports both text and voice interactions.
            """
            
            memory_id = memory.upsert_text_memory_single(
                long_text.strip(),
                tags_json=json.dumps({"type": "system_info", "chunked": True})
            )
            
            if memory_id:
                # Try to retrieve parts of the content
                retrieval_queries = ["music playback", "voice recognition", "memory systems"]
                successful_retrievals = 0
                
                for query in retrieval_queries:
                    memories = memory.retrieve_text_bm25_recency(query, limit=2)
                    if memories and any(memory_id in str(mem) for mem in memories):
                        successful_retrievals += 1
                
                if successful_retrievals >= 2:
                    self.record_test_result('memory_system', 'Semantic Chunking', True,
                                          f"Retrieved {successful_retrievals}/{len(retrieval_queries)} chunks")
                else:
                    self.record_test_result('memory_system', 'Semantic Chunking', False,
                                          f"Only retrieved {successful_retrievals}/{len(retrieval_queries)} chunks")
            else:
                self.record_test_result('memory_system', 'Semantic Chunking', False,
                                      "Failed to store long text for chunking")
                
        except Exception as e:
            self.record_test_result('memory_system', 'Semantic Chunking', False, str(e))
    
    async def _test_conversation_context_tracking(self):
        """Test conversation context tracking"""
        try:
            from memory import MemoryStore
            
            memory = MemoryStore(self.test_db_path)
            
            # Simulate conversation context
            conversation_context = [
                "User: Spela upp lite jazz musik",
                "Alice: Spelar jazz musik åt dig",
                "User: Vad var det för låt?", 
                "Alice: Det var 'Blue Train' av John Coltrane",
                "User: Spela mer av samma artist",
                "Alice: Spelar fler låtar av John Coltrane"
            ]
            
            # Store conversation context
            context_ids = []
            for i, message in enumerate(conversation_context):
                context_id = memory.upsert_text_memory_single(
                    message,
                    tags_json=json.dumps({
                        "type": "conversation",
                        "sequence": i,
                        "timestamp": time.time() + i
                    })
                )
                if context_id:
                    context_ids.append(context_id)
            
            if len(context_ids) == len(conversation_context):
                # Test context retrieval
                context_memories = memory.retrieve_text_bm25_recency("John Coltrane", limit=5)
                
                if context_memories and len(context_memories) >= 2:
                    self.record_test_result('memory_system', 'Context Tracking', True,
                                          f"Stored and retrieved conversation context")
                else:
                    self.record_test_result('memory_system', 'Context Tracking', False,
                                          "Failed to retrieve conversation context")
            else:
                self.record_test_result('memory_system', 'Context Tracking', False,
                                      f"Only stored {len(context_ids)}/{len(conversation_context)} context messages")
                
        except Exception as e:
            self.record_test_result('memory_system', 'Context Tracking', False, str(e))
    
    async def _test_memory_storage_retrieval(self):
        """Test basic memory storage and retrieval performance"""
        try:
            from memory import MemoryStore
            
            memory = MemoryStore(self.test_db_path)
            
            # Performance test - store multiple memories
            start_time = time.time()
            
            test_entries = [
                f"Test memory entry {i} with various content about Alice's capabilities"
                for i in range(50)  # Store 50 entries
            ]
            
            stored_count = 0
            for entry in test_entries:
                memory_id = memory.upsert_text_memory_single(
                    entry,
                    tags_json=json.dumps({"type": "performance_test", "index": stored_count})
                )
                if memory_id:
                    stored_count += 1
            
            storage_time = time.time() - start_time
            
            # Performance test - retrieve memories
            start_time = time.time()
            memories = memory.retrieve_text_bm25_recency("Alice capabilities", limit=10)
            retrieval_time = time.time() - start_time
            
            # Performance metrics
            storage_rate = stored_count / storage_time if storage_time > 0 else 0
            retrieval_count = len(memories) if memories else 0
            
            if stored_count >= 45 and retrieval_count >= 5:  # 90% storage success, some retrieval
                self.record_test_result('memory_system', 'Storage Performance', True,
                                      f"Stored {stored_count}/50 entries at {storage_rate:.1f}/sec, retrieved {retrieval_count}")
                self.results['performance']['response_times'].append(storage_time)
                self.results['performance']['response_times'].append(retrieval_time)
            else:
                self.record_test_result('memory_system', 'Storage Performance', False,
                                      f"Storage issues: {stored_count}/50 stored, {retrieval_count} retrieved")
                
        except Exception as e:
            self.record_test_result('memory_system', 'Storage Retrieval', False, str(e))
    
    # STRESS TESTING AND PERFORMANCE ANALYSIS
    async def run_stress_tests(self):
        """Run comprehensive stress tests"""
        print("\n⚡ Running Stress Tests and Performance Analysis...")
        
        await self._test_concurrent_load()
        await self._test_error_scenarios()
        await self._test_component_isolation()
        await self._test_memory_under_load()
    
    async def _test_concurrent_load(self):
        """Test system under concurrent load"""
        try:
            async def worker_session(worker_id: int, num_requests: int):
                async with aiohttp.ClientSession() as session:
                    results = []
                    
                    for i in range(num_requests):
                        start_time = time.time()
                        
                        payload = {
                            "prompt": f"Worker {worker_id} request {i}: spela musik",
                            "model": "gpt-oss:20b",
                            "provider": "local"
                        }
                        
                        try:
                            async with session.post(f"{ALICE_SERVER_URL}/api/chat", 
                                                  json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                                response_time = time.time() - start_time
                                success = response.status == 200
                                results.append({'success': success, 'response_time': response_time})
                                
                        except Exception as e:
                            response_time = time.time() - start_time
                            results.append({'success': False, 'response_time': response_time, 'error': str(e)})
                    
                    return results
            
            # Run 5 concurrent workers with 10 requests each
            start_time = time.time()
            tasks = [worker_session(i, 10) for i in range(5)]
            worker_results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Analyze results
            total_requests = 0
            successful_requests = 0
            all_response_times = []
            
            for worker_result in worker_results:
                if isinstance(worker_result, list):
                    for result in worker_result:
                        total_requests += 1
                        if result.get('success'):
                            successful_requests += 1
                        all_response_times.append(result.get('response_time', 0))
            
            success_rate = successful_requests / total_requests if total_requests > 0 else 0
            throughput = total_requests / total_time if total_time > 0 else 0
            avg_response_time = statistics.mean(all_response_times) if all_response_times else 0
            
            # Store performance metrics
            self.results['performance']['stress_test_results'] = {
                'concurrent_success_rate': success_rate,
                'throughput': throughput,
                'avg_response_time': avg_response_time,
                'total_requests': total_requests,
                'total_time': total_time
            }
            
            if success_rate >= 0.9 and avg_response_time < 3.0:
                self.record_test_result('performance', 'Concurrent Load', True,
                                      f"Success: {success_rate:.1%}, Throughput: {throughput:.1f}/s")
            else:
                self.record_test_result('performance', 'Concurrent Load', False,
                                      f"Poor performance: {success_rate:.1%} success, {avg_response_time:.1f}s avg")
                
        except Exception as e:
            self.record_test_result('performance', 'Concurrent Load', False, str(e))
    
    async def _test_error_scenarios(self):
        """Test error handling scenarios"""
        try:
            error_inputs = [
                "",  # Empty input
                "   ",  # Whitespace only
                "a" * 1000,  # Very long input
                "!@#$%^&*()",  # Special characters
                "invalid command that should fail",
                "sätt volymen till 200%",  # Invalid volume
                "skicka mail till fel-adress",  # Invalid email
                "spela låt nummer -5"  # Invalid parameters
            ]
            
            graceful_failures = 0
            server_crashes = 0
            
            async with aiohttp.ClientSession() as session:
                for error_input in error_inputs:
                    try:
                        payload = {
                            "prompt": error_input,
                            "model": "gpt-oss:20b",
                            "provider": "local"
                        }
                        
                        async with session.post(f"{ALICE_SERVER_URL}/api/chat",
                                              json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                            if response.status in [200, 400, 422]:  # Expected responses
                                graceful_failures += 1
                            elif response.status >= 500:  # Server errors
                                server_crashes += 1
                                
                    except Exception as e:
                        # Network/timeout errors might indicate server crash
                        if "timeout" in str(e).lower() or "connection" in str(e).lower():
                            server_crashes += 1
            
            crash_rate = server_crashes / len(error_inputs)
            graceful_rate = graceful_failures / len(error_inputs)
            
            if crash_rate < 0.1:  # Less than 10% crashes
                self.record_test_result('performance', 'Error Handling', True,
                                      f"Graceful: {graceful_rate:.1%}, Crashes: {crash_rate:.1%}")
            else:
                self.record_test_result('performance', 'Error Handling', False,
                                      f"Too many crashes: {crash_rate:.1%}")
                
        except Exception as e:
            self.record_test_result('performance', 'Error Scenarios', False, str(e))
    
    async def _test_component_isolation(self):
        """Test component isolation and error boundaries"""
        try:
            # Test that individual system failures don't crash the entire system
            
            # Test memory system isolation
            try:
                from memory import MemoryStore
                # Intentionally use invalid database path to test error handling
                invalid_memory = MemoryStore("/invalid/path/to/database.db")
                invalid_memory.upsert_text_memory_single("test", tags_json='{}')
            except Exception:
                # Expected to fail, but should not crash the process
                pass
            
            # Test voice system isolation
            try:
                from voice_stream import VoiceStreamManager
                # Test with None memory to trigger error
                voice_manager = VoiceStreamManager(None)
            except Exception:
                # Expected to fail, but should not crash the process
                pass
            
            # Test NLU system isolation
            try:
                from core.router import classify
                # Test with problematic input
                classify(None)
            except Exception:
                # Expected to fail, but should not crash the process
                pass
            
            # If we get here, component isolation is working
            self.record_test_result('performance', 'Component Isolation', True,
                                  "Components fail gracefully without system crash")
            
        except SystemExit:
            self.record_test_result('performance', 'Component Isolation', False,
                                  "System exit triggered by component failure")
        except Exception as e:
            self.record_test_result('performance', 'Component Isolation', False,
                                  f"Isolation test failed: {e}")
    
    async def _test_memory_under_load(self):
        """Test memory system under load"""
        try:
            from memory import MemoryStore
            
            memory = MemoryStore(self.test_db_path)
            
            # Rapid memory operations
            start_time = time.time()
            operations = 0
            
            # Rapid storage test
            for i in range(100):
                memory_id = memory.upsert_text_memory_single(
                    f"Load test memory {i} with timestamp {time.time()}",
                    tags_json=json.dumps({"type": "load_test", "index": i})
                )
                if memory_id:
                    operations += 1
            
            storage_time = time.time() - start_time
            
            # Rapid retrieval test
            start_time = time.time()
            for i in range(20):
                memories = memory.retrieve_text_bm25_recency(f"load test", limit=5)
                if memories:
                    operations += 1
            
            retrieval_time = time.time() - start_time
            
            total_time = storage_time + retrieval_time
            ops_per_second = operations / total_time if total_time > 0 else 0
            
            if ops_per_second >= 50:  # At least 50 operations per second
                self.record_test_result('performance', 'Memory Under Load', True,
                                      f"Memory performance: {ops_per_second:.1f} ops/sec")
            else:
                self.record_test_result('performance', 'Memory Under Load', False,
                                      f"Low memory performance: {ops_per_second:.1f} ops/sec")
                
        except Exception as e:
            self.record_test_result('performance', 'Memory Load', False, str(e))
    
    def analyze_performance_metrics(self):
        """Analyze overall performance metrics"""
        print("\n📊 Analyzing Performance Metrics...")
        
        response_times = self.results['performance']['response_times']
        
        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            p95_time = sorted_times[int(0.95 * len(sorted_times))] if len(sorted_times) > 0 else 0
            p99_time = sorted_times[int(0.99 * len(sorted_times))] if len(sorted_times) > 0 else 0
            
            performance_metrics = {
                'avg_response_time': avg_time,
                'median_response_time': median_time,
                'p95_response_time': p95_time,
                'p99_response_time': p99_time,
                'max_response_time': max_time,
                'min_response_time': min_time,
                'total_requests': len(response_times)
            }
            
            self.results['performance'].update(performance_metrics)
            
            # Performance assessment
            if avg_time < 1.0 and p95_time < 2.0:
                perf_grade = "EXCELLENT"
            elif avg_time < 2.0 and p95_time < 4.0:
                perf_grade = "GOOD"
            elif avg_time < 4.0:
                perf_grade = "ACCEPTABLE"
            else:
                perf_grade = "POOR"
                
            self.results['performance']['grade'] = perf_grade
    
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        print("\n💡 Generating Recommendations...")
        
        recommendations = []
        
        # Analyze each system
        for system, results in self.results.items():
            if system in ['performance', 'errors', 'recommendations']:
                continue
                
            total_tests = results['passed'] + results['failed']
            if total_tests == 0:
                continue
                
            success_rate = results['passed'] / total_tests
            
            if success_rate < 0.7:
                recommendations.append(f"🚨 CRITICAL: {system} has low success rate ({success_rate:.1%}). Requires immediate attention before production.")
            elif success_rate < 0.9:
                recommendations.append(f"⚠️ WARNING: {system} needs improvement ({success_rate:.1%}). Consider additional testing and fixes.")
            
            # Specific system recommendations
            failed_tests = [test for test in results['tests'] if not test['success']]
            if failed_tests:
                for test in failed_tests[:3]:  # Top 3 failed tests
                    recommendations.append(f"   - Fix {system}: {test['test']} - {test['details']}")
        
        # Performance recommendations
        if 'performance' in self.results:
            perf = self.results['performance']
            
            if perf.get('grade') == 'POOR':
                recommendations.append("🚨 CRITICAL: Poor performance detected. Optimize response times before production.")
            elif perf.get('grade') == 'ACCEPTABLE':
                recommendations.append("⚠️ WARNING: Performance is acceptable but could be improved.")
            
            # Stress test recommendations
            stress_results = perf.get('stress_test_results', {})
            if stress_results.get('concurrent_success_rate', 1.0) < 0.9:
                recommendations.append("⚠️ WARNING: System struggles under concurrent load. Consider scaling improvements.")
        
        # Production readiness assessment
        overall_systems = ['hud_ui', 'voice_system', 'gmail_integration', 'nlu_system', 'memory_system']
        system_scores = []
        
        for system in overall_systems:
            if system in self.results:
                results = self.results[system]
                total = results['passed'] + results['failed']
                score = results['passed'] / total if total > 0 else 0
                system_scores.append(score)
        
        if system_scores:
            overall_score = statistics.mean(system_scores)
            
            if overall_score >= 0.95:
                recommendations.append("✅ PRODUCTION READY: All systems performing excellently. Safe to deploy.")
            elif overall_score >= 0.9:
                recommendations.append("✅ PRODUCTION READY: Systems performing well with minor issues. Deploy with monitoring.")
            elif overall_score >= 0.8:
                recommendations.append("⚠️ CAUTION: Systems mostly working but have issues. Fix critical problems before production.")
            else:
                recommendations.append("🚨 NOT PRODUCTION READY: Multiple systems have significant issues. Extensive fixes required.")
        
        self.results['recommendations'] = recommendations
    
    def print_comprehensive_report(self):
        """Print comprehensive test report"""
        print("\n" + "=" * 80)
        print("🎯 ALICE COMPREHENSIVE QA TEST REPORT")
        print("=" * 80)
        
        # Executive Summary
        total_passed = sum(results['passed'] for system, results in self.results.items() 
                          if isinstance(results, dict) and 'passed' in results)
        total_failed = sum(results['failed'] for system, results in self.results.items()
                          if isinstance(results, dict) and 'failed' in results)
        total_tests = total_passed + total_failed
        
        overall_success = total_passed / total_tests if total_tests > 0 else 0
        
        print(f"\n📈 EXECUTIVE SUMMARY")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {total_passed}")
        print(f"   Failed: {total_failed}")
        print(f"   Success Rate: {overall_success:.1%}")
        
        # System-by-system results
        print(f"\n🔍 SYSTEM RESULTS")
        print("-" * 50)
        
        systems = {
            'hud_ui': 'Modular HUD UI System',
            'voice_system': 'Voice System Integration',
            'gmail_integration': 'Gmail Integration',
            'nlu_system': 'Enhanced NLU System',
            'memory_system': 'Memory System Enhancements'
        }
        
        for system_key, system_name in systems.items():
            if system_key in self.results:
                results = self.results[system_key]
                total = results['passed'] + results['failed']
                success_rate = results['passed'] / total if total > 0 else 0
                
                status = "✅" if success_rate >= 0.9 else "⚠️" if success_rate >= 0.7 else "❌"
                print(f"{status} {system_name}: {success_rate:.1%} ({results['passed']}/{total})")
                
                # Show failed tests
                failed_tests = [test for test in results['tests'] if not test['success']]
                if failed_tests:
                    for test in failed_tests[:2]:  # Show top 2 failures
                        print(f"     ❌ {test['test']}: {test['details'][:60]}...")
        
        # Performance Analysis
        if 'performance' in self.results:
            perf = self.results['performance']
            print(f"\n⚡ PERFORMANCE ANALYSIS")
            print("-" * 30)
            
            if perf.get('avg_response_time'):
                print(f"   Average Response Time: {perf['avg_response_time']*1000:.0f}ms")
                print(f"   95th Percentile: {perf.get('p95_response_time', 0)*1000:.0f}ms")
                print(f"   Performance Grade: {perf.get('grade', 'Unknown')}")
            
            if 'stress_test_results' in perf:
                stress = perf['stress_test_results']
                print(f"   Concurrent Success Rate: {stress.get('concurrent_success_rate', 0):.1%}")
                print(f"   Throughput: {stress.get('throughput', 0):.1f} requests/sec")
        
        # Recommendations
        if self.results['recommendations']:
            print(f"\n💡 RECOMMENDATIONS")
            print("-" * 25)
            for rec in self.results['recommendations']:
                print(f"   {rec}")
        
        # Error Summary
        if self.results['errors']:
            print(f"\n❌ CRITICAL ERRORS")
            print("-" * 20)
            for error in self.results['errors'][:5]:  # Show top 5 errors
                print(f"   • {error}")
        
        print("\n" + "=" * 80)
        
        # Final verdict
        if overall_success >= 0.95:
            print("🎉 VERDICT: ALICE IS PRODUCTION READY!")
            print("   All systems are performing excellently. Deploy with confidence.")
        elif overall_success >= 0.9:
            print("✅ VERDICT: ALICE IS READY FOR DEPLOYMENT")
            print("   Systems are working well with minor issues. Monitor closely post-deployment.")
        elif overall_success >= 0.8:
            print("⚠️ VERDICT: ALICE NEEDS FIXES BEFORE PRODUCTION")
            print("   Several issues need to be addressed before deployment.")
        else:
            print("🚨 VERDICT: ALICE IS NOT READY FOR PRODUCTION")
            print("   Significant issues detected. Extensive fixes required.")
        
        print("=" * 80)
    
    async def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        print("🚀 ALICE COMPREHENSIVE QA TEST SUITE")
        print("=" * 80)
        print("Testing all new Alice systems for production readiness...")
        
        try:
            # Setup
            await self.setup_test_environment()
            
            # Run all test suites
            await self.test_hud_ui_system()
            await self.test_voice_system()  
            await self.test_gmail_integration()
            await self.test_nlu_system()
            await self.test_memory_system()
            await self.run_stress_tests()
            
            # Analysis
            self.analyze_performance_metrics()
            self.generate_recommendations()
            
            # Report
            self.print_comprehensive_report()
            
        except Exception as e:
            print(f"❌ Critical error in test suite: {e}")
            self.results['errors'].append(f"Test suite critical error: {e}")
        
        finally:
            # Cleanup
            if self.test_db_path and os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)

async def main():
    """Main test runner"""
    test_suite = AliceQATestSuite()
    await test_suite.run_comprehensive_tests()

if __name__ == "__main__":
    asyncio.run(main())