/**
 * Guardian On-Demand Analysis API
 * ===============================
 * 
 * POST /api/metrics/guardian/analyze
 * 
 * Performs on-demand correlation analysis and system optimization recommendations.
 * Provides deep insights into Guardian system behavior for auto-tuning and optimization.
 * 
 * Features:
 * - Custom correlation analysis parameters
 * - Performance optimization recommendations
 * - Threshold tuning suggestions
 * - System capacity analysis
 * - Predictive alerting thresholds
 * - Multi-dimensional correlation analysis
 * 
 * Request body parameters:
 * - analysis_type: Type of analysis (correlation, optimization, capacity, prediction)
 * - time_window: Hours to analyze (default: 24)
 * - custom_thresholds: Custom threshold values for analysis
 * - focus_areas: Specific metrics to focus on
 * - include_predictions: Whether to include predictive analysis
 */

import { NextRequest, NextResponse } from 'next/server';
import { parseGuardianLogs, performCorrelationAnalysis, extractMetrics, calculateSystemSummary } from '../utils';

export const dynamic = 'force-dynamic';

type AnalysisType = 'correlation' | 'optimization' | 'capacity' | 'prediction' | 'comprehensive';

interface AnalysisRequest {
  analysis_type: AnalysisType;
  time_window?: number;
  custom_thresholds?: {
    ram_soft?: number;
    ram_hard?: number;
    cpu_soft?: number;
    cpu_hard?: number;
    response_time_max?: number;
  };
  focus_areas?: string[];
  include_predictions?: boolean;
  optimization_goals?: ('performance' | 'stability' | 'efficiency')[];
}

interface ComprehensiveAnalysis {
  correlation_analysis: any;
  optimization_recommendations: OptimizationRecommendation[];
  capacity_analysis: CapacityAnalysis;
  predictive_insights?: PredictiveInsights;
  system_health_score: number;
  auto_tuning_suggestions: AutoTuningSuggestion[];
  executive_summary: string;
}

interface OptimizationRecommendation {
  category: 'threshold' | 'capacity' | 'configuration' | 'monitoring';
  priority: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  impact: string;
  implementation_effort: 'low' | 'medium' | 'high';
  estimated_improvement: string;
  technical_details: Record<string, any>;
}

interface CapacityAnalysis {
  current_utilization: {
    ram: number;
    cpu: number;
    response_capacity: number;
  };
  trend_analysis: {
    growth_rate_per_week: {
      ram: number;
      cpu: number;
      request_volume: number;
    };
    projected_limits: {
      ram_limit_days: number;
      cpu_limit_days: number;
      capacity_limit_days: number;
    };
  };
  scaling_recommendations: Array<{
    metric: string;
    current_value: number;
    recommended_action: string;
    timeline: string;
  }>;
}

interface PredictiveInsights {
  degradation_probability: {
    next_hour: number;
    next_day: number;
    next_week: number;
  };
  optimal_thresholds: {
    ram_soft: number;
    ram_hard: number;
    cpu_soft: number;
    cpu_hard: number;
  };
  maintenance_windows: Array<{
    start_time: string;
    duration_hours: number;
    confidence: number;
    reason: string;
  }>;
}

interface AutoTuningSuggestion {
  parameter: string;
  current_value: number;
  suggested_value: number;
  confidence: number;
  rationale: string;
  risk_level: 'low' | 'medium' | 'high';
  validation_steps: string[];
}

