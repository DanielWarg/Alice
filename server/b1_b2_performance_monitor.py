"""
Alice AI Assistant - B1/B2 Specific Performance Monitoring
Specialized CPU/RAM monitoring for Ambient Memory (B1) and Barge-in & Echo (B2) systems
"""

import asyncio
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import statistics

# Import the main performance profiler
from performance_profiler import profiler, PerformanceSample, PerformanceMetrics

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class B1PerformanceMetrics:
    """Performance metrics specific to B1 (Ambient Memory) system"""
    timestamp: datetime
    
    # Memory metrics
    ambient_db_size_mb: float
    raw_chunks_count: int
    memory_summaries_count: int
    cache_memory_mb: float
    
    # Processing metrics
    chunk_ingestion_rate_per_min: float
    summary_generation_rate_per_min: float
    database_query_avg_latency_ms: float
    
    # CPU usage during B1 operations
    ambient_processing_cpu_percent: float
    llm_summary_cpu_percent: float
    database_operations_cpu_percent: float
    
    # Resource efficiency
    chunks_per_mb_memory: float
    summaries_per_cpu_second: float
    memory_growth_rate_mb_per_hour: float
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = data['timestamp'].isoformat()
        return data


@dataclass
class B2PerformanceMetrics:
    """Performance metrics specific to B2 (Barge-in & Echo) system"""
    timestamp: datetime
    
    # Voice processing metrics
    voice_sessions_active: int
    barge_in_detections_per_min: float
    echo_cancellation_active: bool
    audio_buffer_size_mb: float
    
    # Latency metrics
    barge_in_detection_latency_ms: float
    echo_cancellation_latency_ms: float
    audio_processing_p95_latency_ms: float
    voice_activity_detection_latency_ms: float
    
    # CPU usage during B2 operations
    voice_processing_cpu_percent: float
    barge_in_detection_cpu_percent: float
    echo_cancellation_cpu_percent: float
    audio_analysis_cpu_percent: float
    
    # Audio quality metrics
    signal_to_noise_ratio_db: float
    echo_suppression_db: float
    voice_activity_accuracy_percent: float
    false_positive_rate_per_min: float
    
    # Resource efficiency
    concurrent_streams_supported: int
    audio_buffer_efficiency_percent: float
    spectral_analysis_cpu_efficiency: float
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = data['timestamp'].isoformat()
        return data


@dataclass
class CombinedB1B2Metrics:
    """Combined performance metrics for B1+B2 integration"""
    timestamp: datetime
    
    # Integration metrics
    voice_to_memory_latency_ms: float
    memory_retrieval_for_voice_ms: float
    cross_system_cpu_overhead_percent: float
    
    # Efficiency metrics
    total_system_memory_mb: float
    combined_cpu_usage_percent: float
    integration_overhead_percent: float
    
    # User experience metrics
    end_to_end_voice_latency_ms: float
    memory_enhanced_response_quality: float
    system_responsiveness_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = data['timestamp'].isoformat()
        return data


