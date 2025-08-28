/**
 * Guardian Correlation Analysis API
 * ================================
 * 
 * GET /api/metrics/guardian/correlation
 * 
 * Provides RAM vs Response Time correlation analysis for auto-tuning recommendations.
 * Analyzes Guardian system performance to identify optimization opportunities.
 * 
 * Features:
 * - RAM-performance correlation coefficient calculation
 * - Threshold breach analysis
 * - Auto-tuning recommendations
 * - Degradation event tracking
 * - Statistical analysis of system behavior
 * 
 * Query parameters:
 * - hours: Time window for analysis (default: 24)
 * - include_breaches: Include detailed threshold breach data (default: true)
 */

import { NextRequest, NextResponse } from 'next/server';
import { parseGuardianLogs, performCorrelationAnalysis, metricsCache } from '../utils';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const hours = parseInt(searchParams.get('hours') || '24', 10);
    const includeBreaches = searchParams.get('include_breaches') !== 'false';
    
    // Validate parameters
    if (hours < 1 || hours > 168) { // Max 1 week
      return NextResponse.json({
        success: false,
        error: 'Invalid hours parameter. Must be between 1 and 168 (1 week).'
      }, { status: 400 });
    }

    // Check cache first
    const cacheKey = `guardian_correlation_${hours}_${includeBreaches}`;
    const cachedAnalysis = metricsCache.get(cacheKey);
    
    if (cachedAnalysis) {
      return NextResponse.json({
        success: true,
        analysis: cachedAnalysis,
        cached: true,
        timestamp: Date.now(),
        parameters: { hours, include_breaches: includeBreaches }
      });
    }

    // Parse Guardian logs
    const entries = await parseGuardianLogs(hours);
    
    if (entries.length < 10) {
      return NextResponse.json({
        success: true,
        analysis: {
          ram_performance_correlation: {
            correlation_coefficient: 0,
            sample_count: 0,
            ram_stats: { min: 0, max: 0, avg: 0, p95: 0 },
            response_time_stats: { min: 0, max: 0, avg: 0, p95: 0 }
          },
          recommendations: ['Insufficient data for correlation analysis (minimum 10 samples required)'],
          degradation_events: 0,
          threshold_breaches: [],
          message: `Only ${entries.length} samples found in the last ${hours} hours`
        },
        cached: false,
        timestamp: Date.now(),
        parameters: { hours, include_breaches: includeBreaches }
      });
    }

    // Perform correlation analysis
    const analysis = performCorrelationAnalysis(entries);
    
    // Enhance analysis with additional insights
    const enhancedAnalysis = {
      ...analysis,
      analysis_window: {
        hours: hours,
        start_time: entries[0]?.timestamp ? new Date(entries[0].timestamp * 1000).toISOString() : null,
        end_time: entries[entries.length - 1]?.timestamp ? new Date(entries[entries.length - 1].timestamp * 1000).toISOString() : null,
        total_entries: entries.length
      },
      correlation_interpretation: interpretCorrelation(analysis.ram_performance_correlation.correlation_coefficient),
      breach_summary: {
        total_breaches: analysis.threshold_breaches.length,
        breach_frequency_per_hour: Math.round((analysis.threshold_breaches.length / hours) * 100) / 100,
        most_common_breach: getMostCommonBreachType(analysis.threshold_breaches),
        recent_breach_trend: getRecentBreachTrend(analysis.threshold_breaches)
      },
      performance_insights: {
        system_efficiency: calculateSystemEfficiency(analysis),
        optimization_priority: getOptimizationPriority(analysis),
        stability_score: calculateStabilityScore(analysis, entries.length)
      }
    };

    // Remove detailed breaches if not requested (reduce payload size)
    if (!includeBreaches) {
      enhancedAnalysis.threshold_breaches = [];
    }

    // Cache the result
    metricsCache.set(cacheKey, enhancedAnalysis);

    return NextResponse.json({
      success: true,
      analysis: enhancedAnalysis,
      cached: false,
      timestamp: Date.now(),
      parameters: { hours, include_breaches: includeBreaches }
    });

  } catch (error) {
    console.error('Failed to perform correlation analysis:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Failed to perform correlation analysis',
      details: error instanceof Error ? error.message : 'Unknown error',
      timestamp: Date.now()
    }, { status: 500 });
  }
}

/**
 * POST endpoint for custom correlation analysis with specific parameters
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { 
      hours = 24, 
      ram_threshold = 0.85, 
      response_time_threshold = 30,
      include_recommendations = true 
    } = body;

    // Validate parameters
    if (hours < 1 || hours > 168) {
      return NextResponse.json({
        success: false,
        error: 'Invalid hours parameter. Must be between 1 and 168.'
      }, { status: 400 });
    }

    // Parse Guardian logs
    const entries = await parseGuardianLogs(hours);
    
    if (entries.length < 5) {
      return NextResponse.json({
        success: true,
        analysis: {
          error: 'Insufficient data for custom analysis',
          sample_count: entries.length
        },
        timestamp: Date.now()
      });
    }

    // Perform correlation analysis
    const analysis = performCorrelationAnalysis(entries);
    
    // Apply custom thresholds and filtering
    const customAnalysis = {
      ...analysis,
      custom_parameters: { hours, ram_threshold, response_time_threshold },
      filtered_breaches: analysis.threshold_breaches.filter(breach => 
        breach.value >= ram_threshold || (breach.threshold_type.includes('cpu') && breach.value >= 0.85)
      ),
      performance_alerts: generatePerformanceAlerts(analysis, ram_threshold, response_time_threshold),
      tuning_suggestions: include_recommendations ? generateTuningSuggestions(analysis, {
        ram_threshold,
        response_time_threshold
      }) : []
    };

    return NextResponse.json({
      success: true,
      analysis: customAnalysis,
      timestamp: Date.now()
    });

  } catch (error) {
    console.error('Failed to perform custom correlation analysis:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Failed to perform custom correlation analysis',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}

/**
 * Interpret correlation coefficient with human-readable explanation
 */
