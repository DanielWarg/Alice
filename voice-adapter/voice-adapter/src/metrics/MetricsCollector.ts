import { EventEmitter } from 'eventemitter3';
import {
  PerformanceMetrics,
  VoiceProviderEvents,
  AudioChunk,
  TranscriptResult,
  TTSResult,
  VADResult
} from '../types';
import { LatencyTracker, LatencyStats } from './LatencyTracker';

/**
 * Comprehensive metrics collector for voice operations
 */
export class MetricsCollector extends EventEmitter<VoiceProviderEvents> {
  private latencyTracker: LatencyTracker;
  private sessionStartTime: number = 0;
  private sessionId: string | null = null;
  private enabled: boolean = true;

  // Audio metrics
  public audioMetrics = {
    inputChunks: 0,
    outputChunks: 0,
    totalInputBytes: 0,
    totalOutputBytes: 0,
    totalInputDuration: 0,
    totalOutputDuration: 0,
    averageInputQuality: 0,
    averageOutputQuality: 0
  };

  // Transcript metrics
  public transcriptMetrics = {
    totalTranscripts: 0,
    totalWords: 0,
    averageConfidence: 0,
    finalTranscripts: 0,
    interimTranscripts: 0,
    confidenceSum: 0
  };

  // TTS metrics
  public ttsMetrics = {
    totalSyntheses: 0,
    totalCharacters: 0,
    totalAudioGenerated: 0,
    averageCharactersPerSecond: 0,
    voiceUsage: new Map<string, number>()
  };

  // VAD metrics
  public vadMetrics = {
    totalVADEvents: 0,
    voiceActiveTime: 0,
    voiceInactiveTime: 0,
    averageVADConfidence: 0,
    vadConfidenceSum: 0
  };

  // Error metrics
  public errorMetrics = {
    totalErrors: 0,
    errorsByType: new Map<string, number>(),
    errorsByProvider: new Map<string, number>()
  };

  // Session metrics
  public sessionMetrics = {
    totalSessions: 0,
    averageSessionDuration: 0,
    activeSessions: 0,
    sessionDurations: [] as number[]
  };

  constructor(targetLatency: number = 500) {
    super();
    this.latencyTracker = new LatencyTracker(targetLatency);
    this.setupLatencyTrackerEvents();
  }

  /**
   * Start a new metrics session
   */
  startSession(sessionId: string): void {
    this.sessionId = sessionId;
    this.sessionStartTime = Date.now();
    this.sessionMetrics.activeSessions++;
    this.latencyTracker.setSessionId(sessionId);
    
    console.log(`[MetricsCollector] Started session: ${sessionId}`);
  }

  /**
   * End current metrics session
   */
  endSession(): void {
    if (this.sessionId && this.sessionStartTime > 0) {
      const duration = Date.now() - this.sessionStartTime;
      this.sessionMetrics.sessionDurations.push(duration);
      this.sessionMetrics.totalSessions++;
      this.sessionMetrics.activeSessions = Math.max(0, this.sessionMetrics.activeSessions - 1);
      
      // Update average session duration
      const totalDuration = this.sessionMetrics.sessionDurations.reduce((sum, d) => sum + d, 0);
      this.sessionMetrics.averageSessionDuration = totalDuration / this.sessionMetrics.sessionDurations.length;
      
      console.log(`[MetricsCollector] Ended session: ${this.sessionId}, duration: ${duration}ms`);
    }
    
    this.sessionId = null;
    this.sessionStartTime = 0;
    this.latencyTracker.clearSessionId();
  }

  /**
   * Record audio input metrics
   */
  recordAudioInput(chunk: AudioChunk): void {
    if (!this.enabled) return;

    this.audioMetrics.inputChunks++;
    this.audioMetrics.totalInputBytes += chunk.data.length;
    this.audioMetrics.totalInputDuration += chunk.duration;
    
    // Estimate audio quality based on format
    const quality = this.calculateAudioQuality(chunk);
    this.audioMetrics.averageInputQuality = this.updateAverage(
      this.audioMetrics.averageInputQuality,
      quality,
      this.audioMetrics.inputChunks
    );
  }

  /**
   * Record audio output metrics
   */
  recordAudioOutput(chunk: AudioChunk): void {
    if (!this.enabled) return;

    this.audioMetrics.outputChunks++;
    this.audioMetrics.totalOutputBytes += chunk.data.length;
    this.audioMetrics.totalOutputDuration += chunk.duration;
    
    const quality = this.calculateAudioQuality(chunk);
    this.audioMetrics.averageOutputQuality = this.updateAverage(
      this.audioMetrics.averageOutputQuality,
      quality,
      this.audioMetrics.outputChunks
    );
  }

