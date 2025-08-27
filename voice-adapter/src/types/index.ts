/**
 * @alice/voice-adapter - Core Type Definitions
 * 
 * Modular voice interface supporting multiple providers:
 * - OpenAI Realtime API (primary)
 * - Local Whisper + Piper (future)
 * - Hybrid configurations
 */

// ============================================================================
// Configuration Types
// ============================================================================

export type VoiceProviderType = 'openai' | 'local' | 'hybrid';

export interface VoiceConfig {
  /** Voice provider selection */
  provider: VoiceProviderType;
  
  /** Voice Activity Detection settings */
  vad: {
    enabled: boolean;
    sensitivity: number; // 0-1, higher = more sensitive
    timeout_ms: number;  // ms of silence before stopping
    rmsThreshold: number; // RMS threshold for speech detection
  };
  
  /** Performance and metrics */
  metrics: {
    enabled: boolean;
    batch_interval_ms: number;
    export_endpoint?: string;
  };
  
  /** Audio format settings */
  audio: {
    sampleRate: number;
    format: 'pcm16' | 'opus' | 'mp3';
    channels: number;
  };
}

export interface OpenAIRealtimeConfig {
  apiKey: string;
  model: string;
  voice: 'alloy' | 'echo' | 'fable' | 'onyx' | 'nova' | 'shimmer';
  maxTokens: number;
  temperature?: number;
  endpointUrl?: string;
}

// ============================================================================
// Core Adapter Interfaces
// ============================================================================

export interface VoiceProvider {
  asr: ASRAdapter;
  tts: TTSAdapter;
  initialize(): Promise<void>;
  destroy(): Promise<void>;
  isHealthy(): boolean;
  getStatus(): ProviderStatus;
  getMetrics(): VoiceMetrics;
  resetMetrics(): void;
}

export interface ASRAdapter {
  initialize(): Promise<void>;
  destroy(): Promise<void>;
  start(options: ASROptions, handlers: ASRHandlers): Promise<void>;
  stop(): Promise<void>;
  pushAudio(chunk: ArrayBuffer | Float32Array | Int16Array): void;
  isListening(): boolean;
  isInitialized(): boolean;
  getConfig(): Record<string, any>;
  updateConfig(config: Partial<ASROptions>): void;
}

export interface TTSAdapter {
  initialize(): Promise<void>;
  destroy(): Promise<void>;
  speak(options: TTSOptions, handlers: TTSHandlers): Promise<string>;
  cancel(playbackId?: string): Promise<void>;
  cancelAll(): Promise<void>;
  isSpeaking(): boolean;
  isInitialized(): boolean;
  getActiveSynthesis(): string[];
  getConfig(): Record<string, any>;
  updateConfig(config: Partial<TTSOptions>): void;
  getAvailableVoices(): Promise<Array<{ id: string; name: string; language: string }>>;
}

export interface ProviderStatus {
  connected: boolean;
  provider: string;
  error?: VoiceError;
}

// ============================================================================
// ASR (Automatic Speech Recognition) Types
// ============================================================================

export interface ASROptions {
  language?: string;
  continuous?: boolean;
  interimResults?: boolean;
  maxAlternatives?: number;
  audioFormat?: 'pcm16' | 'opus';
  sampleRate?: number;
}

export interface ASRHandlers {
  onStart?: () => void;
  onPartial?: (result: PartialTranscription) => void;
  onFinal?: (result: FinalTranscription) => void;
  onError?: (error: VoiceError) => void;
  onEnd?: () => void;
  onSilence?: () => void;
  onSpeechStart?: () => void;
}

export interface BaseTranscription {
  text: string;
  confidence: number;
  timestamp_ms: number;
  session_id: string;
}

export interface PartialTranscription extends BaseTranscription {
  isFinal: false;
  isStable: boolean;
  alternatives?: Array<{
    text: string;
    confidence: number;
  }>;
}

export interface FinalTranscription extends BaseTranscription {
  isFinal: true;
  duration_ms: number;
  words?: WordSegment[];
  language?: string;
}

export interface WordSegment {
  word: string;
  start_ms: number;
  end_ms: number;
  confidence: number;
}

// ============================================================================
// TTS (Text-to-Speech) Types
// ============================================================================

export interface TTSOptions {
  text?: string;
  ssml?: string;
  voiceId?: string;
  rate?: number;     // 0.25-4.0, 1.0 = normal
  pitch?: number;    // -20 to +20 semitones, 0 = normal
  volume?: number;   // 0.0-1.0, 1.0 = max
  format?: 'pcm16' | 'opus' | 'mp3';
  sampleRate?: number;
  streaming?: boolean;
}

export interface TTSHandlers {
  onStart?: (playbackId: string) => void;
  onAudioChunk?: (chunk: AudioChunk) => void;
  onProgress?: (progress: TTSProgress) => void;
  onEnd?: (playbackId: string) => void;
  onError?: (error: VoiceError, playbackId?: string) => void;
  onCancel?: (playbackId: string) => void;
}

export interface AudioChunk {
  data: ArrayBuffer | Float32Array | Int16Array;
  sampleRate: number;
  timestamp_ms: number;
  duration_ms: number;
  isFirst: boolean;
  isFinal: boolean;
  format: 'pcm16' | 'float32' | 'opus';
}

export interface TTSProgress {
  playbackId: string;
  charactersSpoken: number;
  totalCharacters: number;
  timeElapsed_ms: number;
  estimatedTimeRemaining_ms?: number;
}

