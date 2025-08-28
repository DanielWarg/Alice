#!/usr/bin/env node
/**
 * Autonomous Voice Pipeline Test Runner
 * Executes comprehensive real-time testing with validation and cleanup
 */

import { AutonomousVoiceTester } from './autonomous/index';
import { TestLogger } from './utils/test_logger';
import { RealtimeAudioGenerator } from './autonomous/realtime_audio_generator';
import { PrivacyValidator } from './validation/privacy_validator';
import { LatencyValidator } from './validation/latency_validator';
import { BargeInValidator } from './validation/barge_in_validator';
import { MetricsLogger } from '../server/metrics/logger';
import * as fs from 'fs';
import * as path from 'path';

interface TestRunConfig {
  scenarios: string[];
  iterations_per_scenario: number;
  concurrent_sessions: number;
  test_duration_minutes: number;
  generate_audio_samples: boolean;
  validate_privacy: boolean;
  validate_latency: boolean;
  validate_barge_in: boolean;
  cleanup_after: boolean;
  log_level: 'debug' | 'info' | 'warn' | 'error';
}

const DEFAULT_TEST_CONFIG: TestRunConfig = {
  scenarios: ['short_queries', 'pii_filtering', 'tool_requests', 'interruptions', 'long_queries'],
  iterations_per_scenario: 10,
  concurrent_sessions: 3,
  test_duration_minutes: 5,
  generate_audio_samples: true,
  validate_privacy: true,
  validate_latency: true,
  validate_barge_in: true,
  cleanup_after: true,
  log_level: 'info'
};

export class TestRunner {
  private config: TestRunConfig;
  private logger: TestLogger;
  private tester: AutonomousVoiceTester;
  private audioGenerator: RealtimeAudioGenerator;
  private metricsLogger: MetricsLogger;
  private testStartTime: number = 0;

  constructor(config: Partial<TestRunConfig> = {}) {
    this.config = { ...DEFAULT_TEST_CONFIG, ...config };
    
    const testRunId = this.generateTestRunId();
    this.logger = new TestLogger(testRunId, 'logs/autonomous-tests');
    this.audioGenerator = new RealtimeAudioGenerator();
    this.metricsLogger = new MetricsLogger('logs/autonomous-tests');
    this.tester = new AutonomousVoiceTester(this.audioGenerator, this.metricsLogger);
  }

  private generateTestRunId(): string {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
    return `autonomous-${timestamp}`;
  }

  public async runTests(): Promise<TestResults> {
    this.testStartTime = Date.now();
    
    this.logger.info('system', '🚀 Starting autonomous voice pipeline tests', {
      config: this.config,
      timestamp: new Date().toISOString()
    });

    const results: TestResults = {
      overall_passed: true,
      total_tests: 0,
      passed_tests: 0,
      failed_tests: 0,
      scenarios_tested: [],
      performance_summary: null,
      validation_summary: null,
      duration_ms: 0,
      recommendations: []
    };

    try {
      // Initialize validators with logging
      await this.setupValidators();

      // Pre-test validation
      await this.preTestValidation();

      // Generate audio samples if needed
      if (this.config.generate_audio_samples) {
        await this.generateAudioSamples();
      }

      // Run test scenarios
      for (const scenario of this.config.scenarios) {
        this.logger.info('system', `📋 Starting scenario: ${scenario}`, { scenario });
        
        const scenarioResult = await this.runScenario(scenario);
        results.scenarios_tested.push(scenarioResult);
        
        results.total_tests += scenarioResult.total_tests;
        results.passed_tests += scenarioResult.passed_tests;
        results.failed_tests += scenarioResult.failed_tests;
      }

      // Generate performance summary
      results.performance_summary = await this.generatePerformanceSummary();
      
      // Generate validation summary
      results.validation_summary = await this.generateValidationSummary();
      
      // Calculate overall success
      results.overall_passed = results.failed_tests === 0 && 
                               this.validateOverallPerformance(results.performance_summary);

    } catch (error) {
      this.logger.error('system', 'Test execution failed', { error: error.message, stack: error.stack });
      results.overall_passed = false;
    } finally {
      results.duration_ms = Date.now() - this.testStartTime;
      
      // Cleanup if requested
      if (this.config.cleanup_after) {
        await this.cleanup();
      }

      // Generate recommendations
      results.recommendations = this.generateRecommendations(results);
      
      // Final logging
      await this.finalizeTests(results);
    }

    return results;
  }

