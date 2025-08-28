/**
 * Guardian Metrics API Utilities
 * ==============================
 * 
 * Utilities for parsing Guardian NDJSON logs, data processing, and correlation analysis.
 * Integrates with the Guardian system's logger.py for structured metric collection.
 */

import fs from 'fs';
import path from 'path';
import { glob } from 'glob';

// Type definitions for Guardian log entries
export interface GuardianLogEntry {
  timestamp: number;
  event_type: 'metrics' | 'action' | 'correlation' | 'alert' | 'startup';
  guardian_id: string;
  data: Record<string, any>;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL';
  correlation_id?: string;
  session_id?: string;
}

export interface GuardianMetrics {
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
  llm_response_time?: number;
}

export interface SystemSummary {
  status: 'ok' | 'degraded' | 'emergency';
  current_metrics: GuardianMetrics;
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
}

export interface CorrelationAnalysis {
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

export interface AlertInfo {
  id: string;
  type: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL';
  message: string;
  timestamp: number;
  details: Record<string, any>;
  resolved: boolean;
}

// Guardian log directory path (relative to project root)
const GUARDIAN_LOG_DIR = path.join(process.cwd(), '../server/logs/guardian');

/**
 * Parse NDJSON log files to extract Guardian entries
 */
export async function parseGuardianLogs(hours: number = 24): Promise<GuardianLogEntry[]> {
  const cutoffTime = Date.now() / 1000 - (hours * 3600);
  const entries: GuardianLogEntry[] = [];
  
  try {
    // Find all Guardian log files
    const logFiles = await glob(`${GUARDIAN_LOG_DIR}/guardian_*.ndjson`);
    
    for (const logFile of logFiles) {
      if (!fs.existsSync(logFile)) continue;
      
      const content = fs.readFileSync(logFile, 'utf-8');
      const lines = content.split('\n').filter(line => line.trim());
      
      for (const line of lines) {
        try {
          const entry: GuardianLogEntry = JSON.parse(line);
          
          // Filter by time window
          if (entry.timestamp >= cutoffTime) {
            entries.push(entry);
          }
        } catch (parseError) {
          // Skip invalid JSON lines
          console.warn(`Failed to parse Guardian log line: ${parseError}`);
        }
      }
    }
  } catch (error) {
    console.error('Error reading Guardian log files:', error);
  }
  
  // Sort by timestamp
  return entries.sort((a, b) => a.timestamp - b.timestamp);
}

/**
 * Extract metrics entries from Guardian logs
 */
export function extractMetrics(entries: GuardianLogEntry[]): GuardianMetrics[] {
  return entries
    .filter(entry => entry.event_type === 'metrics' && entry.data.metrics)
    .map(entry => ({
      timestamp: entry.data.collection_time || new Date(entry.timestamp * 1000).toISOString(),
      ram_pct: entry.data.metrics.ram_pct || 0,
      cpu_pct: entry.data.metrics.cpu_pct || 0,
      disk_pct: entry.data.metrics.disk_pct || 0,
      temp_c: entry.data.metrics.temp_c || 0,
      ram_gb: entry.data.metrics.ram_gb || 0,
      ollama_pids: entry.data.metrics.ollama_pids || [],
      degraded: entry.data.metrics.degraded || false,
      intake_blocked: entry.data.metrics.intake_blocked || false,
      emergency_mode: entry.data.metrics.emergency_mode || false,
      llm_response_time: entry.data.metrics.llm_response_time,
    }));
}

/**
 * Calculate system status and trends
 */
export function calculateSystemSummary(entries: GuardianLogEntry[]): SystemSummary {
  const metrics = extractMetrics(entries);
  const currentMetrics = metrics[metrics.length - 1];
  
  if (!currentMetrics) {
    return {
      status: 'ok',
      current_metrics: {
        timestamp: new Date().toISOString(),
        ram_pct: 0, cpu_pct: 0, disk_pct: 0, temp_c: 0, ram_gb: 0,
        ollama_pids: [], degraded: false, intake_blocked: false, emergency_mode: false
      },
      trends: { ram_trend: 'stable', cpu_trend: 'stable', response_time_trend: 'stable' },
      last_events: [],
      uptime_hours: 0,
      total_samples: 0
    };
  }
  
  // Determine overall system status
  let status: 'ok' | 'degraded' | 'emergency' = 'ok';
  if (currentMetrics.emergency_mode) status = 'emergency';
  else if (currentMetrics.degraded || currentMetrics.intake_blocked) status = 'degraded';
  
  // Calculate trends (simple moving average comparison)
  const trends = calculateTrends(metrics);
  
  // Extract recent events (actions and alerts)
  const recentEvents = entries
    .filter(entry => ['action', 'alert'].includes(entry.event_type))
    .slice(-10)
    .map(entry => ({
      type: entry.event_type,
      timestamp: entry.timestamp,
      message: entry.data.action || entry.data.alert_type || entry.data.message || 'Unknown event'
    }));
  
  // Calculate uptime
  const startupEntry = entries.find(entry => entry.event_type === 'startup');
  const uptime_hours = startupEntry ? 
    (Date.now() / 1000 - startupEntry.timestamp) / 3600 : 0;
  
  return {
    status,
    current_metrics: currentMetrics,
    trends,
    last_events: recentEvents,
    uptime_hours: Math.round(uptime_hours * 100) / 100,
    total_samples: metrics.length
  };
}

/**
 * Calculate trend analysis for key metrics
 */
function calculateTrends(metrics: GuardianMetrics[]): SystemSummary['trends'] {
  if (metrics.length < 10) {
    return { ram_trend: 'stable', cpu_trend: 'stable', response_time_trend: 'stable' };
  }
  
  // Compare recent vs older samples
  const recent = metrics.slice(-10);
  const older = metrics.slice(-20, -10);
  
  const avgRecent = {
    ram: recent.reduce((sum, m) => sum + m.ram_pct, 0) / recent.length,
    cpu: recent.reduce((sum, m) => sum + m.cpu_pct, 0) / recent.length,
    response_time: recent
      .filter(m => m.llm_response_time !== undefined)
      .reduce((sum, m) => sum + m.llm_response_time!, 0) / Math.max(1, recent.filter(m => m.llm_response_time !== undefined).length)
  };
  
  const avgOlder = {
    ram: older.reduce((sum, m) => sum + m.ram_pct, 0) / Math.max(1, older.length),
    cpu: older.reduce((sum, m) => sum + m.cpu_pct, 0) / Math.max(1, older.length),
    response_time: older
      .filter(m => m.llm_response_time !== undefined)
      .reduce((sum, m) => sum + m.llm_response_time!, 0) / Math.max(1, older.filter(m => m.llm_response_time !== undefined).length)
  };
  
  const TREND_THRESHOLD = 0.05; // 5% change threshold
  
  return {
    ram_trend: Math.abs(avgRecent.ram - avgOlder.ram) < TREND_THRESHOLD ? 'stable' :
               avgRecent.ram > avgOlder.ram ? 'increasing' : 'decreasing',
    cpu_trend: Math.abs(avgRecent.cpu - avgOlder.cpu) < TREND_THRESHOLD ? 'stable' :
               avgRecent.cpu > avgOlder.cpu ? 'increasing' : 'decreasing',
    response_time_trend: Math.abs(avgRecent.response_time - avgOlder.response_time) < 1 ? 'stable' :
                        avgRecent.response_time > avgOlder.response_time ? 'increasing' : 'decreasing'
  };
}

/**
 * Perform RAM vs Response Time correlation analysis
 */
export function performCorrelationAnalysis(entries: GuardianLogEntry[]): CorrelationAnalysis {
  const metrics = extractMetrics(entries);
  
  // Extract RAM and response time pairs
  const dataPoints: Array<{ ram: number; responseTime: number }> = [];
  const degradationEvents: GuardianLogEntry[] = [];
  const thresholdBreaches: CorrelationAnalysis['threshold_breaches'] = [];
  
  for (const entry of entries) {
    if (entry.event_type === 'metrics' && entry.data.metrics) {
      const m = entry.data.metrics;
      if (m.ram_pct && m.llm_response_time) {
        dataPoints.push({ ram: m.ram_pct, responseTime: m.llm_response_time });
      }
      
      if (m.degraded) {
        degradationEvents.push(entry);
      }
      
      // Track threshold breaches
      const RAM_SOFT = 0.85, RAM_HARD = 0.92, CPU_SOFT = 0.85, CPU_HARD = 0.92;
      if (m.ram_pct > RAM_HARD) {
        thresholdBreaches.push({
          timestamp: entry.timestamp,
          threshold_type: 'ram_hard',
          value: m.ram_pct,
          threshold: RAM_HARD
        });
      } else if (m.ram_pct > RAM_SOFT) {
        thresholdBreaches.push({
          timestamp: entry.timestamp,
          threshold_type: 'ram_soft', 
          value: m.ram_pct,
          threshold: RAM_SOFT
        });
      }
      
      if (m.cpu_pct > CPU_HARD) {
        thresholdBreaches.push({
          timestamp: entry.timestamp,
          threshold_type: 'cpu_hard',
          value: m.cpu_pct,
          threshold: CPU_HARD
        });
      } else if (m.cpu_pct > CPU_SOFT) {
        thresholdBreaches.push({
          timestamp: entry.timestamp,
          threshold_type: 'cpu_soft',
          value: m.cpu_pct,
          threshold: CPU_SOFT
        });
      }
    }
  }
  
  // Calculate correlation coefficient (Pearson)
  let correlationCoefficient = 0;
  if (dataPoints.length > 1) {
    correlationCoefficient = calculatePearsonCorrelation(
      dataPoints.map(p => p.ram),
      dataPoints.map(p => p.responseTime)
    );
  }
  
  // Calculate statistics
  const ramValues = dataPoints.map(p => p.ram);
  const responseValues = dataPoints.map(p => p.responseTime);
  
  const ramStats = calculateStats(ramValues);
  const responseTimeStats = calculateStats(responseValues);
  
  // Generate recommendations
  const recommendations = generateRecommendations(metrics, thresholdBreaches, correlationCoefficient);
  
  return {
    ram_performance_correlation: {
      correlation_coefficient: Math.round(correlationCoefficient * 1000) / 1000,
      sample_count: dataPoints.length,
      ram_stats,
      response_time_stats: responseTimeStats
    },
    recommendations,
    degradation_events: degradationEvents.length,
    threshold_breaches: thresholdBreaches.slice(-50) // Last 50 breaches
  };
}

/**
 * Calculate Pearson correlation coefficient
 */
function calculatePearsonCorrelation(x: number[], y: number[]): number {
  const n = Math.min(x.length, y.length);
  if (n < 2) return 0;
  
  const sumX = x.reduce((a, b) => a + b, 0);
  const sumY = y.reduce((a, b) => a + b, 0);
  const sumXY = x.reduce((sum, xi, i) => sum + xi * y[i], 0);
  const sumX2 = x.reduce((sum, xi) => sum + xi * xi, 0);
  const sumY2 = y.reduce((sum, yi) => sum + yi * yi, 0);
  
  const numerator = n * sumXY - sumX * sumY;
  const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
  
  return denominator === 0 ? 0 : numerator / denominator;
}

/**
 * Calculate basic statistics for an array of numbers
 */
function calculateStats(values: number[]) {
  if (values.length === 0) return { min: 0, max: 0, avg: 0, p95: 0 };
  
  const sorted = [...values].sort((a, b) => a - b);
  const sum = values.reduce((a, b) => a + b, 0);
  
  return {
    min: Math.round(sorted[0] * 1000) / 1000,
    max: Math.round(sorted[sorted.length - 1] * 1000) / 1000,
    avg: Math.round((sum / values.length) * 1000) / 1000,
    p95: Math.round(sorted[Math.floor(sorted.length * 0.95)] * 1000) / 1000
  };
}

/**
 * Generate auto-tuning recommendations based on correlation analysis
 */
function generateRecommendations(
  metrics: GuardianMetrics[],
  breaches: CorrelationAnalysis['threshold_breaches'],
  correlation: number
): string[] {
  const recommendations: string[] = [];
  
  if (metrics.length === 0) {
    recommendations.push('Insufficient data for analysis');
    return recommendations;
  }
  
  const recentMetrics = metrics.slice(-10);
  const avgRam = recentMetrics.reduce((sum, m) => sum + m.ram_pct, 0) / recentMetrics.length;
  const maxRam = Math.max(...recentMetrics.map(m => m.ram_pct));
  
  // RAM-based recommendations
  if (maxRam > 0.90) {
    recommendations.push('Consider lowering RAM thresholds - system reaching 90%+ usage');
  }
  
  if (avgRam > 0.75) {
    recommendations.push('Average RAM usage high - consider more aggressive early intervention');
  }
  
  // Correlation-based recommendations
  if (Math.abs(correlation) > 0.7) {
    if (correlation > 0) {
      recommendations.push('Strong positive RAM-performance correlation detected - optimize memory management');
    } else {
      recommendations.push('Strong negative RAM-performance correlation detected - investigate system bottlenecks');
    }
  }
  
  // Breach frequency recommendations  
  const recentBreaches = breaches.filter(b => b.timestamp > Date.now() / 1000 - 3600); // Last hour
  if (recentBreaches.length > 10) {
    recommendations.push('Frequent threshold breaches - consider lowering soft thresholds for earlier intervention');
  }
  
  // Emergency mode recommendations
  const emergencyEvents = recentMetrics.filter(m => m.emergency_mode).length;
  if (emergencyEvents > 0) {
    recommendations.push('Emergency mode triggered - review system capacity and consider scaling');
  }
  
  if (recommendations.length === 0) {
    recommendations.push('System performing within normal parameters');
  }
  
  return recommendations;
}

/**
 * Extract alert information from Guardian logs
 */
export function extractAlerts(entries: GuardianLogEntry[]): AlertInfo[] {
  return entries
    .filter(entry => entry.event_type === 'alert')
    .map((entry, index) => ({
      id: `alert_${entry.timestamp}_${index}`,
      type: entry.data.alert_type || 'unknown',
      level: entry.level,
      message: entry.data.message || 'Unknown alert',
      timestamp: entry.timestamp,
      details: entry.data.details || {},
      resolved: false // Could be enhanced to track resolution
    }));
}

/**
 * Cache management for expensive operations with tiered TTL
 */
interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
  hitCount: number;
  lastAccessed: number;
}

