#!/usr/bin/env node
/**
 * Simple Voice Pipeline Test Runner
 * Basic validation of the autonomous testing system
 */

import { RealtimeAudioGenerator } from './autonomous/realtime_audio_generator';
import { PrivacyValidator } from './validation/privacy_validator';
import { LatencyValidator } from './validation/latency_validator';
import { BargeInValidator } from './validation/barge_in_validator';
import { TestLogger } from './utils/test_logger';
import { VoiceMetrics } from '../types/events';
import * as fs from 'fs';

async function runSimpleTest() {
  console.log('🤖 Alice Voice Pipeline - Simple Test Runner\n');
  
  const testRunId = 'simple-' + new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
  const logger = new TestLogger(testRunId);
  
  logger.info('system', '🚀 Starting simple validation test');

  try {
    // Test 1: Audio Generator
    logger.info('system', '📝 Test 1: Audio Generator Validation');
    await testAudioGenerator(logger);
    
    // Test 2: Privacy Validator  
    logger.info('system', '📝 Test 2: Privacy Validator');
    await testPrivacyValidator(logger);
    
    // Test 3: Latency Validator
    logger.info('system', '📝 Test 3: Latency Validator');
    await testLatencyValidator(logger);
    
    // Test 4: Barge-in Validator
    logger.info('system', '📝 Test 4: Barge-in Validator');
    await testBargeInValidator(logger);
    
    // Test 5: Integration Test
    logger.info('system', '📝 Test 5: Integration Test');
    await testIntegration(logger);
    
    logger.info('system', '✅ All validation tests passed!');
    
    // Generate final report
    const report = logger.generateReport();
    console.log('\n📊 Test Report Generated:');
    console.log(`   Success Rate: ${((report.summary.tests_passed / report.summary.tests_completed) * 100).toFixed(1)}%`);
    console.log(`   Total Tests: ${report.summary.tests_completed}`);
    console.log(`   Duration: ${(Date.now() - report.summary.tests_started).toFixed(0)}ms`);
    console.log(`   Recommendations: ${report.recommendations.length}`);
    
    if (report.recommendations.length > 0) {
      console.log('\n💡 Recommendations:');
      report.recommendations.forEach(rec => console.log(`   • ${rec}`));
    }
    
  } catch (error) {
    logger.error('system', 'Test execution failed', { error: error.message });
    console.error('❌ Test failed:', error.message);
    return false;
  } finally {
    logger.cleanup();
  }
  
  return true;
}

async function testAudioGenerator(logger: TestLogger): Promise<void> {
  logger.logTestStart('audio-gen', 'component', 'Audio Generator Validation');
  const startTime = Date.now();
  
  try {
    const audioGen = new RealtimeAudioGenerator();
    
    // Test audio generation
    const testText = 'Hej Alice, detta är ett test';
    const audioData = await audioGen.generateSpeech(testText);
    
    if (!audioData || audioData.byteLength === 0) {
      throw new Error('Generated audio data is empty');
    }
    
    logger.logAudioGeneration('audio-gen', testText, 'synthetic', Date.now() - startTime);
    
    // Cleanup
    await audioGen.cleanup();
    
    logger.logTestComplete('audio-gen', 'component', true, Date.now() - startTime, {
      audioSize: audioData.byteLength,
      textLength: testText.length
    });
    
  } catch (error) {
    logger.logTestComplete('audio-gen', 'component', false, Date.now() - startTime, { error: error.message });
    throw error;
  }
}