class B1PerformanceMonitor:
    """Performance monitor for Ambient Memory (B1) system"""
    
    def __init__(self):
        self.metrics_history: List[B1PerformanceMetrics] = []
        self.last_metrics_time = time.time()
        self.chunk_ingestion_count = 0
        self.summary_generation_count = 0
        self.database_query_times = []
        
        # Database monitoring
        self.db_path = Path(__file__).parent / "data" / "ambient.db"
        
    async def collect_b1_metrics(self) -> B1PerformanceMetrics:
        """Collect B1-specific performance metrics"""
        timestamp = datetime.now()
        
        try:
            # Database metrics
            db_size_mb = self._get_database_size_mb()
            raw_chunks, summaries = self._get_database_counts()
            
            # Cache memory usage
            cache_memory_mb = self._estimate_cache_memory_usage()
            
            # Processing rates (since last collection)
            current_time = time.time()
            time_diff_min = (current_time - self.last_metrics_time) / 60
            
            chunk_rate = self.chunk_ingestion_count / max(time_diff_min, 0.01)
            summary_rate = self.summary_generation_count / max(time_diff_min, 0.01)
            
            # Database query performance
            avg_query_latency = statistics.mean(self.database_query_times) if self.database_query_times else 0
            
            # CPU monitoring (estimated based on process activity)
            ambient_cpu, llm_cpu, db_cpu = self._estimate_b1_cpu_usage()
            
            # Efficiency metrics
            chunks_per_mb = raw_chunks / max(cache_memory_mb, 1)
            summaries_per_cpu = summary_rate / max(ambient_cpu / 100, 0.01)
            
            # Memory growth estimation
            memory_growth_rate = self._calculate_memory_growth_rate(cache_memory_mb)
            
            metrics = B1PerformanceMetrics(
                timestamp=timestamp,
                ambient_db_size_mb=db_size_mb,
                raw_chunks_count=raw_chunks,
                memory_summaries_count=summaries,
                cache_memory_mb=cache_memory_mb,
                chunk_ingestion_rate_per_min=chunk_rate,
                summary_generation_rate_per_min=summary_rate,
                database_query_avg_latency_ms=avg_query_latency,
                ambient_processing_cpu_percent=ambient_cpu,
                llm_summary_cpu_percent=llm_cpu,
                database_operations_cpu_percent=db_cpu,
                chunks_per_mb_memory=chunks_per_mb,
                summaries_per_cpu_second=summaries_per_cpu,
                memory_growth_rate_mb_per_hour=memory_growth_rate
            )
            
            # Update tracking variables
            self.last_metrics_time = current_time
            self.chunk_ingestion_count = 0
            self.summary_generation_count = 0
            self.database_query_times = self.database_query_times[-100:]  # Keep last 100 samples
            
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]  # Keep last 1000 samples
            
            return metrics
            
        except Exception as e:
            logger.warning(f"Failed to collect B1 metrics: {e}")
            return self._create_empty_b1_metrics(timestamp)
    
    def _get_database_size_mb(self) -> float:
        """Get ambient database size in MB"""
        try:
            if self.db_path.exists():
                return self.db_path.stat().st_size / (1024 * 1024)
        except:
            pass
        return 0.0
    
    def _get_database_counts(self) -> tuple:
        """Get count of raw chunks and summaries"""
        try:
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                raw_count = conn.execute("SELECT COUNT(*) FROM ambient_raw").fetchone()[0]
                summary_count = conn.execute(
                    "SELECT COUNT(*) FROM memory WHERE kind = 'ambient_summary'"
                ).fetchone()[0]
                return raw_count, summary_count
        except:
            return 0, 0
    
    def _estimate_cache_memory_usage(self) -> float:
        """Estimate memory usage for B1 caching"""
        # This would be enhanced with actual memory tracking
        try:
            if PSUTIL_AVAILABLE:
                process = psutil.Process()
                # Rough estimation based on database size and active operations
                db_size = self._get_database_size_mb()
                return min(db_size * 0.3, 100)  # Assume 30% of DB size or max 100MB
        except:
            pass
        return 0.0
    
    def _estimate_b1_cpu_usage(self) -> tuple:
        """Estimate CPU usage for different B1 operations"""
        # This would be enhanced with actual process monitoring
        try:
            if PSUTIL_AVAILABLE:
                # Base estimation on recent activity
                chunk_activity = min(self.chunk_ingestion_count, 10) * 2  # 2% per chunk
                summary_activity = min(self.summary_generation_count, 5) * 8  # 8% per summary
                db_activity = min(len(self.database_query_times), 20) * 0.5  # 0.5% per query
                
                return chunk_activity, summary_activity, db_activity
        except:
            pass
        return 0.0, 0.0, 0.0
    
    def _calculate_memory_growth_rate(self, current_memory: float) -> float:
        """Calculate memory growth rate in MB per hour"""
        if len(self.metrics_history) < 2:
            return 0.0
        
        # Compare with metrics from 1 hour ago (or oldest available)
        target_time = datetime.now() - timedelta(hours=1)
        
        for old_metrics in self.metrics_history:
            if old_metrics.timestamp <= target_time:
                time_diff_hours = (datetime.now() - old_metrics.timestamp).total_seconds() / 3600
                memory_diff = current_memory - old_metrics.cache_memory_mb
                return memory_diff / max(time_diff_hours, 0.1)
        
        return 0.0
    
    def _create_empty_b1_metrics(self, timestamp: datetime) -> B1PerformanceMetrics:
        """Create empty B1 metrics for error cases"""
        return B1PerformanceMetrics(
            timestamp=timestamp,
            ambient_db_size_mb=0,
            raw_chunks_count=0,
            memory_summaries_count=0,
            cache_memory_mb=0,
            chunk_ingestion_rate_per_min=0,
            summary_generation_rate_per_min=0,
            database_query_avg_latency_ms=0,
            ambient_processing_cpu_percent=0,
            llm_summary_cpu_percent=0,
            database_operations_cpu_percent=0,
            chunks_per_mb_memory=0,
            summaries_per_cpu_second=0,
            memory_growth_rate_mb_per_hour=0
        )
    
    def record_chunk_ingestion(self):
        """Record a chunk ingestion event"""
        self.chunk_ingestion_count += 1
    
    def record_summary_generation(self):
        """Record a summary generation event"""
        self.summary_generation_count += 1
    
    def record_database_query(self, duration_ms: float):
        """Record database query duration"""
        self.database_query_times.append(duration_ms)


