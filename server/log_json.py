#!/usr/bin/env python3
"""
Strukturerad JSON Logger - NDJSON för korrelation
=================================================

Mini-logger för FastAPI som skriver NDJSON med ts, lvl, evt, req_id, user_id, 
lane, latency_ms för korrelationsanalys.

Features:
- NDJSON output (newline-delimited JSON) 
- Automatisk request correlation
- UX-KPI tracking (e2e_ms, tts_ttfa_ms, fallback_rate)
- Log rotation och disk-guard
- Performance optimized för hög throughput
"""

import json
import sys
import time
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Union
from pathlib import Path
from collections import defaultdict

class JSONLogger:
    """
    High-performance NDJSON logger för structured logging.
    """
    
    def __init__(self, output_file: str = None, max_size_mb: int = 50, max_files: int = 10):
        self.output_file = output_file
        self.max_size_mb = max_size_mb
        self.max_files = max_files
        
        # File handle eller stdout
        self._file_handle = None
        self._current_size = 0
        self._lock = threading.RLock()
        
        # Performance metrics
        self.logs_written = 0
        self.bytes_written = 0
        self.last_rotation = time.time()
        
        # Open output file if specified
        if self.output_file:
            self._open_log_file()
    
    def _open_log_file(self):
        """Open/reopen log file handle."""
        try:
            if self._file_handle:
                self._file_handle.close()
            
            log_path = Path(self.output_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._file_handle = open(log_path, 'a', encoding='utf-8', buffering=1)  # Line buffering
            self._current_size = log_path.stat().st_size if log_path.exists() else 0
            
        except Exception as e:
            print(f"Failed to open log file {self.output_file}: {e}", file=sys.stderr)
            self._file_handle = None
    
    def _rotate_if_needed(self):
        """Rotate log file if size limit exceeded."""
        if not self.output_file or self._current_size < (self.max_size_mb * 1024 * 1024):
            return
        
        try:
            log_path = Path(self.output_file)
            
            # Rotate existing files
            for i in range(self.max_files - 1, 0, -1):
                old_file = log_path.with_suffix(f'.{i}.jsonl')
                new_file = log_path.with_suffix(f'.{i+1}.jsonl') 
                
                if old_file.exists():
                    if i == self.max_files - 1:
                        old_file.unlink()  # Delete oldest
                    else:
                        old_file.rename(new_file)
            
            # Move current to .1
            if log_path.exists():
                log_path.rename(log_path.with_suffix('.1.jsonl'))
            
            # Reopen current file
            self._open_log_file()
            self.last_rotation = time.time()
            
        except Exception as e:
            print(f"Log rotation failed: {e}", file=sys.stderr)
    
    def log(self, event: str, level: str = 'INFO', **kwargs):
        """
        Log structured event.
        
        Args:
            event: Event type (e.g. 'chat.req', 'guardian.action')
            level: Log level (DEBUG, INFO, WARN, ERROR, CRITICAL)
            **kwargs: Additional structured data
        """
        
        with self._lock:
            # Build log record
            record = {
                'ts': time.time(),
                'lvl': level,
                'evt': event,
                **kwargs
            }
            
            # Serialize to JSON
            try:
                json_line = json.dumps(record, ensure_ascii=False, separators=(',', ':'))
                json_line += '\n'
                
                # Write to output
                if self._file_handle:
                    self._file_handle.write(json_line)
                    self._file_handle.flush()
                    self._current_size += len(json_line.encode('utf-8'))
                    self._rotate_if_needed()
                else:
                    # Fallback to stdout
                    sys.stdout.write(json_line)
                    sys.stdout.flush()
                
                # Update metrics
                self.logs_written += 1
                self.bytes_written += len(json_line.encode('utf-8'))
                
            except Exception as e:
                # Emergency fallback - don't let logging break the app
                print(f"JSON log failed: {e}", file=sys.stderr)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get logger performance metrics."""
        return {
            'logs_written': self.logs_written,
            'bytes_written': self.bytes_written,
            'current_file_size': self._current_size,
            'output_file': self.output_file,
            'last_rotation': self.last_rotation,
            'rotation_age_hours': (time.time() - self.last_rotation) / 3600
        }


# Global logger instance
_json_logger = None

def get_json_logger() -> JSONLogger:
    """Get global JSON logger instance."""
    global _json_logger
    if _json_logger is None:
        # Default to structured stdout, can be configured later
        _json_logger = JSONLogger()
    return _json_logger

def configure_json_logger(output_file: str = None, **kwargs):
    """Configure global JSON logger."""
    global _json_logger
    _json_logger = JSONLogger(output_file=output_file, **kwargs)

def jlog(event: str, level: str = 'INFO', **kwargs):
    """
    Convenience function för structured logging.
    
    Example:
        jlog('chat.req', req_id='abc123', text_len=45, user_id='user_456')
        jlog('guardian.action', action='degrade', ram_pct=0.87, level='WARN')
    """
    get_json_logger().log(event, level=level, **kwargs)


# Request correlation helper
class RequestCorrelator:
    """
    Helper för att korrelera events inom samma request.
    Används tillsammans med middleware för automatisk request tracking.
    """
    
    def __init__(self):
        self._request_data = threading.local()
    
    def set_request_context(self, req_id: str, user_id: str = None, 
                          lane: str = None, start_time: float = None):
        """Set context för current request."""
        self._request_data.req_id = req_id
        self._request_data.user_id = user_id
        self._request_data.lane = lane
        self._request_data.start_time = start_time or time.time()
    
    def log_request_event(self, event: str, level: str = 'INFO', **kwargs):
        """Log event med automatisk request correlation."""
        
        # Add request context
        context = {}
        if hasattr(self._request_data, 'req_id'):
            context['req_id'] = self._request_data.req_id
        if hasattr(self._request_data, 'user_id'):  
            context['user_id'] = self._request_data.user_id
        if hasattr(self._request_data, 'lane'):
            context['lane'] = self._request_data.lane
        if hasattr(self._request_data, 'start_time'):
            context['latency_ms'] = int((time.time() - self._request_data.start_time) * 1000)
        
        # Log med context
        jlog(event, level=level, **context, **kwargs)
    
    def get_request_id(self) -> Optional[str]:
        """Get current request ID."""
        return getattr(self._request_data, 'req_id', None)


# Global request correlator
_correlator = RequestCorrelator()

def rlog(event: str, level: str = 'INFO', **kwargs):
    """
    Request-aware logging convenience function.
    Automatiskt lägger till req_id, user_id, lane, latency_ms.
    """
    _correlator.log_request_event(event, level=level, **kwargs)

def set_request_context(req_id: str, user_id: str = None, lane: str = None):
    """Set request context för correlation."""
    _correlator.set_request_context(req_id, user_id, lane)


# UX KPI tracking helpers
class KPITracker:
    """
    Helper för att tracka UX-KPIs och korrelera med Guardian-metrics.
    """
    
    def __init__(self):
        self._metrics = defaultdict(list)
        self._lock = threading.RLock()
    
    def track_e2e_latency(self, latency_ms: int, req_id: str = None):
        """Track end-to-end response latency."""
        with self._lock:
            self._metrics['e2e_ms'].append(latency_ms)
            jlog('kpi.e2e_latency', latency_ms=latency_ms, req_id=req_id)
    
    def track_tts_ttfa(self, ttfa_ms: int, req_id: str = None):
        """Track TTS time-to-first-audio."""
        with self._lock:
            self._metrics['tts_ttfa_ms'].append(ttfa_ms)
            jlog('kpi.tts_ttfa', ttfa_ms=ttfa_ms, req_id=req_id)
    
    def track_fallback(self, fallback_type: str, reason: str, req_id: str = None):
        """Track fallback events (degraded responses, etc)."""
        with self._lock:
            self._metrics['fallbacks'].append({
                'type': fallback_type,
                'reason': reason,
                'timestamp': time.time()
            })
            jlog('kpi.fallback', type=fallback_type, reason=reason, req_id=req_id)
    
    def get_recent_stats(self, window_minutes: int = 5) -> Dict[str, Any]:
        """Get KPI statistics for recent window."""
        cutoff = time.time() - (window_minutes * 60)
        
        with self._lock:
            # Filter recent metrics
            recent_e2e = [x for x in self._metrics['e2e_ms'] if x > cutoff] # Simplified 
            recent_ttfa = [x for x in self._metrics['tts_ttfa_ms'] if x > cutoff]
            recent_fallbacks = [x for x in self._metrics['fallbacks'] if x['timestamp'] > cutoff]
            
            stats = {
                'window_minutes': window_minutes,
                'e2e_latency': {
                    'count': len(recent_e2e),
                    'avg': sum(recent_e2e) / len(recent_e2e) if recent_e2e else 0,
                    'p95': sorted(recent_e2e)[int(0.95 * len(recent_e2e))] if recent_e2e else 0
                },
                'tts_ttfa': {
                    'count': len(recent_ttfa), 
                    'avg': sum(recent_ttfa) / len(recent_ttfa) if recent_ttfa else 0
                },
                'fallback_rate': len(recent_fallbacks) / max(len(recent_e2e), 1)
            }
            
            return stats


# Global KPI tracker
_kpi_tracker = KPITracker()

def track_e2e_latency(latency_ms: int, req_id: str = None):
    """Track end-to-end latency KPI.""" 
    _kpi_tracker.track_e2e_latency(latency_ms, req_id)

def track_tts_ttfa(ttfa_ms: int, req_id: str = None):
    """Track TTS time-to-first-audio KPI."""
    _kpi_tracker.track_tts_ttfa(ttfa_ms, req_id)

def track_fallback(fallback_type: str, reason: str, req_id: str = None):
    """Track fallback event KPI."""
    _kpi_tracker.track_fallback(fallback_type, reason, req_id)

def get_kpi_stats(window_minutes: int = 5) -> Dict[str, Any]:
    """Get recent KPI statistics."""
    return _kpi_tracker.get_recent_stats(window_minutes)


if __name__ == "__main__":
    # Test structured logging
    print("Testing JSON logger...")
    
    # Configure för test
    configure_json_logger("test_logs/alice.jsonl")
    
    # Test basic logging
    jlog('test.start', test_id='123', level='INFO')
    jlog('chat.req', req_id='req_456', text_len=42, user_id='user_789')
    jlog('guardian.metrics', ram_pct=0.73, cpu_pct=0.45, level='DEBUG')
    jlog('chat.resp', req_id='req_456', resp_len=156, latency_ms=2340)
    
    # Test request correlation  
    set_request_context('req_999', user_id='user_abc', lane='chat')
    rlog('chat.llm_start')
    time.sleep(0.1)
    rlog('chat.llm_complete', tokens=45)
    
    # Test KPI tracking
    track_e2e_latency(2340, 'req_456')
    track_tts_ttfa(250, 'req_456')
    track_fallback('model_switch', 'guardian_brownout', 'req_456')
    
    print("KPI Stats:", get_kpi_stats())
    print("Logger metrics:", get_json_logger().get_metrics())
    print("Test completed - check test_logs/alice.jsonl")