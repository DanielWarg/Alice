/**
 * Voice Pipeline Metrics Logger
 * Real-time latency tracking and NDJSON telemetry
 */

import * as fs from 'fs';
import * as path from 'path';
import { VoiceMetrics } from '../../types/events';

interface PerformanceStats {
  p50: number;
  p95: number;
  p99: number;
  avg: number;
  min: number;
  max: number;
  count: number;
}

interface MetricsSummary {
  totalSessions: number;
  activeSessions: number;
  turnsCompleted: number;
  
  // Latency metrics
  first_partial_ms: PerformanceStats;
  ttft_ms: PerformanceStats;
  tts_first_chunk_ms: PerformanceStats;
  total_latency_ms: PerformanceStats;
  barge_in_cut_ms: PerformanceStats;
  
  // Route distribution
  routeDistribution: Record<string, number>;
  
  // Quality metrics
  privacyLeakAttempts: number;
  targetAchievementRate: number; // % of turns meeting <500ms target
  
  // Timestamp
  generatedAt: number;
}

export class MetricsLogger {
  private metricsLog: VoiceMetrics[] = [];
  private logFilePath: string;
  private sessionCount: number = 0;
  private maxLogSize: number = 10000; // Keep last 10k metrics

  // Real-time performance tracking
  private recentMetrics: VoiceMetrics[] = [];
  private recentWindow: number = 100; // Last 100 turns for real-time stats

  constructor(logDir: string = 'logs') {
    // Ensure log directory exists
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    this.logFilePath = path.join(logDir, `voice-metrics-${timestamp}.ndjson`);
    
    console.log(`📊 Metrics logger initialized: ${this.logFilePath}`);
  }

  public recordTurn(metrics: VoiceMetrics): void {
    const enhancedMetrics = {
      ...metrics,
      timestamp: Date.now(),
      target_achieved: (metrics.total_latency_ms || 0) <= 500,
      session_turn: this.metricsLog.filter(m => m.sessionId === metrics.sessionId).length + 1
    };

    // Add to logs
    this.metricsLog.push(enhancedMetrics);
    this.recentMetrics.push(enhancedMetrics);

    // Maintain log size limits
    if (this.metricsLog.length > this.maxLogSize) {
      this.metricsLog = this.metricsLog.slice(-this.maxLogSize);
    }

    if (this.recentMetrics.length > this.recentWindow) {
      this.recentMetrics = this.recentMetrics.slice(-this.recentWindow);
    }

    // Write to NDJSON log file
    this.writeToLog(enhancedMetrics);

    // Log performance summary for significant turns
    if (this.metricsLog.length % 50 === 0) {
      this.logPerformanceSummary();
    }
  }

  private writeToLog(metrics: any): void {
    try {
      const logLine = JSON.stringify(metrics) + '\\n';
      fs.appendFileSync(this.logFilePath, logLine);
    } catch (error) {
      console.error('❌ Failed to write metrics to log:', error);
    }
  }

  public getRealtimeStats(): MetricsSummary {
    const metrics = this.recentMetrics;
    
    if (metrics.length === 0) {
      return this.getEmptyStats();
    }

    return {
      totalSessions: new Set(this.metricsLog.map(m => m.sessionId)).size,
      activeSessions: new Set(metrics.map(m => m.sessionId)).size,
      turnsCompleted: this.metricsLog.length,
      
      first_partial_ms: this.calculateStats(metrics.map(m => m.first_partial_ms).filter(Boolean)),
      ttft_ms: this.calculateStats(metrics.map(m => m.ttft_ms).filter(Boolean)),
      tts_first_chunk_ms: this.calculateStats(metrics.map(m => m.tts_first_chunk_ms).filter(Boolean)),
      total_latency_ms: this.calculateStats(metrics.map(m => m.total_latency_ms).filter(Boolean)),
      barge_in_cut_ms: this.calculateStats(metrics.map(m => m.barge_in_cut_ms).filter(Boolean)),
      
      routeDistribution: this.calculateRouteDistribution(metrics),
      privacyLeakAttempts: metrics.reduce((sum, m) => sum + (m.privacy_leak_attempts || 0), 0),
      targetAchievementRate: this.calculateTargetAchievementRate(metrics),
      
      generatedAt: Date.now()
    };
  }

