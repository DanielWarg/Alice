/**
 * Barge-in Validator for Voice Pipeline Testing
 * Validates interruption handling and response times
 */

import { VoiceMetrics } from '../../types/events';
import { TestLogger } from '../utils/test_logger';

interface BargeInValidationConfig {
  max_interrupt_detection_ms: number;
  max_playback_stop_ms: number;
  max_new_response_start_ms: number;
  require_smooth_fadeout: boolean;
  validate_audio_gaps: boolean;
}

const DEFAULT_BARGE_IN_CONFIG: BargeInValidationConfig = {
  max_interrupt_detection_ms: 50,  // Detect interruption within 50ms
  max_playback_stop_ms: 100,       // Stop current playback within 100ms
  max_new_response_start_ms: 200,  // Start new response within 200ms total
  require_smooth_fadeout: true,    // Require audio fadeout, not abrupt cut
  validate_audio_gaps: true        // Check for audio gaps/artifacts
};

interface BargeInEvent {
  type: 'user_speech_start' | 'playback_stopped' | 'new_response_start';
  timestamp: number;
  audioLevel?: number;
  fadeoutApplied?: boolean;
  gapDetected?: boolean;
}

interface BargeInValidationResult {
  passed: boolean;
  failures: string[];
  warnings: string[];
  timings: {
    detection_latency_ms?: number;
    playback_stop_ms?: number;
    new_response_start_ms?: number;
    total_barge_in_ms?: number;
  };
  audio_quality: {
    smooth_fadeout: boolean;
    gaps_detected: boolean;
    abrupt_cuts: number;
  };
  score: number; // 0-100 barge-in performance score
}

export class BargeInValidator {
  private config: BargeInValidationConfig;
  private validationHistory: BargeInValidationResult[] = [];
  private logger?: TestLogger;

  constructor(config: Partial<BargeInValidationConfig> = {}) {
    this.config = { ...DEFAULT_BARGE_IN_CONFIG, ...config };
  }

  public setLogger(logger: TestLogger): void {
    this.logger = logger;
  }

  public validate(metrics: VoiceMetrics, bargeInEvents: BargeInEvent[]): BargeInValidationResult {
    const result: BargeInValidationResult = {
      passed: true,
      failures: [],
      warnings: [],
      timings: {
        total_barge_in_ms: metrics.barge_in_cut_ms
      },
      audio_quality: {
        smooth_fadeout: false,
        gaps_detected: false,
        abrupt_cuts: 0
      },
      score: 100
    };

    // If no barge-in occurred, this test is N/A
    if (!metrics.barge_in_cut_ms && bargeInEvents.length === 0) {
      result.warnings.push('No barge-in events to validate');
      return result;
    }

    // Validate barge-in event timing sequence
    const timingValidation = this.validateBargeInTiming(bargeInEvents);
    result.timings = { ...result.timings, ...timingValidation.timings };
    
    if (!timingValidation.passed) {
      result.failures.push(...timingValidation.failures);
      result.passed = false;
      result.score -= 40; // Heavy penalty for timing failures
    }

    // Validate overall barge-in cut timing from metrics
    if (metrics.barge_in_cut_ms) {
      if (metrics.barge_in_cut_ms > this.config.max_new_response_start_ms) {
        result.failures.push(`Total barge-in time ${metrics.barge_in_cut_ms}ms exceeds target ${this.config.max_new_response_start_ms}ms`);
        result.passed = false;
        result.score -= 30;
      } else if (metrics.barge_in_cut_ms > this.config.max_new_response_start_ms * 0.8) {
        result.warnings.push(`Total barge-in time ${metrics.barge_in_cut_ms}ms approaching target`);
        result.score -= 10;
      }
    }

    // Validate audio quality during barge-in
    const audioValidation = this.validateAudioQuality(bargeInEvents);
    result.audio_quality = audioValidation;
    
    if (this.config.require_smooth_fadeout && !audioValidation.smooth_fadeout) {
      result.failures.push('Smooth fadeout not applied during barge-in');
      result.passed = false;
      result.score -= 20;
    }

    if (this.config.validate_audio_gaps && audioValidation.gaps_detected) {
      result.warnings.push('Audio gaps detected during barge-in transition');
      result.score -= 15;
    }

    if (audioValidation.abrupt_cuts > 0) {
      result.failures.push(`${audioValidation.abrupt_cuts} abrupt audio cuts detected`);
      result.passed = false;
      result.score -= audioValidation.abrupt_cuts * 10;
    }

    // Ensure score doesn't go below 0
    result.score = Math.max(0, result.score);

    // Store validation result
    this.validationHistory.push(result);

    // Log results
    if (!result.passed) {
      console.error(`❌ Barge-in validation failed for ${metrics.sessionId}:`, result.failures);
      
      // Log individual barge-in failures
      if (this.logger) {
        result.failures.forEach(failure => {
          this.logger!.logBargeInFailure(metrics.sessionId, failure, result.timings);
        });
      }
    } else if (result.warnings.length > 0) {
      console.warn(`⚠️ Barge-in warnings for ${metrics.sessionId}:`, result.warnings);
    } else {
      console.log(`✅ Barge-in validation passed for ${metrics.sessionId} (score: ${result.score})`);
    }

    // Log validation result
    if (this.logger) {
      this.logger.logValidationResult(metrics.sessionId, 'barge_in', result);
    }

    return result;
  }

