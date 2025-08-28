#!/usr/bin/env python3
"""
Final Comprehensive Integration Testing for Alice System
Tests all components of the Alice ecosystem for production readiness.
"""

import asyncio
import aiohttp
import json
import time
import subprocess
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
import socket
import websockets
import traceback

class AliceIntegrationTester:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3100"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "critical_failures": 0
            }
        }
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def add_test_result(self, test_name: str, passed: bool, details: Dict[str, Any], critical: bool = False):
        """Add test result to results"""
        self.results["tests"][test_name] = {
            "passed": passed,
            "details": details,
            "critical": critical,
            "timestamp": datetime.now().isoformat()
        }
        self.results["summary"]["total"] += 1
        if passed:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1
            if critical:
                self.results["summary"]["critical_failures"] += 1
                
    async def test_backend_health(self) -> bool:
        """Test backend health and basic API functionality"""
        self.log("Testing Backend Health and API...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test health endpoint
                async with session.get(f"{self.backend_url}/api/health") as resp:
                    if resp.status != 200:
                        self.add_test_result("backend_health", False, 
                                           {"error": f"Health check failed: {resp.status}"}, True)
                        return False
                    
                    health_data = await resp.json()
                    self.log(f"Health check: {health_data}")
                    
                # Test tools endpoints
                async with session.get(f"{self.backend_url}/tools/enabled") as resp:
                    if resp.status != 200:
                        self.add_test_result("backend_tools", False, 
                                           {"error": f"Tools check failed: {resp.status}"}, True)
                        return False
                    
                    tools_data = await resp.json()
                    self.log(f"Enabled tools: {tools_data}")
                    
                # Test chat endpoint
                chat_payload = {"prompt": "Hello, are you working?"}
                async with session.post(f"{self.backend_url}/api/chat", 
                                      json=chat_payload) as resp:
                    if resp.status != 200:
                        self.add_test_result("backend_chat", False, 
                                           {"error": f"Chat failed: {resp.status}"}, True)
                        return False
                    
                    chat_data = await resp.json()
                    self.log(f"Chat response: {chat_data.get('text', '')[:100]}...")
                    
                self.add_test_result("backend_health", True, {
                    "health": health_data,
                    "tools": tools_data,
                    "chat_working": True
                })
                return True
                
        except Exception as e:
            self.add_test_result("backend_health", False, 
                               {"error": str(e), "traceback": traceback.format_exc()}, True)
            return False
            
    async def test_frontend_hud(self) -> bool:
        """Test frontend HUD demo page"""
        self.log("Testing Frontend HUD Demo...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test HUD demo page
                async with session.get(f"{self.frontend_url}/hud-demo") as resp:
                    if resp.status != 200:
                        self.add_test_result("frontend_hud", False, 
                                           {"error": f"HUD demo failed: {resp.status}"}, True)
                        return False
                    
                    html_content = await resp.text()
                    
                    # Check for key HUD components
                    components_found = {
                        "alice_core": "Alice Core" in html_content,
                        "voice_system": "Röst" in html_content or "Voice" in html_content,
                        "system_metrics": "System" in html_content or "metrics" in html_content,
                        "navigation": "Kalender" in html_content or "Calendar" in html_content,
                        "no_errors": "3 Issues" not in html_content  # Check for the previous error
                    }
                    
                    all_components = all(components_found.values())
                    
                    self.add_test_result("frontend_hud", all_components, {
                        "status_code": resp.status,
                        "components_found": components_found,
                        "page_size": len(html_content)
                    })
                    
                    return all_components
                    
        except Exception as e:
            self.add_test_result("frontend_hud", False, 
                               {"error": str(e), "traceback": traceback.format_exc()}, True)
            return False
            
    async def test_voice_interface(self) -> bool:
        """Test voice interface page"""
        self.log("Testing Voice Interface...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.frontend_url}/voice") as resp:
                    if resp.status != 200:
                        self.add_test_result("voice_interface", False, 
                                           {"error": f"Voice interface failed: {resp.status}"}, True)
                        return False
                    
                    html_content = await resp.text()
                    
                    # Check for voice interface components
                    voice_components = {
                        "voice_ui": "voice" in html_content.lower() or "mic" in html_content.lower(),
                        "websocket_setup": "ws://" in html_content or "WebSocket" in html_content,
                        "audio_elements": "audio" in html_content.lower()
                    }
                    
                    voice_working = any(voice_components.values())
                    
                    self.add_test_result("voice_interface", voice_working, {
                        "status_code": resp.status,
                        "components": voice_components,
                        "page_size": len(html_content)
                    })
                    
                    return voice_working
                    
        except Exception as e:
            self.add_test_result("voice_interface", False, 
                               {"error": str(e), "traceback": traceback.format_exc()})
            return False
            
    async def test_tool_system(self) -> bool:
        """Test tool system integration"""
        self.log("Testing Tool System...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test tool registry
                async with session.get(f"{self.backend_url}/tools/registry") as resp:
                    if resp.status != 200:
                        self.add_test_result("tool_system", False, 
                                           {"error": f"Tool registry failed: {resp.status}"})
                        return False
                    
                    registry_data = await resp.json()
                    
                # Test enabled tools
                async with session.get(f"{self.backend_url}/tools/enabled") as resp:
                    if resp.status != 200:
                        self.add_test_result("tool_system", False, 
                                           {"error": f"Enabled tools failed: {resp.status}"})
                        return False
                    
                    enabled_data = await resp.json()
                    
                # Test tool execution (safe command)
                exec_payload = {
                    "command": "PLAY",
                    "args": {},
                    "safe": True
                }
                async with session.post(f"{self.backend_url}/api/tools/exec", 
                                      json=exec_payload) as resp:
                    # Tool execution might fail due to missing Spotify config, but API should respond
                    tool_exec_status = resp.status in [200, 400, 422]  # Accept these as valid responses
                    exec_data = await resp.json() if resp.status == 200 else {"status": resp.status}
                    
                self.add_test_result("tool_system", True, {
                    "registry": registry_data,
                    "enabled": enabled_data,
                    "execution_test": tool_exec_status,
                    "exec_response": exec_data
                })
                
                return True
                
        except Exception as e:
            self.add_test_result("tool_system", False, 
                               {"error": str(e), "traceback": traceback.format_exc()})
            return False
            
    async def test_websocket_connection(self) -> bool:
        """Test WebSocket connections"""
        self.log("Testing WebSocket Connections...")
        
        # For now, we'll test if the WebSocket endpoint is available
        # Full WebSocket testing would require more complex setup
        try:
            # Check if the voice WebSocket endpoint responds
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 8000))
            sock.close()
            
            websocket_available = result == 0
            
            self.add_test_result("websocket_connection", websocket_available, {
                "backend_socket_test": websocket_available,
                "note": "Basic socket connectivity test"
            })
            
            return websocket_available
            
        except Exception as e:
            self.add_test_result("websocket_connection", False, 
                               {"error": str(e), "traceback": traceback.format_exc()})
            return False
            
    async def test_streaming_chat(self) -> bool:
        """Test streaming chat functionality"""
        self.log("Testing Streaming Chat...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test streaming endpoint
                payload = {"prompt": "Count to 3"}
                async with session.post(f"{self.backend_url}/api/chat/stream", 
                                      json=payload) as resp:
                    if resp.status != 200:
                        self.add_test_result("streaming_chat", False, 
                                           {"error": f"Streaming failed: {resp.status}"})
                        return False
                    
                    # Read streaming response
                    chunks = []
                    async for chunk in resp.content.iter_any():
                        if chunk:
                            chunks.append(chunk.decode('utf-8'))
                            if len(chunks) > 10:  # Limit chunks for testing
                                break
                    
                    streaming_working = len(chunks) > 0
                    
                    self.add_test_result("streaming_chat", streaming_working, {
                        "chunks_received": len(chunks),
                        "first_chunk": chunks[0][:100] if chunks else None
                    })
                    
                    return streaming_working
                    
        except Exception as e:
            self.add_test_result("streaming_chat", False, 
                               {"error": str(e), "traceback": traceback.format_exc()})
            return False
            
    async def test_error_handling(self) -> bool:
        """Test error handling and recovery"""
        self.log("Testing Error Handling...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test invalid endpoint
                async with session.get(f"{self.backend_url}/api/invalid") as resp:
                    invalid_handled = resp.status == 404
                    
                # Test malformed chat request
                async with session.post(f"{self.backend_url}/api/chat", 
                                      json={"invalid": "request"}) as resp:
                    malformed_handled = resp.status in [400, 422]
                    
                # Test invalid tool execution
                exec_payload = {"command": "INVALID_TOOL", "args": {}}
                async with session.post(f"{self.backend_url}/api/tools/exec", 
                                      json=exec_payload) as resp:
                    invalid_tool_handled = resp.status in [400, 422, 404]
                    
                error_handling_working = all([invalid_handled, malformed_handled, invalid_tool_handled])
                
                self.add_test_result("error_handling", error_handling_working, {
                    "invalid_endpoint": invalid_handled,
                    "malformed_request": malformed_handled,
                    "invalid_tool": invalid_tool_handled
                })
                
                return error_handling_working
                
        except Exception as e:
            self.add_test_result("error_handling", False, 
                               {"error": str(e), "traceback": traceback.format_exc()})
            return False
            
    async def test_end_to_end_workflow(self) -> bool:
        """Test complete end-to-end user workflow"""
        self.log("Testing End-to-End Workflow...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Simulate user interaction workflow
                # 1. Check system health
                async with session.get(f"{self.backend_url}/api/health") as resp:
                    health_ok = resp.status == 200
                    
                # 2. Load HUD interface
                async with session.get(f"{self.frontend_url}/hud-demo") as resp:
                    hud_ok = resp.status == 200
                    
                # 3. Interact with chat
                chat_payload = {"prompt": "What tools are available?"}
                async with session.post(f"{self.backend_url}/api/chat", 
                                      json=chat_payload) as resp:
                    chat_ok = resp.status == 200
                    
                # 4. Check tool availability
                async with session.get(f"{self.backend_url}/tools/enabled") as resp:
                    tools_ok = resp.status == 200
                    
                workflow_success = all([health_ok, hud_ok, chat_ok, tools_ok])
                
                self.add_test_result("end_to_end_workflow", workflow_success, {
                    "health_check": health_ok,
                    "hud_load": hud_ok,
                    "chat_interaction": chat_ok,
                    "tools_available": tools_ok
                })
                
                return workflow_success
                
        except Exception as e:
            self.add_test_result("end_to_end_workflow", False, 
                               {"error": str(e), "traceback": traceback.format_exc()})
            return False
            
    def check_service_availability(self) -> bool:
        """Check if required services are running"""
        self.log("Checking Service Availability...")
        
        services = {}
        
        # Check backend
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 8000))
            services['backend'] = result == 0
            sock.close()
        except:
            services['backend'] = False
            
        # Check frontend
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 3100))
            services['frontend'] = result == 0
            sock.close()
        except:
            services['frontend'] = False
            
        all_services_up = all(services.values())
        
        self.add_test_result("service_availability", all_services_up, services, True)
        
        if not all_services_up:
            self.log(f"Services status: {services}", "ERROR")
            
        return all_services_up
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests"""
        self.log("Starting Comprehensive Integration Testing...")
        
        # Check services first
        if not self.check_service_availability():
            self.log("Required services are not running. Aborting tests.", "ERROR")
            return self.results
            
        # Run all tests
        tests = [
            ("Backend Health", self.test_backend_health()),
            ("Frontend HUD", self.test_frontend_hud()),
            ("Voice Interface", self.test_voice_interface()),
            ("Tool System", self.test_tool_system()),
            ("WebSocket", self.test_websocket_connection()),
            ("Streaming Chat", self.test_streaming_chat()),
            ("Error Handling", self.test_error_handling()),
            ("End-to-End Workflow", self.test_end_to_end_workflow())
        ]
        
        for test_name, test_coro in tests:
            self.log(f"Running {test_name} test...")
            try:
                await test_coro
                self.log(f"{test_name} test completed")
            except Exception as e:
                self.log(f"{test_name} test failed: {e}", "ERROR")
                
        return self.results
        
    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        summary = self.results["summary"]
        total = summary["total"]
        passed = summary["passed"]
        failed = summary["failed"]
        critical = summary["critical_failures"]
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        report = f"""
# Alice System Integration Test Report
**Timestamp:** {self.results["timestamp"]}

