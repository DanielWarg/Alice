/**
 * SelfTestRunner - Synthetic Voice Pipeline Testing
 * Runs end-to-end voice tests without human mic input
 */

export interface SelfTestResult {
  pass: boolean;
  testId: string;
  timestamp: number;
  metrics: {
    asr_partial_latency_ms?: number;
    asr_final_latency_ms?: number;
    llm_latency_ms?: number;
    tts_ttfa_ms?: number;
    e2e_roundtrip_ms?: number;
  };
  errors: string[];
  steps: SelfTestStep[];
}

export interface SelfTestStep {
  name: string;
  status: 'pending' | 'running' | 'complete' | 'failed';
  duration_ms?: number;
  error?: string;
}

export interface SelfTestThresholds {
  asr_partial_latency_ms: number;
  asr_final_latency_ms: number;
  tts_ttfa_ms: number;
  e2e_roundtrip_ms: number;
}

const DEFAULT_THRESHOLDS: SelfTestThresholds = {
  asr_partial_latency_ms: 500,
  asr_final_latency_ms: 1000,
  tts_ttfa_ms: 500,
  e2e_roundtrip_ms: 1500
};

const P95_THRESHOLDS: SelfTestThresholds = {
  asr_partial_latency_ms: 1000,
  asr_final_latency_ms: 2000,
  tts_ttfa_ms: 1000,
  e2e_roundtrip_ms: 3000
};

export class SelfTestRunner {
  private testId: string;
  private startTime: number = 0;
  private steps: SelfTestStep[] = [];
  private metrics: SelfTestResult['metrics'] = {};
  private errors: string[] = [];
  private onStepUpdate?: (steps: SelfTestStep[]) => void;
  
  constructor(
    private voiceBinding: any,
    private thresholds: SelfTestThresholds = DEFAULT_THRESHOLDS
  ) {
    this.testId = `selftest_${Date.now()}`;
  }
  
  setStepUpdateCallback(callback: (steps: SelfTestStep[]) => void) {
    this.onStepUpdate = callback;
  }
  
  private updateStep(name: string, status: SelfTestStep['status'], error?: string, duration_ms?: number) {
    const existingIndex = this.steps.findIndex(s => s.name === name);
    const step: SelfTestStep = {
      name,
      status,
      duration_ms,
      error
    };
    
    if (existingIndex >= 0) {
      this.steps[existingIndex] = step;
    } else {
      this.steps.push(step);
    }
    
    console.log(`[SelfTest] ${name}: ${status}${error ? ` - ${error}` : ''}`);
    this.onStepUpdate?.(this.steps);
  }
  
  private generateSyntheticAudio(): Int16Array {
    // Generate 200ms of synthetic voice-like audio (16kHz PCM16)
    const sampleRate = 16000;
    const duration = 0.2; // 200ms
    const samples = Math.floor(sampleRate * duration);
    const audio = new Int16Array(samples);
    
    // Create voice-like waveform: mix of frequencies with some noise
    for (let i = 0; i < samples; i++) {
      const t = i / sampleRate;
      
      // Base frequency around 150Hz (typical male voice)
      const baseFreq = 150;
      const harmonics = Math.sin(2 * Math.PI * baseFreq * t) * 0.3 +
                      Math.sin(2 * Math.PI * baseFreq * 2 * t) * 0.2 +
                      Math.sin(2 * Math.PI * baseFreq * 3 * t) * 0.1;
      
      // Add some noise for realism
      const noise = (Math.random() - 0.5) * 0.1;
      
      // Apply envelope (fade in/out)
      const envelope = Math.sin(Math.PI * t / duration);
      
      const sample = (harmonics + noise) * envelope * 0.7;
      audio[i] = Math.round(sample * 16384); // Convert to PCM16 range
    }
    
    return audio;
  }
  
  private sendSyntheticAudioChunks(audio: Int16Array): Promise<void> {
    return new Promise((resolve) => {
      const chunkSize = 4096;
      const chunks = Math.ceil(audio.length / chunkSize);
      let chunkIndex = 0;
      
      const sendNextChunk = () => {
        if (chunkIndex >= chunks) {
          resolve();
          return;
        }
        
        const start = chunkIndex * chunkSize;
        const end = Math.min(start + chunkSize, audio.length);
        const chunk = audio.slice(start, end);
        
        this.voiceBinding.provider?.asr.pushAudio(chunk);
        chunkIndex++;
        
        // Send next chunk after 50ms (simulating real-time audio)
        setTimeout(sendNextChunk, 50);
      };
      
      sendNextChunk();
    });
  }
  
