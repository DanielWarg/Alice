// Barge-in Detection System för Alice B2
// Upptäcker när användaren avbryter Alice mitt i tal

export interface BargeInConfig {
  sensitivity: number; // 0.0-1.0, higher = more sensitive
  minConfidence: number; // Minimum confidence för barge-in trigger
  detectionWindowMs: number; // Window size för analysis
  voiceActivityThreshold: number; // Threshold för voice activity detection
  spectralAnalysisEnabled: boolean; // Use spectral features för better detection
  optimizedProcessing: boolean; // Enable performance optimizations
}

export interface BargeInEvent {
  timestamp: number;
  confidence: number;
  audioLevel: number;
  spectralFeatures?: SpectralFeatures;
  contextState: 'listening' | 'speaking' | 'processing';
}

export interface SpectralFeatures {
  fundamentalFreq: number;
  spectralCentroid: number;
  spectralRolloff: number;
  mfccCoefficients: number[];
  voiceProbability: number;
}

export interface VoiceActivityMetrics {
  energyLevel: number;
  zeroCrossingRate: number;
  spectralEnergy: number;
  signalToNoiseRatio: number;
  voiceActivityDetected: boolean;
}

export class BargeInDetector {
  private audioContext: AudioContext | null = null;
  private micStream: MediaStream | null = null;
  private analyserNode: AnalyserNode | null = null;
  private workletNode: AudioWorkletNode | null = null;
  
  // Configuration with optimizations
  private config: BargeInConfig;
  private isInitialized = false;
  private isMonitoring = false;
  private fastModeEnabled = false; // Skip heavy spectral analysis when possible
  
  // State management
  private currentState: 'listening' | 'speaking' | 'processing' = 'listening';
  private isAliceSpeaking = false;
  private lastBargeInTime = 0;
  private consecutiveDetections = 0;
  
  // Audio analysis buffers
  private audioBuffer: Float32Array;
  private frequencyData: Uint8Array;
  private timeData: Uint8Array;
  
  // Spectral analysis
  private fftSize = 2048;
  private windowFunction: Float32Array;
  private previousSpectrum: Float32Array;
  
  // Background noise profiling
  private noiseProfile: Float32Array;
  private noiseCalibrated = false;
  private calibrationSamples = 0;
  
  // Event handlers
  public onBargeInDetected: (event: BargeInEvent) => void = () => {};
  public onVoiceActivity: (metrics: VoiceActivityMetrics) => void = () => {};
  public onCalibrationComplete: () => void = () => {};
  public onError: (error: string) => void = () => {};

  constructor(config: Partial<BargeInConfig> = {}) {
    this.config = {
      sensitivity: 0.7,
      minConfidence: 0.8,
      detectionWindowMs: 150,
      voiceActivityThreshold: 0.02,
      spectralAnalysisEnabled: true,
      ...config
    };
    
    // Initialize buffers
    this.audioBuffer = new Float32Array(this.fftSize);
    this.frequencyData = new Uint8Array(this.fftSize / 2);
    this.timeData = new Uint8Array(this.fftSize);
    this.noiseProfile = new Float32Array(this.fftSize / 2);
    this.previousSpectrum = new Float32Array(this.fftSize / 2);
    
    // Create window function (Hann window)
    this.windowFunction = new Float32Array(this.fftSize);
    for (let i = 0; i < this.fftSize; i++) {
      this.windowFunction[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (this.fftSize - 1)));
    }
    