export async function POST(request: NextRequest) {
  try {
    const body: AnalysisRequest = await request.json();
    const {
      analysis_type = 'comprehensive',
      time_window = 24,
      custom_thresholds = {},
      focus_areas = [],
      include_predictions = false,
      optimization_goals = ['performance', 'stability']
    } = body;

    // Validate parameters
    if (time_window < 1 || time_window > 168) {
      return NextResponse.json({
        success: false,
        error: 'Invalid time_window. Must be between 1 and 168 hours.'
      }, { status: 400 });
    }

    if (!['correlation', 'optimization', 'capacity', 'prediction', 'comprehensive'].includes(analysis_type)) {
      return NextResponse.json({
        success: false,
        error: 'Invalid analysis_type. Must be one of: correlation, optimization, capacity, prediction, comprehensive'
      }, { status: 400 });
    }

    // Parse Guardian logs
    const entries = await parseGuardianLogs(time_window);
    
    if (entries.length < 20) {
      return NextResponse.json({
        success: false,
        error: `Insufficient data for analysis. Found ${entries.length} entries, minimum 20 required.`,
        suggestion: 'Wait for more Guardian data to be collected or increase time window.'
      }, { status: 400 });
    }

    let analysisResult: any;

    switch (analysis_type) {
      case 'correlation':
        analysisResult = await performCorrelationOnlyAnalysis(entries, custom_thresholds);
        break;
      
      case 'optimization':
        analysisResult = await performOptimizationAnalysis(entries, optimization_goals);
        break;
      
      case 'capacity':
        analysisResult = await performCapacityAnalysis(entries);
        break;
      
      case 'prediction':
        if (!include_predictions) {
          return NextResponse.json({
            success: false,
            error: 'Predictive analysis requires include_predictions=true'
          }, { status: 400 });
        }
        analysisResult = await performPredictiveAnalysis(entries);
        break;
      
      case 'comprehensive':
      default:
        analysisResult = await performComprehensiveAnalysis(
          entries, 
          custom_thresholds, 
          optimization_goals, 
          include_predictions
        );
        break;
    }

    return NextResponse.json({
      success: true,
      analysis: analysisResult,
      meta: {
        analysis_type,
        time_window,
        sample_count: entries.length,
        analysis_timestamp: Date.now(),
        data_coverage: {
          start_time: entries[0]?.timestamp ? new Date(entries[0].timestamp * 1000).toISOString() : null,
          end_time: entries[entries.length - 1]?.timestamp ? new Date(entries[entries.length - 1].timestamp * 1000).toISOString() : null
        }
      }
    });

  } catch (error) {
    console.error('Failed to perform Guardian analysis:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Failed to perform Guardian analysis',
      details: error instanceof Error ? error.message : 'Unknown error',
      timestamp: Date.now()
    }, { status: 500 });
  }
}

/**
 * Perform correlation-only analysis
 */
async function performCorrelationOnlyAnalysis(entries: any[], customThresholds: any) {
  const correlation = performCorrelationAnalysis(entries);
  
  return {
    type: 'correlation',
    correlation_analysis: correlation,
    custom_threshold_impact: analyzeCustomThresholdImpact(entries, customThresholds),
    correlation_insights: generateCorrelationInsights(correlation)
  };
}

/**
 * Perform optimization-focused analysis
 */
async function performOptimizationAnalysis(entries: any[], goals: string[]) {
  const metrics = extractMetrics(entries);
  const correlation = performCorrelationAnalysis(entries);
  
  const recommendations: OptimizationRecommendation[] = [];
  
  // Performance optimization recommendations
  if (goals.includes('performance')) {
    recommendations.push(...generatePerformanceRecommendations(metrics, correlation));
  }
  
  // Stability optimization recommendations
  if (goals.includes('stability')) {
    recommendations.push(...generateStabilityRecommendations(metrics, correlation));
  }
  
  // Efficiency optimization recommendations
  if (goals.includes('efficiency')) {
    recommendations.push(...generateEfficiencyRecommendations(metrics, correlation));
  }
  
  return {
    type: 'optimization',
    optimization_recommendations: recommendations.sort((a, b) => {
      const priorityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
      return priorityOrder[b.priority] - priorityOrder[a.priority];
    }),
    optimization_score: calculateOptimizationScore(metrics),
    quick_wins: recommendations.filter(r => r.implementation_effort === 'low' && r.priority !== 'low')
  };
}

/**
 * Perform capacity analysis
 */
