import { EventEmitter } from 'eventemitter3';
import {
  AudioChunk,
  VADResult,
  AudioFormat,
  VADInterface,
  VoiceProviderEvents
} from '../types';

/**
 * Voice Activity Detection implementation
 * Uses energy-based and zero-crossing rate analysis for voice detection
 */
export class VAD extends EventEmitter<VoiceProviderEvents> implements VADInterface {
  private config = {
    sampleRate: 16000,
    frameSize: 512,
    threshold: 0.3,
    minVoiceFrames: 3,
    minSilenceFrames: 5,
    energyThreshold: 0.01,
    zeroCrossingRateThreshold: 0.3
  };

  private isVoiceActive: boolean = false;
  private voiceFrameCount: number = 0;
  private silenceFrameCount: number = 0;
  private recentFrames: number[] = [];
  private maxRecentFrames: number = 10;
  private lastVADResult: VADResult | null = null;

  // Audio processing state
  private audioBuffer: Buffer = Buffer.alloc(0);
  private previousSample: number = 0;

  constructor(config?: Partial<typeof VAD.prototype.config>) {
    super();
    if (config) {
      this.config = { ...this.config, ...config };
    }
  }

  /**
   * Initialize VAD with configuration
   */
  initialize(config?: {
    sampleRate?: number;
    frameSize?: number;
    threshold?: number;
  }): void {
    if (config) {
      this.config = { ...this.config, ...config };
    }

    // Reset state
    this.audioBuffer = Buffer.alloc(0);
    this.isVoiceActive = false;
    this.voiceFrameCount = 0;
    this.silenceFrameCount = 0;
    this.recentFrames = [];
    this.previousSample = 0;

    console.log(`[VAD] Initialized with config:`, this.config);
  }

  /**
   * Process audio chunk for voice activity detection
   */
  processAudio(chunk: AudioChunk): VADResult {
    // Ensure chunk format is compatible
    if (chunk.format.sampleRate !== this.config.sampleRate) {
      console.warn(`[VAD] Sample rate mismatch: expected ${this.config.sampleRate}, got ${chunk.format.sampleRate}`);
    }

    // Add to audio buffer
    this.audioBuffer = Buffer.concat([this.audioBuffer, chunk.data]);

    // Process all available frames
    let lastResult = this.lastVADResult || this.createVADResult(false, 0, chunk.timestamp);

    while (this.audioBuffer.length >= this.config.frameSize * 2) { // 2 bytes per 16-bit sample
      const frameResult = this.processFrame(chunk.timestamp);
      if (frameResult) {
        lastResult = frameResult;
      }
    }

    this.lastVADResult = lastResult;
    return lastResult;
  }

  /**
   * Set voice activity threshold
   */
  setThreshold(threshold: number): void {
    if (threshold < 0 || threshold > 1) {
      throw new Error('Threshold must be between 0 and 1');
    }
    this.config.threshold = threshold;
  }

  /**
   * Get current configuration
   */
  getConfig(): {
    sampleRate: number;
    frameSize: number;
    threshold: number;
  } {
    return {
      sampleRate: this.config.sampleRate,
      frameSize: this.config.frameSize,
      threshold: this.config.threshold
    };
  }

  /**
   * Check if voice is currently active
   */
  isCurrentlyActive(): boolean {
    return this.isVoiceActive;
  }

  /**
   * Get recent voice activity confidence
   */
  getRecentConfidence(): number {
    if (this.recentFrames.length === 0) return 0;
    
    const sum = this.recentFrames.reduce((acc, val) => acc + val, 0);
    return sum / this.recentFrames.length;
  }

  /**
   * Reset VAD state
   */
  reset(): void {
    this.audioBuffer = Buffer.alloc(0);
    this.isVoiceActive = false;
    this.voiceFrameCount = 0;
    this.silenceFrameCount = 0;
    this.recentFrames = [];
    this.previousSample = 0;
    this.lastVADResult = null;
  }

