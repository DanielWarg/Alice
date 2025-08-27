import { EventEmitter } from 'eventemitter3';
import { 
  LatencyMeasurement,
  PerformanceMetrics,
  VoiceProviderEvents 
} from '../types';

/**
 * Latency tracking and measurement for voice operations
 */
export class LatencyTracker extends EventEmitter<VoiceProviderEvents> {
  private measurements: Map<string, LatencyMeasurement[]> = new Map();
  private pendingRequests: Map<string, number> = new Map();
  private sessionId: string | null = null;
  private enabled: boolean = true;

  constructor(
    private targetLatency: number = 500,
    private maxMeasurements: number = 1000
  ) {
    super();
  }

  /**
   * Start tracking a new request
   */
  startTracking(requestId: string, type: 'asr' | 'tts' | 'endToEnd'): void {
    if (!this.enabled) return;

    const timestamp = Date.now();
    this.pendingRequests.set(`${type}_${requestId}`, timestamp);
  }

  /**
   * End tracking for a request and record measurement
   */
  endTracking(requestId: string, type: 'asr' | 'tts' | 'endToEnd'): LatencyMeasurement | null {
    if (!this.enabled) return null;

    const key = `${type}_${requestId}`;
    const startTime = this.pendingRequests.get(key);
    
    if (!startTime) {
      console.warn(`[LatencyTracker] No start time found for request: ${key}`);
      return null;
    }

    const endTime = Date.now();
    const latency = endTime - startTime;

    const measurement: LatencyMeasurement = {
      type,
      value: latency,
      timestamp: endTime,
      sessionId: this.sessionId || undefined
    };

    // Store measurement
    this.storeMeasurement(measurement);

    // Clean up pending request
    this.pendingRequests.delete(key);

    // Emit latency update
    this.emit('latency_update', latency, type);

    // Check if latency exceeds target
    if (latency > this.targetLatency) {
      console.warn(`[LatencyTracker] High latency detected: ${latency}ms (target: ${this.targetLatency}ms) for ${type}`);
    }

    return measurement;
  }

  /**
   * Record a direct latency measurement
   */
  recordLatency(type: 'asr' | 'tts' | 'endToEnd', latency: number): LatencyMeasurement {
    const measurement: LatencyMeasurement = {
      type,
      value: latency,
      timestamp: Date.now(),
      sessionId: this.sessionId || undefined
    };

    this.storeMeasurement(measurement);
    this.emit('latency_update', latency, type);

    return measurement;
  }

  /**
   * Get current latency statistics
   */
  getLatencyStats(type?: 'asr' | 'tts' | 'endToEnd'): LatencyStats {
    let allMeasurements: LatencyMeasurement[] = [];

    if (type) {
      const typeMeasurements = this.measurements.get(type);
      if (typeMeasurements) {
        allMeasurements = [...typeMeasurements];
      }
    } else {
      // Combine all measurements
      this.measurements.forEach(measurements => {
        allMeasurements.push(...measurements);
      });
    }

    if (allMeasurements.length === 0) {
      return {
        count: 0,
        average: 0,
        median: 0,
        min: 0,
        max: 0,
        p95: 0,
        p99: 0,
        targetExceeded: 0,
        targetExceededPercentage: 0
      };
    }

    const latencies = allMeasurements.map(m => m.value).sort((a, b) => a - b);
    const count = latencies.length;
    const sum = latencies.reduce((acc, val) => acc + val, 0);
    const average = sum / count;
    const median = this.calculatePercentile(latencies, 50);
    const min = latencies[0]!;
    const max = latencies[count - 1]!;
    const p95 = this.calculatePercentile(latencies, 95);
    const p99 = this.calculatePercentile(latencies, 99);
    const targetExceeded = latencies.filter(l => l > this.targetLatency).length;
    const targetExceededPercentage = (targetExceeded / count) * 100;

    return {
      count,
      average,
      median,
      min,
      max,
      p95,
      p99,
      targetExceeded,
      targetExceededPercentage
    };
  }

