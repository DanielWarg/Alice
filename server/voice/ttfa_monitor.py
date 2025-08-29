"""
TTFA Monitor - Time-to-First-Audio measurement for real audio pipeline
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import deque, defaultdict
import logging
import json

logger = logging.getLogger("alice.voice.ttfa")

@dataclass
class TTFAMeasurement:
    """Single TTFA measurement"""
    request_id: str
    source_type: str  # chat, notification, email_tldr, email_part
    text_length: int
    
    # Timing stages
    request_start: float
    translation_start: float
    translation_end: float
    tts_start: float
    tts_end: float
    first_audio_byte: float  # When first audio byte is available
    first_audio_played: float  # When first audio byte starts playing
    
    # Derived metrics
    ttfa_ms: float = field(init=False)  # Time to first audio (request -> first byte)
    ttp_ms: float = field(init=False)   # Time to play (request -> first played)
    translation_ms: float = field(init=False)
    tts_ms: float = field(init=False)
    
    # Metadata
    model_used: str = ""
    cache_hit: bool = False
    fast_lane: bool = False
    error: Optional[str] = None
    
    def __post_init__(self):
        """Calculate derived metrics"""
        self.ttfa_ms = (self.first_audio_byte - self.request_start) * 1000
        self.ttp_ms = (self.first_audio_played - self.request_start) * 1000
        self.translation_ms = (self.translation_end - self.translation_start) * 1000
        self.tts_ms = (self.tts_end - self.tts_start) * 1000

class TTFAMonitor:
    """
    Monitor Time-to-First-Audio metrics for voice pipeline performance
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.measurements: deque = deque(maxlen=max_history)
        
        # Active requests being tracked
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        
        # Performance targets (from production config)
        self.targets = {
            "chat": 3000,      # 3.0s for chat TTFA
            "notification": 2500,  # 2.5s for notifications  
            "email_tldr": 3500,    # 3.5s for email TL;DR
            "email_part": 5000     # 5.0s for email parts
        }
        
        # Alerting thresholds
        self.p95_alert_threshold = 1.2  # Alert if p95 > target * 1.2
        self.consecutive_slow_alert = 5  # Alert after N consecutive slow requests
        
        # Alert state
        self.consecutive_slow_counts = defaultdict(int)
        self.last_alert_time = defaultdict(float)
        self.alert_cooldown = 300  # 5 minutes
    
    def start_request_tracking(self, request_id: str, source_type: str, text_sv: str) -> None:
        """Start tracking a new voice request"""
        
        now = time.time()
        
        self.active_requests[request_id] = {
            "source_type": source_type,
            "text_length": len(text_sv),
            "request_start": now,
            "translation_start": None,
            "translation_end": None,
            "tts_start": None,
            "tts_end": None,
            "first_audio_byte": None,
            "first_audio_played": None,
            "model_used": "",
            "cache_hit": False,
            "fast_lane": False,
            "error": None
        }
        
        logger.debug(f"Started tracking request {request_id}: {source_type}")
    
    def record_translation_start(self, request_id: str, model: str = "") -> None:
        """Record when translation starts"""
        if request_id in self.active_requests:
            self.active_requests[request_id]["translation_start"] = time.time()
            self.active_requests[request_id]["model_used"] = model
    
    def record_translation_end(self, request_id: str, cache_hit: bool = False, fast_lane: bool = False) -> None:
        """Record when translation completes"""
        if request_id in self.active_requests:
            self.active_requests[request_id]["translation_end"] = time.time()
            self.active_requests[request_id]["cache_hit"] = cache_hit
            self.active_requests[request_id]["fast_lane"] = fast_lane
    
    def record_tts_start(self, request_id: str) -> None:
        """Record when TTS processing starts"""
        if request_id in self.active_requests:
            self.active_requests[request_id]["tts_start"] = time.time()
    
    def record_tts_end(self, request_id: str) -> None:
        """Record when TTS processing completes"""
        if request_id in self.active_requests:
            self.active_requests[request_id]["tts_end"] = time.time()
    
    def record_first_audio_byte(self, request_id: str) -> None:
        """Record when first audio byte is available (TTFA)"""
        if request_id in self.active_requests:
            self.active_requests[request_id]["first_audio_byte"] = time.time()
            
            # This is the critical TTFA measurement
            self._check_ttfa_performance(request_id)
    
    def record_first_audio_played(self, request_id: str) -> None:
        """Record when first audio byte starts playing (TTP)"""
        if request_id in self.active_requests:
            self.active_requests[request_id]["first_audio_played"] = time.time()
            
            # Complete the measurement
            self._complete_measurement(request_id)
    
    def record_error(self, request_id: str, error: str) -> None:
        """Record an error for this request"""
        if request_id in self.active_requests:
            self.active_requests[request_id]["error"] = error
            self._complete_measurement(request_id, failed=True)
    
    def _check_ttfa_performance(self, request_id: str) -> None:
        """Check if TTFA meets performance targets"""
        
        req_data = self.active_requests.get(request_id)
        if not req_data or not req_data.get("first_audio_byte"):
            return
        
        ttfa_ms = (req_data["first_audio_byte"] - req_data["request_start"]) * 1000
        source_type = req_data["source_type"]
        target_ms = self.targets.get(source_type, 3000)
        
        if ttfa_ms > target_ms:
            self.consecutive_slow_counts[source_type] += 1
            logger.warning(f"Slow TTFA: {ttfa_ms:.0f}ms > {target_ms}ms for {source_type} (consecutive: {self.consecutive_slow_counts[source_type]})")
            
            # Alert if too many consecutive slow requests
            if self.consecutive_slow_counts[source_type] >= self.consecutive_slow_alert:
                self._trigger_alert(source_type, ttfa_ms, target_ms)
        else:
            # Reset consecutive counter on success
            self.consecutive_slow_counts[source_type] = 0
    
    def _complete_measurement(self, request_id: str, failed: bool = False) -> None:
        """Complete and store a TTFA measurement"""
        
        req_data = self.active_requests.pop(request_id, None)
        if not req_data:
            return
        
        try:
            # Fill in missing timestamps with reasonable defaults
            now = time.time()
            if req_data["translation_start"] is None:
                req_data["translation_start"] = req_data["request_start"]
            if req_data["translation_end"] is None:
                req_data["translation_end"] = req_data["translation_start"] + 0.1
            if req_data["tts_start"] is None:
                req_data["tts_start"] = req_data["translation_end"]
            if req_data["tts_end"] is None:
                req_data["tts_end"] = req_data["tts_start"] + 0.1
            if req_data["first_audio_byte"] is None:
                req_data["first_audio_byte"] = now
            if req_data["first_audio_played"] is None:
                req_data["first_audio_played"] = req_data["first_audio_byte"] + 0.05
            
            measurement = TTFAMeasurement(
                request_id=request_id,
                source_type=req_data["source_type"],
                text_length=req_data["text_length"],
                request_start=req_data["request_start"],
                translation_start=req_data["translation_start"],
                translation_end=req_data["translation_end"],
                tts_start=req_data["tts_start"],
                tts_end=req_data["tts_end"],
                first_audio_byte=req_data["first_audio_byte"],
                first_audio_played=req_data["first_audio_played"],
                model_used=req_data.get("model_used", "unknown"),
                cache_hit=req_data.get("cache_hit", False),
                fast_lane=req_data.get("fast_lane", False),
                error=req_data.get("error")
            )
            
            self.measurements.append(measurement)
            
            if not failed:
                logger.info(f"TTFA completed: {measurement.ttfa_ms:.0f}ms ({measurement.source_type})")
            
        except Exception as e:
            logger.error(f"Failed to complete TTFA measurement for {request_id}: {e}")
    
    def _trigger_alert(self, source_type: str, ttfa_ms: float, target_ms: float) -> None:
        """Trigger performance alert"""
        
        now = time.time()
        
        # Check cooldown
        if now - self.last_alert_time[source_type] < self.alert_cooldown:
            return
        
        self.last_alert_time[source_type] = now
        
        logger.error(f"🚨 TTFA ALERT: {source_type} consistently slow - {ttfa_ms:.0f}ms > {target_ms}ms target")
        logger.error(f"   Consecutive slow requests: {self.consecutive_slow_counts[source_type]}")
        logger.error(f"   Consider checking system load, Ollama performance, or Guardian throttling")
    
    def get_performance_metrics(self, minutes: int = 60) -> Dict[str, Any]:
        """Get performance metrics for the last N minutes"""
        
        cutoff_time = time.time() - (minutes * 60)
        recent_measurements = [m for m in self.measurements if m.request_start >= cutoff_time]
        
        if not recent_measurements:
            return {"period_minutes": minutes, "total_requests": 0}
        
        # Overall metrics
        ttfa_times = [m.ttfa_ms for m in recent_measurements if m.error is None]
        translation_times = [m.translation_ms for m in recent_measurements if m.error is None]
        tts_times = [m.tts_ms for m in recent_measurements if m.error is None]
        
        # By source type
        by_source = defaultdict(list)
        for m in recent_measurements:
            if m.error is None:
                by_source[m.source_type].append(m.ttfa_ms)
        
        # Calculate percentiles
        def percentile(data: List[float], p: float) -> float:
            if not data:
                return 0.0
            sorted_data = sorted(data)
            index = int(len(sorted_data) * p / 100)
            return sorted_data[min(index, len(sorted_data) - 1)]
        
        metrics = {
            "period_minutes": minutes,
            "total_requests": len(recent_measurements),
            "successful_requests": len(ttfa_times),
            "error_rate_percent": round((len(recent_measurements) - len(ttfa_times)) / len(recent_measurements) * 100, 1),
            "overall_ttfa": {
                "avg_ms": round(sum(ttfa_times) / len(ttfa_times), 0) if ttfa_times else 0,
                "p50_ms": round(percentile(ttfa_times, 50), 0),
                "p95_ms": round(percentile(ttfa_times, 95), 0),
                "p99_ms": round(percentile(ttfa_times, 99), 0)
            },
            "translation_performance": {
                "avg_ms": round(sum(translation_times) / len(translation_times), 0) if translation_times else 0,
                "p95_ms": round(percentile(translation_times, 95), 0)
            },
            "tts_performance": {
                "avg_ms": round(sum(tts_times) / len(tts_times), 0) if tts_times else 0,
                "p95_ms": round(percentile(tts_times, 95), 0)
            }
        }
        
        # Per source type analysis
        for source_type, ttfa_list in by_source.items():
            target_ms = self.targets.get(source_type, 3000)
            p95_ms = percentile(ttfa_list, 95)
            
            metrics[f"{source_type}_ttfa"] = {
                "count": len(ttfa_list),
                "avg_ms": round(sum(ttfa_list) / len(ttfa_list), 0),
                "p95_ms": round(p95_ms, 0),
                "target_ms": target_ms,
                "meets_target": p95_ms <= target_ms,
                "target_violation_percent": round((p95_ms - target_ms) / target_ms * 100, 1) if p95_ms > target_ms else 0
            }
        
        return metrics
    
    def get_active_requests_count(self) -> int:
        """Get number of requests currently being tracked"""
        return len(self.active_requests)

# Global TTFA monitor instance
ttfa_monitor = TTFAMonitor()

# Convenience functions for easy integration
def start_ttfa_tracking(request_id: str, source_type: str, text_sv: str) -> None:
    """Start tracking TTFA for a voice request"""
    ttfa_monitor.start_request_tracking(request_id, source_type, text_sv)

def record_translation_complete(request_id: str, model: str = "", cache_hit: bool = False) -> None:
    """Record translation completion"""
    ttfa_monitor.record_translation_end(request_id, cache_hit=cache_hit)

def record_audio_ready(request_id: str) -> None:
    """Record when first audio byte is ready (TTFA)"""
    ttfa_monitor.record_first_audio_byte(request_id)

def record_audio_playing(request_id: str) -> None:
    """Record when audio starts playing"""
    ttfa_monitor.record_first_audio_played(request_id)

def get_ttfa_stats(minutes: int = 60) -> Dict[str, Any]:
    """Get TTFA performance statistics"""
    return ttfa_monitor.get_performance_metrics(minutes)