/**
 * Latency Validator for Voice Pipeline Testing
 * Validates SLO targets and performance metrics
 */

import { VoiceMetrics } from '../../types/events';
import { TestLogger } from '../utils/test_logger';

interface LatencyTargets {
  max_total_latency_ms: number;
  max_first_partial_ms: number;
  max_ttft_ms: number;
  max_tts_first_chunk_ms: number;
  max_barge_in_cut_ms: number;
  min_success_rate: number;
}

interface ValidationResult {
  passed: boolean;
  failures: string[];
  warnings: string[];
  metrics: {
    total_latency_ms?: number;
    first_partial_ms?: number;
    ttft_ms?: number;
    tts_first_chunk_ms?: number;
    barge_in_cut_ms?: number;
  };
  score: number; // 0-100 performance score
}

export class LatencyValidator {
  private targets: LatencyTargets;
  private validationHistory: ValidationResult[] = [];
  private logger?: TestLogger;

  constructor(targets: LatencyTargets) {
    this.targets = targets;
  }

  public setLogger(logger: TestLogger): void {
    this.logger = logger;
  }

  public validate(metrics: VoiceMetrics): ValidationResult {
    const result: ValidationResult = {
      passed: true,
      failures: [],
      warnings: [],
      metrics: {
        total_latency_ms: metrics.total_latency_ms,
        first_partial_ms: metrics.first_partial_ms,
        ttft_ms: metrics.ttft_ms,
        tts_first_chunk_ms: metrics.tts_first_chunk_ms,
        barge_in_cut_ms: metrics.barge_in_cut_ms
      },
      score: 100
    };

    // Validate total latency (critical SLO)
    if (metrics.total_latency_ms) {
      if (metrics.total_latency_ms > this.targets.max_total_latency_ms) {
        result.failures.push(`Total latency ${metrics.total_latency_ms}ms exceeds target ${this.targets.max_total_latency_ms}ms`);
        result.passed = false;
        result.score -= 30; // Heavy penalty for total latency failure
      } else if (metrics.total_latency_ms > this.targets.max_total_latency_ms * 0.8) {
        result.warnings.push(`Total latency ${metrics.total_latency_ms}ms approaching target (${this.targets.max_total_latency_ms}ms)`);
        result.score -= 10;
      }
    } else {
      result.failures.push('Total latency measurement missing');
      result.passed = false;
      result.score -= 50;
    }

    // Validate first partial timing
    if (metrics.first_partial_ms) {
      if (metrics.first_partial_ms > this.targets.max_first_partial_ms) {
        result.failures.push(`First partial ${metrics.first_partial_ms}ms exceeds target ${this.targets.max_first_partial_ms}ms`);
        result.passed = false;
        result.score -= 20;
      } else if (metrics.first_partial_ms > this.targets.max_first_partial_ms * 0.9) {
        result.warnings.push(`First partial ${metrics.first_partial_ms}ms approaching target`);
        result.score -= 5;
      }
    } else {
      result.warnings.push('First partial timing missing');
      result.score -= 10;
    }

    // Validate TTFT (Time To First Token)
    if (metrics.ttft_ms) {
      if (metrics.ttft_ms > this.targets.max_ttft_ms) {
        result.failures.push(`TTFT ${metrics.ttft_ms}ms exceeds target ${this.targets.max_ttft_ms}ms`);
        result.passed = false;
        result.score -= 25;
      } else if (metrics.ttft_ms > this.targets.max_ttft_ms * 0.8) {
        result.warnings.push(`TTFT ${metrics.ttft_ms}ms approaching target`);
        result.score -= 8;
      }
    } else {
      result.warnings.push('TTFT timing missing');
      result.score -= 15;
    }

    // Validate TTS first chunk timing
    if (metrics.tts_first_chunk_ms) {
      if (metrics.tts_first_chunk_ms > this.targets.max_tts_first_chunk_ms) {
        result.failures.push(`TTS first chunk ${metrics.tts_first_chunk_ms}ms exceeds target ${this.targets.max_tts_first_chunk_ms}ms`);
        result.passed = false;
        result.score -= 20;
      } else if (metrics.tts_first_chunk_ms > this.targets.max_tts_first_chunk_ms * 0.8) {
        result.warnings.push(`TTS first chunk ${metrics.tts_first_chunk_ms}ms approaching target`);
        result.score -= 5;
      }
    } else {
      result.warnings.push('TTS first chunk timing missing');
      result.score -= 10;
    }

    // Validate barge-in cut timing (if applicable)
    if (metrics.barge_in_cut_ms !== undefined) {
      if (metrics.barge_in_cut_ms > this.targets.max_barge_in_cut_ms) {
        result.failures.push(`Barge-in cut ${metrics.barge_in_cut_ms}ms exceeds target ${this.targets.max_barge_in_cut_ms}ms`);
        result.passed = false;
        result.score -= 15;
      }
    }

    // Ensure score doesn't go below 0
    result.score = Math.max(0, result.score);

    // Store for historical analysis
    this.validationHistory.push(result);

    // Log results
    if (!result.passed) {
      console.error(`❌ Latency validation failed for ${metrics.sessionId}:`, result.failures);
      
      // Log individual latency violations
      if (this.logger) {
        result.failures.forEach(failure => {
          const match = failure.match(/(\w+)\s+(\d+)ms exceeds target (\d+)ms/);
          if (match) {
            this.logger!.logLatencyViolation(metrics.sessionId, match[1], parseInt(match[2]), parseInt(match[3]));
          }
        });
      }
    } else if (result.warnings.length > 0) {
      console.warn(`⚠️ Latency warnings for ${metrics.sessionId}:`, result.warnings);
    } else {
      console.log(`✅ Latency validation passed for ${metrics.sessionId} (score: ${result.score})`);
    }

    // Log validation result
    if (this.logger) {
      this.logger.logValidationResult(metrics.sessionId, 'latency', result);
    }

    return result;
  }