  /**
   * Record transcript metrics
   */
  recordTranscript(result: TranscriptResult): void {
    if (!this.enabled) return;

    this.transcriptMetrics.totalTranscripts++;
    this.transcriptMetrics.confidenceSum += result.confidence;
    this.transcriptMetrics.averageConfidence = 
      this.transcriptMetrics.confidenceSum / this.transcriptMetrics.totalTranscripts;

    if (result.isFinal) {
      this.transcriptMetrics.finalTranscripts++;
      this.transcriptMetrics.totalWords += result.text.split(/\s+/).length;
    } else {
      this.transcriptMetrics.interimTranscripts++;
    }
  }

  /**
   * Record TTS synthesis metrics
   */
  recordTTSSynthesis(result: TTSResult): void {
    if (!this.enabled) return;

    this.ttsMetrics.totalSyntheses++;
    this.ttsMetrics.totalCharacters += result.text.length;
    this.ttsMetrics.totalAudioGenerated += result.audio.duration;

    // Update voice usage
    const currentUsage = this.ttsMetrics.voiceUsage.get(result.voice) || 0;
    this.ttsMetrics.voiceUsage.set(result.voice, currentUsage + 1);

    // Calculate characters per second
    if (this.ttsMetrics.totalAudioGenerated > 0) {
      this.ttsMetrics.averageCharactersPerSecond = 
        (this.ttsMetrics.totalCharacters / this.ttsMetrics.totalAudioGenerated) * 1000;
    }
  }

  /**
   * Record VAD event metrics
   */
  recordVADEvent(result: VADResult): void {
    if (!this.enabled) return;

    this.vadMetrics.totalVADEvents++;
    this.vadMetrics.vadConfidenceSum += result.confidence;
    this.vadMetrics.averageVADConfidence = 
      this.vadMetrics.vadConfidenceSum / this.vadMetrics.totalVADEvents;

    // Track voice active/inactive time (simplified)
    if (result.isVoiceActive) {
      this.vadMetrics.voiceActiveTime += 100; // Approximate 100ms segments
    } else {
      this.vadMetrics.voiceInactiveTime += 100;
    }
  }

  /**
   * Record error metrics
   */
  recordError(error: Error, provider?: string): void {
    if (!this.enabled) return;

    this.errorMetrics.totalErrors++;

    // Track by error type
    const errorType = error.constructor.name;
    const currentTypeCount = this.errorMetrics.errorsByType.get(errorType) || 0;
    this.errorMetrics.errorsByType.set(errorType, currentTypeCount + 1);

    // Track by provider
    if (provider) {
      const currentProviderCount = this.errorMetrics.errorsByProvider.get(provider) || 0;
      this.errorMetrics.errorsByProvider.set(provider, currentProviderCount + 1);
    }

    console.warn(`[MetricsCollector] Recorded error: ${errorType}${provider ? ` (${provider})` : ''}`);
  }

  /**
   * Record latency measurement
   */
  recordLatency(type: 'asr' | 'tts' | 'endToEnd', latency: number): void {
    if (!this.enabled) return;
    this.latencyTracker.recordLatency(type, latency);
  }

  /**
   * Start tracking latency for a request
   */
  startLatencyTracking(requestId: string, type: 'asr' | 'tts' | 'endToEnd'): void {
    if (!this.enabled) return;
    this.latencyTracker.startTracking(requestId, type);
  }

  /**
   * End tracking latency for a request
   */
  endLatencyTracking(requestId: string, type: 'asr' | 'tts' | 'endToEnd'): void {
    if (!this.enabled) return;
    this.latencyTracker.endTracking(requestId, type);
  }

  /**
   * Get comprehensive performance metrics
   */
  getPerformanceMetrics(): PerformanceMetrics {
    const latencyStats = this.latencyTracker.getPerformanceSummary();
    const now = Date.now();

    return {
      latency: {
        asr: latencyStats.asr.average,
        tts: latencyStats.tts.average,
        endToEnd: latencyStats.endToEnd.average
      },
      throughput: {
        audioProcessed: this.audioMetrics.inputChunks + this.audioMetrics.outputChunks,
        messagesPerSecond: this.calculateMessagesPerSecond()
      },
      quality: {
        audioQuality: (this.audioMetrics.averageInputQuality + this.audioMetrics.averageOutputQuality) / 2,
        transcriptAccuracy: this.transcriptMetrics.averageConfidence
      },
      timestamps: {
        requestStart: this.sessionStartTime || 0,
        asrComplete: 0, // Would be set by specific implementations
        ttsStart: 0,    // Would be set by specific implementations
        ttsComplete: 0, // Would be set by specific implementations
        responseEnd: now
      }
    };
  }