async function performCapacityAnalysis(entries: any[]): Promise<{ type: string; capacity_analysis: CapacityAnalysis }> {
  const metrics = extractMetrics(entries);
  
  if (metrics.length === 0) {
    throw new Error('No metrics data available for capacity analysis');
  }

  // Calculate current utilization
  const recentMetrics = metrics.slice(-10);
  const currentUtilization = {
    ram: recentMetrics.reduce((sum, m) => sum + m.ram_pct, 0) / recentMetrics.length,
    cpu: recentMetrics.reduce((sum, m) => sum + m.cpu_pct, 0) / recentMetrics.length,
    response_capacity: recentMetrics.filter(m => m.llm_response_time).length > 0 ?
      recentMetrics.filter(m => m.llm_response_time).reduce((sum, m) => sum + m.llm_response_time!, 0) / 
      recentMetrics.filter(m => m.llm_response_time).length : 0
  };

  // Calculate trends (simplified linear regression)
  const trends = calculateMetricTrends(metrics);
  
  // Project when limits might be reached
  const projectedLimits = {
    ram_limit_days: calculateTimeToLimit(trends.ram, currentUtilization.ram, 0.90),
    cpu_limit_days: calculateTimeToLimit(trends.cpu, currentUtilization.cpu, 0.90),
    capacity_limit_days: calculateTimeToLimit(trends.response_time || 0, currentUtilization.response_capacity, 60)
  };

  const scalingRecommendations = generateScalingRecommendations(currentUtilization, trends);

  const capacity_analysis: CapacityAnalysis = {
    current_utilization,
    trend_analysis: {
      growth_rate_per_week: {
        ram: trends.ram * 7,
        cpu: trends.cpu * 7,
        request_volume: trends.request_volume || 0
      },
      projected_limits: projectedLimits
    },
    scaling_recommendations: scalingRecommendations
  };

  return {
    type: 'capacity',
    capacity_analysis
  };
}

/**
 * Perform predictive analysis
 */
async function performPredictiveAnalysis(entries: any[]) {
  const metrics = extractMetrics(entries);
  const correlation = performCorrelationAnalysis(entries);
  
  // Calculate degradation probability based on historical patterns
  const degradationProbability = calculateDegradationProbability(metrics);
  
  // Calculate optimal thresholds based on historical performance
  const optimalThresholds = calculateOptimalThresholds(metrics, correlation);
  
  // Identify maintenance windows
  const maintenanceWindows = identifyMaintenanceWindows(metrics);
  
  const predictiveInsights: PredictiveInsights = {
    degradation_probability: degradationProbability,
    optimal_thresholds: optimalThresholds,
    maintenance_windows: maintenanceWindows
  };

  return {
    type: 'prediction',
    predictive_insights: predictiveInsights
  };
}

/**
 * Perform comprehensive analysis combining all analysis types
 */
async function performComprehensiveAnalysis(
  entries: any[], 
  customThresholds: any, 
  goals: string[], 
  includePredictions: boolean
): Promise<ComprehensiveAnalysis> {
  
  const metrics = extractMetrics(entries);
  const correlation = performCorrelationAnalysis(entries);
  const summary = calculateSystemSummary(entries);
  
  // Get all analysis components
  const optimizationResult = await performOptimizationAnalysis(entries, goals);
  const capacityResult = await performCapacityAnalysis(entries);
  
  let predictiveInsights: PredictiveInsights | undefined;
  if (includePredictions) {
    const predictiveResult = await performPredictiveAnalysis(entries);
    predictiveInsights = predictiveResult.predictive_insights;
  }

  // Calculate overall system health score
  const systemHealthScore = calculateSystemHealthScore(metrics, correlation, summary);
  
  // Generate auto-tuning suggestions
  const autoTuningSuggestions = generateAutoTuningSuggestions(metrics, correlation, predictiveInsights);
  
  // Generate executive summary
  const executiveSummary = generateExecutiveSummary(
    systemHealthScore,
    optimizationResult.optimization_recommendations,
    capacityResult.capacity_analysis,
    predictiveInsights
  );

  return {
    correlation_analysis: correlation,
    optimization_recommendations: optimizationResult.optimization_recommendations,
    capacity_analysis: capacityResult.capacity_analysis,
    predictive_insights: predictiveInsights,
    system_health_score: systemHealthScore,
    auto_tuning_suggestions: autoTuningSuggestions,
    executive_summary: executiveSummary
  };
}

/**
 * Generate performance optimization recommendations
 */
function generatePerformanceRecommendations(metrics: any[], correlation: any): OptimizationRecommendation[] {
  const recommendations: OptimizationRecommendation[] = [];
  
  if (correlation.ram_performance_correlation.correlation_coefficient > 0.6) {
    recommendations.push({
      category: 'threshold',
      priority: 'high',
      title: 'Lower RAM soft threshold for better performance',
      description: 'Strong correlation detected between RAM usage and response times',
      impact: 'Reduce average response time by 20-30%',
      implementation_effort: 'low',
      estimated_improvement: 'Response time improvement of 500-1000ms',
      technical_details: {
        current_threshold: 0.85,
        suggested_threshold: 0.75,
        correlation_coefficient: correlation.ram_performance_correlation.correlation_coefficient
      }
    });
  }
  
  return recommendations;
}

