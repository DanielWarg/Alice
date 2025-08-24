// Enhanced Orchestrator för Alice B2 - Barge-in & Echo-skydd
// Extends B1 Orchestrator with echo cancellation and barge-in detection

import { RealtimeASR, ASREvent } from './RealtimeASR';
import { AmbientBuffer, AmbientEvent } from './AmbientBuffer';
import EchoCanceller, { EchoCancellerConfig, EchoMetrics } from './EchoCanceller';
import BargeInDetector, { BargeInConfig, BargeInEvent, VoiceActivityMetrics } from './BargeInDetector';
import AudioStateManager, { AudioState, StateContext, StateTransition } from './AudioStateManager';

export interface EnhancedOrchestratorConfig extends OrchestratorConfig {
  // Echo cancellation settings
  echoCancellation: {
    enabled: boolean;
    adaptationRate: number;
    suppressionLevel: number;
    noiseGateThreshold: number;
  };
  
  // Barge-in detection settings
  bargeInDetection: {
    enabled: boolean;
    sensitivity: number;
    minConfidence: number;
    detectionWindowMs: number;
  };
  
  // Audio processing settings
  audioProcessing: {
    lowLatencyMode: boolean;
    bufferSize: number;
    sampleRate: number;
    enableSpectralAnalysis: boolean;
  };
  
  // Conversation flow settings
  conversationFlow: {
    maxSpeakingTime: number; // ms
    interruptionTimeout: number; // ms
    processingTimeout: number; // ms
    autoResumeEnabled: boolean;
  };
}

interface OrchestratorConfig {
  voiceMode: 'always' | 'ptt';
  asrBackend: 'realtime' | 'browser';
  ambientEnabled: boolean;
  echoCancellation: boolean;
  noiseSuppression: boolean;
  autoGainControl: boolean;
}

export interface EnhancedOrchestratorStatus {
  // Core status från B1
  micPermission: 'pending' | 'granted' | 'denied';
  asrStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  isListening: boolean;
  lastPartial?: string;
  bufferStats?: {
    totalChunks: number;
    highScoreChunks: number;
  };
  
  // B2 enhancements
  audioState: AudioState;
  echoCancellation: {
    enabled: boolean;
    active: boolean;
    metrics: EchoMetrics;
  };
  bargeInDetection: {
    enabled: boolean;
    monitoring: boolean;
    sensitivity: number;
    lastDetection?: BargeInEvent;
  };
  conversationFlow: {
    currentlySpeaking: boolean;
    canBeInterrupted: boolean;
    interruptedContent?: string;
  };
}

export interface EnhancedOrchestratorEvent {
  type: 'status_change' | 'barge_in_detected' | 'echo_detected' | 'state_changed' | 'conversation_interrupted';
  status?: EnhancedOrchestratorStatus;
  bargeInEvent?: BargeInEvent;
  echoLevel?: number;
  stateTransition?: StateTransition;
  interruptionData?: {
    userInput: string;
    confidence: number;
    resumeContent?: string;
  };
  ts: Date;
}

export class EnhancedOrchestrator {
  // Core B1 components
  private realtimeASR: RealtimeASR | null = null;
  private ambientBuffer: AmbientBuffer | null = null;
  
  // B2 enhancements
  private echoCanceller: EchoCanceller | null = null;
  private bargeInDetector: BargeInDetector | null = null;
  private audioStateManager: AudioStateManager;
  
  // Audio context and streams
  private audioContext: AudioContext | null = null;
  private micStream: MediaStream | null = null;
  private processedStream: MediaStream | null = null;
  
  // Configuration
  private config: EnhancedOrchestratorConfig;
  private isInitialized = false;
  private isActive = false;
  
  // State tracking
  private currentStatus: EnhancedOrchestratorStatus;
  
  // Event handlers
  public onEvent: (event: EnhancedOrchestratorEvent) => void = () => {};
  public onError: (error: string) => void = () => {};
  
  // Alice speaking integration
  public onAliceStartSpeaking: (content: string) => void = () => {};
  public onAliceStopSpeaking: () => void = () => {};