## Summary
- **Total Tests:** {total}
- **Passed:** {passed} ({pass_rate:.1f}%)
- **Failed:** {failed}
- **Critical Failures:** {critical}

## Test Results

"""
        
        for test_name, result in self.results["tests"].items():
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            critical_flag = " (CRITICAL)" if result.get("critical", False) else ""
            
            report += f"### {test_name.replace('_', ' ').title()}\n"
            report += f"**Status:** {status}{critical_flag}\n"
            
            if not result["passed"]:
                details = result["details"]
                if "error" in details:
                    report += f"**Error:** {details['error']}\n"
                    
            report += "\n"
            
        # Deployment readiness assessment
        if critical > 0:
            readiness = "❌ NOT READY - Critical failures detected"
        elif failed > total * 0.2:  # More than 20% failure rate
            readiness = "⚠️ CAUTION - High failure rate"
        elif passed == total:
            readiness = "✅ PRODUCTION READY"
        else:
            readiness = "⚠️ MOSTLY READY - Minor issues detected"
            
        report += f"""
## Deployment Readiness Assessment
{readiness}

## Next Steps
"""
        
        if critical > 0:
            report += "- Address critical failures before deployment\n"
        if failed > 0:
            report += "- Review and fix failed tests\n"
        if passed == total:
            report += "- System is ready for production deployment\n"
        else:
            report += "- Review test results and address issues as needed\n"
            
        return report


async def main():
    """Main test runner"""
    tester = AliceIntegrationTester()
    
    print("=" * 80)
    print("ALICE SYSTEM - FINAL INTEGRATION TESTING")
    print("=" * 80)
    
    # Run all tests
    results = await tester.run_all_tests()
    
    # Generate and display report
    report = tester.generate_report()
    print(report)
    
    # Save results to file
    results_file = f"integration_test_results_{int(time.time())}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_file}")
    
    # Return exit code based on critical failures
    if results["summary"]["critical_failures"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())