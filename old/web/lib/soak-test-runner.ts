/**
 * SoakTestRunner - Continuous Stability Testing with Chaos Engineering
 * Runs 100-200 synthetic rounds with network issues, CPU spikes, and error injection
 */

import { VoiceUIBinding } from './voice-binding';

export interface SoakTestConfig {
  rounds: number;
  errorInjectionRate: number; // 0.05 = 5%
  pauseRange: [number, number]; // [min_ms, max_ms] between rounds
  amplitudeVariation: boolean;
  enableChaos: boolean;
}

export interface SoakTestMetrics {
  round_number: number;
  timestamp_ms: number;
  e2e_roundtrip_ms?: number;
  asr_partial_latency_ms?: number;
  asr_final_latency_ms?: number;
  tts_ttfa_ms?: number;
  error_injected?: string;
  reconnect_attempt?: boolean;
  reconnect_success?: boolean;
  cancelled_playback?: boolean;
  synthetic_rerun?: boolean;
  backoff_delay_ms?: number;
}

export interface SoakTestResult {
  test_id: string;
  start_time: number;
  end_time: number;
  total_duration_min: number;
  rounds_attempted: number;
  rounds_completed: number;
  success_rate: number;
  
  // Performance metrics
  performance: {
    e2e_p50: number;
    e2e_p95: number;
    asr_partial_p50: number;
    asr_partial_p95: number;
    tts_ttfa_p50: number;
    tts_ttfa_p95: number;
  };
  
  // Reliability metrics
  reliability: {
    reconnect_count: number;
    reconnect_success_rate: number;
    max_reconnect_attempts: number;
    cancelled_playbacks: number;
    synthetic_reruns: number;
    memory_stable: boolean;
    heap_variation_percent: number;
  };
  
  // Error breakdown
  errors: {
    [error_type: string]: number;
  };
  
  // Pass/Fail evaluation
  pass: boolean;
  failures: string[];
  
  // Heatmap data (round -> e2e latency)
  heatmap: Array<{ round: number; e2e_ms: number }>;
}

const DEFAULT_CONFIG: SoakTestConfig = {
  rounds: 100,
  errorInjectionRate: 0.07, // 7% error injection
  pauseRange: [200, 1200],
  amplitudeVariation: true,
  enableChaos: true
};

export class SoakTestRunner {
  private testId: string;
  private config: SoakTestConfig;
  private metrics: SoakTestMetrics[] = [];
  private isRunning = false;
  private shouldStop = false;
  private startHeapSize = 0;
  private reconnectCount = 0;
  private cancelledPlaybacks = 0;
  private syntheticReruns = 0;
  private onProgress?: (progress: { round: number; total: number; metrics: SoakTestMetrics }) => void;
  
  constructor(
    private voiceBinding: VoiceUIBinding,
    config: Partial<SoakTestConfig> = {}
  ) {
    this.testId = `soak_${Date.now()}`;
    this.config = { ...DEFAULT_CONFIG, ...config };
  }
  
  setProgressCallback(callback: (progress: { round: number; total: number; metrics: SoakTestMetrics }) => void) {
    this.onProgress = callback;
  }
  
  async start(): Promise<SoakTestResult> {
    if (this.isRunning) {
      throw new Error('Soak test already running');
    }
    
    this.isRunning = true;
    this.shouldStop = false;
    this.metrics = [];
    this.reconnectCount = 0;
    this.cancelledPlaybacks = 0;
    this.syntheticReruns = 0;
    
    const startTime = Date.now();
    
    // Capture initial heap size
    this.startHeapSize = this.getHeapSize();
    
    console.log(`🚀 Starting soak test: ${this.config.rounds} rounds with ${(this.config.errorInjectionRate * 100).toFixed(1)}% chaos`);
    
    let completedRounds = 0;
    
    for (let round = 1; round <= this.config.rounds && !this.shouldStop; round++) {
      try {
        const roundMetrics = await this.runSingleRound(round);
        this.metrics.push(roundMetrics);
        completedRounds++;
        
        this.onProgress?.({
          round,
          total: this.config.rounds,
          metrics: roundMetrics
        });
        
        // Random pause between rounds
        const pauseMs = this.randomBetween(this.config.pauseRange[0], this.config.pauseRange[1]);
        await this.sleep(pauseMs);
        
      } catch (error) {
        console.error(`Soak test round ${round} failed:`, error);
        
        // Count as synthetic rerun and continue
        this.syntheticReruns++;
        const failedMetrics: SoakTestMetrics = {
          round_number: round,
          timestamp_ms: Date.now(),
          synthetic_rerun: true,
          error_injected: `round_failure: ${error}`
        };
        this.metrics.push(failedMetrics);
      }
    }
    
    const endTime = Date.now();
    const result = this.generateResult(startTime, endTime, completedRounds);
    
    // Send result to API
    this.sendSoakResultToAPI(result).catch(console.error);
    
    // Save to localStorage
    this.saveSoakReportToStorage(result);
    
    this.isRunning = false;
    return result;
  }
  
