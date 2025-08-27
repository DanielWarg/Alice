#!/usr/bin/env node
/**
 * 🎚️ Audio Processor - Ducking & Echo Cancellation
 * Roadmap: Audio ducking (-18dB when TTS active) and echo cancellation
 */

import { EventEmitter } from 'events';

// Audio processing configuration
interface AudioProcessorConfig {
  sampleRate: number;
  frameSize: number;
  duckingLevel: number;      // -18dB = 0.125
  duckingRampMs: number;     // Transition time
  echoCancellation: boolean;
  adaptiveGain: boolean;
}

// Echo cancellation state
interface EchoCancellerState {
  enabled: boolean;
  speakerBuffer: Float32Array[];
  maxDelay: number;          // Max echo delay in samples
  adaptationRate: number;    // Learning rate for adaptation
  suppressionGain: number;   // How much to suppress detected echo
}

// Audio analysis metrics
interface AudioMetrics {
  inputLevel: number;
  outputLevel: number;
  echoSuppression: number;
  duckingActive: boolean;
  timestamp: number;
}

/**
 * Audio Processor with ducking and echo cancellation
 * Manages audio levels and prevents feedback loops
 */
export class AudioProcessor extends EventEmitter {
  private config: AudioProcessorConfig;
  private audioContext: AudioContext;
  
  // Audio nodes
  private inputGain: GainNode;
  private outputGain: GainNode;
  private duckingGain: GainNode;
  private analyserNode: AnalyserNode;
  
  // Echo canceller state
  private echoCanceller: EchoCancellerState;
  
  // Ducking state
  private isDucking = false;
  private duckingTimeout: NodeJS.Timeout | null = null;
  
  // Audio level monitoring
  private inputLevels: number[] = [];
  private outputLevels: number[] = [];
  
  // Metrics
  private metrics: AudioMetrics = {
    inputLevel: 0,
    outputLevel: 0,
    echoSuppression: 0,
    duckingActive: false,
    timestamp: Date.now()
  };

  constructor(audioContext: AudioContext, config: Partial<AudioProcessorConfig> = {}) {
    super();
    
    this.audioContext = audioContext;
    this.config = {
      sampleRate: 16000,
      frameSize: 320,        // 20ms frames
      duckingLevel: 0.125,   // -18dB per roadmap
      duckingRampMs: 100,    // 100ms ramp
      echoCancellation: true,
      adaptiveGain: true,
      ...config
    };
    
    this.setupAudioNodes();
    this.setupEchoCanceller();
    
    console.log(`🎚️ Audio Processor initialized: ducking=${this.config.duckingLevel.toFixed(3)} (-18dB), EC=${this.config.echoCancellation}`);
  }

  /**
   * Setup Web Audio API nodes
   */
  private setupAudioNodes(): void {
    // Input gain (microphone)
    this.inputGain = this.audioContext.createGain();
    this.inputGain.gain.value = 1.0;
    
    // Output gain (speakers)
    this.outputGain = this.audioContext.createGain(); 
    this.outputGain.gain.value = 1.0;
    
    // Ducking gain (reduces input during TTS)
    this.duckingGain = this.audioContext.createGain();
    this.duckingGain.gain.value = 1.0;
    
    // Analyser for level monitoring
    this.analyserNode = this.audioContext.createAnalyser();
    this.analyserNode.fftSize = 256;
    this.analyserNode.smoothingTimeConstant = 0.3;
    
    // Chain: Input → Ducking → Output → Destination
    this.inputGain.connect(this.duckingGain);
    this.duckingGain.connect(this.analyserNode);
    this.analyserNode.connect(this.outputGain);
    this.outputGain.connect(this.audioContext.destination);
  }

  /**
   * Setup echo canceller
   */
  private setupEchoCanceller(): void {
    this.echoCanceller = {
      enabled: this.config.echoCancellation,
      speakerBuffer: [],
      maxDelay: Math.floor(0.5 * this.config.sampleRate), // 500ms max delay
      adaptationRate: 0.01,
      suppressionGain: 0.5
    };
    
    console.log(`🔄 Echo Canceller: ${this.echoCanceller.enabled ? 'ENABLED' : 'DISABLED'}`);
  }

  /**
   * Connect input source (microphone)
   */
  connectInput(sourceNode: AudioNode): void {
    sourceNode.connect(this.inputGain);
    console.log('🎤 Input connected to audio processor');
  }

  /**
   * Connect output destination 
   */
  connectOutput(): GainNode {
    return this.outputGain;
  }