// ============================================================================
// Error Types
// ============================================================================

export interface VoiceError {
  code: VoiceErrorCode;
  message: string;
  details?: Record<string, any>;
  recoverable: boolean;
  timestamp_ms: number;
}

export type VoiceErrorCode = 
  // Network errors
  | 'network_connection_failed'
  | 'network_timeout' 
  | 'network_disconnect'
  // Authentication errors
  | 'auth_invalid_key'
  | 'auth_quota_exceeded'
  | 'auth_permission_denied'
  // Audio errors
  | 'audio_device_unavailable'
  | 'audio_format_unsupported'
  | 'audio_processing_failed'
  // Service errors
  | 'service_unavailable'
  | 'service_overloaded'
  | 'service_internal_error'
  // Configuration errors
  | 'config_invalid'
  | 'provider_not_available'
  // Usage errors
  | 'text_too_long'
  | 'language_unsupported'
  | 'voice_unavailable';

// ============================================================================
// Performance Metrics Types
// ============================================================================

export interface VoiceMetrics {
  session_id: string;
  timestamp_ms: number;
  provider: VoiceProviderType;
  
  // Latency measurements (all in milliseconds)
  asr_partial_latency_ms?: number;     // Time to first partial result
  asr_final_latency_ms?: number;       // Time to final transcription
  llm_latency_ms?: number;             // LLM processing time
  tts_ttfa_ms?: number;                // Time to First Audio
  e2e_roundtrip_ms?: number;           // Complete user interaction
  
  // Quality metrics
  asr_confidence_score?: number;       // Average confidence
  audio_quality_score?: number;        // Signal quality
  
  // Usage statistics
  characters_transcribed?: number;
  characters_synthesized?: number;
  audio_duration_seconds?: number;
  
  // Error tracking
  error_count: number;
  fallback_triggered: boolean;
  retry_count?: number;
  
  // Additional metadata
  language?: string;
  voice_id?: string;
  user_agent?: string;
}

export interface MetricsSnapshot {
  timespan_ms: number;
  total_sessions: number;
  success_rate: number;
  
  // Latency percentiles
  asr_partial_p50: number;
  asr_partial_p95: number;
  asr_final_p50: number;
  asr_final_p95: number;
  tts_ttfa_p50: number;
  tts_ttfa_p95: number;
  e2e_roundtrip_p50: number;
  e2e_roundtrip_p95: number;
  
  // Error statistics
  total_errors: number;
  error_rate: number;
  fallback_rate: number;
  
  // Top error types
  top_errors: Array<{
    code: VoiceErrorCode;
    count: number;
    rate: number;
  }>;
}

// ============================================================================
// Voice Activity Detection Types
// ============================================================================

export type VADState = 'silence' | 'speech' | 'unknown';

export interface VADResult {
  state: VADState;
  confidence: number;
  energy: number;
  timestamp_ms: number;
}

export interface VADOptions {
  sampleRate: number;
  frameSize: number;
  energyThreshold: number;
  silenceThreshold: number;
  speechThreshold: number;
  hangoverFrames: number; // Frames to continue after speech ends
}

// ============================================================================
// Event System Types
// ============================================================================

export interface VoiceEvents {
  // Session lifecycle
  'session:start': (sessionId: string) => void;
  'session:end': (sessionId: string) => void;
  
  // ASR events
  'asr:start': () => void;
  'asr:partial': (result: PartialTranscription) => void;
  'asr:final': (result: FinalTranscription) => void;
  'asr:error': (error: VoiceError) => void;
  'asr:end': () => void;
  
  // TTS events  
  'tts:start': (playbackId: string) => void;
  'tts:chunk': (chunk: AudioChunk) => void;
  'tts:progress': (progress: TTSProgress) => void;
  'tts:end': (playbackId: string) => void;
  'tts:error': (error: VoiceError, playbackId?: string) => void;
  'tts:cancel': (playbackId: string) => void;
  
  // VAD events
  'vad:speech_start': (result: VADResult) => void;
  'vad:speech_end': (result: VADResult) => void;
  'vad:silence': (result: VADResult) => void;
  
  // Performance events
  'metrics:collected': (metrics: VoiceMetrics) => void;
  'metrics:exported': (snapshot: MetricsSnapshot) => void;
  
  // Provider events
  'provider:connected': (provider: VoiceProviderType) => void;
  'provider:disconnected': (provider: VoiceProviderType) => void;
  'provider:fallback': (from: VoiceProviderType, to: VoiceProviderType) => void;
  
  // General events
  'error': (error: VoiceError) => void;
  'warning': (message: string, details?: any) => void;
  'debug': (message: string, details?: any) => void;
}

// ============================================================================
// Utility Types
// ============================================================================

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type RequireAtLeastOne<T, Keys extends keyof T = keyof T> = 
  Pick<T, Exclude<keyof T, Keys>> & {
    [K in Keys]-?: Required<Pick<T, K>> & Partial<Pick<T, Exclude<Keys, K>>>;
  }[Keys];

// Export default configuration
export const DEFAULT_VOICE_CONFIG: VoiceConfig = {
  provider: 'openai',
  vad: {
    enabled: true,
    sensitivity: 0.6,
    timeout_ms: 1500,
    rmsThreshold: 0.01,
  },
  metrics: {
    enabled: true,
    batch_interval_ms: 5000,
  },
  audio: {
    sampleRate: 16000,
    format: 'pcm16',
    channels: 1,
  },
};