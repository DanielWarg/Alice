"""
Guardian Voice Fast-Lane Policy - Priority handling for voice requests
"""

import time
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger("alice.voice.guardian_policy")

@dataclass
class VoiceFastLaneConfig:
    """Configuration for voice fast-lane policy"""
    
    # Priority settings
    priority: str = "high"
    max_queue_length: int = 3
    burst_rps: float = 8.0
    sustained_rps: float = 4.0
    
    # Resource reservations
    reserved_cpu_cores: int = 2
    reserved_memory_mb: int = 4096
    
    # Emergency thresholds (only block voice when system is truly overloaded)
    emergency_cpu_threshold: float = 85.0  # %
    emergency_memory_threshold: float = 80.0  # %
    emergency_duration_seconds: float = 10.0  # Must be sustained
    
    # Hysteresis for voice (more lenient than default)
    consecutive_failures_to_block: int = 3
    successful_requests_to_unblock: int = 1

class VoiceGuardianPolicy:
    """
    Guardian policy specifically for voice requests:
    - Higher priority than default traffic
    - More lenient blocking thresholds
    - Faster recovery
    - Resource reservations
    """
    
    def __init__(self, config: Optional[VoiceFastLaneConfig] = None):
        self.config = config or VoiceFastLaneConfig()
        
        # State tracking
        self.consecutive_failures = 0
        self.last_success_time = time.time()
        self.emergency_start_time: Optional[float] = None
        self.is_blocked = False
        
        # Rate limiting
        self.request_times = []  # Sliding window for RPS calculation
        self.window_duration = 60.0  # 1 minute window
        
        # Metrics
        self.total_requests = 0
        self.blocked_requests = 0
        self.emergency_blocks = 0
        
    def should_allow_request(self, system_metrics: Dict[str, Any]) -> tuple[bool, str]:
        """
        Determine if voice request should be allowed based on:
        1. Rate limiting
        2. Queue length
        3. Emergency system state
        4. Consecutive failures
        """
        
        now = time.time()
        self.total_requests += 1
        
        # Check rate limits
        allow_rate, rate_reason = self._check_rate_limits(now)
        if not allow_rate:
            self.blocked_requests += 1
            return False, f"voice_rate_limit: {rate_reason}"
        
        # Check queue length
        queue_length = system_metrics.get("voice_queue_length", 0)
        if queue_length >= self.config.max_queue_length:
            self.blocked_requests += 1
            return False, f"voice_queue_full: {queue_length}/{self.config.max_queue_length}"
        
        # Check emergency system state (only block voice in extreme cases)
        allow_emergency, emergency_reason = self._check_emergency_state(system_metrics, now)
        if not allow_emergency:
            self.blocked_requests += 1
            self.emergency_blocks += 1
            return False, f"voice_emergency: {emergency_reason}"
        
        # Check consecutive failures (voice-specific hysteresis)
        if self.is_blocked:
            # Voice unblocks faster - just need 1 success
            logger.debug("Voice still blocked, waiting for system recovery")
            return False, f"voice_blocked: {self.consecutive_failures} consecutive failures"
        
        # Allow the request
        self.request_times.append(now)
        return True, "voice_fastlane_allowed"
    
    def record_request_result(self, success: bool, error: Optional[str] = None):
        """Record the result of a voice request for hysteresis logic"""
        
        now = time.time()
        
        if success:
            self.consecutive_failures = 0
            self.last_success_time = now
            
            # Unblock immediately after 1 success (voice-specific)
            if self.is_blocked:
                self.is_blocked = False
                logger.info("Voice fast-lane unblocked after successful request")
        else:
            self.consecutive_failures += 1
            logger.warning(f"Voice request failed: {error} (consecutive: {self.consecutive_failures})")
            
            # Block after 3 consecutive failures (voice-specific threshold)
            if self.consecutive_failures >= self.config.consecutive_failures_to_block:
                self.is_blocked = True
                logger.error(f"Voice fast-lane blocked after {self.consecutive_failures} consecutive failures")
    
    def _check_rate_limits(self, now: float) -> tuple[bool, str]:
        """Check if request is within rate limits"""
        
        # Clean old requests from sliding window
        cutoff_time = now - self.window_duration
        self.request_times = [t for t in self.request_times if t > cutoff_time]
        
        current_rps = len(self.request_times) / self.window_duration
        
        # Check burst limit (short term)
        recent_requests = [t for t in self.request_times if t > now - 1.0]  # Last second
        if len(recent_requests) >= self.config.burst_rps:
            return False, f"burst_exceeded: {len(recent_requests)}/{self.config.burst_rps} rps"
        
        # Check sustained limit (long term)
        if current_rps > self.config.sustained_rps:
            return False, f"sustained_exceeded: {current_rps:.1f}/{self.config.sustained_rps} rps"
        
        return True, "rate_ok"
    
    def _check_emergency_state(self, system_metrics: Dict[str, Any], now: float) -> tuple[bool, str]:
        """Check if system is in emergency state requiring voice blocking"""
        
        cpu_usage = system_metrics.get("cpu_usage_percent", 0)
        memory_usage = system_metrics.get("memory_usage_percent", 0)
        
        # Check if system is above emergency thresholds
        cpu_emergency = cpu_usage > self.config.emergency_cpu_threshold
        memory_emergency = memory_usage > self.config.emergency_memory_threshold
        
        emergency_active = cpu_emergency or memory_emergency
        
        if emergency_active:
            if self.emergency_start_time is None:
                self.emergency_start_time = now
                logger.warning(f"Emergency state detected: CPU={cpu_usage}% RAM={memory_usage}%")
            
            # Only block voice if emergency state is sustained
            emergency_duration = now - self.emergency_start_time
            if emergency_duration >= self.config.emergency_duration_seconds:
                return False, f"sustained_emergency: CPU={cpu_usage}% RAM={memory_usage}% for {emergency_duration:.1f}s"
        else:
            # Clear emergency state
            if self.emergency_start_time is not None:
                logger.info("Emergency state cleared")
                self.emergency_start_time = None
        
        return True, "system_ok"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get policy metrics for monitoring"""
        
        now = time.time()
        
        # Calculate current RPS
        recent_requests = [t for t in self.request_times if t > now - self.window_duration]
        current_rps = len(recent_requests) / self.window_duration
        
        # Calculate success rate
        success_rate = ((self.total_requests - self.blocked_requests) / self.total_requests * 100) if self.total_requests > 0 else 100
        
        return {
            "policy": "voice_fastlane",
            "total_requests": self.total_requests,
            "blocked_requests": self.blocked_requests,
            "success_rate_percent": round(success_rate, 1),
            "emergency_blocks": self.emergency_blocks,
            "current_rps": round(current_rps, 2),
            "consecutive_failures": self.consecutive_failures,
            "is_blocked": self.is_blocked,
            "emergency_active": self.emergency_start_time is not None,
            "config": {
                "burst_rps": self.config.burst_rps,
                "sustained_rps": self.config.sustained_rps,
                "max_queue_length": self.config.max_queue_length,
                "emergency_cpu_threshold": self.config.emergency_cpu_threshold,
                "emergency_memory_threshold": self.config.emergency_memory_threshold
            }
        }

# Global voice policy instance
voice_guardian_policy = VoiceGuardianPolicy()