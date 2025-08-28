"""
Performance Monitor - Tracks voice pipeline metrics and latency.
Provides real-time monitoring and historical analysis.
"""

import json
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
from collections import deque, defaultdict

logger = logging.getLogger("alice.voice.performance")

@dataclass
class VoiceMetric:
    """Single voice pipeline performance metric"""
    timestamp: float
    source_type: str
    text_length: int
    processing_stages: Dict[str, float]  # stage_name -> duration
    total_latency: float
    success: bool
    cached: bool = False
    error: Optional[str] = None
    meta: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.meta is None:
            self.meta = {}

class PerformanceMonitor:
    """
    Real-time performance monitoring for voice pipeline.
    Tracks latency, success rates, and cache effectiveness.
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics: deque = deque(maxlen=max_history)
        
        # Real-time counters
        self.total_requests = 0
        self.successful_requests = 0
        self.cached_requests = 0
        self.errors_by_type = defaultdict(int)
        
        # Latency tracking
        self.latency_samples = deque(maxlen=100)  # Keep recent samples for p95
        
        # Stage-specific tracking
        self.stage_latencies = defaultdict(lambda: deque(maxlen=100))
        
        # Performance targets
        self.targets = {
            "chat_p95_latency": 1.5,
            "email_p95_latency": 2.0,
            "notification_p95_latency": 0.7,
            "cache_hit_rate": 30.0,
            "success_rate": 95.0
        }
        
        # File for persistent metrics
        self.metrics_file = Path(__file__).parent / "performance_metrics.jsonl"
        
        logger.info("Performance monitor initialized")
    
    def record_metric(self, metric: VoiceMetric):
        """Record a new performance metric"""
        
        # Add to collections
        self.metrics.append(metric)
        self.total_requests += 1
        
        if metric.success:
            self.successful_requests += 1
            self.latency_samples.append(metric.total_latency)
            
            # Track stage latencies
            for stage, duration in metric.processing_stages.items():
                self.stage_latencies[stage].append(duration)
        
        if metric.cached:
            self.cached_requests += 1
            
        if metric.error:
            self.errors_by_type[metric.error] += 1
        
        # Persist to file
        self._persist_metric(metric)
        
        # Log warnings for performance issues
        self._check_performance_warnings(metric)
    
    def record_voice_request(
        self,
        source_type: str,
        text_length: int,
        processing_stages: Dict[str, float],
        total_latency: float,
        success: bool,
        cached: bool = False,
        error: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ):
        """Convenience method to record a voice request"""
        
        metric = VoiceMetric(
            timestamp=time.time(),
            source_type=source_type,
            text_length=text_length,
            processing_stages=processing_stages,
            total_latency=total_latency,
            success=success,
            cached=cached,
            error=error,
            meta=meta or {}
        )
        
        self.record_metric(metric)
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        
        # Calculate rates
        success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        cache_hit_rate = (self.cached_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        
        # Calculate latency percentiles
        if self.latency_samples:
            sorted_latencies = sorted(self.latency_samples)
            p50_latency = sorted_latencies[len(sorted_latencies) // 2]
            p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            avg_latency = sum(sorted_latencies) / len(sorted_latencies)
        else:
            p50_latency = p95_latency = avg_latency = 0
        
        # Stage performance
        stage_stats = {}
        for stage, samples in self.stage_latencies.items():
            if samples:
                stage_stats[stage] = {
                    "avg": sum(samples) / len(samples),
                    "p95": sorted(samples)[int(len(samples) * 0.95)] if samples else 0
                }
        
        return {
            "summary": {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "success_rate": round(success_rate, 1),
                "cache_hit_rate": round(cache_hit_rate, 1)
            },
            "latency": {
                "avg": round(avg_latency, 3),
                "p50": round(p50_latency, 3),
                "p95": round(p95_latency, 3)
            },
            "targets": {
                "success_rate": "✅" if success_rate >= self.targets["success_rate"] else "❌",
                "cache_hit_rate": "✅" if cache_hit_rate >= self.targets["cache_hit_rate"] else "❌",
                "latency": "✅" if p95_latency <= 2.0 else "❌"  # General target
            },
            "stages": stage_stats,
            "errors": dict(self.errors_by_type),
            "metrics_collected": len(self.metrics)
        }
    
    def get_source_type_analysis(self) -> Dict[str, Any]:
        """Analyze performance by source type (chat, email, etc.)"""
        
        source_stats = defaultdict(lambda: {
            "count": 0,
            "successes": 0,
            "latencies": [],
            "cached": 0
        })
        
        # Analyze recent metrics
        for metric in list(self.metrics)[-200:]:  # Last 200 requests
            stats = source_stats[metric.source_type]
            stats["count"] += 1
            
            if metric.success:
                stats["successes"] += 1
                stats["latencies"].append(metric.total_latency)
            
            if metric.cached:
                stats["cached"] += 1
        
        # Calculate statistics for each source type
        results = {}
        for source_type, stats in source_stats.items():
            if stats["count"] == 0:
                continue
                
            success_rate = stats["successes"] / stats["count"] * 100
            cache_rate = stats["cached"] / stats["count"] * 100
            
            if stats["latencies"]:
                avg_latency = sum(stats["latencies"]) / len(stats["latencies"])
                p95_latency = sorted(stats["latencies"])[int(len(stats["latencies"]) * 0.95)]
            else:
                avg_latency = p95_latency = 0
            
            # Check if meets targets
            target_key = f"{source_type}_p95_latency"
            target_latency = self.targets.get(target_key, 2.0)
            meets_target = p95_latency <= target_latency
            
            results[source_type] = {
                "count": stats["count"],
                "success_rate": round(success_rate, 1),
                "cache_hit_rate": round(cache_rate, 1),
                "avg_latency": round(avg_latency, 3),
                "p95_latency": round(p95_latency, 3),
                "target_latency": target_latency,
                "meets_target": meets_target
            }
        
        return results
    
    def get_time_series_data(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get time series data for the last N hours"""
        
        cutoff_time = time.time() - (hours * 3600)
        recent_metrics = [m for m in self.metrics if m.timestamp >= cutoff_time]
        
        # Group by hour
        hourly_stats = defaultdict(lambda: {
            "timestamp": 0,
            "requests": 0,
            "successes": 0,
            "latencies": [],
            "cached": 0
        })
        
        for metric in recent_metrics:
            # Round to hour
            hour_timestamp = int(metric.timestamp // 3600) * 3600
            stats = hourly_stats[hour_timestamp]
            
            if stats["timestamp"] == 0:
                stats["timestamp"] = hour_timestamp
            
            stats["requests"] += 1
            
            if metric.success:
                stats["successes"] += 1
                stats["latencies"].append(metric.total_latency)
            
            if metric.cached:
                stats["cached"] += 1
        
        # Convert to list and calculate rates
        time_series = []
        for stats in sorted(hourly_stats.values(), key=lambda x: x["timestamp"]):
            success_rate = (stats["successes"] / stats["requests"] * 100) if stats["requests"] > 0 else 0
            cache_rate = (stats["cached"] / stats["requests"] * 100) if stats["requests"] > 0 else 0
            avg_latency = sum(stats["latencies"]) / len(stats["latencies"]) if stats["latencies"] else 0
            
            time_series.append({
                "timestamp": stats["timestamp"],
                "datetime": datetime.fromtimestamp(stats["timestamp"]).isoformat(),
                "requests": stats["requests"],
                "success_rate": round(success_rate, 1),
                "cache_hit_rate": round(cache_rate, 1),
                "avg_latency": round(avg_latency, 3)
            })
        
        return time_series
    
    def _check_performance_warnings(self, metric: VoiceMetric):
        """Check for performance issues and log warnings"""
        
        if not metric.success:
            logger.warning(f"Voice request failed: {metric.source_type} - {metric.error}")
            return
        
        # Check latency targets
        target_key = f"{metric.source_type}_p95_latency"
        target_latency = self.targets.get(target_key, 2.0)
        
        if metric.total_latency > target_latency * 1.5:  # 50% over target
            logger.warning(f"High latency detected: {metric.total_latency:.2f}s for {metric.source_type} (target: {target_latency}s)")
        
        # Check for slow stages
        for stage, duration in metric.processing_stages.items():
            if duration > 3.0:  # Any stage over 3 seconds
                logger.warning(f"Slow {stage} stage: {duration:.2f}s")
    
    def _persist_metric(self, metric: VoiceMetric):
        """Persist metric to JSONL file"""
        
        try:
            with open(self.metrics_file, 'a') as f:
                json.dump(asdict(metric), f)
                f.write('\n')
        except Exception as e:
            logger.error(f"Failed to persist metric: {e}")
    
    def load_historical_metrics(self, days: int = 7) -> int:
        """Load historical metrics from file"""
        
        if not self.metrics_file.exists():
            return 0
        
        cutoff_time = time.time() - (days * 24 * 3600)
        loaded_count = 0
        
        try:
            with open(self.metrics_file, 'r') as f:
                for line in f:
                    try:
                        metric_data = json.loads(line.strip())
                        if metric_data.get("timestamp", 0) >= cutoff_time:
                            metric = VoiceMetric(**metric_data)
                            self.metrics.append(metric)
                            loaded_count += 1
                    except Exception as e:
                        logger.debug(f"Failed to parse metric line: {e}")
            
            logger.info(f"Loaded {loaded_count} historical metrics")
            return loaded_count
            
        except Exception as e:
            logger.error(f"Failed to load historical metrics: {e}")
            return 0
    
    def generate_performance_report(self) -> str:
        """Generate a human-readable performance report"""
        
        stats = self.get_current_stats()
        source_analysis = self.get_source_type_analysis()
        
        report = ["🎙️ VOICE PIPELINE PERFORMANCE REPORT"]
        report.append("=" * 50)
        
        # Summary
        report.append("\n📊 OVERALL PERFORMANCE:")
        report.append(f"  Total Requests: {stats['summary']['total_requests']}")
        report.append(f"  Success Rate: {stats['summary']['success_rate']}% {stats['targets']['success_rate']}")
        report.append(f"  Cache Hit Rate: {stats['summary']['cache_hit_rate']}% {stats['targets']['cache_hit_rate']}")
        
        # Latency
        report.append("\n⚡ LATENCY METRICS:")
        report.append(f"  Average: {stats['latency']['avg']}s")
        report.append(f"  P50: {stats['latency']['p50']}s")
        report.append(f"  P95: {stats['latency']['p95']}s {stats['targets']['latency']}")
        
        # Source type breakdown
        report.append("\n📱 BY SOURCE TYPE:")
        for source_type, source_stats in source_analysis.items():
            target_icon = "✅" if source_stats["meets_target"] else "❌"
            report.append(f"  {source_type.title()}:")
            report.append(f"    Requests: {source_stats['count']}")
            report.append(f"    Success: {source_stats['success_rate']}%")
            report.append(f"    P95 Latency: {source_stats['p95_latency']}s {target_icon}")
            report.append(f"    Cache Rate: {source_stats['cache_hit_rate']}%")
        
        # Stages
        if stats['stages']:
            report.append("\n🔧 STAGE PERFORMANCE:")
            for stage, stage_stats in stats['stages'].items():
                report.append(f"  {stage}: {stage_stats['avg']:.3f}s avg, {stage_stats['p95']:.3f}s p95")
        
        # Errors
        if stats['errors']:
            report.append("\n❌ ERROR BREAKDOWN:")
            for error, count in stats['errors'].items():
                report.append(f"  {error}: {count}")
        
        return "\n".join(report)

# Global performance monitor instance
performance_monitor = PerformanceMonitor()