class B2PerformanceMonitor:
    """Performance monitor for Barge-in & Echo (B2) system"""
    
    def __init__(self):
        self.metrics_history: List[B2PerformanceMetrics] = []
        self.voice_sessions = {}
        self.barge_in_detections = 0
        self.last_metrics_time = time.time()
        
        # Audio quality tracking
        self.snr_measurements = []
        self.echo_suppression_measurements = []
        self.false_positives = 0
        
        # Latency tracking
        self.barge_in_latencies = []
        self.echo_latencies = []
        self.vad_latencies = []
        self.audio_processing_latencies = []
    
    async def collect_b2_metrics(self) -> B2PerformanceMetrics:
        """Collect B2-specific performance metrics"""
        timestamp = datetime.now()
        
        try:
            # Voice session metrics
            active_sessions = len(self.voice_sessions)
            
            # Calculate rates since last collection
            current_time = time.time()
            time_diff_min = (current_time - self.last_metrics_time) / 60
            barge_in_rate = self.barge_in_detections / max(time_diff_min, 0.01)
            
            # Audio buffer estimation
            audio_buffer_mb = self._estimate_audio_buffer_size()
            
            # Latency metrics
            barge_in_latency = statistics.mean(self.barge_in_latencies) if self.barge_in_latencies else 0
            echo_latency = statistics.mean(self.echo_latencies) if self.echo_latencies else 0
            vad_latency = statistics.mean(self.vad_latencies) if self.vad_latencies else 0
            audio_p95_latency = self._calculate_p95_latency(self.audio_processing_latencies)
            
            # CPU usage estimation
            voice_cpu, barge_cpu, echo_cpu, analysis_cpu = self._estimate_b2_cpu_usage()
            
            # Audio quality metrics
            avg_snr = statistics.mean(self.snr_measurements) if self.snr_measurements else 0
            avg_echo_suppression = statistics.mean(self.echo_suppression_measurements) if self.echo_suppression_measurements else 0
            false_positive_rate = self.false_positives / max(time_diff_min, 0.01)
            
            # Efficiency metrics
            concurrent_support = self._estimate_concurrent_stream_support()
            buffer_efficiency = self._calculate_buffer_efficiency()
            spectral_efficiency = self._calculate_spectral_analysis_efficiency()
            
            metrics = B2PerformanceMetrics(
                timestamp=timestamp,
                voice_sessions_active=active_sessions,
                barge_in_detections_per_min=barge_in_rate,
                echo_cancellation_active=self._is_echo_cancellation_active(),
                audio_buffer_size_mb=audio_buffer_mb,
                barge_in_detection_latency_ms=barge_in_latency,
                echo_cancellation_latency_ms=echo_latency,
                audio_processing_p95_latency_ms=audio_p95_latency,
                voice_activity_detection_latency_ms=vad_latency,
                voice_processing_cpu_percent=voice_cpu,
                barge_in_detection_cpu_percent=barge_cpu,
                echo_cancellation_cpu_percent=echo_cpu,
                audio_analysis_cpu_percent=analysis_cpu,
                signal_to_noise_ratio_db=avg_snr,
                echo_suppression_db=avg_echo_suppression,
                voice_activity_accuracy_percent=self._calculate_vad_accuracy(),
                false_positive_rate_per_min=false_positive_rate,
                concurrent_streams_supported=concurrent_support,
                audio_buffer_efficiency_percent=buffer_efficiency,
                spectral_analysis_cpu_efficiency=spectral_efficiency
            )
            
            # Reset counters
            self.last_metrics_time = current_time
            self.barge_in_detections = 0
            self.false_positives = 0
            
            # Trim history arrays
            self._trim_measurement_arrays()
            
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
            
            return metrics
            
        except Exception as e:
            logger.warning(f"Failed to collect B2 metrics: {e}")
            return self._create_empty_b2_metrics(timestamp)
    
    def _estimate_audio_buffer_size(self) -> float:
        """Estimate audio buffer memory usage"""
        # Rough estimation based on active sessions and buffer configuration
        active_sessions = len(self.voice_sessions)
        # Assume each session uses ~5MB for audio buffers (16kHz, 16-bit, multiple buffers)
        return active_sessions * 5.0
    
    def _calculate_p95_latency(self, latencies: List[float]) -> float:
        """Calculate 95th percentile latency"""
        if not latencies:
            return 0
        sorted_latencies = sorted(latencies)
        index = int(0.95 * len(sorted_latencies))
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]
    
    def _estimate_b2_cpu_usage(self) -> tuple:
        """Estimate CPU usage for different B2 operations"""
        # Estimation based on active sessions and recent activity
        active_sessions = len(self.voice_sessions)
        
        voice_cpu = min(active_sessions * 15, 80)  # 15% per session, max 80%
        barge_cpu = min(self.barge_in_detections * 2, 20)  # 2% per detection, max 20%
        echo_cpu = 10 if self._is_echo_cancellation_active() else 0
        analysis_cpu = min(len(self.audio_processing_latencies) * 0.5, 30)  # 0.5% per analysis
        
        return voice_cpu, barge_cpu, echo_cpu, analysis_cpu
    
    def _is_echo_cancellation_active(self) -> bool:
        """Check if echo cancellation is currently active"""
        # This would check actual echo cancellation state
        return len(self.voice_sessions) > 0
    
    def _calculate_vad_accuracy(self) -> float:
        """Calculate voice activity detection accuracy"""
        # This would be based on ground truth data in a real implementation
        # For now, estimate based on false positive rate
        if self.false_positives == 0:
            return 95.0
        return max(70.0, 95.0 - (self.false_positives * 2))
    
    def _estimate_concurrent_stream_support(self) -> int:
        """Estimate how many concurrent streams the system can support"""
        if not PSUTIL_AVAILABLE:
            return 5  # Conservative estimate
        
        try:
            # Base estimate on available CPU and memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            
            # Rough calculation based on resource availability
            cpu_capacity = max(1, int((100 - cpu_percent) / 15))  # 15% CPU per stream
            memory_capacity = max(1, int((100 - memory_percent) / 10))  # 10% memory per stream
            
            return min(cpu_capacity, memory_capacity, 10)  # Cap at 10 streams
        except:
            return 5
    
    def _calculate_buffer_efficiency(self) -> float:
        """Calculate audio buffer efficiency"""
        # Efficiency based on buffer utilization vs. latency
        if not self.voice_sessions:
            return 100.0
        
        # Simple efficiency calculation based on active sessions
        active_sessions = len(self.voice_sessions)
        theoretical_max = 8  # Theoretical maximum efficient sessions
        
        return min(100.0, (theoretical_max / max(active_sessions, 1)) * 100)
    
    def _calculate_spectral_analysis_efficiency(self) -> float:
        """Calculate spectral analysis CPU efficiency"""
        # Efficiency based on processing time vs. results
        if not self.audio_processing_latencies:
            return 100.0
        
        avg_latency = statistics.mean(self.audio_processing_latencies)
        target_latency = 50  # Target 50ms processing time
        
        return min(100.0, (target_latency / max(avg_latency, 1)) * 100)
    
    def _trim_measurement_arrays(self):
        """Trim measurement arrays to prevent memory growth"""
        max_samples = 200
        
        self.snr_measurements = self.snr_measurements[-max_samples:]
        self.echo_suppression_measurements = self.echo_suppression_measurements[-max_samples:]
        self.barge_in_latencies = self.barge_in_latencies[-max_samples:]
        self.echo_latencies = self.echo_latencies[-max_samples:]
        self.vad_latencies = self.vad_latencies[-max_samples:]
        self.audio_processing_latencies = self.audio_processing_latencies[-max_samples:]
    
    def _create_empty_b2_metrics(self, timestamp: datetime) -> B2PerformanceMetrics:
        """Create empty B2 metrics for error cases"""
        return B2PerformanceMetrics(
            timestamp=timestamp,
            voice_sessions_active=0,
            barge_in_detections_per_min=0,
            echo_cancellation_active=False,
            audio_buffer_size_mb=0,
            barge_in_detection_latency_ms=0,
            echo_cancellation_latency_ms=0,
            audio_processing_p95_latency_ms=0,
            voice_activity_detection_latency_ms=0,
            voice_processing_cpu_percent=0,
            barge_in_detection_cpu_percent=0,
            echo_cancellation_cpu_percent=0,
            audio_analysis_cpu_percent=0,
            signal_to_noise_ratio_db=0,
            echo_suppression_db=0,
            voice_activity_accuracy_percent=0,
            false_positive_rate_per_min=0,
            concurrent_streams_supported=0,
            audio_buffer_efficiency_percent=0,
            spectral_analysis_cpu_efficiency=0
        )
    
    # Event recording methods
    def start_voice_session(self, session_id: str):
        """Record start of voice session"""
        self.voice_sessions[session_id] = {
            'start_time': time.time(),
            'operations': 0
        }
    
    def end_voice_session(self, session_id: str):
        """Record end of voice session"""
        if session_id in self.voice_sessions:
            del self.voice_sessions[session_id]
    
    def record_barge_in_detection(self, latency_ms: float):
        """Record barge-in detection event"""
        self.barge_in_detections += 1
        self.barge_in_latencies.append(latency_ms)
    
    def record_echo_cancellation(self, latency_ms: float, suppression_db: float):
        """Record echo cancellation metrics"""
        self.echo_latencies.append(latency_ms)
        self.echo_suppression_measurements.append(suppression_db)
    
    def record_vad_operation(self, latency_ms: float):
        """Record voice activity detection operation"""
        self.vad_latencies.append(latency_ms)
    
    def record_audio_processing(self, latency_ms: float):
        """Record general audio processing latency"""
        self.audio_processing_latencies.append(latency_ms)
    
    def record_snr_measurement(self, snr_db: float):
        """Record signal-to-noise ratio measurement"""
        self.snr_measurements.append(snr_db)
    
    def record_false_positive(self):
        """Record false positive detection"""
        self.false_positives += 1


