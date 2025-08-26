#!/usr/bin/env python3
"""
📊 Voice Gateway Metrics - Prometheus Integration
Collects real-time performance metrics for voice pipeline monitoring
"""
import time
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry

class VoiceMetrics:
    """Prometheus metrics for voice gateway performance"""
    
    def __init__(self):
        # Create custom registry to avoid conflicts
        self.registry = CollectorRegistry()
        
        # WebRTC metrics
        self.webrtc_offers_total = Counter(
            'voice_webrtc_offers_total',
            'Total WebRTC offers processed',
            registry=self.registry
        )
        
        self.webrtc_offer_processing_time = Histogram(
            'voice_webrtc_offer_processing_seconds',
            'Time to process WebRTC offers',
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )
        
        self.webrtc_active_sessions = Gauge(
            'voice_webrtc_active_sessions',
            'Number of active WebRTC sessions',
            registry=self.registry
        )
        
        # Voice processing metrics (placeholders for future phases)
        self.voice_first_partial_ms = Histogram(
            'voice_first_partial_ms',
            'Time to first partial transcript in milliseconds',
            buckets=[100, 200, 300, 500, 1000, 2000],
            registry=self.registry
        )
        
        self.voice_first_audio_ms = Histogram(
            'voice_first_audio_ms', 
            'Time to first audio output in milliseconds',
            buckets=[200, 400, 600, 1000, 2000, 5000],
            registry=self.registry
        )
        
        self.voice_barge_in_ms = Histogram(
            'voice_barge_in_ms',
            'Barge-in response time in milliseconds', 
            buckets=[50, 100, 120, 200, 500],
            registry=self.registry
        )
        
        self.tts_underflow_count = Counter(
            'voice_tts_underflow_total',
            'Total TTS audio underflow events',
            registry=self.registry
        )
        
        self.asr_stream_reconnects = Counter(
            'voice_asr_stream_reconnects_total', 
            'Total ASR stream reconnections',
            registry=self.registry
        )
        
        self.router_choice_total = Counter(
            'voice_router_choice_total',
            'LLM router path choices',
            ['route'],  # fast|deep
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'voice_errors_total',
            'Total voice processing errors',
            ['error_type'],
            registry=self.registry
        )
        
        # System metrics
        self.service_info = Info(
            'voice_gateway_info',
            'Voice gateway service information',
            registry=self.registry
        )
        
        self.uptime_seconds = Gauge(
            'voice_gateway_uptime_seconds',
            'Voice gateway uptime in seconds',
            registry=self.registry
        )
        
        # Initialize start time for uptime
        self.start_time = time.time()
    
    def initialize(self):
        """Initialize metrics with service info"""
        self.service_info.info({
            'version': '1.0.0',
            'service': 'alice_voice_gateway',
            'pipeline': 'livekit_class'
        })
        
    def record_webrtc_offer(self):
        """Record WebRTC offer processed"""
        self.webrtc_offers_total.inc()
    
    def record_offer_processing_time(self, duration_ms: float):
        """Record WebRTC offer processing time"""
        self.webrtc_offer_processing_time.observe(duration_ms / 1000.0)
        
    def update_active_sessions(self, count: int):
        """Update active WebRTC sessions count"""
        self.webrtc_active_sessions.set(count)
    
    def record_first_partial(self, duration_ms: float):
        """Record time to first partial transcript"""
        self.voice_first_partial_ms.observe(duration_ms)
    
    def record_first_audio(self, duration_ms: float):
        """Record time to first audio output (TTFA)"""
        self.voice_first_audio_ms.observe(duration_ms)
        
    def record_barge_in(self, duration_ms: float = None):
        """Record barge-in response time"""
        if duration_ms is not None:
            self.voice_barge_in_ms.observe(duration_ms)
    
    def record_tts_underflow(self):
        """Record TTS underflow event"""
        self.tts_underflow_count.inc()
    
    def record_asr_reconnect(self):
        """Record ASR stream reconnection"""
        self.asr_stream_reconnects.inc()
        
    def record_router_choice(self, route: str):
        """Record LLM router choice (fast|deep)"""
        self.router_choice_total.labels(route=route).inc()
        
    def record_error(self, error_type: str):
        """Record error by type"""
        self.errors_total.labels(error_type=error_type).inc()
    
    def update_uptime(self):
        """Update service uptime"""
        uptime = time.time() - self.start_time
        self.uptime_seconds.set(uptime)
    
    def get_summary_metrics(self) -> dict:
        """Get summary of key metrics for health checks"""
        return {
            'active_sessions': self.webrtc_active_sessions._value.get(),
            'total_offers': self.webrtc_offers_total._value.get(),
            'total_errors': sum(self.errors_total._value.values()),
            'uptime_seconds': time.time() - self.start_time
        }