  private validateBargeInTiming(events: BargeInEvent[]): { passed: boolean; failures: string[]; timings: any } {
    const timings: any = {};
    const failures: string[] = [];

    if (events.length === 0) {
      failures.push('No barge-in events provided for timing validation');
      return { passed: false, failures, timings };
    }

    // Find key events
    const userSpeechStart = events.find(e => e.type === 'user_speech_start');
    const playbackStopped = events.find(e => e.type === 'playback_stopped');
    const newResponseStart = events.find(e => e.type === 'new_response_start');

    if (!userSpeechStart) {
      failures.push('User speech start event missing');
      return { passed: false, failures, timings };
    }

    // Validate detection latency
    if (playbackStopped) {
      timings.detection_latency_ms = playbackStopped.timestamp - userSpeechStart.timestamp;
      
      if (timings.detection_latency_ms > this.config.max_interrupt_detection_ms) {
        failures.push(`Interrupt detection took ${timings.detection_latency_ms}ms, exceeds ${this.config.max_interrupt_detection_ms}ms target`);
      }
    } else {
      failures.push('Playback stopped event missing');
    }

    // Validate playback stop timing
    if (playbackStopped) {
      timings.playback_stop_ms = playbackStopped.timestamp - userSpeechStart.timestamp;
      
      if (timings.playback_stop_ms > this.config.max_playback_stop_ms) {
        failures.push(`Playback stop took ${timings.playback_stop_ms}ms, exceeds ${this.config.max_playback_stop_ms}ms target`);
      }
    }

    // Validate new response start timing
    if (newResponseStart) {
      timings.new_response_start_ms = newResponseStart.timestamp - userSpeechStart.timestamp;
      
      if (timings.new_response_start_ms > this.config.max_new_response_start_ms) {
        failures.push(`New response start took ${timings.new_response_start_ms}ms, exceeds ${this.config.max_new_response_start_ms}ms target`);
      }
    } else {
      failures.push('New response start event missing');
    }

    return {
      passed: failures.length === 0,
      failures,
      timings
    };
  }

  private validateAudioQuality(events: BargeInEvent[]): { smooth_fadeout: boolean; gaps_detected: boolean; abrupt_cuts: number } {
    let smooth_fadeout = false;
    let gaps_detected = false;
    let abrupt_cuts = 0;

    for (const event of events) {
      if (event.type === 'playback_stopped') {
        // Check if fadeout was applied
        if (event.fadeoutApplied === true) {
          smooth_fadeout = true;
        } else if (event.fadeoutApplied === false) {
          abrupt_cuts++;
        }
      }

      // Check for audio gaps
      if (event.gapDetected === true) {
        gaps_detected = true;
      }
    }

    return {
      smooth_fadeout,
      gaps_detected,
      abrupt_cuts
    };
  }

