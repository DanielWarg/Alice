"""
B3 Metrics & Telemetry - Production Monitoring
Prometheus-compatible metrics för B3 Always-On Voice System
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
from dataclasses import dataclass
import json

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("alice.b3_metrics")

@dataclass
class MetricSample:
    """Single metric sample with timestamp"""
    value: float
    timestamp: float
    labels: Dict[str, str] = None

class HistogramBucket:
    """Simple histogram implementation"""
    def __init__(self, buckets: list = None):
        self.buckets = buckets or [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self.counts = defaultdict(int)
        self.sum = 0
        self.count = 0
    
    def observe(self, value: float):
        self.sum += value
        self.count += 1
        for bucket in self.buckets:
            if value <= bucket:
                self.counts[bucket] += 1

class B3MetricsCollector:
    """
    Collects and exposes B3 system metrics in Prometheus format
    """
    
    def __init__(self):
        # Counters
        self.counters = defaultdict(int)
        
        # Histograms for latency measurements
        self.histograms = {
            'asr_partial_latency_ms': HistogramBucket(),
            'tts_stop_latency_ms': HistogramBucket(),
            'ws_message_latency_ms': HistogramBucket(),
            'privacy_forget_duration_ms': HistogramBucket()
        }
        
        # Gauges for current state
        self.gauges = defaultdict(float)
        
        # Rate tracking (per minute)
        self.rate_windows = defaultdict(lambda: deque(maxlen=60))  # 60 seconds
        
        # Recent samples for dashboard
        self.recent_samples = defaultdict(lambda: deque(maxlen=1000))
        
        # System health
        self.health_status = {
            'asr_healthy': True,
            'websocket_healthy': True,
            'barge_in_healthy': True,
            'privacy_healthy': True,
            'last_health_check': time.time()
        }
        
        logger.info("B3 Metrics Collector initialized")
    
    def increment_counter(self, name: str, labels: Dict[str, str] = None, value: float = 1.0):
        """Increment a counter metric"""
        key = self._make_key(name, labels)
        self.counters[key] += value
        
        # Track for rate calculation
        now = time.time()
        self.rate_windows[key].append(now)
        
        logger.debug(f"Counter {key}: {self.counters[key]}")
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value"""
        key = self._make_key(name, labels)
        self.gauges[key] = value
        
        # Store recent sample
        sample = MetricSample(value, time.time(), labels)
        self.recent_samples[name].append(sample)
        
        logger.debug(f"Gauge {key}: {value}")
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Add observation to histogram"""
        if name in self.histograms:
            self.histograms[name].observe(value)
            
            # Store recent sample
            sample = MetricSample(value, time.time(), labels)
            self.recent_samples[name].append(sample)
            
            logger.debug(f"Histogram {name}: {value}")
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create metric key with labels"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_rate(self, name: str, labels: Dict[str, str] = None) -> float:
        """Get current rate per minute for a counter"""
        key = self._make_key(name, labels)
        window = self.rate_windows[key]
        
        if not window:
            return 0.0
        
        now = time.time()
        # Count samples in last minute
        recent_count = sum(1 for timestamp in window if now - timestamp <= 60)
        return recent_count  # per minute
    
    def health_check(self):
        """Update system health status"""
        now = time.time()
        
        # Check if we've seen recent activity
        asr_rate = self.get_rate('asr_transcriptions_total')
        ws_rate = self.get_rate('websocket_messages_total')
        
        self.health_status.update({
            'asr_healthy': asr_rate > 0 or (now - self.health_status['last_health_check']) < 300,  # 5 min grace
            'websocket_healthy': ws_rate > 0 or (now - self.health_status['last_health_check']) < 60,  # 1 min grace
            'barge_in_healthy': self.counters.get('barge_in_errors_total', 0) < 10,  # <10 errors
            'privacy_healthy': self.counters.get('privacy_errors_total', 0) < 5,  # <5 errors
            'last_health_check': now
        })
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        # Add help and type info
        lines.append('# HELP alice_b3_asr_partial_latency_ms Time from audio input to ASR partial result')
        lines.append('# TYPE alice_b3_asr_partial_latency_ms histogram')
        
        # Export histograms
        for name, hist in self.histograms.items():
            for bucket, count in hist.counts.items():
                lines.append(f'alice_b3_{name}_bucket{{le="{bucket}"}} {count}')
            lines.append(f'alice_b3_{name}_sum {hist.sum}')
            lines.append(f'alice_b3_{name}_count {hist.count}')
        
        # Export counters
        lines.append('# TYPE alice_b3_counter counter')
        for key, value in self.counters.items():
            lines.append(f'alice_b3_{key} {value}')
        
        # Export gauges
        lines.append('# TYPE alice_b3_gauge gauge')
        for key, value in self.gauges.items():
            lines.append(f'alice_b3_{key} {value}')
        
        # System health
        lines.append('# TYPE alice_b3_healthy gauge')
        for component, healthy in self.health_status.items():
            if isinstance(healthy, bool):
                lines.append(f'alice_b3_healthy{{component="{component}"}} {1 if healthy else 0}')
        
        return '\n'.join(lines)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get formatted data for dashboard"""
        now = time.time()
        
        # Calculate recent averages
        dashboard = {
            'timestamp': now,
            'health': self.health_status,
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'rates_per_minute': {},
            'latencies': {}
        }
        
        # Calculate rates
        for name in ['asr_transcriptions_total', 'websocket_messages_total', 'barge_in_triggers_total', 'privacy_forget_total']:
            dashboard['rates_per_minute'][name] = self.get_rate(name)
        
        # Calculate latency percentiles (approximation)
        for name, hist in self.histograms.items():
            if hist.count > 0:
                dashboard['latencies'][name] = {
                    'avg': hist.sum / hist.count,
                    'count': hist.count,
                    'sum': hist.sum
                }
        
        return dashboard

