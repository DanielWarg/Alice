#!/usr/bin/env python3
"""
🔒 Privacy Leak Test Suite - CRITICAL FOR DEPLOYMENT
Tests that PII never reaches OpenAI Realtime API endpoint
Must be 100% green before production deployment
"""
import asyncio
import json
import logging
import time
from typing import Dict, List, Any
import aiohttp
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from network_guard import get_network_guard, GuardDecision, ViolationType
from privacy_filter import PrivacyFilter
from llm_router import get_llm_router, RouteType
from tool_lane_stub import ToolLane

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockNetworkMonitor:
    """Mock network monitor to track outbound requests"""
    
    def __init__(self):
        self.outbound_requests = []
        self.blocked_requests = []
        self.realtime_requests = []
    
    def log_request(self, url: str, data: Any, headers: Dict):
        """Log outbound request"""
        request_info = {
            'timestamp': time.time(),
            'url': url,
            'data': data,
            'headers': headers,
            'is_realtime': 'api.openai.com' in url and 'realtime' in url.lower()
        }
        
        self.outbound_requests.append(request_info)
        
        if request_info['is_realtime']:
            self.realtime_requests.append(request_info)
    
    def get_realtime_content(self) -> List[str]:
        """Get all content sent to Realtime API"""
        content_list = []
        
        for req in self.realtime_requests:
            if isinstance(req['data'], dict):
                content_list.append(json.dumps(req['data']))
            else:
                content_list.append(str(req['data']))
        
        return content_list
    
    def reset(self):
        """Reset monitoring"""
        self.outbound_requests.clear()
        self.blocked_requests.clear()
        self.realtime_requests.clear()