  async runSingleTest(): Promise<SelfTestResult> {
    this.startTime = Date.now();
    this.steps = [];
    this.metrics = {};
    this.errors = [];
    
    this.updateStep('INIT', 'running');
    
    try {
      // Step 1: Initialize voice binding
      if (!this.voiceBinding.isInitialized) {
        await this.voiceBinding.initialize();
      }
      this.updateStep('INIT', 'complete', undefined, Date.now() - this.startTime);
      
      // Step 2: Generate synthetic audio
      this.updateStep('GENERATING_AUDIO', 'running');
      const syntheticAudio = this.generateSyntheticAudio();
      this.updateStep('GENERATING_AUDIO', 'complete', undefined, 10);
      
      // Step 3: Start listening (synthetic mode)
      this.updateStep('LISTENING', 'running');
      const asrStartTime = Date.now();
      
      const testPromise = new Promise<void>((resolve, reject) => {
        let partialReceived = false;
        let finalReceived = false;
        let speakingStarted = false;
        let speakingEnded = false;
        
        const timeout = setTimeout(() => {
          reject(new Error('Test timeout after 10 seconds'));
        }, 10000);
        
        const cleanup = () => {
          clearTimeout(timeout);
          this.voiceBinding.provider?.off?.('asr:partial');
          this.voiceBinding.provider?.off?.('asr:final');
          this.voiceBinding.provider?.off?.('tts:start');
          this.voiceBinding.provider?.off?.('tts:end');
          this.voiceBinding.provider?.off?.('error');
        };
        
        // Set up listeners
        this.voiceBinding.provider?.on('asr:partial', (result: any) => {
          if (!partialReceived) {
            partialReceived = true;
            this.metrics.asr_partial_latency_ms = Date.now() - asrStartTime;
            console.log(`[SelfTest] ASR Partial: ${this.metrics.asr_partial_latency_ms}ms`);
          }
        });
        
        this.voiceBinding.provider?.on('asr:final', (result: any) => {
          if (!finalReceived) {
            finalReceived = true;
            this.metrics.asr_final_latency_ms = Date.now() - asrStartTime;
            this.updateStep('LISTENING', 'complete', undefined, this.metrics.asr_final_latency_ms);
            this.updateStep('THINKING', 'running');
            
            console.log(`[SelfTest] ASR Final: ${this.metrics.asr_final_latency_ms}ms`);
            
            // Start TTS
            const ttsStartTime = Date.now();
            this.voiceBinding.speakText('Detta är ett självtest').catch(reject);
          }
        });
        
        this.voiceBinding.provider?.on('tts:start', () => {
          if (!speakingStarted) {
            speakingStarted = true;
            this.metrics.tts_ttfa_ms = Date.now() - asrStartTime - (this.metrics.asr_final_latency_ms || 0);
            this.updateStep('THINKING', 'complete', undefined, this.metrics.tts_ttfa_ms);
            this.updateStep('SPEAKING', 'running');
            
            console.log(`[SelfTest] TTS Start: ${this.metrics.tts_ttfa_ms}ms`);
          }
        });
        
        this.voiceBinding.provider?.on('tts:end', () => {
          if (!speakingEnded) {
            speakingEnded = true;
            this.metrics.e2e_roundtrip_ms = Date.now() - asrStartTime;
            this.updateStep('SPEAKING', 'complete', undefined, this.metrics.e2e_roundtrip_ms);
            this.updateStep('DONE', 'complete');
            
            console.log(`[SelfTest] E2E Complete: ${this.metrics.e2e_roundtrip_ms}ms`);
            cleanup();
            resolve();
          }
        });
        
        this.voiceBinding.provider?.on('error', (error: any) => {
          this.errors.push(error.message || error.toString());
          cleanup();
          reject(error);
        });
      });
      
      // Start ASR
      await this.voiceBinding.provider?.asr.start({
        language: 'en-US', // Use English for synthetic test for better recognition
        continuous: false,
        interimResults: true
      }, {
        onStart: () => {
          // Send synthetic audio chunks
          this.sendSyntheticAudioChunks(syntheticAudio).catch(console.error);
        },
        onError: (error: any) => {
          this.errors.push(error.message || error.toString());
        }
      });
      
      // Wait for test completion
      await testPromise;
      
    } catch (error) {
      this.errors.push(error instanceof Error ? error.message : String(error));
      
      // Mark current step as failed
      const currentStep = this.steps.find(s => s.status === 'running');
      if (currentStep) {
        this.updateStep(currentStep.name, 'failed', error instanceof Error ? error.message : String(error));
      }
    }
    
    // Evaluate results
    const pass = this.evaluateTestResult();
    
    const result: SelfTestResult = {
      pass,
      testId: this.testId,
      timestamp: this.startTime,
      metrics: this.metrics,
      errors: this.errors,
      steps: this.steps
    };
    
    // Send to metrics API
    this.sendTestResultToAPI(result).catch(console.error);
    
    return result;
  }
  
