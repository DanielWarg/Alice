import { EventEmitter } from 'eventemitter3';
import {
  VoiceProvider,
  ASRAdapter,
  TTSAdapter,
  VoiceProviderEvents,
  VoiceProviderConfig,
  AudioChunk,
  TranscriptResult,
  TTSRequest,
  TTSResult,
  VoiceSessionState,
  PerformanceMetrics,
  AudioFormat,
  DEFAULT_AUDIO_FORMAT,
  VoiceProviderError
} from '../types';

/**
 * Base abstract class for voice providers
 */
export abstract class BaseVoiceProvider extends EventEmitter<VoiceProviderEvents> implements VoiceProvider {
  protected config: VoiceProviderConfig;
  protected state: VoiceSessionState = 'disconnected';
  protected asrAdapter: ASRAdapter | null = null;
  protected ttsAdapter: TTSAdapter | null = null;
  protected metrics: PerformanceMetrics | null = null;

  constructor(config: VoiceProviderConfig) {
    super();
    this.config = { ...config };
  }

  abstract connect(): Promise<void>;
  abstract disconnect(): Promise<void>;
  abstract sendAudio(chunk: AudioChunk): Promise<void>;
  abstract sendText(text: string): Promise<void>;
  abstract startSession(): Promise<void>;
  abstract endSession(): Promise<void>;

  getState(): VoiceSessionState {
    return this.state;
  }

  getASR(): ASRAdapter | null {
    return this.asrAdapter;
  }

  getTTS(): TTSAdapter | null {
    return this.ttsAdapter;
  }

  getMetrics(): PerformanceMetrics | null {
    return this.metrics;
  }

  updateConfig(config: Partial<VoiceProviderConfig>): void {
    this.config = { ...this.config, ...config };
  }

  protected setState(newState: VoiceSessionState): void {
    if (this.state !== newState) {
      this.state = newState;
      this.emit('state_changed', newState);
    }
  }

  protected handleError(error: Error | VoiceProviderError): void {
    this.setState('error');
    this.emit('error', error);
  }
}

/**
 * Base abstract class for ASR adapters
 */
export abstract class BaseASRAdapter extends EventEmitter<VoiceProviderEvents> implements ASRAdapter {
  protected config: VoiceProviderConfig;
  protected state: VoiceSessionState = 'disconnected';
  protected supportedFormats: AudioFormat[] = [DEFAULT_AUDIO_FORMAT];

  constructor(config: VoiceProviderConfig) {
    super();
    this.config = config;
  }

  abstract start(): Promise<void>;
  abstract stop(): Promise<void>;
  abstract processAudio(chunk: AudioChunk): Promise<void>;

  getState(): VoiceSessionState {
    return this.state;
  }

  getSupportedFormats(): AudioFormat[] {
    return [...this.supportedFormats];
  }

  protected setState(newState: VoiceSessionState): void {
    if (this.state !== newState) {
      this.state = newState;
      this.emit('state_changed', newState);
    }
  }

  protected emitTranscript(result: TranscriptResult): void {
    this.emit('transcript', result);
  }

  protected handleError(error: Error): void {
    this.setState('error');
    this.emit('error', error);
  }
}

/**
 * Base abstract class for TTS adapters
 */
export abstract class BaseTTSAdapter extends EventEmitter<VoiceProviderEvents> implements TTSAdapter {
  protected config: VoiceProviderConfig;
  protected supportedFormats: AudioFormat[] = [DEFAULT_AUDIO_FORMAT];
  protected availableVoices: string[] = [];

  constructor(config: VoiceProviderConfig) {
    super();
    this.config = config;
  }

  abstract synthesize(request: TTSRequest): Promise<TTSResult>;
  abstract startStream(): Promise<void>;
  abstract stopStream(): Promise<void>;
  abstract streamText(text: string): Promise<void>;

  async getVoices(): Promise<string[]> {
    return [...this.availableVoices];
  }

  getSupportedFormats(): AudioFormat[] {
    return [...this.supportedFormats];
  }

  protected emitTTSResult(result: TTSResult): void {
    this.emit('tts_result', result);
  }

  protected emitAudioOutput(chunk: AudioChunk): void {
    this.emit('audio_output', chunk);
  }

