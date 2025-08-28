/**
 * Latency Tracker - Real Performance Measurement
 * Measures and tracks voice pipeline latencies with percentile calculations
 */
export class LatencyTracker {
  private measurements = new Map<string, number>();
  private history = new Map<string, number[]>();
  private startTimes = new Map<string, number>();
  
  start(name: string): string {
    const timestamp = performance.now();
    this.startTimes.set(name, timestamp);
    return name;
  }
  
  end(name: string): number {
    const endTime = performance.now();
    const startTime = this.startTimes.get(name);
    
    if (!startTime) {
      console.warn(`No start time found for latency measurement: ${name}`);
      return 0;
    }
    
    const duration = endTime - startTime;
    this.measurements.set(name, duration);
    
    // Add to history for percentile calculations
    if (!this.history.has(name)) {
      this.history.set(name, []);
    }
    const history = this.history.get(name)!;
    history.push(duration);
    
    // Keep only last 100 measurements for percentiles
    if (history.length > 100) {
      history.shift();
    }
    
    this.startTimes.delete(name);
    return duration;
  }
  
  hasStarted(name: string): boolean {
    return this.startTimes.has(name);
  }
  
  getLatency(name: string): number | undefined {
    return this.measurements.get(name);
  }
  
  getMetrics(): Record<string, number> {
    const metrics: Record<string, number> = {};
    
    for (const [name, value] of this.measurements.entries()) {
      metrics[`${name}_ms`] = Math.round(value);
    }
    
    return metrics;
  }
  
  getPercentiles(name: string): { p50: number; p95: number; p99: number } {
    const history = this.history.get(name);
    if (!history || history.length === 0) {
      return { p50: 0, p95: 0, p99: 0 };
    }
    
    const sorted = [...history].sort((a, b) => a - b);
    const len = sorted.length;
    
    return {
      p50: sorted[Math.floor(len * 0.5)],
      p95: sorted[Math.floor(len * 0.95)],
      p99: sorted[Math.floor(len * 0.99)]
    };
  }
  
  getAllPercentiles(): Record<string, { p50: number; p95: number; p99: number }> {
    const result: Record<string, { p50: number; p95: number; p99: number }> = {};
    
    for (const name of this.history.keys()) {
      result[name] = this.getPercentiles(name);
    }
    
    return result;
  }
  
  reset(): void {
    this.measurements.clear();
    this.startTimes.clear();
    // Keep history for trending analysis
  }
  
  resetHistory(): void {
    this.history.clear();
    this.reset();
  }
  
  getSummary(): {
    current: Record<string, number>;
    percentiles: Record<string, { p50: number; p95: number; p99: number }>;
    activeMeasurements: string[];
  } {
    return {
      current: this.getMetrics(),
      percentiles: this.getAllPercentiles(),
      activeMeasurements: Array.from(this.startTimes.keys())
    };
  }
}