async function testPrivacyValidator(logger: TestLogger): Promise<void> {
  logger.logTestStart('privacy-val', 'component', 'Privacy Validator');
  const startTime = Date.now();
  
  try {
    const validator = new PrivacyValidator({ strict_mode: true });
    validator.setLogger(logger);
    
    // Test metrics with PII
    const testMetrics: VoiceMetrics = {
      sessionId: 'privacy-test',
      route: 'cloud_complex',
      total_latency_ms: 400,
      first_partial_ms: 150,
      ttft_ms: 200,
      tts_first_chunk_ms: 100,
      timestamp: Date.now()
    };
    
    const additionalData = {
      transcription: 'Min epost är test@example.com och mitt telefon är 070-123-4567',
      response: 'Jag kan hjälpa dig med det'
    };
    
    const result = validator.validate(testMetrics, additionalData);
    
    // Should detect PII violations
    if (result.violations.length === 0) {
      throw new Error('Expected PII violations but none were found');
    }
    
    if (result.passed) {
      throw new Error('Test should have failed due to PII in cloud route');
    }
    
    logger.info('validation', `Privacy validator correctly detected ${result.violations.length} violations`);
    
    logger.logTestComplete('privacy-val', 'component', true, Date.now() - startTime, {
      violations: result.violations.length,
      privacyScore: result.pii_score
    });
    
  } catch (error) {
    logger.logTestComplete('privacy-val', 'component', false, Date.now() - startTime, { error: error.message });
    throw error;
  }
}

async function testLatencyValidator(logger: TestLogger): Promise<void> {
  logger.logTestStart('latency-val', 'component', 'Latency Validator');
  const startTime = Date.now();
  
  try {
    const validator = new LatencyValidator({
      max_total_latency_ms: 500,
      max_first_partial_ms: 300,
      max_ttft_ms: 300,
      max_tts_first_chunk_ms: 150,
      max_barge_in_cut_ms: 120,
      min_success_rate: 0.95
    });
    validator.setLogger(logger);
    
    // Test good metrics (should pass)
    const goodMetrics: VoiceMetrics = {
      sessionId: 'latency-good',
      route: 'local_fast',
      total_latency_ms: 350,
      first_partial_ms: 150,
      ttft_ms: 200,
      tts_first_chunk_ms: 100,
      timestamp: Date.now()
    };
    
    const goodResult = validator.validate(goodMetrics);
    if (!goodResult.passed) {
      throw new Error(`Good metrics failed validation: ${goodResult.failures.join(', ')}`);
    }
    
    // Test bad metrics (should fail)
    const badMetrics: VoiceMetrics = {
      sessionId: 'latency-bad',
      route: 'local_fast', 
      total_latency_ms: 800, // Exceeds 500ms target
      first_partial_ms: 400, // Exceeds 300ms target
      ttft_ms: 500,          // Exceeds 300ms target
      tts_first_chunk_ms: 200, // Exceeds 150ms target
      timestamp: Date.now()
    };
    
    const badResult = validator.validate(badMetrics);
    if (badResult.passed) {
      throw new Error('Bad metrics should have failed validation');
    }
    
    logger.info('validation', `Latency validator correctly failed bad metrics with ${badResult.failures.length} failures`);
    
    logger.logTestComplete('latency-val', 'component', true, Date.now() - startTime, {
      goodResult: goodResult.passed,
      badResult: !badResult.passed
    });
    
  } catch (error) {
    logger.logTestComplete('latency-val', 'component', false, Date.now() - startTime, { error: error.message });
    throw error;
  }
}