function interpretCorrelation(coefficient: number): string {
  const abs = Math.abs(coefficient);
  
  if (abs < 0.1) return 'No significant correlation';
  if (abs < 0.3) return 'Weak correlation';
  if (abs < 0.5) return 'Moderate correlation';
  if (abs < 0.7) return 'Strong correlation';
  return 'Very strong correlation';
}

/**
 * Find most common threshold breach type
 */
function getMostCommonBreachType(breaches: any[]): string {
  if (breaches.length === 0) return 'None';
  
  const counts = breaches.reduce((acc, breach) => {
    acc[breach.threshold_type] = (acc[breach.threshold_type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  return Object.entries(counts)
    .sort(([,a], [,b]) => b - a)[0]?.[0] || 'Unknown';
}

/**
 * Analyze recent breach trend
 */
function getRecentBreachTrend(breaches: any[]): 'increasing' | 'decreasing' | 'stable' {
  if (breaches.length < 4) return 'stable';
  
  const now = Date.now() / 1000;
  const oneHourAgo = now - 3600;
  const twoHoursAgo = now - 7200;
  
  const recentBreaches = breaches.filter(b => b.timestamp > oneHourAgo).length;
  const olderBreaches = breaches.filter(b => b.timestamp > twoHoursAgo && b.timestamp <= oneHourAgo).length;
  
  if (recentBreaches > olderBreaches * 1.2) return 'increasing';
  if (recentBreaches < olderBreaches * 0.8) return 'decreasing';
  return 'stable';
}

/**
 * Calculate system efficiency based on correlation analysis
 */
function calculateSystemEfficiency(analysis: any): number {
  const { ram_performance_correlation, degradation_events, threshold_breaches } = analysis;
  
  let efficiency = 100;
  
  // Penalize for poor correlation (high RAM should not mean bad performance in ideal system)
  if (ram_performance_correlation.correlation_coefficient > 0.5) {
    efficiency -= 20;
  }
  
  // Penalize for degradation events
  efficiency -= Math.min(degradation_events * 5, 30);
  
  // Penalize for frequent threshold breaches
  efficiency -= Math.min(threshold_breaches.length * 2, 40);
  
  return Math.max(0, Math.round(efficiency));
}

/**
 * Determine optimization priority level
 */
function getOptimizationPriority(analysis: any): 'low' | 'medium' | 'high' | 'critical' {
  const { degradation_events, threshold_breaches, ram_performance_correlation } = analysis;
  
  if (degradation_events > 5 || threshold_breaches.filter(b => b.threshold_type.includes('hard')).length > 3) {
    return 'critical';
  }
  
  if (degradation_events > 2 || Math.abs(ram_performance_correlation.correlation_coefficient) > 0.7) {
    return 'high';
  }
  
  if (threshold_breaches.length > 10 || Math.abs(ram_performance_correlation.correlation_coefficient) > 0.4) {
    return 'medium';
  }
  
  return 'low';
}

/**
 * Calculate system stability score (0-100)
 */
function calculateStabilityScore(analysis: any, totalSamples: number): number {
  const { degradation_events, threshold_breaches } = analysis;
  
  let score = 100;
  
  // Penalize based on degradation event frequency
  const degradationRate = degradation_events / totalSamples;
  score -= degradationRate * 50;
  
  // Penalize based on threshold breach frequency
  const breachRate = threshold_breaches.length / totalSamples;
  score -= breachRate * 30;
  
  return Math.max(0, Math.round(score));
}

/**
 * Generate performance alerts based on analysis
 */
function generatePerformanceAlerts(analysis: any, ramThreshold: number, responseThreshold: number) {
  const alerts = [];
  
  if (analysis.ram_performance_correlation.correlation_coefficient > 0.7) {
    alerts.push({
      level: 'warning',
      message: 'Strong positive correlation between RAM usage and response time detected',
      recommendation: 'Consider optimizing memory allocation or increasing system resources'
    });
  }
  
  if (analysis.degradation_events > 5) {
    alerts.push({
      level: 'error',
      message: `High number of degradation events: ${analysis.degradation_events}`,
      recommendation: 'Review system thresholds and consider capacity planning'
    });
  }
  
  return alerts;
}

/**
 * Generate specific tuning suggestions
 */
function generateTuningSuggestions(analysis: any, params: any) {
  const suggestions = [];
  
  if (analysis.ram_performance_correlation.ram_stats.avg > 0.8) {
    suggestions.push({
      parameter: 'ram_soft_threshold',
      current: 0.85,
      suggested: 0.75,
      reason: 'High average RAM usage detected'
    });
  }
  
  if (analysis.threshold_breaches.filter(b => b.threshold_type === 'ram_hard').length > 3) {
    suggestions.push({
      parameter: 'ram_hard_threshold',
      current: 0.92,
      suggested: 0.88,
      reason: 'Frequent hard RAM threshold breaches'
    });
  }
  
  return suggestions;
}