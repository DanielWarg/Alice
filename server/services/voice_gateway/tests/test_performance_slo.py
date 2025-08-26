#!/usr/bin/env python3
"""
⚡ Performance SLO Validation Tests
Ensures WebRTC system meets LiveKit-class performance targets
"""
import pytest
import asyncio
import time
import json
import statistics
from typing import List, Dict
import aiohttp
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class PerformanceMetrics:
    """Collect and analyze performance metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {
            "webrtc_handshake_ms": [],
            "ice_connection_ms": [],
            "first_audio_ms": [],
            "session_cleanup_ms": []
        }
    
    def record(self, metric: str, value: float):
        """Record a metric value"""
        if metric in self.metrics:
            self.metrics[metric].append(value)
    
    def get_stats(self, metric: str) -> Dict:
        """Get statistics for a metric"""
        values = self.metrics[metric]
        if not values:
            return {"count": 0}
        
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p95": sorted(values)[int(len(values) * 0.95)] if len(values) > 1 else values[0],
            "p99": sorted(values)[int(len(values) * 0.99)] if len(values) > 1 else values[0],
            "min": min(values),
            "max": max(values)
        }
    
    def export_report(self) -> Dict:
        """Export full performance report"""
        return {metric: self.get_stats(metric) for metric in self.metrics.keys()}

class TestPerformanceSLO:
    """Test WebRTC performance against SLO targets"""
    
    BASE_URL = "http://localhost:8001"
    
    # SLO Targets from LIVEKIT_VOICE_PLAN.md
    SLO_TARGETS = {
        "webrtc_handshake_ms": 100,    # <100ms
        "ice_connection_ms": 3000,     # <3000ms  
        "first_audio_ms": 600,         # <600ms (FAS 2 target)
        "session_cleanup_ms": 1000     # <1000ms (reasonable)
    }
    
    @pytest.fixture
    def metrics(self):
        return PerformanceMetrics()
    
    @pytest.mark.asyncio
    async def test_webrtc_handshake_performance(self, metrics):
        """Test WebRTC offer/answer handshake speed"""
        
        sample_offer = """v=0
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
        
        # Run multiple handshake tests
        for i in range(10):
            session_id = f"perf_test_{i:03d}"
            
            start_time = time.perf_counter()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}/api/webrtc/offer",
                    json={
                        "session_id": session_id,
                        "offer": sample_offer
                    }
                ) as response:
                    assert response.status == 200
                    result = await response.json()
                    assert "answer" in result
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            metrics.record("webrtc_handshake_ms", elapsed_ms)
            
            # Small delay between tests
            await asyncio.sleep(0.1)
        
        # Validate SLO
        stats = metrics.get_stats("webrtc_handshake_ms")
        target = self.SLO_TARGETS["webrtc_handshake_ms"]
        
        print(f"\\n🎯 WebRTC Handshake Performance:")
        print(f"   Mean: {stats['mean']:.1f}ms (target: <{target}ms)")
        print(f"   P95:  {stats['p95']:.1f}ms")
        print(f"   P99:  {stats['p99']:.1f}ms")
        
        # SLO validation
        assert stats["p95"] < target, f"P95 {stats['p95']:.1f}ms exceeds target {target}ms"
        assert stats["mean"] < target * 0.8, f"Mean {stats['mean']:.1f}ms should be <80% of target"
    
    @pytest.mark.asyncio
    async def test_concurrent_session_handling(self, metrics):
        """Test performance under concurrent session load"""
        
        async def create_session(session_id: str) -> float:
            """Create a single WebRTC session and measure time"""
            offer = "v=0\\no=- 123 1 IN IP4 127.0.0.1\\ns=-\\nt=0 0\\nm=audio 9 RTP/AVP 0"
            
            start_time = time.perf_counter()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}/api/webrtc/offer",
                    json={"session_id": session_id, "offer": offer}
                ) as response:
                    if response.status == 200:
                        await response.json()
            
            return (time.perf_counter() - start_time) * 1000
        
        # Create 20 concurrent sessions
        session_ids = [f"concurrent_{i:03d}" for i in range(20)]
        
        start_time = time.perf_counter()
        
        # Run concurrently
        tasks = [create_session(sid) for sid in session_ids]
        handshake_times = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        # Filter successful handshakes
        successful_times = [t for t in handshake_times if isinstance(t, (int, float))]
        
        print(f"\\n⚡ Concurrent Load Test:")
        print(f"   Total sessions: {len(session_ids)}")
        print(f"   Successful: {len(successful_times)}")
        print(f"   Total time: {total_time:.1f}ms")
        print(f"   Avg per session: {statistics.mean(successful_times):.1f}ms")
        
        # Record metrics
        for t in successful_times:
            metrics.record("webrtc_handshake_ms", t)
        
        # Validate concurrent performance doesn't degrade significantly
        if successful_times:
            avg_time = statistics.mean(successful_times)
            assert avg_time < self.SLO_TARGETS["webrtc_handshake_ms"] * 2, \
                f"Concurrent avg {avg_time:.1f}ms exceeds 2x target"
        
        assert len(successful_times) >= 18, "At least 90% of concurrent sessions should succeed"
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self):
        """Test for memory leaks during session creation/cleanup"""
        
        async def get_session_count() -> int:
            """Get active session count from API"""
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/api/webrtc/status") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("active_sessions", 0)
            return 0
        
        initial_sessions = await get_session_count()
        
        # Create and "abandon" 50 sessions (no proper cleanup)
        for i in range(50):
            session_id = f"leak_test_{i:03d}"
            offer = "v=0\\no=- 123 1 IN IP4 127.0.0.1\\ns=-\\nt=0 0"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}/api/webrtc/offer",
                    json={"session_id": session_id, "offer": offer}
                ) as response:
                    if response.status == 200:
                        await response.json()
        
        peak_sessions = await get_session_count()
        
        # Wait for cleanup task to run (30s cycle + buffer)
        print(f"\\n🧹 Waiting for cleanup cycle...")
        await asyncio.sleep(35)
        
        final_sessions = await get_session_count()
        
        print(f"\\n🔍 Memory Leak Detection:")
        print(f"   Initial sessions: {initial_sessions}")
        print(f"   Peak sessions: {peak_sessions}")
        print(f"   Final sessions: {final_sessions}")
        print(f"   Sessions cleaned: {peak_sessions - final_sessions}")
        
        # Validate cleanup effectiveness
        cleanup_ratio = (peak_sessions - final_sessions) / max(peak_sessions - initial_sessions, 1)
        
        assert cleanup_ratio > 0.8, f"Cleanup ratio {cleanup_ratio:.2f} indicates memory leak"
        assert final_sessions <= initial_sessions + 5, "Session count should return to baseline"
    
    @pytest.mark.asyncio 
    async def test_health_endpoint_performance(self, metrics):
        """Test health endpoint response time"""
        
        for i in range(10):
            start_time = time.perf_counter()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/health") as response:
                    assert response.status == 200
                    data = await response.json()
                    assert data["status"] == "healthy"
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            metrics.record("health_check_ms", elapsed_ms)
        
        stats = metrics.get_stats("health_check_ms")
        
        print(f"\\n💚 Health Check Performance:")
        print(f"   Mean: {stats['mean']:.1f}ms")
        print(f"   P95:  {stats['p95']:.1f}ms")
        
        # Health checks should be very fast
        assert stats["p95"] < 50, f"Health check P95 {stats['p95']:.1f}ms too slow"
    
    def test_generate_performance_report(self, metrics):
        """Generate and save performance report"""
        
        # This would run after other tests have populated metrics
        report = metrics.export_report()
        
        # Add SLO compliance check
        compliance = {}
        for metric, target in self.SLO_TARGETS.items():
            if metric in report and report[metric]["count"] > 0:
                p95_value = report[metric]["p95"]
                compliance[metric] = {
                    "target_ms": target,
                    "actual_p95_ms": p95_value,
                    "compliant": p95_value < target,
                    "margin_percent": ((target - p95_value) / target) * 100
                }
        
        report["slo_compliance"] = compliance
        report["test_timestamp"] = time.time()
        
        # Save report
        report_path = "performance_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\\n📊 Performance report saved: {report_path}")
        
        # Print compliance summary
        print(f"\\n📈 SLO Compliance Summary:")
        for metric, data in compliance.items():
            status = "✅" if data["compliant"] else "❌"
            print(f"   {status} {metric}: {data['actual_p95_ms']:.1f}ms (target: <{data['target_ms']}ms)")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])