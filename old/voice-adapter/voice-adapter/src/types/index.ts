import { EventEmitter } from 'eventemitter3';

/**
 * Audio format specifications
 */
export interface AudioFormat {
  sampleRate: number;
  channels: number;
  bitDepth: 16 | 24 | 32;
  encoding: 'pcm' | 'mp3' | 'opus' | 'wav';
}

/**
 * Audio chunk data with metadata
 */
export interface AudioChunk {
  data: Buffer;
  format: AudioFormat;
  timestamp: number;
  duration: number;
  sequenceId?: number;
}

/**
 * Transcript result from ASR
 */
export interface TranscriptResult {
  text: string;
  confidence: number;
  isFinal: boolean;
  timestamp: number;
  wordTimings?: Array<{
    word: string;
    start: number;
    end: number;
    confidence: number;
  }>;
}

/**
 * TTS synthesis request
 */
export interface TTSRequest {
  text: string;
  voice?: string;
  speed?: number;
  pitch?: number;
  format?: AudioFormat;
}

/**
 * TTS synthesis result
 */
export interface TTSResult {
  audio: AudioChunk;
  text: string;
  voice: string;
  metadata?: {
    duration: number;
    wordTimings?: Array<{
      word: string;
      start: number;
      end: number;
    }>;
  };
}

/**
 * Voice Activity Detection result
 */
export interface VADResult {
  isVoiceActive: boolean;
  confidence: number;
  timestamp: number;
  energyLevel: number;
}

/**
 * Performance metrics
 */
export interface PerformanceMetrics {
  latency: {
    asr: number;
    tts: number;
    endToEnd: number;
  };
  throughput: {
    audioProcessed: number;
    messagesPerSecond: number;
  };
  quality: {
    audioQuality: number;
    transcriptAccuracy: number;
  };
  timestamps: {
    requestStart: number;
    asrComplete: number;
    ttsStart: number;
    ttsComplete: number;
    responseEnd: number;
  };
}

/**
 * Voice provider configuration options
 */
export interface VoiceProviderConfig {
  provider: 'openai-realtime' | 'whisper' | 'piper';
  latencyTarget: number;
  audioFormat?: AudioFormat;
  enableMetrics?: boolean;
  enableVAD?: boolean;
  
  // OpenAI Realtime specific
  openai?: {
    apiKey: string;
    model: string;
    voice?: 'alloy' | 'echo' | 'fable' | 'onyx' | 'nova' | 'shimmer';
    temperature?: number;
    maxTokens?: number;
    modalities?: Array<'text' | 'audio'>;
    instructions?: string;
  };
  
  // Whisper specific
  whisper?: {
    modelPath: string;
    language?: string;
    temperature?: number;
    initialPrompt?: string;
  };
  
  // Piper specific
  piper?: {
    modelPath: string;
    voice?: string;
    speakingRate?: number;
  };
}

/**
 * Voice session state
 */
export type VoiceSessionState = 
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'active'
  | 'error'
  | 'reconnecting';

/**
 * Voice provider events
 */
export interface VoiceProviderEvents {
  // Connection events
  'connected': () => void;
  'disconnected': () => void;
  'error': (error: Error) => void;
  'state_changed': (state: VoiceSessionState) => void;
  
  // Audio events
  'audio_input': (chunk: AudioChunk) => void;
  'audio_output': (chunk: AudioChunk) => void;
  'transcript': (result: TranscriptResult) => void;
  'tts_result': (result: TTSResult) => void;
  
  // VAD events
  'voice_start': (vad: VADResult) => void;
  'voice_end': (vad: VADResult) => void;
  'vad_result': (vad: VADResult) => void;
  
  // Metrics events
  'metrics': (metrics: PerformanceMetrics) => void;
  'latency_update': (latency: number, type: 'asr' | 'tts' | 'endToEnd') => void;
  'reconnected': () => void;
  'reconnect_failed': (error: Error) => void;
}

