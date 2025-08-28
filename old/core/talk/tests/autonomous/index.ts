/**
 * Alice Voice Pipeline Autonomous Testing System
 * Real-time end-to-end testing with actual audio and live performance validation
 */

import { EventEmitter } from 'events';
import { VoicePipelineServer } from '../server';
import { RealtimeAudioGenerator } from './realtime_audio_generator';
import { LatencyValidator } from '../validation/latency_validator';
import { BargeInValidator } from '../validation/barge_in_validator';  
import { PrivacyValidator } from '../validation/privacy_validator';
import { VoiceMetrics } from '../types/events';
import * as fs from 'fs';

interface TestConfig {
  duration_minutes: number;
  concurrent_sessions: number;
  test_scenarios: string[];
  validation_targets: {
    max_total_latency_ms: number;
    max_first_partial_ms: number;
    max_ttft_ms: number;
    max_tts_first_chunk_ms: number;
    max_barge_in_cut_ms: number;
    min_success_rate: number;
  };
  audio_sources: {
    use_real_microphone: boolean;
    use_synthetic_speech: boolean;
    use_recorded_samples: boolean;
  };
  cleanup_after_test: boolean;
}

const DEFAULT_TEST_CONFIG: TestConfig = {
  duration_minutes: 10,
  concurrent_sessions: 3,
  test_scenarios: ['short_queries', 'interruptions', 'pii_filtering', 'tool_requests'],
  validation_targets: {
    max_total_latency_ms: 500,
    max_first_partial_ms: 300,
    max_ttft_ms: 300,
    max_tts_first_chunk_ms: 150,
    max_barge_in_cut_ms: 120,
    min_success_rate: 0.95
  },
  audio_sources: {
    use_real_microphone: false,
    use_synthetic_speech: true,
    use_recorded_samples: true
  },
  cleanup_after_test: true
};

export interface TestSession {
  id: string;
  scenario: string;
  startTime: number;
  endTime?: number;
  metrics: VoiceMetrics[];
  audioClient: any;
  validator: any;
}

export class AutonomousVoiceTest extends EventEmitter {
  private config: TestConfig;
  private voiceServer: VoicePipelineServer;
  private audioGenerator: RealtimeAudioGenerator;
  private validators: {
    latency: LatencyValidator;
    bargeIn: BargeInValidator;
    privacy: PrivacyValidator;
  };
  
  private testSessions: Map<string, TestSession> = new Map();
  private isRunning: boolean = false;
  private testStartTime: number = 0;
  private testResults: any[] = [];

  constructor(config: Partial<TestConfig> = {}) {
    super();
    
    this.config = { ...DEFAULT_TEST_CONFIG, ...config };
    
    // Initialize voice server for testing
    this.voiceServer = new VoicePipelineServer(8002); // Use different port for testing
    
    // Initialize audio generator
    this.audioGenerator = new RealtimeAudioGenerator({
      sample_rate: 16000,
      chunk_size_ms: 20,
      use_synthetic_voice: this.config.audio_sources.use_synthetic_speech,
      use_recorded_samples: this.config.audio_sources.use_recorded_samples
    });

    // Initialize validators
    this.validators = {
      latency: new LatencyValidator(this.config.validation_targets),
      bargeIn: new BargeInValidator({ max_cut_ms: this.config.validation_targets.max_barge_in_cut_ms }),
      privacy: new PrivacyValidator({ strict_mode: true })
    };

    console.log('🤖 Autonomous Voice Test System initialized');
  }

  public async runFullTestSuite(): Promise<TestResults> {
    console.log('🚀 Starting Autonomous Voice Pipeline Test Suite');
    console.log(`⏱️ Duration: ${this.config.duration_minutes} minutes`);
    console.log(`🎭 Scenarios: ${this.config.test_scenarios.join(', ')}`);
    console.log(`👥 Concurrent sessions: ${this.config.concurrent_sessions}`);
    
    this.isRunning = true;
    this.testStartTime = Date.now();
    
    try {
      // 1. Initialize all test sessions
      await this.initializeTestSessions();
      
      // 2. Run concurrent testing scenarios
      const testPromises = Array.from(this.testSessions.values()).map(session => 
        this.runTestSession(session)
      );
      
      // 3. Wait for all tests to complete or timeout
      await Promise.race([
        Promise.all(testPromises),
        this.createTestTimeout()
      ]);
      
      // 4. Collect and validate results
      const results = await this.collectTestResults();
      
      // 5. Cleanup if requested
      if (this.config.cleanup_after_test) {
        await this.cleanup();
      }
      
      console.log('✅ Autonomous test suite completed');
      this.emit('test_complete', results);
      
      return results;
      
    } catch (error) {
      console.error('❌ Test suite failed:', error);
      this.emit('test_error', error);
      throw error;
    } finally {
      this.isRunning = false;
    }
  }