  /**
   * Process a single audio frame
   */
  private processFrame(timestamp: number): VADResult | null {
    const frameSizeBytes = this.config.frameSize * 2; // 2 bytes per 16-bit sample
    
    if (this.audioBuffer.length < frameSizeBytes) {
      return null;
    }

    // Extract frame
    const frameBuffer = this.audioBuffer.slice(0, frameSizeBytes);
    this.audioBuffer = this.audioBuffer.slice(frameSizeBytes);

    // Convert to samples
    const samples = this.bufferToSamples(frameBuffer);

    // Calculate features
    const energy = this.calculateEnergy(samples);
    const zeroCrossingRate = this.calculateZeroCrossingRate(samples);
    const spectralCentroid = this.calculateSpectralCentroid(samples);

    // Combine features for voice activity decision
    const confidence = this.calculateVoiceConfidence(energy, zeroCrossingRate, spectralCentroid);

    // Update recent frames for smoothing
    this.recentFrames.push(confidence);
    if (this.recentFrames.length > this.maxRecentFrames) {
      this.recentFrames.shift();
    }

    // Smoothed confidence
    const smoothedConfidence = this.getRecentConfidence();

    // Voice activity decision with hysteresis
    const wasVoiceActive = this.isVoiceActive;
    const voiceDetected = smoothedConfidence > this.config.threshold;

    if (voiceDetected) {
      this.voiceFrameCount++;
      this.silenceFrameCount = 0;
      
      if (!this.isVoiceActive && this.voiceFrameCount >= this.config.minVoiceFrames) {
        this.isVoiceActive = true;
      }
    } else {
      this.silenceFrameCount++;
      this.voiceFrameCount = 0;
      
      if (this.isVoiceActive && this.silenceFrameCount >= this.config.minSilenceFrames) {
        this.isVoiceActive = false;
      }
    }

    const result = this.createVADResult(
      this.isVoiceActive,
      smoothedConfidence,
      timestamp,
      energy
    );

    // Emit events on state changes
    if (!wasVoiceActive && this.isVoiceActive) {
      this.emit('voice_start', result);
    } else if (wasVoiceActive && !this.isVoiceActive) {
      this.emit('voice_end', result);
    }

    this.emit('vad_result', result);

    return result;
  }

  /**
   * Convert buffer to 16-bit samples
   */
  private bufferToSamples(buffer: Buffer): number[] {
    const samples: number[] = [];
    for (let i = 0; i < buffer.length; i += 2) {
      const sample = buffer.readInt16LE(i) / 32768.0; // Normalize to [-1, 1]
      samples.push(sample);
    }
    return samples;
  }

  /**
   * Calculate RMS energy of audio frame
   */
  protected calculateEnergy(samples: number[]): number {
    const sumSquares = samples.reduce((sum, sample) => sum + sample * sample, 0);
    return Math.sqrt(sumSquares / samples.length);
  }

  /**
   * Calculate zero crossing rate
   */
  protected calculateZeroCrossingRate(samples: number[]): number {
    let crossings = 0;
    
    for (let i = 1; i < samples.length; i++) {
      if ((samples[i-1]! >= 0) !== (samples[i]! >= 0)) {
        crossings++;
      }
    }
    
    return crossings / (samples.length - 1);
  }

  /**
   * Calculate spectral centroid (simplified)
   */
  protected calculateSpectralCentroid(samples: number[]): number {
    // Simplified spectral centroid calculation
    // In a full implementation, this would use FFT
    let weightedSum = 0;
    let totalEnergy = 0;
    
    for (let i = 0; i < samples.length; i++) {
      const magnitude = Math.abs(samples[i]!);
      const frequency = i * (this.config.sampleRate / 2) / samples.length;
      
      weightedSum += frequency * magnitude;
      totalEnergy += magnitude;
    }
    
    return totalEnergy > 0 ? weightedSum / totalEnergy : 0;
  }

  /**
   * Calculate voice confidence from features
   */
  private calculateVoiceConfidence(
    energy: number,
    zeroCrossingRate: number,
    spectralCentroid: number
  ): number {
    let confidence = 0;

    // Energy contribution (40% weight)
    if (energy > this.config.energyThreshold) {
      confidence += 0.4 * Math.min(1, energy / this.config.energyThreshold);
    }

    // Zero crossing rate contribution (30% weight)
    // Voice typically has moderate ZCR (0.1-0.4)
    const zcr = zeroCrossingRate;
    if (zcr >= 0.05 && zcr <= 0.5) {
      const zcrScore = zcr < this.config.zeroCrossingRateThreshold ? 
        zcr / this.config.zeroCrossingRateThreshold :
        (1 - zcr) / (1 - this.config.zeroCrossingRateThreshold);
      confidence += 0.3 * zcrScore;
    }

    // Spectral centroid contribution (30% weight)
    // Voice typically has centroid in 200-2000 Hz range
    if (spectralCentroid >= 200 && spectralCentroid <= 4000) {
      let centroidScore = 0;
      if (spectralCentroid <= 2000) {
        centroidScore = (spectralCentroid - 200) / 1800;
      } else {
        centroidScore = (4000 - spectralCentroid) / 2000;
      }
      confidence += 0.3 * Math.max(0, centroidScore);
    }

    return Math.min(1, Math.max(0, confidence));
  }

  /**
   * Create VAD result object
   */
  private createVADResult(
    isActive: boolean,
    confidence: number,
    timestamp: number,
    energyLevel: number = 0
  ): VADResult {
    return {
      isVoiceActive: isActive,
      confidence,
      timestamp,
      energyLevel
    };
  }
}