  /**
   * Get recent measurements
   */
  getRecentMeasurements(type?: 'asr' | 'tts' | 'endToEnd', limit: number = 50): LatencyMeasurement[] {
    let allMeasurements: LatencyMeasurement[] = [];

    if (type) {
      const typeMeasurements = this.measurements.get(type);
      if (typeMeasurements) {
        allMeasurements = [...typeMeasurements];
      }
    } else {
      // Combine all measurements
      this.measurements.forEach(measurements => {
        allMeasurements.push(...measurements);
      });
    }

    return allMeasurements
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, limit);
  }

  /**
   * Get measurements for time range
   */
  getMeasurementsInRange(
    startTime: number, 
    endTime: number, 
    type?: 'asr' | 'tts' | 'endToEnd'
  ): LatencyMeasurement[] {
    let allMeasurements: LatencyMeasurement[] = [];

    if (type) {
      const typeMeasurements = this.measurements.get(type);
      if (typeMeasurements) {
        allMeasurements = [...typeMeasurements];
      }
    } else {
      this.measurements.forEach(measurements => {
        allMeasurements.push(...measurements);
      });
    }

    return allMeasurements.filter(m => 
      m.timestamp >= startTime && m.timestamp <= endTime
    );
  }

  /**
   * Calculate average latency over time window
   */
  getAverageLatency(windowMs: number = 60000, type?: 'asr' | 'tts' | 'endToEnd'): number {
    const now = Date.now();
    const measurements = this.getMeasurementsInRange(now - windowMs, now, type);
    
    if (measurements.length === 0) return 0;
    
    const sum = measurements.reduce((acc, m) => acc + m.value, 0);
    return sum / measurements.length;
  }

  /**
   * Check if latency is within target
   */
  isLatencyWithinTarget(type?: 'asr' | 'tts' | 'endToEnd'): boolean {
    const recentLatency = this.getAverageLatency(10000, type); // Last 10 seconds
    return recentLatency <= this.targetLatency;
  }

  /**
   * Set session ID for tracking
   */
  setSessionId(sessionId: string): void {
    this.sessionId = sessionId;
  }

  /**
   * Clear session ID
   */
  clearSessionId(): void {
    this.sessionId = null;
  }

  /**
   * Enable or disable tracking
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    if (!enabled) {
      this.clearPendingRequests();
    }
  }

  /**
   * Check if tracking is enabled
   */
  isEnabled(): boolean {
    return this.enabled;
  }

  /**
   * Set target latency
   */
  setTargetLatency(targetMs: number): void {
    this.targetLatency = targetMs;
  }

  /**
   * Get target latency
   */
  getTargetLatency(): number {
    return this.targetLatency;
  }

  /**
   * Clear all measurements
   */
  clearMeasurements(): void {
    this.measurements.clear();
    this.clearPendingRequests();
  }

  /**
   * Clear pending requests
   */
  clearPendingRequests(): void {
    this.pendingRequests.clear();
  }

  /**
   * Get performance summary
   */
  getPerformanceSummary(): PerformanceSummary {
    const asrStats = this.getLatencyStats('asr');
    const ttsStats = this.getLatencyStats('tts');
    const endToEndStats = this.getLatencyStats('endToEnd');
    
    return {
      asr: asrStats,
      tts: ttsStats,
      endToEnd: endToEndStats,
      overall: {
        totalMeasurements: asrStats.count + ttsStats.count + endToEndStats.count,
        averageLatency: (asrStats.average + ttsStats.average + endToEndStats.average) / 3,
        targetLatency: this.targetLatency,
        withinTarget: this.isLatencyWithinTarget()
      }
    };
  }

  /**
   * Export measurements to JSON
   */
  exportMeasurements(): string {
    const data = {
      sessionId: this.sessionId,
      targetLatency: this.targetLatency,
      measurements: Object.fromEntries(this.measurements),
      timestamp: Date.now()
    };
    
    return JSON.stringify(data, null, 2);
  }

  /**
   * Import measurements from JSON
   */
  importMeasurements(json: string): void {
    try {
      const data = JSON.parse(json);
      
      if (data.measurements) {
        this.measurements = new Map(Object.entries(data.measurements));
      }
      
      if (data.targetLatency) {
        this.targetLatency = data.targetLatency;
      }
      
      if (data.sessionId) {
        this.sessionId = data.sessionId;
      }
    } catch (error) {
      console.error('[LatencyTracker] Failed to import measurements:', error);
    }
  }

  /**
   * Store a measurement with cleanup
   */
  private storeMeasurement(measurement: LatencyMeasurement): void {
    const typeKey = measurement.type;
    
    if (!this.measurements.has(typeKey)) {
      this.measurements.set(typeKey, []);
    }
    
    const typeMeasurements = this.measurements.get(typeKey)!;
    typeMeasurements.push(measurement);
    
    // Keep only recent measurements
    if (typeMeasurements.length > this.maxMeasurements) {
      typeMeasurements.splice(0, typeMeasurements.length - this.maxMeasurements);
    }
  }

  /**
   * Calculate percentile from sorted array
   */
  private calculatePercentile(sortedValues: number[], percentile: number): number {
    if (sortedValues.length === 0) return 0;
    
    const index = (percentile / 100) * (sortedValues.length - 1);
    const lower = Math.floor(index);
    const upper = Math.ceil(index);
    
    if (lower === upper) {
      return sortedValues[lower]!;
    }
    
    const weight = index - lower;
    return sortedValues[lower]! * (1 - weight) + sortedValues[upper]! * weight;
  }
}

