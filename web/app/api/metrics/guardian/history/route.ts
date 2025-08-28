/**
 * Guardian Historical Data API
 * ===========================
 * 
 * GET /api/metrics/guardian/history
 * 
 * Returns historical Guardian metrics data for dashboard graphs and analysis.
 * Provides time-series data with flexible aggregation and filtering options.
 * 
 * Features:
 * - Flexible time window selection
 * - Data aggregation (raw, minute, hour averages)
 * - Metric filtering (RAM, CPU, response times)
 * - Graph-ready JSON format
 * - Downsampling for performance
 * 
 * Query parameters:
 * - hours: Time window for history (default: 24, max: 168)
 * - resolution: Data resolution (raw, minute, hour) (default: auto)
 * - metrics: Comma-separated list of metrics to include (default: all)
 * - format: Output format (timeseries, summary) (default: timeseries)
 * - downsample: Max number of data points (default: 1000)
 */

import { NextRequest, NextResponse } from 'next/server';
import { parseGuardianLogs, extractMetrics, GuardianMetrics, metricsCache } from '../utils';

export const dynamic = 'force-dynamic';

type Resolution = 'raw' | 'minute' | 'hour' | 'auto';
type OutputFormat = 'timeseries' | 'summary';
type MetricType = 'ram_pct' | 'cpu_pct' | 'disk_pct' | 'temp_c' | 'ram_gb' | 'response_time' | 'ollama_pids';

interface TimeSeriesPoint {
  timestamp: number;
  iso_time: string;
  metrics: Partial<Record<MetricType, number>>;
  system_state: {
    degraded: boolean;
    intake_blocked: boolean;
    emergency_mode: boolean;
  };
}

interface HistoricalSummary {
  timespan: {
    hours: number;
    start_time: string;
    end_time: string;
    total_samples: number;
  };
  aggregated_metrics: Record<MetricType, {
    min: number;
    max: number;
    avg: number;
    p50: number;
    p95: number;
    current: number;
  }>;
  system_events: {
    total_degradations: number;
    total_emergencies: number;
    uptime_percentage: number;
    state_changes: Array<{
      timestamp: number;
      from_state: string;
      to_state: string;
    }>;
  };
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const hours = Math.min(parseInt(searchParams.get('hours') || '24', 10), 168); // Max 1 week
    const resolution = (searchParams.get('resolution') || 'auto') as Resolution;
    const metricsParam = searchParams.get('metrics');
    const format = (searchParams.get('format') || 'timeseries') as OutputFormat;
    const downsample = parseInt(searchParams.get('downsample') || '1000', 10);
    
    // Validate parameters
    if (hours < 1) {
      return NextResponse.json({
        success: false,
        error: 'Invalid hours parameter. Must be at least 1.'
      }, { status: 400 });
    }

    if (!['raw', 'minute', 'hour', 'auto'].includes(resolution)) {
      return NextResponse.json({
        success: false,
        error: 'Invalid resolution parameter. Must be one of: raw, minute, hour, auto'
      }, { status: 400 });
    }

    if (!['timeseries', 'summary'].includes(format)) {
      return NextResponse.json({
        success: false,
        error: 'Invalid format parameter. Must be one of: timeseries, summary'
      }, { status: 400 });
    }

    // Parse requested metrics
    const requestedMetrics: MetricType[] = metricsParam 
      ? metricsParam.split(',').map(m => m.trim() as MetricType)
      : ['ram_pct', 'cpu_pct', 'disk_pct', 'temp_c', 'ram_gb', 'response_time'];

    // Check cache first
    const cacheKey = `guardian_history_${hours}_${resolution}_${format}_${metricsParam || 'all'}_${downsample}`;
    const cachedHistory = metricsCache.get(cacheKey);
    
    if (cachedHistory) {
      return NextResponse.json({
        success: true,
        data: cachedHistory,
        cached: true,
        timestamp: Date.now(),
        parameters: { hours, resolution, metrics: requestedMetrics, format, downsample }
      });
    }

    // Parse Guardian logs
    const entries = await parseGuardianLogs(hours);
    
    if (entries.length === 0) {
      const emptyResponse = format === 'summary' ? {
        timespan: { hours, start_time: null, end_time: null, total_samples: 0 },
        aggregated_metrics: {},
        system_events: { total_degradations: 0, total_emergencies: 0, uptime_percentage: 0, state_changes: [] }
      } : {
        timeseries: [],
        meta: { hours, resolution: 'raw', total_points: 0 }
      };

      return NextResponse.json({
        success: true,
        data: emptyResponse,
        cached: false,
        timestamp: Date.now(),
        parameters: { hours, resolution, metrics: requestedMetrics, format, downsample }
      });
    }

    // Extract metrics
    const metrics = extractMetrics(entries);
    
    if (metrics.length === 0) {
      return NextResponse.json({
        success: false,
        error: 'No metric data found in Guardian logs',
        timestamp: Date.now()
      });
    }