# Global metrics collector
_metrics_collector = None

def get_b3_metrics() -> B3MetricsCollector:
    """Get singleton metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = B3MetricsCollector()
    return _metrics_collector

# Convenience functions for common metrics
def record_asr_latency(latency_ms: float, language: str = "sv"):
    """Record ASR partial latency"""
    metrics = get_b3_metrics()
    metrics.observe_histogram('asr_partial_latency_ms', latency_ms, {'language': language})
    metrics.increment_counter('asr_transcriptions_total', {'language': language})

def record_barge_in(success: bool, stopped_processes: int = 0, latency_ms: float = 0):
    """Record barge-in event"""
    metrics = get_b3_metrics()
    
    if success:
        metrics.increment_counter('barge_in_success_total')
        metrics.set_gauge('barge_in_stopped_processes', stopped_processes)
        if latency_ms > 0:
            metrics.observe_histogram('tts_stop_latency_ms', latency_ms)
    else:
        metrics.increment_counter('barge_in_errors_total')

def record_websocket_activity(message_type: str, session_count: int = 0):
    """Record WebSocket activity"""
    metrics = get_b3_metrics()
    metrics.increment_counter('websocket_messages_total', {'type': message_type})
    
    if session_count > 0:
        metrics.set_gauge('websocket_active_sessions', session_count)

def record_privacy_operation(operation: str, deleted_count: int = 0, duration_ms: float = 0):
    """Record privacy/forget operation"""
    metrics = get_b3_metrics()
    metrics.increment_counter('privacy_operations_total', {'operation': operation})
    
    if deleted_count > 0:
        metrics.set_gauge('privacy_last_deleted_count', deleted_count)
    
    if duration_ms > 0:
        metrics.observe_histogram('privacy_forget_duration_ms', duration_ms)

def record_error(component: str, error_type: str):
    """Record system error"""
    metrics = get_b3_metrics()
    metrics.increment_counter(f'{component}_errors_total', {'type': error_type})

# FastAPI router for metrics endpoints
router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint"""
    from fastapi.responses import PlainTextResponse
    
    metrics = get_b3_metrics()
    metrics.health_check()
    
    return PlainTextResponse(metrics.export_prometheus(), media_type="text/plain")

@router.get("/dashboard")
async def dashboard_metrics():
    """JSON metrics for dashboard"""
    metrics = get_b3_metrics()
    metrics.health_check()
    
    return metrics.get_dashboard_data()

@router.get("/health")
async def health_check():
    """Health check endpoint for load balancers"""
    metrics = get_b3_metrics()
    metrics.health_check()
    
    all_healthy = all(
        status for key, status in metrics.health_status.items() 
        if isinstance(status, bool)
    )
    
    return {
        "healthy": all_healthy,
        "status": metrics.health_status,
        "timestamp": time.time()
    }

# Background task for periodic health checks
async def start_metrics_background_task():
    """Start background task for periodic metrics collection"""
    metrics = get_b3_metrics()
    
    while True:
        try:
            metrics.health_check()
            await asyncio.sleep(30)  # Health check every 30 seconds
        except Exception as e:
            logger.error(f"Error in metrics background task: {e}")
            await asyncio.sleep(60)  # Longer wait on error