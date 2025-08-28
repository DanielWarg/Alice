/**
 * Voice Metrics Assert API - PASS/FAIL evaluation with thresholds
 */
import { NextRequest, NextResponse } from 'next/server';

interface AssertThresholds {
  asr_partial_latency_ms?: number;
  asr_final_latency_ms?: number;
  llm_latency_ms?: number;
  tts_ttfa_ms?: number;
  e2e_roundtrip_ms?: number;
  min_samples?: number;
  max_error_rate?: number;
}

interface AssertResult {
  pass: boolean;
  timestamp: number;
  thresholds: AssertThresholds;
  results: {
    metric: string;
    p50: number;
    p95: number;
    threshold: number;
    pass: boolean;
    sample_count: number;
  }[];
  overall_stats: {
    total_samples: number;
    error_rate: number;
    test_duration_hours: number;
  };
  failures: string[];
}

const DEFAULT_THRESHOLDS: Required<AssertThresholds> = {
  asr_partial_latency_ms: 500,
  asr_final_latency_ms: 1000,
  llm_latency_ms: 2000,
  tts_ttfa_ms: 500,
  e2e_roundtrip_ms: 1500,
  min_samples: 1,
  max_error_rate: 0.1
};

// Simplified metrics store for testing (in production, use the shared store)
let metricsStore: any[] = [];

function calculatePercentiles(values: number[]): { p50: number; p95: number; p99: number } {
  if (values.length === 0) return { p50: 0, p95: 0, p99: 0 };
  
  const sorted = [...values].sort((a, b) => a - b);
  const len = sorted.length;
  
  return {
    p50: sorted[Math.floor(len * 0.5)] || 0,
    p95: sorted[Math.floor(len * 0.95)] || 0,
    p99: sorted[Math.floor(len * 0.99)] || 0
  };
}

export async function POST(request: NextRequest) {
  try {
    const thresholds: AssertThresholds = {
      ...DEFAULT_THRESHOLDS,
      ...(await request.json())
    };
    
    const now = Date.now();
    const testWindow = 60 * 60 * 1000; // 1 hour
    const windowStart = now - testWindow;
    
    // Filter recent metrics
    const recentMetrics = metricsStore.filter(m => 
      m.timestamp_ms > windowStart
    );
    
    if (recentMetrics.length === 0) {
      return NextResponse.json({
        pass: false,
        timestamp: now,
        thresholds,
        results: [],
        overall_stats: {
          total_samples: 0,
          error_rate: 0,
          test_duration_hours: 1
        },
        failures: ['No metrics found in the last hour']
      } as AssertResult);
    }
    
    // Extract metric arrays
    const metricExtractors = {
      asr_partial_latency_ms: (m: any) => m.asr_partial_latency_ms,
      asr_final_latency_ms: (m: any) => m.asr_final_latency_ms,
      llm_latency_ms: (m: any) => m.llm_latency_ms,
      tts_ttfa_ms: (m: any) => m.tts_ttfa_ms,
      e2e_roundtrip_ms: (m: any) => m.e2e_roundtrip_ms
    };
    
    const results: AssertResult['results'] = [];
    const failures: string[] = [];
    
    // Evaluate each metric
    for (const [metricName, extractor] of Object.entries(metricExtractors)) {
      const threshold = thresholds[metricName as keyof AssertThresholds];
      if (!threshold) continue;
      
      const values = recentMetrics
        .map(extractor)
        .filter(v => v !== undefined && v !== null) as number[];
      
      const percentiles = calculatePercentiles(values);
      const sampleCount = values.length;
      
      // Check minimum samples
      const minSamples = thresholds.min_samples || DEFAULT_THRESHOLDS.min_samples;
      if (sampleCount < minSamples) {
        failures.push(`${metricName}: Insufficient samples (${sampleCount} < ${minSamples})`);
      }
      
      // Check P95 against threshold
      const pass = percentiles.p95 <= threshold && sampleCount >= minSamples;
      if (!pass && sampleCount >= minSamples) {
        failures.push(`${metricName}: P95 ${percentiles.p95}ms exceeds threshold ${threshold}ms`);
      }
      
      results.push({
        metric: metricName,
        p50: Math.round(percentiles.p50),
        p95: Math.round(percentiles.p95),
        threshold,
        pass,
        sample_count: sampleCount
      });
    }
    
    // Calculate overall stats
    const errorCount = recentMetrics.filter(m => m.error_count > 0).length;
    const errorRate = recentMetrics.length > 0 ? errorCount / recentMetrics.length : 0;
    const maxErrorRate = thresholds.max_error_rate || DEFAULT_THRESHOLDS.max_error_rate;
    
    if (errorRate > maxErrorRate) {
      failures.push(`Error rate ${(errorRate * 100).toFixed(1)}% exceeds threshold ${(maxErrorRate * 100).toFixed(1)}%`);
    }
    
    const overallPass = failures.length === 0;
    
    const result: AssertResult = {
      pass: overallPass,
      timestamp: now,
      thresholds,
      results,
      overall_stats: {
        total_samples: recentMetrics.length,
        error_rate: errorRate,
        test_duration_hours: 1
      },
      failures
    };
    
    return NextResponse.json(result);
    
  } catch (error) {
    console.error('Failed to assert metrics:', error);
    return NextResponse.json(
      { 
        pass: false,
        error: 'Failed to assert metrics',
        timestamp: Date.now(),
        failures: ['Internal server error']
      },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    message: 'POST JSON with thresholds to assert metrics',
    example_body: DEFAULT_THRESHOLDS,
    current_metrics_count: metricsStore.length
  });
}