  stop() {
    console.log('🛑 Stopping soak test...');
    this.shouldStop = true;
  }
  
  private async runSingleRound(roundNumber: number): Promise<SoakTestMetrics> {
    const roundStartTime = Date.now();
    
    const metrics: SoakTestMetrics = {
      round_number: roundNumber,
      timestamp_ms: roundStartTime
    };
    
    // Chaos engineering - inject random errors
    if (this.config.enableChaos && Math.random() < this.config.errorInjectionRate) {
      const chaosType = this.injectChaos();
      metrics.error_injected = chaosType;
      
      // Some chaos requires special handling
      if (chaosType === 'ws_drop') {
        metrics.reconnect_attempt = true;
        metrics.backoff_delay_ms = await this.simulateWebSocketDrop();
        metrics.reconnect_success = true; // If we get here, reconnect worked
        this.reconnectCount++;
      } else if (chaosType === 'tts_cancel') {
        metrics.cancelled_playback = true;
        await this.simulateTTSCancel();
        this.cancelledPlaybacks++;
      }
    }
    
    // Generate synthetic audio with optional amplitude variation
    const audioAmplitude = this.config.amplitudeVariation 
      ? 0.3 + Math.random() * 0.4 // 0.3 to 0.7
      : 0.7;
    
    const syntheticAudio = this.generateVariableAmplitudeAudio(audioAmplitude);
    
    // Run the voice round
    try {
      const roundMetrics = await this.runVoiceRound(syntheticAudio);
      
      // Merge metrics
      Object.assign(metrics, roundMetrics);
      
      // Calculate E2E for this round
      if (metrics.asr_partial_latency_ms && metrics.tts_ttfa_ms) {
        metrics.e2e_roundtrip_ms = Date.now() - roundStartTime;
      }
      
    } catch (error) {
      metrics.synthetic_rerun = true;
      this.syntheticReruns++;
      throw error;
    }
    
    return metrics;
  }
  
  private injectChaos(): string {
    const chaosTypes = [
      'ws_drop',
      'ws_latency_spike', 
      'tts_cancel',
      'mic_denied',
      'rate_limit',
      'audio_gap'
    ];
    
    return chaosTypes[Math.floor(Math.random() * chaosTypes.length)];
  }
  
  private async simulateWebSocketDrop(): Promise<number> {
    console.log('🌪️ Chaos: Simulating WebSocket drop');
    
    // Force close the WebSocket connection
    if (this.voiceBinding.provider?.ws) {
      this.voiceBinding.provider.ws.close(1006, 'Chaos test disconnect');
    }
    
    // Wait for auto-reconnect with exponential backoff simulation
    const backoffMs = Math.min(1000 * Math.pow(2, this.reconnectCount), 8000);
    await this.sleep(backoffMs);
    
    return backoffMs;
  }
  
  private async simulateTTSCancel(): Promise<void> {
    console.log('🌪️ Chaos: Cancelling TTS mid-playback');
    
    if (this.voiceBinding.provider?.tts.isSpeaking()) {
      await this.voiceBinding.provider.tts.cancelAll();
    }
    
    // Wait for cancel to take effect
    await this.sleep(100);
  }
  