  /**
   * Get detailed metrics report
   */
  getDetailedMetrics(): DetailedMetricsReport {
    const performanceMetrics = this.getPerformanceMetrics();
    const latencySummary = this.latencyTracker.getPerformanceSummary();

    return {
      performance: performanceMetrics,
      latency: latencySummary,
      audio: { ...this.audioMetrics },
      transcript: { ...this.transcriptMetrics },
      tts: {
        ...this.ttsMetrics,
        voiceUsage: Object.fromEntries(this.ttsMetrics.voiceUsage) as any
      },
      vad: { ...this.vadMetrics },
      errors: {
        ...this.errorMetrics,
        errorsByType: Object.fromEntries(this.errorMetrics.errorsByType) as any,
        errorsByProvider: Object.fromEntries(this.errorMetrics.errorsByProvider) as any
      },
      session: { ...this.sessionMetrics },
      timestamp: Date.now(),
      sessionId: this.sessionId
    };
  }

  /**
   * Get metrics summary for monitoring
   */
  getMetricsSummary(): MetricsSummary {
    const performance = this.getPerformanceMetrics();
    const latencyHealth = this.latencyTracker.isLatencyWithinTarget();

    return {
      healthy: this.isSystemHealthy(),
      latencyWithinTarget: latencyHealth,
      averageLatency: performance.latency.endToEnd,
      errorRate: this.calculateErrorRate(),
      throughput: performance.throughput.messagesPerSecond,
      sessionDuration: this.sessionStartTime > 0 ? Date.now() - this.sessionStartTime : 0,
      activeSession: this.sessionId !== null,
      totalErrors: this.errorMetrics.totalErrors,
      timestamp: Date.now()
    };
  }

  /**
   * Enable or disable metrics collection
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    this.latencyTracker.setEnabled(enabled);
    
    if (!enabled) {
      console.log('[MetricsCollector] Metrics collection disabled');
    }
  }

  /**
   * Check if metrics collection is enabled
   */
  isEnabled(): boolean {
    return this.enabled;
  }

  /**
   * Clear all collected metrics
   */
  clearMetrics(): void {
    this.audioMetrics = {
      inputChunks: 0,
      outputChunks: 0,
      totalInputBytes: 0,
      totalOutputBytes: 0,
      totalInputDuration: 0,
      totalOutputDuration: 0,
      averageInputQuality: 0,
      averageOutputQuality: 0
    };

    this.transcriptMetrics = {
      totalTranscripts: 0,
      totalWords: 0,
      averageConfidence: 0,
      finalTranscripts: 0,
      interimTranscripts: 0,
      confidenceSum: 0
    };

    this.ttsMetrics = {
      totalSyntheses: 0,
      totalCharacters: 0,
      totalAudioGenerated: 0,
      averageCharactersPerSecond: 0,
      voiceUsage: new Map<string, number>()
    };

    this.vadMetrics = {
      totalVADEvents: 0,
      voiceActiveTime: 0,
      voiceInactiveTime: 0,
      averageVADConfidence: 0,
      vadConfidenceSum: 0
    };

    this.errorMetrics = {
      totalErrors: 0,
      errorsByType: new Map<string, number>(),
      errorsByProvider: new Map<string, number>()
    };

    this.latencyTracker.clearMeasurements();
    
    console.log('[MetricsCollector] All metrics cleared');
  }

  /**
   * Export metrics to JSON
   */
  exportMetrics(): string {
    const metrics = this.getDetailedMetrics();
    return JSON.stringify(metrics, null, 2);
  }

  /**
   * Get the latency tracker instance
   */
  getLatencyTracker(): LatencyTracker {
    return this.latencyTracker;
  }

  /**
   * Calculate audio quality based on format
   */
  private calculateAudioQuality(chunk: AudioChunk): number {
    const { sampleRate, bitDepth, channels } = chunk.format;
    
    // Simple quality calculation based on audio parameters
    let quality = 0.5; // Base quality
    
    // Sample rate contribution (higher is better)
    if (sampleRate >= 48000) quality += 0.3;
    else if (sampleRate >= 44100) quality += 0.25;
    else if (sampleRate >= 24000) quality += 0.2;
    else if (sampleRate >= 16000) quality += 0.15;
    else quality += 0.1;
    
    // Bit depth contribution
    if (bitDepth >= 24) quality += 0.2;
    else if (bitDepth >= 16) quality += 0.15;
    else quality += 0.1;
    
    // Stereo bonus
    if (channels > 1) quality += 0.05;
    
    return Math.min(1.0, quality);
  }