  /**
   * Enable audio ducking (reduce mic sensitivity during TTS)
   */
  enableDucking(duration?: number): void {
    if (this.isDucking) return;
    
    this.isDucking = true;
    const currentTime = this.audioContext.currentTime;
    const rampTime = this.config.duckingRampMs / 1000;
    
    // Exponential ramp down to ducking level
    this.duckingGain.gain.exponentialRampToValueAtTime(
      Math.max(this.config.duckingLevel, 0.001), // Avoid zero for exponential
      currentTime + rampTime
    );
    
    console.log(`🦆 Audio ducking ENABLED: ${Math.round(20 * Math.log10(this.config.duckingLevel))}dB`);
    
    // Auto-disable after duration
    if (duration) {
      this.duckingTimeout = setTimeout(() => {
        this.disableDucking();
      }, duration);
    }
    
    this.updateMetrics();
    this.emit('ducking.enabled', this.config.duckingLevel);
  }

  /**
   * Disable audio ducking (restore normal mic sensitivity)
   */
  disableDucking(): void {
    if (!this.isDucking) return;
    
    this.isDucking = false;
    const currentTime = this.audioContext.currentTime;
    const rampTime = this.config.duckingRampMs / 1000;
    
    // Clear timeout
    if (this.duckingTimeout) {
      clearTimeout(this.duckingTimeout);
      this.duckingTimeout = null;
    }
    
    // Exponential ramp up to normal level
    this.duckingGain.gain.exponentialRampToValueAtTime(
      1.0,
      currentTime + rampTime
    );
    
    console.log('🦆 Audio ducking DISABLED');
    this.updateMetrics();
    this.emit('ducking.disabled');
  }

  /**
   * Process audio frame with echo cancellation
   */
  processAudioFrame(inputSamples: Float32Array, speakerSamples?: Float32Array): Float32Array {
    if (!this.echoCanceller.enabled) {
      return inputSamples;
    }
    
    // Store speaker samples for echo cancellation
    if (speakerSamples) {
      this.addSpeakerSamples(speakerSamples);
    }
    
    // Apply echo cancellation
    const processedSamples = this.cancelEcho(inputSamples);
    
    // Update metrics
    this.trackAudioLevels(inputSamples, processedSamples);
    
    return processedSamples;
  }

  /**
   * Add speaker samples to echo cancellation buffer
   */
  private addSpeakerSamples(samples: Float32Array): void {
    this.echoCanceller.speakerBuffer.push(new Float32Array(samples));
    
    // Limit buffer size (prevent memory buildup)
    const maxBufferSize = Math.ceil(this.echoCanceller.maxDelay / this.config.frameSize);
    if (this.echoCanceller.speakerBuffer.length > maxBufferSize) {
      this.echoCanceller.speakerBuffer.shift();
    }
  }

  /**
   * Simple echo cancellation implementation
   */
  private cancelEcho(inputSamples: Float32Array): Float32Array {
    if (this.echoCanceller.speakerBuffer.length === 0) {
      return inputSamples;
    }
    
    const processedSamples = new Float32Array(inputSamples.length);
    let maxSuppression = 0;
    
    // Simple correlation-based echo detection
    for (let delay = 0; delay < Math.min(this.echoCanceller.speakerBuffer.length, 10); delay++) {
      const speakerSamples = this.echoCanceller.speakerBuffer[
        this.echoCanceller.speakerBuffer.length - 1 - delay
      ];
      
      if (!speakerSamples || speakerSamples.length !== inputSamples.length) continue;
      
      // Calculate correlation
      const correlation = this.calculateCorrelation(inputSamples, speakerSamples);
      
      if (correlation > 0.3) { // Echo detected
        const suppression = correlation * this.echoCanceller.suppressionGain;
        maxSuppression = Math.max(maxSuppression, suppression);
        
        // Subtract scaled speaker signal
        for (let i = 0; i < inputSamples.length; i++) {
          processedSamples[i] = inputSamples[i] - (speakerSamples[i] * suppression);
        }
      }
    }
    
    // If no echo detected, return original
    if (maxSuppression === 0) {
      processedSamples.set(inputSamples);
    }
    
    // Update metrics
    this.metrics.echoSuppression = maxSuppression;
    
    return processedSamples;
  }