  public validateBatch(metricsList: VoiceMetrics[], eventsList: BargeInEvent[][] = []): BatchBargeInResult {
    const results = metricsList.map((metrics, index) => 
      this.validate(metrics, eventsList[index] || [])
    );

    const bargeInResults = results.filter(r => r.timings.total_barge_in_ms !== undefined);
    
    if (bargeInResults.length === 0) {
      return {
        overall_passed: true,
        barge_in_tested: 0,
        success_rate: 0,
        average_score: 0,
        timing_stats: {
          avg_detection_ms: 0,
          avg_playback_stop_ms: 0,
          avg_total_barge_in_ms: 0,
          p95_total_barge_in_ms: 0
        },
        audio_quality_stats: {
          smooth_fadeout_rate: 0,
          gap_detection_rate: 0,
          abrupt_cut_rate: 0
        },
        individual_results: results
      };
    }

    const passed = bargeInResults.filter(r => r.passed).length;
    const successRate = passed / bargeInResults.length;
    const avgScore = bargeInResults.reduce((sum, r) => sum + r.score, 0) / bargeInResults.length;

    // Calculate timing statistics
    const detectionTimes = bargeInResults.map(r => r.timings.detection_latency_ms).filter(Boolean);
    const playbackStopTimes = bargeInResults.map(r => r.timings.playback_stop_ms).filter(Boolean);
    const totalBargeInTimes = bargeInResults.map(r => r.timings.total_barge_in_ms).filter(Boolean);

    const timingStats = {
      avg_detection_ms: this.average(detectionTimes),
      avg_playback_stop_ms: this.average(playbackStopTimes),
      avg_total_barge_in_ms: this.average(totalBargeInTimes),
      p95_total_barge_in_ms: this.percentile(totalBargeInTimes.sort((a, b) => a - b), 95)
    };

    // Calculate audio quality statistics
    const audioQualityStats = {
      smooth_fadeout_rate: bargeInResults.filter(r => r.audio_quality.smooth_fadeout).length / bargeInResults.length,
      gap_detection_rate: bargeInResults.filter(r => r.audio_quality.gaps_detected).length / bargeInResults.length,
      abrupt_cut_rate: bargeInResults.filter(r => r.audio_quality.abrupt_cuts > 0).length / bargeInResults.length
    };

    return {
      overall_passed: successRate >= 0.9, // 90% success rate required
      barge_in_tested: bargeInResults.length,
      success_rate: successRate,
      average_score: avgScore,
      timing_stats: timingStats,
      audio_quality_stats: audioQualityStats,
      individual_results: results
    };
  }

  private average(numbers: number[]): number {
    if (numbers.length === 0) return 0;
    return numbers.reduce((sum, n) => sum + n, 0) / numbers.length;
  }

  private percentile(sortedArray: number[], p: number): number {
    if (sortedArray.length === 0) return 0;
    
    const index = (p / 100) * (sortedArray.length - 1);
    const lower = Math.floor(index);
    const upper = Math.ceil(index);
    
    if (lower === upper) return sortedArray[lower];
    
    const weight = index - lower;
    return sortedArray[lower] * (1 - weight) + sortedArray[upper] * weight;
  }

  public getValidationHistory(): BargeInValidationResult[] {
    return [...this.validationHistory];
  }

  public getSuccessRate(): number {
    if (this.validationHistory.length === 0) return 0;
    
    const bargeInValidations = this.validationHistory.filter(r => r.timings.total_barge_in_ms !== undefined);
    if (bargeInValidations.length === 0) return 0;
    
    const passed = bargeInValidations.filter(r => r.passed).length;
    return passed / bargeInValidations.length;
  }

  public reset(): void {
    this.validationHistory = [];
    console.log('🔄 Barge-in validator reset');
  }
}

interface BatchBargeInResult {
  overall_passed: boolean;
  barge_in_tested: number;
  success_rate: number;
  average_score: number;
  timing_stats: {
    avg_detection_ms: number;
    avg_playback_stop_ms: number;
    avg_total_barge_in_ms: number;
    p95_total_barge_in_ms: number;
  };
  audio_quality_stats: {
    smooth_fadeout_rate: number;
    gap_detection_rate: number;
    abrupt_cut_rate: number;
  };
  individual_results: BargeInValidationResult[];
}