/**
 * Advanced VAD with machine learning features (stub implementation)
 */
export class AdvancedVAD extends VAD {
  private modelLoaded: boolean = false;
  private features: number[][] = [];

  constructor(config?: Partial<VAD['config']>) {
    super(config);
    console.log('[AdvancedVAD] Created - ML features not yet implemented');
  }

  /**
   * Load ML model for voice activity detection
   */
  async loadModel(modelPath?: string): Promise<void> {
    console.log(`[AdvancedVAD] Would load ML model from: ${modelPath || 'default'}`);
    
    // Simulate model loading
    await new Promise(resolve => setTimeout(resolve, 100));
    
    this.modelLoaded = true;
    console.log('[AdvancedVAD] ML model loaded (stub)');
  }

  /**
   * Process audio with ML-enhanced VAD
   */
  processAudio(chunk: AudioChunk): VADResult {
    const baseResult = super.processAudio(chunk);

    if (this.modelLoaded) {
      // TODO: Implement ML-based VAD enhancement
      // This would:
      // 1. Extract additional features (MFCC, pitch, formants)
      // 2. Run features through trained model
      // 3. Combine with traditional VAD results
      
      // For now, just add slight confidence boost
      baseResult.confidence = Math.min(1, baseResult.confidence * 1.1);
    }

    return baseResult;
  }

  /**
   * Extract advanced features for ML model
   */
  private extractAdvancedFeatures(samples: number[]): number[] {
    // TODO: Implement MFCC, pitch detection, formant analysis
    // For now, return basic features
    const energy = this.calculateEnergy(samples);
    const zcr = this.calculateZeroCrossingRate(samples);
    const centroid = this.calculateSpectralCentroid(samples);
    
    return [energy, zcr, centroid];
  }
}

/**
 * WebRTC-based VAD wrapper
 */
export class WebRTCVAD extends EventEmitter<VoiceProviderEvents> implements VADInterface {
  private isInitialized: boolean = false;
  private sampleRate: number = 16000;
  private frameSize: number = 160; // 10ms at 16kHz
  private aggressiveness: number = 1; // 0-3, higher = more aggressive

  constructor(aggressiveness: number = 1) {
    super();
    this.aggressiveness = Math.max(0, Math.min(3, aggressiveness));
  }

  initialize(config?: {
    sampleRate?: number;
    frameSize?: number;
    threshold?: number;
  }): void {
    if (config?.sampleRate) {
      this.sampleRate = config.sampleRate;
    }
    
    if (config?.frameSize) {
      this.frameSize = config.frameSize;
    }

    console.log('[WebRTCVAD] Initialized (stub) - WebRTC VAD not yet implemented');
    this.isInitialized = true;
  }

  processAudio(chunk: AudioChunk): VADResult {
    if (!this.isInitialized) {
      this.initialize();
    }

    // TODO: Implement actual WebRTC VAD integration
    // For now, use simple energy-based detection
    const samples = this.bufferToSamples(chunk.data);
    const energy = this.calculateEnergy(samples);
    const isActive = energy > 0.01;

    const result: VADResult = {
      isVoiceActive: isActive,
      confidence: Math.min(1, energy * 10),
      timestamp: chunk.timestamp,
      energyLevel: energy
    };

    this.emit('vad_result', result);
    
    if (isActive) {
      this.emit('voice_start', result);
    } else {
      this.emit('voice_end', result);
    }

    return result;
  }

  setThreshold(threshold: number): void {
    this.aggressiveness = Math.round(threshold * 3);
    console.log(`[WebRTCVAD] Set aggressiveness to ${this.aggressiveness}`);
  }

  getConfig(): {
    sampleRate: number;
    frameSize: number;
    threshold: number;
  } {
    return {
      sampleRate: this.sampleRate,
      frameSize: this.frameSize,
      threshold: this.aggressiveness / 3
    };
  }

  private bufferToSamples(buffer: Buffer): number[] {
    const samples: number[] = [];
    for (let i = 0; i < buffer.length; i += 2) {
      const sample = buffer.readInt16LE(i) / 32768.0;
      samples.push(sample);
    }
    return samples;
  }

  private calculateEnergy(samples: number[]): number {
    const sumSquares = samples.reduce((sum, sample) => sum + sample * sample, 0);
    return Math.sqrt(sumSquares / samples.length);
  }
}

/**
 * VAD factory for creating different VAD implementations
 */
export class VADFactory {
  /**
   * Create VAD instance
   */
  static create(
    type: 'basic' | 'advanced' | 'webrtc' = 'basic',
    config?: any
  ): VADInterface {
    switch (type) {
      case 'advanced':
        return new AdvancedVAD(config);
      
      case 'webrtc':
        return new WebRTCVAD(config?.aggressiveness);
      
      case 'basic':
      default:
        return new VAD(config);
    }
  }