  /**
   * Calculate correlation between two audio signals
   */
  private calculateCorrelation(signal1: Float32Array, signal2: Float32Array): number {
    if (signal1.length !== signal2.length) return 0;
    
    let sum1 = 0, sum2 = 0, sum1Sq = 0, sum2Sq = 0, pSum = 0;
    const n = signal1.length;
    
    for (let i = 0; i < n; i++) {
      sum1 += signal1[i];
      sum2 += signal2[i];
      sum1Sq += signal1[i] * signal1[i];
      sum2Sq += signal2[i] * signal2[i];
      pSum += signal1[i] * signal2[i];
    }
    
    const num = pSum - (sum1 * sum2 / n);
    const den = Math.sqrt((sum1Sq - sum1 * sum1 / n) * (sum2Sq - sum2 * sum2 / n));
    
    if (den === 0) return 0;
    return Math.abs(num / den); // Absolute correlation
  }

  /**
   * Track audio levels for monitoring
   */
  private trackAudioLevels(inputSamples: Float32Array, outputSamples: Float32Array): void {
    const inputLevel = this.calculateRMS(inputSamples);
    const outputLevel = this.calculateRMS(outputSamples);
    
    this.inputLevels.push(inputLevel);
    this.outputLevels.push(outputLevel);
    
    // Keep only last 100 measurements
    if (this.inputLevels.length > 100) {
      this.inputLevels.shift();
      this.outputLevels.shift();
    }
    
    // Update metrics
    this.metrics.inputLevel = inputLevel;
    this.metrics.outputLevel = outputLevel;
    this.metrics.timestamp = Date.now();
  }

  /**
   * Calculate RMS (Root Mean Square) level
   */
  private calculateRMS(samples: Float32Array): number {
    let sum = 0;
    for (let i = 0; i < samples.length; i++) {
      sum += samples[i] * samples[i];
    }
    return Math.sqrt(sum / samples.length);
  }

  /**
   * Update metrics
   */
  private updateMetrics(): void {
    this.metrics.duckingActive = this.isDucking;
    this.metrics.timestamp = Date.now();
    this.emit('metrics.updated', this.metrics);
  }

  /**
   * Set input gain level
   */
  setInputGain(gain: number): void {
    if (gain < 0 || gain > 2) {
      throw new Error('Input gain must be between 0 and 2');
    }
    
    this.inputGain.gain.setValueAtTime(gain, this.audioContext.currentTime);
    console.log(`🎚️ Input gain: ${gain.toFixed(2)} (${Math.round(20 * Math.log10(gain))}dB)`);
    this.emit('input.gain.changed', gain);
  }

  /**
   * Set output gain level
   */
  setOutputGain(gain: number): void {
    if (gain < 0 || gain > 2) {
      throw new Error('Output gain must be between 0 and 2');
    }
    
    this.outputGain.gain.setValueAtTime(gain, this.audioContext.currentTime);
    console.log(`🔊 Output gain: ${gain.toFixed(2)} (${Math.round(20 * Math.log10(gain))}dB)`);
    this.emit('output.gain.changed', gain);
  }

  /**
   * Get current audio metrics
   */
  getMetrics(): AudioMetrics {
    return { ...this.metrics };
  }

  /**
   * Get audio level statistics
   */
  getLevelStats() {
    if (this.inputLevels.length === 0) {
      return { input: 0, output: 0, ratio: 0 };
    }
    
    const avgInput = this.inputLevels.reduce((a, b) => a + b) / this.inputLevels.length;
    const avgOutput = this.outputLevels.reduce((a, b) => a + b) / this.outputLevels.length;
    
    return {
      input: avgInput,
      output: avgOutput,
      ratio: avgInput > 0 ? avgOutput / avgInput : 0,
      samples: this.inputLevels.length
    };
  }

  /**
   * Reset audio processor state
   */
  reset(): void {
    this.disableDucking();
    this.inputLevels = [];
    this.outputLevels = [];
    this.echoCanceller.speakerBuffer = [];
    
    this.inputGain.gain.setValueAtTime(1.0, this.audioContext.currentTime);
    this.outputGain.gain.setValueAtTime(1.0, this.audioContext.currentTime);
    
    console.log('🔄 Audio processor reset');
    this.emit('reset');
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.disableDucking();
    
    if (this.duckingTimeout) {
      clearTimeout(this.duckingTimeout);
    }
    
    // Disconnect nodes
    this.inputGain.disconnect();
    this.duckingGain.disconnect();
    this.analyserNode.disconnect();
    this.outputGain.disconnect();
    
    console.log('🧹 Audio processor cleanup complete');
  }
}

// Export types
export type { AudioProcessorConfig, EchoCancellerState, AudioMetrics };