  private async setupValidators(): Promise<void> {
    this.logger.info('system', '🔧 Setting up validators');

    // Setup validators in the tester
    if (this.config.validate_privacy) {
      const privacyValidator = new PrivacyValidator({ strict_mode: true });
      privacyValidator.setLogger(this.logger);
      this.tester.setPrivacyValidator(privacyValidator);
    }

    if (this.config.validate_latency) {
      const latencyValidator = new LatencyValidator({
        max_total_latency_ms: 500,
        max_first_partial_ms: 300,
        max_ttft_ms: 300,
        max_tts_first_chunk_ms: 150,
        max_barge_in_cut_ms: 120,
        min_success_rate: 0.95
      });
      latencyValidator.setLogger(this.logger);
      this.tester.setLatencyValidator(latencyValidator);
    }

    if (this.config.validate_barge_in) {
      const bargeInValidator = new BargeInValidator({
        max_interrupt_detection_ms: 50,
        max_playback_stop_ms: 100,
        max_new_response_start_ms: 200,
        require_smooth_fadeout: true,
        validate_audio_gaps: true
      });
      bargeInValidator.setLogger(this.logger);
      this.tester.setBargeInValidator(bargeInValidator);
    }

    this.logger.info('system', '✅ Validators configured successfully');
  }

  private async preTestValidation(): Promise<void> {
    this.logger.info('system', '🔍 Running pre-test validation');

    // Check if voice pipeline server is running
    try {
      const response = await fetch('http://localhost:8002/health');
      if (!response.ok) {
        throw new Error('Voice pipeline health check failed');
      }
      this.logger.info('system', '✅ Voice pipeline server is healthy');
    } catch (error) {
      this.logger.error('system', '❌ Voice pipeline server not available', { error: error.message });
      throw new Error('Voice pipeline server must be running on localhost:8002');
    }

    // Check required directories
    const requiredDirs = [
      'logs/autonomous-tests',
      'core/talk/tests/fixtures/audio',
      'core/talk/tests/results'
    ];

    for (const dir of requiredDirs) {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
        this.logger.info('system', `📁 Created directory: ${dir}`);
      }
    }

