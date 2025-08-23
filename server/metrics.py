from __future__ import annotations

import time
import os
from typing import Any, Dict, List

# Optional psutil import for advanced system metrics
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    arr = sorted(values)
    k = max(0, min(len(arr) - 1, int(round((p / 100.0) * (len(arr) - 1)))))
    return float(arr[k])


class Metrics:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.first_token_ms: List[float] = []
        self.final_latency_ms: List[float] = []
        self.tool_call_latency_ms: List[float] = []
        self.tool_calls_attempted: int = 0
        self.tool_validation_failed: int = 0
        self.router_hits: int = 0
        self.llm_hits: int = 0
        
        # System resource monitoring
        self.memory_usage_mb: List[float] = []
        self.cpu_usage_percent: List[float] = []
        self.active_connections: List[int] = []
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        
        # Process monitoring for memory leaks
        if PSUTIL_AVAILABLE:
            self.process = psutil.Process()
            self.initial_memory_mb = self.process.memory_info().rss / 1024 / 1024

    def _cap(self, arr: List[float], value: float, cap: int = 500) -> None:
        arr.append(float(value))
        if len(arr) > cap:
            del arr[: len(arr) - cap]

    def record_first_token(self, ms: float) -> None:
        self._cap(self.first_token_ms, ms)

    def record_final_latency(self, ms: float) -> None:
        self._cap(self.final_latency_ms, ms)

    def record_tool_call_attempted(self) -> None:
        self.tool_calls_attempted += 1

    def record_tool_validation_failed(self) -> None:
        self.tool_validation_failed += 1

    def record_tool_call_latency(self, ms: float) -> None:
        self._cap(self.tool_call_latency_ms, ms)

    def record_router_hit(self) -> None:
        self.router_hits += 1

    def record_llm_hit(self) -> None:
        self.llm_hits += 1
    
    def record_cache_hit(self) -> None:
        self.cache_hits += 1
    
    def record_cache_miss(self) -> None:
        self.cache_misses += 1
    
    def record_system_metrics(self) -> None:
        """Record current system metrics for monitoring"""
        if PSUTIL_AVAILABLE:
            # Memory usage
            memory_mb = self.process.memory_info().rss / 1024 / 1024
            self._cap(self.memory_usage_mb, memory_mb, 1000)
            
            # CPU usage (non-blocking)
            try:
                cpu_percent = self.process.cpu_percent(interval=None)
                self._cap(self.cpu_usage_percent, cpu_percent, 1000)
            except:
                pass  # CPU measurement might fail occasionally
            
            # Connection count (if available)
            try:
                connections = len(self.process.connections())
                self.active_connections.append(connections)
                if len(self.active_connections) > 1000:
                    del self.active_connections[:len(self.active_connections) - 1000]
            except:
                pass  # May not have permission on some systems
    
    def get_memory_leak_info(self) -> Dict[str, Any]:
        """Get memory leak detection information"""
        if not PSUTIL_AVAILABLE or not hasattr(self, 'initial_memory_mb'):
            return {"available": False}
        
        current_memory_mb = self.process.memory_info().rss / 1024 / 1024
        memory_growth_mb = current_memory_mb - self.initial_memory_mb
        
        return {
            "available": True,
            "initial_memory_mb": self.initial_memory_mb,
            "current_memory_mb": current_memory_mb,
            "memory_growth_mb": memory_growth_mb,
            "potential_leak": memory_growth_mb > 100,  # Alert if > 100MB growth
            "memory_samples": len(self.memory_usage_mb)
        }

    def snapshot(self) -> Dict[str, Any]:
        # Record current system metrics before snapshot
        self.record_system_metrics()
        
        base_metrics = {
            "first_token_ms": {
                "count": len(self.first_token_ms),
                "p50": _percentile(self.first_token_ms, 50),
                "p95": _percentile(self.first_token_ms, 95),
            },
            "final_latency_ms": {
                "count": len(self.final_latency_ms),
                "p50": _percentile(self.final_latency_ms, 50),
                "p95": _percentile(self.final_latency_ms, 95),
            },
            "tool_call_latency_ms": {
                "count": len(self.tool_call_latency_ms),
                "p50": _percentile(self.tool_call_latency_ms, 50),
                "p95": _percentile(self.tool_call_latency_ms, 95),
            },
            "counters": {
                "tool_calls_attempted": self.tool_calls_attempted,
                "tool_validation_failed": self.tool_validation_failed,
                "router_hits": self.router_hits,
                "llm_hits": self.llm_hits,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
            },
        }
        
        # Add system metrics if available
        if PSUTIL_AVAILABLE:
            base_metrics["system"] = {
                "memory_usage_mb": {
                    "count": len(self.memory_usage_mb),
                    "current": self.memory_usage_mb[-1] if self.memory_usage_mb else 0,
                    "p50": _percentile(self.memory_usage_mb, 50),
                    "p95": _percentile(self.memory_usage_mb, 95),
                },
                "cpu_usage_percent": {
                    "count": len(self.cpu_usage_percent),
                    "current": self.cpu_usage_percent[-1] if self.cpu_usage_percent else 0,
                    "p50": _percentile(self.cpu_usage_percent, 50),
                    "p95": _percentile(self.cpu_usage_percent, 95),
                },
                "active_connections": {
                    "count": len(self.active_connections),
                    "current": self.active_connections[-1] if self.active_connections else 0,
                },
                "memory_leak_info": self.get_memory_leak_info()
            }
        
        return base_metrics


metrics = Metrics()