  private evaluateTestResult(): boolean {
    if (this.errors.length > 0) {
      return false;
    }
    
    const checks = [
      {
        name: 'ASR Partial Latency',
        value: this.metrics.asr_partial_latency_ms,
        threshold: this.thresholds.asr_partial_latency_ms,
        p95Threshold: P95_THRESHOLDS.asr_partial_latency_ms
      },
      {
        name: 'ASR Final Latency',
        value: this.metrics.asr_final_latency_ms,
        threshold: this.thresholds.asr_final_latency_ms,
        p95Threshold: P95_THRESHOLDS.asr_final_latency_ms
      },
      {
        name: 'TTS TTFA',
        value: this.metrics.tts_ttfa_ms,
        threshold: this.thresholds.tts_ttfa_ms,
        p95Threshold: P95_THRESHOLDS.tts_ttfa_ms
      },
      {
        name: 'E2E Roundtrip',
        value: this.metrics.e2e_roundtrip_ms,
        threshold: this.thresholds.e2e_roundtrip_ms,
        p95Threshold: P95_THRESHOLDS.e2e_roundtrip_ms
      }
    ];
    
    for (const check of checks) {
      if (check.value === undefined) {
        this.errors.push(`Missing metric: ${check.name}`);
        return false;
      }
      
      if (check.value > check.p95Threshold) {
        this.errors.push(`${check.name} (${check.value}ms) exceeds P95 threshold (${check.p95Threshold}ms)`);
        return false;
      }
    }
    
    return true;
  }
  
  async runMultipleTests(count: number = 3): Promise<{
    results: SelfTestResult[];
    summary: {
      passRate: number;
      medianMetrics: SelfTestResult['metrics'];
      p95Metrics: SelfTestResult['metrics'];
      overallPass: boolean;
    };
  }> {
    const results: SelfTestResult[] = [];
    
    for (let i = 0; i < count; i++) {
      console.log(`[SelfTest] Running test ${i + 1}/${count}`);
      this.testId = `selftest_${Date.now()}_${i + 1}`;
      
      const result = await this.runSingleTest();
      results.push(result);
      
      // Wait 1 second between tests
      if (i < count - 1) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
    
    // Calculate summary statistics
    const passCount = results.filter(r => r.pass).length;
    const passRate = passCount / count;
    
    const metricKeys: (keyof SelfTestResult['metrics'])[] = [
      'asr_partial_latency_ms',
      'asr_final_latency_ms',
      'tts_ttfa_ms',
      'e2e_roundtrip_ms'
    ];
    
    const medianMetrics: SelfTestResult['metrics'] = {};
    const p95Metrics: SelfTestResult['metrics'] = {};
    
    for (const key of metricKeys) {
      const values = results
        .map(r => r.metrics[key])
        .filter(v => v !== undefined) as number[];
      
      if (values.length > 0) {
        const sorted = [...values].sort((a, b) => a - b);
        medianMetrics[key] = sorted[Math.floor(sorted.length * 0.5)];
        p95Metrics[key] = sorted[Math.floor(sorted.length * 0.95)];
      }
    }
    
    const overallPass = passRate >= 0.67; // At least 2/3 tests must pass
    
    return {
      results,
      summary: {
        passRate,
        medianMetrics,
        p95Metrics,
        overallPass
      }
    };
  }
  
  private async sendTestResultToAPI(result: SelfTestResult): Promise<void> {
    try {
      await fetch('/api/metrics/voice', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          timestamp_ms: result.timestamp,
          session_id: result.testId,
          asr_partial_latency_ms: result.metrics.asr_partial_latency_ms,
          asr_final_latency_ms: result.metrics.asr_final_latency_ms,
          llm_latency_ms: result.metrics.llm_latency_ms,
          tts_ttfa_ms: result.metrics.tts_ttfa_ms,
          e2e_roundtrip_ms: result.metrics.e2e_roundtrip_ms,
          provider: 'openai',
          test_type: 'selftest_v1',
          test_pass: result.pass,
          error_count: result.errors.length
        })
      });
    } catch (error) {
      console.warn('Failed to send test result to API:', error);
    }
  }
}