class CombinedB1B2Monitor:
    """Combined monitoring for B1+B2 system integration"""
    
    def __init__(self, b1_monitor: B1PerformanceMonitor, b2_monitor: B2PerformanceMonitor):
        self.b1_monitor = b1_monitor
        self.b2_monitor = b2_monitor
        self.integration_metrics_history: List[CombinedB1B2Metrics] = []
        
        # Integration performance tracking
        self.voice_to_memory_latencies = []
        self.memory_retrieval_latencies = []
    
    async def collect_combined_metrics(self) -> CombinedB1B2Metrics:
        """Collect combined B1+B2 performance metrics"""
        timestamp = datetime.now()
        
        try:
            # Get individual system metrics
            b1_metrics = await self.b1_monitor.collect_b1_metrics()
            b2_metrics = await self.b2_monitor.collect_b2_metrics()
            
            # Calculate integration metrics
            voice_to_memory_latency = statistics.mean(self.voice_to_memory_latencies) if self.voice_to_memory_latencies else 0
            memory_retrieval_latency = statistics.mean(self.memory_retrieval_latencies) if self.memory_retrieval_latencies else 0
            
            # Calculate system totals
            total_memory = b1_metrics.cache_memory_mb + b2_metrics.audio_buffer_size_mb
            combined_cpu = (
                b1_metrics.ambient_processing_cpu_percent + 
                b1_metrics.llm_summary_cpu_percent +
                b2_metrics.voice_processing_cpu_percent + 
                b2_metrics.barge_in_detection_cpu_percent
            )
            
            # Integration overhead estimation
            integration_overhead = self._calculate_integration_overhead(b1_metrics, b2_metrics)
            
            # End-to-end performance metrics
            e2e_latency = (
                b2_metrics.barge_in_detection_latency_ms +
                voice_to_memory_latency +
                memory_retrieval_latency +
                b2_metrics.audio_processing_p95_latency_ms
            )
            
            # User experience scoring
            response_quality = self._calculate_response_quality(b1_metrics, b2_metrics)
            responsiveness_score = self._calculate_responsiveness_score(e2e_latency, combined_cpu)
            
            metrics = CombinedB1B2Metrics(
                timestamp=timestamp,
                voice_to_memory_latency_ms=voice_to_memory_latency,
                memory_retrieval_for_voice_ms=memory_retrieval_latency,
                cross_system_cpu_overhead_percent=integration_overhead,
                total_system_memory_mb=total_memory,
                combined_cpu_usage_percent=min(combined_cpu, 100),
                integration_overhead_percent=integration_overhead,
                end_to_end_voice_latency_ms=e2e_latency,
                memory_enhanced_response_quality=response_quality,
                system_responsiveness_score=responsiveness_score
            )
            
            # Trim latency tracking arrays
            self.voice_to_memory_latencies = self.voice_to_memory_latencies[-100:]
            self.memory_retrieval_latencies = self.memory_retrieval_latencies[-100:]
            
            self.integration_metrics_history.append(metrics)
            if len(self.integration_metrics_history) > 500:
                self.integration_metrics_history = self.integration_metrics_history[-500:]
            
            return metrics
            
        except Exception as e:
            logger.warning(f"Failed to collect combined metrics: {e}")
            return self._create_empty_combined_metrics(timestamp)
    
    def _calculate_integration_overhead(self, b1_metrics: B1PerformanceMetrics, b2_metrics: B2PerformanceMetrics) -> float:
        """Calculate CPU overhead from B1+B2 integration"""
        # Base overhead from data synchronization and cross-system communication
        base_overhead = 2.0  # 2% base overhead
        
        # Additional overhead based on activity
        b1_activity_overhead = (b1_metrics.chunk_ingestion_rate_per_min / 10) * 0.5
        b2_activity_overhead = (b2_metrics.barge_in_detections_per_min / 5) * 0.3
        
        return min(base_overhead + b1_activity_overhead + b2_activity_overhead, 15.0)
    
    def _calculate_response_quality(self, b1_metrics: B1PerformanceMetrics, b2_metrics: B2PerformanceMetrics) -> float:
        """Calculate memory-enhanced response quality score"""
        # Base quality score
        base_quality = 0.7
        
        # Enhancement from memory system
        memory_enhancement = min(0.2, b1_metrics.memory_summaries_count / 1000)
        
        # Degradation from performance issues
        cpu_penalty = max(0, (b1_metrics.llm_summary_cpu_percent - 50) / 500)  # Penalty if CPU > 50%
        latency_penalty = max(0, (b2_metrics.audio_processing_p95_latency_ms - 500) / 5000)  # Penalty if > 500ms
        
        quality_score = base_quality + memory_enhancement - cpu_penalty - latency_penalty
        return max(0.0, min(1.0, quality_score))
    
    def _calculate_responsiveness_score(self, e2e_latency: float, cpu_usage: float) -> float:
        """Calculate system responsiveness score (0-100)"""
        # Target: < 1.5s latency, < 70% CPU
        latency_score = max(0, 100 - (e2e_latency - 1500) / 50)  # Penalty for > 1.5s
        cpu_score = max(0, 100 - (cpu_usage - 70) / 2)  # Penalty for > 70% CPU
        
        return (latency_score * 0.6 + cpu_score * 0.4) / 2
    
    def _create_empty_combined_metrics(self, timestamp: datetime) -> CombinedB1B2Metrics:
        """Create empty combined metrics for error cases"""
        return CombinedB1B2Metrics(
            timestamp=timestamp,
            voice_to_memory_latency_ms=0,
            memory_retrieval_for_voice_ms=0,
            cross_system_cpu_overhead_percent=0,
            total_system_memory_mb=0,
            combined_cpu_usage_percent=0,
            integration_overhead_percent=0,
            end_to_end_voice_latency_ms=0,
            memory_enhanced_response_quality=0,
            system_responsiveness_score=0
        )
    
    def record_voice_to_memory_operation(self, latency_ms: float):
        """Record voice-to-memory integration latency"""
        self.voice_to_memory_latencies.append(latency_ms)
    
    def record_memory_retrieval_for_voice(self, latency_ms: float):
        """Record memory retrieval for voice response latency"""
        self.memory_retrieval_latencies.append(latency_ms)


