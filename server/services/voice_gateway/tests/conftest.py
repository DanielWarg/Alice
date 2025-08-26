#!/usr/bin/env python3
"""
🔧 Pytest Configuration and Shared Fixtures
Test setup, Redis mocking, and common test utilities
"""
import pytest
import asyncio
import os
import sys
from unittest.mock import AsyncMock, Mock

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def mock_redis():
    """Mock Redis connection for testing"""
    redis = AsyncMock()
    
    # Mock common Redis operations
    redis.hset = AsyncMock()
    redis.hget = AsyncMock(return_value="false")
    redis.expire = AsyncMock()
    redis.delete = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    
    # Mock hash operations for session state
    redis.hgetall = AsyncMock(return_value={"tts_active": "false", "session_active": "true"})
    
    return redis

@pytest.fixture
def sample_sdp_offer():
    """Standard SDP offer for testing"""
    return """v=0
o=- 4611731400430051336 2 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0
a=extmap-allow-mixed
a=msid-semantic: WMS
m=audio 9 UDP/TLS/RTP/SAVPF 111 63 103 104 9 0 8 106 105 13 110 112 113 126
c=IN IP4 0.0.0.0
a=rtcp:9 IN IP4 0.0.0.0
a=ice-ufrag:4ZcD
a=ice-pwd:2/1muCWoOi3ulifTESo2tjlh
a=ice-options:trickle
a=fingerprint:sha-256 75:74:5A:A6:A4:E5:52:F4:A7:67:4C:01:C7:EE:91:3F:21:3D:A2:E3:53:7B:6F:30:86:F2:30:FF:A6:22:D2:04
a=setup:actpass
a=mid:0
a=extmap:1 urn:ietf:params:rtp-hdrext:ssrc-audio-level
a=extmap:2 http://www.webrtc.org/experiments/rtp-hdrext/abs-send-time
a=extmap:3 http://www.ietf.org/id/draft-holmer-rmcat-transport-wide-cc-extensions-01
a=extmap:4 urn:ietf:params:rtp-hdrext:sdes:mid
a=extmap:5 urn:ietf:params:rtp-hdrext:sdes:rtp-stream-id
a=extmap:6 urn:ietf:params:rtp-hdrext:sdes:repaired-rtp-stream-id
a=sendrecv
a=msid:- {550e8400-e29b-41d4-a716-446655440000}
a=rtcp-mux
a=rtpmap:111 opus/48000/2
a=rtcp-fb:111 transport-cc
a=fmtp:111 minptime=10;useinbandfec=1
a=rtpmap:63 red/48000/2
a=fmtp:63 111/111
a=rtpmap:103 ISAC/16000
a=rtpmap:104 ISAC/32000
a=rtpmap:9 G722/8000
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:106 CN/32000
a=rtpmap:105 CN/16000
a=rtpmap:13 CN/8000
a=rtpmap:110 telephone-event/48000
a=rtpmap:112 telephone-event/32000
a=rtpmap:113 telephone-event/16000
a=rtpmap:126 telephone-event/8000
a=ssrc:550e8400 cname:{550e8400-e29b-41d4-a716-446655440001}
a=ssrc:550e8400 msid:- {550e8400-e29b-41d4-a716-446655440000}
a=ssrc:550e8400 mslabel:-
a=ssrc:550e8400 label:{550e8400-e29b-41d4-a716-446655440000}"""

@pytest.fixture
def minimal_sdp_offer():
    """Minimal SDP offer for basic testing"""
    return """v=0
o=- 123456789 1 IN IP4 127.0.0.1
s=-
t=0 0
m=audio 9 RTP/AVP 0
a=sendrecv"""

# Test data constants
TEST_SESSION_ID = "pytest_session_001"
VOICE_GATEWAY_URL = "http://localhost:8001"

# Performance test thresholds (from LIVEKIT_VOICE_PLAN.md)
PERFORMANCE_TARGETS = {
    "webrtc_handshake_ms": 100,
    "ice_connection_ms": 3000,
    "first_audio_ms": 600,  # FAS 2 target
    "first_partial_ms": 300,  # FAS 3 target
    "barge_in_ms": 120,  # FAS 5 target
}

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", 
        "slow: mark test as slow running (>5s)"
    )
    config.addinivalue_line(
        "markers", 
        "integration: mark test as integration test requiring running services"
    )
    config.addinivalue_line(
        "markers", 
        "performance: mark test as performance/SLO validation test"
    )

def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on name patterns"""
    for item in items:
        # Mark integration tests
        if "integration" in item.name or "test_webrtc_manager" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Mark performance tests
        if "performance" in item.name or "slo" in item.name:
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)

@pytest.fixture
def performance_thresholds():
    """Performance test thresholds"""
    return PERFORMANCE_TARGETS.copy()

# Async test utilities
async def wait_for_condition(condition_func, timeout=10.0, interval=0.1):
    """Wait for a condition to become true with timeout"""
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < timeout:
        if await condition_func():
            return True
        await asyncio.sleep(interval)
    return False