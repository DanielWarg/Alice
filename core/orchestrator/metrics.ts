/**
 * Metrics System - NDJSON Logging and P50/P95 Aggregation
 * 
 * Comprehensive metrics collection for Alice's orchestrator.
 * Provides real-time performance monitoring and historical analysis.
 */

import fs from "fs";
import path from "path";

// Metrics configuration
const METRICS_CONFIG = {
  logFile: "metrics.ndjson",
  maxFileSize: 100 * 1024 * 1024, // 100MB
  rotationInterval: 24 * 60 * 60 * 1000, // 24 hours
  aggregationWindow: 5 * 60 * 1000, // 5 minutes
  maxHistorySize: 10000 // Keep last 10k metrics
};

// Metrics storage
interface MetricRecord {
  timestamp: number;
  event: string;
  [key: string]: any;
}

interface AggregatedMetrics {
  timestamp: number;
  window: number;
  metrics: Record<string, MetricAggregation>;
}

interface MetricAggregation {
  count: number;
  sum: number;
  min: number;
  max: number;
  p50: number;
  p95: number;
  p99: number;
  values: number[];
}

class MetricsManager {
  private logStream: fs.WriteStream | null = null;
  private metricsBuffer: MetricRecord[] = [];
  private aggregations: Map<string, MetricAggregation> = new Map();
  private lastRotation: number = Date.now();
  private lastAggregation: number = Date.now();

  constructor() {
    this.initializeLogFile();
    this.startPeriodicTasks();
  }

  /**
   * Initialize log file
   */
  private initializeLogFile(): void {
    try {
      // Create logs directory if it doesn't exist
      const logsDir = path.dirname(METRICS_CONFIG.logFile);
      if (!fs.existsSync(logsDir)) {
        fs.mkdirSync(logsDir, { recursive: true });
      }

      // Open write stream
      this.logStream = fs.createWriteStream(METRICS_CONFIG.logFile, {
        flags: "a",
        encoding: "utf8"
      });

      console.log(`📊 Metrics logging initialized: ${METRICS_CONFIG.logFile}`);
    } catch (error) {
      console.error("❌ Failed to initialize metrics logging:", error);
    }
  }

  /**
   * Start periodic tasks
   */
  private startPeriodicTasks(): void {
    // File rotation
    setInterval(() => {
      this.rotateLogFile();
    }, METRICS_CONFIG.rotationInterval);

    // Metrics aggregation
    setInterval(() => {
      this.aggregateMetrics();
    }, METRICS_CONFIG.aggregationWindow);

    // Buffer flush
    setInterval(() => {
      this.flushBuffer();
    }, 1000); // Every second
  }

  /**
   * Log metric to NDJSON file
   */
  logMetric(metric: MetricRecord): void {
    if (!this.logStream) {
      console.warn("⚠️ Metrics logging not initialized");
      return;
    }

    // Add timestamp if not present
    if (!metric.timestamp) {
      metric.timestamp = Date.now();
    }

    // Add to buffer
    this.metricsBuffer.push(metric);

    // Flush if buffer is large
    if (this.metricsBuffer.length > 100) {
      this.flushBuffer();
    }

    // Update aggregations
    this.updateAggregation(metric);
  }

  /**
   * Flush metrics buffer to file
   */
  private flushBuffer(): void {
    if (!this.logStream || this.metricsBuffer.length === 0) {
      return;
    }

    try {
      for (const metric of this.metricsBuffer) {
        const line = JSON.stringify(metric) + "\n";
        this.logStream.write(line);
      }
      
      this.metricsBuffer = [];
    } catch (error) {
      console.error("❌ Failed to flush metrics buffer:", error);
    }
  }

  /**
   * Update metric aggregation
   */
  private updateAggregation(metric: MetricRecord): void {
    const event = metric.event;
    
    if (!this.aggregations.has(event)) {
      this.aggregations.set(event, {
        count: 0,
        sum: 0,
        min: Infinity,
        max: -Infinity,
        p50: 0,
        p95: 0,
        p99: 0,
        values: []
      });
    }

    const agg = this.aggregations.get(event)!;
    
    // Extract numeric values from metric
    const numericValues = this.extractNumericValues(metric);
    
    for (const value of numericValues) {
      agg.count++;
      agg.sum += value;
      agg.min = Math.min(agg.min, value);
      agg.max = Math.max(agg.max, value);
      agg.values.push(value);
    }

    // Keep only recent values for percentile calculation
    if (agg.values.length > 1000) {
      agg.values = agg.values.slice(-1000);
    }
  }

  /**
   * Extract numeric values from metric object
   */
  private extractNumericValues(metric: MetricRecord): number[] {
    const values: number[] = [];
    
    for (const [key, value] of Object.entries(metric)) {
      if (typeof value === "number" && !isNaN(value)) {
        values.push(value);
      }
    }
    
    return values;
  }

  /**
   * Calculate percentiles
   */
  private calculatePercentiles(values: number[]): { p50: number; p95: number; p99: number } {
    if (values.length === 0) {
      return { p50: 0, p95: 0, p99: 0 };
    }

    const sorted = [...values].sort((a, b) => a - b);
    
    return {
      p50: this.getPercentile(sorted, 50),
      p95: this.getPercentile(sorted, 95),
      p99: this.getPercentile(sorted, 99)
    };
  }