  private async initializeTestSessions(): Promise<void> {
    console.log('🔧 Initializing test sessions...');
    
    for (let i = 0; i < this.config.concurrent_sessions; i++) {
      for (const scenario of this.config.test_scenarios) {
        const sessionId = `test-${scenario}-${i}-${Date.now()}`;
        
        const session: TestSession = {
          id: sessionId,
          scenario,
          startTime: Date.now(),
          metrics: [],
          audioClient: null,
          validator: null
        };
        
        // Create audio client for this session
        session.audioClient = await this.audioGenerator.createTestClient(sessionId, scenario);
        
        // Assign validator based on scenario
        session.validator = this.getValidatorForScenario(scenario);
        
        this.testSessions.set(sessionId, session);
        console.log(`📝 Created test session: ${sessionId} (${scenario})`);
      }
    }
  }

  private async runTestSession(session: TestSession): Promise<void> {
    console.log(`🎬 Starting test session: ${session.id} (${session.scenario})`);
    
    try {
      const testDurationMs = this.config.duration_minutes * 60 * 1000;
      const endTime = session.startTime + testDurationMs;
      
      while (Date.now() < endTime && this.isRunning) {
        // Generate realistic test scenario
        await this.executeScenario(session);
        
        // Small pause between interactions
        await this.sleep(Math.random() * 2000 + 1000); // 1-3 second intervals
      }
      
      session.endTime = Date.now();
      console.log(`✅ Test session completed: ${session.id}`);
      
    } catch (error) {
      console.error(`❌ Test session failed: ${session.id}`, error);
      session.endTime = Date.now();
    }
  }

  private async executeScenario(session: TestSession): Promise<void> {
    switch (session.scenario) {
      case 'short_queries':
        await this.runShortQueryScenario(session);
        break;
        
      case 'interruptions':
        await this.runInterruptionScenario(session);
        break;
        
      case 'pii_filtering':
        await this.runPIIFilteringScenario(session);
        break;
        
      case 'tool_requests':
        await this.runToolRequestScenario(session);
        break;
        
      default:
        console.warn(`⚠️ Unknown scenario: ${session.scenario}`);
    }
  }

  private async runShortQueryScenario(session: TestSession): Promise<void> {
    const queries = [
      "Hej Alice, vad är klockan?",
      "Hur är vädret idag?", 
      "Spela musik",
      "Vad heter du?",
      "Tack så mycket",
      "Kan du hjälpa mig?",
      "Bra, tack",
      "Nej tack"
    ];
    
    const query = queries[Math.floor(Math.random() * queries.length)];
    const metrics = await this.sendAudioQuery(session, query);
    
    // Validate latency targets for short queries
    this.validators.latency.validate(metrics);
    session.metrics.push(metrics);
  }

  private async runInterruptionScenario(session: TestSession): Promise<void> {
    // Start a longer response
    const longQuery = "Alice, kan du förklara i detalj hur artificiell intelligens fungerar och vad det innebär för framtiden?";
    
    // Send query and wait for TTS to start
    const queryPromise = this.sendAudioQuery(session, longQuery);
    await this.sleep(800); // Wait for TTS to start
    
    // Interrupt with barge-in
    const interruption = "Stopp, tack!";
    const interruptionMetrics = await this.sendBargeInInterruption(session, interruption);
    
    // Validate barge-in timing
    this.validators.bargeIn.validate(interruptionMetrics);
    
    const originalMetrics = await queryPromise;
    session.metrics.push(originalMetrics, interruptionMetrics);
  }

  private async runPIIFilteringScenario(session: TestSession): Promise<void> {
    const piiQueries = [
      "Min epost är test@example.com, kan du komma ihåg det?",
      "Mitt telefonnummer är 070-123-4567",
      "Jag bor på Storgatan 123, Stockholm",
      "Mitt personnummer är 901201-1234",
      "Ring John Andersson på 08-123456"
    ];
    
    const query = piiQueries[Math.floor(Math.random() * piiQueries.length)];
    const metrics = await this.sendAudioQuery(session, query);
    
    // Validate that no PII was leaked
    const privacyResult = this.validators.privacy.validate(metrics);
    if (!privacyResult.passed) {
      console.error(`🚨 PII leak detected in session ${session.id}:`, privacyResult.violations);
      metrics.privacy_leak_attempts = (metrics.privacy_leak_attempts || 0) + 1;
    }
    
    session.metrics.push(metrics);
  }