/**
 * ASR (Automatic Speech Recognition) adapter interface
 */
export interface ASRAdapter extends EventEmitter<VoiceProviderEvents> {
  /**
   * Start speech recognition
   */
  start(): Promise<void>;
  
  /**
   * Stop speech recognition
   */
  stop(): Promise<void>;
  
  /**
   * Process audio chunk
   */
  processAudio(chunk: AudioChunk): Promise<void>;
  
  /**
   * Get current state
   */
  getState(): VoiceSessionState;
  
  /**
   * Get supported audio formats
   */
  getSupportedFormats(): AudioFormat[];
}

/**
 * TTS (Text-to-Speech) adapter interface
 */
export interface TTSAdapter extends EventEmitter<VoiceProviderEvents> {
  /**
   * Synthesize speech from text
   */
  synthesize(request: TTSRequest): Promise<TTSResult>;
  
  /**
   * Start streaming synthesis
   */
  startStream(): Promise<void>;
  
  /**
   * Stop streaming synthesis
   */
  stopStream(): Promise<void>;
  
  /**
   * Stream text for synthesis
   */
  streamText(text: string): Promise<void>;
  
  /**
   * Get available voices
   */
  getVoices(): Promise<string[]>;
  
  /**
   * Get supported audio formats
   */
  getSupportedFormats(): AudioFormat[];
}

/**
 * Main voice provider interface
 */
export interface VoiceProvider extends EventEmitter<VoiceProviderEvents> {
  /**
   * Connect to the voice service
   */
  connect(): Promise<void>;
  
  /**
   * Disconnect from the voice service
   */
  disconnect(): Promise<void>;
  
  /**
   * Send audio input
   */
  sendAudio(chunk: AudioChunk): Promise<void>;
  
  /**
   * Send text input
   */
  sendText(text: string): Promise<void>;
  
  /**
   * Start voice session
   */
  startSession(): Promise<void>;
  
  /**
   * End voice session
   */
  endSession(): Promise<void>;
  
  /**
   * Get current session state
   */
  getState(): VoiceSessionState;
  
  /**
   * Get ASR adapter
   */
  getASR(): ASRAdapter | null;
  
  /**
   * Get TTS adapter
   */
  getTTS(): TTSAdapter | null;
  
  /**
   * Get current metrics
   */
  getMetrics(): PerformanceMetrics | null;
  
  /**
   * Update configuration
   */
  updateConfig(config: Partial<VoiceProviderConfig>): void;
}

/**
 * Voice provider factory interface
 */
export interface VoiceProviderFactory {
  /**
   * Create a voice provider instance
   */
  create(type: string, config: VoiceProviderConfig): Promise<VoiceProvider>;
  
  /**
   * Get supported provider types
   */
  getSupportedProviders(): string[];
  
  /**
   * Register a new provider type
   */
  registerProvider(type: string, factory: (config: VoiceProviderConfig) => Promise<VoiceProvider>): void;
}

/**
 * Latency measurement data
 */
export interface LatencyMeasurement {
  type: 'asr' | 'tts' | 'endToEnd';
  value: number;
  timestamp: number;
  sessionId?: string;
}

/**
 * Audio utility functions interface
 */
export interface AudioUtilsInterface {
  /**
   * Convert audio between formats
   */
  convertFormat(input: AudioChunk, targetFormat: AudioFormat): Promise<AudioChunk>;
  
  /**
   * Resample audio to different sample rate
   */
  resample(input: AudioChunk, targetSampleRate: number): Promise<AudioChunk>;
  
  /**
   * Normalize audio volume
   */
  normalize(input: AudioChunk, targetLevel?: number): AudioChunk;
  
  /**
   * Detect audio format from buffer
   */
  detectFormat(buffer: Buffer): AudioFormat | null;
  
  /**
   * Calculate audio duration
   */
  getDuration(chunk: AudioChunk): number;
  