  protected handleError(error: Error): void {
    this.emit('error', error);
  }
}

/**
 * Streaming ASR adapter for real-time processing
 */
export abstract class StreamingASRAdapter extends BaseASRAdapter {
  protected isStreaming: boolean = false;
  protected audioBuffer: Buffer = Buffer.alloc(0);
  protected sequenceId: number = 0;

  async start(): Promise<void> {
    if (this.isStreaming) {
      throw new Error('ASR adapter is already streaming');
    }
    
    this.setState('connecting');
    await this.initializeStream();
    this.isStreaming = true;
    this.setState('active');
  }

  async stop(): Promise<void> {
    if (!this.isStreaming) {
      return;
    }

    await this.cleanupStream();
    this.isStreaming = false;
    this.audioBuffer = Buffer.alloc(0);
    this.sequenceId = 0;
    this.setState('disconnected');
  }

  async processAudio(chunk: AudioChunk): Promise<void> {
    if (!this.isStreaming) {
      throw new Error('ASR adapter is not streaming');
    }

    // Validate audio format
    if (!this.isFormatSupported(chunk.format)) {
      throw new Error(`Unsupported audio format: ${JSON.stringify(chunk.format)}`);
    }

    // Buffer audio data
    this.audioBuffer = Buffer.concat([this.audioBuffer, chunk.data]);
    
    // Process buffered audio
    await this.processBufferedAudio(chunk.timestamp);
  }

  protected abstract initializeStream(): Promise<void>;
  protected abstract cleanupStream(): Promise<void>;
  protected abstract processBufferedAudio(timestamp: number): Promise<void>;

  protected isFormatSupported(format: AudioFormat): boolean {
    return this.supportedFormats.some(supported => 
      supported.sampleRate === format.sampleRate &&
      supported.channels === format.channels &&
      supported.bitDepth === format.bitDepth &&
      supported.encoding === format.encoding
    );
  }

  protected getNextSequenceId(): number {
    return ++this.sequenceId;
  }
}

/**
 * Streaming TTS adapter for real-time synthesis
 */
export abstract class StreamingTTSAdapter extends BaseTTSAdapter {
  protected isStreaming: boolean = false;
  protected textQueue: string[] = [];
  protected currentVoice: string = '';

  async startStream(): Promise<void> {
    if (this.isStreaming) {
      throw new Error('TTS adapter is already streaming');
    }

    await this.initializeStream();
    this.isStreaming = true;
  }

  async stopStream(): Promise<void> {
    if (!this.isStreaming) {
      return;
    }

    await this.flushTextQueue();
    await this.cleanupStream();
    this.isStreaming = false;
    this.textQueue = [];
  }

  async streamText(text: string): Promise<void> {
    if (!this.isStreaming) {
      throw new Error('TTS adapter is not streaming');
    }

    this.textQueue.push(text);
    await this.processTextQueue();
  }

  protected abstract initializeStream(): Promise<void>;
  protected abstract cleanupStream(): Promise<void>;
  protected abstract processTextQueue(): Promise<void>;
  protected abstract flushTextQueue(): Promise<void>;

  protected getDefaultTTSRequest(text: string): TTSRequest {
    return {
      text,
      voice: this.currentVoice || this.availableVoices[0] || 'default',
      format: this.supportedFormats[0]
    };
  }
}

/**
 * Utility functions for adapters
 */
export class AdapterUtils {
  /**
   * Validate audio chunk format and data
   */
  static validateAudioChunk(chunk: AudioChunk): void {
    if (!chunk.data || chunk.data.length === 0) {
      throw new Error('Audio chunk data is empty');
    }

    if (!chunk.format) {
      throw new Error('Audio chunk format is missing');
    }

    if (chunk.format.sampleRate <= 0) {
      throw new Error('Invalid sample rate');
    }

    if (chunk.format.channels <= 0) {
      throw new Error('Invalid channel count');
    }

    if (![16, 24, 32].includes(chunk.format.bitDepth)) {
      throw new Error('Unsupported bit depth');
    }
  }

