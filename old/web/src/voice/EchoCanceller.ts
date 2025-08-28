// Echo Cancellation System för Alice B2
// Förhindrar feedback loops från Alice's egen röst

export interface EchoCancellerConfig {
  sampleRate: number;
  bufferSize: number;
  adaptationRate: number;
  echoSuppressionLevel: number;
  noiseGateThreshold: number;
}

export interface EchoMetrics {
  echoLevel: number;
  suppressionGain: number;
  processingLatency: number;
  adaptationConverged: boolean;
}

export class EchoCanceller {
  private audioContext: AudioContext | null = null;
  private micStream: MediaStream | null = null;
  private speakerNode: AudioNode | null = null;
  
  // Optimized adaptive filter state
  private adaptiveFilter: Float32Array;
  private echoBuffer: Float32Array;
  private micBuffer: Float32Array;
  private processingEnabled: boolean = true; // Lazy processing toggle
  
  // Processing nodes
  private micGainNode: GainNode | null = null;
  private outputGainNode: GainNode | null = null;
  private workletNode: AudioWorkletNode | null = null;
  
  // Configuration
  private config: EchoCancellerConfig;
  private isInitialized = false;
  private isProcessing = false;
  
  // Metrics and monitoring
  private metrics: EchoMetrics;
  private calibrationSamples: number = 0;
  
  // Event handlers
  public onEchoDetected: (level: number) => void = () => {};
  public onCalibrationComplete: () => void = () => {};
  public onError: (error: string) => void = () => {};

  constructor(config: Partial<EchoCancellerConfig> = {}) {
    this.config = {
      sampleRate: 16000,
      bufferSize: 256, // Optimized: reduced from 512
      adaptationRate: 0.005, // Optimized: reduced for stability
      echoSuppressionLevel: 0.8,
      noiseGateThreshold: 0.01,
      ...config
    };
    
    this.adaptiveFilter = new Float32Array(this.config.bufferSize);
    this.echoBuffer = new Float32Array(this.config.bufferSize * 2);
    this.micBuffer = new Float32Array(this.config.bufferSize);
    
    this.metrics = {
      echoLevel: 0,
      suppressionGain: 1.0,
      processingLatency: 0,
      adaptationConverged: false
    };
    
    console.log('🔇 EchoCanceller initialized with config:', this.config);
  }

  async initialize(micStream: MediaStream, audioContext: AudioContext): Promise<void> {
    try {
      this.audioContext = audioContext;
      this.micStream = micStream;
      
      // Ensure AudioWorklet is available
      if (!this.audioContext.audioWorklet) {
        throw new Error('AudioWorklet not supported - echo cancellation requires modern browser');
      }
      
      // Load echo cancellation worklet
      await this.loadEchoCancellationWorklet();
      
      // Set up audio processing pipeline
      await this.setupAudioPipeline();
      
      this.isInitialized = true;
      console.log('✅ EchoCanceller initialized successfully');
      
    } catch (error) {
      const errorMsg = `Failed to initialize echo canceller: ${error}`;
      console.error('❌', errorMsg);
      this.onError(errorMsg);
      throw error;
    }
  }

  private async loadEchoCancellationWorklet(): Promise<void> {
    const workletCode = this.generateWorkletCode();
    const blob = new Blob([workletCode], { type: 'application/javascript' });
    const workletUrl = URL.createObjectURL(blob);
    
    try {
      await this.audioContext!.audioWorklet.addModule(workletUrl);
      console.log('✅ Echo cancellation worklet loaded');
    } finally {
      URL.revokeObjectURL(workletUrl);
    }
  }