  private async runToolRequestScenario(session: TestSession): Promise<void> {
    const toolQueries = [
      "Skicka ett mejl till teamet",
      "Vad har jag för möten imorgon?",
      "Spela min favorit-playlist",
      "Sätt en timer på 5 minuter",
      "Tända lamporna i vardagsrummet"
    ];
    
    const query = toolQueries[Math.floor(Math.random() * toolQueries.length)];
    const metrics = await this.sendAudioQuery(session, query);
    
    // Tool requests should use appropriate routing
    if (metrics.route !== 'local_reason' && metrics.route !== 'cloud_complex') {
      console.warn(`⚠️ Tool request routed to ${metrics.route} instead of reasoning path`);
    }
    
    session.metrics.push(metrics);
  }

  private async sendAudioQuery(session: TestSession, text: string): Promise<VoiceMetrics> {
    const startTime = Date.now();
    
    // Generate synthetic audio for the text
    const audioData = await this.audioGenerator.generateSpeech(text);
    
    // Send to voice pipeline and measure performance
    const metrics = await session.audioClient.sendAudioAndMeasure(audioData);
    
    metrics.sessionId = session.id;
    metrics.timestamp = startTime;
    
    return metrics;
  }

  private async sendBargeInInterruption(session: TestSession, text: string): Promise<VoiceMetrics> {
    const startTime = Date.now();
    
    // Generate interruption audio
    const audioData = await this.audioGenerator.generateSpeech(text);
    
    // Send barge-in signal followed by new audio
    const metrics = await session.audioClient.sendBargeInAndMeasure(audioData);
    
    metrics.sessionId = session.id;
    metrics.timestamp = startTime;
    
    return metrics;
  }

  private getValidatorForScenario(scenario: string): any {
    switch (scenario) {
      case 'short_queries':
        return this.validators.latency;
      case 'interruptions':
        return this.validators.bargeIn;
      case 'pii_filtering':
        return this.validators.privacy;
      case 'tool_requests':
        return this.validators.latency; // Tools still need to be fast
      default:
        return this.validators.latency;
    }
  }

  private async collectTestResults(): Promise<TestResults> {
    console.log('📊 Collecting test results...');
    
    const allMetrics: VoiceMetrics[] = [];
    for (const session of this.testSessions.values()) {
      allMetrics.push(...session.metrics);
    }
    
    // Calculate overall performance statistics
    const latencyStats = this.calculateLatencyStats(allMetrics);
    const routeDistribution = this.calculateRouteDistribution(allMetrics);
    const errorRate = this.calculateErrorRate(allMetrics);
    const sloCompliance = this.checkSLOCompliance(allMetrics);
    
    const results: TestResults = {
      summary: {
        total_sessions: this.testSessions.size,
        total_interactions: allMetrics.length,
        test_duration_minutes: (Date.now() - this.testStartTime) / (1000 * 60),
        overall_success_rate: 1 - errorRate,
        slo_compliance: sloCompliance
      },
      performance: latencyStats,
      routing: routeDistribution,
      scenarios: this.getScenarioResults(),
      raw_metrics: allMetrics,
      timestamp: Date.now()
    };
    
    // Save results to file
    await this.saveTestResults(results);
    
    return results;
  }

  private calculateLatencyStats(metrics: VoiceMetrics[]): any {
    const latencies = {
      first_partial: metrics.map(m => m.first_partial_ms).filter(Boolean),
      ttft: metrics.map(m => m.ttft_ms).filter(Boolean),
      tts_first_chunk: metrics.map(m => m.tts_first_chunk_ms).filter(Boolean),
      total: metrics.map(m => m.total_latency_ms).filter(Boolean),
      barge_in_cut: metrics.map(m => m.barge_in_cut_ms).filter(Boolean)
    };
    
    const stats: any = {};
    
    for (const [key, values] of Object.entries(latencies)) {
      if (values.length > 0) {
        const sorted = [...values].sort((a, b) => a - b);
        stats[key] = {
          avg: values.reduce((sum, val) => sum + val, 0) / values.length,
          p50: this.percentile(sorted, 50),
          p95: this.percentile(sorted, 95),
          p99: this.percentile(sorted, 99),
          min: Math.min(...values),
          max: Math.max(...values),
          count: values.length
        };
      }
    }
    
    return stats;
  }

  private calculateRouteDistribution(metrics: VoiceMetrics[]): Record<string, number> {
    const distribution: Record<string, number> = {};
    for (const metric of metrics) {
      const route = metric.route || 'unknown';
      distribution[route] = (distribution[route] || 0) + 1;
    }
    return distribution;
  }

  private calculateErrorRate(metrics: VoiceMetrics[]): number {
    const errors = metrics.filter(m => 
      !m.total_latency_ms || 
      m.total_latency_ms > this.config.validation_targets.max_total_latency_ms ||
      (m.privacy_leak_attempts && m.privacy_leak_attempts > 0)
    );
    
    return metrics.length > 0 ? errors.length / metrics.length : 0;
  }