  public validateBatch(metricsList: VoiceMetrics[]): BatchValidationResult {
    const results = metricsList.map(metrics => this.validate(metrics));
    
    const passed = results.filter(r => r.passed).length;
    const failed = results.filter(r => !r.passed).length;
    const successRate = metricsList.length > 0 ? passed / metricsList.length : 0;
    
    const avgScore = results.length > 0 ? 
      results.reduce((sum, r) => sum + r.score, 0) / results.length : 0;

    // Calculate latency statistics
    const latencyStats = this.calculateLatencyStats(metricsList);

    const batchResult: BatchValidationResult = {
      overall_passed: successRate >= this.targets.min_success_rate,
      success_rate: successRate,
      total_tested: metricsList.length,
      passed: passed,
      failed: failed,
      average_score: avgScore,
      latency_stats: latencyStats,
      slo_compliance: this.checkSLOCompliance(metricsList),
      individual_results: results
    };

    console.log(`📊 Batch validation: ${passed}/${metricsList.length} passed (${(successRate * 100).toFixed(1)}%)`);
    console.log(`📈 Average latency: ${latencyStats.total_latency.avg.toFixed(1)}ms (p95: ${latencyStats.total_latency.p95.toFixed(1)}ms)`);

    return batchResult;
  }

  private calculateLatencyStats(metricsList: VoiceMetrics[]): LatencyStats {
    const stats: LatencyStats = {
      total_latency: this.calculateMetricStats(metricsList.map(m => m.total_latency_ms).filter(Boolean)),
      first_partial: this.calculateMetricStats(metricsList.map(m => m.first_partial_ms).filter(Boolean)),
      ttft: this.calculateMetricStats(metricsList.map(m => m.ttft_ms).filter(Boolean)),
      tts_first_chunk: this.calculateMetricStats(metricsList.map(m => m.tts_first_chunk_ms).filter(Boolean)),
      barge_in_cut: this.calculateMetricStats(metricsList.map(m => m.barge_in_cut_ms).filter(Boolean))
    };

    return stats;
  }

