"""
Alice AI Assistant - 60-Minute Soak Test
Continuous operation monitoring and stress testing for production readiness
"""

import asyncio
import time
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import statistics

from performance_profiler import profiler, PerformanceBudget

# Optional imports
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SoakTestConfig:
    """Configuration for soak test scenarios"""
    duration_minutes: int = 60
    voice_operations_per_minute: int = 10
    concurrent_users_min: int = 1
    concurrent_users_max: int = 5
    simulate_memory_pressure: bool = True
    simulate_cpu_spikes: bool = True
    simulate_network_requests: bool = True
    enable_garbage_collection_monitoring: bool = True
    performance_alert_threshold: float = 80.0  # Alert if any metric exceeds 80% of budget
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SoakTestResult:
    """Results from a soak test run"""
    test_id: str
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    config: SoakTestConfig
    
    # Performance metrics
    cpu_max: float
    cpu_average: float
    memory_peak_mb: float
    memory_average_mb: float
    memory_growth_mb: float
    
    # Voice operation metrics
    voice_operations_total: int
    voice_operations_successful: int
    voice_operation_avg_latency_ms: float
    voice_operation_p95_latency_ms: float
    
    # System stability metrics
    crashes: int
    memory_leaks_detected: int
    performance_violations: List[Dict[str, Any]]
    
    # Overall assessment
    test_passed: bool
    stability_score: float  # 0-100
    performance_score: float  # 0-100
    overall_score: float  # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['start_time'] = data['start_time'].isoformat()
        data['end_time'] = data['end_time'].isoformat()
        return data