    this.logger.info('system', '✅ Pre-test validation completed');
  }

  private async generateAudioSamples(): Promise<void> {
    this.logger.info('system', '🎵 Generating audio samples for testing');

    const startTime = Date.now();
    
    try {
      // Generate samples for different scenarios
      const samples = [
        { scenario: 'short_queries', text: 'Hej Alice, vad är klockan?', name: 'short_greeting' },
        { scenario: 'pii_filtering', text: 'Min epost är test@example.com och telefon 070-123-4567', name: 'pii_data' },
        { scenario: 'tool_requests', text: 'Skicka ett mejl till teamet om mötet imorgon', name: 'tool_request' },
        { scenario: 'interruptions', text: 'Kan du förklara...', name: 'interrupt_start' },
        { scenario: 'long_queries', text: 'Förklara i detalj hur artificiell intelligens fungerar och dess påverkan på samhället', name: 'long_explanation' }
      ];

      for (const sample of samples) {
        try {
          const audioData = await this.audioGenerator.generateSpeech(sample.text, true);
          const duration = Date.now() - startTime;
          
          this.logger.logAudioGeneration('system', sample.text, 'synthetic', duration);
          this.logger.debug('audio', `Generated sample: ${sample.name}`, {
            scenario: sample.scenario,
            textLength: sample.text.length,
            audioSize: audioData.byteLength
          });
        } catch (error) {
          this.logger.warn('audio', `Failed to generate sample: ${sample.name}`, { error: error.message });
        }
      }

      const totalDuration = Date.now() - startTime;
      this.logger.info('system', `✅ Audio samples generated in ${totalDuration}ms`);
    } catch (error) {
      this.logger.error('system', 'Failed to generate audio samples', { error: error.message });
      throw error;
    }
  }

  private async runScenario(scenario: string): Promise<ScenarioResult> {
    const scenarioStartTime = Date.now();
    
    this.logger.logTestStart('system', 'scenario', scenario);

    const scenarioResult: ScenarioResult = {
      scenario,
      total_tests: this.config.iterations_per_scenario,
      passed_tests: 0,
      failed_tests: 0,
      duration_ms: 0,
      individual_results: []
    };

    for (let i = 0; i < this.config.iterations_per_scenario; i++) {
      const sessionId = `${scenario}-${i + 1}`;
      
      try {
        this.logger.logTestStart(sessionId, 'iteration', `${scenario} iteration ${i + 1}`);
        
        const testResult = await this.tester.runScenario(scenario, sessionId);
        
        scenarioResult.individual_results.push(testResult);
        
        if (testResult.success) {
          scenarioResult.passed_tests++;
        } else {
          scenarioResult.failed_tests++;
        }

        const iterationDuration = Date.now() - scenarioStartTime;
        this.logger.logTestComplete(sessionId, 'iteration', testResult.success, iterationDuration, {
          scenario,
          metrics: testResult.metrics
        });

      } catch (error) {
        scenarioResult.failed_tests++;
        this.logger.error('system', `Test iteration failed: ${sessionId}`, { error: error.message });
      }
    }

    scenarioResult.duration_ms = Date.now() - scenarioStartTime;
    
    const success = scenarioResult.failed_tests === 0;
    this.logger.logTestComplete('system', 'scenario', success, scenarioResult.duration_ms, {
      scenario,
      passRate: scenarioResult.passed_tests / scenarioResult.total_tests
    });

    return scenarioResult;
  }

  private async generatePerformanceSummary(): Promise<any> {
    this.logger.info('system', '📊 Generating performance summary');

    const performanceStats = this.metricsLogger.getPerformanceStats();
    this.logger.logPerformanceSummary(performanceStats);

    return performanceStats;
  }

  private async generateValidationSummary(): Promise<any> {
    this.logger.info('system', '🔍 Generating validation summary');

    const validationSummary = {
      privacy: this.tester.getPrivacyStats(),
      latency: this.tester.getLatencyStats(), 
      bargeIn: this.tester.getBargeInStats()
    };

    this.logger.metric('validation', 'Validation summary generated', validationSummary);
    
    return validationSummary;
  }

  private validateOverallPerformance(performanceSummary: any): boolean {
    if (!performanceSummary?.realtime) {
      return false;
    }

    const stats = performanceSummary.realtime;
    
    // Check SLO targets
    const sloViolations = [];
    
    if (stats.total_latency_ms?.p95 > 500) {
      sloViolations.push(`Total latency p95 ${stats.total_latency_ms.p95.toFixed(1)}ms > 500ms`);
    }
    
    if (stats.first_partial_ms?.p95 > 300) {
      sloViolations.push(`First partial p95 ${stats.first_partial_ms.p95.toFixed(1)}ms > 300ms`);
    }
    
    if (stats.ttft_ms?.p95 > 300) {
      sloViolations.push(`TTFT p95 ${stats.ttft_ms.p95.toFixed(1)}ms > 300ms`);
    }
    
    if (stats.tts_first_chunk_ms?.p95 > 150) {
      sloViolations.push(`TTS first chunk p95 ${stats.tts_first_chunk_ms.p95.toFixed(1)}ms > 150ms`);
    }
    
    if (stats.targetAchievementRate < 95) {
      sloViolations.push(`Target achievement rate ${stats.targetAchievementRate.toFixed(1)}% < 95%`);
    }

    if (sloViolations.length > 0) {
      this.logger.error('system', 'SLO validation failed', { violations: sloViolations });
      return false;
    }

    this.logger.info('system', '✅ All SLO targets met');
    return true;
  }

  private generateRecommendations(results: TestResults): string[] {
    const recommendations: string[] = [];
    
    if (results.failed_tests > 0) {
      const failureRate = (results.failed_tests / results.total_tests) * 100;
      recommendations.push(`${failureRate.toFixed(1)}% test failure rate. Review failed test details.`);
    }

    if (results.performance_summary?.realtime?.privacyLeakAttempts > 0) {
      recommendations.push('Privacy leak attempts detected. Review PII handling and routing logic.');
    }

    if (results.performance_summary?.realtime?.targetAchievementRate < 90) {
      recommendations.push('Low latency target achievement. Consider performance optimizations.');
    }

    if (results.duration_ms > 30 * 60 * 1000) { // 30 minutes
      recommendations.push('Long test duration. Consider parallel execution or shorter scenarios.');
    }

    // Add scenario-specific recommendations
    for (const scenario of results.scenarios_tested) {
      const passRate = scenario.passed_tests / scenario.total_tests;
      if (passRate < 0.8) {
        recommendations.push(`Low success rate in ${scenario.scenario} (${(passRate * 100).toFixed(1)}%). Review scenario implementation.`);
      }
    }

    if (recommendations.length === 0) {
      recommendations.push('All tests passing! Voice pipeline performing excellently.');
    }

    return recommendations;
  }

  private async cleanup(): Promise<void> {
    this.logger.info('system', '🧹 Starting cleanup process');

    try {
      // Cleanup audio generator
      await this.audioGenerator.cleanup();
      
      // Cleanup metrics logger  
      this.metricsLogger.cleanup();
      
      // Cleanup test results older than 7 days
      await this.cleanupOldResults();
      
      this.logger.info('system', '✅ Cleanup completed successfully');
    } catch (error) {
      this.logger.error('system', 'Cleanup failed', { error: error.message });
    }
  }

  private async cleanupOldResults(): Promise<void> {
    const resultsDir = 'logs/autonomous-tests';
    
    if (!fs.existsSync(resultsDir)) {
      return;
    }

    const sevenDaysAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
    const files = fs.readdirSync(resultsDir);
    let cleanedCount = 0;

    for (const file of files) {
      const filePath = path.join(resultsDir, file);
      const stats = fs.statSync(filePath);
      
      if (stats.birthtimeMs < sevenDaysAgo) {
        fs.unlinkSync(filePath);
        cleanedCount++;
      }
    }

    if (cleanedCount > 0) {
      this.logger.info('system', `🗑️ Cleaned up ${cleanedCount} old test result files`);
    }
  }

  private async finalizeTests(results: TestResults): Promise<void> {
    // Generate and log final report
    const finalReport = this.logger.generateReport();
    
    this.logger.info('system', '🏁 Test execution completed', {
      results: {
        total_tests: results.total_tests,
        passed_tests: results.passed_tests,
        failed_tests: results.failed_tests,
        success_rate: ((results.passed_tests / results.total_tests) * 100).toFixed(1) + '%',
        duration_seconds: (results.duration_ms / 1000).toFixed(1)
      },
      recommendations: results.recommendations
    });

    // Cleanup logger
    this.logger.cleanup();
  }
}