  /**
   * Get percentile value
   */
  private getPercentile(sorted: number[], percentile: number): number {
    const index = Math.ceil((percentile / 100) * sorted.length) - 1;
    return sorted[Math.max(0, index)];
  }

  /**
   * Aggregate metrics for current window
   */
  private aggregateMetrics(): void {
    const now = Date.now();
    const window = METRICS_CONFIG.aggregationWindow;

    for (const [event, agg] of this.aggregations.entries()) {
      if (agg.count === 0) continue;

      // Calculate percentiles
      const percentiles = this.calculatePercentiles(agg.values);
      agg.p50 = percentiles.p50;
      agg.p95 = percentiles.p95;
      agg.p99 = percentiles.p99;

      // Log aggregated metrics
      this.logMetric({
        timestamp: now,
        event: "metrics_aggregated",
        metric: event,
        window,
        aggregation: {
          count: agg.count,
          sum: agg.sum,
          min: agg.min,
          max: agg.max,
          p50: agg.p50,
          p95: agg.p95,
          p99: agg.p99,
          avg: agg.sum / agg.count
        }
      });

      // Reset aggregation
      agg.count = 0;
      agg.sum = 0;
      agg.min = Infinity;
      agg.max = -Infinity;
      agg.values = [];
    }

    this.lastAggregation = now;
  }

  /**
   * Rotate log file
   */
  private rotateLogFile(): void {
    if (!this.logStream) return;

    try {
      // Close current stream
      this.logStream.end();
      
      // Rename current file
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      const rotatedFile = `${METRICS_CONFIG.logFile}.${timestamp}`;
      fs.renameSync(METRICS_CONFIG.logFile, rotatedFile);
      
      // Open new stream
      this.logStream = fs.createWriteStream(METRICS_CONFIG.logFile, {
        flags: "a",
        encoding: "utf8"
      });
      
      console.log(`🔄 Metrics log rotated: ${rotatedFile}`);
      this.lastRotation = Date.now();
    } catch (error) {
      console.error("❌ Failed to rotate metrics log:", error);
    }
  }

  /**
   * Get current metrics summary
   */
  getMetricsSummary(): {
    totalMetrics: number;
    activeAggregations: number;
    lastAggregation: number;
    logFileSize: number;
  } {
    let logFileSize = 0;
    try {
      if (fs.existsSync(METRICS_CONFIG.logFile)) {
        const stats = fs.statSync(METRICS_CONFIG.logFile);
        logFileSize = stats.size;
      }
    } catch (error) {
      console.error("❌ Failed to get log file size:", error);
    }

    return {
      totalMetrics: this.metricsBuffer.length,
      activeAggregations: this.aggregations.size,
      lastAggregation: this.lastAggregation,
      logFileSize
    };
  }

  /**
   * Get specific metric aggregation
   */
  getMetricAggregation(event: string): MetricAggregation | undefined {
    return this.aggregations.get(event);
  }

  /**
   * Get all metric aggregations
   */
  getAllAggregations(): Map<string, MetricAggregation> {
    return new Map(this.aggregations);
  }

  /**
   * Clean up resources
   */
  cleanup(): void {
    if (this.logStream) {
      this.logStream.end();
      this.logStream = null;
    }
  }
}

// Create singleton metrics manager
const metricsManager = new MetricsManager();

/**
 * Log metric to NDJSON file (main export function)
 */
export function logNDJSON(metric: any): void {
  metricsManager.logMetric(metric);
}

/**
 * Get metrics summary
 */
export function getMetricsSummary() {
  return metricsManager.getMetricsSummary();
}

/**
 * Get metric aggregation
 */
export function getMetricAggregation(event: string) {
  return metricsManager.getMetricAggregation(event);
}

/**
 * Get all aggregations
 */
export function getAllAggregations() {
  return metricsManager.getAllAggregations();
}

/**
 * Performance measurement utilities
 */
export class PerformanceTimer {
  private startTime: number;
  private label: string;

  constructor(label: string) {
    this.startTime = Date.now();
    this.label = label;
  }

  /**
   * End timer and log metric
   */
  end(): number {
    const duration = Date.now() - this.startTime;
    
    logNDJSON({
      event: "performance_timer",
      timestamp: Date.now(),
      label: this.label,
      duration_ms: duration
    });
    
    return duration;
  }

  /**
   * End timer without logging
   */
  endSilent(): number {
    return Date.now() - this.startTime;
  }
}

/**
 * Create performance timer
 */
export function startTimer(label: string): PerformanceTimer {
  return new PerformanceTimer(label);
}

/**
 * Measure function execution time
 */
export function measureTime<T>(label: string, fn: () => T): T {
  const timer = startTimer(label);
  try {
    return fn();
  } finally {
    timer.end();
  }
}

/**
 * Measure async function execution time
 */
export async function measureTimeAsync<T>(label: string, fn: () => Promise<T>): Promise<T> {
  const timer = startTimer(label);
  try {
    return await fn();
  } finally {
    timer.end();
  }
}

// Cleanup on process exit
process.on("exit", () => {
  metricsManager.cleanup();
});

process.on("SIGINT", () => {
  metricsManager.cleanup();
  process.exit(0);
});

process.on("SIGTERM", () => {
  metricsManager.cleanup();
  process.exit(0);
});

export default metricsManager;
