/**
 * Core Voice Adapter Interfaces
 */
import type { 
  ASROptions, ASRHandlers, PartialTranscription, FinalTranscription,
  TTSOptions, TTSHandlers, AudioChunk,
  VoiceError, VoiceMetrics 
} from '../types/index.js';

export interface ASRAdapter {
  // Lifecycle
  initialize(): Promise<void>;
  destroy(): Promise<void>;
  
  // Recording control
  start(options: ASROptions, handlers: ASRHandlers): Promise<void>;
  stop(): Promise<void>;
  
  // Audio input
  pushAudio(chunk: ArrayBuffer | Float32Array | Int16Array): void;
  
  // State
  isListening(): boolean;
  isInitialized(): boolean;
  
  // Configuration
  getConfig(): Record<string, any>;
  updateConfig(config: Partial<ASROptions>): void;
}

export interface TTSAdapter {
  // Lifecycle  
  initialize(): Promise<void>;
  destroy(): Promise<void>;
  
  // Speech synthesis
  speak(options: TTSOptions, handlers: TTSHandlers): Promise<string>; // Returns playback ID
  cancel(playbackId?: string): Promise<void>;
  cancelAll(): Promise<void>;
  
  // State
  isSpeaking(): boolean;
  isInitialized(): boolean;
  getActiveSynthesis(): string[]; // Return active playback IDs
  
  // Configuration
  getConfig(): Record<string, any>;
  updateConfig(config: Partial<TTSOptions>): void;
  
  // Voice management
  getAvailableVoices(): Promise<Array<{
    id: string;
    name: string;
    language: string;
    gender?: 'male' | 'female' | 'neutral';
  }>>;
}

export interface VoiceProvider {
  // Core adapters
  asr: ASRAdapter;
  tts: TTSAdapter;
  
  // Provider lifecycle
  initialize(): Promise<void>;
  destroy(): Promise<void>;
  
  // Health & diagnostics
  isHealthy(): boolean;
  getStatus(): {
    connected: boolean;
    provider: string;
    latency_ms?: number;
    error?: VoiceError;
  };
  
  // Metrics
  getMetrics(): VoiceMetrics;
  resetMetrics(): void;
}