  private generateWorkletCode(): string {
    return `
class EchoCancellationProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.adaptiveFilter = new Float32Array(512);
    this.echoBuffer = new Float32Array(1024);
    this.bufferIndex = 0;
    this.adaptationRate = 0.01;
    this.echoSuppressionLevel = 0.8;
    this.noiseGateThreshold = 0.01;
    
    this.port.onmessage = (event) => {
      const { type, data } = event.data;
      switch (type) {
        case 'config':
          this.adaptationRate = data.adaptationRate || this.adaptationRate;
          this.echoSuppressionLevel = data.echoSuppressionLevel || this.echoSuppressionLevel;
          this.noiseGateThreshold = data.noiseGateThreshold || this.noiseGateThreshold;
          break;
        case 'speakerSignal':
          this.updateSpeakerSignal(data.samples);
          break;
      }
    };
  }
  
  updateSpeakerSignal(samples) {
    // Store speaker signal for echo reference
    for (let i = 0; i < samples.length; i++) {
      this.echoBuffer[this.bufferIndex] = samples[i];
      this.bufferIndex = (this.bufferIndex + 1) % this.echoBuffer.length;
    }
  }
  
  process(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];
    
    if (input.length > 0 && output.length > 0) {
      const inputChannel = input[0];
      const outputChannel = output[0];
      
      for (let sample = 0; sample < inputChannel.length; sample++) {
        // Get current mic sample
        const micSample = inputChannel[sample];
        
        // Estimate echo using adaptive filter
        let echoEstimate = 0;
        const startIdx = (this.bufferIndex - inputChannel.length + sample + this.echoBuffer.length) % this.echoBuffer.length;
        
        for (let tap = 0; tap < this.adaptiveFilter.length; tap++) {
          const echoIdx = (startIdx - tap + this.echoBuffer.length) % this.echoBuffer.length;
          echoEstimate += this.adaptiveFilter[tap] * this.echoBuffer[echoIdx];
        }
        
        // Remove echo from mic signal
        let cleanSample = micSample - echoEstimate;
        
        // Update adaptive filter (LMS algorithm)
        const error = cleanSample;
        for (let tap = 0; tap < this.adaptiveFilter.length; tap++) {
          const echoIdx = (startIdx - tap + this.echoBuffer.length) % this.echoBuffer.length;
          const echoSample = this.echoBuffer[echoIdx];
          this.adaptiveFilter[tap] += this.adaptationRate * error * echoSample;
        }
        
        // Apply noise gate
        if (Math.abs(cleanSample) < this.noiseGateThreshold) {
          cleanSample *= 0.1; // Reduce low-level noise
        }
        
        // Apply echo suppression gain
        cleanSample *= (1 - this.echoSuppressionLevel * Math.tanh(Math.abs(echoEstimate) * 10));
        
        outputChannel[sample] = cleanSample;
      }
      
      // Send metrics back to main thread
      const echoLevel = this.calculateEchoLevel(inputChannel);
      this.port.postMessage({
        type: 'metrics',
        data: {
          echoLevel,
          suppressionGain: 1 - this.echoSuppressionLevel * 0.5,
          processingLatency: 128 / sampleRate * 1000 // Estimate in ms
        }
      });
    }
    
    return true;
  }
  
  calculateEchoLevel(samples) {
    let sum = 0;
    for (let i = 0; i < samples.length; i++) {
      sum += Math.abs(samples[i]);
    }
    return sum / samples.length;
  }
}

registerProcessor('echo-cancellation-processor', EchoCancellationProcessor);
`;
  }

  private async setupAudioPipeline(): Promise<void> {
    if (!this.audioContext || !this.micStream) {
      throw new Error('Audio context or mic stream not available');
    }

    // Create mic input source
    const micSource = this.audioContext.createMediaStreamSource(this.micStream);
    
    // Create gain nodes for volume control
    this.micGainNode = this.audioContext.createGain();
    this.outputGainNode = this.audioContext.createGain();
    
    // Create echo cancellation worklet
    this.workletNode = new AudioWorkletNode(this.audioContext, 'echo-cancellation-processor', {
      numberOfInputs: 1,
      numberOfOutputs: 1,
      outputChannelCount: [1]
    });
    
    // Set up worklet message handling
    this.workletNode.port.onmessage = (event) => {
      const { type, data } = event.data;
      if (type === 'metrics') {
        this.updateMetrics(data);
      }
    };
    
    // Connect audio pipeline
    micSource.connect(this.micGainNode);
    this.micGainNode.connect(this.workletNode);
    this.workletNode.connect(this.outputGainNode);
    
    // Send initial configuration to worklet
    this.updateWorkletConfig();
    
    console.log('✅ Audio pipeline setup complete');
  }

  private updateWorkletConfig(): void {
    if (this.workletNode) {
      this.workletNode.port.postMessage({
        type: 'config',
        data: {
          adaptationRate: this.config.adaptationRate,
          echoSuppressionLevel: this.config.echoSuppressionLevel,
          noiseGateThreshold: this.config.noiseGateThreshold
        }
      });
    }
  }