// Interfaces
interface TestResults {
  overall_passed: boolean;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  scenarios_tested: ScenarioResult[];
  performance_summary: any;
  validation_summary: any;
  duration_ms: number;
  recommendations: string[];
}

interface ScenarioResult {
  scenario: string;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  duration_ms: number;
  individual_results: any[];
}

// CLI execution
async function main() {
  console.log('🤖 Alice Autonomous Voice Pipeline Test Runner\n');

  const args = process.argv.slice(2);
  const config: Partial<TestRunConfig> = {};

  // Parse command line arguments
  if (args.includes('--quick')) {
    config.iterations_per_scenario = 3;
    config.test_duration_minutes = 2;
    config.scenarios = ['short_queries', 'pii_filtering'];
  }

  if (args.includes('--comprehensive')) {
    config.iterations_per_scenario = 20;
    config.test_duration_minutes = 15;
    config.concurrent_sessions = 5;
  }

  if (args.includes('--no-cleanup')) {
    config.cleanup_after = false;
  }

  if (args.includes('--verbose')) {
    config.log_level = 'debug';
  }

  const runner = new TestRunner(config);
  
  try {
    const results = await runner.runTests();
    
    console.log('\n' + '='.repeat(50));
    console.log('🎯 AUTONOMOUS TEST RESULTS');
    console.log('='.repeat(50));
    console.log(`Overall Status: ${results.overall_passed ? '✅ PASSED' : '❌ FAILED'}`);
    console.log(`Total Tests: ${results.total_tests}`);
    console.log(`Passed: ${results.passed_tests} (${((results.passed_tests / results.total_tests) * 100).toFixed(1)}%)`);
    console.log(`Failed: ${results.failed_tests}`);
    console.log(`Duration: ${(results.duration_ms / 1000).toFixed(1)}s`);
    console.log('\n💡 Recommendations:');
    results.recommendations.forEach(rec => console.log(`   • ${rec}`));
    console.log('='.repeat(50) + '\n');

    // Exit with appropriate code
    process.exit(results.overall_passed ? 0 : 1);
    
  } catch (error) {
    console.error('❌ Test execution failed:', error.message);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

export { TestRunner, TestRunConfig, TestResults };