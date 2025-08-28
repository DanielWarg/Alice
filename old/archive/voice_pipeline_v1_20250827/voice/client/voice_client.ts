#!/usr/bin/env node
/**
 * 🎤 Voice Client - Browser WebSocket Binary Audio Streaming
 * Handles mic capture, VAD, and binary frame transmission
 */

import { EventEmitter } from 'events';
import { JitterBuffer } from './jitter_buffer.js';
import { AudioProcessor } from './audio_processor.js';

// Client configuration
interface VoiceClientConfig {
  serverUrl: string;
  sampleRate: number;
  frameSize: number;        // 20ms frames
  vadThreshold: number;     // Energy threshold for voice detection
  echoCancellation: boolean;
  noiseSuppression: boolean;
  autoGainControl: boolean;
}

// Audio analysis result
interface AudioAnalysis {
  energy: number;
  isVoiced: boolean;
  timestamp: number;
}

/**
 * Browser Voice Client
 * Captures mic audio and streams to voice server
 */
export class VoiceStreamClient extends EventEmitter {
  private config: VoiceClientConfig;
  private ws: WebSocket | null = null;
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private analyser: AnalyserNode | null = null;
  
  // New audio pipeline components
  private jitterBuffer: JitterBuffer | null = null;
  private audioProcessor: AudioProcessor | null = null;
  
  private isRecording = false;
  private isConnected = false;
  private sessionId: string | null = null;
  
  // Audio analysis
  private frameBuffer: Float32Array[] = [];
  private lastVoiceTime = 0;
  
  // Playback management
  private isPlayingTTS = false;

  constructor(config: Partial<VoiceClientConfig> = {}) {
    super();
    
    this.config = {
      serverUrl: 'ws://localhost:8001',
      sampleRate: 16000,
      frameSize: 320,  // 20ms at 16kHz
      vadThreshold: 0.01,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      ...config
    };

    console.log('🎤 Voice Client initialized');
  }