  public getAllTimeStats(): MetricsSummary {
    const metrics = this.metricsLog;
    
    if (metrics.length === 0) {
      return this.getEmptyStats();
    }

    return {
      totalSessions: new Set(metrics.map(m => m.sessionId)).size,
      activeSessions: new Set(this.recentMetrics.map(m => m.sessionId)).size,
      turnsCompleted: metrics.length,
      
      first_partial_ms: this.calculateStats(metrics.map(m => m.first_partial_ms).filter(Boolean)),
      ttft_ms: this.calculateStats(metrics.map(m => m.ttft_ms).filter(Boolean)),
      tts_first_chunk_ms: this.calculateStats(metrics.map(m => m.tts_first_chunk_ms).filter(Boolean)),
      total_latency_ms: this.calculateStats(metrics.map(m => m.total_latency_ms).filter(Boolean)),
      barge_in_cut_ms: this.calculateStats(metrics.map(m => m.barge_in_cut_ms).filter(Boolean)),
      
      routeDistribution: this.calculateRouteDistribution(metrics),
      privacyLeakAttempts: metrics.reduce((sum, m) => sum + (m.privacy_leak_attempts || 0), 0),
      targetAchievementRate: this.calculateTargetAchievementRate(metrics),
      
      generatedAt: Date.now()
    };
  }

  private calculateStats(values: number[]): PerformanceStats {
    if (values.length === 0) {
      return { p50: 0, p95: 0, p99: 0, avg: 0, min: 0, max: 0, count: 0 };
    }

    const sorted = [...values].sort((a, b) => a - b);
    const count = sorted.length;
    
    return {
      p50: this.percentile(sorted, 50),
      p95: this.percentile(sorted, 95),
      p99: this.percentile(sorted, 99),
      avg: sorted.reduce((sum, val) => sum + val, 0) / count,
      min: sorted[0],
      max: sorted[count - 1],
      count
    };
  }

  private percentile(sortedArray: number[], p: number): number {
    if (sortedArray.length === 0) return 0;
    
    const index = (p / 100) * (sortedArray.length - 1);
    const lower = Math.floor(index);
    const upper = Math.ceil(index);
    
    if (lower === upper) {
      return sortedArray[lower];
    }
    
    const weight = index - lower;
    return sortedArray[lower] * (1 - weight) + sortedArray[upper] * weight;
  }

  private calculateRouteDistribution(metrics: VoiceMetrics[]): Record<string, number> {
    const distribution: Record<string, number> = {};
    
    for (const metric of metrics) {
      const route = metric.route || 'unknown';
      distribution[route] = (distribution[route] || 0) + 1;
    }
    
    return distribution;
  }

  private calculateTargetAchievementRate(metrics: VoiceMetrics[]): number {
    const turnsWithLatency = metrics.filter(m => m.total_latency_ms !== undefined);
    if (turnsWithLatency.length === 0) return 0;
    
    const successfulTurns = turnsWithLatency.filter(m => (m.total_latency_ms || 0) <= 500);
    return (successfulTurns.length / turnsWithLatency.length) * 100;
  }

  private getEmptyStats(): MetricsSummary {
    const emptyPerf: PerformanceStats = { p50: 0, p95: 0, p99: 0, avg: 0, min: 0, max: 0, count: 0 };
    
    return {
      totalSessions: 0,
      activeSessions: 0,
      turnsCompleted: 0,
      first_partial_ms: emptyPerf,
      ttft_ms: emptyPerf,
      tts_first_chunk_ms: emptyPerf,
      total_latency_ms: emptyPerf,
      barge_in_cut_ms: emptyPerf,
      routeDistribution: {},
      privacyLeakAttempts: 0,
      targetAchievementRate: 0,
      generatedAt: Date.now()
    };
  }

