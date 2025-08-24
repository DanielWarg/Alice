#!/usr/bin/env python3
"""
Specialized barge-in detection test för Alice B2
Fokuserar på detaljerad testning av barge-in detection funktionalitet
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

class BargeInDetectionTest:
    """Specialized test suite för barge-in detection system"""
    
    def __init__(self):
        self.sample_rate = 16000
        self.detection_window_ms = 150
        self.detection_window_samples = int(self.sample_rate * self.detection_window_ms / 1000)
        
        self.results = {
            'tests_run': 0,
            'tests_passed': 0, 
            'tests_failed': 0,
            'detailed_results': {}
        }
        
        # Voice characteristics för realistic testing
        self.voice_characteristics = {
            'male_voice': {'f0_range': (80, 200), 'formants': [700, 1220, 2600]},
            'female_voice': {'f0_range': (150, 300), 'formants': [800, 1400, 2800]}, 
            'child_voice': {'f0_range': (200, 400), 'formants': [900, 1500, 3000]}
        }
    
    def test_detection_speed(self):
        """Test how fast barge-in detection responds"""
        logger.info("🧪 Testing barge-in detection speed...")
        self.results['tests_run'] += 1
        
        try:
            test_scenarios = [
                {
                    'name': 'Immediate strong voice',
                    'voice_strength': 0.8,
                    'onset_samples': 0,
                    'target_detection_ms': 50
                },
                {
                    'name': 'Gradual voice onset',
                    'voice_strength': 0.6, 
                    'onset_samples': 80,  # 5ms ramp
                    'target_detection_ms': 100
                },
                {
                    'name': 'Weak voice signal',
                    'voice_strength': 0.3,
                    'onset_samples': 0,
                    'target_detection_ms': 150
                },
                {
                    'name': 'Noisy environment',
                    'voice_strength': 0.5,
                    'background_noise': 0.1,
                    'target_detection_ms': 120
                }
            ]
            
            detection_results = []
            
            for scenario in test_scenarios:
                # Generate test signal
                signal = self.generate_barge_in_test_signal(scenario)
                
                # Simulate detection
                detection_time_ms = self.simulate_barge_in_detection(signal, scenario)
                
                # Check if within target
                target_ms = scenario['target_detection_ms']
                success = detection_time_ms <= target_ms and detection_time_ms > 0
                
                result = {
                    'name': scenario['name'],
                    'target_ms': target_ms,
                    'actual_ms': detection_time_ms,
                    'success': success
                }
                
                detection_results.append(result)
                
                if success:
                    logger.info(f"  ✅ {scenario['name']}: {detection_time_ms:.1f}ms (target: {target_ms}ms)")
                else:
                    logger.error(f"  ❌ {scenario['name']}: {detection_time_ms:.1f}ms (target: {target_ms}ms)")
            
            # Overall success
            successful_detections = sum(1 for r in detection_results if r['success'])
            overall_success = successful_detections >= len(test_scenarios) * 0.8
            
            self.results['detailed_results']['detection_speed'] = {
                'results': detection_results,
                'successful_detections': successful_detections,
                'passed': overall_success
            }
            
            if overall_success:
                logger.info(f"✅ Detection speed test passed: {successful_detections}/{len(test_scenarios)}")
                self.results['tests_passed'] += 1
            else:
                logger.error(f"❌ Detection speed test failed: {successful_detections}/{len(test_scenarios)}")
                self.results['tests_failed'] += 1
                
        except Exception as e:
            logger.error(f"❌ Detection speed test crashed: {e}")
            self.results['tests_failed'] += 1
    
    def test_confidence_scoring(self):
        """Test confidence scoring accuracy"""
        logger.info("🧪 Testing confidence scoring...")
        self.results['tests_run'] += 1
        
        try:
            # Create test cases with known confidence levels
            confidence_test_cases = [
                {
                    'description': 'Clear strong voice',
                    'signal_type': 'clear_voice',
                    'strength': 0.9,
                    'expected_confidence_range': (0.8, 1.0)
                },
                {
                    'description': 'Moderate voice', 
                    'signal_type': 'moderate_voice',
                    'strength': 0.6,
                    'expected_confidence_range': (0.6, 0.8)
                },
                {
                    'description': 'Weak voice',
                    'signal_type': 'weak_voice', 
                    'strength': 0.3,
                    'expected_confidence_range': (0.3, 0.6)
                },
                {
                    'description': 'Voice with noise',
                    'signal_type': 'noisy_voice',
                    'strength': 0.7,
                    'background_noise': 0.2,
                    'expected_confidence_range': (0.4, 0.7)
                },
                {
                    'description': 'Whispered voice',
                    'signal_type': 'whisper',
                    'strength': 0.2,
                    'expected_confidence_range': (0.2, 0.4)
                },
                {
                    'description': 'Non-voice sound',
                    'signal_type': 'non_voice',
                    'expected_confidence_range': (0.0, 0.3)
                }
            ]
            
            confidence_results = []
            
            for test_case in confidence_test_cases:
                # Generate test signal
                signal = self.generate_confidence_test_signal(test_case)
                
                # Calculate confidence
                actual_confidence = self.calculate_barge_in_confidence(signal)
                
                # Check if within expected range
                expected_min, expected_max = test_case['expected_confidence_range']
                in_range = expected_min <= actual_confidence <= expected_max
                
                result = {
                    'description': test_case['description'],
                    'expected_range': test_case['expected_confidence_range'],
                    'actual_confidence': actual_confidence,
                    'in_range': in_range
                }
                
                confidence_results.append(result)
                
                if in_range:
                    logger.info(f"  ✅ {test_case['description']}: {actual_confidence:.3f} (expected: {expected_min:.1f}-{expected_max:.1f})")
                else:
                    logger.error(f"  ❌ {test_case['description']}: {actual_confidence:.3f} (expected: {expected_min:.1f}-{expected_max:.1f})")
            
            # Overall success
            accurate_scores = sum(1 for r in confidence_results if r['in_range'])
            overall_success = accurate_scores >= len(confidence_test_cases) * 0.8
            
            self.results['detailed_results']['confidence_scoring'] = {
                'results': confidence_results,
                'accurate_scores': accurate_scores,
                'passed': overall_success
            }
            
            if overall_success:
                logger.info(f"✅ Confidence scoring test passed: {accurate_scores}/{len(confidence_test_cases)}")
                self.results['tests_passed'] += 1
            else:
                logger.error(f"❌ Confidence scoring test failed: {accurate_scores}/{len(confidence_test_cases)}")
                self.results['tests_failed'] += 1
                
        except Exception as e:
            logger.error(f"❌ Confidence scoring test crashed: {e}")
            self.results['tests_failed'] += 1
    
    def test_false_positive_rejection(self):
        """Test rejection of false positive triggers"""
        logger.info("🧪 Testing false positive rejection...")
        self.results['tests_run'] += 1
        
        try:
            # Non-voice sounds that should NOT trigger barge-in
            false_positive_sounds = [
                {
                    'name': 'Keyboard typing',
                    'generator': self.generate_keyboard_sound,
                    'max_acceptable_confidence': 0.2
                },
                {
                    'name': 'Mouse clicks',
                    'generator': self.generate_mouse_clicks,
                    'max_acceptable_confidence': 0.1
                },
                {
                    'name': 'Paper shuffling',
                    'generator': self.generate_paper_shuffling,
                    'max_acceptable_confidence': 0.3
                },
                {
                    'name': 'Background music',
                    'generator': self.generate_background_music, 
                    'max_acceptable_confidence': 0.4
                },
                {
                    'name': 'Air conditioning hum',
                    'generator': self.generate_ac_hum,
                    'max_acceptable_confidence': 0.1
                },
                {
                    'name': 'Car engine outside',
                    'generator': self.generate_car_engine,
                    'max_acceptable_confidence': 0.2
                },
                {
                    'name': 'Footsteps',
                    'generator': self.generate_footsteps,
                    'max_acceptable_confidence': 0.3
                },
                {
                    'name': 'Door closing',
                    'generator': self.generate_door_close,
                    'max_acceptable_confidence': 0.2
                }
            ]
            
            rejection_results = []
            
            for sound_test in false_positive_sounds:
                # Generate non-voice sound
                signal = sound_test['generator']()
                
                # Calculate barge-in confidence
                confidence = self.calculate_barge_in_confidence(signal)
                
                # Check if properly rejected
                max_acceptable = sound_test['max_acceptable_confidence']
                properly_rejected = confidence <= max_acceptable
                
                result = {
                    'name': sound_test['name'],
                    'confidence': confidence,
                    'max_acceptable': max_acceptable,
                    'properly_rejected': properly_rejected
                }
                
                rejection_results.append(result)
                
                if properly_rejected:
                    logger.info(f"  ✅ {sound_test['name']}: confidence={confidence:.3f} (< {max_acceptable:.1f})")
                else:
                    logger.error(f"  ❌ {sound_test['name']}: confidence={confidence:.3f} (should be < {max_acceptable:.1f})")
            
            # Overall success
            properly_rejected_count = sum(1 for r in rejection_results if r['properly_rejected'])
            overall_success = properly_rejected_count >= len(false_positive_sounds) * 0.9  # High bar för false positives
            
            # Calculate false positive rate
            false_positive_rate = (len(false_positive_sounds) - properly_rejected_count) / len(false_positive_sounds)
            
            self.results['detailed_results']['false_positive_rejection'] = {
                'results': rejection_results,
                'properly_rejected_count': properly_rejected_count,
                'false_positive_rate': false_positive_rate,
                'passed': overall_success
            }
            
            if overall_success:
                logger.info(f"✅ False positive test passed: {properly_rejected_count}/{len(false_positive_sounds)} (FP rate: {false_positive_rate:.1%})")
                self.results['tests_passed'] += 1
            else:
                logger.error(f"❌ False positive test failed: {properly_rejected_count}/{len(false_positive_sounds)} (FP rate: {false_positive_rate:.1%})")
                self.results['tests_failed'] += 1
                
        except Exception as e:
            logger.error(f"❌ False positive test crashed: {e}")
            self.results['tests_failed'] += 1
    
    def test_voice_classification_accuracy(self):
        """Test accuracy of voice vs non-voice classification"""
        logger.info("🧪 Testing voice classification accuracy...")
        self.results['tests_run'] += 1
        
        try:
            # Create balanced dataset of voice and non-voice samples
            test_samples = []
            
            # Voice samples (should be detected)
            voice_types = ['male_voice', 'female_voice', 'child_voice', 'whisper', 'shouting']
            for voice_type in voice_types:
                for i in range(3):  # 3 samples per type
                    signal = self.generate_voice_sample(voice_type)
                    test_samples.append({
                        'signal': signal,
                        'is_voice': True,
                        'type': voice_type
                    })
            
            # Non-voice samples (should NOT be detected)
            non_voice_types = ['music', 'nature_sounds', 'mechanical_noise', 'electronic_beeps', 'silence']
            for non_voice_type in non_voice_types:
                for i in range(3):  # 3 samples per type
                    signal = self.generate_non_voice_sample(non_voice_type)
                    test_samples.append({
                        'signal': signal,
                        'is_voice': False,
                        'type': non_voice_type
                    })
            
            # Classification results
            correct_classifications = 0
            classification_results = []
            
            # Classification thresholds
            voice_threshold = 0.5  # Confidence above this = voice detected
            
            for sample in test_samples:
                confidence = self.calculate_barge_in_confidence(sample['signal'])
                detected_as_voice = confidence > voice_threshold
                correct = detected_as_voice == sample['is_voice']
                
                if correct:
                    correct_classifications += 1
                
                result = {
                    'type': sample['type'],
                    'is_voice': sample['is_voice'], 
                    'confidence': confidence,
                    'detected_as_voice': detected_as_voice,
                    'correct': correct
                }
                
                classification_results.append(result)
                
                status = "✅" if correct else "❌"
                logger.info(f"  {status} {sample['type']}: confidence={confidence:.3f}, detected={detected_as_voice}, actual={sample['is_voice']}")
            
            # Calculate metrics
            accuracy = correct_classifications / len(test_samples)
            
            # Calculate precision and recall for voice detection
            true_positives = sum(1 for r in classification_results if r['is_voice'] and r['detected_as_voice'])
            false_positives = sum(1 for r in classification_results if not r['is_voice'] and r['detected_as_voice'])
            false_negatives = sum(1 for r in classification_results if r['is_voice'] and not r['detected_as_voice'])
            
            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            # Success criteria
            success = accuracy >= 0.8 and precision >= 0.8 and recall >= 0.8
            
            self.results['detailed_results']['voice_classification'] = {
                'results': classification_results,
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1_score,
                'correct_classifications': correct_classifications,
                'total_samples': len(test_samples),
                'passed': success
            }
            
            logger.info(f"  📊 Accuracy: {accuracy:.3f}")
            logger.info(f"  📊 Precision: {precision:.3f}")
            logger.info(f"  📊 Recall: {recall:.3f}")
            logger.info(f"  📊 F1 Score: {f1_score:.3f}")
            
            if success:
                logger.info(f"✅ Voice classification test passed")
                self.results['tests_passed'] += 1
            else:
                logger.error(f"❌ Voice classification test failed (acc={accuracy:.3f}, prec={precision:.3f}, rec={recall:.3f})")
                self.results['tests_failed'] += 1
                
        except Exception as e:
            logger.error(f"❌ Voice classification test crashed: {e}")
            self.results['tests_failed'] += 1
    
    def test_context_awareness(self):
        """Test context-aware barge-in detection (only when Alice is speaking)"""
        logger.info("🧪 Testing context-aware detection...")
        self.results['tests_run'] += 1
        
        try:
            # Test scenarios with different Alice speaking states
            context_scenarios = [
                {
                    'name': 'Alice speaking - should detect barge-in',
                    'alice_speaking': True,
                    'user_voice_strength': 0.7,
                    'should_detect': True
                },
                {
                    'name': 'Alice silent - should not detect as barge-in',
                    'alice_speaking': False,
                    'user_voice_strength': 0.7, 
                    'should_detect': False
                },
                {
                    'name': 'Alice just finished - grace period',
                    'alice_speaking': False,
                    'alice_stopped_ms_ago': 200,
                    'user_voice_strength': 0.6,
                    'should_detect': False
                },
                {
                    'name': 'Alice speaking loudly - harder detection',
                    'alice_speaking': True,
                    'alice_volume': 0.8,
                    'user_voice_strength': 0.5,
                    'should_detect': True,
                    'expected_confidence_reduction': 0.2
                }
            ]
            
            context_results = []
            
            for scenario in context_scenarios:
                # Generate test signal
                signal = self.generate_context_test_signal(scenario)
                
                # Simulate context-aware detection
                detection_result = self.simulate_context_aware_detection(signal, scenario)
                
                detected = detection_result['detected']
                confidence = detection_result['confidence']
                should_detect = scenario['should_detect']
                
                correct = detected == should_detect
                
                result = {
                    'name': scenario['name'],
                    'should_detect': should_detect,
                    'actually_detected': detected,
                    'confidence': confidence,
                    'correct': correct
                }
                
                context_results.append(result)
                
                status = "✅" if correct else "❌"
                logger.info(f"  {status} {scenario['name']}: detected={detected}, should={should_detect}, conf={confidence:.3f}")
            
            # Overall success
            correct_contexts = sum(1 for r in context_results if r['correct'])
            overall_success = correct_contexts >= len(context_scenarios) * 0.8
            
            self.results['detailed_results']['context_awareness'] = {
                'results': context_results,
                'correct_contexts': correct_contexts,
                'passed': overall_success
            }
            
            if overall_success:
                logger.info(f"✅ Context awareness test passed: {correct_contexts}/{len(context_scenarios)}")
                self.results['tests_passed'] += 1
            else:
                logger.error(f"❌ Context awareness test failed: {correct_contexts}/{len(context_scenarios)}")
                self.results['tests_failed'] += 1
                
        except Exception as e:
            logger.error(f"❌ Context awareness test crashed: {e}")
            self.results['tests_failed'] += 1

    # Signal generation methods
    
    def generate_barge_in_test_signal(self, scenario: Dict[str, Any]) -> np.ndarray:
        """Generate test signal för barge-in detection speed test"""
        duration_samples = 3200  # 200ms at 16kHz
        signal = np.zeros(duration_samples)
        
        voice_strength = scenario['voice_strength']
        onset_samples = scenario.get('onset_samples', 0)
        
        # Generate voice signal
        voice_signal = self.generate_realistic_voice_signal(duration_samples, voice_strength)
        
        # Apply onset ramp if specified
        if onset_samples > 0:
            ramp = np.linspace(0, 1, onset_samples)
            voice_signal[:onset_samples] *= ramp
        
        signal += voice_signal
        
        # Add background noise if specified
        if 'background_noise' in scenario:
            noise_level = scenario['background_noise']
            noise = np.random.normal(0, noise_level, duration_samples)
            signal += noise
        
        return signal
    
    def generate_confidence_test_signal(self, test_case: Dict[str, Any]) -> np.ndarray:
        """Generate signal för confidence scoring test"""
        duration_samples = 2400  # 150ms
        
        signal_type = test_case['signal_type']
        
        if signal_type == 'clear_voice':
            signal = self.generate_realistic_voice_signal(duration_samples, test_case['strength'])
            
        elif signal_type == 'moderate_voice':
            signal = self.generate_realistic_voice_signal(duration_samples, test_case['strength'])
            # Add slight distortion
            signal += 0.05 * np.random.randn(duration_samples)
            
        elif signal_type == 'weak_voice':
            signal = self.generate_realistic_voice_signal(duration_samples, test_case['strength'])
            
        elif signal_type == 'noisy_voice':
            signal = self.generate_realistic_voice_signal(duration_samples, test_case['strength'])
            noise = np.random.normal(0, test_case['background_noise'], duration_samples)
            signal += noise
            
        elif signal_type == 'whisper':
            # Whisper has different spectral characteristics
            signal = self.generate_whisper_signal(duration_samples, test_case['strength'])
            
        elif signal_type == 'non_voice':
            # Generate non-voice sound (random noise with some structure)
            signal = np.random.normal(0, 0.3, duration_samples)
            # Add some periodic component to make it seem more structured
            t = np.arange(duration_samples) / self.sample_rate
            signal += 0.2 * np.sin(2 * np.pi * 1000 * t)  # 1kHz tone
            
        else:
            signal = np.zeros(duration_samples)
        
        return signal
    
    def generate_realistic_voice_signal(self, length: int, strength: float) -> np.ndarray:
        """Generate realistic human voice signal"""
        t = np.arange(length) / self.sample_rate
        
        # Use male voice characteristics as default
        f0_min, f0_max = self.voice_characteristics['male_voice']['f0_range']
        formants = self.voice_characteristics['male_voice']['formants']
        
        # Varying fundamental frequency (natural speech prosody)
        f0 = f0_min + (f0_max - f0_min) * 0.5 * (1 + 0.3 * np.sin(2 * np.pi * 8 * t))
        
        # Generate voice signal with harmonics and formants
        signal = np.zeros(length)
        
        # Add harmonics
        for harmonic in range(1, 6):
            amplitude = strength / harmonic  # Decreasing amplitude
            signal += amplitude * np.sin(2 * np.pi * harmonic * f0 * t)
        
        # Apply formant filtering (simplified)
        for formant_freq in formants[:2]:  # Use first two formants
            # Simple resonance filter
            resonance = 1 + 0.5 * np.exp(-((np.fft.fftfreq(length, 1/self.sample_rate) - formant_freq) / 200)**2)
            signal_fft = np.fft.fft(signal)
            signal_fft *= resonance[:len(signal_fft)]
            signal = np.real(np.fft.ifft(signal_fft))
        
        # Apply speech envelope
        envelope = 0.5 * (1 + np.sin(2 * np.pi * 12 * t))  # 12 Hz modulation
        signal *= envelope
        
        return signal
    
    def generate_whisper_signal(self, length: int, strength: float) -> np.ndarray:
        """Generate whispered speech signal"""
        # Whisper has more noise-like characteristics, less harmonic structure
        signal = strength * np.random.randn(length)
        
        # Apply formant-like filtering
        formants = [800, 1400, 2800]  # Slightly higher than normal speech
        
        for formant_freq in formants:
            # Broadband resonance for whisper
            resonance = 1 + 0.3 * np.exp(-((np.fft.fftfreq(length, 1/self.sample_rate) - formant_freq) / 300)**2)
            signal_fft = np.fft.fft(signal)
            signal_fft *= resonance[:len(signal_fft)]
            signal = np.real(np.fft.ifft(signal_fft))
        
        # Apply speech-like envelope
        t = np.arange(length) / self.sample_rate
        envelope = 0.7 * (1 + 0.3 * np.sin(2 * np.pi * 8 * t))
        signal *= envelope
        
        return signal
    
    def generate_voice_sample(self, voice_type: str) -> np.ndarray:
        """Generate voice sample of specific type"""
        length = 2400  # 150ms
        
        if voice_type == 'male_voice':
            characteristics = self.voice_characteristics['male_voice']
        elif voice_type == 'female_voice':
            characteristics = self.voice_characteristics['female_voice']
        elif voice_type == 'child_voice':
            characteristics = self.voice_characteristics['child_voice']
        elif voice_type == 'whisper':
            return self.generate_whisper_signal(length, 0.3)
        elif voice_type == 'shouting':
            signal = self.generate_realistic_voice_signal(length, 0.9)
            # Add distortion för shouting
            signal = np.tanh(signal * 3) * 0.8
            return signal
        else:
            characteristics = self.voice_characteristics['male_voice']
        
        # Generate signal with specific characteristics
        t = np.arange(length) / self.sample_rate
        f0_min, f0_max = characteristics['f0_range']
        f0 = f0_min + (f0_max - f0_min) * 0.5
        
        signal = np.zeros(length)
        for harmonic in range(1, 4):
            amplitude = 0.4 / harmonic
            signal += amplitude * np.sin(2 * np.pi * harmonic * f0 * t)
        
        return signal
    
    def generate_non_voice_sample(self, sample_type: str) -> np.ndarray:
        """Generate non-voice sample of specific type"""
        length = 2400  # 150ms
        t = np.arange(length) / self.sample_rate
        
        if sample_type == 'music':
            # Simple musical chord
            freqs = [440, 550, 660]  # A major chord
            signal = sum(0.3 * np.sin(2 * np.pi * f * t) för f in freqs)
            
        elif sample_type == 'nature_sounds':
            # Wind-like broadband noise
            signal = 0.2 * np.random.randn(length)
            # Low-pass filter
            from scipy import signal as scipy_signal
            b, a = scipy_signal.butter(4, 2000, 'low', fs=self.sample_rate)
            signal = scipy_signal.filtfilt(b, a, signal)
            
        elif sample_type == 'mechanical_noise':
            # Motor-like periodic noise
            signal = 0.3 * np.sin(2 * np.pi * 50 * t)  # 50 Hz hum
            signal += 0.1 * np.random.randn(length)
            
        elif sample_type == 'electronic_beeps':
            # Series of beeps
            beep_freq = 1000
            beep_duration = 0.02  # 20ms beeps
            beep_samples = int(beep_duration * self.sample_rate)
            
            signal = np.zeros(length)
            för i in range(0, length, beep_samples * 3):
                if i + beep_samples < length:
                    signal[i:i+beep_samples] = 0.5 * np.sin(2 * np.pi * beep_freq * np.arange(beep_samples) / self.sample_rate)
                    
        elif sample_type == 'silence':
            signal = 0.01 * np.random.randn(length)  # Very quiet noise
            
        else:
            signal = np.zeros(length)
        
        return signal
    
    # Non-voice sound generators för false positive testing
    
    def generate_keyboard_sound(self) -> np.ndarray:
        """Generate keyboard typing sound"""
        length = 2400
        signal = np.zeros(length)
        
        # Multiple key clicks
        click_positions = [300, 800, 1300, 1800]
        för pos in click_positions:
            if pos < length - 100:
                # Sharp click with quick decay
                click = 0.3 * np.exp(-np.arange(100) / 20) * np.random.randn(100)
                signal[pos:pos+100] += click
        
        return signal
    
    def generate_mouse_clicks(self) -> np.ndarray:
        """Generate mouse click sounds"""
        length = 2400
        signal = np.zeros(length)
        
        # Two clicks (double-click)
        för pos in [800, 1000]:
            if pos < length - 50:
                click = 0.2 * np.exp(-np.arange(50) / 10) * np.random.randn(50)
                signal[pos:pos+50] += click
        
        return signal
    
    def generate_paper_shuffling(self) -> np.ndarray:
        """Generate paper shuffling sound"""
        length = 2400
        # High-frequency broadband noise
        signal = 0.15 * np.random.randn(length)
        
        # High-pass filter to emphasize paper-like characteristics
        cutoff = 2000
        b = np.array([1, -0.9])  # Simple high-pass
        a = np.array([1, -0.95])
        för i in range(1, length):
            signal[i] = b[0] * signal[i] + b[1] * signal[i-1] - a[1] * (signal[i-1] if i > 0 else 0)
        
        return signal
    
    def generate_background_music(self) -> np.ndarray:
        """Generate background music"""
        length = 2400
        t = np.arange(length) / self.sample_rate
        
        # Simple melody
        freqs = [262, 294, 330, 349]  # C, D, E, F
        signal = sum(0.1 * np.sin(2 * np.pi * f * t) för f in freqs)
        
        return signal
    
    def generate_ac_hum(self) -> np.ndarray:
        """Generate air conditioning hum"""
        length = 2400
        t = np.arange(length) / self.sample_rate
        
        # Low frequency hum with harmonics
        signal = 0.1 * np.sin(2 * np.pi * 60 * t)  # 60 Hz
        signal += 0.05 * np.sin(2 * np.pi * 120 * t)  # 120 Hz harmonic
        signal += 0.02 * np.random.randn(length)  # Random component
        
        return signal
    
    def generate_car_engine(self) -> np.ndarray:
        """Generate car engine sound"""
        length = 2400
        t = np.arange(length) / self.sample_rate
        
        # Low frequency rumble with modulation
        base_freq = 30 + 10 * np.sin(2 * np.pi * 3 * t)  # Varying RPM
        signal = 0.2 * np.sin(2 * np.pi * base_freq * t)
        signal += 0.1 * np.random.randn(length)
        
        return signal
    
    def generate_footsteps(self) -> np.ndarray:
        """Generate footstep sounds"""
        length = 2400
        signal = np.zeros(length)
        
        # Two footsteps
        för pos in [600, 1400]:
            if pos < length - 200:
                # Footstep has initial impact then decay
                step = 0.4 * np.exp(-np.arange(200) / 50) * (1 + 0.5 * np.random.randn(200))
                signal[pos:pos+200] += step
        
        return signal
    
    def generate_door_close(self) -> np.ndarray:
        """Generate door closing sound"""
        length = 2400
        signal = np.zeros(length)
        
        # Impact at beginning, then decay
        impact_length = 300
        impact = 0.5 * np.exp(-np.arange(impact_length) / 100) * np.random.randn(impact_length)
        signal[:impact_length] = impact
        
        return signal
    
    def generate_context_test_signal(self, scenario: Dict[str, Any]) -> np.ndarray:
        """Generate signal för context-aware testing"""
        length = 2400
        
        # User voice part
        user_strength = scenario['user_voice_strength']
        user_voice = self.generate_realistic_voice_signal(length, user_strength)
        
        signal = user_voice.copy()
        
        # If Alice is speaking, add her voice as background
        if scenario.get('alice_speaking', False):
            alice_volume = scenario.get('alice_volume', 0.6)
            # Alice's voice with different characteristics
            alice_voice = self.generate_realistic_voice_signal(length, alice_volume)
            # Make Alice's voice slightly different (different F0)
            t = np.arange(length) / self.sample_rate
            alice_voice *= np.sin(2 * np.pi * 180 * t)  # 180 Hz instead of 150 Hz
            
            signal += alice_voice
        
        return signal
    
    # Detection simulation methods
    
    def simulate_barge_in_detection(self, signal: np.ndarray, scenario: Dict[str, Any]) -> float:
        """Simulate barge-in detection and return detection time"""
        window_size = 80  # 5ms windows at 16kHz
        
        för i in range(0, len(signal) - window_size, window_size):
            window = signal[i:i+window_size]
            
            # Calculate basic features
            energy = np.mean(window ** 2)
            zcr = np.sum(np.diff(np.signbit(window))) / len(window)
            
            # Voice activity detection
            if energy > 0.01 and 0.05 < zcr < 0.5:  # Voice-like characteristics
                detection_time_ms = (i / self.sample_rate) * 1000
                return detection_time_ms
        
        return -1  # No detection
    
    def calculate_barge_in_confidence(self, signal: np.ndarray) -> float:
        """Calculate barge-in confidence för signal"""
        # Multiple features for confidence calculation
        
        # Energy
        energy = np.mean(signal ** 2)
        energy_score = min(1.0, energy / 0.1)
        
        # Zero crossing rate (voice indicator)
        zcr = np.sum(np.diff(np.signbit(signal))) / len(signal)
        zcr_score = 1.0 if 0.1 < zcr < 0.4 else 0.5
        
        # Spectral characteristics
        fft = np.fft.fft(signal)
        magnitude = np.abs(fft[:len(fft)//2])
        
        # Spectral centroid
        freqs = np.fft.fftfreq(len(signal), 1/self.sample_rate)[:len(fft)//2]
        spectral_centroid = np.sum(freqs * magnitude) / (np.sum(magnitude) + 1e-10)
        
        # Voice-like spectral centroid (500-3000 Hz)
        spectral_score = 1.0 if 500 < spectral_centroid < 3000 else 0.3
        
        # Harmonic content (simplified)
        # Look för peaks in low frequencies (fundamental)
        low_freq_power = np.sum(magnitude[1:40])  # ~0-500 Hz
        total_power = np.sum(magnitude) + 1e-10
        harmonic_score = min(1.0, low_freq_power / total_power * 5)
        
        # Combine features
        confidence = (
            energy_score * 0.3 +
            zcr_score * 0.25 +
            spectral_score * 0.25 +
            harmonic_score * 0.2
        )
        
        return min(1.0, confidence)
    
    def simulate_context_aware_detection(self, signal: np.ndarray, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate context-aware detection"""
        base_confidence = self.calculate_barge_in_confidence(signal)
        
        alice_speaking = scenario.get('alice_speaking', False)
        
        # Only detect as barge-in if Alice is speaking
        detected = alice_speaking and base_confidence > 0.5
        
        # Reduce confidence if Alice is speaking loudly
        if alice_speaking:
            alice_volume = scenario.get('alice_volume', 0.6)
            if alice_volume > 0.7:
                # Harder to detect user över loud Alice
                adjusted_confidence = base_confidence * (1 - (alice_volume - 0.7) / 0.3 * 0.3)
                detected = adjusted_confidence > 0.5
            else:
                adjusted_confidence = base_confidence
        else:
            # Not a barge-in if Alice isn't speaking
            adjusted_confidence = base_confidence * 0.2  # Still some confidence, but low
            detected = False
        
        return {
            'detected': detected,
            'confidence': adjusted_confidence,
            'base_confidence': base_confidence
        }

    def generate_test_report(self):
        """Generate detailed test report"""
        success_rate = (self.results['tests_passed'] / self.results['tests_run']) * 100 if self.results['tests_run'] > 0 else 0
        
        logger.info("")
        logger.info("==================================================")
        logger.info("🎯 BARGE-IN DETECTION TEST RESULTS")
        logger.info("==================================================")
        logger.info(f"🧪 Tests run: {self.results['tests_run']}")
        logger.info(f"✅ Passed: {self.results['tests_passed']}")
        logger.info(f"❌ Failed: {self.results['tests_failed']}")
        logger.info(f"📊 Success rate: {success_rate:.1f}%")
        
        # Detailed results
        logger.info("")
        logger.info("📋 DETAILED RESULTS:")
        för test_name, details in self.results['detailed_results'].items():
            status = "PASS" if details.get('passed', False) else "FAIL"
            logger.info(f"  {test_name}: {status}")
            
            if test_name == 'voice_classification' and 'accuracy' in details:
                logger.info(f"    - Accuracy: {details['accuracy']:.3f}")
                logger.info(f"    - Precision: {details['precision']:.3f}")
                logger.info(f"    - Recall: {details['recall']:.3f}")
            elif test_name == 'false_positive_rejection' and 'false_positive_rate' in details:
                logger.info(f"    - False Positive Rate: {details['false_positive_rate']:.1%}")
        
        if success_rate == 100.0:
            logger.info("🎉 ALL BARGE-IN DETECTION TESTS PASSED!")
            return 0
        else:
            logger.error(f"💥 {self.results['tests_failed']} barge-in detection tests failed!")
            return 1

def main():
    """Main test runner för barge-in detection"""
    logger.info("🎯 Starting Barge-in Detection Specialized Test")
    
    test_suite = BargeInDetectionTest()
    
    try:
        # Run all barge-in detection tests
        test_suite.test_detection_speed()
        test_suite.test_confidence_scoring()
        test_suite.test_false_positive_rejection()
        test_suite.test_voice_classification_accuracy() 
        test_suite.test_context_awareness()
        
        # Generate report
        return test_suite.generate_test_report()
        
    except Exception as e:
        logger.error(f"💥 Barge-in detection test suite crashed: {e}")
        return 1

if __name__ == "__main__":
    # Fix syntax error - use regular for loops
    import sys
    sys.exit(main())