interface CacheConfig {
  ttlSeconds: number;
  maxEntries: number;
  hitCountBonus: number; // Extra TTL for frequently accessed items
}

class MetricsCache {
  private cache = new Map<string, CacheEntry<any>>();
  private readonly configs: Map<string, CacheConfig> = new Map();
  
  constructor() {
    // Configure different TTLs for different endpoint types
    this.configs.set('summary', { 
      ttlSeconds: 30, 
      maxEntries: 50, 
      hitCountBonus: 15 
    });
    
    this.configs.set('correlation', { 
      ttlSeconds: 60, 
      maxEntries: 100, 
      hitCountBonus: 30 
    });
    
    this.configs.set('alerts', { 
      ttlSeconds: 15, 
      maxEntries: 200, 
      hitCountBonus: 10 
    });
    
    this.configs.set('history', { 
      ttlSeconds: 120, 
      maxEntries: 150, 
      hitCountBonus: 60 
    });
    
    this.configs.set('analysis', { 
      ttlSeconds: 300, 
      maxEntries: 50, 
      hitCountBonus: 180 
    });
    
    // Default config
    this.configs.set('default', { 
      ttlSeconds: 30, 
      maxEntries: 100, 
      hitCountBonus: 15 
    });
    
    // Cleanup interval - every 2 minutes
    setInterval(() => this.cleanup(), 2 * 60 * 1000);
  }

