/**
 * OpenAI Realtime Provider - Full WebSocket Implementation
 * Handles ASR partials/finals and streaming TTS via OpenAI Realtime API
 */
import { EventEmitter } from 'eventemitter3';
import WebSocket from 'ws';
import type { 
  VoiceProvider, ASRAdapter, TTSAdapter,
  ASROptions, ASRHandlers, TTSOptions, TTSHandlers,
  VoiceError, VoiceMetrics, VoiceEvents, OpenAIRealtimeConfig,
  ProviderStatus
} from '../types/index.js';
import { LatencyTracker } from '../metrics/LatencyTracker.js';

interface RealtimeMessage {
  type: string;
  event_id?: string;
  [key: string]: any;
}

export class OpenAIRealtimeProvider extends EventEmitter<VoiceEvents> implements VoiceProvider {
  public asr: ASRAdapter;
  public tts: TTSAdapter;
  
  private ws: WebSocket | null = null;
  private config: OpenAIRealtimeConfig;
  private latencyTracker = new LatencyTracker();
  private isInitialized = false;
  private sessionId = '';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private errorCount = 0;
  
  constructor(config: OpenAIRealtimeConfig) {
    super();
    this.config = config;
    this.asr = new OpenAIRealtimeASR(this);
    this.tts = new OpenAIRealtimeTTS(this);
  }
  
  async initialize(): Promise<void> {
    if (this.isInitialized) return;
    
    try {
      await this.connect();
      this.isInitialized = true;
      this.emit('provider:connected', 'openai');
    } catch (error) {
      this.errorCount++;
      const voiceError: VoiceError = {
        code: 'network_connection_failed',
        message: `Failed to initialize OpenAI Realtime: ${error}`,
        recoverable: true,
        timestamp_ms: Date.now()
      };
      this.emit('error', voiceError);
      throw voiceError;
    }
  }
  
  private async connect(): Promise<void> {
    const url = this.config.endpointUrl || 'wss://api.openai.com/v1/realtime';
    const wsUrl = `${url}?model=${this.config.model}`;
    
    this.ws = new WebSocket(wsUrl, {
      headers: {
        'Authorization': `Bearer ${this.config.apiKey}`,
        'OpenAI-Beta': 'realtime=v1'
      }
    });
    
    return new Promise((resolve, reject) => {
      if (!this.ws) return reject(new Error('WebSocket not created'));
      
      this.ws.onopen = () => {
        console.log('OpenAI Realtime WebSocket connected');
        this.reconnectAttempts = 0;
        this.startSession();
        resolve();
      };
      
      this.ws.onclose = (event) => {
        console.log('OpenAI Realtime WebSocket closed:', event.code, event.reason);
        this.handleDisconnect();
      };
      
      this.ws.onerror = (error) => {
        console.error('OpenAI Realtime WebSocket error:', error);
        this.errorCount++;
        reject(error);
      };
      
      this.ws.onmessage = (event) => {
        this.handleMessage(event.data);
      };
    });
  }
  
  private startSession(): void {
    this.sessionId = `session_${Date.now()}`;
    this.latencyTracker.start('session');
    
    const sessionConfig = {
      type: 'session.update',
      session: {
        modalities: ['text', 'audio'],
        instructions: 'You are Alice, a helpful AI assistant. Respond naturally in Swedish.',
        voice: this.config.voice,
        input_audio_format: 'pcm16',
        output_audio_format: 'pcm16',
        input_audio_transcription: {
          model: 'whisper-1'
        },
        turn_detection: {
          type: 'server_vad',
          threshold: 0.5,
          prefix_padding_ms: 300,
          silence_duration_ms: 500
        },
        tool_choice: 'auto',
        temperature: this.config.temperature || 0.8,
        max_output_tokens: this.config.maxTokens || 150
      }
    };
    
    this.sendMessage(sessionConfig);
  }
  
  private handleMessage(data: string | Buffer): void {
    try {
      let message: RealtimeMessage;
      
      if (data instanceof Buffer) {
        // Handle binary audio data
        this.handleAudioResponse(data);
        return;
      }
      
      message = JSON.parse(data as string);
      
      switch (message.type) {
        case 'session.created':
          console.log('OpenAI Realtime session created:', message.session?.id);
          break;
          
        case 'input_audio_buffer.speech_started':
          this.latencyTracker.start('asr_partial');
          break;
          
        case 'conversation.item.input_audio_transcription.completed':
          this.handleASRPartial(message);
          break;
          
        case 'conversation.item.input_audio_transcription.final':
          this.handleASRFinal(message);
          break;
          
        case 'response.audio_transcript.delta':
          this.handleTTSStart(message);
          break;
          
        case 'response.audio.delta':
          this.handleTTSAudio(message);
          break;
          
        case 'response.done':
          this.handleResponseComplete();
          break;
          
        case 'error':
          this.handleServerError(message);
          break;
          
        default:
          console.log('Unhandled OpenAI Realtime message:', message.type);
      }
    } catch (error) {
      console.error('Failed to parse OpenAI Realtime message:', error);
      this.errorCount++;
    }
  }
  