  private logPerformanceSummary(): void {
    const stats = this.getRealtimeStats();
    
    console.log(`\\n📊 === Voice Pipeline Performance Summary ===`);
    console.log(`🎯 Turns completed: ${stats.turnsCompleted}`);
    console.log(`⚡ Target achievement rate: ${stats.targetAchievementRate.toFixed(1)}%`);
    console.log(`📈 Total latency p95: ${stats.total_latency_ms.p95.toFixed(1)}ms`);
    console.log(`🎙️ First partial p95: ${stats.first_partial_ms.p95.toFixed(1)}ms`);
    console.log(`🧠 TTFT p95: ${stats.ttft_ms.p95.toFixed(1)}ms`);
    console.log(`🔊 TTS first chunk p95: ${stats.tts_first_chunk_ms.p95.toFixed(1)}ms`);
    console.log(`🛡️ Privacy leak attempts: ${stats.privacyLeakAttempts}`);
    console.log(`🧭 Route distribution:`, stats.routeDistribution);
    console.log(`=======================================\\n`);
  }

  // Public API methods
  public getTotalSessions(): number {
    return new Set(this.metricsLog.map(m => m.sessionId)).size;
  }

  public getAverageLatency(): number {
    const latencies = this.metricsLog.map(m => m.total_latency_ms).filter(Boolean);
    if (latencies.length === 0) return 0;
    
    return latencies.reduce((sum, lat) => sum + lat, 0) / latencies.length;
  }

  public getPerformanceStats(): any {
    return {
      realtime: this.getRealtimeStats(),
      allTime: this.getAllTimeStats()
    };
  }

  public exportMetrics(format: 'json' | 'csv' = 'json'): string {
    if (format === 'csv') {
      return this.exportAsCSV();
    }
    
    return JSON.stringify(this.metricsLog, null, 2);
  }

  private exportAsCSV(): string {
    if (this.metricsLog.length === 0) {
      return 'No metrics to export';
    }

    const headers = Object.keys(this.metricsLog[0]).join(',');
    const rows = this.metricsLog.map(metric => 
      Object.values(metric).map(val => 
        typeof val === 'string' ? `"${val}"` : val
      ).join(',')
    );
    
    return [headers, ...rows].join('\\n');
  }

  public validateSLOs(): { passed: boolean; failures: string[] } {
    const stats = this.getAllTimeStats();
    const failures: string[] = [];

    // Check SLO targets
    if (stats.first_partial_ms.p95 > 300) {
      failures.push(`First partial p95: ${stats.first_partial_ms.p95.toFixed(1)}ms > 300ms`);
    }

    if (stats.ttft_ms.p95 > 300) {
      failures.push(`TTFT p95: ${stats.ttft_ms.p95.toFixed(1)}ms > 300ms`);
    }

    if (stats.tts_first_chunk_ms.p95 > 150) {
      failures.push(`TTS first chunk p95: ${stats.tts_first_chunk_ms.p95.toFixed(1)}ms > 150ms`);
    }

    if (stats.total_latency_ms.p95 > 500) {
      failures.push(`Total latency p95: ${stats.total_latency_ms.p95.toFixed(1)}ms > 500ms`);
    }

    if (stats.barge_in_cut_ms.p95 > 120) {
      failures.push(`Barge-in cut p95: ${stats.barge_in_cut_ms.p95.toFixed(1)}ms > 120ms`);
    }

    if (stats.targetAchievementRate < 95) {
      failures.push(`Target achievement rate: ${stats.targetAchievementRate.toFixed(1)}% < 95%`);
    }

    return {
      passed: failures.length === 0,
      failures
    };
  }

  public reset(): void {
    this.metricsLog = [];
    this.recentMetrics = [];
    console.log('🔄 Metrics logger reset');
  }

  public cleanup(): void {
    // Final performance summary
    if (this.metricsLog.length > 0) {
      this.logPerformanceSummary();
      
      // Write final summary to log
      const finalSummary = {
        type: 'session_summary',
        ...this.getAllTimeStats()
      };
      
      this.writeToLog(finalSummary);
    }
    
    console.log(`📊 Metrics logger cleanup complete. Log saved to: ${this.logFilePath}`);
  }
}