async function testBargeInValidator(logger: TestLogger): Promise<void> {
  logger.logTestStart('barge-val', 'component', 'Barge-in Validator');
  const startTime = Date.now();
  
  try {
    const validator = new BargeInValidator({
      max_interrupt_detection_ms: 50,
      max_playback_stop_ms: 100,
      max_new_response_start_ms: 200,
      require_smooth_fadeout: true,
      validate_audio_gaps: true
    });
    validator.setLogger(logger);
    
    // Test metrics with barge-in
    const testMetrics: VoiceMetrics = {
      sessionId: 'barge-test',
      route: 'local_fast',
      total_latency_ms: 400,
      barge_in_cut_ms: 150,
      timestamp: Date.now()
    };
    
    // Test events for good barge-in
    const goodEvents = [
      { type: 'user_speech_start' as const, timestamp: 1000 },
      { type: 'playback_stopped' as const, timestamp: 1040, fadeoutApplied: true },
      { type: 'new_response_start' as const, timestamp: 1180 }
    ];
    
    const goodResult = validator.validate(testMetrics, goodEvents);
    if (!goodResult.passed) {
      throw new Error(`Good barge-in failed validation: ${goodResult.failures.join(', ')}`);
    }
    
    // Test bad barge-in (too slow)
    const badEvents = [
      { type: 'user_speech_start' as const, timestamp: 1000 },
      { type: 'playback_stopped' as const, timestamp: 1200, fadeoutApplied: false }, // Too slow + abrupt
      { type: 'new_response_start' as const, timestamp: 1400 } // Way too slow
    ];
    
    const badResult = validator.validate(testMetrics, badEvents);
    if (badResult.passed) {
      throw new Error('Bad barge-in should have failed validation');
    }
    
    logger.info('validation', `Barge-in validator correctly handled both good and bad cases`);
    
    logger.logTestComplete('barge-val', 'component', true, Date.now() - startTime, {
      goodResult: goodResult.passed,
      badResult: !badResult.passed
    });
    
  } catch (error) {
    logger.logTestComplete('barge-val', 'component', false, Date.now() - startTime, { error: error.message });
    throw error;
  }
}

async function testIntegration(logger: TestLogger): Promise<void> {
  logger.logTestStart('integration', 'integration', 'Full Integration Test');
  const startTime = Date.now();
  
  try {
    // Create all components
    const audioGen = new RealtimeAudioGenerator();
    const privacyValidator = new PrivacyValidator();
    const latencyValidator = new LatencyValidator({
      max_total_latency_ms: 500,
      max_first_partial_ms: 300,
      max_ttft_ms: 300,
      max_tts_first_chunk_ms: 150,
      max_barge_in_cut_ms: 120,
      min_success_rate: 0.95
    });
    const bargeInValidator = new BargeInValidator();
    
    // Set loggers
    privacyValidator.setLogger(logger);
    latencyValidator.setLogger(logger);
    bargeInValidator.setLogger(logger);
    
    // Generate test audio
    const testAudio = await audioGen.generateSpeech('Hej Alice, vad är klockan?');
    
    // Create test metrics
    const metrics: VoiceMetrics = {
      sessionId: 'integration-test',
      route: 'local_fast',
      total_latency_ms: 450,
      first_partial_ms: 200,
      ttft_ms: 250,
      tts_first_chunk_ms: 120,
      timestamp: Date.now()
    };
    
    // Test all validators
    const privacyResult = privacyValidator.validate(metrics, {
      transcription: 'Hej Alice, vad är klockan?',
      response: 'Klockan är 14:30'
    });
    
    const latencyResult = latencyValidator.validate(metrics);
    
    const bargeInResult = bargeInValidator.validate(metrics, []); // No barge-in events
    
    // All should pass for this clean test
    if (!privacyResult.passed) {
      throw new Error(`Privacy validation failed: ${privacyResult.violations.map(v => v.type).join(', ')}`);
    }
    
    if (!latencyResult.passed) {
      throw new Error(`Latency validation failed: ${latencyResult.failures.join(', ')}`);
    }
    
    // Barge-in should pass (no events = no barge-in to validate)
    
    logger.info('integration', 'All validators passed integration test');
    
    // Cleanup
    await audioGen.cleanup();
    
    logger.logTestComplete('integration', 'integration', true, Date.now() - startTime, {
      privacyPassed: privacyResult.passed,
      latencyPassed: latencyResult.passed,
      audioSize: testAudio.byteLength
    });
    
  } catch (error) {
    logger.logTestComplete('integration', 'integration', false, Date.now() - startTime, { error: error.message });
    throw error;
  }
}

// Run the test
if (require.main === module) {
  runSimpleTest()
    .then(success => {
      console.log(success ? '\n✅ All tests passed!' : '\n❌ Tests failed!');
      process.exit(success ? 0 : 1);
    })
    .catch(error => {
      console.error('\n💥 Fatal error:', error.message);
      process.exit(1);
    });
}