class B1B2PerformanceManager:
    """Main performance manager for B1+B2 systems"""
    
    def __init__(self):
        self.b1_monitor = B1PerformanceMonitor()
        self.b2_monitor = B2PerformanceMonitor()
        self.combined_monitor = CombinedB1B2Monitor(self.b1_monitor, self.b2_monitor)
        
        self.is_monitoring = False
        self.monitoring_task = None
        self.monitoring_interval = 30  # 30 seconds
        
        # Performance alert thresholds
        self.alert_thresholds = {
            'b1_memory_growth_mb_per_hour': 20.0,
            'b1_database_query_latency_ms': 100.0,
            'b2_barge_in_latency_ms': 200.0,
            'b2_false_positive_rate_per_min': 2.0,
            'combined_cpu_percent': 80.0,
            'e2e_latency_ms': 3000.0
        }
        
        # Alert callbacks
        self.alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
    
    async def start_monitoring(self, interval_seconds: int = 30):
        """Start continuous B1+B2 performance monitoring"""
        if self.is_monitoring:
            return
        
        self.monitoring_interval = interval_seconds
        self.is_monitoring = True
        
        logger.info(f"Starting B1+B2 performance monitoring (interval: {interval_seconds}s)")
        
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        logger.info("Stopped B1+B2 performance monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Collect all metrics
                combined_metrics = await self.combined_monitor.collect_combined_metrics()
                
                # Check for performance alerts
                await self._check_performance_alerts(combined_metrics)
                
                # Log performance summary
                self._log_performance_summary(combined_metrics)
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error in B1+B2 monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _check_performance_alerts(self, metrics: CombinedB1B2Metrics):
        """Check for performance threshold violations"""
        alerts = []
        
        # Get latest B1/B2 metrics
        if self.b1_monitor.metrics_history:
            b1_latest = self.b1_monitor.metrics_history[-1]
            
            if b1_latest.memory_growth_rate_mb_per_hour > self.alert_thresholds['b1_memory_growth_mb_per_hour']:
                alerts.append(('b1_memory_growth', {
                    'current': b1_latest.memory_growth_rate_mb_per_hour,
                    'threshold': self.alert_thresholds['b1_memory_growth_mb_per_hour']
                }))
            
            if b1_latest.database_query_avg_latency_ms > self.alert_thresholds['b1_database_query_latency_ms']:
                alerts.append(('b1_database_latency', {
                    'current': b1_latest.database_query_avg_latency_ms,
                    'threshold': self.alert_thresholds['b1_database_query_latency_ms']
                }))
        
        if self.b2_monitor.metrics_history:
            b2_latest = self.b2_monitor.metrics_history[-1]
            
            if b2_latest.barge_in_detection_latency_ms > self.alert_thresholds['b2_barge_in_latency_ms']:
                alerts.append(('b2_barge_in_latency', {
                    'current': b2_latest.barge_in_detection_latency_ms,
                    'threshold': self.alert_thresholds['b2_barge_in_latency_ms']
                }))
            
            if b2_latest.false_positive_rate_per_min > self.alert_thresholds['b2_false_positive_rate_per_min']:
                alerts.append(('b2_false_positives', {
                    'current': b2_latest.false_positive_rate_per_min,
                    'threshold': self.alert_thresholds['b2_false_positive_rate_per_min']
                }))
        
        # Combined system alerts
        if metrics.combined_cpu_usage_percent > self.alert_thresholds['combined_cpu_percent']:
            alerts.append(('combined_cpu_high', {
                'current': metrics.combined_cpu_usage_percent,
                'threshold': self.alert_thresholds['combined_cpu_percent']
            }))
        
        if metrics.end_to_end_voice_latency_ms > self.alert_thresholds['e2e_latency_ms']:
            alerts.append(('e2e_latency_high', {
                'current': metrics.end_to_end_voice_latency_ms,
                'threshold': self.alert_thresholds['e2e_latency_ms']
            }))
        
        # Trigger alert callbacks
        for alert_type, alert_data in alerts:
            for callback in self.alert_callbacks:
                try:
                    callback(alert_type, alert_data)
                except Exception as e:
                    logger.warning(f"Alert callback failed: {e}")
    
    def _log_performance_summary(self, metrics: CombinedB1B2Metrics):
        """Log a summary of current performance"""
        logger.info(
            f"B1+B2 Performance Summary: "
            f"CPU: {metrics.combined_cpu_usage_percent:.1f}%, "
            f"Memory: {metrics.total_system_memory_mb:.1f}MB, "
            f"E2E Latency: {metrics.end_to_end_voice_latency_ms:.1f}ms, "
            f"Responsiveness: {metrics.system_responsiveness_score:.1f}/100"
        )
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add callback for performance alerts"""
        self.alert_callbacks.append(callback)
    
    def get_current_performance_status(self) -> Dict[str, Any]:
        """Get current performance status for all systems"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'monitoring_active': self.is_monitoring,
            'b1_metrics': None,
            'b2_metrics': None,
            'combined_metrics': None
        }
        
        if self.b1_monitor.metrics_history:
            status['b1_metrics'] = self.b1_monitor.metrics_history[-1].to_dict()
        
        if self.b2_monitor.metrics_history:
            status['b2_metrics'] = self.b2_monitor.metrics_history[-1].to_dict()
        
        if self.combined_monitor.integration_metrics_history:
            status['combined_metrics'] = self.combined_monitor.integration_metrics_history[-1].to_dict()
        
        return status
    
    def save_performance_report(self, filepath: Optional[Path] = None) -> str:
        """Save comprehensive performance report"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = Path(f"./data/performance_reports/b1_b2_report_{timestamp}.json")
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        report_data = {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'monitoring_active': self.is_monitoring,
                'alert_thresholds': self.alert_thresholds
            },
            'b1_performance': [m.to_dict() for m in self.b1_monitor.metrics_history[-100:]],
            'b2_performance': [m.to_dict() for m in self.b2_monitor.metrics_history[-100:]],
            'combined_performance': [m.to_dict() for m in self.combined_monitor.integration_metrics_history[-100:]],
            'current_status': self.get_current_performance_status()
        }
        
        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"B1+B2 performance report saved to {filepath}")
        return str(filepath)


# Global instance
b1b2_performance_manager = B1B2PerformanceManager()

# Integration with main performance profiler
def integrate_with_main_profiler():
    """Integrate B1+B2 monitoring with main performance profiler"""
    # Add B1+B2 metrics to main profiler's voice profiler
    original_start_session = profiler.voice_profiler.start_voice_session
    original_end_session = profiler.voice_profiler.end_voice_session
    
    def enhanced_start_session(session_id: str):
        original_start_session(session_id)
        b1b2_performance_manager.b2_monitor.start_voice_session(session_id)
    
    def enhanced_end_session(session_id: str):
        result = original_end_session(session_id)
        b1b2_performance_manager.b2_monitor.end_voice_session(session_id)
        return result
    
    profiler.voice_profiler.start_voice_session = enhanced_start_session
    profiler.voice_profiler.end_voice_session = enhanced_end_session
    
    logger.info("B1+B2 monitoring integrated with main performance profiler")

# Export key components
__all__ = [
    'B1PerformanceMetrics', 'B2PerformanceMetrics', 'CombinedB1B2Metrics',
    'B1PerformanceMonitor', 'B2PerformanceMonitor', 'CombinedB1B2Monitor',
    'B1B2PerformanceManager', 'b1b2_performance_manager', 'integrate_with_main_profiler'
]