  /**
   * Connect to voice server
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.config.serverUrl);
        
        this.ws.onopen = () => {
          console.log('✅ Connected to voice server');
          this.isConnected = true;
          this.emit('connected');
          resolve();
        };
        
        this.ws.onmessage = (event) => {
          this.handleServerMessage(event);
        };
        
        this.ws.onclose = () => {
          console.log('🔌 Disconnected from voice server');
          this.isConnected = false;
          this.sessionId = null;
          this.emit('disconnected');
        };
        
        this.ws.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
          reject(error);
        };
        
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Start audio capture and streaming
   */
  async startRecording(): Promise<void> {
    if (this.isRecording) {
      console.warn('⚠️ Already recording');
      return;
    }

    try {
      // Request microphone access
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.config.sampleRate,
          channelCount: 1,
          echoCancellation: this.config.echoCancellation,
          noiseSuppression: this.config.noiseSuppression,
          autoGainControl: this.config.autoGainControl
        }
      });

      // Create audio context
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: this.config.sampleRate
      });

      // Initialize audio pipeline components
      this.jitterBuffer = new JitterBuffer(this.audioContext);
      this.audioProcessor = new AudioProcessor(this.audioContext);

      // Create audio nodes
      const source = this.audioContext.createMediaStreamSource(this.mediaStream);
      
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      this.analyser.smoothingTimeConstant = 0.3;
      
      // Use ScriptProcessorNode for real-time processing
      this.processor = this.audioContext.createScriptProcessor(
        this.config.frameSize, 1, 1
      );

      // Connect audio graph with audio processor
      source.connect(this.analyser);
      this.audioProcessor.connectInput(source);
      source.connect(this.processor);
      this.processor.connect(this.audioProcessor.connectOutput());

      // Process audio frames
      this.processor.onaudioprocess = (event) => {
        this.processAudioFrame(event.inputBuffer.getChannelData(0));
      };

      this.isRecording = true;
      this.emit('recording.start');
      console.log('🎤 Recording started');

      // Send mic control message
      this.sendControlMessage({ type: 'control.mic', enabled: true });

    } catch (error) {
      console.error('❌ Failed to start recording:', error);
      throw error;
    }
  }

  /**
   * Stop audio capture
   */
  async stopRecording(): Promise<void> {
    if (!this.isRecording) return;

    try {
      // Stop audio processing
      if (this.processor) {
        this.processor.disconnect();
        this.processor = null;
      }

      if (this.analyser) {
        this.analyser.disconnect();
        this.analyser = null;
      }

      if (this.audioContext) {
        await this.audioContext.close();
        this.audioContext = null;
      }

      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach(track => track.stop());
        this.mediaStream = null;
      }

      this.isRecording = false;
      this.emit('recording.stop');
      console.log('🛑 Recording stopped');

      // Send mic control message
      this.sendControlMessage({ type: 'control.mic', enabled: false });

    } catch (error) {
      console.error('❌ Error stopping recording:', error);
    }
  }

  /**
   * Process individual audio frame with audio processor
   */
  private processAudioFrame(samples: Float32Array): void {
    if (!this.isConnected || !this.ws || !this.audioProcessor) return;

    const timestamp = Date.now();
    
    // Apply audio processing (echo cancellation, etc.)
    const processedSamples = this.audioProcessor.processAudioFrame(samples);
    
    // Analyze audio for VAD
    const analysis = this.analyzeAudioFrame(processedSamples);
    
    // Send processed frame to server
    this.sendAudioFrame(processedSamples, timestamp);
    
    // Update voice activity
    if (analysis.isVoiced) {
      this.lastVoiceTime = timestamp;
      this.emit('voice.detected', analysis);
    } else {
      this.emit('voice.silence', analysis);
    }
    
    // Emit general audio analysis
    this.emit('audio.analysis', analysis);
  }

  /**
   * Analyze audio frame for voice activity
   */
  private analyzeAudioFrame(samples: Float32Array): AudioAnalysis {
    // Calculate RMS energy
    let sum = 0;
    for (let i = 0; i < samples.length; i++) {
      sum += samples[i] * samples[i];
    }
    const energy = Math.sqrt(sum / samples.length);
    
    // Simple energy-based VAD
    const isVoiced = energy > this.config.vadThreshold;
    
    return {
      energy,
      isVoiced,
      timestamp: Date.now()
    };
  }

  /**
   * Send binary audio frame to server
   */
  private sendAudioFrame(samples: Float32Array, timestamp: number): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    try {
      // Send as binary ArrayBuffer
      const buffer = samples.buffer.slice(
        samples.byteOffset,
        samples.byteOffset + samples.byteLength
      );
      
      this.ws.send(buffer);
    } catch (error) {
      console.error('❌ Failed to send audio frame:', error);
    }
  }

  /**
   * Send control message to server
   */
  private sendControlMessage(message: any): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    try {
      this.ws.send(JSON.stringify(message));
    } catch (error) {
      console.error('❌ Failed to send control message:', error);
    }
  }

  /**
   * Handle incoming server messages
   */
  private handleServerMessage(event: MessageEvent): void {
    try {
      // Handle binary audio data (TTS playback)
      if (event.data instanceof ArrayBuffer) {
        this.handleAudioPlayback(event.data);
        return;
      }

      // Handle JSON control messages
      if (typeof event.data === 'string') {
        const message = JSON.parse(event.data);
        this.handleControlMessage(message);
        return;
      }

    } catch (error) {
      console.error('❌ Error handling server message:', error);
    }
  }

  /**
   * Handle control messages from server
   */
  private handleControlMessage(message: any): void {
    switch (message.type) {
      case 'handshake':
        this.sessionId = message.sessionId;
        console.log(`🤝 Session established: ${this.sessionId}`);
        this.emit('session.established', this.sessionId);
        break;

      case 'stt.partial':
        console.log(`🗣️ Partial: "${message.text}" (${message.confidence})`);
        this.emit('transcript.partial', message.text, message.confidence);
        break;

      case 'stt.final':
        console.log(`✅ Final: "${message.text}" (${message.confidence})`);
        this.emit('transcript.final', message.text, message.confidence);
        break;

      case 'llm.delta':
        this.emit('llm.token', message.text, message.done);
        break;

      case 'tts.begin':
        console.log('🔊 TTS playback beginning');
        this.isPlayingTTS = true;
        // Enable audio ducking during TTS
        if (this.audioProcessor) {
          this.audioProcessor.enableDucking();
        }
        this.emit('tts.start');
        break;

      case 'tts.end':
        console.log('🔊 TTS playback finished');
        this.isPlayingTTS = false;
        // Disable audio ducking when TTS ends
        if (this.audioProcessor) {
          this.audioProcessor.disableDucking();
        }
        this.emit('tts.end');
        break;

      case 'metrics':
        this.emit('metrics', message.latency, message.stage);
        break;
    }
  }

  /**
   * Handle TTS audio playback via jitter buffer
   */
  private handleAudioPlayback(audioData: ArrayBuffer): void {
    try {
      if (this.jitterBuffer) {
        // Use jitter buffer for smooth playback with cross-fade
        this.jitterBuffer.addChunk(audioData, Date.now());
      } else {
        // Fallback to direct playback
        const audioBlob = new Blob([audioData], { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        
        const audio = new Audio();
        audio.src = audioUrl;
        audio.play();
      }
      
      this.emit('audio.play', audioData.byteLength);
      
    } catch (error) {
      console.error('❌ Audio playback error:', error);
    }
  }

  /**
   * Trigger barge-in (interrupt TTS)
   */
  bargeIn(): void {
    if (!this.isPlayingTTS) return;
    
    console.log('🛑 Barge-in triggered');
    
    // Send barge-in signal
    this.sendControlMessage({
      type: 'control.barge_in',
      timestamp: Date.now()
    });
    
    // Stop jitter buffer playback
    if (this.jitterBuffer) {
      this.jitterBuffer.stop();
    }
    
    this.isPlayingTTS = false;
    this.emit('barge.in');
  }

  /**
   * Get current voice client status
   */
  getStatus() {
    return {
      connected: this.isConnected,
      recording: this.isRecording,
      sessionId: this.sessionId,
      playingTTS: this.isPlayingTTS,
      lastVoiceTime: this.lastVoiceTime
    };
  }

  /**
   * Disconnect and cleanup
   */
  async disconnect(): Promise<void> {
    console.log('🔌 Disconnecting voice client...');
    
    // Stop recording
    await this.stopRecording();
    
    // Close WebSocket
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    // Cleanup audio components
    if (this.jitterBuffer) {
      this.jitterBuffer.stop();
      this.jitterBuffer = null;
    }
    
    if (this.audioProcessor) {
      this.audioProcessor.cleanup();
      this.audioProcessor = null;
    }
    
    this.isConnected = false;
    this.sessionId = null;
    
    console.log('✅ Voice client disconnected');
  }
}

// Export for browser use
export type { VoiceClientConfig, AudioAnalysis };