  /**
   * Split audio into chunks
   */
  splitIntoChunks(input: AudioChunk, chunkDurationMs: number): AudioChunk[];
}

/**
 * VAD (Voice Activity Detection) interface
 */
export interface VADInterface {
  /**
   * Initialize VAD with configuration
   */
  initialize(config?: {
    sampleRate?: number;
    frameSize?: number;
    threshold?: number;
  }): void;
  
  /**
   * Process audio for voice activity
   */
  processAudio(chunk: AudioChunk): VADResult;
  
  /**
   * Set voice activity threshold
   */
  setThreshold(threshold: number): void;
  
  /**
   * Get current configuration
   */
  getConfig(): {
    sampleRate: number;
    frameSize: number;
    threshold: number;
  };
}

/**
 * OpenAI Realtime API specific types
 */
export namespace OpenAIRealtime {
  export interface RealtimeEvent {
    type: string;
    event_id?: string;
    [key: string]: any;
  }
  
  export interface SessionConfig {
    modalities: Array<'text' | 'audio'>;
    instructions: string;
    voice: string;
    input_audio_format: 'pcm16' | 'g711_ulaw' | 'g711_alaw';
    output_audio_format: 'pcm16' | 'g711_ulaw' | 'g711_alaw';
    input_audio_transcription?: {
      model: 'whisper-1';
    };
    turn_detection?: {
      type: 'server_vad' | 'none';
      threshold?: number;
      prefix_padding_ms?: number;
      silence_duration_ms?: number;
    };
    tools?: Array<{
      type: 'function';
      name: string;
      description: string;
      parameters: any;
    }>;
    tool_choice?: 'auto' | 'none' | 'required' | { type: 'function'; name: string };
    temperature?: number;
    max_response_output_tokens?: number | 'inf';
  }
  
  export interface InputAudioBufferAppend {
    type: 'input_audio_buffer.append';
    audio: string; // base64 encoded audio
  }
  
  export interface InputAudioBufferCommit {
    type: 'input_audio_buffer.commit';
  }
  
  export interface ResponseCreate {
    type: 'response.create';
    response?: {
      modalities?: Array<'text' | 'audio'>;
      instructions?: string;
      voice?: string;
      output_audio_format?: 'pcm16' | 'g711_ulaw' | 'g711_alaw';
      tools?: Array<any>;
      tool_choice?: string | { type: 'function'; name: string };
      temperature?: number;
      max_output_tokens?: number | 'inf';
    };
  }
}

/**
 * Error types
 */
export class VoiceProviderError extends Error {
  constructor(
    message: string,
    public code: string,
    public provider: string,
    public originalError?: Error
  ) {
    super(message);
    this.name = 'VoiceProviderError';
  }
}

export class ASRError extends VoiceProviderError {
  constructor(message: string, originalError?: Error) {
    super(message, 'ASR_ERROR', 'asr', originalError);
    this.name = 'ASRError';
  }
}

export class TTSError extends VoiceProviderError {
  constructor(message: string, originalError?: Error) {
    super(message, 'TTS_ERROR', 'tts', originalError);
    this.name = 'TTSError';
  }
}

export class ConnectionError extends VoiceProviderError {
  constructor(message: string, provider: string, originalError?: Error) {
    super(message, 'CONNECTION_ERROR', provider, originalError);
    this.name = 'ConnectionError';
  }
}

/**
 * Default audio format configuration
 */
export const DEFAULT_AUDIO_FORMAT: AudioFormat = {
  sampleRate: 24000,
  channels: 1,
  bitDepth: 16,
  encoding: 'pcm'
};

/**
 * Default voice provider configuration
 */
export const DEFAULT_VOICE_CONFIG: Partial<VoiceProviderConfig> = {
  latencyTarget: 500,
  audioFormat: DEFAULT_AUDIO_FORMAT,
  enableMetrics: true,
  enableVAD: true
};