  get<T>(key: string): T | null {
    const entry = this.cache.get(key);
    if (!entry || Date.now() > entry.expiresAt) {
      this.cache.delete(key);
      return null;
    }
    
    // Update hit count and last accessed
    entry.hitCount++;
    entry.lastAccessed = Date.now();
    
    return entry.data;
  }

  set<T>(key: string, data: T, category: string = 'default'): void {
    const config = this.configs.get(category) || this.configs.get('default')!;
    
    // Check if we need to evict entries
    if (this.cache.size >= config.maxEntries) {
      this.evictLeastRecentlyUsed(config.maxEntries * 0.8); // Remove 20% of entries
    }
    
    const now = Date.now();
    this.cache.set(key, {
      data,
      timestamp: now,
      expiresAt: now + (config.ttlSeconds * 1000),
      hitCount: 0,
      lastAccessed: now
    });
  }

  clear(category?: string): void {
    if (category) {
      // Clear only entries for a specific category
      const keysToDelete = Array.from(this.cache.keys()).filter(key => key.includes(category));
      keysToDelete.forEach(key => this.cache.delete(key));
    } else {
      this.cache.clear();
    }
  }

  private cleanup(): void {
    const now = Date.now();
    for (const [key, entry] of this.cache.entries()) {
      if (now >= entry.expiresAt) {
        this.cache.delete(key);
      }
    }
  }