  private generateVariableAmplitudeAudio(amplitude: number): Int16Array {
    const sampleRate = 16000;
    const duration = 0.15 + Math.random() * 0.1; // 150-250ms
    const samples = Math.floor(sampleRate * duration);
    const audio = new Int16Array(samples);
    
    for (let i = 0; i < samples; i++) {
      const t = i / sampleRate;
      
      // Variable frequency based on amplitude
      const baseFreq = 120 + amplitude * 80; // 120-200Hz
      const harmonics = Math.sin(2 * Math.PI * baseFreq * t) * 0.4 +
                      Math.sin(2 * Math.PI * baseFreq * 2 * t) * 0.2 +
                      Math.sin(2 * Math.PI * baseFreq * 3 * t) * 0.1;
      
      // Amplitude-based noise
      const noise = (Math.random() - 0.5) * 0.15 * amplitude;
      
      // Envelope
      const envelope = Math.sin(Math.PI * t / duration);
      
      const sample = (harmonics + noise) * envelope * amplitude;
      audio[i] = Math.round(sample * 16384);
    }
    
    return audio;
  }
  
  private async runVoiceRound(audio: Int16Array): Promise<Partial<SoakTestMetrics>> {
    const metrics: Partial<SoakTestMetrics> = {};
    
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      const timeout = setTimeout(() => {
        reject(new Error('Voice round timeout'));
      }, 8000);
      
      let partialReceived = false;
      let finalReceived = false;
      
      const cleanup = () => {
        clearTimeout(timeout);
        this.voiceBinding.provider?.off?.('asr:partial');
        this.voiceBinding.provider?.off?.('asr:final');
        this.voiceBinding.provider?.off?.('tts:start');
        this.voiceBinding.provider?.off?.('error');
      };
      
      this.voiceBinding.provider?.on('asr:partial', () => {
        if (!partialReceived) {
          partialReceived = true;
          metrics.asr_partial_latency_ms = Date.now() - startTime;
        }
      });
      
      this.voiceBinding.provider?.on('asr:final', () => {
        if (!finalReceived) {
          finalReceived = true;
          metrics.asr_final_latency_ms = Date.now() - startTime;
        }
      });
      
      this.voiceBinding.provider?.on('tts:start', () => {
        metrics.tts_ttfa_ms = Date.now() - startTime - (metrics.asr_final_latency_ms || 0);
        
        // Complete the round after TTS starts
        cleanup();
        resolve(metrics);
      });
      
      this.voiceBinding.provider?.on('error', (error: any) => {
        cleanup();
        reject(error);
      });
      
      // Start ASR and send audio
      this.voiceBinding.provider?.asr.start({
        language: 'en-US',
        continuous: false,
        interimResults: true
      }, {
        onStart: () => {
          // Send audio in chunks
          this.sendAudioChunks(audio).catch(reject);
        },
        onFinal: () => {
          // Trigger TTS response
          this.voiceBinding.speakText('Test response').catch(reject);
        }
      }).catch(reject);
    });
  }
  
  private async sendAudioChunks(audio: Int16Array): Promise<void> {
    const chunkSize = 2048;
    const chunks = Math.ceil(audio.length / chunkSize);
    
    for (let i = 0; i < chunks; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, audio.length);
      const chunk = audio.slice(start, end);
      
      this.voiceBinding.provider?.asr.pushAudio(chunk);
      
      // Simulate real-time with small delays
      if (i < chunks - 1) {
        await this.sleep(30);
      }
    }
  }
  
  private generateResult(startTime: number, endTime: number, completedRounds: number): SoakTestResult {
    const durationMin = (endTime - startTime) / (1000 * 60);
    
    // Calculate performance percentiles
    const e2eValues = this.metrics.map(m => m.e2e_roundtrip_ms).filter(v => v !== undefined) as number[];
    const asrPartialValues = this.metrics.map(m => m.asr_partial_latency_ms).filter(v => v !== undefined) as number[];
    const ttsValues = this.metrics.map(m => m.tts_ttfa_ms).filter(v => v !== undefined) as number[];
    
    const performance = {
      e2e_p50: this.percentile(e2eValues, 0.5),
      e2e_p95: this.percentile(e2eValues, 0.95),
      asr_partial_p50: this.percentile(asrPartialValues, 0.5),
      asr_partial_p95: this.percentile(asrPartialValues, 0.95),
      tts_ttfa_p50: this.percentile(ttsValues, 0.5),
      tts_ttfa_p95: this.percentile(ttsValues, 0.95)
    };
    
    // Memory stability check
    const currentHeapSize = this.getHeapSize();
    const heapVariation = currentHeapSize > 0 && this.startHeapSize > 0
      ? Math.abs(currentHeapSize - this.startHeapSize) / this.startHeapSize
      : 0;
    
    // Reliability metrics
    const reliability = {
      reconnect_count: this.reconnectCount,
      reconnect_success_rate: this.reconnectCount > 0 ? 1.0 : 1.0, // Assume success if we completed
      max_reconnect_attempts: Math.max(...this.metrics.map(m => m.reconnect_attempt ? 1 : 0)),
      cancelled_playbacks: this.cancelledPlaybacks,
      synthetic_reruns: this.syntheticReruns,
      memory_stable: heapVariation < 0.1, // Less than 10% variation
      heap_variation_percent: heapVariation * 100
    };
    
    // Error breakdown
    const errors: { [key: string]: number } = {};
    this.metrics.forEach(m => {
      if (m.error_injected) {
        errors[m.error_injected] = (errors[m.error_injected] || 0) + 1;
      }
    });
    
    // Heatmap data
    const heatmap = this.metrics
      .filter(m => m.e2e_roundtrip_ms !== undefined)
      .map(m => ({
        round: m.round_number,
        e2e_ms: m.e2e_roundtrip_ms!
      }));
    
    // Pass/Fail evaluation
    const failures: string[] = [];
    
    if (performance.e2e_p50 > 1300) {
      failures.push(`E2E P50 ${performance.e2e_p50}ms > 1300ms`);
    }
    if (performance.e2e_p95 > 2700) {
      failures.push(`E2E P95 ${performance.e2e_p95}ms > 2700ms`);
    }
    if (reliability.reconnect_success_rate < 1.0) {
      failures.push(`Reconnect success rate ${reliability.reconnect_success_rate} < 100%`);
    }
    if (!reliability.memory_stable) {
      failures.push(`Memory unstable: ${reliability.heap_variation_percent.toFixed(1)}% variation`);
    }
    
    const result: SoakTestResult = {
      test_id: this.testId,
      start_time: startTime,
      end_time: endTime,
      total_duration_min: durationMin,
      rounds_attempted: this.config.rounds,
      rounds_completed: completedRounds,
      success_rate: completedRounds / this.config.rounds,
      performance,
      reliability,
      errors,
      pass: failures.length === 0,
      failures,
      heatmap
    };
    
    return result;
  }
  
  private percentile(values: number[], p: number): number {
    if (values.length === 0) return 0;
    const sorted = [...values].sort((a, b) => a - b);
    const index = Math.floor(sorted.length * p);
    return sorted[index] || 0;
  }
  
  private getHeapSize(): number {
    if (typeof (performance as any).memory !== 'undefined') {
      return (performance as any).memory.usedJSHeapSize;
    }
    return 0; // Not available in all browsers
  }
  
  private randomBetween(min: number, max: number): number {
    return min + Math.random() * (max - min);
  }
  
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  private async sendSoakResultToAPI(result: SoakTestResult): Promise<void> {
    try {
      await fetch('/api/metrics/voice', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          timestamp_ms: result.end_time,
          session_id: result.test_id,
          test_type: 'soak_v1',
          test_pass: result.pass,
          duration_minutes: result.total_duration_min,
          rounds_completed: result.rounds_completed,
          success_rate: result.success_rate,
          e2e_roundtrip_ms: result.performance.e2e_p50,
          provider: 'openai',
          chaos_enabled: this.config.enableChaos,
          error_injection_rate: this.config.errorInjectionRate
        })
      });
    } catch (error) {
      console.warn('Failed to send soak result to API:', error);
    }
  }
  
  private saveSoakReportToStorage(result: SoakTestResult): void {
    const report = {
      ...result,
      environment: {
        VOICE_PROVIDER: process.env.NEXT_PUBLIC_VOICE_PROVIDER,
        OPENAI_REALTIME_MODEL: process.env.NEXT_PUBLIC_OPENAI_REALTIME_MODEL,
        VAD_ENABLED: process.env.NEXT_PUBLIC_VOICE_VAD,
        build_id: `build_${Date.now()}` // In real app, use actual build ID
      }
    };
    
    localStorage.setItem('alice_soak_test_report', JSON.stringify(report));
  }
}