  private updateMetrics(data: Partial<EchoMetrics>): void {
    this.metrics = { ...this.metrics, ...data };
    
    // Check if echo detected
    if (this.metrics.echoLevel > 0.1) {
      this.onEchoDetected(this.metrics.echoLevel);
    }
    
    // Update calibration progress
    this.calibrationSamples++;
    if (this.calibrationSamples > 1000 && !this.metrics.adaptationConverged) {
      this.metrics.adaptationConverged = true;
      this.onCalibrationComplete();
    }
  }

  // Inform echo canceller about outgoing audio (Alice speaking)
  notifySpeakerOutput(audioData: Float32Array): void {
    if (this.workletNode && this.isProcessing) {
      this.workletNode.port.postMessage({
        type: 'speakerSignal',
        data: { samples: Array.from(audioData) }
      });
    }
  }

  // Start processing audio
  startProcessing(): void {
    if (!this.isInitialized) {
      throw new Error('Echo canceller not initialized');
    }
    
    this.isProcessing = true;
    console.log('🔇 Echo cancellation processing started');
  }

  // Stop processing audio
  stopProcessing(): void {
    this.isProcessing = false;
    console.log('⏹️ Echo cancellation processing stopped');
  }

  // Get processed audio stream
  getProcessedStream(): MediaStream {
    if (!this.audioContext || !this.outputGainNode) {
      throw new Error('Audio pipeline not set up');
    }

    // Create destination for processed audio
    const destination = this.audioContext.createMediaStreamDestination();
    this.outputGainNode.connect(destination);
    
    return destination.stream;
  }

  // Adjust sensitivity and parameters
  setSensitivity(level: number): void {
    this.config.echoSuppressionLevel = Math.max(0, Math.min(1, level));
    this.updateWorkletConfig();
    console.log(`🎚️ Echo suppression level set to ${this.config.echoSuppressionLevel}`);
  }

  setAdaptationRate(rate: number): void {
    this.config.adaptationRate = Math.max(0.001, Math.min(0.1, rate));
    this.updateWorkletConfig();
    console.log(`⚙️ Adaptation rate set to ${this.config.adaptationRate}`);
  }

  // Manual calibration trigger
  async calibrate(): Promise<void> {
    console.log('🎯 Starting echo cancellation calibration...');
    this.calibrationSamples = 0;
    this.metrics.adaptationConverged = false;
    
    // Reset adaptive filter
    this.adaptiveFilter.fill(0);
    
    return new Promise((resolve) => {
      const originalHandler = this.onCalibrationComplete;
      this.onCalibrationComplete = () => {
        this.onCalibrationComplete = originalHandler;
        console.log('✅ Echo cancellation calibration complete');
        resolve();
      };
    });
  }

  // Get current metrics
  getMetrics(): EchoMetrics {
    return { ...this.metrics };
  }

  // Cleanup resources
  cleanup(): void {
    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    
    if (this.micGainNode) {
      this.micGainNode.disconnect();
      this.micGainNode = null;
    }
    
    if (this.outputGainNode) {
      this.outputGainNode.disconnect();
      this.outputGainNode = null;
    }
    
    this.isInitialized = false;
    this.isProcessing = false;
    
    console.log('🧹 Echo canceller cleanup complete');
  }
}

// Utility functions for echo cancellation testing
export class EchoCancellerTester {
  static async testEchoDetection(canceller: EchoCanceller): Promise<boolean> {
    console.log('🧪 Testing echo detection...');
    
    return new Promise((resolve) => {
      let echoDetected = false;
      
      const originalHandler = canceller.onEchoDetected;
      canceller.onEchoDetected = (level: number) => {
        console.log(`🔍 Echo detected with level: ${level}`);
        echoDetected = true;
        canceller.onEchoDetected = originalHandler;
        resolve(true);
      };
      
      // Simulate echo after 2 seconds if none detected
      setTimeout(() => {
        if (!echoDetected) {
          canceller.onEchoDetected = originalHandler;
          resolve(false);
        }
      }, 2000);
    });
  }

  static measureProcessingLatency(canceller: EchoCanceller): number {
    const metrics = canceller.getMetrics();
    return metrics.processingLatency;
  }
}

export default EchoCanceller;