class PrivacyLeakTester:
    """Comprehensive privacy leak testing"""
    
    def __init__(self):
        self.network_monitor = MockNetworkMonitor()
        self.guard = get_network_guard()
        self.privacy_filter = PrivacyFilter()
        self.router = get_llm_router()
        self.tool_lane = ToolLane()
        
        # Reset metrics for clean test
        self.guard.reset_metrics()
        
        # Test data with various PII types
        self.pii_test_cases = [
            {
                "name": "Email and Name",
                "input": "Send email to john.smith@example.com about the meeting with Maria Johnson",
                "pii_types": ["email", "name"],
                "expected_violation": ViolationType.PII_DETECTED
            },
            {
                "name": "Phone Number",
                "input": "Call me at 555-123-4567 or +1-555-987-6543",
                "pii_types": ["phone"],
                "expected_violation": ViolationType.PII_DETECTED
            },
            {
                "name": "File Path",
                "input": "Read the document at /Users/john/Documents/private/financial_report.pdf",
                "pii_types": ["file_path"],
                "expected_violation": ViolationType.PII_DETECTED
            },
            {
                "name": "Credit Card-like Number",
                "input": "The number is 4532-1234-5678-9012",
                "pii_types": ["credit_card"],
                "expected_violation": ViolationType.PII_DETECTED
            },
            {
                "name": "Raw Email Data",
                "input": "Email from: maria.andersson@company.se\nSubject: Quarterly Results\nBody: Revenue increased by 15%...",
                "pii_types": ["email", "raw_data"],
                "expected_violation": ViolationType.PII_DETECTED
            },
            {
                "name": "Tool Function Call",
                "input": json.dumps({
                    "function_call": {
                        "name": "read_email",
                        "arguments": {"from": "boss@company.com", "after": "2024-01-01"}
                    }
                }),
                "pii_types": ["function_args"],
                "expected_violation": ViolationType.FUNCTION_ARGUMENTS
            },
            {
                "name": "no_cloud Flag",
                "input": json.dumps({
                    "type": "tool_result",
                    "content": "Private calendar data here",
                    "no_cloud": True
                }),
                "pii_types": ["no_cloud"],
                "expected_violation": ViolationType.NO_CLOUD_FLAG
            },
            {
                "name": "Calendar Data with Personal Info",
                "input": "Meeting with Dr. Lisa Peterson at Stockholm Health Center, room 204B, regarding medical consultation",
                "pii_types": ["name", "medical"],
                "expected_violation": ViolationType.PII_DETECTED
            },
            {
                "name": "Mixed Swedish/English with PII",
                "input": "Skicka mejl till erik.larsson@teknikfirma.se om projektmötet imorgon",
                "pii_types": ["email", "swedish"],
                "expected_violation": ViolationType.PII_DETECTED
            },
            {
                "name": "Bank Account Info",
                "input": "Transfer to account 123-456-789 at Swedbank, reference number 98765",
                "pii_types": ["bank", "account"],
                "expected_violation": ViolationType.PII_DETECTED
            },
            {
                "name": "IP Address and System Info",
                "input": "Connect to server 192.168.1.100, user admin, location /home/user/.ssh/",
                "pii_types": ["ip", "system"],
                "expected_violation": ViolationType.PII_DETECTED
            },
            {
                "name": "Raw Document Content", 
                "input": "Document excerpt: Contract between ABC Corp and John Smith, employee ID 12345, salary $85,000, start date Jan 15, 2024, SSN 123-45-6789",
                "pii_types": ["document", "ssn", "salary"],
                "expected_violation": ViolationType.PII_DETECTED
            }
        ]
        
        # Safe test cases that should pass
        self.safe_test_cases = [
            "What time is it?",
            "How is the weather today?", 
            "Tell me a joke",
            "What's 25 + 17?",
            "Explain quantum physics briefly",
            "I found some information about your request",
            "There are several items in your inbox",
            "The meeting is scheduled for tomorrow"
        ]
        
    async def run_complete_leak_test_suite(self):
        """Run the complete privacy leak test suite"""
        
        logger.info("🔒 Starting CRITICAL Privacy Leak Test Suite")
        logger.info("=" * 70)
        
        results = {
            'pii_blocks': [],
            'safe_passes': [],
            'routing_tests': [],
            'filter_tests': [],
            'network_guard_tests': [],
            'integration_tests': []
        }
        
        # Test 1: PII Detection and Blocking
        logger.info("🚫 Test 1: PII Detection and Blocking")
        logger.info("-" * 50)
        
        pii_pass_count = 0
        for test_case in self.pii_test_cases:
            logger.info(f"Testing: {test_case['name']}")
            
            # Check network guard
            guard_result = self.guard.check_outbound_message(test_case['input'], "realtime")
            
            if guard_result.decision == GuardDecision.BLOCK:
                logger.info(f"  ✅ BLOCKED: {guard_result.reason}")
                pii_pass_count += 1
                results['pii_blocks'].append({
                    'name': test_case['name'],
                    'status': 'PASS',
                    'violation_type': guard_result.violation_type.value if guard_result.violation_type else None
                })
            else:
                logger.error(f"  ❌ FAILED: Content was NOT blocked!")
                results['pii_blocks'].append({
                    'name': test_case['name'], 
                    'status': 'FAIL',
                    'reason': 'PII content was not blocked'
                })
        
        logger.info(f"PII Blocking: {pii_pass_count}/{len(self.pii_test_cases)} tests passed")
        
        # Test 2: Safe Content Passes
        logger.info("\n✅ Test 2: Safe Content Passes")
        logger.info("-" * 50)
        
        safe_pass_count = 0
        for safe_content in self.safe_test_cases:
            guard_result = self.guard.check_outbound_message(safe_content, "realtime")
            
            if guard_result.decision == GuardDecision.ALLOW:
                logger.info(f"  ✅ ALLOWED: '{safe_content[:30]}...'")
                safe_pass_count += 1
                results['safe_passes'].append({'content': safe_content, 'status': 'PASS'})
            else:
                logger.warning(f"  ⚠️ BLOCKED: '{safe_content[:30]}...' - {guard_result.reason}")
                results['safe_passes'].append({
                    'content': safe_content,
                    'status': 'BLOCKED', 
                    'reason': guard_result.reason
                })
        
        logger.info(f"Safe Content: {safe_pass_count}/{len(self.safe_test_cases)} tests passed")
        
        # Test 3: Routing Privacy
        logger.info("\n🔀 Test 3: Routing Privacy Enforcement")  
        logger.info("-" * 50)
        
        routing_pass_count = 0
        for test_case in self.pii_test_cases[:5]:  # Test subset
            route_decision = self.router.route_request(test_case['input'])
            
            # Private content should be routed locally with no_cloud=True
            if route_decision.route == RouteType.LOCAL and route_decision.no_cloud:
                logger.info(f"  ✅ ROUTED LOCAL: {test_case['name']}")
                routing_pass_count += 1
                results['routing_tests'].append({
                    'name': test_case['name'],
                    'route': route_decision.route.value,
                    'no_cloud': route_decision.no_cloud,
                    'status': 'PASS'
                })
            else:
                logger.error(f"  ❌ ROUTING FAIL: {test_case['name']} - Route: {route_decision.route.value}, no_cloud: {route_decision.no_cloud}")
                results['routing_tests'].append({
                    'name': test_case['name'],
                    'route': route_decision.route.value, 
                    'no_cloud': route_decision.no_cloud,
                    'status': 'FAIL'
                })
        
        logger.info(f"Routing Privacy: {routing_pass_count}/{min(5, len(self.pii_test_cases))} tests passed")
        
        # Test 4: Privacy Filter
        logger.info("\n🔒 Test 4: Privacy Filter Safe Summary")
        logger.info("-" * 50)
        
        filter_pass_count = 0
        raw_results = [
            "Email from john.doe@company.com: Meeting scheduled for tomorrow at 2 PM in room 304",
            "Calendar shows 3 meetings: 9 AM with Sarah Johnson (555-1234), 11 AM budget review, 3 PM project sync",  
            "Document contains salary information: John Smith - $95,000, Maria Garcia - $87,500",
            "Contact search found: Dr. Lisa Peterson, phone 555-9876, email lisa.p@clinic.com"
        ]
        
        for i, raw_result in enumerate(raw_results):
            try:
                safe_summary = await self.privacy_filter.create_safe_summary(raw_result)
                
                # Check that safe summary has no PII
                guard_check = self.guard.check_outbound_message(safe_summary, "realtime")
                
                if guard_check.decision == GuardDecision.ALLOW and len(safe_summary) <= 300:
                    logger.info(f"  ✅ FILTERED: '{safe_summary}'")
                    filter_pass_count += 1
                    results['filter_tests'].append({
                        'input_length': len(raw_result),
                        'output_length': len(safe_summary), 
                        'guard_decision': guard_check.decision.value,
                        'status': 'PASS'
                    })
                else:
                    logger.error(f"  ❌ FILTER FAIL: '{safe_summary}' - Decision: {guard_check.decision.value}")
                    results['filter_tests'].append({
                        'input_length': len(raw_result),
                        'output_length': len(safe_summary),
                        'guard_decision': guard_check.decision.value,
                        'status': 'FAIL'
                    })
                    
            except Exception as e:
                logger.error(f"  ❌ FILTER ERROR: {e}")
                results['filter_tests'].append({
                    'error': str(e),
                    'status': 'ERROR'
                })
        
        logger.info(f"Privacy Filter: {filter_pass_count}/{len(raw_results)} tests passed")
        
        # Test 5: End-to-End Integration
        logger.info("\n🔄 Test 5: End-to-End Integration Test")
        logger.info("-" * 50)
        
        integration_pass_count = 0
        
        # Test private email request
        private_request = "Show me emails from john.smith@company.com about the budget"
        
        try:
            # 1. Route the request
            route_decision = self.router.route_request(private_request)
            
            # 2. Should be routed to local tool lane
            if route_decision.route == RouteType.LOCAL and route_decision.no_cloud:
                logger.info(f"  ✅ Step 1: Routed to local ({route_decision.intent.value})")
                
                # 3. Process with tool lane
                tool_result = await self.tool_lane.process_request(
                    private_request,
                    {"no_cloud": True, "intent": route_decision.intent.value}
                )
                
                if tool_result and tool_result.get('no_cloud', False):
                    logger.info(f"  ✅ Step 2: Tool lane processed with no_cloud=True")
                    
                    # 4. Create safe summary
                    raw_result = tool_result.get('result', 'No result')
                    safe_summary = await self.privacy_filter.create_safe_summary(raw_result)
                    
                    # 5. Final guard check
                    final_check = self.guard.check_outbound_message(safe_summary, "realtime")
                    
                    if final_check.decision == GuardDecision.ALLOW:
                        logger.info(f"  ✅ Step 3: Safe summary passed final check: '{safe_summary}'")
                        integration_pass_count += 1
                        results['integration_tests'].append({
                            'request': private_request,
                            'route': route_decision.route.value,
                            'safe_summary': safe_summary,
                            'status': 'PASS'
                        })
                    else:
                        logger.error(f"  ❌ Step 3: Safe summary failed final check")
                        results['integration_tests'].append({
                            'request': private_request,
                            'error': 'Safe summary failed final check',
                            'status': 'FAIL'
                        })
                else:
                    logger.error(f"  ❌ Step 2: Tool lane result missing no_cloud flag")
                    results['integration_tests'].append({
                        'request': private_request,
                        'error': 'Tool result missing no_cloud flag',
                        'status': 'FAIL'
                    })
            else:
                logger.error(f"  ❌ Step 1: Private request not routed locally")
                results['integration_tests'].append({
                    'request': private_request,
                    'error': f'Routed to {route_decision.route.value}, no_cloud={route_decision.no_cloud}',
                    'status': 'FAIL'
                })
                
        except Exception as e:
            logger.error(f"  ❌ Integration test error: {e}")
            results['integration_tests'].append({
                'request': private_request,
                'error': str(e),
                'status': 'ERROR'
            })
        
        logger.info(f"Integration: {integration_pass_count}/1 tests passed")
        
        # Final Results
        logger.info("\n" + "=" * 70)
        logger.info("🎯 PRIVACY LEAK TEST RESULTS")
        logger.info("=" * 70)
        
        total_tests = (len(self.pii_test_cases) + len(self.safe_test_cases) + 
                      min(5, len(self.pii_test_cases)) + len(raw_results) + 1)
        passed_tests = (pii_pass_count + safe_pass_count + routing_pass_count + 
                       filter_pass_count + integration_pass_count)
        
        logger.info(f"📊 Overall Score: {passed_tests}/{total_tests} tests passed")
        logger.info(f"🚫 PII Blocking: {pii_pass_count}/{len(self.pii_test_cases)} ({'PASS' if pii_pass_count == len(self.pii_test_cases) else 'FAIL'})")
        logger.info(f"✅ Safe Content: {safe_pass_count}/{len(self.safe_test_cases)} ({'PASS' if safe_pass_count >= len(self.safe_test_cases) * 0.9 else 'FAIL'})")
        logger.info(f"🔀 Routing Privacy: {routing_pass_count}/{min(5, len(self.pii_test_cases))} ({'PASS' if routing_pass_count == min(5, len(self.pii_test_cases)) else 'FAIL'})")
        logger.info(f"🔒 Privacy Filter: {filter_pass_count}/{len(raw_results)} ({'PASS' if filter_pass_count == len(raw_results) else 'FAIL'})")
        logger.info(f"🔄 Integration: {integration_pass_count}/1 ({'PASS' if integration_pass_count == 1 else 'FAIL'})")
        
        # Guard metrics
        metrics = self.guard.get_metrics()
        logger.info(f"\n📈 Network Guard Metrics:")
        logger.info(f"   Privacy leak attempts: {metrics.get('privacy_leak_attempts', 0)}")
        logger.info(f"   Block rate: {metrics.get('block_rate', 0):.1f}%") 
        logger.info(f"   Total violations: {sum(metrics.get('violation_types', {}).values())}")
        
        # Critical check: ZERO privacy leak attempts should reach production
        critical_pass = (pii_pass_count == len(self.pii_test_cases) and 
                        routing_pass_count == min(5, len(self.pii_test_cases)) and
                        filter_pass_count == len(raw_results) and
                        integration_pass_count == 1)
        
        if critical_pass:
            logger.info("\n🎉 ✅ PRIVACY LEAK TEST SUITE: PASS")
            logger.info("   🚀 DEPLOYMENT APPROVED - No privacy leaks detected")
            logger.info("   🛡️ All PII successfully blocked from cloud transmission")
        else:
            logger.error("\n💥 ❌ PRIVACY LEAK TEST SUITE: FAIL") 
            logger.error("   🚫 DEPLOYMENT BLOCKED - Privacy violations detected")
            logger.error("   ⚠️ Fix all privacy issues before deployment")
            
        results['overall'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'critical_pass': critical_pass,
            'deployment_approved': critical_pass
        }
        
        return results

async def run_leak_tests():
    """Run the privacy leak test suite"""
    tester = PrivacyLeakTester()
    return await tester.run_complete_leak_test_suite()

if __name__ == "__main__":
    asyncio.run(run_leak_tests())