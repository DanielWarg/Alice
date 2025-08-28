/**
 * Guardian Metrics API Root Endpoint
 * ==================================
 * 
 * GET /api/metrics/guardian
 * 
 * Provides health check and overview of Guardian metrics API system.
 * Returns status of all endpoints and system capabilities.
 */

import { NextResponse } from 'next/server';
import { metricsCache, apiMetricsCollector } from './utils';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const cacheStats = metricsCache.getStats();
    const apiStats = apiMetricsCollector.getPerformanceStats(1); // Last hour

    const systemInfo = {
      status: 'healthy',
      version: '1.0.0',
      timestamp: Date.now(),
      endpoints: {
        '/api/metrics/guardian/summary': {
          description: 'System status and trends',
          methods: ['GET'],
          cache_ttl: 30
        },
        '/api/metrics/guardian/correlation': {
          description: 'RAM vs performance correlation analysis',
          methods: ['GET', 'POST'],
          cache_ttl: 60
        },
        '/api/metrics/guardian/alerts': {
          description: 'Active alerts and warnings',
          methods: ['GET', 'POST'],
          cache_ttl: 15
        },
        '/api/metrics/guardian/history': {
          description: 'Historical metrics for graphs',
          methods: ['GET'],
          cache_ttl: 120
        },
        '/api/metrics/guardian/analyze': {
          description: 'On-demand correlation analysis',
          methods: ['POST'],
          cache_ttl: 300
        }
      },
      rate_limits: {
        summary: '30 req/min',
        correlation: '20 req/min',
        alerts: '60 req/min',
        history: '15 req/min',
        analyze: '10 req/5min'
      },
      cache_performance: {
        total_entries: cacheStats.totalEntries,
        hit_rates: cacheStats.hitRates,
        oldest_entry_age_seconds: cacheStats.oldestEntry > 0 ? 
          Math.round((Date.now() - cacheStats.oldestEntry) / 1000) : 0,
        newest_entry_age_seconds: cacheStats.newestEntry > 0 ? 
          Math.round((Date.now() - cacheStats.newestEntry) / 1000) : 0
      },
      api_performance: {
        requests_last_hour: apiStats.total_requests,
        average_response_time_ms: apiStats.avg_duration,
        cache_hit_rate: apiStats.cache_hit_rate,
        error_rate: apiStats.error_rate,
        endpoint_breakdown: apiStats.endpoint_breakdown
      },
      capabilities: {
        ndjson_parsing: true,
        correlation_analysis: true,
        trend_analysis: true,
        predictive_insights: true,
        auto_tuning_recommendations: true,
        real_time_caching: true,
        rate_limiting: true,
        performance_monitoring: true
      }
    };

    return NextResponse.json({
      success: true,
      system: systemInfo
    });

  } catch (error) {
    console.error('Guardian metrics health check failed:', error);
    
    return NextResponse.json({
      success: false,
      status: 'unhealthy',
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: Date.now()
    }, { status: 500 });
  }
}

/**
 * POST endpoint for system maintenance operations
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action } = body;

    if (!action) {
      return NextResponse.json({
        success: false,
        error: 'Missing required field: action'
      }, { status: 400 });
    }

    switch (action) {
      case 'clear_cache':
        const { category } = body;
        metricsCache.clear(category);
        return NextResponse.json({
          success: true,
          message: `Cache cleared${category ? ` for category: ${category}` : ' (all)'}`,
          timestamp: Date.now()
        });

      case 'get_cache_stats':
        const stats = metricsCache.getStats();
        return NextResponse.json({
          success: true,
          cache_stats: stats,
          timestamp: Date.now()
        });

      case 'get_performance_stats':
        const { hours = 1 } = body;
        const perfStats = apiMetricsCollector.getPerformanceStats(hours);
        return NextResponse.json({
          success: true,
          performance_stats: perfStats,
          timespan_hours: hours,
          timestamp: Date.now()
        });

      default:
        return NextResponse.json({
          success: false,
          error: `Unknown action: ${action}`,
          available_actions: ['clear_cache', 'get_cache_stats', 'get_performance_stats']
        }, { status: 400 });
    }

  } catch (error) {
    console.error('Guardian metrics maintenance operation failed:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Maintenance operation failed',
      details: error instanceof Error ? error.message : 'Unknown error',
      timestamp: Date.now()
    }, { status: 500 });
  }
}