  constructor(config: Partial<EnhancedOrchestratorConfig> = {}) {
    // Default configuration
    this.config = {
      // B1 base config
      voiceMode: 'always',
      asrBackend: 'realtime',
      ambientEnabled: true,
      echoCancellation: false, // Will be overridden by B2 config
      noiseSuppression: true,
      autoGainControl: true,
      
      // B2 enhancements
      echoCancellation: {
        enabled: true,
        adaptationRate: 0.01,
        suppressionLevel: 0.8,
        noiseGateThreshold: 0.01,
        ...config.echoCancellation
      },
      
      bargeInDetection: {
        enabled: true,
        sensitivity: 0.7,
        minConfidence: 0.8,
        detectionWindowMs: 150,
        ...config.bargeInDetection
      },
      
      audioProcessing: {
        lowLatencyMode: true,
        bufferSize: 512,
        sampleRate: 16000,
        enableSpectralAnalysis: true,
        ...config.audioProcessing
      },
      
      conversationFlow: {
        maxSpeakingTime: 30000,
        interruptionTimeout: 5000,
        processingTimeout: 10000,
        autoResumeEnabled: true,
        ...config.conversationFlow
      },
      
      ...config
    };
    
    // Initialize state manager
    this.audioStateManager = new AudioStateManager();
    this.setupStateManagerHandlers();
    
    // Initialize status
    this.currentStatus = {
      micPermission: 'pending',
      asrStatus: 'disconnected',
      isListening: false,
      audioState: 'listening',
      echoCancellation: {
        enabled: this.config.echoCancellation.enabled,
        active: false,
        metrics: {
          echoLevel: 0,
          suppressionGain: 1.0,
          processingLatency: 0,
          adaptationConverged: false
        }
      },
      bargeInDetection: {
        enabled: this.config.bargeInDetection.enabled,
        monitoring: false,
        sensitivity: this.config.bargeInDetection.sensitivity
      },
      conversationFlow: {
        currentlySpeaking: false,
        canBeInterrupted: true
      }
    };
    
    console.log('🎛️ EnhancedOrchestrator initialized with B2 features');
  }

  private setupStateManagerHandlers(): void {
    this.audioStateManager.onStateChange = (oldState, newState, context) => {
      this.handleStateChange(oldState, newState, context);
    };
    
    this.audioStateManager.onStateTimeout = (state, duration) => {
      console.warn(`⏰ State timeout: ${state} after ${duration}ms`);
      this.handleStateTimeout(state, duration);
    };
    
    this.audioStateManager.onError = (error, state) => {
      console.error(`❌ State manager error in ${state}: ${error}`);
      this.onError(`State management error: ${error}`);
    };
  }

  private handleStateChange(oldState: AudioState, newState: AudioState, context?: StateContext): void {
    this.currentStatus.audioState = newState;
    
    // Update conversation flow status
    this.currentStatus.conversationFlow.currentlySpeaking = newState === 'speaking';
    this.currentStatus.conversationFlow.canBeInterrupted = newState === 'speaking';
    
    if (context?.interruptedContent) {
      this.currentStatus.conversationFlow.interruptedContent = context.interruptedContent;
    }
    
    // Update barge-in detector
    if (this.bargeInDetector) {
      this.bargeInDetector.setContextState(newState === 'speaking' ? 'speaking' : 'listening');
      this.bargeInDetector.setAliceSpeakingState(newState === 'speaking');
    }
    
    // Emit state change event
    this.emitEvent({
      type: 'state_changed',
      stateTransition: {
        from: oldState,
        to: newState,
        timestamp: Date.now(),
        trigger: 'orchestrator_managed',
        context
      },
      ts: new Date()
    });
    
    console.log(`🔄 Audio state changed: ${oldState} -> ${newState}`);
  }

  private handleStateTimeout(state: AudioState, duration: number): void {
    // Handle state-specific timeouts
    switch (state) {
      case 'speaking':
        console.log('🗣️ Speaking timeout - stopping Alice');
        this.stopAliceSpeaking();
        break;
        
      case 'interrupted':
        console.log('⏸️ Interruption timeout - resuming or going to listening');
        if (this.config.conversationFlow.autoResumeEnabled) {
          this.resumeAfterInterruption();
        } else {
          this.audioStateManager.startListening();
        }
        break;
        
      case 'processing':
        console.log('⚙️ Processing timeout - returning to listening');
        this.audioStateManager.startListening();
        break;
    }
  }

  async initialize(): Promise<void> {
    try {
      console.log('🚀 Initializing Enhanced Orchestrator...');
      
      // Initialize audio context
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: this.config.audioProcessing.sampleRate,
        latencyHint: this.config.audioProcessing.lowLatencyMode ? 'interactive' : 'balanced'
      });
      
      // Request microphone permission
      await this.requestMicrophoneAccess();
      
      // Initialize B2 components
      await this.initializeEchoCancellation();
      await this.initializeBargeInDetection();
      
      // Initialize B1 components with processed audio
      await this.initializeCoreComponents();
      
      this.isInitialized = true;
      this.updateStatus();
      