  /**
   * Calculate expected audio chunk size
   */
  static calculateChunkSize(format: AudioFormat, durationMs: number): number {
    const bytesPerSample = format.bitDepth / 8;
    const samplesPerSecond = format.sampleRate * format.channels;
    const bytesPerSecond = samplesPerSecond * bytesPerSample;
    return Math.floor((bytesPerSecond * durationMs) / 1000);
  }

  /**
   * Create audio chunk with metadata
   */
  static createAudioChunk(
    data: Buffer,
    format: AudioFormat,
    timestamp?: number,
    sequenceId?: number
  ): AudioChunk {
    const duration = AdapterUtils.calculateDuration(data, format);
    
    return {
      data,
      format,
      timestamp: timestamp || Date.now(),
      duration,
      sequenceId: sequenceId || 0
    };
  }

  /**
   * Calculate audio duration from buffer and format
   */
  static calculateDuration(data: Buffer, format: AudioFormat): number {
    const bytesPerSample = format.bitDepth / 8;
    const totalSamples = data.length / (bytesPerSample * format.channels);
    return (totalSamples / format.sampleRate) * 1000; // Duration in milliseconds
  }

  /**
   * Validate transcript result
   */
  static validateTranscriptResult(result: TranscriptResult): void {
    if (typeof result.text !== 'string') {
      throw new Error('Transcript text must be a string');
    }

    if (typeof result.confidence !== 'number' || result.confidence < 0 || result.confidence > 1) {
      throw new Error('Transcript confidence must be a number between 0 and 1');
    }

    if (typeof result.isFinal !== 'boolean') {
      throw new Error('Transcript isFinal must be a boolean');
    }

    if (typeof result.timestamp !== 'number' || result.timestamp <= 0) {
      throw new Error('Transcript timestamp must be a positive number');
    }
  }

  /**
   * Create error with context
   */
  static createError(message: string, context: any, originalError?: Error): VoiceProviderError {
    const errorMessage = `${message}${context ? ` Context: ${JSON.stringify(context)}` : ''}`;
    return new VoiceProviderError(errorMessage, 'ADAPTER_ERROR', 'adapter', originalError);
  }
}

/**
 * Connection manager for voice providers
 */
export class ConnectionManager extends EventEmitter<VoiceProviderEvents> {
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectDelay: number = 1000;
  private isReconnecting: boolean = false;

  constructor(
    private provider: BaseVoiceProvider,
    options?: {
      maxReconnectAttempts?: number;
      reconnectDelay?: number;
    }
  ) {
    super();
    
    if (options?.maxReconnectAttempts !== undefined) {
      this.maxReconnectAttempts = options.maxReconnectAttempts;
    }
    
    if (options?.reconnectDelay !== undefined) {
      this.reconnectDelay = options.reconnectDelay;
    }

    this.setupProviderListeners();
  }

  async connect(): Promise<void> {
    try {
      await this.provider.connect();
      this.reconnectAttempts = 0;
    } catch (error) {
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    this.isReconnecting = false;
    await this.provider.disconnect();
  }

  private setupProviderListeners(): void {
    this.provider.on('disconnected', () => {
      if (!this.isReconnecting) {
        this.attemptReconnect();
      }
    });

    this.provider.on('error', (error) => {
      this.emit('error', error);
      if (!this.isReconnecting) {
        this.attemptReconnect();
      }
    });
  }

  private async attemptReconnect(): Promise<void> {
    if (this.isReconnecting || this.reconnectAttempts >= this.maxReconnectAttempts) {
      return;
    }

    this.isReconnecting = true;
    this.reconnectAttempts++;

    try {
      await new Promise(resolve => setTimeout(resolve, this.reconnectDelay));
      await this.provider.connect();
      this.reconnectAttempts = 0;
      this.isReconnecting = false;
      this.emit('reconnected');
    } catch (error) {
      this.isReconnecting = false;
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.attemptReconnect();
      } else {
        this.emit('reconnect_failed', error);
      }
    }
  }
}

export {
  VoiceProvider,
  ASRAdapter,
  TTSAdapter,
  VoiceProviderEvents,
  VoiceProviderConfig,
  AudioChunk,
  TranscriptResult,
  TTSRequest,
  TTSResult,
  VoiceSessionState,
  PerformanceMetrics,
  AudioFormat
} from '../types';