/**
 * Guardian Metrics Summary API
 * ============================
 * 
 * GET /api/metrics/guardian/summary
 * 
 * Returns the latest Guardian system status, current metrics, and trends.
 * Provides a high-level overview of the Guardian system health for dashboards.
 * 
 * Features:
 * - Current system metrics (RAM, CPU, disk usage)
 * - System status (ok/degraded/emergency)
 * - Performance trends analysis
 * - Recent system events
 * - Cache optimization for dashboard performance
 */

import { NextResponse } from 'next/server';
import { parseGuardianLogs, calculateSystemSummary, metricsCache, withPerformanceTracking } from '../utils';
import { rateLimiter } from '@/lib/rate-limiter';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  // Apply rate limiting
  const rateLimitResult = await rateLimiter.isAllowed(request, '/api/metrics/guardian/summary');
  
  if (!rateLimitResult.allowed) {
    return NextResponse.json({
      success: false,
      error: 'Rate limit exceeded',
      retry_after_ms: rateLimitResult.resetTime - Date.now()
    }, { 
      status: 429,
      headers: {
        'X-RateLimit-Limit': rateLimitResult.limit.toString(),
        'X-RateLimit-Remaining': rateLimitResult.remaining.toString(),
        'X-RateLimit-Reset': rateLimitResult.resetTime.toString()
      }
    });
  }

  return withPerformanceTracking('/api/metrics/guardian/summary', 'GET', async () => {
    // Check cache first
    const cacheKey = 'guardian_summary';
    const cachedSummary = metricsCache.get(cacheKey);
    
    if (cachedSummary) {
      return NextResponse.json({
        success: true,
        summary: cachedSummary,
        cached: true,
        timestamp: Date.now()
      }, {
        headers: {
          'X-RateLimit-Limit': rateLimitResult.limit.toString(),
          'X-RateLimit-Remaining': rateLimitResult.remaining.toString(),
          'X-RateLimit-Reset': rateLimitResult.resetTime.toString()
        }
      });
    }

    // Parse recent Guardian logs (last 24 hours)
    const entries = await parseGuardianLogs(24);
    
    if (entries.length === 0) {
      return NextResponse.json({
        success: true,
        summary: {
          status: 'unknown',
          current_metrics: null,
          trends: { ram_trend: 'stable', cpu_trend: 'stable', response_time_trend: 'stable' },
          last_events: [],
          uptime_hours: 0,
          total_samples: 0,
          message: 'No Guardian logs found - Guardian may not be running'
        },
        cached: false,
        timestamp: Date.now()
      }, {
        headers: {
          'X-RateLimit-Limit': rateLimitResult.limit.toString(),
          'X-RateLimit-Remaining': rateLimitResult.remaining.toString(),
          'X-RateLimit-Reset': rateLimitResult.resetTime.toString()
        }
      });
    }

    // Calculate system summary with trends
    const summary = calculateSystemSummary(entries);
    
    // Enhanced summary with additional dashboard info
    const enhancedSummary = {
      ...summary,
      guardian_info: {
        guardian_count: new Set(entries.map(e => e.guardian_id)).size,
        session_count: new Set(entries.map(e => e.session_id)).size,
        log_coverage_hours: Math.round(
          ((entries[entries.length - 1]?.timestamp || 0) - (entries[0]?.timestamp || 0)) / 3600 * 100
        ) / 100
      },
      thresholds: {
        ram_soft: 0.85,
        ram_hard: 0.92,
        cpu_soft: 0.85,
        cpu_hard: 0.92,
        disk_hard: 0.95
      },
      health_indicators: {
        ollama_running: summary.current_metrics?.ollama_pids?.length > 0,
        system_stable: !summary.current_metrics?.degraded && !summary.current_metrics?.emergency_mode,
        intake_healthy: !summary.current_metrics?.intake_blocked,
        memory_healthy: (summary.current_metrics?.ram_pct || 0) < 0.85,
        cpu_healthy: (summary.current_metrics?.cpu_pct || 0) < 0.85
      }
    };

    // Cache the result with category-specific settings
    metricsCache.set(cacheKey, enhancedSummary, 'summary');

    return NextResponse.json({
      success: true,
      summary: enhancedSummary,
      cached: false,
      timestamp: Date.now()
    }, {
      headers: {
        'X-RateLimit-Limit': rateLimitResult.limit.toString(),
        'X-RateLimit-Remaining': rateLimitResult.remaining.toString(),
        'X-RateLimit-Reset': rateLimitResult.resetTime.toString()
      }
    });
  }, false).catch(error => {
    console.error('Failed to generate Guardian summary:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Failed to generate Guardian summary',
      details: error instanceof Error ? error.message : 'Unknown error',
      timestamp: Date.now()
    }, { 
      status: 500,
      headers: {
        'X-RateLimit-Limit': rateLimitResult.limit.toString(),
        'X-RateLimit-Remaining': rateLimitResult.remaining.toString(),
        'X-RateLimit-Reset': rateLimitResult.resetTime.toString()
      }
    });
  });
}

/**
 * Health check endpoint
 */
export async function HEAD() {
  try {
    // Quick health check - just verify log directory access
    const entries = await parseGuardianLogs(1); // Last hour only
    
    return new NextResponse(null, {
      status: 200,
      headers: {
        'X-Guardian-Status': entries.length > 0 ? 'active' : 'inactive',
        'X-Sample-Count': entries.length.toString(),
        'X-Last-Entry': entries.length > 0 ? 
          new Date(entries[entries.length - 1].timestamp * 1000).toISOString() : 
          'none'
      }
    });
  } catch (error) {
    return new NextResponse(null, {
      status: 503,
      headers: {
        'X-Guardian-Status': 'error',
        'X-Error': 'Failed to access Guardian logs'
      }
    });
  }
}