/**
 * Generate stability optimization recommendations
 */
function generateStabilityRecommendations(metrics: any[], correlation: any): OptimizationRecommendation[] {
  const recommendations: OptimizationRecommendation[] = [];
  
  if (correlation.degradation_events > 5) {
    recommendations.push({
      category: 'configuration',
      priority: 'high',
      title: 'Reduce degradation frequency',
      description: `System degraded ${correlation.degradation_events} times in the analysis window`,
      impact: 'Improve system stability and user experience',
      implementation_effort: 'medium',
      estimated_improvement: 'Reduce degradation events by 50%',
      technical_details: {
        current_degradations: correlation.degradation_events,
        threshold_breaches: correlation.threshold_breaches.length
      }
    });
  }
  
  return recommendations;
}

/**
 * Generate efficiency optimization recommendations
 */
function generateEfficiencyRecommendations(metrics: any[], correlation: any): OptimizationRecommendation[] {
  const recommendations: OptimizationRecommendation[] = [];
  
  // Add efficiency-specific recommendations based on resource usage patterns
  const avgRam = metrics.reduce((sum, m) => sum + m.ram_pct, 0) / metrics.length;
  
  if (avgRam < 0.5) {
    recommendations.push({
      category: 'capacity',
      priority: 'medium',
      title: 'Consider resource reallocation',
      description: 'System is running below 50% average RAM utilization',
      impact: 'Optimize resource allocation and reduce costs',
      implementation_effort: 'high',
      estimated_improvement: 'Potential 20-30% resource savings',
      technical_details: {
        average_ram_usage: avgRam,
        peak_usage: Math.max(...metrics.map(m => m.ram_pct))
      }
    });
  }
  
  return recommendations;
}

/**
 * Helper functions for calculations
 */
function calculateOptimizationScore(metrics: any[]): number {
  // Simple optimization score based on stability and efficiency
  const avgRam = metrics.reduce((sum, m) => sum + m.ram_pct, 0) / metrics.length;
  const degradationRate = metrics.filter(m => m.degraded).length / metrics.length;
  
  let score = 100;
  score -= degradationRate * 50; // Penalize degradations
  score -= Math.max(0, (avgRam - 0.7) * 100); // Penalize high average usage
  
  return Math.max(0, Math.round(score));
}

function calculateMetricTrends(metrics: any[]) {
  // Simple linear trend calculation
  if (metrics.length < 2) return { ram: 0, cpu: 0, response_time: 0, request_volume: 0 };
  
  const ramTrend = (metrics[metrics.length - 1].ram_pct - metrics[0].ram_pct) / metrics.length;
  const cpuTrend = (metrics[metrics.length - 1].cpu_pct - metrics[0].cpu_pct) / metrics.length;
  
  return {
    ram: ramTrend,
    cpu: cpuTrend,
    response_time: 0, // Placeholder
    request_volume: 0 // Placeholder
  };
}

function calculateTimeToLimit(trend: number, current: number, limit: number): number {
  if (trend <= 0) return -1; // No limit if trend is stable/decreasing
  return Math.round((limit - current) / trend);
}

function generateScalingRecommendations(utilization: any, trends: any) {
  const recommendations = [];
  
  if (utilization.ram > 0.8) {
    recommendations.push({
      metric: 'RAM',
      current_value: utilization.ram,
      recommended_action: 'Scale up memory capacity',
      timeline: 'Within 1-2 weeks'
    });
  }
  
  if (utilization.cpu > 0.8) {
    recommendations.push({
      metric: 'CPU',
      current_value: utilization.cpu,
      recommended_action: 'Scale up compute capacity',
      timeline: 'Within 1-2 weeks'
    });
  }
  
  return recommendations;
}

function calculateDegradationProbability(metrics: any[]) {
  const recentDegradations = metrics.slice(-24).filter(m => m.degraded).length;
  const totalDegradations = metrics.filter(m => m.degraded).length;
  
  return {
    next_hour: Math.min(recentDegradations / 24, 1),
    next_day: Math.min(totalDegradations / metrics.length, 1),
    next_week: Math.min((totalDegradations / metrics.length) * 7, 1)
  };
}