    // Determine optimal resolution if auto
    const finalResolution = resolution === 'auto' ? 
      determineOptimalResolution(metrics.length, hours) : 
      resolution;

    // Process data based on format
    let result;
    
    if (format === 'summary') {
      result = generateHistoricalSummary(metrics, requestedMetrics, hours);
    } else {
      // Generate timeseries data
      const timeseries = generateTimeSeries(metrics, requestedMetrics, finalResolution);
      
      // Apply downsampling if needed
      const downsampledTimeseries = downsample && timeseries.length > downsample ?
        downsampleTimeSeries(timeseries, downsample) :
        timeseries;

      result = {
        timeseries: downsampledTimeseries,
        meta: {
          hours,
          resolution: finalResolution,
          total_points: downsampledTimeseries.length,
          original_points: timeseries.length,
          downsampled: timeseries.length > downsampledTimeseries.length,
          time_range: {
            start: downsampledTimeseries[0]?.iso_time || null,
            end: downsampledTimeseries[downsampledTimeseries.length - 1]?.iso_time || null
          }
        }
      };
    }

    // Cache the result
    metricsCache.set(cacheKey, result);

    return NextResponse.json({
      success: true,
      data: result,
      cached: false,
      timestamp: Date.now(),
      parameters: { hours, resolution: finalResolution, metrics: requestedMetrics, format, downsample }
    });

  } catch (error) {
    console.error('Failed to fetch Guardian history:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch Guardian history',
      details: error instanceof Error ? error.message : 'Unknown error',
      timestamp: Date.now()
    }, { status: 500 });
  }
}

/**
 * Determine optimal resolution based on data volume and time range
 */
function determineOptimalResolution(sampleCount: number, hours: number): Resolution {
  // For large datasets or long time ranges, use aggregated resolution
  if (hours > 72 || sampleCount > 5000) return 'hour';
  if (hours > 24 || sampleCount > 2000) return 'minute';
  return 'raw';
}

/**
 * Generate time series data with specified resolution
 */
function generateTimeSeries(
  metrics: GuardianMetrics[], 
  requestedMetrics: MetricType[], 
  resolution: Resolution
): TimeSeriesPoint[] {
  if (resolution === 'raw') {
    return metrics.map(metric => ({
      timestamp: new Date(metric.timestamp).getTime(),
      iso_time: metric.timestamp,
      metrics: extractRequestedMetrics(metric, requestedMetrics),
      system_state: {
        degraded: metric.degraded,
        intake_blocked: metric.intake_blocked,
        emergency_mode: metric.emergency_mode
      }
    }));
  }

  // Aggregate data by time buckets
  const bucketSize = resolution === 'minute' ? 60 * 1000 : 60 * 60 * 1000; // ms
  const buckets = new Map<number, GuardianMetrics[]>();

  metrics.forEach(metric => {
    const timestamp = new Date(metric.timestamp).getTime();
    const bucketKey = Math.floor(timestamp / bucketSize) * bucketSize;
    
    if (!buckets.has(bucketKey)) {
      buckets.set(bucketKey, []);
    }
    buckets.get(bucketKey)!.push(metric);
  });

  // Generate aggregated time series points
  return Array.from(buckets.entries())
    .sort(([a], [b]) => a - b)
    .map(([timestamp, bucketMetrics]) => ({
      timestamp,
      iso_time: new Date(timestamp).toISOString(),
      metrics: aggregateBucketMetrics(bucketMetrics, requestedMetrics),
      system_state: {
        degraded: bucketMetrics.some(m => m.degraded),
        intake_blocked: bucketMetrics.some(m => m.intake_blocked),
        emergency_mode: bucketMetrics.some(m => m.emergency_mode)
      }
    }));
}

/**
 * Extract only requested metrics from a metric object
 */
function extractRequestedMetrics(metric: GuardianMetrics, requested: MetricType[]): Partial<Record<MetricType, number>> {
  const result: Partial<Record<MetricType, number>> = {};
  
  requested.forEach(metricName => {
    switch (metricName) {
      case 'ram_pct':
        result.ram_pct = metric.ram_pct;
        break;
      case 'cpu_pct':
        result.cpu_pct = metric.cpu_pct;
        break;
      case 'disk_pct':
        result.disk_pct = metric.disk_pct;
        break;
      case 'temp_c':
        result.temp_c = metric.temp_c;
        break;
      case 'ram_gb':
        result.ram_gb = metric.ram_gb;
        break;
      case 'response_time':
        result.response_time = metric.llm_response_time;
        break;
      case 'ollama_pids':
        result.ollama_pids = metric.ollama_pids.length;
        break;
    }
  });

  return result;
}

/**
 * Aggregate metrics within a time bucket
 */