  private calculateMetricStats(values: number[]): MetricStats {
    if (values.length === 0) {
      return { avg: 0, p50: 0, p95: 0, p99: 0, min: 0, max: 0, count: 0 };
    }

    const sorted = [...values].sort((a, b) => a - b);
    return {
      avg: values.reduce((sum, val) => sum + val, 0) / values.length,
      p50: this.percentile(sorted, 50),
      p95: this.percentile(sorted, 95),
      p99: this.percentile(sorted, 99),
      min: sorted[0],
      max: sorted[sorted.length - 1],
      count: values.length
    };
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

  private checkSLOCompliance(metricsList: VoiceMetrics[]): SLOCompliance {
    const totalLatencies = metricsList.map(m => m.total_latency_ms).filter(Boolean);
    const firstPartials = metricsList.map(m => m.first_partial_ms).filter(Boolean);
    const ttfts = metricsList.map(m => m.ttft_ms).filter(Boolean);
    const ttsFirstChunks = metricsList.map(m => m.tts_first_chunk_ms).filter(Boolean);
    const bargeInCuts = metricsList.map(m => m.barge_in_cut_ms).filter(Boolean);

    return {
      total_latency: {
        target: this.targets.max_total_latency_ms,
        compliance_rate: totalLatencies.length > 0 ? 
          totalLatencies.filter(lat => lat <= this.targets.max_total_latency_ms).length / totalLatencies.length : 0,
        p95_actual: totalLatencies.length > 0 ? this.percentile([...totalLatencies].sort((a, b) => a - b), 95) : 0
      },
      first_partial: {
        target: this.targets.max_first_partial_ms,
        compliance_rate: firstPartials.length > 0 ? 
          firstPartials.filter(lat => lat <= this.targets.max_first_partial_ms).length / firstPartials.length : 0,
        p95_actual: firstPartials.length > 0 ? this.percentile([...firstPartials].sort((a, b) => a - b), 95) : 0
      },
      ttft: {
        target: this.targets.max_ttft_ms,
        compliance_rate: ttfts.length > 0 ? 
          ttfts.filter(lat => lat <= this.targets.max_ttft_ms).length / ttfts.length : 0,
        p95_actual: ttfts.length > 0 ? this.percentile([...ttfts].sort((a, b) => a - b), 95) : 0
      },
      tts_first_chunk: {
        target: this.targets.max_tts_first_chunk_ms,
        compliance_rate: ttsFirstChunks.length > 0 ? 
          ttsFirstChunks.filter(lat => lat <= this.targets.max_tts_first_chunk_ms).length / ttsFirstChunks.length : 0,
        p95_actual: ttsFirstChunks.length > 0 ? this.percentile([...ttsFirstChunks].sort((a, b) => a - b), 95) : 0
      },
      barge_in_cut: {
        target: this.targets.max_barge_in_cut_ms,
        compliance_rate: bargeInCuts.length > 0 ? 
          bargeInCuts.filter(lat => lat <= this.targets.max_barge_in_cut_ms).length / bargeInCuts.length : 0,
        p95_actual: bargeInCuts.length > 0 ? this.percentile([...bargeInCuts].sort((a, b) => a - b), 95) : 0
      }
    };
  }

  public getValidationHistory(): ValidationResult[] {
    return [...this.validationHistory];
  }

  public getSuccessRate(): number {
    if (this.validationHistory.length === 0) return 0;
    
    const passed = this.validationHistory.filter(r => r.passed).length;
    return passed / this.validationHistory.length;
  }

  public reset(): void {
    this.validationHistory = [];
    console.log('🔄 Latency validator reset');
  }
}

interface MetricStats {
  avg: number;
  p50: number;
  p95: number;
  p99: number;
  min: number;
  max: number;
  count: number;
}

interface LatencyStats {
  total_latency: MetricStats;
  first_partial: MetricStats;
  ttft: MetricStats;
  tts_first_chunk: MetricStats;
  barge_in_cut: MetricStats;
}

interface SLOTarget {
  target: number;
  compliance_rate: number;
  p95_actual: number;
}

interface SLOCompliance {
  total_latency: SLOTarget;
  first_partial: SLOTarget;
  ttft: SLOTarget;
  tts_first_chunk: SLOTarget;
  barge_in_cut: SLOTarget;
}

interface BatchValidationResult {
  overall_passed: boolean;
  success_rate: number;
  total_tested: number;
  passed: number;
  failed: number;
  average_score: number;
  latency_stats: LatencyStats;
  slo_compliance: SLOCompliance;
  individual_results: ValidationResult[];
}