    console.log('🎯 BargeInDetector initialized with config:', this.config);
  }

  async initialize(micStream: MediaStream, audioContext: AudioContext): Promise<void> {
    try {
      this.audioContext = audioContext;
      this.micStream = micStream;
      
      // Set up audio analysis pipeline
      await this.setupAnalysisPipeline();
      
      // Start background noise calibration
      await this.startNoiseCalibration();
      
      this.isInitialized = true;
      console.log('✅ BargeInDetector initialized successfully');
      
    } catch (error) {
      const errorMsg = `Failed to initialize barge-in detector: ${error}`;
      console.error('❌', errorMsg);
      this.onError(errorMsg);
      throw error;
    }
  }

  private async setupAnalysisPipeline(): Promise<void> {
    if (!this.audioContext || !this.micStream) {
      throw new Error('Audio context or mic stream not available');
    }

    // Create mic input source
    const micSource = this.audioContext.createMediaStreamSource(this.micStream);
    
    // Create analyser node för frequency analysis
    this.analyserNode = this.audioContext.createAnalyser();
    this.analyserNode.fftSize = this.fftSize;
    this.analyserNode.smoothingTimeConstant = 0.3;
    this.analyserNode.minDecibels = -90;
    this.analyserNode.maxDecibels = -10;
    
    // Set up real-time processing worklet
    if (this.audioContext.audioWorklet) {
      await this.loadBargeInWorklet();
      
      this.workletNode = new AudioWorkletNode(this.audioContext, 'barge-in-processor', {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [1]
      });
      
      this.workletNode.port.onmessage = (event) => {
        this.handleWorkletMessage(event.data);
      };
      
      // Connect pipeline: Mic -> Analyser -> Worklet
      micSource.connect(this.analyserNode);
      this.analyserNode.connect(this.workletNode);
    } else {
      // Fallback för older browsers
      micSource.connect(this.analyserNode);
      this.startFallbackProcessing();
    }
    
    console.log('✅ Barge-in analysis pipeline setup complete');
  }

  private async loadBargeInWorklet(): Promise<void> {
    const workletCode = this.generateWorkletCode();
    const blob = new Blob([workletCode], { type: 'application/javascript' });
    const workletUrl = URL.createObjectURL(blob);
    
    try {
      await this.audioContext!.audioWorklet.addModule(workletUrl);
      console.log('✅ Barge-in detection worklet loaded');
    } finally {
      URL.revokeObjectURL(workletUrl);
    }
  }

  private generateWorkletCode(): string {
    return `
class BargeInProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.sensitivity = 0.7;
    this.voiceActivityThreshold = 0.02;
    this.detectionWindowSize = Math.floor(0.15 * sampleRate); // 150ms window
    this.audioBuffer = new Float32Array(this.detectionWindowSize);
    this.bufferIndex = 0;
    this.frameCount = 0;
    
    this.port.onmessage = (event) => {
      const { type, data } = event.data;
      switch (type) {
        case 'config':
          this.sensitivity = data.sensitivity || this.sensitivity;
          this.voiceActivityThreshold = data.voiceActivityThreshold || this.voiceActivityThreshold;
          break;
        case 'setAliceSpeaking':
          this.isAliceSpeaking = data.speaking;
          break;
      }
    };
  }
  
  process(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];
    
    if (input.length > 0 && output.length > 0) {
      const inputChannel = input[0];
      const outputChannel = output[0];
      
      // Copy input to output (pass-through)
      for (let i = 0; i < inputChannel.length; i++) {
        outputChannel[i] = inputChannel[i];
        
        // Store in circular buffer
        this.audioBuffer[this.bufferIndex] = inputChannel[i];
        this.bufferIndex = (this.bufferIndex + 1) % this.audioBuffer.length;
      }
      
      // Analyze every 512 samples (32ms at 16kHz)
      this.frameCount += inputChannel.length;
      if (this.frameCount >= 512) {
        this.frameCount = 0;
        this.analyzeAudioFrame();
      }
    }
    
    return true;
  }
  
  analyzeAudioFrame() {
    // Calculate RMS energy
    let energy = 0;
    for (let i = 0; i < this.audioBuffer.length; i++) {
      energy += this.audioBuffer[i] * this.audioBuffer[i];
    }
    energy = Math.sqrt(energy / this.audioBuffer.length);
    
    // Calculate zero crossing rate
    let zeroCrossings = 0;
    for (let i = 1; i < this.audioBuffer.length; i++) {
      if ((this.audioBuffer[i] >= 0) !== (this.audioBuffer[i-1] >= 0)) {
        zeroCrossings++;
      }
    }
    const zcr = zeroCrossings / this.audioBuffer.length;
    
    // Voice activity detection
    const voiceActivityDetected = energy > this.voiceActivityThreshold && zcr > 0.01 && zcr < 0.8;
    
    // Barge-in detection (only when Alice is speaking)
    let bargeInConfidence = 0;
    if (this.isAliceSpeaking && voiceActivityDetected) {
      // Calculate confidence based on energy and spectral characteristics
      const energyConfidence = Math.min(1, energy / (this.voiceActivityThreshold * 5));
      const zcrConfidence = zcr > 0.1 && zcr < 0.4 ? 1 : 0.5; // Human speech typically 0.1-0.4
      
      bargeInConfidence = (energyConfidence * 0.7 + zcrConfidence * 0.3) * this.sensitivity;
    }
    
    // Send analysis results to main thread
    this.port.postMessage({
      type: 'analysis',
      data: {
        timestamp: currentTime * 1000,
        energy,
        zeroCrossingRate: zcr,
        voiceActivityDetected,
        bargeInConfidence,
        isAliceSpeaking: this.isAliceSpeaking
      }
    });
  }
}

registerProcessor('barge-in-processor', BargeInProcessor);
`;
  }

  private handleWorkletMessage(data: any): void {
    const { type, data: analysisData } = data;
    
    if (type === 'analysis') {
      this.processAnalysisResults(analysisData);
    }
  }

  private processAnalysisResults(data: any): void {
    const {
      timestamp,
      energy,
      zeroCrossingRate,
      voiceActivityDetected,
      bargeInConfidence,
      isAliceSpeaking
    } = data;
    
    // Update voice activity metrics
    const metrics: VoiceActivityMetrics = {
      energyLevel: energy,
      zeroCrossingRate,
      spectralEnergy: this.calculateSpectralEnergy(),
      signalToNoiseRatio: this.calculateSNR(energy),
      voiceActivityDetected
    };
    
    this.onVoiceActivity(metrics);
    
    // Check för barge-in detection
    if (isAliceSpeaking && bargeInConfidence > this.config.minConfidence) {
      this.consecutiveDetections++;
      
      // Require multiple consecutive detections för stability
      if (this.consecutiveDetections >= 3) {
        this.triggerBargeIn(timestamp, bargeInConfidence, energy);
        this.consecutiveDetections = 0;
      }
    } else {
      this.consecutiveDetections = 0;
    }
  }

  private calculateSpectralEnergy(): number {
    if (!this.analyserNode) return 0;
    
    this.analyserNode.getByteFrequencyData(this.frequencyData);
    
    let spectralEnergy = 0;
    for (let i = 0; i < this.frequencyData.length; i++) {
      spectralEnergy += this.frequencyData[i] / 255;
    }
    
    return spectralEnergy / this.frequencyData.length;
  }

  private calculateSNR(signalEnergy: number): number {
    if (!this.noiseCalibrated || signalEnergy === 0) return 0;
    
    // Calculate average noise energy
    let noiseEnergy = 0;
    for (let i = 0; i < this.noiseProfile.length; i++) {
      noiseEnergy += this.noiseProfile[i];
    }
    noiseEnergy /= this.noiseProfile.length;
    
    return noiseEnergy > 0 ? 20 * Math.log10(signalEnergy / noiseEnergy) : 0;
  }

  private triggerBargeIn(timestamp: number, confidence: number, audioLevel: number): void {
    // Prevent rapid-fire triggers
    if (timestamp - this.lastBargeInTime < 500) return;
    
    this.lastBargeInTime = timestamp;
    
    const bargeInEvent: BargeInEvent = {
      timestamp,
      confidence,
      audioLevel,
      contextState: this.currentState
    };
    
    // Add spectral features if enabled
    if (this.config.spectralAnalysisEnabled) {
      bargeInEvent.spectralFeatures = this.extractSpectralFeatures();
    }
    
    console.log('🎯 Barge-in detected!', {
      confidence: confidence.toFixed(3),
      audioLevel: audioLevel.toFixed(3),
      state: this.currentState
    });
    
    this.onBargeInDetected(bargeInEvent);
  }

  private extractSpectralFeatures(): SpectralFeatures {
    if (!this.analyserNode) {
      return {
        fundamentalFreq: 0,
        spectralCentroid: 0,
        spectralRolloff: 0,
        mfccCoefficients: [],
        voiceProbability: 0
      };
    }
    
    this.analyserNode.getByteFrequencyData(this.frequencyData);
    
    // Calculate spectral centroid
    let weightedSum = 0;
    let magnitudeSum = 0;
    
    for (let i = 0; i < this.frequencyData.length; i++) {
      const magnitude = this.frequencyData[i] / 255;
      const frequency = (i * this.audioContext!.sampleRate) / (2 * this.frequencyData.length);
      
      weightedSum += frequency * magnitude;
      magnitudeSum += magnitude;
    }
    
    const spectralCentroid = magnitudeSum > 0 ? weightedSum / magnitudeSum : 0;
    
    // Calculate spectral rolloff (95% energy point)
    let cumulativeEnergy = 0;
    let totalEnergy = magnitudeSum;
    let rolloffFreq = 0;
    
    for (let i = 0; i < this.frequencyData.length; i++) {
      cumulativeEnergy += this.frequencyData[i] / 255;
      if (cumulativeEnergy >= 0.95 * totalEnergy) {
        rolloffFreq = (i * this.audioContext!.sampleRate) / (2 * this.frequencyData.length);
        break;
      }
    }
    
    // Estimate voice probability based on spectral characteristics
    const voiceProbability = this.estimateVoiceProbability(spectralCentroid, rolloffFreq);
    
    return {
      fundamentalFreq: this.findFundamentalFrequency(),
      spectralCentroid,
      spectralRolloff: rolloffFreq,
      mfccCoefficients: this.calculateMFCC(),
      voiceProbability
    };
  }

  private findFundamentalFrequency(): number {
    if (!this.analyserNode) return 0;
    
    this.analyserNode.getByteFrequencyData(this.frequencyData);
    
    let maxMagnitude = 0;
    let fundamentalBin = 0;
    
    // Look for fundamental in voice range (80-300 Hz)
    const minBin = Math.floor(80 * this.frequencyData.length * 2 / this.audioContext!.sampleRate);
    const maxBin = Math.floor(300 * this.frequencyData.length * 2 / this.audioContext!.sampleRate);
    
    for (let i = minBin; i < Math.min(maxBin, this.frequencyData.length); i++) {
      if (this.frequencyData[i] > maxMagnitude) {
        maxMagnitude = this.frequencyData[i];
        fundamentalBin = i;
      }
    }
    
    return (fundamentalBin * this.audioContext!.sampleRate) / (2 * this.frequencyData.length);
  }

  private calculateMFCC(): number[] {
    // Simplified MFCC calculation för voice characteristics
    // In production, this would use proper mel-scale filterbank
    const mfcc = new Array(13).fill(0);
    
    if (this.analyserNode) {
      this.analyserNode.getByteFrequencyData(this.frequencyData);
      
      // Simple approximation - group frequencies into mel-scale bands
      const bandsPerCoeff = Math.floor(this.frequencyData.length / 13);
      
      for (let coeff = 0; coeff < 13; coeff++) {
        let bandEnergy = 0;
        const startBin = coeff * bandsPerCoeff;
        const endBin = Math.min((coeff + 1) * bandsPerCoeff, this.frequencyData.length);
        
        for (let bin = startBin; bin < endBin; bin++) {
          bandEnergy += this.frequencyData[bin] / 255;
        }
        
        mfcc[coeff] = bandEnergy / (endBin - startBin);
      }
    }
    
    return mfcc;
  }

  private estimateVoiceProbability(centroid: number, rolloff: number): number {
    // Voice characteristics:
    // - Spectral centroid typically 1000-4000 Hz
    // - Spectral rolloff typically 4000-8000 Hz
    
    let probability = 0;
    
    if (centroid >= 1000 && centroid <= 4000) {
      probability += 0.5;
    } else if (centroid >= 500 && centroid <= 6000) {
      probability += 0.3;
    }
    
    if (rolloff >= 4000 && rolloff <= 8000) {
      probability += 0.3;
    } else if (rolloff >= 3000 && rolloff <= 10000) {
      probability += 0.2;
    }
    
    // Additional 20% based on harmonic structure (simplified)
    probability += Math.min(0.2, this.calculateHarmonicScore());
    
    return Math.min(1, probability);
  }

  private calculateHarmonicScore(): number {
    // Simplified harmonic analysis
    // Real implementation would check för harmonic peaks
    return 0.1; // Placeholder
  }

  private async startNoiseCalibration(): Promise<void> {
    console.log('🎚️ Starting background noise calibration...');
    
    // Calibrate för 2 seconds
    const calibrationTime = 2000;
    const startTime = Date.now();
    
    const calibrateFrame = () => {
      if (!this.analyserNode) return;
      
      this.analyserNode.getByteFrequencyData(this.frequencyData);
      
      // Accumulate noise profile
      for (let i = 0; i < this.frequencyData.length; i++) {
        this.noiseProfile[i] += this.frequencyData[i] / 255;
      }
      
      this.calibrationSamples++;
      
      if (Date.now() - startTime < calibrationTime) {
        setTimeout(calibrateFrame, 50); // Sample every 50ms
      } else {
        // Average the accumulated samples
        for (let i = 0; i < this.noiseProfile.length; i++) {
          this.noiseProfile[i] /= this.calibrationSamples;
        }
        
        this.noiseCalibrated = true;
        console.log('✅ Noise calibration complete');
        this.onCalibrationComplete();
      }
    };
    
    calibrateFrame();
  }

  private startFallbackProcessing(): void {
    // Fallback processing för browsers without AudioWorklet
    const processFrame = () => {
      if (!this.isMonitoring || !this.analyserNode) return;
      
      this.analyserNode.getByteTimeDomainData(this.timeData);
      
      // Simple energy-based detection
      let energy = 0;
      for (let i = 0; i < this.timeData.length; i++) {
        const sample = (this.timeData[i] - 128) / 128;
        energy += sample * sample;
      }
      energy = Math.sqrt(energy / this.timeData.length);
      
      const voiceActivityDetected = energy > this.config.voiceActivityThreshold;
      
      if (this.isAliceSpeaking && voiceActivityDetected) {
        const confidence = Math.min(1, energy * this.config.sensitivity * 10);
        
        if (confidence > this.config.minConfidence) {
          this.triggerBargeIn(Date.now(), confidence, energy);
        }
      }
      
      setTimeout(processFrame, 32); // ~30 FPS
    };
    
    processFrame();
  }

  // Public interface methods

  startMonitoring(): void {
    if (!this.isInitialized) {
      throw new Error('BargeInDetector not initialized');
    }
    
    this.isMonitoring = true;
    
    // Configure worklet för monitoring
    if (this.workletNode) {
      this.workletNode.port.postMessage({
        type: 'config',
        data: {
          sensitivity: this.config.sensitivity,
          voiceActivityThreshold: this.config.voiceActivityThreshold
        }
      });
    }
    
    console.log('👂 Barge-in monitoring started');
  }

  stopMonitoring(): void {
    this.isMonitoring = false;
    console.log('⏹️ Barge-in monitoring stopped');
  }

  setAliceSpeakingState(speaking: boolean): void {
    this.isAliceSpeaking = speaking;
    
    if (this.workletNode) {
      this.workletNode.port.postMessage({
        type: 'setAliceSpeaking',
        data: { speaking }
      });
    }
    
    console.log(`🗣️ Alice speaking state: ${speaking}`);
  }

  setContextState(state: 'listening' | 'speaking' | 'processing'): void {
    this.currentState = state;
  }

  setSensitivity(sensitivity: number): void {
    this.config.sensitivity = Math.max(0, Math.min(1, sensitivity));
    
    if (this.workletNode) {
      this.workletNode.port.postMessage({
        type: 'config',
        data: { sensitivity: this.config.sensitivity }
      });
    }
    
    console.log(`🎚️ Barge-in sensitivity set to ${this.config.sensitivity}`);
  }

  setMinConfidence(confidence: number): void {
    this.config.minConfidence = Math.max(0, Math.min(1, confidence));
    console.log(`🎯 Minimum confidence set to ${this.config.minConfidence}`);
  }

  getConfig(): BargeInConfig {
    return { ...this.config };
  }

  isCurrentlySpeaking(): boolean {
    return this.isAliceSpeaking;
  }

  // Recalibrate noise profile
  async recalibrate(): Promise<void> {
    this.noiseProfile.fill(0);
    this.noiseCalibrated = false;
    this.calibrationSamples = 0;
    
    await this.startNoiseCalibration();
  }

  cleanup(): void {
    this.stopMonitoring();
    
    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    
    if (this.analyserNode) {
      this.analyserNode.disconnect();
      this.analyserNode = null;
    }
    
    this.isInitialized = false;
    console.log('🧹 BargeInDetector cleanup complete');
  }
}