  private checkSLOCompliance(metrics: VoiceMetrics[]): any {
    const targets = this.config.validation_targets;
    const compliance: any = {};
    
    // Check each SLO target
    const totalLatencies = metrics.map(m => m.total_latency_ms).filter(Boolean);
    compliance.total_latency = totalLatencies.length > 0 ? 
      (totalLatencies.filter(lat => lat <= targets.max_total_latency_ms).length / totalLatencies.length) : 0;
      
    // Add other SLO checks...
    
    return compliance;
  }

  private getScenarioResults(): any {
    const scenarioResults: any = {};
    
    for (const [sessionId, session] of this.testSessions) {
      if (!scenarioResults[session.scenario]) {
        scenarioResults[session.scenario] = {
          sessions: 0,
          total_interactions: 0,
          avg_latency: 0,
          success_rate: 0
        };
      }
      
      const result = scenarioResults[session.scenario];
      result.sessions++;
      result.total_interactions += session.metrics.length;
      
      const latencies = session.metrics.map(m => m.total_latency_ms).filter(Boolean);
      if (latencies.length > 0) {
        result.avg_latency = latencies.reduce((sum, lat) => sum + lat, 0) / latencies.length;
      }
    }
    
    return scenarioResults;
  }

  private percentile(sortedArray: number[], p: number): number {
    const index = (p / 100) * (sortedArray.length - 1);
    const lower = Math.floor(index);
    const upper = Math.ceil(index);
    
    if (lower === upper) return sortedArray[lower];
    
    const weight = index - lower;
    return sortedArray[lower] * (1 - weight) + sortedArray[upper] * weight;
  }

  private async saveTestResults(results: TestResults): Promise<void> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `voice-test-results-${timestamp}.json`;
    const filepath = `core/talk/tests/results/${filename}`;
    
    // Ensure results directory exists
    await fs.promises.mkdir('core/talk/tests/results', { recursive: true });
    
    await fs.promises.writeFile(filepath, JSON.stringify(results, null, 2));
    console.log(`💾 Test results saved to: ${filepath}`);
  }

  private createTestTimeout(): Promise<never> {
    const timeoutMs = (this.config.duration_minutes + 1) * 60 * 1000; // Extra minute for cleanup
    
    return new Promise((_, reject) => {
      setTimeout(() => {
        reject(new Error(`Test timeout after ${this.config.duration_minutes + 1} minutes`));
      }, timeoutMs);
    });
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  public async cleanup(): Promise<void> {
    console.log('🧹 Cleaning up autonomous test system...');
    
    // Stop all test sessions
    this.isRunning = false;
    
    // Cleanup audio clients
    for (const session of this.testSessions.values()) {
      if (session.audioClient && session.audioClient.cleanup) {
        await session.audioClient.cleanup();
      }
    }
    
    // Cleanup audio generator
    await this.audioGenerator.cleanup();
    
    // Cleanup voice server
    this.voiceServer.close();
    
    // Clear test data if requested
    if (this.config.cleanup_after_test) {
      // Remove temporary test files
      await this.cleanupTestFiles();
    }
    
    console.log('✅ Autonomous test cleanup completed');
  }

  private async cleanupTestFiles(): Promise<void> {
    const testDirs = [
      'core/talk/tests/fixtures/audio/generated',
      'core/talk/tests/results/temp'
    ];
    
    for (const dir of testDirs) {
      try {
        await fs.promises.rm(dir, { recursive: true, force: true });
        console.log(`🗑️ Cleaned up: ${dir}`);
      } catch (error) {
        // Ignore errors for non-existent directories
      }
    }
  }
}

interface TestResults {
  summary: {
    total_sessions: number;
    total_interactions: number;
    test_duration_minutes: number;
    overall_success_rate: number;
    slo_compliance: any;
  };
  performance: any;
  routing: Record<string, number>;
  scenarios: any;
  raw_metrics: VoiceMetrics[];
  timestamp: number;
}

// Export for easy CLI usage
export async function runAutonomousTests(config?: Partial<TestConfig>): Promise<TestResults> {
  const testSystem = new AutonomousVoiceTest(config);
  
  try {
    return await testSystem.runFullTestSuite();
  } finally {
    await testSystem.cleanup();
  }
}

// CLI entry point
if (require.main === module) {
  const config = process.env.NODE_ENV === 'production' ? {
    duration_minutes: 30,
    concurrent_sessions: 5,
    cleanup_after_test: true
  } : {
    duration_minutes: 5,
    concurrent_sessions: 2,
    cleanup_after_test: true
  };
  
  runAutonomousTests(config)
    .then(results => {
      console.log('🎉 Autonomous tests completed successfully!');
      console.log(`📊 Overall success rate: ${(results.summary.overall_success_rate * 100).toFixed(1)}%`);
      process.exit(0);
    })
    .catch(error => {
      console.error('❌ Autonomous tests failed:', error);
      process.exit(1);
    });
}