  private evictLeastRecentlyUsed(targetSize: number): void {
    const entries = Array.from(this.cache.entries())
      .sort(([, a], [, b]) => {
        // Sort by last accessed time and hit count
        const scoreA = a.lastAccessed + (a.hitCount * 60000); // 1 min per hit
        const scoreB = b.lastAccessed + (b.hitCount * 60000);
        return scoreA - scoreB;
      });
    
    // Remove least recently used entries
    const toRemove = entries.slice(0, this.cache.size - targetSize);
    toRemove.forEach(([key]) => this.cache.delete(key));
  }

  getStats(): {
    totalEntries: number;
    hitRates: Record<string, number>;
    oldestEntry: number;
    newestEntry: number;
  } {
    const now = Date.now();
    let oldestEntry = now;
    let newestEntry = 0;
    const categoryHits: Record<string, { total: number; hits: number }> = {};
    
    for (const [key, entry] of this.cache.entries()) {
      oldestEntry = Math.min(oldestEntry, entry.timestamp);
      newestEntry = Math.max(newestEntry, entry.timestamp);
      
      // Determine category from key
      const category = key.split('_')[0] || 'unknown';
      if (!categoryHits[category]) {
        categoryHits[category] = { total: 0, hits: 0 };
      }
      categoryHits[category].total++;
      categoryHits[category].hits += entry.hitCount;
    }
    
    const hitRates: Record<string, number> = {};
    for (const [category, stats] of Object.entries(categoryHits)) {
      hitRates[category] = stats.total > 0 ? stats.hits / stats.total : 0;
    }
    
    return {
      totalEntries: this.cache.size,
      hitRates,
      oldestEntry: this.cache.size > 0 ? oldestEntry : 0,
      newestEntry: this.cache.size > 0 ? newestEntry : 0
    };
  }
}

