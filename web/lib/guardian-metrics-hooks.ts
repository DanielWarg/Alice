/**
 * Guardian Metrics React Hooks
 * ============================
 * 
 * Custom React hooks for fetching Guardian metrics data from the API endpoints.
 * Provides easy-to-use hooks for dashboard components with built-in error handling,
 * caching, and auto-refresh capabilities.
 * 
 * Available hooks:
 * - useGuardianSummary: System status and trends
 * - useGuardianCorrelation: RAM vs performance correlation
 * - useGuardianAlerts: Active alerts and warnings
 * - useGuardianHistory: Historical metrics for graphs
 * - useGuardianAnalysis: On-demand correlation analysis
 */

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

// Types for Guardian metrics data
interface GuardianMetrics {
  timestamp: string;
  ram_pct: number;
  cpu_pct: number;
  disk_pct: number;
  temp_c: number;
  ram_gb: number;
  ollama_pids: number[];
  degraded: boolean;
  intake_blocked: boolean;
  emergency_mode: boolean;
}

interface SystemSummary {
  status: 'ok' | 'degraded' | 'emergency' | 'unknown';
  current_metrics: GuardianMetrics | null;
  trends: {
    ram_trend: 'increasing' | 'decreasing' | 'stable';
    cpu_trend: 'increasing' | 'decreasing' | 'stable';
    response_time_trend: 'increasing' | 'decreasing' | 'stable';
  };
  last_events: Array<{
    type: string;
    timestamp: number;
    message: string;
  }>;
  uptime_hours: number;
  total_samples: number;
  guardian_info?: {
    guardian_count: number;
    session_count: number;
    log_coverage_hours: number;
  };
  health_indicators?: {
    ollama_running: boolean;
    system_stable: boolean;
    intake_healthy: boolean;
    memory_healthy: boolean;
    cpu_healthy: boolean;
  };
}

interface AlertInfo {
  id: string;
  type: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL';
  message: string;
  timestamp: number;
  details: Record<string, any>;
  resolved: boolean;
}

interface CorrelationAnalysis {
  ram_performance_correlation: {
    correlation_coefficient: number;
    sample_count: number;
    ram_stats: {
      min: number;
      max: number;
      avg: number;
      p95: number;
    };
    response_time_stats: {
      min: number;
      max: number;
      avg: number;
      p95: number;
    };
  };
  recommendations: string[];
  degradation_events: number;
  threshold_breaches: Array<{
    timestamp: number;
    threshold_type: 'ram_soft' | 'ram_hard' | 'cpu_soft' | 'cpu_hard';
    value: number;
    threshold: number;
  }>;
}

interface HistoryData {
  timeseries?: Array<{
    timestamp: number;
    iso_time: string;
    metrics: Partial<Record<string, number>>;
    system_state: {
      degraded: boolean;
      intake_blocked: boolean;
      emergency_mode: boolean;
    };
  }>;
  meta?: {
    hours: number;
    resolution: string;
    total_points: number;
    time_range: {
      start: string | null;
      end: string | null;
    };
  };
}

interface UseMetricsOptions {
  enabled?: boolean;
  refetchInterval?: number;
  retryOnError?: boolean;
  maxRetries?: number;
  onError?: (error: Error) => void;
  onSuccess?: (data: any) => void;
}

interface UseMetricsResult<T> {
  data: T | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  lastUpdated: number | null;
}

/**
 * Generic hook for Guardian metrics API calls
 */