/**
 * Latency statistics interface
 */
export interface LatencyStats {
  count: number;
  average: number;
  median: number;
  min: number;
  max: number;
  p95: number;
  p99: number;
  targetExceeded: number;
  targetExceededPercentage: number;
}

/**
 * Performance summary interface
 */
export interface PerformanceSummary {
  asr: LatencyStats;
  tts: LatencyStats;
  endToEnd: LatencyStats;
  overall: {
    totalMeasurements: number;
    averageLatency: number;
    targetLatency: number;
    withinTarget: boolean;
  };
}

/**
 * Create a latency tracker with default settings
 */
export function createLatencyTracker(targetLatency: number = 500): LatencyTracker {
  return new LatencyTracker(targetLatency);
}

/**
 * Latency monitoring utility functions
 */
export class LatencyMonitor {
  /**
   * Monitor a function and track its execution time
   */
  static async monitor<T>(
    tracker: LatencyTracker,
    requestId: string,
    type: 'asr' | 'tts' | 'endToEnd',
    fn: () => Promise<T>
  ): Promise<T> {
    tracker.startTracking(requestId, type);
    
    try {
      const result = await fn();
      tracker.endTracking(requestId, type);
      return result;
    } catch (error) {
      tracker.endTracking(requestId, type);
      throw error;
    }
  }

  /**
   * Create a monitoring wrapper for a function
   */
  static createWrapper<T extends any[], R>(
    tracker: LatencyTracker,
    type: 'asr' | 'tts' | 'endToEnd',
    fn: (...args: T) => Promise<R>
  ): (...args: T) => Promise<R> {
    return async (...args: T): Promise<R> => {
      const requestId = `${type}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      return LatencyMonitor.monitor(tracker, requestId, type, () => fn(...args));
    };
  }

  /**
   * Check latency health for all types
   */
  static checkLatencyHealth(tracker: LatencyTracker): {
    healthy: boolean;
    issues: string[];
  } {
    const issues: string[] = [];
    const targetLatency = tracker.getTargetLatency();

    // Check each latency type
    const types: Array<'asr' | 'tts' | 'endToEnd'> = ['asr', 'tts', 'endToEnd'];
    
    for (const type of types) {
      const stats = tracker.getLatencyStats(type);
      
      if (stats.count === 0) continue;
      
      if (stats.average > targetLatency) {
        issues.push(`${type} average latency (${stats.average.toFixed(1)}ms) exceeds target (${targetLatency}ms)`);
      }
      
      if (stats.p95 > targetLatency * 1.5) {
        issues.push(`${type} P95 latency (${stats.p95.toFixed(1)}ms) significantly exceeds target`);
      }
      
      if (stats.targetExceededPercentage > 20) {
        issues.push(`${type} latency exceeds target ${stats.targetExceededPercentage.toFixed(1)}% of the time`);
      }
    }

    return {
      healthy: issues.length === 0,
      issues
    };
  }
}