// Utility class för testing barge-in detection
export class BargeInTester {
  static async testDetectionSpeed(detector: BargeInDetector): Promise<number> {
    console.log('🧪 Testing barge-in detection speed...');
    
    return new Promise((resolve) => {
      const startTime = Date.now();
      
      const originalHandler = detector.onBargeInDetected;
      detector.onBargeInDetected = (event: BargeInEvent) => {
        const detectionTime = Date.now() - startTime;
        detector.onBargeInDetected = originalHandler;
        console.log(`⚡ Detection time: ${detectionTime}ms`);
        resolve(detectionTime);
      };
      
      // Timeout after 5 seconds
      setTimeout(() => {
        detector.onBargeInDetected = originalHandler;
        resolve(-1); // Indicate failure
      }, 5000);
    });
  }

  static testFalsePositiveRate(detector: BargeInDetector, durationMs: number): Promise<number> {
    console.log(`🧪 Testing false positive rate över ${durationMs}ms...`);
    
    return new Promise((resolve) => {
      let falsePositives = 0;
      const startTime = Date.now();
      
      const originalHandler = detector.onBargeInDetected;
      detector.onBargeInDetected = (event: BargeInEvent) => {
        falsePositives++;
        console.log(`⚠️ False positive detected (confidence: ${event.confidence})`);
      };
      
      setTimeout(() => {
        detector.onBargeInDetected = originalHandler;
        const rate = falsePositives / (durationMs / 1000); // Per second
        console.log(`📊 False positive rate: ${rate.toFixed(2)} per second`);
        resolve(rate);
      }, durationMs);
    });
  }
}

export default BargeInDetector;