export const metricsCache = new MetricsCache();

/**
 * Rate limiting configuration for Guardian metrics endpoints
 */
export const GUARDIAN_RATE_LIMITS = {
  '/api/metrics/guardian/summary': {
    windowMs: 60 * 1000, // 1 minute
    maxRequests: 30 // 0.5 req/second
  },
  '/api/metrics/guardian/correlation': {
    windowMs: 60 * 1000, // 1 minute  
    maxRequests: 20 // Expensive operation
  },
  '/api/metrics/guardian/alerts': {
    windowMs: 60 * 1000, // 1 minute
    maxRequests: 60 // More frequent polling needed
  },
  '/api/metrics/guardian/history': {
    windowMs: 60 * 1000, // 1 minute
    maxRequests: 15 // Very expensive operation
  },
  '/api/metrics/guardian/analyze': {
    windowMs: 5 * 60 * 1000, // 5 minutes
    maxRequests: 10 // Most expensive operation
  }
};

/**
 * Enhanced error handling with context
 */
export class GuardianMetricsError extends Error {
  public readonly code: string;
  public readonly context: Record<string, any>;
  public readonly timestamp: number;

  constructor(message: string, code: string, context: Record<string, any> = {}) {
    super(message);
    this.name = 'GuardianMetricsError';
    this.code = code;
    this.context = context;
    this.timestamp = Date.now();
  }

