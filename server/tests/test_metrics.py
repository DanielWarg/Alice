#!/usr/bin/env python3
"""
Test suite för metrics.py - Metriker och prestanda-uppföljning
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
from metrics import AliceMetrics


class TestAliceMetrics:
    """Test Alice metrics collection system"""
    
    def setup_method(self):
        """Setup fresh metrics instance for each test"""
        self.metrics = AliceMetrics()
        self.metrics.reset()  # Clear any existing data
    
    def test_metrics_initialization(self):
        """Test that metrics system initializes correctly"""
        assert self.metrics is not None
        assert hasattr(self.metrics, 'voice_latency_ms')
        assert hasattr(self.metrics, 'api_calls')
        assert hasattr(self.metrics, 'error_count')
        
    def test_record_voice_latency(self):
        """Test recording voice processing latency"""
        # Record some latency values
        self.metrics.record_voice_latency(150.5)
        self.metrics.record_voice_latency(200.0)
        self.metrics.record_voice_latency(175.2)
        
        # Check that values were recorded
        assert len(self.metrics.voice_latency_ms) == 3
        assert 150.5 in self.metrics.voice_latency_ms
        assert 200.0 in self.metrics.voice_latency_ms
        assert 175.2 in self.metrics.voice_latency_ms
        
    def test_record_api_call(self):
        """Test recording API call metrics"""
        # Record some API calls
        self.metrics.record_api_call("openai", 500, True)
        self.metrics.record_api_call("spotify", 200, True)
        self.metrics.record_api_call("google", 1000, False)
        
        # Check api_calls structure
        assert "openai" in self.metrics.api_calls
        assert "spotify" in self.metrics.api_calls
        assert "google" in self.metrics.api_calls
        
        # Check success/failure tracking
        assert self.metrics.api_calls["openai"]["success"] == 1
        assert self.metrics.api_calls["spotify"]["success"] == 1
        assert self.metrics.api_calls["google"]["success"] == 0
        assert self.metrics.api_calls["google"]["failure"] == 1
        
    def test_increment_error_count(self):
        """Test error counting functionality"""
        # Record some errors
        self.metrics.increment_error_count("tts_error")
        self.metrics.increment_error_count("api_timeout")
        self.metrics.increment_error_count("tts_error")  # Same error type again
        
        # Check error counts
        assert self.metrics.error_count["tts_error"] == 2
        assert self.metrics.error_count["api_timeout"] == 1
        
    def test_record_tool_execution(self):
        """Test tool execution metrics"""
        # Record tool executions
        self.metrics.record_tool_execution("PLAY", 100.5, True)
        self.metrics.record_tool_execution("PAUSE", 50.0, True)
        self.metrics.record_tool_execution("SET_VOLUME", 200.0, False)
        
        # Check tool metrics
        assert "PLAY" in self.metrics.tool_metrics
        assert self.metrics.tool_metrics["PLAY"]["avg_latency"] == 100.5
        assert self.metrics.tool_metrics["PLAY"]["success_count"] == 1
        
        assert "SET_VOLUME" in self.metrics.tool_metrics
        assert self.metrics.tool_metrics["SET_VOLUME"]["failure_count"] == 1
        
    def test_get_summary_statistics(self):
        """Test summary statistics generation"""
        # Add some test data
        self.metrics.record_voice_latency(100)
        self.metrics.record_voice_latency(200)
        self.metrics.record_voice_latency(150)
        
        self.metrics.record_api_call("test_api", 500, True)
        self.metrics.record_api_call("test_api", 600, False)
        
        # Get summary
        summary = self.metrics.get_summary()
        
        # Verify summary structure
        assert "voice_latency" in summary
        assert "api_performance" in summary
        assert "error_summary" in summary
        
        # Verify voice latency stats
        assert summary["voice_latency"]["avg"] == 150.0
        assert summary["voice_latency"]["min"] == 100
        assert summary["voice_latency"]["max"] == 200
        
    def test_reset_metrics(self):
        """Test metrics reset functionality"""
        # Add some data
        self.metrics.record_voice_latency(100)
        self.metrics.increment_error_count("test_error")
        self.metrics.record_api_call("test", 500, True)
        
        # Verify data exists
        assert len(self.metrics.voice_latency_ms) > 0
        assert len(self.metrics.error_count) > 0
        assert len(self.metrics.api_calls) > 0
        
        # Reset and verify cleanup
        self.metrics.reset()
        assert len(self.metrics.voice_latency_ms) == 0
        assert len(self.metrics.error_count) == 0
        assert len(self.metrics.api_calls) == 0
        
    def test_performance_thresholds(self):
        """Test performance threshold detection"""
        # Record some slow operations
        self.metrics.record_voice_latency(3000)  # 3 seconds - should be flagged
        self.metrics.record_voice_latency(100)   # Normal
        
        summary = self.metrics.get_summary()
        
        # Check if slow operations are flagged
        if "warnings" in summary:
            warnings = summary["warnings"]
            assert any("voice_latency" in w for w in warnings)
            
    def test_concurrent_metrics_recording(self):
        """Test metrics recording under concurrent load"""
        async def record_metrics():
            for i in range(10):
                self.metrics.record_voice_latency(100 + i)
                self.metrics.record_api_call(f"api_{i}", 200 + i, True)
                await asyncio.sleep(0.001)  # Small delay
                
        # Run concurrent metric recording
        asyncio.run(record_metrics())
        
        # Verify all metrics were recorded
        assert len(self.metrics.voice_latency_ms) == 10
        assert len(self.metrics.api_calls) == 10
        
    def test_memory_usage_tracking(self):
        """Test memory usage metrics if available"""
        try:
            import psutil
            # Test memory tracking if psutil is available
            self.metrics.record_memory_usage()
            summary = self.metrics.get_summary()
            
            if "memory" in summary:
                assert "current_mb" in summary["memory"]
                assert summary["memory"]["current_mb"] > 0
        except ImportError:
            # Skip test if psutil not available
            pytest.skip("psutil not available for memory tracking tests")
            
    def test_export_metrics_format(self):
        """Test metrics export format for monitoring systems"""
        # Add test data
        self.metrics.record_voice_latency(150)
        self.metrics.record_api_call("test", 300, True)
        self.metrics.increment_error_count("test_error")
        
        # Export metrics
        exported = self.metrics.export_for_monitoring()
        
        # Verify export format
        assert isinstance(exported, dict)
        assert "timestamp" in exported
        assert "metrics" in exported
        assert "alice" in exported["metrics"]  # Namespace
        
    @patch('time.time')
    def test_latency_measurement_accuracy(self, mock_time):
        """Test accuracy of latency measurements"""
        # Mock time progression
        mock_time.side_effect = [1000.0, 1000.5, 1001.0]  # 500ms then 500ms
        
        start_time = time.time()
        # Simulate some work
        end_time = time.time()
        latency = (end_time - start_time) * 1000
        
        self.metrics.record_voice_latency(latency)
        
        # Verify latency calculation
        assert self.metrics.voice_latency_ms[0] == 500.0
        
    def test_metrics_thread_safety(self):
        """Test that metrics recording is thread-safe"""
        import threading
        
        def record_data(thread_id):
            for i in range(100):
                self.metrics.record_voice_latency(thread_id * 100 + i)
        
        # Create multiple threads
        threads = []
        for t_id in range(5):
            thread = threading.Thread(target=record_data, args=(t_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
            
        # Verify all data was recorded
        assert len(self.metrics.voice_latency_ms) == 500  # 5 threads * 100 records


if __name__ == "__main__":
    pytest.main([__file__, "-v"])