  /**
   * Update running average
   */
  private updateAverage(currentAverage: number, newValue: number, count: number): number {
    return ((currentAverage * (count - 1)) + newValue) / count;
  }

  /**
   * Calculate messages per second
   */
  private calculateMessagesPerSecond(): number {
    if (!this.sessionStartTime || this.sessionStartTime === 0) return 0;
    
    const durationSeconds = (Date.now() - this.sessionStartTime) / 1000;
    const totalMessages = this.transcriptMetrics.totalTranscripts + this.ttsMetrics.totalSyntheses;
    
    return durationSeconds > 0 ? totalMessages / durationSeconds : 0;
  }

  /**
   * Calculate error rate
   */
  private calculateErrorRate(): number {
    const totalOperations = 
      this.audioMetrics.inputChunks + 
      this.audioMetrics.outputChunks + 
      this.transcriptMetrics.totalTranscripts + 
      this.ttsMetrics.totalSyntheses;
    
    return totalOperations > 0 ? (this.errorMetrics.totalErrors / totalOperations) * 100 : 0;
  }

  /**
   * Check overall system health
   */
  private isSystemHealthy(): boolean {
    const errorRate = this.calculateErrorRate();
    const latencyHealthy = this.latencyTracker.isLatencyWithinTarget();
    
    return errorRate < 5 && latencyHealthy; // Less than 5% error rate and latency within target
  }

  /**
   * Setup latency tracker event forwarding
   */
  private setupLatencyTrackerEvents(): void {
    this.latencyTracker.on('latency_update', (latency, type) => {
      this.emit('latency_update', latency, type);
    });
  }
}

/**
 * Detailed metrics report interface
 */
export interface DetailedMetricsReport {
  performance: PerformanceMetrics;
  latency: any; // PerformanceSummary from LatencyTracker
  audio: typeof MetricsCollector.prototype.audioMetrics;
  transcript: typeof MetricsCollector.prototype.transcriptMetrics;
  tts: typeof MetricsCollector.prototype.ttsMetrics & { voiceUsage: Record<string, number> };
  vad: typeof MetricsCollector.prototype.vadMetrics;
  errors: typeof MetricsCollector.prototype.errorMetrics & {
    errorsByType: Record<string, number>;
    errorsByProvider: Record<string, number>;
  };
  session: typeof MetricsCollector.prototype.sessionMetrics;
  timestamp: number;
  sessionId: string | null;
}

/**
 * Metrics summary interface
 */
export interface MetricsSummary {
  healthy: boolean;
  latencyWithinTarget: boolean;
  averageLatency: number;
  errorRate: number;
  throughput: number;
  sessionDuration: number;
  activeSession: boolean;
  totalErrors: number;
  timestamp: number;
}

/**
 * Create metrics collector with default settings
 */
export function createMetricsCollector(targetLatency: number = 500): MetricsCollector {
  return new MetricsCollector(targetLatency);
}

/**
 * Metrics monitoring helper
 */
export class MetricsMonitor {
  private static watchers = new Map<string, NodeJS.Timeout>();

  /**
   * Start monitoring metrics with periodic reporting
   */
  static startMonitoring(
    collector: MetricsCollector,
    intervalMs: number = 30000,
    callback: (summary: MetricsSummary) => void
  ): string {
    const watcherId = `monitor_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const interval = setInterval(() => {
      const summary = collector.getMetricsSummary();
      callback(summary);
    }, intervalMs);

    this.watchers.set(watcherId, interval);
    console.log(`[MetricsMonitor] Started monitoring with ID: ${watcherId}`);
    
    return watcherId;
  }

  /**
   * Stop monitoring metrics
   */
  static stopMonitoring(watcherId: string): void {
    const interval = this.watchers.get(watcherId);
    if (interval) {
      clearInterval(interval);
      this.watchers.delete(watcherId);
      console.log(`[MetricsMonitor] Stopped monitoring: ${watcherId}`);
    }
  }

  /**
   * Stop all monitoring
   */
  static stopAllMonitoring(): void {
    this.watchers.forEach((interval, watcherId) => {
      clearInterval(interval);
      console.log(`[MetricsMonitor] Stopped monitoring: ${watcherId}`);
    });
    this.watchers.clear();
  }
}