function aggregateBucketMetrics(bucketMetrics: GuardianMetrics[], requested: MetricType[]): Partial<Record<MetricType, number>> {
  const result: Partial<Record<MetricType, number>> = {};
  
  requested.forEach(metricName => {
    let values: number[] = [];
    
    switch (metricName) {
      case 'ram_pct':
        values = bucketMetrics.map(m => m.ram_pct);
        break;
      case 'cpu_pct':
        values = bucketMetrics.map(m => m.cpu_pct);
        break;
      case 'disk_pct':
        values = bucketMetrics.map(m => m.disk_pct);
        break;
      case 'temp_c':
        values = bucketMetrics.map(m => m.temp_c);
        break;
      case 'ram_gb':
        values = bucketMetrics.map(m => m.ram_gb);
        break;
      case 'response_time':
        values = bucketMetrics.map(m => m.llm_response_time).filter(v => v !== undefined) as number[];
        break;
      case 'ollama_pids':
        values = bucketMetrics.map(m => m.ollama_pids.length);
        break;
    }
    
    if (values.length > 0) {
      // Use average for aggregated values
      result[metricName] = Math.round(values.reduce((sum, val) => sum + val, 0) / values.length * 1000) / 1000;
    }
  });

  return result;
}

/**
 * Downsample time series to reduce data points
 */
function downsampleTimeSeries(timeseries: TimeSeriesPoint[], targetPoints: number): TimeSeriesPoint[] {
  if (timeseries.length <= targetPoints) {
    return timeseries;
  }

  const ratio = timeseries.length / targetPoints;
  const downsampled: TimeSeriesPoint[] = [];

  for (let i = 0; i < targetPoints; i++) {
    const startIndex = Math.floor(i * ratio);
    const endIndex = Math.min(Math.floor((i + 1) * ratio), timeseries.length);
    
    // Take the middle point of the range, or average multiple points
    const middleIndex = Math.floor((startIndex + endIndex) / 2);
    downsampled.push(timeseries[middleIndex]);
  }

  return downsampled;
}

/**
 * Generate historical summary with aggregated statistics
 */
function generateHistoricalSummary(
  metrics: GuardianMetrics[], 
  requestedMetrics: MetricType[], 
  hours: number
): HistoricalSummary {
  const startTime = metrics[0]?.timestamp;
  const endTime = metrics[metrics.length - 1]?.timestamp;
  
  // Calculate aggregated metrics
  const aggregatedMetrics: Record<string, any> = {};
  
  requestedMetrics.forEach(metricName => {
    let values: number[] = [];
    
    switch (metricName) {
      case 'ram_pct':
        values = metrics.map(m => m.ram_pct);
        break;
      case 'cpu_pct':
        values = metrics.map(m => m.cpu_pct);
        break;
      case 'disk_pct':
        values = metrics.map(m => m.disk_pct);
        break;
      case 'temp_c':
        values = metrics.map(m => m.temp_c);
        break;
      case 'ram_gb':
        values = metrics.map(m => m.ram_gb);
        break;
      case 'response_time':
        values = metrics.map(m => m.llm_response_time).filter(v => v !== undefined) as number[];
        break;
      case 'ollama_pids':
        values = metrics.map(m => m.ollama_pids.length);
        break;
    }
    
    if (values.length > 0) {
      const sorted = [...values].sort((a, b) => a - b);
      aggregatedMetrics[metricName] = {
        min: Math.round(sorted[0] * 1000) / 1000,
        max: Math.round(sorted[sorted.length - 1] * 1000) / 1000,
        avg: Math.round(values.reduce((sum, val) => sum + val, 0) / values.length * 1000) / 1000,
        p50: Math.round(sorted[Math.floor(sorted.length * 0.5)] * 1000) / 1000,
        p95: Math.round(sorted[Math.floor(sorted.length * 0.95)] * 1000) / 1000,
        current: Math.round(values[values.length - 1] * 1000) / 1000
      };
    }
  });

  // Calculate system events
  const degradations = metrics.filter(m => m.degraded).length;
  const emergencies = metrics.filter(m => m.emergency_mode).length;
  const uptimePercentage = metrics.length > 0 ? 
    Math.round((1 - emergencies / metrics.length) * 100 * 100) / 100 : 100;

  // Track state changes
  const stateChanges: HistoricalSummary['system_events']['state_changes'] = [];
  let lastState = 'normal';
  
  metrics.forEach((metric, index) => {
    let currentState = 'normal';
    if (metric.emergency_mode) currentState = 'emergency';
    else if (metric.degraded || metric.intake_blocked) currentState = 'degraded';
    
    if (currentState !== lastState) {
      stateChanges.push({
        timestamp: new Date(metric.timestamp).getTime(),
        from_state: lastState,
        to_state: currentState
      });
      lastState = currentState;
    }
  });

  return {
    timespan: {
      hours,
      start_time: startTime || '',
      end_time: endTime || '',
      total_samples: metrics.length
    },
    aggregated_metrics: aggregatedMetrics,
    system_events: {
      total_degradations: degradations,
      total_emergencies: emergencies,
      uptime_percentage: uptimePercentage,
      state_changes: stateChanges
    }
  };
}