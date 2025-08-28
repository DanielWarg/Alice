/**
 * Monitoring Dashboard API - Real-time system metrics and alerts
 */
import { NextRequest, NextResponse } from 'next/server';
import { monitoring } from '@/lib/monitoring';
import { FeatureFlag } from '@/lib/feature-flags';

export async function GET(request: NextRequest) {
  try {
    // Check if monitoring is enabled
    if (!FeatureFlag.isMetricsCollectionEnabled()) {
      return NextResponse.json({
        error: 'Monitoring is disabled'
      }, { status: 503 });
    }

    const { searchParams } = new URL(request.url);
    const windowMs = parseInt(searchParams.get('window_ms') || '3600000'); // Default 1 hour
    const includeResolved = searchParams.get('include_resolved') === 'true';

    // Get system health
    const systemHealth = monitoring.getSystemHealth();
    
    // Get recent metrics
    const recentMetrics = monitoring.getMetrics(undefined, windowMs);
    
    // Get alerts
    const alerts = monitoring.getAlerts(includeResolved);
    
    // Group metrics by name for easier consumption
    const metricsByName: Record<string, any[]> = {};
    for (const metric of recentMetrics) {
      if (!metricsByName[metric.name]) {
        metricsByName[metric.name] = [];
      }
      metricsByName[metric.name].push({
        value: metric.value,
        timestamp: metric.timestamp,
        tags: metric.tags
      });
    }

    // Calculate summary statistics
    const summaryStats: Record<string, any> = {};
    for (const [metricName, events] of Object.entries(metricsByName)) {
      if (events.length === 0) continue;
      
      const values = events.map(e => e.value);
      summaryStats[metricName] = {
        count: events.length,
        latest: values[values.length - 1],
        min: Math.min(...values),
        max: Math.max(...values),
        avg: values.reduce((a, b) => a + b, 0) / values.length,
        p50: values.sort((a, b) => a - b)[Math.floor(values.length * 0.5)] || 0,
        p95: values.sort((a, b) => a - b)[Math.floor(values.length * 0.95)] || 0,
        p99: values.sort((a, b) => a - b)[Math.floor(values.length * 0.99)] || 0
      };
    }

    // Voice system specific metrics
    const voiceMetrics = {
      latency: {
        e2e: summaryStats['voice_e2e_latency_ms'] || null,
        asr: summaryStats['voice_asr_latency_ms'] || null,
        tts: summaryStats['voice_tts_latency_ms'] || null,
        agent: summaryStats['agent_llm_latency_ms'] || null
      },
      error_rates: {
        agent: calculateErrorRate('agent_error_count', 'agent_request_count', metricsByName),
        tools: calculateErrorRate('tool_error_count', 'tool_call_count', metricsByName),
        voice: calculateErrorRate('voice_error_count', 'voice_request_count', metricsByName)
      },
      throughput: {
        voice_requests: summaryStats['voice_request_count']?.count || 0,
        agent_requests: summaryStats['agent_request_count']?.count || 0,
        tool_calls: summaryStats['tool_call_count']?.count || 0
      }
    };

    // Feature flags status
    const featureFlags = FeatureFlag.isDevelopment() ? FeatureFlag.getAllFlags() : undefined;

    const dashboard = {
      timestamp: new Date().toISOString(),
      window_ms: windowMs,
      system_health: systemHealth,
      alerts: alerts.map(alert => ({
        id: alert.id,
        name: alert.rule.name,
        severity: alert.rule.severity,
        description: alert.description,
        value: alert.value,
        threshold: alert.rule.threshold,
        status: alert.status,
        timestamp: alert.timestamp,
        age_ms: Date.now() - alert.timestamp
      })),
      voice_metrics: voiceMetrics,
      summary_stats: summaryStats,
      recent_metrics_count: recentMetrics.length,
      ...(featureFlags && { feature_flags: featureFlags })
    };

    return NextResponse.json(dashboard, {
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'X-System-Health': systemHealth.status,
        'X-Alert-Count': alerts.length.toString()
      }
    });

  } catch (error) {
    console.error('Dashboard API error:', error);
    
    return NextResponse.json({
      error: 'Failed to generate dashboard',
      message: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}

function calculateErrorRate(
  errorMetricName: string, 
  totalMetricName: string, 
  metricsByName: Record<string, any[]>
): number {
  const errorEvents = metricsByName[errorMetricName] || [];
  const totalEvents = metricsByName[totalMetricName] || [];
  
  const errorCount = errorEvents.reduce((sum, event) => sum + event.value, 0);
  const totalCount = totalEvents.reduce((sum, event) => sum + event.value, 0);
  
  if (totalCount === 0) return 0;
  return errorCount / totalCount;
}

// Endpoint for specific metric data (for charting)
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { metric_names, window_ms = 3600000 } = body;
    
    if (!Array.isArray(metric_names)) {
      return NextResponse.json({
        error: 'metric_names must be an array'
      }, { status: 400 });
    }

    const metricsData: Record<string, any[]> = {};
    
    for (const metricName of metric_names) {
      const events = monitoring.getMetrics(metricName, window_ms);
      metricsData[metricName] = events.map(event => ({
        timestamp: event.timestamp,
        value: event.value,
        tags: event.tags
      }));
    }

    return NextResponse.json({
      metrics: metricsData,
      window_ms,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    return NextResponse.json({
      error: 'Failed to fetch metrics',
      message: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}