"""
Alice AI Assistant - Performance Profiler
Comprehensive CPU/RAM monitoring for always-on voice operations
"""

import asyncio
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# Optional imports for advanced profiling
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import memory_profiler
    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False

try:
    import cProfile
    import pstats
    import io
    CPROFILE_AVAILABLE = True
except ImportError:
    CPROFILE_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class PerformanceSample:
    """Single performance measurement sample"""
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_bytes_sent: float
    network_bytes_recv: float
    thread_count: int
    file_descriptors: int
    voice_processing_active: bool
    concurrent_users: int
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = data['timestamp'].isoformat()
        return data


@dataclass
class PerformanceBudget:
    """Performance budget thresholds and targets"""
    cpu_average_max: float = 30.0  # % - Average CPU usage should not exceed 30%
    cpu_peak_max: float = 80.0     # % - Peak CPU usage should not exceed 80%
    memory_mb_max: float = 1024.0  # MB - Memory usage should not exceed 1GB
    memory_growth_rate_mb_per_hour: float = 10.0  # MB/hour - Memory growth threshold
    response_time_p95_ms: float = 500.0  # ms - 95th percentile response time
    voice_processing_latency_ms: float = 200.0  # ms - Voice processing latency
    concurrent_users_max: int = 50  # Maximum concurrent users
    disk_io_mb_per_hour: float = 100.0  # MB/hour - Disk I/O threshold
    
    def check_compliance(self, metrics: 'PerformanceMetrics') -> Dict[str, Any]:
        """Check if current metrics comply with performance budgets"""
        violations = []
        
        if metrics.cpu_average > self.cpu_average_max:
            violations.append({
                'metric': 'cpu_average',
                'value': metrics.cpu_average,
                'threshold': self.cpu_average_max,
                'severity': 'warning'
            })
        
        if metrics.cpu_peak > self.cpu_peak_max:
            violations.append({
                'metric': 'cpu_peak',
                'value': metrics.cpu_peak,
                'threshold': self.cpu_peak_max,
                'severity': 'critical'
            })
        
        if metrics.memory_current_mb > self.memory_mb_max:
            violations.append({
                'metric': 'memory_current',
                'value': metrics.memory_current_mb,
                'threshold': self.memory_mb_max,
                'severity': 'critical'
            })
        
        if metrics.memory_growth_rate_mb_per_hour > self.memory_growth_rate_mb_per_hour:
            violations.append({
                'metric': 'memory_growth_rate',
                'value': metrics.memory_growth_rate_mb_per_hour,
                'threshold': self.memory_growth_rate_mb_per_hour,
                'severity': 'warning'
            })
        
        return {
            'compliant': len(violations) == 0,
            'violations': violations,
            'score': max(0, 100 - len(violations) * 20)  # Simple scoring system
        }


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics over a time period"""
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    sample_count: int
    
    # CPU metrics
    cpu_average: float
    cpu_peak: float
    cpu_p95: float
    
    # Memory metrics
    memory_current_mb: float
    memory_peak_mb: float
    memory_average_mb: float
    memory_growth_rate_mb_per_hour: float
    
    # I/O metrics
    disk_read_mb_total: float
    disk_write_mb_total: float
    network_sent_mb_total: float
    network_recv_mb_total: float
    
    # System metrics
    thread_count_average: float
    file_descriptors_average: float
    
    # Voice-specific metrics
    voice_active_percentage: float
    concurrent_users_peak: int
    concurrent_users_average: float


class VoiceOperationProfiler:
    """Specialized profiler for voice operations"""
    
    def __init__(self):
        self.voice_sessions: Dict[str, Dict[str, Any]] = {}
        self.processing_times: List[float] = []
        
    def start_voice_session(self, session_id: str) -> None:
        """Start profiling a voice session"""
        self.voice_sessions[session_id] = {
            'start_time': time.time(),
            'cpu_start': None,
            'memory_start': None,
            'operations': []
        }
        
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            self.voice_sessions[session_id]['cpu_start'] = process.cpu_percent()
            self.voice_sessions[session_id]['memory_start'] = process.memory_info().rss / 1024 / 1024
    
    def record_voice_operation(self, session_id: str, operation: str, duration_ms: float) -> None:
        """Record a voice operation within a session"""
        if session_id in self.voice_sessions:
            self.voice_sessions[session_id]['operations'].append({
                'operation': operation,
                'duration_ms': duration_ms,
                'timestamp': time.time()
            })
    
    def end_voice_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """End profiling a voice session and return metrics"""
        if session_id not in self.voice_sessions:
            return None
        
        session = self.voice_sessions[session_id]
        end_time = time.time()
        total_duration = end_time - session['start_time']
        
        metrics = {
            'session_id': session_id,
            'total_duration_ms': total_duration * 1000,
            'operations': session['operations'],
            'operations_count': len(session['operations']),
            'average_operation_ms': sum(op['duration_ms'] for op in session['operations']) / max(1, len(session['operations']))
        }
        
        if PSUTIL_AVAILABLE and session['cpu_start'] is not None:
            process = psutil.Process()
            metrics['cpu_usage'] = process.cpu_percent() - session['cpu_start']
            metrics['memory_usage_mb'] = process.memory_info().rss / 1024 / 1024 - session['memory_start']
        
        # Clean up
        del self.voice_sessions[session_id]
        self.processing_times.append(total_duration * 1000)
        
        return metrics


class PerformanceProfiler:
    """Main performance profiler for Alice AI Assistant"""
    
    def __init__(self, 
                 sample_interval: float = 5.0,
                 max_samples: int = 17280,  # 24 hours at 5s intervals
                 profile_directory: str = "./data/performance_profiles"):
        self.sample_interval = sample_interval
        self.max_samples = max_samples
        self.profile_directory = Path(profile_directory)
        self.profile_directory.mkdir(parents=True, exist_ok=True)
        
        self.samples: List[PerformanceSample] = []
        self.budget = PerformanceBudget()
        self.voice_profiler = VoiceOperationProfiler()
        
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # CPU profiling
        self.cpu_profiler = None
        self.profile_stats = None
        
        # Initial system state
        if PSUTIL_AVAILABLE:
            self.process = psutil.Process()
            self.initial_memory = self.process.memory_info().rss / 1024 / 1024
            self.initial_time = time.time()
            
            # Get initial I/O counters
            try:
                io_counters = self.process.io_counters()
                self.initial_disk_read = io_counters.read_bytes / 1024 / 1024
                self.initial_disk_write = io_counters.write_bytes / 1024 / 1024
            except:
                self.initial_disk_read = 0
                self.initial_disk_write = 0
                
            # Get initial network counters
            try:
                net_counters = psutil.net_io_counters()
                self.initial_net_sent = net_counters.bytes_sent / 1024 / 1024
                self.initial_net_recv = net_counters.bytes_recv / 1024 / 1024
            except:
                self.initial_net_sent = 0
                self.initial_net_recv = 0
        
        self.concurrent_users = 0
        self.voice_processing_active = False
    
    def set_concurrent_users(self, count: int) -> None:
        """Update concurrent user count"""
        self.concurrent_users = count
    
    def set_voice_processing_active(self, active: bool) -> None:
        """Update voice processing status"""
        self.voice_processing_active = active
    
    def start_cpu_profiling(self) -> None:
        """Start CPU profiling using cProfile"""
        if CPROFILE_AVAILABLE:
            self.cpu_profiler = cProfile.Profile()
            self.cpu_profiler.enable()
    
    def stop_cpu_profiling(self) -> Optional[Dict[str, Any]]:
        """Stop CPU profiling and return top functions"""
        if not CPROFILE_AVAILABLE or not self.cpu_profiler:
            return None
        
        self.cpu_profiler.disable()
        
        # Capture profiling results
        s = io.StringIO()
        ps = pstats.Stats(self.cpu_profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions
        
        profile_text = s.getvalue()
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        profile_file = self.profile_directory / f"cpu_profile_{timestamp}.prof"
        self.cpu_profiler.dump_stats(str(profile_file))
        
        return {
            'profile_file': str(profile_file),
            'top_functions': profile_text,
            'timestamp': datetime.now().isoformat()
        }
    
    def collect_sample(self) -> Optional[PerformanceSample]:
        """Collect a single performance sample"""
        if not PSUTIL_AVAILABLE:
            return None
        
        try:
            # CPU and memory
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = self.process.memory_percent()
            
            # I/O counters
            try:
                io_counters = self.process.io_counters()
                disk_read_mb = io_counters.read_bytes / 1024 / 1024 - self.initial_disk_read
                disk_write_mb = io_counters.write_bytes / 1024 / 1024 - self.initial_disk_write
            except:
                disk_read_mb = 0
                disk_write_mb = 0
            
            # Network counters
            try:
                net_counters = psutil.net_io_counters()
                net_sent = net_counters.bytes_sent / 1024 / 1024 - self.initial_net_sent
                net_recv = net_counters.bytes_recv / 1024 / 1024 - self.initial_net_recv
            except:
                net_sent = 0
                net_recv = 0
            
            # Thread and file descriptor count
            try:
                thread_count = self.process.num_threads()
                fd_count = self.process.num_fds() if hasattr(self.process, 'num_fds') else 0
            except:
                thread_count = 0
                fd_count = 0
            
            sample = PerformanceSample(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                disk_io_read_mb=disk_read_mb,
                disk_io_write_mb=disk_write_mb,
                network_bytes_sent=net_sent,
                network_bytes_recv=net_recv,
                thread_count=thread_count,
                file_descriptors=fd_count,
                voice_processing_active=self.voice_processing_active,
                concurrent_users=self.concurrent_users
            )
            
            return sample
            
        except Exception as e:
            logger.warning(f"Failed to collect performance sample: {e}")
            return None
    
    def add_sample(self, sample: PerformanceSample) -> None:
        """Add a performance sample to the collection"""
        self.samples.append(sample)
        
        # Maintain maximum sample count
        if len(self.samples) > self.max_samples:
            self.samples = self.samples[-self.max_samples:]
    
    def calculate_metrics(self, 
                         start_time: Optional[datetime] = None, 
                         end_time: Optional[datetime] = None) -> Optional[PerformanceMetrics]:
        """Calculate performance metrics for a time period"""
        if not self.samples:
            return None
        
        # Filter samples by time range
        if start_time or end_time:
            filtered_samples = []
            for sample in self.samples:
                if start_time and sample.timestamp < start_time:
                    continue
                if end_time and sample.timestamp > end_time:
                    continue
                filtered_samples.append(sample)
        else:
            filtered_samples = self.samples
        
        if not filtered_samples:
            return None
        
        # Calculate aggregated metrics
        start_time = start_time or filtered_samples[0].timestamp
        end_time = end_time or filtered_samples[-1].timestamp
        duration_seconds = (end_time - start_time).total_seconds()
        
        cpu_values = [s.cpu_percent for s in filtered_samples]
        memory_values = [s.memory_mb for s in filtered_samples]
        thread_counts = [s.thread_count for s in filtered_samples]
        fd_counts = [s.file_descriptors for s in filtered_samples]
        
        # Voice activity percentage
        voice_active_count = sum(1 for s in filtered_samples if s.voice_processing_active)
        voice_active_percentage = (voice_active_count / len(filtered_samples)) * 100
        
        # Concurrent users
        user_counts = [s.concurrent_users for s in filtered_samples]
        
        # Memory growth rate (MB per hour)
        if len(memory_values) > 1 and duration_seconds > 0:
            memory_growth = memory_values[-1] - memory_values[0]
            memory_growth_rate = (memory_growth / duration_seconds) * 3600  # per hour
        else:
            memory_growth_rate = 0
        
        return PerformanceMetrics(
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            sample_count=len(filtered_samples),
            
            cpu_average=sum(cpu_values) / len(cpu_values),
            cpu_peak=max(cpu_values),
            cpu_p95=self._percentile(cpu_values, 95),
            
            memory_current_mb=memory_values[-1],
            memory_peak_mb=max(memory_values),
            memory_average_mb=sum(memory_values) / len(memory_values),
            memory_growth_rate_mb_per_hour=memory_growth_rate,
            
            disk_read_mb_total=filtered_samples[-1].disk_io_read_mb if filtered_samples else 0,
            disk_write_mb_total=filtered_samples[-1].disk_io_write_mb if filtered_samples else 0,
            network_sent_mb_total=filtered_samples[-1].network_bytes_sent if filtered_samples else 0,
            network_recv_mb_total=filtered_samples[-1].network_bytes_recv if filtered_samples else 0,
            
            thread_count_average=sum(thread_counts) / len(thread_counts) if thread_counts else 0,
            file_descriptors_average=sum(fd_counts) / len(fd_counts) if fd_counts else 0,
            
            voice_active_percentage=voice_active_percentage,
            concurrent_users_peak=max(user_counts) if user_counts else 0,
            concurrent_users_average=sum(user_counts) / len(user_counts) if user_counts else 0
        )
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        k = max(0, min(len(sorted_values) - 1, int(round((percentile / 100.0) * (len(sorted_values) - 1)))))
        return sorted_values[k]
    
    async def start_monitoring(self) -> None:
        """Start continuous performance monitoring"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info(f"Starting performance monitoring with {self.sample_interval}s intervals")
        
        while self.is_running:
            sample = self.collect_sample()
            if sample:
                self.add_sample(sample)
            
            await asyncio.sleep(self.sample_interval)
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
        logger.info("Stopped performance monitoring")
    
    def save_profile_data(self, filename_prefix: str = "performance_profile") -> str:
        """Save current profile data to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.json"
        filepath = self.profile_directory / filename
        
        # Calculate current metrics
        metrics = self.calculate_metrics()
        budget_compliance = self.budget.check_compliance(metrics) if metrics else {}
        
        profile_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'sample_count': len(self.samples),
                'duration_seconds': (datetime.now() - self.samples[0].timestamp).total_seconds() if self.samples else 0,
                'sample_interval': self.sample_interval,
                'psutil_available': PSUTIL_AVAILABLE,
                'memory_profiler_available': MEMORY_PROFILER_AVAILABLE
            },
            'performance_budget': asdict(self.budget),
            'budget_compliance': budget_compliance,
            'metrics': asdict(metrics) if metrics else {},
            'samples': [sample.to_dict() for sample in self.samples],
            'voice_operations': {
                'processing_times_ms': self.voice_profiler.processing_times[-1000:],  # Last 1000 operations
                'active_sessions': len(self.voice_profiler.voice_sessions)
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(profile_data, f, indent=2, default=str)
        
        logger.info(f"Performance profile saved to {filepath}")
        return str(filepath)
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current performance status"""
        if not self.samples:
            return {'status': 'no_data', 'samples_collected': 0}
        
        latest_sample = self.samples[-1]
        metrics = self.calculate_metrics()
        budget_compliance = self.budget.check_compliance(metrics) if metrics else {}
        
        return {
            'status': 'monitoring' if self.is_running else 'stopped',
            'samples_collected': len(self.samples),
            'latest_sample': latest_sample.to_dict(),
            'current_metrics': asdict(metrics) if metrics else {},
            'budget_compliance': budget_compliance,
            'monitoring_duration_hours': (datetime.now() - self.samples[0].timestamp).total_seconds() / 3600,
            'voice_profiler': {
                'active_sessions': len(self.voice_profiler.voice_sessions),
                'total_operations': len(self.voice_profiler.processing_times)
            }
        }


# Global profiler instance
profiler = PerformanceProfiler()