      console.log('✅ Enhanced Orchestrator initialized successfully');
      
    } catch (error) {
      const errorMsg = `Failed to initialize Enhanced Orchestrator: ${error}`;
      console.error('❌', errorMsg);
      this.onError(errorMsg);
      throw error;
    }
  }

  private async requestMicrophoneAccess(): Promise<void> {
    try {
      this.currentStatus.micPermission = 'pending';
      this.updateStatus();
      
      const constraints = {
        audio: {
          echoCancellation: false, // We handle this ourselves
          noiseSuppression: this.config.noiseSuppression,
          autoGainControl: this.config.autoGainControl,
          sampleRate: this.config.audioProcessing.sampleRate
        }
      };
      
      this.micStream = await navigator.mediaDevices.getUserMedia(constraints);
      this.currentStatus.micPermission = 'granted';
      
      console.log('🎤 Microphone access granted');
      
    } catch (error) {
      this.currentStatus.micPermission = 'denied';
      throw new Error(`Microphone access denied: ${error}`);
    }
  }

  private async initializeEchoCancellation(): Promise<void> {
    if (!this.config.echoCancellation.enabled) {
      console.log('🔇 Echo cancellation disabled');
      return;
    }
    
    const echoConfig: Partial<EchoCancellerConfig> = {
      sampleRate: this.config.audioProcessing.sampleRate,
      bufferSize: this.config.audioProcessing.bufferSize,
      adaptationRate: this.config.echoCancellation.adaptationRate,
      echoSuppressionLevel: this.config.echoCancellation.suppressionLevel,
      noiseGateThreshold: this.config.echoCancellation.noiseGateThreshold
    };
    
    this.echoCanceller = new EchoCanceller(echoConfig);
    
    // Set up event handlers
    this.echoCanceller.onEchoDetected = (level) => {
      this.handleEchoDetected(level);
    };
    
    this.echoCanceller.onCalibrationComplete = () => {
      console.log('✅ Echo cancellation calibrated');
      this.currentStatus.echoCancellation.metrics.adaptationConverged = true;
      this.updateStatus();
    };
    
    this.echoCanceller.onError = (error) => {
      console.error('❌ Echo cancellation error:', error);
      this.onError(`Echo cancellation: ${error}`);
    };
    
    // Initialize with mic stream
    await this.echoCanceller.initialize(this.micStream!, this.audioContext!);
    
    // Get processed stream
    this.processedStream = this.echoCanceller.getProcessedStream();
    this.currentStatus.echoCancellation.active = true;
    
    console.log('✅ Echo cancellation initialized');
  }

  private async initializeBargeInDetection(): Promise<void> {
    if (!this.config.bargeInDetection.enabled) {
      console.log('🎯 Barge-in detection disabled');
      return;
    }
    
    const bargeInConfig: Partial<BargeInConfig> = {
      sensitivity: this.config.bargeInDetection.sensitivity,
      minConfidence: this.config.bargeInDetection.minConfidence,
      detectionWindowMs: this.config.bargeInDetection.detectionWindowMs,
      voiceActivityThreshold: 0.02,
      spectralAnalysisEnabled: this.config.audioProcessing.enableSpectralAnalysis
    };
    
    this.bargeInDetector = new BargeInDetector(bargeInConfig);
    
    // Set up event handlers
    this.bargeInDetector.onBargeInDetected = (event) => {
      this.handleBargeInDetected(event);
    };
    
    this.bargeInDetector.onVoiceActivity = (metrics) => {
      // Could emit voice activity events if needed
    };
    
    this.bargeInDetector.onCalibrationComplete = () => {
      console.log('✅ Barge-in detection calibrated');
    };
    
    this.bargeInDetector.onError = (error) => {
      console.error('❌ Barge-in detection error:', error);
      this.onError(`Barge-in detection: ${error}`);
    };
    
    // Use processed stream if echo cancellation is active, otherwise raw stream
    const inputStream = this.processedStream || this.micStream!;
    
    // Initialize with audio stream
    await this.bargeInDetector.initialize(inputStream, this.audioContext!);
    
    console.log('✅ Barge-in detection initialized');
  }

  private async initializeCoreComponents(): Promise<void> {
    // Use processed stream för B1 components
    const audioStream = this.processedStream || this.micStream!;
    
    // Initialize RealtimeASR
    this.realtimeASR = new RealtimeASR();
    this.realtimeASR.onEvent = (event: ASREvent) => {
      this.handleASREvent(event);
    };
    
    // Initialize AmbientBuffer
    if (this.config.ambientEnabled) {
      this.ambientBuffer = new AmbientBuffer();
      this.ambientBuffer.onEvent = (event: AmbientEvent) => {
        this.handleAmbientEvent(event);
      };
    }
    
    console.log('✅ Core B1 components initialized with processed audio');
  }

  private handleEchoDetected(level: number): void {
    console.log(`🔊 Echo detected: level ${level.toFixed(3)}`);
    
    // Update metrics
    if (this.echoCanceller) {
      this.currentStatus.echoCancellation.metrics = this.echoCanceller.getMetrics();
    }
    
    // Emit echo detection event
    this.emitEvent({
      type: 'echo_detected',
      echoLevel: level,
      ts: new Date()
    });
    
    // Auto-adjust if echo is too high
    if (level > 0.3) {
      this.adjustEchoSuppression(level);
    }
  }

  private adjustEchoSuppression(echoLevel: number): void {
    if (!this.echoCanceller) return;
    
    // Increase suppression level based on detected echo
    const newLevel = Math.min(0.95, echoLevel * 2);
    this.echoCanceller.setSensitivity(newLevel);
    
    console.log(`🎚️ Auto-adjusted echo suppression to ${newLevel.toFixed(2)}`);
  }

  private handleBargeInDetected(event: BargeInEvent): void {
    console.log(`🎯 Barge-in detected! Confidence: ${event.confidence.toFixed(3)}`);
    
    // Store last detection
    this.currentStatus.bargeInDetection.lastDetection = event;
    
    // Handle interruption based on current state
    if (this.audioStateManager.getCurrentState() === 'speaking') {
      this.handleUserInterruption(event);
    }
    
    // Emit barge-in event
    this.emitEvent({
      type: 'barge_in_detected',
      bargeInEvent: event,
      ts: new Date()
    });
  }

  private handleUserInterruption(bargeInEvent: BargeInEvent): void {
    console.log('⏸️ Handling user interruption...');
    
    // Stop Alice immediately
    this.stopAliceSpeaking();
    
    // Transition to interrupted state
    const context: StateContext = {
      interruptedContent: this.currentStatus.conversationFlow.interruptedContent,
      confidence: bargeInEvent.confidence
    };
    
    this.audioStateManager.handleInterruption(undefined, bargeInEvent.confidence);
    
    // Emit conversation interrupted event
    this.emitEvent({
      type: 'conversation_interrupted',
      interruptionData: {
        userInput: '', // Will be filled when ASR provides text
        confidence: bargeInEvent.confidence,
        resumeContent: context.interruptedContent
      },
      ts: new Date()
    });
    
    // Start processing user input
    setTimeout(() => {
      this.audioStateManager.startProcessing();
    }, 100);
  }

  private handleASREvent(event: ASREvent): void {
    // Handle ASR events and update state accordingly
    switch (event.type) {
      case 'partial':
        this.currentStatus.lastPartial = event.transcript;
        break;
        
      case 'final':
        if (this.audioStateManager.getCurrentState() === 'interrupted') {
          // This is the user's interrupting input
          this.processUserInterruptionInput(event.transcript);
        }
        break;
        
      case 'error':
        this.onError(`ASR error: ${event.error}`);
        this.audioStateManager.enterErrorState(event.error);
        break;
    }
    
    this.updateStatus();
  }

  private processUserInterruptionInput(transcript: string): void {
    console.log(`💬 User interruption input: "${transcript}"`);
    
    // Update context with user input
    this.audioStateManager.updateContext({ userInput: transcript });
    
    // Could trigger response generation here
    // For now, just transition back to listening
    setTimeout(() => {
      this.audioStateManager.startListening();
    }, 1000);
  }

  private handleAmbientEvent(event: AmbientEvent): void {
    // Handle ambient buffer events
    if (event.type === 'summary_created') {
      this.currentStatus.bufferStats = event.bufferStats;
      this.updateStatus();
    }
  }

  // Public interface methods

  async start(): Promise<void> {
    if (!this.isInitialized) {
      throw new Error('Enhanced Orchestrator not initialized');
    }
    
    console.log('▶️ Starting Enhanced Orchestrator...');
    
    // Start echo cancellation
    if (this.echoCanceller && this.config.echoCancellation.enabled) {
      this.echoCanceller.startProcessing();
      this.currentStatus.echoCancellation.active = true;
    }
    
    // Start barge-in monitoring
    if (this.bargeInDetector && this.config.bargeInDetection.enabled) {
      this.bargeInDetector.startMonitoring();
      this.currentStatus.bargeInDetection.monitoring = true;
    }
    
    // Start core components
    if (this.realtimeASR) {
      await this.realtimeASR.connect();
      this.currentStatus.asrStatus = 'connected';
    }
    
    if (this.ambientBuffer) {
      this.ambientBuffer.start();
    }
    
    // Start listening
    this.audioStateManager.startListening();
    this.currentStatus.isListening = true;
    
    this.isActive = true;
    this.updateStatus();
    
    console.log('✅ Enhanced Orchestrator started successfully');
  }

  async stop(): Promise<void> {
    console.log('⏹️ Stopping Enhanced Orchestrator...');
    
    this.isActive = false;
    
    // Stop monitoring
    if (this.bargeInDetector) {
      this.bargeInDetector.stopMonitoring();
      this.currentStatus.bargeInDetection.monitoring = false;
    }
    
    // Stop processing
    if (this.echoCanceller) {
      this.echoCanceller.stopProcessing();
      this.currentStatus.echoCancellation.active = false;
    }
    
    // Stop core components
    if (this.realtimeASR) {
      await this.realtimeASR.disconnect();
      this.currentStatus.asrStatus = 'disconnected';
    }
    
    if (this.ambientBuffer) {
      this.ambientBuffer.stop();
    }
    
    // Stop listening
    this.audioStateManager.startListening();
    this.currentStatus.isListening = false;
    
    this.updateStatus();
    console.log('⏹️ Enhanced Orchestrator stopped');
  }

  // Alice speaking integration
  startAliceSpeaking(content: string): void {
    console.log(`🗣️ Alice started speaking: "${content.substring(0, 50)}..."`);
    
    // Store content för potential interruption
    this.currentStatus.conversationFlow.interruptedContent = content;
    
    // Transition to speaking state
    this.audioStateManager.startSpeaking(content);
    
    // Notify echo canceller about outgoing audio
    // (In real implementation, this would be called with actual audio data)
    
    this.updateStatus();
    this.onAliceStartSpeaking(content);
  }

  stopAliceSpeaking(): void {
    console.log('🔇 Alice stopped speaking');
    
    // Clear interrupted content unless we're in interrupted state
    if (this.audioStateManager.getCurrentState() !== 'interrupted') {
      this.currentStatus.conversationFlow.interruptedContent = undefined;
    }
    
    // Transition back to listening unless interrupted
    if (this.audioStateManager.getCurrentState() === 'speaking') {
      this.audioStateManager.startListening();
    }
    
    this.updateStatus();
    this.onAliceStopSpeaking();
  }

  resumeAfterInterruption(newContent?: string): void {
    console.log('🔄 Resuming after interruption...');
    
    this.audioStateManager.resumeAfterInterruption(newContent);
    
    if (newContent || this.currentStatus.conversationFlow.interruptedContent) {
      const contentToSpeak = newContent || this.currentStatus.conversationFlow.interruptedContent!;
      this.startAliceSpeaking(contentToSpeak);
    }
  }

  // Configuration methods
  setEchoSuppression(level: number): void {
    if (this.echoCanceller) {
      this.echoCanceller.setSensitivity(level);
      console.log(`🎚️ Echo suppression set to ${level.toFixed(2)}`);
    }
  }

  setBargeInSensitivity(sensitivity: number): void {
    this.config.bargeInDetection.sensitivity = sensitivity;
    
    if (this.bargeInDetector) {
      this.bargeInDetector.setSensitivity(sensitivity);
      this.currentStatus.bargeInDetection.sensitivity = sensitivity;
      console.log(`🎯 Barge-in sensitivity set to ${sensitivity.toFixed(2)}`);
    }
  }

  // Status and metrics
  getStatus(): EnhancedOrchestratorStatus {
    return { ...this.currentStatus };
  }

  getStateMetrics() {
    return this.audioStateManager.getMetrics();
  }

  // Event emission
  private emitEvent(event: EnhancedOrchestratorEvent): void {
    this.onEvent(event);
  }

  private updateStatus(): void {
    this.emitEvent({
      type: 'status_change',
      status: { ...this.currentStatus },
      ts: new Date()
    });
  }

  // Cleanup
  async cleanup(): Promise<void> {
    console.log('🧹 Cleaning up Enhanced Orchestrator...');
    
    await this.stop();
    
    if (this.echoCanceller) {
      this.echoCanceller.cleanup();
    }
    
    if (this.bargeInDetector) {
      this.bargeInDetector.cleanup();
    }
    
    this.audioStateManager.cleanup();
    
    if (this.audioContext) {
      await this.audioContext.close();
    }
    
    if (this.micStream) {
      this.micStream.getTracks().forEach(track => track.stop());
    }
    
    console.log('✅ Enhanced Orchestrator cleanup complete');
  }
}

export default EnhancedOrchestrator;