  private handleASRPartial(message: any): void {
    const latency = this.latencyTracker.end('asr_partial');
    const result = {
      text: message.transcript || '',
      confidence: message.confidence || 0.8,
      timestamp_ms: Date.now(),
      session_id: this.sessionId,
      isFinal: false,
      isStable: true
    };
    
    this.emit('asr:partial', result);
  }
  
  private handleASRFinal(message: any): void {
    const latency = this.latencyTracker.end('asr_final') || this.latencyTracker.end('asr_partial');
    this.latencyTracker.start('llm');
    
    const result = {
      text: message.transcript || '',
      confidence: message.confidence || 0.8,
      timestamp_ms: Date.now(),
      session_id: this.sessionId,
      isFinal: true,
      duration_ms: latency
    };
    
    this.emit('asr:final', result);
  }
  
  private handleTTSStart(message: any): void {
    if (!this.latencyTracker.hasStarted('tts_ttfa')) {
      this.latencyTracker.start('tts_ttfa');
      const ttfaLatency = this.latencyTracker.end('tts_ttfa');
      this.emit('tts:start', `tts_${Date.now()}`);
    }
  }
  
  private handleTTSAudio(message: any): void {
    if (message.delta && message.delta.length > 0) {
      // Convert base64 audio to buffer
      const audioBuffer = Buffer.from(message.delta, 'base64');
      const audioChunk = {
        data: audioBuffer,
        sampleRate: 24000, // OpenAI Realtime default
        timestamp_ms: Date.now(),
        duration_ms: (audioBuffer.length / 2 / 24000) * 1000, // PCM16 calculation
        isFirst: false,
        isFinal: false,
        format: 'pcm16' as const
      };
      
      this.emit('tts:chunk', audioChunk);
    }
  }
  
  private handleAudioResponse(audioData: Buffer): void {
    const audioChunk = {
      data: audioData,
      sampleRate: 24000,
      timestamp_ms: Date.now(),
      duration_ms: (audioData.length / 2 / 24000) * 1000,
      isFirst: false,
      isFinal: false,
      format: 'pcm16' as const
    };
    
    this.emit('tts:chunk', audioChunk);
  }
  
  private handleResponseComplete(): void {
    const e2eLatency = this.latencyTracker.end('session');
    const llmLatency = this.latencyTracker.end('llm');
    
    this.emit('tts:end', `tts_${Date.now()}`);
    
    // Emit metrics
    const metrics: VoiceMetrics = {
      session_id: this.sessionId,
      timestamp_ms: Date.now(),
      provider: 'openai',
      e2e_roundtrip_ms: e2eLatency,
      llm_latency_ms: llmLatency,
      error_count: this.errorCount,
      fallback_triggered: false
    };
    
    this.emit('metrics:collected', metrics);
  }
  
  private handleServerError(message: any): void {
    this.errorCount++;
    const error: VoiceError = {
      code: message.error?.code || 'service_internal_error',
      message: message.error?.message || 'OpenAI Realtime server error',
      recoverable: message.error?.code !== 'auth_invalid_key',
      timestamp_ms: Date.now()
    };
    
    this.emit('error', error);
  }
  
  private handleDisconnect(): void {
    this.emit('provider:disconnected', 'openai');
    
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
      
      setTimeout(() => {
        this.connect().catch(error => {
          console.error('Reconnect failed:', error);
        });
      }, Math.pow(2, this.reconnectAttempts) * 1000); // Exponential backoff
    }
  }
  
  public sendAudio(audioData: ArrayBuffer): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      // Send binary audio data
      this.ws.send(audioData);
    }
  }
  
  public sendMessage(message: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }
  
  async destroy(): Promise<void> {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isInitialized = false;
    this.removeAllListeners();
  }
  
  isHealthy(): boolean {
    return this.ws?.readyState === WebSocket.OPEN && this.isInitialized;
  }
  
  getStatus(): ProviderStatus {
    return {
      connected: this.isHealthy(),
      provider: 'openai-realtime',
      error: this.errorCount > 0 ? {
        code: 'service_errors',
        message: `${this.errorCount} errors encountered`,
        recoverable: true,
        timestamp_ms: Date.now()
      } : undefined
    };
  }
  
  getMetrics(): VoiceMetrics {
    return {
      session_id: this.sessionId,
      timestamp_ms: Date.now(),
      provider: 'openai',
      error_count: this.errorCount,
      fallback_triggered: false,
      ...this.latencyTracker.getMetrics()
    };
  }
  
  resetMetrics(): void {
    this.latencyTracker.reset();
    this.errorCount = 0;
  }
}

class OpenAIRealtimeASR implements ASRAdapter {
  private provider: OpenAIRealtimeProvider;
  private isListening = false;
  private handlers: ASRHandlers = {};
  
  constructor(provider: OpenAIRealtimeProvider) {
    this.provider = provider;
  }
  
  async initialize(): Promise<void> {
    // ASR is initialized with the provider
  }
  
  async destroy(): Promise<void> {
    this.stop();
  }
  