  toJSON() {
    return {
      error: this.message,
      code: this.code,
      context: this.context,
      timestamp: this.timestamp
    };
  }
}

/**
 * Metrics collection for API performance monitoring
 */
interface APIMetric {
  endpoint: string;
  method: string;
  duration_ms: number;
  status_code: number;
  cache_hit: boolean;
  timestamp: number;
  error?: string;
}

class APIMetricsCollector {
  private metrics: APIMetric[] = [];
  private readonly MAX_METRICS = 1000;

  recordMetric(metric: Omit<APIMetric, 'timestamp'>) {
    this.metrics.push({
      ...metric,
      timestamp: Date.now()
    });

    // Keep only recent metrics
    if (this.metrics.length > this.MAX_METRICS) {
      this.metrics = this.metrics.slice(-this.MAX_METRICS * 0.8); // Keep 80%
    }
  }

  getMetrics(hours: number = 1): APIMetric[] {
    const cutoff = Date.now() - (hours * 60 * 60 * 1000);
    return this.metrics.filter(m => m.timestamp > cutoff);
  }

  getPerformanceStats(hours: number = 1) {
    const recentMetrics = this.getMetrics(hours);
    
    if (recentMetrics.length === 0) {
      return { total_requests: 0, avg_duration: 0, cache_hit_rate: 0, error_rate: 0 };
    }

    const totalRequests = recentMetrics.length;
    const avgDuration = recentMetrics.reduce((sum, m) => sum + m.duration_ms, 0) / totalRequests;
    const cacheHits = recentMetrics.filter(m => m.cache_hit).length;
    const cacheHitRate = cacheHits / totalRequests;
    const errors = recentMetrics.filter(m => m.status_code >= 400).length;
    const errorRate = errors / totalRequests;

    const endpointStats = recentMetrics.reduce((acc, metric) => {
      if (!acc[metric.endpoint]) {
        acc[metric.endpoint] = { count: 0, total_duration: 0, errors: 0 };
      }
      acc[metric.endpoint].count++;
      acc[metric.endpoint].total_duration += metric.duration_ms;
      if (metric.status_code >= 400) acc[metric.endpoint].errors++;
      return acc;
    }, {} as Record<string, { count: number; total_duration: number; errors: number }>);

    return {
      total_requests: totalRequests,
      avg_duration: Math.round(avgDuration),
      cache_hit_rate: Math.round(cacheHitRate * 100) / 100,
      error_rate: Math.round(errorRate * 100) / 100,
      endpoint_breakdown: Object.entries(endpointStats).map(([endpoint, stats]) => ({
        endpoint,
        requests: stats.count,
        avg_duration: Math.round(stats.total_duration / stats.count),
        error_rate: Math.round((stats.errors / stats.count) * 100) / 100
      }))
    };
  }
}

export const apiMetricsCollector = new APIMetricsCollector();

/**
 * Utility function to measure API performance
 */
export function withPerformanceTracking<T>(
  endpoint: string,
  method: string,
  operation: () => Promise<T>,
  cacheHit: boolean = false
): Promise<T> {
  const startTime = Date.now();
  
  return operation()
    .then(result => {
      apiMetricsCollector.recordMetric({
        endpoint,
        method,
        duration_ms: Date.now() - startTime,
        status_code: 200,
        cache_hit: cacheHit
      });
      return result;
    })
    .catch(error => {
      apiMetricsCollector.recordMetric({
        endpoint,
        method,
        duration_ms: Date.now() - startTime,
        status_code: error.status || 500,
        cache_hit: cacheHit,
        error: error.message || 'Unknown error'
      });
      throw error;
    });
}