function useGuardianMetrics<T>(
  endpoint: string,
  options: UseMetricsOptions = {}
): UseMetricsResult<T> {
  const {
    enabled = true,
    refetchInterval = 30000, // 30 seconds default
    retryOnError = true,
    maxRetries = 3,
    onError,
    onSuccess
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(enabled);
  const [isError, setIsError] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  const retryCountRef = useRef(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchData = useCallback(async () => {
    if (!enabled) return;

    // Cancel previous request if still pending
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();

    try {
      setIsLoading(true);
      setIsError(false);

      const response = await fetch(endpoint, {
        signal: abortControllerRef.current.signal,
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        // Handle rate limiting
        if (response.status === 429) {
          const retryAfter = response.headers.get('Retry-After');
          const delay = retryAfter ? parseInt(retryAfter) * 1000 : 60000;
          throw new Error(`Rate limited. Retry after ${delay}ms`);
        }

        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'API request failed');
      }

      setData(result.data || result.summary || result.analysis || result.alerts || result);
      setLastUpdated(Date.now());
      retryCountRef.current = 0; // Reset retry count on success

      if (onSuccess) {
        onSuccess(result);
      }

    } catch (err) {
      const error = err as Error;
      
      // Don't treat abort as an error
      if (error.name === 'AbortError') {
        return;
      }

      console.error(`Guardian metrics fetch error for ${endpoint}:`, error);

      setIsError(true);
      setError(error);

      if (onError) {
        onError(error);
      }

      // Retry logic
      if (retryOnError && retryCountRef.current < maxRetries) {
        retryCountRef.current++;
        const retryDelay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000); // Exponential backoff, max 30s
        
        setTimeout(() => {
          fetchData();
        }, retryDelay);
      }

    } finally {
      setIsLoading(false);
    }
  }, [endpoint, enabled, retryOnError, maxRetries, onError, onSuccess]);

  // Initial fetch and interval setup
  useEffect(() => {
    if (!enabled) return;

    // Initial fetch
    fetchData();

    // Set up interval for auto-refresh
    if (refetchInterval > 0) {
      intervalRef.current = setInterval(fetchData, refetchInterval);
    }

    // Cleanup
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchData, refetchInterval]);

  return {
    data,
    isLoading,
    isError,
    error,
    refetch: fetchData,
    lastUpdated
  };
}

/**
 * Hook for Guardian system summary
 */
export function useGuardianSummary(options: UseMetricsOptions = {}) {
  return useGuardianMetrics<SystemSummary>('/api/metrics/guardian/summary', {
    refetchInterval: 15000, // 15 seconds for dashboard
    ...options
  });
}

/**
 * Hook for Guardian correlation analysis
 */
export function useGuardianCorrelation(hours: number = 24, options: UseMetricsOptions = {}) {
  const endpoint = `/api/metrics/guardian/correlation?hours=${hours}`;
  
  return useGuardianMetrics<CorrelationAnalysis>(endpoint, {
    refetchInterval: 60000, // 1 minute for correlation data
    ...options
  });
}

/**
 * Hook for Guardian alerts
 */
export function useGuardianAlerts(
  hours: number = 24,
  activeOnly: boolean = true,
  options: UseMetricsOptions = {}
) {
  const endpoint = `/api/metrics/guardian/alerts?hours=${hours}&active_only=${activeOnly}`;
  
  return useGuardianMetrics<{
    active_alerts: AlertInfo[];
    resolved_alerts?: AlertInfo[];
    alert_summary: {
      total: number;
      by_level: Record<string, number>;
      by_type: Record<string, number>;
      active_count: number;
      resolved_count: number;
    };
  }>(endpoint, {
    refetchInterval: 20000, // 20 seconds for alerts
    ...options
  });
}

/**
 * Hook for Guardian historical data
 */
export function useGuardianHistory(
  hours: number = 24,
  resolution: 'raw' | 'minute' | 'hour' | 'auto' = 'auto',
  metrics: string[] = ['ram_pct', 'cpu_pct'],
  options: UseMetricsOptions = {}
) {
  const metricsParam = metrics.join(',');
  const endpoint = `/api/metrics/guardian/history?hours=${hours}&resolution=${resolution}&metrics=${metricsParam}`;
  
  return useGuardianMetrics<HistoryData>(endpoint, {
    refetchInterval: 60000, // 1 minute for history data
    ...options
  });
}

/**
 * Hook for on-demand Guardian analysis
 */
export function useGuardianAnalysis(
  analysisType: 'correlation' | 'optimization' | 'capacity' | 'prediction' | 'comprehensive' = 'comprehensive',
  timeWindow: number = 24,
  options: UseMetricsOptions & { autoRun?: boolean } = {}
) {
  const { autoRun = false, ...hookOptions } = options;
  
  const [requestBody, setRequestBody] = useState({
    analysis_type: analysisType,
    time_window: timeWindow,
    include_predictions: analysisType === 'prediction' || analysisType === 'comprehensive'
  });

  const fetchAnalysis = useCallback(async (customBody?: any) => {
    const body = customBody || requestBody;
    
    const response = await fetch('/api/metrics/guardian/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });

    if (!response.ok) {
      if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After');
        const delay = retryAfter ? parseInt(retryAfter) * 1000 : 300000; // 5 min default
        throw new Error(`Rate limited. Retry after ${delay}ms`);
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error || 'Analysis request failed');
    }

    return result.analysis;
  }, [requestBody]);

  const [data, setData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  const runAnalysis = useCallback(async (customOptions?: any) => {
    try {
      setIsLoading(true);
      setIsError(false);
      setError(null);

      const result = await fetchAnalysis(customOptions);
      setData(result);
      setLastUpdated(Date.now());

      if (hookOptions.onSuccess) {
        hookOptions.onSuccess(result);
      }

    } catch (err) {
      const error = err as Error;
      console.error('Guardian analysis error:', error);
      
      setIsError(true);
      setError(error);

      if (hookOptions.onError) {
        hookOptions.onError(error);
      }
    } finally {
      setIsLoading(false);
    }
  }, [fetchAnalysis, hookOptions]);

  // Auto-run analysis if enabled
  useEffect(() => {
    if (autoRun && hookOptions.enabled !== false) {
      runAnalysis();
    }
  }, [autoRun, runAnalysis, hookOptions.enabled]);

  // Update request body when parameters change
  useEffect(() => {
    setRequestBody({
      analysis_type: analysisType,
      time_window: timeWindow,
      include_predictions: analysisType === 'prediction' || analysisType === 'comprehensive'
    });
  }, [analysisType, timeWindow]);

  return {
    data,
    isLoading,
    isError,
    error,
    refetch: runAnalysis,
    runAnalysis,
    lastUpdated
  };
}

/**
 * Hook for multiple Guardian metrics (dashboard overview)
 */
export function useGuardianDashboard(options: UseMetricsOptions = {}) {
  const summary = useGuardianSummary(options);
  const alerts = useGuardianAlerts(24, true, options);
  const correlation = useGuardianCorrelation(24, { 
    ...options, 
    refetchInterval: 120000 // Less frequent for correlation
  });

  return {
    summary,
    alerts,
    correlation,
    isLoading: summary.isLoading || alerts.isLoading || correlation.isLoading,
    hasError: summary.isError || alerts.isError || correlation.isError,
    errors: [summary.error, alerts.error, correlation.error].filter(Boolean),
    refetchAll: async () => {
      await Promise.all([
        summary.refetch(),
        alerts.refetch(),
        correlation.refetch()
      ]);
    },
    lastUpdated: Math.max(
      summary.lastUpdated || 0,
      alerts.lastUpdated || 0,
      correlation.lastUpdated || 0
    )
  };
}

/**
 * Utility hook for handling rate limiting
 */
export function useRateLimitHandler() {
  const [isRateLimited, setIsRateLimited] = useState(false);
  const [retryAfter, setRetryAfter] = useState<number>(0);

  const handleRateLimit = useCallback((error: Error) => {
    if (error.message.includes('Rate limited')) {
      setIsRateLimited(true);
      const match = error.message.match(/Retry after (\d+)ms/);
      if (match) {
        const delay = parseInt(match[1]);
        setRetryAfter(delay);
        
        // Auto-reset after delay
        setTimeout(() => {
          setIsRateLimited(false);
          setRetryAfter(0);
        }, delay);
      }
    }
  }, []);

  return {
    isRateLimited,
    retryAfter,
    handleRateLimit
  };
}

/**
 * Utility function to format Guardian status for display
 */
export function formatGuardianStatus(status: string): {
  label: string;
  color: string;
  icon: string;
} {
  switch (status) {
    case 'ok':
      return { label: 'Healthy', color: 'green', icon: '✅' };
    case 'degraded':
      return { label: 'Degraded', color: 'yellow', icon: '⚠️' };
    case 'emergency':
      return { label: 'Emergency', color: 'red', icon: '🚨' };
    case 'unknown':
      return { label: 'Unknown', color: 'gray', icon: '❓' };
    default:
      return { label: status, color: 'gray', icon: '❓' };
  }
}

/**
 * Utility function to format metric values
 */
export function formatMetricValue(value: number, type: 'percentage' | 'bytes' | 'milliseconds' | 'count'): string {
  switch (type) {
    case 'percentage':
      return `${Math.round(value * 100)}%`;
    case 'bytes':
      if (value >= 1) return `${value.toFixed(1)} GB`;
      return `${(value * 1024).toFixed(0)} MB`;
    case 'milliseconds':
      if (value >= 1000) return `${(value / 1000).toFixed(1)}s`;
      return `${Math.round(value)}ms`;
    case 'count':
      return value.toString();
    default:
      return value.toString();
  }
}