  async start(options: ASROptions, handlers: ASRHandlers): Promise<void> {
    this.handlers = handlers;
    this.isListening = true;
    
    // Set up event listeners
    this.provider.on('asr:partial', handlers.onPartial || (() => {}));
    this.provider.on('asr:final', handlers.onFinal || (() => {}));
    this.provider.on('error', handlers.onError || (() => {}));
    
    handlers.onStart?.();
    this.emit('asr:start');
  }
  
  async stop(): Promise<void> {
    this.isListening = false;
    this.provider.removeAllListeners('asr:partial');
    this.provider.removeAllListeners('asr:final');
    this.handlers.onEnd?.();
  }
  
  pushAudio(chunk: ArrayBuffer | Float32Array | Int16Array): void {
    if (!this.isListening) return;
    
    let audioBuffer: ArrayBuffer;
    
    if (chunk instanceof Float32Array) {
      // Convert Float32 to Int16 (PCM16)
      const int16Data = new Int16Array(chunk.length);
      for (let i = 0; i < chunk.length; i++) {
        int16Data[i] = Math.round(chunk[i] * 32767);
      }
      audioBuffer = int16Data.buffer;
    } else if (chunk instanceof Int16Array) {
      audioBuffer = chunk.buffer;
    } else {
      audioBuffer = chunk;
    }
    
    this.provider.sendAudio(audioBuffer);
  }
  
  isListening(): boolean {
    return this.isListening;
  }
  
  isInitialized(): boolean {
    return this.provider.isHealthy();
  }
  
  getConfig(): Record<string, any> {
    return {
      provider: 'openai-realtime',
      language: 'sv-SE',
      sampleRate: 16000,
      format: 'pcm16'
    };
  }
  
  updateConfig(config: Partial<ASROptions>): void {
    // Configuration updates would require reconnection
    console.log('ASR config update:', config);
  }
  
  private emit(event: string, ...args: any[]): void {
    // Helper for type-safe event emission
    (this.provider as any).emit(event, ...args);
  }
}

class OpenAIRealtimeTTS implements TTSAdapter {
  private provider: OpenAIRealtimeProvider;
  private isSpeaking = false;
  private activeSynthesis: string[] = [];
  
  constructor(provider: OpenAIRealtimeProvider) {
    this.provider = provider;
  }
  
  async initialize(): Promise<void> {
    // TTS is initialized with the provider
  }
  
  async destroy(): Promise<void> {
    await this.cancelAll();
  }
  
  async speak(options: TTSOptions, handlers: TTSHandlers): Promise<string> {
    const playbackId = `tts_${Date.now()}`;
    this.activeSynthesis.push(playbackId);
    this.isSpeaking = true;
    
    // Set up event listeners
    this.provider.on('tts:start', (id) => {
      handlers.onStart?.(playbackId);
    });
    
    this.provider.on('tts:chunk', handlers.onAudioChunk || (() => {}));
    
    this.provider.on('tts:end', (id) => {
      this.activeSynthesis = this.activeSynthesis.filter(aid => aid !== playbackId);
      this.isSpeaking = this.activeSynthesis.length > 0;
      handlers.onEnd?.(playbackId);
    });
    
    this.provider.on('error', (error) => {
      handlers.onError?.(error, playbackId);
    });
    
    // Send text for TTS (this would be handled by the conversation flow in real implementation)
    const message = {
      type: 'response.create',
      response: {
        modalities: ['text', 'audio'],
        instructions: options.text || options.ssml || '',
        voice: this.provider.config.voice,
        output_audio_format: 'pcm16'
      }
    };
    
    this.provider.sendMessage(message);
    
    return playbackId;
  }
  
  async cancel(playbackId?: string): Promise<void> {
    if (playbackId) {
      this.activeSynthesis = this.activeSynthesis.filter(id => id !== playbackId);
    }
    
    // Send cancel message to OpenAI
    this.provider.sendMessage({
      type: 'response.cancel'
    });
    
    this.isSpeaking = this.activeSynthesis.length > 0;
  }
  
  async cancelAll(): Promise<void> {
    this.activeSynthesis = [];
    this.isSpeaking = false;
    
    this.provider.sendMessage({
      type: 'response.cancel'
    });
  }
  
  isSpeaking(): boolean {
    return this.isSpeaking;
  }
  
  isInitialized(): boolean {
    return this.provider.isHealthy();
  }
  
  getActiveSynthesis(): string[] {
    return [...this.activeSynthesis];
  }
  
  getConfig(): Record<string, any> {
    return {
      provider: 'openai-realtime',
      voice: this.provider.config.voice,
      format: 'pcm16',
      sampleRate: 24000
    };
  }
  
  updateConfig(config: Partial<TTSOptions>): void {
    console.log('TTS config update:', config);
  }
  
  async getAvailableVoices() {
    return [
      { id: 'alloy', name: 'Alloy', language: 'en-US' },
      { id: 'echo', name: 'Echo', language: 'en-US' },
      { id: 'fable', name: 'Fable', language: 'en-US' },
      { id: 'onyx', name: 'Onyx', language: 'en-US' },
      { id: 'nova', name: 'Nova', language: 'en-US' },
      { id: 'shimmer', name: 'Shimmer', language: 'en-US' }
    ];
  }
}