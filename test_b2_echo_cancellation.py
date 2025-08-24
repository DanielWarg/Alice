#!/usr/bin/env python3
"""
Specialized echo cancellation test för Alice B2
Fokuserar på detaljerad testning av echo cancellation funktionalitet
"""

import sys
import json
import time
import logging
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EchoCancellationTest:
    """Specialized test suite för echo cancellation system"""
    
    def __init__(self):
        self.sample_rate = 16000
        self.buffer_size = 512
        self.test_duration_samples = 8000  # 0.5 seconds
        
        self.results = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'detailed_results': {}
        }
    
    def test_adaptive_filter_convergence(self):
        """Test adaptive filter convergence behavior"""
        logger.info("🧪 Testing adaptive filter convergence...")
        self.results['tests_run'] += 1
        
        try:
            # Simulate echo path (room impulse response)
            echo_path = self.generate_room_impulse_response(length=256)
            
            # Generate test signals
            speaker_signal = self.generate_speech_like_signal(self.test_duration_samples)
            echo_signal = np.convolve(speaker_signal, echo_path, mode='same')
            mic_signal = speaker_signal * 0.1 + echo_signal  # Direct path + echo
            
            # Test adaptive filter
            filter_coeffs = np.zeros(256)
            adaptation_rate = 0.01
            error_history = []
            
            for i in range(len(speaker_signal) - 256):
                # Get current speaker signal window
                x = speaker_signal[i:i+256]
                
                # Estimate echo
                echo_estimate = np.dot(filter_coeffs, x)
                
                # Calculate error
                error = mic_signal[i + 128] - echo_estimate  # Compensate för delay
                error_history.append(abs(error))
                
                # Update filter (LMS algorithm)
                filter_coeffs += adaptation_rate * error * x
            
            # Analyze convergence
            initial_error = np.mean(error_history[:100])
            final_error = np.mean(error_history[-100:])
            convergence_ratio = final_error / initial_error if initial_error > 0 else 0
            convergence_samples = self.find_convergence_point(error_history)
            
            # Test criteria
            convergence_good = convergence_ratio < 0.2  # 80% error reduction
            convergence_fast = convergence_samples < 2000  # Converge within 2000 samples
            
            result = {
                'convergence_ratio': convergence_ratio,
                'convergence_samples': convergence_samples,
                'initial_error': initial_error,
                'final_error': final_error,
                'passed': convergence_good and convergence_fast
            }
            
            self.results['detailed_results']['adaptive_filter_convergence'] = result
            
            if result['passed']:
                logger.info(f"  ✅ Convergence ratio: {convergence_ratio:.3f}")
                logger.info(f"  ✅ Convergence time: {convergence_samples} samples")
                self.results['tests_passed'] += 1
            else:
                logger.error(f"  ❌ Poor convergence: ratio={convergence_ratio:.3f}, samples={convergence_samples}")
                self.results['tests_failed'] += 1
                
        except Exception as e:
            logger.error(f"❌ Adaptive filter test crashed: {e}")
            self.results['tests_failed'] += 1
    
    def test_echo_suppression_levels(self):
        """Test different levels of echo suppression"""
        logger.info("🧪 Testing echo suppression levels...")
        self.results['tests_run'] += 1
        
        try:
            # Test different suppression levels
            suppression_levels = [0.3, 0.5, 0.7, 0.9]
            results = []
            
            # Generate test signal with known echo
            original_signal = self.generate_speech_like_signal(4000)
            echo_level = 0.4
            mixed_signal = original_signal + echo_level * np.roll(original_signal, 100)  # Simple delay echo
            
            for level in suppression_levels:
                # Apply echo suppression
                suppressed_signal = self.apply_echo_suppression(mixed_signal, level)
                
                # Measure suppression effectiveness
                echo_power_original = np.mean(mixed_signal ** 2)
                echo_power_suppressed = np.mean(suppressed_signal ** 2)
                suppression_achieved = 1 - (echo_power_suppressed / echo_power_original)
                
                # Measure signal preservation (should preserve original signal)
                signal_preservation = self.calculate_signal_preservation(original_signal, suppressed_signal)
                
                result = {
                    'level': level,
                    'suppression_achieved': suppression_achieved,
                    'signal_preservation': signal_preservation,
                    'effective': suppression_achieved > level * 0.8 and signal_preservation > 0.7
                }
                
                results.append(result)
                
                if result['effective']:
                    logger.info(f"  ✅ Level {level}: {suppression_achieved:.3f} suppression, {signal_preservation:.3f} preservation")
                else:
                    logger.error(f"  ❌ Level {level}: {suppression_achieved:.3f} suppression, {signal_preservation:.3f} preservation")
            
            # Overall success if most levels work
            effective_count = sum(1 for r in results if r['effective'])
            passed = effective_count >= len(suppression_levels) * 0.75
            
            self.results['detailed_results']['echo_suppression_levels'] = {
                'results': results,
                'effective_count': effective_count,
                'passed': passed
            }
            
            if passed:
                logger.info(f"✅ Echo suppression test passed: {effective_count}/{len(suppression_levels)} effective")
                self.results['tests_passed'] += 1
            else:
                logger.error(f"❌ Echo suppression test failed: {effective_count}/{len(suppression_levels)} effective")
                self.results['tests_failed'] += 1
                
        except Exception as e:
            logger.error(f"❌ Echo suppression test crashed: {e}")
            self.results['tests_failed'] += 1
    
    def test_noise_gate_functionality(self):
        """Test noise gate functionality"""
        logger.info("🧪 Testing noise gate functionality...")
        self.results['tests_run'] += 1
        
        try:
            # Test scenarios
            noise_gate_threshold = 0.01
            
            test_scenarios = [
                {
                    'name': 'Low level noise suppression',
                    'signal': np.random.normal(0, 0.005, 1000),  # Very quiet noise
                    'expected_suppression': 0.8
                },
                {
                    'name': 'Speech preservation',
                    'signal': self.generate_speech_like_signal(1000) * 0.1,  # Quiet speech
                    'expected_suppression': 0.2  # Should preserve most speech
                },
                {
                    'name': 'Loud signal passthrough', 
                    'signal': self.generate_speech_like_signal(1000) * 0.5,  # Normal speech
                    'expected_suppression': 0.05  # Should pass through almost unchanged
                },
                {
                    'name': 'Mixed signal handling',
                    'signal': self.generate_mixed_signal(),
                    'expected_suppression': 0.3  # Should suppress quiet parts, preserve loud
                }
            ]
            
            results = []
            
            for scenario in test_scenarios:
                # Apply noise gate
                gated_signal = self.apply_noise_gate(scenario['signal'], noise_gate_threshold)
                
                # Measure suppression
                original_power = np.mean(scenario['signal'] ** 2)
                gated_power = np.mean(gated_signal ** 2)
                actual_suppression = 1 - (gated_power / original_power) if original_power > 0 else 0
                
                # Check if suppression matches expectation
                expected = scenario['expected_suppression']
                tolerance = 0.2
                
                success = abs(actual_suppression - expected) < tolerance
                
                result = {
                    'name': scenario['name'],
                    'expected_suppression': expected,
                    'actual_suppression': actual_suppression,
                    'success': success
                }
                
                results.append(result)
                
                if success:
                    logger.info(f"  ✅ {scenario['name']}: {actual_suppression:.3f} suppression (expected ~{expected:.3f})")
                else:
                    logger.error(f"  ❌ {scenario['name']}: {actual_suppression:.3f} suppression (expected ~{expected:.3f})")
            
            # Overall success
            passed_count = sum(1 for r in results if r['success'])
            overall_passed = passed_count >= len(results) * 0.75
            
            self.results['detailed_results']['noise_gate_functionality'] = {
                'results': results,
                'passed_count': passed_count,
                'passed': overall_passed
            }
            
            if overall_passed:
                logger.info(f"✅ Noise gate test passed: {passed_count}/{len(results)} scenarios")
                self.results['tests_passed'] += 1
            else:
                logger.error(f"❌ Noise gate test failed: {passed_count}/{len(results)} scenarios")
                self.results['tests_failed'] += 1
                
        except Exception as e:
            logger.error(f"❌ Noise gate test crashed: {e}")
            self.results['tests_failed'] += 1
    
    def test_processing_latency(self):
        """Test processing latency of echo cancellation"""
        logger.info("🧪 Testing echo cancellation processing latency...")
        self.results['tests_run'] += 1
        
        try:
            buffer_sizes = [128, 256, 512, 1024]
            latency_results = []
            
            for buffer_size in buffer_sizes:
                # Simulate processing för different buffer sizes
                start_time = time.perf_counter()
                
                # Simulate the processing load
                self.simulate_echo_processing(buffer_size)
                
                end_time = time.perf_counter()
                processing_time_ms = (end_time - start_time) * 1000
                
                # Theoretical latency (buffer size related)
                theoretical_latency_ms = (buffer_size / self.sample_rate) * 1000
                
                result = {
                    'buffer_size': buffer_size,
                    'processing_time_ms': processing_time_ms,
                    'theoretical_latency_ms': theoretical_latency_ms,
                    'total_latency_ms': processing_time_ms + theoretical_latency_ms,
                    'acceptable': processing_time_ms + theoretical_latency_ms < 50  # <50ms total
                }
                
                latency_results.append(result)
                
                if result['acceptable']:
                    logger.info(f"  ✅ Buffer {buffer_size}: {result['total_latency_ms']:.1f}ms total latency")
                else:
                    logger.error(f"  ❌ Buffer {buffer_size}: {result['total_latency_ms']:.1f}ms total latency (too high)")
            
            # Overall success if most buffer sizes have acceptable latency
            acceptable_count = sum(1 for r in latency_results if r['acceptable'])
            overall_passed = acceptable_count >= len(buffer_sizes) * 0.75
            
            self.results['detailed_results']['processing_latency'] = {
                'results': latency_results,
                'acceptable_count': acceptable_count,
                'passed': overall_passed
            }
            
            if overall_passed:
                logger.info(f"✅ Latency test passed: {acceptable_count}/{len(buffer_sizes)} acceptable")
                self.results['tests_passed'] += 1
            else:
                logger.error(f"❌ Latency test failed: {acceptable_count}/{len(buffer_sizes)} acceptable")
                self.results['tests_failed'] += 1
                
        except Exception as e:
            logger.error(f"❌ Latency test crashed: {e}")
            self.results['tests_failed'] += 1
    
    def test_real_world_scenarios(self):
        """Test echo cancellation in realistic scenarios"""
        logger.info("🧪 Testing real-world echo scenarios...")
        self.results['tests_run'] += 1
        
        try:
            scenarios = [
                {
                    'name': 'Near-end speech with far-end echo',
                    'setup': self.create_near_far_end_scenario,
                    'success_criteria': {'echo_suppression': 0.7, 'speech_preservation': 0.8}
                },
                {
                    'name': 'Double-talk situation',
                    'setup': self.create_double_talk_scenario, 
                    'success_criteria': {'echo_suppression': 0.5, 'speech_preservation': 0.7}
                },
                {
                    'name': 'Room acoustics with reverberation',
                    'setup': self.create_reverberant_scenario,
                    'success_criteria': {'echo_suppression': 0.6, 'speech_preservation': 0.8}
                },
                {
                    'name': 'Background noise with echo',
                    'setup': self.create_noisy_echo_scenario,
                    'success_criteria': {'echo_suppression': 0.4, 'speech_preservation': 0.6}
                }
            ]
            
            scenario_results = []
            
            for scenario in scenarios:
                # Generate scenario
                test_data = scenario['setup']()
                
                # Apply echo cancellation
                result = self.process_echo_scenario(test_data)
                
                # Check success criteria
                criteria = scenario['success_criteria']
                success = (
                    result['echo_suppression'] >= criteria['echo_suppression'] and
                    result['speech_preservation'] >= criteria['speech_preservation']
                )
                
                scenario_result = {
                    'name': scenario['name'],
                    'echo_suppression': result['echo_suppression'],
                    'speech_preservation': result['speech_preservation'],
                    'success': success
                }
                
                scenario_results.append(scenario_result)
                
                if success:
                    logger.info(f"  ✅ {scenario['name']}: suppression={result['echo_suppression']:.3f}, preservation={result['speech_preservation']:.3f}")
                else:
                    logger.error(f"  ❌ {scenario['name']}: suppression={result['echo_suppression']:.3f}, preservation={result['speech_preservation']:.3f}")
            
            # Overall success
            passed_scenarios = sum(1 for r in scenario_results if r['success'])
            overall_passed = passed_scenarios >= len(scenarios) * 0.75
            
            self.results['detailed_results']['real_world_scenarios'] = {
                'results': scenario_results,
                'passed_scenarios': passed_scenarios,
                'passed': overall_passed
            }
            
            if overall_passed:
                logger.info(f"✅ Real-world scenarios test passed: {passed_scenarios}/{len(scenarios)}")
                self.results['tests_passed'] += 1
            else:
                logger.error(f"❌ Real-world scenarios test failed: {passed_scenarios}/{len(scenarios)}")
                self.results['tests_failed'] += 1
                
        except Exception as e:
            logger.error(f"❌ Real-world scenarios test crashed: {e}")
            self.results['tests_failed'] += 1

    # Helper methods för signal generation and processing
    
    def generate_room_impulse_response(self, length: int) -> np.ndarray:
        """Generate realistic room impulse response"""
        # Simple exponentially decaying impulse with some reflections
        h = np.zeros(length)
        h[0] = 1.0  # Direct path
        
        # Add some reflections
        reflection_delays = [50, 120, 200, 280]
        reflection_gains = [0.3, 0.2, 0.15, 0.1]
        
        for delay, gain in zip(reflection_delays, reflection_gains):
            if delay < length:
                h[delay] += gain
        
        # Apply exponential decay
        decay = np.exp(-np.arange(length) / 1000)
        h *= decay
        
        return h
    
    def generate_speech_like_signal(self, length: int) -> np.ndarray:
        """Generate speech-like signal with realistic characteristics"""
        # Create formant-like structure
        t = np.arange(length) / self.sample_rate
        
        # Fundamental frequency varying över time
        f0 = 150 + 30 * np.sin(2 * np.pi * 5 * t)  # 120-180 Hz fundamental
        
        # Generate harmonics
        signal = np.zeros(length)
        for harmonic in [1, 2, 3, 4]:
            amplitude = 1.0 / harmonic  # Decreasing harmonic amplitudes
            signal += amplitude * np.sin(2 * np.pi * harmonic * f0 * t)
        
        # Add some noise för realism
        signal += 0.05 * np.random.randn(length)
        
        # Apply envelope (speech-like amplitude variations)
        envelope = 0.5 * (1 + np.sin(2 * np.pi * 10 * t))
        signal *= envelope
        
        return signal * 0.3  # Normalize
    
    def generate_mixed_signal(self) -> np.ndarray:
        """Generate mixed signal with quiet and loud sections"""
        length = 2000
        signal = np.zeros(length)
        
        # Quiet section
        signal[:500] = np.random.normal(0, 0.003, 500)
        
        # Loud section (speech)
        signal[500:1000] = self.generate_speech_like_signal(500) * 0.2
        
        # Medium section
        signal[1000:1500] = self.generate_speech_like_signal(500) * 0.05
        
        # Very quiet section
        signal[1500:] = np.random.normal(0, 0.001, 500)
        
        return signal
    
    def apply_echo_suppression(self, signal: np.ndarray, level: float) -> np.ndarray:
        """Apply echo suppression to signal"""
        # Simple echo suppression model
        suppressed = signal.copy()
        
        # Apply frequency-domain suppression (simplified)
        fft_signal = np.fft.fft(signal)
        magnitude = np.abs(fft_signal)
        phase = np.angle(fft_signal)
        
        # Suppress based on magnitude and level
        suppressed_magnitude = magnitude * (1 - level * np.tanh(magnitude * 10))
        
        # Reconstruct signal
        suppressed_fft = suppressed_magnitude * np.exp(1j * phase)
        suppressed = np.real(np.fft.ifft(suppressed_fft))
        
        return suppressed
    
    def apply_noise_gate(self, signal: np.ndarray, threshold: float) -> np.ndarray:
        """Apply noise gate to signal"""
        gated = signal.copy()
        
        # Calculate running energy
        window_size = 64
        energy = np.zeros(len(signal))
        
        for i in range(len(signal)):
            start = max(0, i - window_size // 2)
            end = min(len(signal), i + window_size // 2)
            energy[i] = np.mean(signal[start:end] ** 2)
        
        # Apply gate
        gate_factor = np.where(energy > threshold**2, 1.0, 0.1)
        gated *= gate_factor
        
        return gated
    
    def calculate_signal_preservation(self, original: np.ndarray, processed: np.ndarray) -> float:
        """Calculate how well the processed signal preserves the original"""
        # Normalize både signals
        orig_norm = original / (np.max(np.abs(original)) + 1e-10)
        proc_norm = processed / (np.max(np.abs(processed)) + 1e-10)
        
        # Calculate correlation
        correlation = np.corrcoef(orig_norm, proc_norm)[0, 1]
        
        return max(0, correlation)  # Ensure non-negative
    
    def find_convergence_point(self, error_history: List[float]) -> int:
        """Find convergence point in error history"""
        if len(error_history) < 100:
            return len(error_history)
        
        # Look för point where error stops decreasing significantly
        window_size = 50
        for i in range(window_size, len(error_history) - window_size):
            before = np.mean(error_history[i-window_size:i])
            after = np.mean(error_history[i:i+window_size])
            
            if before > 0 and (before - after) / before < 0.05:  # Less than 5% improvement
                return i
        
        return len(error_history)
    
    def simulate_echo_processing(self, buffer_size: int):
        """Simulate the computational load of echo processing"""
        # Simulate the work done för echo cancellation
        dummy_data = np.random.randn(buffer_size, 2)  # Stereo
        
        # Simulate filter operations
        filter_coeffs = np.random.randn(256)
        
        # Convolution (main computational load)
        for _ in range(5):  # Multiple filter taps
            _ = np.convolve(dummy_data[:, 0], filter_coeffs, mode='valid')
        
        # Simulate adaptation step
        _ = np.dot(dummy_data[:buffer_size//4], filter_coeffs[:buffer_size//4])
    
    def create_near_far_end_scenario(self) -> Dict[str, np.ndarray]:
        """Create near-end speech with far-end echo scenario"""
        length = 4000
        
        # Near-end speech (what user is saying)
        near_end = self.generate_speech_like_signal(length) * 0.6
        
        # Far-end signal (Alice speaking)
        far_end = self.generate_speech_like_signal(length) * 0.8
        
        # Echo of far-end signal
        echo_path = self.generate_room_impulse_response(200)
        echo = np.convolve(far_end, echo_path, mode='same') * 0.4
        
        # Mixed signal at microphone
        microphone = near_end + echo + 0.02 * np.random.randn(length)
        
        return {
            'near_end': near_end,
            'far_end': far_end, 
            'echo': echo,
            'microphone': microphone
        }
    
    def create_double_talk_scenario(self) -> Dict[str, np.ndarray]:
        """Create double-talk scenario (both parties speaking)"""
        length = 4000
        
        # Both parties speaking at same time
        near_end = self.generate_speech_like_signal(length) * 0.5
        far_end = self.generate_speech_like_signal(length) * 0.5
        
        # Shift far-end signal slightly för realism
        far_end = np.roll(far_end, 100)
        
        # Echo
        echo_path = self.generate_room_impulse_response(150)
        echo = np.convolve(far_end, echo_path, mode='same') * 0.3
        
        microphone = near_end + echo + 0.01 * np.random.randn(length)
        
        return {
            'near_end': near_end,
            'far_end': far_end,
            'echo': echo,
            'microphone': microphone
        }
    
    def create_reverberant_scenario(self) -> Dict[str, np.ndarray]:
        """Create reverberant room scenario"""
        length = 4000
        
        # Long reverberant impulse response
        echo_path = self.generate_room_impulse_response(500)
        
        near_end = self.generate_speech_like_signal(length) * 0.4
        far_end = self.generate_speech_like_signal(length) * 0.7
        
        # Strong reverberation
        echo = np.convolve(far_end, echo_path, mode='same') * 0.6
        
        microphone = near_end + echo + 0.015 * np.random.randn(length)
        
        return {
            'near_end': near_end,
            'far_end': far_end,
            'echo': echo,
            'microphone': microphone
        }
    
    def create_noisy_echo_scenario(self) -> Dict[str, np.ndarray]:
        """Create scenario with background noise and echo"""
        length = 4000
        
        near_end = self.generate_speech_like_signal(length) * 0.4
        far_end = self.generate_speech_like_signal(length) * 0.6
        
        echo_path = self.generate_room_impulse_response(200)
        echo = np.convolve(far_end, echo_path, mode='same') * 0.3
        
        # Significant background noise
        background_noise = 0.08 * np.random.randn(length)
        
        microphone = near_end + echo + background_noise
        
        return {
            'near_end': near_end,
            'far_end': far_end,
            'echo': echo,
            'microphone': microphone
        }
    
    def process_echo_scenario(self, test_data: Dict[str, np.ndarray]) -> Dict[str, float]:
        """Process echo cancellation scenario and return metrics"""
        microphone = test_data['microphone']
        near_end = test_data['near_end'] 
        echo = test_data['echo']
        
        # Apply simplified echo cancellation
        processed = self.apply_echo_suppression(microphone, 0.7)
        
        # Calculate metrics
        echo_power_before = np.mean(echo ** 2)
        echo_power_after = np.mean((processed - near_end) ** 2)
        echo_suppression = 1 - (echo_power_after / echo_power_before) if echo_power_before > 0 else 0
        
        speech_preservation = self.calculate_signal_preservation(near_end, processed)
        
        return {
            'echo_suppression': max(0, echo_suppression),
            'speech_preservation': speech_preservation
        }

    def generate_test_report(self):
        """Generate detailed test report"""
        success_rate = (self.results['tests_passed'] / self.results['tests_run']) * 100 if self.results['tests_run'] > 0 else 0
        
        logger.info("")
        logger.info("==================================================")
        logger.info("🔇 ECHO CANCELLATION TEST RESULTS")
        logger.info("==================================================")
        logger.info(f"🧪 Tests run: {self.results['tests_run']}")
        logger.info(f"✅ Passed: {self.results['tests_passed']}")
        logger.info(f"❌ Failed: {self.results['tests_failed']}")
        logger.info(f"📊 Success rate: {success_rate:.1f}%")
        
        # Detailed results
        logger.info("")
        logger.info("📋 DETAILED RESULTS:")
        for test_name, details in self.results['detailed_results'].items():
            logger.info(f"  {test_name}: {'PASS' if details.get('passed', False) else 'FAIL'}")
        
        if success_rate == 100.0:
            logger.info("🎉 ALL ECHO CANCELLATION TESTS PASSED!")
            return 0
        else:
            logger.error(f"💥 {self.results['tests_failed']} echo cancellation tests failed!")
            return 1

def main():
    """Main test runner för echo cancellation"""
    logger.info("🔇 Starting Echo Cancellation Specialized Test")
    
    test_suite = EchoCancellationTest()
    
    try:
        # Run all echo cancellation tests
        test_suite.test_adaptive_filter_convergence()
        test_suite.test_echo_suppression_levels()
        test_suite.test_noise_gate_functionality()
        test_suite.test_processing_latency()
        test_suite.test_real_world_scenarios()
        
        # Generate report
        return test_suite.generate_test_report()
        
    except Exception as e:
        logger.error(f"💥 Echo cancellation test suite crashed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())