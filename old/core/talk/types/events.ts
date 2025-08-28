/**
 * Alice Voice Pipeline Event Types
 * Sub-500ms streaming voice pipeline with barge-in support
 */

// Upstream events (client → server)
export interface AudioFrameEvent {
  type: 'audio.frame';
  sessionId: string;
  seq: number;
  data: ArrayBuffer; // PCM or Opus encoded audio
  timestamp: number;
}

export interface BargeInEvent {
  type: 'control.barge_in';
  sessionId: string;
  playbackId: string;
  timestamp: number;
}

export interface MicControlEvent {
  type: 'control.mic';
  sessionId: string;
  action: 'open' | 'close';
  timestamp: number;
}

export type UpstreamEvent = AudioFrameEvent | BargeInEvent | MicControlEvent;

// Downstream events (server → client)
export interface STTPartialEvent {
  type: 'stt.partial';
  text: string;
  confidence: number;
  timestamp: number;
}

export interface STTFinalEvent {
  type: 'stt.final';
  text: string;
  confidence: number;
  timestamp: number;
}

export interface LLMDeltaEvent {
  type: 'llm.delta';
  text: string;
  timestamp: number;
}

export interface TTSAudioChunkEvent {
  type: 'tts.audio_chunk';
  playbackId: string;
  seq: number;
  data: ArrayBuffer; // PCM audio data
  timestamp: number;
}

export interface TTSBeginEvent {
  type: 'tts.begin';
  playbackId: string;
  timestamp: number;
}

export interface TTSEndEvent {
  type: 'tts.end';
  playbackId: string;
  timestamp: number;
}

export interface TTSActiveEvent {
  type: 'tts.active';
  playbackId: string;
  active: boolean;
  timestamp: number;
}

export type DownstreamEvent = 
  | STTPartialEvent 
  | STTFinalEvent 
  | LLMDeltaEvent 
  | TTSAudioChunkEvent 
  | TTSBeginEvent 
  | TTSEndEvent 
  | TTSActiveEvent;

export type VoiceEvent = UpstreamEvent | DownstreamEvent;

// Performance metrics
export interface VoiceMetrics {
  sessionId: string;
  timestamp: number;
  route: 'local_fast' | 'local_reason' | 'cloud_complex';
  first_partial_ms?: number;
  ttft_ms?: number; // Time to first token
  tts_first_chunk_ms?: number;
  total_latency_ms?: number;
  barge_in_cut_ms?: number;
  privacy_leak_attempts?: number;
}

// Configuration
export interface VoiceConfig {
  // Audio settings
  jitter_ms: number;
  vad_min_voiced_frames: number;
  barge_in_fade_ms: number;
  
  // ASR settings
  asr_chunk_ms: number;
  asr_stabilize_ms: number;
  
  // LLM settings
  llm_max_new_tokens: number;
  llm_temperature: number;
  
  // TTS settings
  tts_chunk_ms: number;
  
  // Privacy settings
  safe_summary_maxlen: number;
  allow_cloud: boolean;
  cloud_ttfa_degrade_ms: number;
}

export const DEFAULT_VOICE_CONFIG: VoiceConfig = {
  jitter_ms: 100,
  vad_min_voiced_frames: 2,
  barge_in_fade_ms: 100,
  asr_chunk_ms: 200,
  asr_stabilize_ms: 250,
  llm_max_new_tokens: 40,
  llm_temperature: 0.2,
  tts_chunk_ms: 60,
  safe_summary_maxlen: 300,
  allow_cloud: false,
  cloud_ttfa_degrade_ms: 600
};