  /**
   * Get recommended VAD type for use case
   */
  static getRecommendedType(useCase: 'realtime' | 'accuracy' | 'performance'): string {
    switch (useCase) {
      case 'realtime':
        return 'webrtc';
      case 'accuracy':
        return 'advanced';
      case 'performance':
      default:
        return 'basic';
    }
  }
}

/**
 * VAD utilities
 */
export class VADUtils {
  /**
   * Test VAD with sample audio
   */
  static testVAD(vad: VADInterface, testAudio: AudioChunk[]): VADResult[] {
    const results: VADResult[] = [];
    
    for (const chunk of testAudio) {
      const result = vad.processAudio(chunk);
      results.push(result);
    }
    
    return results;
  }

  /**
   * Calculate VAD accuracy metrics
   */
  static calculateAccuracy(
    results: VADResult[],
    groundTruth: boolean[]
  ): {
    accuracy: number;
    precision: number;
    recall: number;
    f1Score: number;
  } {
    if (results.length !== groundTruth.length) {
      throw new Error('Results and ground truth arrays must have same length');
    }

    let truePositives = 0;
    let falsePositives = 0;
    let trueNegatives = 0;
    let falseNegatives = 0;

    for (let i = 0; i < results.length; i++) {
      const predicted = results[i]!.isVoiceActive;
      const actual = groundTruth[i]!;

      if (predicted && actual) truePositives++;
      else if (predicted && !actual) falsePositives++;
      else if (!predicted && !actual) trueNegatives++;
      else if (!predicted && actual) falseNegatives++;
    }

    const accuracy = (truePositives + trueNegatives) / results.length;
    const precision = truePositives / (truePositives + falsePositives) || 0;
    const recall = truePositives / (truePositives + falseNegatives) || 0;
    const f1Score = 2 * (precision * recall) / (precision + recall) || 0;

    return { accuracy, precision, recall, f1Score };
  }

  /**
   * Generate test audio for VAD testing
   */
  static generateTestAudio(
    sampleRate: number = 16000,
    durationMs: number = 5000,
    voiceSegments: Array<{ start: number; end: number }> = []
  ): { audio: AudioChunk[]; groundTruth: boolean[] } {
    const totalSamples = Math.floor(sampleRate * durationMs / 1000);
    const chunkSize = Math.floor(sampleRate * 0.02); // 20ms chunks
    const chunks: AudioChunk[] = [];
    const groundTruth: boolean[] = [];

    for (let offset = 0; offset < totalSamples; offset += chunkSize) {
      const currentTimeMs = (offset / sampleRate) * 1000;
      const isVoiceSegment = voiceSegments.some(
        segment => currentTimeMs >= segment.start && currentTimeMs <= segment.end
      );

      // Generate audio data
      const buffer = Buffer.alloc(chunkSize * 2); // 16-bit samples
      
      for (let i = 0; i < chunkSize; i++) {
        let sample = 0;
        
        if (isVoiceSegment) {
          // Generate speech-like signal (multiple frequencies)
          const t = (offset + i) / sampleRate;
          sample = 0.3 * Math.sin(2 * Math.PI * 440 * t) + // Base frequency
                   0.2 * Math.sin(2 * Math.PI * 880 * t) + // Harmonic
                   0.1 * Math.sin(2 * Math.PI * 1320 * t); // Another harmonic
          
          // Add some noise
          sample += (Math.random() - 0.5) * 0.1;
        } else {
          // Generate background noise
          sample = (Math.random() - 0.5) * 0.05;
        }
        
        const sample16bit = Math.floor(sample * 32767);
        buffer.writeInt16LE(sample16bit, i * 2);
      }

      const chunk: AudioChunk = {
        data: buffer,
        format: {
          sampleRate,
          channels: 1,
          bitDepth: 16,
          encoding: 'pcm'
        },
        timestamp: Date.now() + currentTimeMs,
        duration: (chunkSize / sampleRate) * 1000
      };

      chunks.push(chunk);
      groundTruth.push(isVoiceSegment);
    }

    return { audio: chunks, groundTruth };
  }
}

/**
 * Create a basic VAD instance
 */
export function createVAD(config?: Partial<VAD['config']>): VAD {
  return new VAD(config);
}

/**
 * Create an advanced VAD instance
 */
export function createAdvancedVAD(config?: Partial<VAD['config']>): AdvancedVAD {
  return new AdvancedVAD(config);
}

/**
 * Create a WebRTC VAD instance
 */
export function createWebRTCVAD(aggressiveness: number = 1): WebRTCVAD {
  return new WebRTCVAD(aggressiveness);
}