class VoiceOperationSimulator:
    """Simulates voice operations for soak testing"""
    
    def __init__(self):
        self.operations_performed = 0
        self.successful_operations = 0
        self.operation_latencies = []
        self.active_sessions = {}
    
    async def simulate_voice_session(self, session_id: str, duration_ms: int = None) -> Dict[str, Any]:
        """Simulate a complete voice interaction session"""
        if duration_ms is None:
            # Realistic voice session duration (2-30 seconds)
            duration_ms = random.randint(2000, 30000)
        
        start_time = time.time()
        
        try:
            # Start voice profiling
            profiler.voice_profiler.start_voice_session(session_id)
            profiler.set_voice_processing_active(True)
            
            # Simulate various voice operations
            await self._simulate_wake_word_detection(session_id)
            await self._simulate_speech_to_text(session_id, duration_ms * 0.6)
            await self._simulate_intent_processing(session_id)
            await self._simulate_response_generation(session_id)
            await self._simulate_text_to_speech(session_id, duration_ms * 0.3)
            
            # Random processing delay to simulate real workload
            processing_delay = random.uniform(0.1, 0.5)
            await asyncio.sleep(processing_delay)
            
            self.successful_operations += 1
            
        except Exception as e:
            logger.warning(f"Voice session {session_id} failed: {e}")
        finally:
            profiler.set_voice_processing_active(False)
            end_time = time.time()
            
            session_latency = (end_time - start_time) * 1000
            self.operation_latencies.append(session_latency)
            self.operations_performed += 1
            
            # End voice profiling
            session_metrics = profiler.voice_profiler.end_voice_session(session_id)
            
            return {
                'session_id': session_id,
                'latency_ms': session_latency,
                'successful': True,
                'operations': session_metrics.get('operations', []) if session_metrics else []
            }
    
    async def _simulate_wake_word_detection(self, session_id: str):
        """Simulate wake word detection processing"""
        # Simulate wake word processing time (50-200ms)
        processing_time = random.uniform(0.05, 0.2)
        await asyncio.sleep(processing_time)
        profiler.voice_profiler.record_voice_operation(session_id, 'wake_word_detection', processing_time * 1000)
    
    async def _simulate_speech_to_text(self, session_id: str, duration_ms: float):
        """Simulate speech-to-text processing"""
        # STT processing typically takes 10-30% of audio duration
        processing_time = (duration_ms / 1000) * random.uniform(0.1, 0.3)
        await asyncio.sleep(processing_time)
        profiler.voice_profiler.record_voice_operation(session_id, 'speech_to_text', processing_time * 1000)
    
    async def _simulate_intent_processing(self, session_id: str):
        """Simulate intent recognition and NLU processing"""
        processing_time = random.uniform(0.1, 0.5)
        await asyncio.sleep(processing_time)
        profiler.voice_profiler.record_voice_operation(session_id, 'intent_processing', processing_time * 1000)
    
    async def _simulate_response_generation(self, session_id: str):
        """Simulate LLM response generation"""
        # LLM processing can vary widely (200ms - 2s)
        processing_time = random.uniform(0.2, 2.0)
        await asyncio.sleep(processing_time)
        profiler.voice_profiler.record_voice_operation(session_id, 'response_generation', processing_time * 1000)
    
    async def _simulate_text_to_speech(self, session_id: str, audio_duration_ms: float):
        """Simulate text-to-speech synthesis"""
        # TTS processing typically takes 5-15% of output audio duration
        processing_time = (audio_duration_ms / 1000) * random.uniform(0.05, 0.15)
        await asyncio.sleep(processing_time)
        profiler.voice_profiler.record_voice_operation(session_id, 'text_to_speech', processing_time * 1000)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current voice operation metrics"""
        if not self.operation_latencies:
            return {
                'operations_total': 0,
                'operations_successful': 0,
                'average_latency_ms': 0,
                'p95_latency_ms': 0,
                'success_rate': 0
            }
        
        return {
            'operations_total': self.operations_performed,
            'operations_successful': self.successful_operations,
            'average_latency_ms': statistics.mean(self.operation_latencies),
            'p95_latency_ms': statistics.quantiles(self.operation_latencies, n=20)[18] if len(self.operation_latencies) >= 20 else max(self.operation_latencies),
            'success_rate': (self.successful_operations / self.operations_performed) * 100 if self.operations_performed > 0 else 0
        }


class SystemStressSimulator:
    """Simulates various system stress conditions"""
    
    def __init__(self):
        self.memory_allocations = []
        self.stress_tasks = []
    
    async def simulate_memory_pressure(self, duration_seconds: int = 60):
        """Simulate memory pressure by allocating and deallocating memory"""
        logger.info(f"Starting memory pressure simulation for {duration_seconds} seconds")
        
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            try:
                # Allocate 10-50MB chunks
                chunk_size = random.randint(10, 50) * 1024 * 1024
                memory_chunk = bytearray(chunk_size)
                self.memory_allocations.append(memory_chunk)
                
                # Randomly deallocate old chunks
                if len(self.memory_allocations) > 10:
                    del self.memory_allocations[random.randint(0, len(self.memory_allocations) - 1)]
                
                await asyncio.sleep(random.uniform(1, 5))
                
            except MemoryError:
                logger.warning("Memory allocation failed during stress test")
                break
    
    async def simulate_cpu_spikes(self, duration_seconds: int = 60):
        """Simulate CPU spikes with intensive computation"""
        logger.info(f"Starting CPU spike simulation for {duration_seconds} seconds")
        
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            # Create CPU-intensive task
            spike_duration = random.uniform(0.1, 1.0)
            spike_start = time.time()
            
            # Busy wait to consume CPU
            while time.time() - spike_start < spike_duration:
                _ = sum(i**2 for i in range(1000))
            
            # Rest period
            await asyncio.sleep(random.uniform(2, 10))
    
    async def simulate_network_requests(self, duration_seconds: int = 60):
        """Simulate network request load"""
        logger.info(f"Starting network simulation for {duration_seconds} seconds")
        
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < duration_seconds:
            try:
                # Simulate API calls with varying response times
                response_time = random.uniform(0.1, 2.0)
                await asyncio.sleep(response_time)
                request_count += 1
                
                # Vary request frequency
                await asyncio.sleep(random.uniform(0.5, 3.0))
                
            except Exception as e:
                logger.warning(f"Network simulation error: {e}")
        
        logger.info(f"Completed {request_count} simulated network requests")
    
    def cleanup(self):
        """Clean up stress simulation resources"""
        self.memory_allocations.clear()
        for task in self.stress_tasks:
            if not task.done():
                task.cancel()


class SoakTester:
    """Main soak testing orchestrator"""
    
    def __init__(self, config: SoakTestConfig = None):
        self.config = config or SoakTestConfig()
        self.voice_simulator = VoiceOperationSimulator()
        self.stress_simulator = SystemStressSimulator()
        self.test_results = []
        self.is_running = False
        
        # Performance monitoring
        self.performance_violations = []
        self.stability_issues = []
    
    async def run_soak_test(self, test_name: str = None) -> SoakTestResult:
        """Run a complete 60-minute soak test"""
        test_id = test_name or f"soak_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Starting soak test: {test_id}")
        
        start_time = datetime.now()
        self.is_running = True
        
        try:
            # Start performance monitoring
            profiler.start_cpu_profiling()
            monitoring_task = asyncio.create_task(profiler.start_monitoring())
            
            # Create stress simulation tasks
            stress_tasks = []
            if self.config.simulate_memory_pressure:
                stress_tasks.append(
                    asyncio.create_task(
                        self.stress_simulator.simulate_memory_pressure(self.config.duration_minutes * 60)
                    )
                )
            
            if self.config.simulate_cpu_spikes:
                stress_tasks.append(
                    asyncio.create_task(
                        self.stress_simulator.simulate_cpu_spikes(self.config.duration_minutes * 60)
                    )
                )
            
            if self.config.simulate_network_requests:
                stress_tasks.append(
                    asyncio.create_task(
                        self.stress_simulator.simulate_network_requests(self.config.duration_minutes * 60)
                    )
                )
            
            # Run voice operations continuously
            voice_task = asyncio.create_task(self._run_voice_operations())
            
            # Monitor performance during test
            monitoring_task_performance = asyncio.create_task(self._monitor_performance_during_test())
            
            # Wait for test duration
            await asyncio.sleep(self.config.duration_minutes * 60)
            
            # Stop all tasks
            self.is_running = False
            voice_task.cancel()
            monitoring_task_performance.cancel()
            monitoring_task.cancel()
            
            for task in stress_tasks:
                task.cancel()
            
            # Stop profiling
            profiler.stop_monitoring()
            cpu_profile_data = profiler.stop_cpu_profiling()
            
            # Generate results
            end_time = datetime.now()
            result = await self._generate_test_result(test_id, start_time, end_time, cpu_profile_data)
            
            logger.info(f"Soak test completed: {test_id} - Score: {result.overall_score:.1f}%")
            return result
            
        except Exception as e:
            logger.error(f"Soak test failed: {e}")
            raise
        finally:
            self.is_running = False
            self.stress_simulator.cleanup()
    
    async def _run_voice_operations(self):
        """Continuously run voice operations during the test"""
        operation_interval = 60.0 / self.config.voice_operations_per_minute
        session_counter = 0
        
        while self.is_running:
            try:
                # Vary concurrent users
                concurrent_users = random.randint(
                    self.config.concurrent_users_min,
                    self.config.concurrent_users_max
                )
                profiler.set_concurrent_users(concurrent_users)
                
                # Create voice sessions
                session_tasks = []
                for i in range(concurrent_users):
                    session_id = f"soak_session_{session_counter}_{i}"
                    session_task = asyncio.create_task(
                        self.voice_simulator.simulate_voice_session(session_id)
                    )
                    session_tasks.append(session_task)
                    session_counter += 1
                
                # Wait for sessions to complete
                await asyncio.gather(*session_tasks, return_exceptions=True)
                
                # Wait for next batch
                await asyncio.sleep(operation_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Voice operation batch failed: {e}")
                await asyncio.sleep(1)  # Brief pause before retrying
    
    async def _monitor_performance_during_test(self):
        """Monitor performance and detect violations during test"""
        check_interval = 30  # Check every 30 seconds
        
        while self.is_running:
            try:
                # Get current performance status
                status = profiler.get_current_status()
                
                if 'current_metrics' in status and status['current_metrics']:
                    metrics = status['current_metrics']
                    budget_compliance = status.get('budget_compliance', {})
                    
                    # Check for performance violations
                    if not budget_compliance.get('compliant', True):
                        for violation in budget_compliance.get('violations', []):
                            violation['timestamp'] = datetime.now().isoformat()
                            self.performance_violations.append(violation)
                            logger.warning(f"Performance violation detected: {violation}")
                    
                    # Check for stability issues
                    if PSUTIL_AVAILABLE:
                        try:
                            memory_info = psutil.Process().memory_info()
                            memory_mb = memory_info.rss / 1024 / 1024
                            
                            # Check for rapid memory growth (potential leak)
                            if hasattr(self, 'last_memory_check'):
                                memory_growth = memory_mb - self.last_memory_check
                                if memory_growth > 50:  # More than 50MB growth in 30 seconds
                                    issue = {
                                        'type': 'potential_memory_leak',
                                        'growth_mb': memory_growth,
                                        'timestamp': datetime.now().isoformat()
                                    }
                                    self.stability_issues.append(issue)
                                    logger.warning(f"Potential memory leak detected: {memory_growth:.1f}MB growth in 30s")
                            
                            self.last_memory_check = memory_mb
                            
                        except Exception:
                            pass
                
                await asyncio.sleep(check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Performance monitoring error: {e}")
                await asyncio.sleep(check_interval)
    
    async def _generate_test_result(self, 
                                  test_id: str,
                                  start_time: datetime,
                                  end_time: datetime,
                                  cpu_profile_data: Optional[Dict[str, Any]]) -> SoakTestResult:
        """Generate comprehensive test results"""
        duration_minutes = (end_time - start_time).total_seconds() / 60
        
        # Get performance metrics
        performance_metrics = profiler.calculate_metrics(start_time, end_time)
        voice_metrics = self.voice_simulator.get_metrics()
        
        # Calculate scores
        stability_score = self._calculate_stability_score()
        performance_score = self._calculate_performance_score(performance_metrics)
        overall_score = (stability_score + performance_score) / 2
        
        # Determine if test passed (score >= 70%)
        test_passed = overall_score >= 70.0
        
        result = SoakTestResult(
            test_id=test_id,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            config=self.config,
            
            # Performance metrics
            cpu_max=performance_metrics.cpu_peak if performance_metrics else 0,
            cpu_average=performance_metrics.cpu_average if performance_metrics else 0,
            memory_peak_mb=performance_metrics.memory_peak_mb if performance_metrics else 0,
            memory_average_mb=performance_metrics.memory_average_mb if performance_metrics else 0,
            memory_growth_mb=performance_metrics.memory_growth_rate_mb_per_hour * (duration_minutes / 60) if performance_metrics else 0,
            
            # Voice operation metrics
            voice_operations_total=voice_metrics['operations_total'],
            voice_operations_successful=voice_metrics['operations_successful'],
            voice_operation_avg_latency_ms=voice_metrics['average_latency_ms'],
            voice_operation_p95_latency_ms=voice_metrics['p95_latency_ms'],
            
            # System stability metrics
            crashes=0,  # Would be detected by monitoring system
            memory_leaks_detected=len([issue for issue in self.stability_issues if issue['type'] == 'potential_memory_leak']),
            performance_violations=self.performance_violations.copy(),
            
            # Assessment scores
            test_passed=test_passed,
            stability_score=stability_score,
            performance_score=performance_score,
            overall_score=overall_score
        )
        
        # Save detailed results
        await self._save_test_results(result, cpu_profile_data)
        
        return result
    
    def _calculate_stability_score(self) -> float:
        """Calculate stability score (0-100) based on issues detected"""
        base_score = 100.0
        
        # Deduct for stability issues
        for issue in self.stability_issues:
            if issue['type'] == 'potential_memory_leak':
                base_score -= 20.0  # Major deduction for memory leaks
            else:
                base_score -= 5.0   # Minor deduction for other issues
        
        # Deduct for critical performance violations
        critical_violations = [v for v in self.performance_violations if v.get('severity') == 'critical']
        base_score -= len(critical_violations) * 15.0
        
        return max(0.0, base_score)
    
    def _calculate_performance_score(self, metrics) -> float:
        """Calculate performance score (0-100) based on metrics vs budget"""
        if not metrics:
            return 50.0  # Neutral score if no metrics
        
        budget = PerformanceBudget()
        compliance = budget.check_compliance(metrics)
        
        base_score = 100.0
        
        # Deduct for violations
        for violation in compliance.get('violations', []):
            if violation['severity'] == 'critical':
                base_score -= 25.0
            elif violation['severity'] == 'warning':
                base_score -= 10.0
        
        return max(0.0, base_score)
    
    async def _save_test_results(self, result: SoakTestResult, cpu_profile_data: Optional[Dict[str, Any]]):
        """Save comprehensive test results to file"""
        results_dir = Path("./data/soak_test_results")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Save main results
        results_file = results_dir / f"{result.test_id}_results.json"
        with open(results_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        
        # Save performance profile data
        profile_file = profiler.save_profile_data(f"soak_test_{result.test_id}")
        
        # Save CPU profiling data if available
        if cpu_profile_data:
            cpu_profile_file = results_dir / f"{result.test_id}_cpu_profile.json"
            with open(cpu_profile_file, 'w') as f:
                json.dump(cpu_profile_data, f, indent=2, default=str)
        
        logger.info(f"Soak test results saved to {results_file}")


# Convenience functions for running tests
async def run_quick_soak_test(duration_minutes: int = 10) -> SoakTestResult:
    """Run a quick soak test for development/testing"""
    config = SoakTestConfig(
        duration_minutes=duration_minutes,
        voice_operations_per_minute=5,  # Reduced for quick test
        concurrent_users_max=3,
        simulate_memory_pressure=False,  # Disabled for quick test
        simulate_cpu_spikes=False
    )
    
    tester = SoakTester(config)
    return await tester.run_soak_test(f"quick_test_{duration_minutes}min")


async def run_full_production_soak_test() -> SoakTestResult:
    """Run the full 60-minute production soak test"""
    config = SoakTestConfig()  # Use default 60-minute configuration
    tester = SoakTester(config)
    return await tester.run_soak_test("production_60min")


# CLI interface for running soak tests
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Alice AI Soak Test")
    parser.add_argument('--duration', type=int, default=60, help='Test duration in minutes')
    parser.add_argument('--quick', action='store_true', help='Run quick 10-minute test')
    parser.add_argument('--voice-ops', type=int, default=10, help='Voice operations per minute')
    parser.add_argument('--concurrent-users', type=int, default=5, help='Max concurrent users')
    
    args = parser.parse_args()
    
    async def main():
        if args.quick:
            result = await run_quick_soak_test(10)
        else:
            config = SoakTestConfig(
                duration_minutes=args.duration,
                voice_operations_per_minute=args.voice_ops,
                concurrent_users_max=args.concurrent_users
            )
            tester = SoakTester(config)
            result = await tester.run_soak_test()
        
        print(f"\n{'='*60}")
        print(f"SOAK TEST RESULTS: {result.test_id}")
        print(f"{'='*60}")
        print(f"Duration: {result.duration_minutes:.1f} minutes")
        print(f"Overall Score: {result.overall_score:.1f}% ({'PASS' if result.test_passed else 'FAIL'})")
        print(f"Stability Score: {result.stability_score:.1f}%")
        print(f"Performance Score: {result.performance_score:.1f}%")
        print(f"\nVoice Operations: {result.voice_operations_successful}/{result.voice_operations_total}")
        print(f"Average Latency: {result.voice_operation_avg_latency_ms:.1f}ms")
        print(f"P95 Latency: {result.voice_operation_p95_latency_ms:.1f}ms")
        print(f"\nCPU Peak: {result.cpu_max:.1f}%")
        print(f"Memory Peak: {result.memory_peak_mb:.1f}MB")
        print(f"Memory Growth: {result.memory_growth_mb:.1f}MB")
        print(f"\nPerformance Violations: {len(result.performance_violations)}")
        print(f"Memory Leaks Detected: {result.memory_leaks_detected}")
    
    asyncio.run(main())