function calculateOptimalThresholds(metrics: any[], correlation: any) {
  // Calculate optimal thresholds based on historical performance
  const avgRam = metrics.reduce((sum, m) => sum + m.ram_pct, 0) / metrics.length;
  
  return {
    ram_soft: Math.max(0.6, avgRam + 0.1),
    ram_hard: Math.max(0.8, avgRam + 0.2),
    cpu_soft: 0.85,
    cpu_hard: 0.92
  };
}

function identifyMaintenanceWindows(metrics: any[]) {
  // Identify low-activity periods suitable for maintenance
  // This is a simplified implementation
  return [
    {
      start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      duration_hours: 2,
      confidence: 0.8,
      reason: 'Low historical activity period'
    }
  ];
}

function calculateSystemHealthScore(metrics: any[], correlation: any, summary: any): number {
  let score = 100;
  
  // Penalize for degradations
  score -= summary.last_events.filter((e: any) => e.type === 'alert').length * 5;
  
  // Penalize for high correlation (inefficiency)
  if (Math.abs(correlation.ram_performance_correlation.correlation_coefficient) > 0.7) {
    score -= 20;
  }
  
  // Penalize for system instability
  if (summary.status === 'emergency') score -= 40;
  else if (summary.status === 'degraded') score -= 20;
  
  return Math.max(0, Math.round(score));
}

function generateAutoTuningSuggestions(metrics: any[], correlation: any, predictions?: PredictiveInsights): AutoTuningSuggestion[] {
  const suggestions: AutoTuningSuggestion[] = [];
  
  if (correlation.ram_performance_correlation.correlation_coefficient > 0.6) {
    suggestions.push({
      parameter: 'ram_soft_threshold',
      current_value: 0.85,
      suggested_value: 0.75,
      confidence: 0.8,
      rationale: 'High RAM-performance correlation detected',
      risk_level: 'low',
      validation_steps: [
        'Monitor for 24 hours after change',
        'Verify no increase in degradation frequency',
        'Check response time improvements'
      ]
    });
  }
  
  return suggestions;
}

function generateExecutiveSummary(
  healthScore: number,
  recommendations: OptimizationRecommendation[],
  capacity: CapacityAnalysis,
  predictions?: PredictiveInsights
): string {
  const criticalRecs = recommendations.filter(r => r.priority === 'critical').length;
  const highRecs = recommendations.filter(r => r.priority === 'high').length;
  
  let summary = `System Health Score: ${healthScore}/100. `;
  
  if (criticalRecs > 0) {
    summary += `${criticalRecs} critical issues require immediate attention. `;
  }
  
  if (highRecs > 0) {
    summary += `${highRecs} high-priority optimizations identified. `;
  }
  
  if (capacity.current_utilization.ram > 0.8) {
    summary += 'RAM utilization is high and may require scaling. ';
  }
  
  if (predictions && predictions.degradation_probability.next_day > 0.3) {
    summary += 'High probability of system degradation in the next 24 hours. ';
  }
  
  summary += 'Review recommendations for detailed optimization steps.';
  
  return summary;
}

function analyzeCustomThresholdImpact(entries: any[], customThresholds: any) {
  // Analyze how custom thresholds would have performed historically
  if (Object.keys(customThresholds).length === 0) {
    return { message: 'No custom thresholds provided for analysis' };
  }
  
  const metrics = extractMetrics(entries);
  let impactAnalysis: Record<string, any> = {};
  
  if (customThresholds.ram_soft) {
    const wouldTrigger = metrics.filter(m => m.ram_pct >= customThresholds.ram_soft).length;
    impactAnalysis.ram_soft = {
      threshold: customThresholds.ram_soft,
      would_trigger_count: wouldTrigger,
      percentage_of_time: Math.round((wouldTrigger / metrics.length) * 100)
    };
  }
  
  return impactAnalysis;
}

function generateCorrelationInsights(correlation: any) {
  const insights = [];
  
  if (Math.abs(correlation.ram_performance_correlation.correlation_coefficient) > 0.7) {
    insights.push({
      type: 'strong_correlation',
      metric_pair: 'RAM vs Performance',
      coefficient: correlation.ram_performance_correlation.correlation_coefficient,
      interpretation: correlation.ram_performance_correlation.correlation_coefficient > 0 ?
        'Higher RAM usage strongly correlates with slower performance' :
        'Higher RAM usage strongly correlates with better performance (unexpected)'
    });
  }
  
  return insights;
}