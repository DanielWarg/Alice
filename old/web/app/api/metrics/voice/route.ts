/**
 * Voice Metrics API - Shadow Report Endpoint
 * Collects and returns p50/p95 voice latency metrics
 */
import { NextRequest, NextResponse } from 'next/server';

interface VoiceMetric {
  timestamp_ms: number;
  session_id: string;
  asr_partial_latency_ms?: number;
  asr_final_latency_ms?: number;
  llm_latency_ms?: number;
  tts_ttfa_ms?: number;
  e2e_roundtrip_ms?: number;
  tool_duration_ms?: number;
  tool_call_count?: number;
  tool_error_count?: number;
  provider: string;
}

// In-memory storage for metrics (in production, use Redis or database)
let metricsStore: VoiceMetric[] = [];
const MAX_METRICS = 1000;

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

function getMetricsReport() {
  const now = Date.now();
  const oneHourAgo = now - (60 * 60 * 1000);
  
  // Filter metrics from last hour
  const recentMetrics = metricsStore.filter(m => m.timestamp_ms > oneHourAgo);
  
  if (recentMetrics.length === 0) {
    return {
      timespan_hours: 1,
      total_sessions: 0,
      metrics: {},
      message: 'No metrics collected in the last hour'
    };
  }
  
  // Extract latency arrays
  const asrPartial = recentMetrics
    .map(m => m.asr_partial_latency_ms)
    .filter(v => v !== undefined) as number[];
    
  const asrFinal = recentMetrics
    .map(m => m.asr_final_latency_ms)
    .filter(v => v !== undefined) as number[];
    
  const llm = recentMetrics
    .map(m => m.llm_latency_ms)
    .filter(v => v !== undefined) as number[];
    
  const ttsTtfa = recentMetrics
    .map(m => m.tts_ttfa_ms)
    .filter(v => v !== undefined) as number[];
    
  const e2e = recentMetrics
    .map(m => m.e2e_roundtrip_ms)
    .filter(v => v !== undefined) as number[];
    
  const toolDuration = recentMetrics
    .map(m => m.tool_duration_ms)
    .filter(v => v !== undefined) as number[];
    
  // Tool call statistics
  const totalToolCalls = recentMetrics.reduce((sum, m) => sum + (m.tool_call_count || 0), 0);
  const totalToolErrors = recentMetrics.reduce((sum, m) => sum + (m.tool_error_count || 0), 0);
  const toolErrorRate = totalToolCalls > 0 ? totalToolErrors / totalToolCalls : 0;
  
  return {
    timespan_hours: 1,
    total_sessions: recentMetrics.length,
    metrics: {
      asr_partial_latency: calculatePercentiles(asrPartial),
      asr_final_latency: calculatePercentiles(asrFinal),
      llm_latency: calculatePercentiles(llm),
      tts_ttfa: calculatePercentiles(ttsTtfa),
      e2e_roundtrip: calculatePercentiles(e2e),
      tool_duration: calculatePercentiles(toolDuration)
    },
    sample_counts: {
      asr_partial: asrPartial.length,
      asr_final: asrFinal.length,
      llm: llm.length,
      tts_ttfa: ttsTtfa.length,
      e2e_roundtrip: e2e.length,
      tool_duration: toolDuration.length
    },
    tool_stats: {
      total_calls: totalToolCalls,
      total_errors: totalToolErrors,
      error_rate: Math.round(toolErrorRate * 100) / 100
    },
    providers: [...new Set(recentMetrics.map(m => m.provider))],
    timestamp: now
  };
}

export async function POST(request: NextRequest) {
  try {
    const metric: VoiceMetric = await request.json();
    
    // Validate required fields
    if (!metric.timestamp_ms || !metric.session_id) {
      return NextResponse.json(
        { error: 'Missing required fields: timestamp_ms, session_id' },
        { status: 400 }
      );
    }
    
    // Add to store
    metricsStore.push({
      ...metric,
      provider: metric.provider || 'unknown'
    });
    
    // Keep only recent metrics to prevent memory bloat
    if (metricsStore.length > MAX_METRICS) {
      const oneHourAgo = Date.now() - (60 * 60 * 1000);
      metricsStore = metricsStore
        .filter(m => m.timestamp_ms > oneHourAgo)
        .slice(-MAX_METRICS);
    }
    
    return NextResponse.json({ 
      success: true, 
      stored: true,
      total_metrics: metricsStore.length
    });
    
  } catch (error) {
    console.error('Failed to store voice metric:', error);
    return NextResponse.json(
      { error: 'Failed to store metric' },
      { status: 500 }
    );
  }
}

export async function GET() {
  try {
    const report = getMetricsReport();
    
    // Add compliance flags to the report
    const complianceInfo = {
      consent_required: process.env.NEXT_PUBLIC_VOICE_REQUIRE_CONSENT === 'on',
      banner_shown: process.env.NEXT_PUBLIC_VOICE_SHOW_SYNTHETIC_BADGE !== 'off',
      blocked_tts_count: 0, // Would get from ContentFilter in real implementation
      filter_level: process.env.NEXT_PUBLIC_VOICE_CONTENT_FILTER || 'strict'
    };
    
    return NextResponse.json({
      success: true,
      report: {
        ...report,
        compliance: complianceInfo
      }
    });
    
  } catch (error) {
    console.error('Failed to generate metrics report:', error);
    return NextResponse.json(
      { error: 'Failed to generate report' },
      { status: 500 }
    );
  }
}

// Health check endpoint
export async function HEAD() {
  return new NextResponse(null, { 
    status: 200, 
    headers: {
      'X-Metrics-Count': metricsStore.length.toString(),
      'X-Last-Metric': metricsStore.length > 0 
        ? new Date(metricsStore[metricsStore.length - 1].timestamp_ms).toISOString()
        : 'none'
    }
  });
}