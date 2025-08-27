/**
 * Whisper Stub Provider - placeholder
 */
import type { VoiceProvider, ASRAdapter, TTSAdapter } from '../types/index.js';

export class WhisperStubProvider implements VoiceProvider {
  asr: ASRAdapter = new StubASR();
  tts: TTSAdapter = new StubTTS();
  
  async initialize() { throw new Error('Whisper provider not implemented'); }
  async destroy() {}
  isHealthy() { return false; }
  getStatus() { return { connected: false, provider: 'whisper-stub' }; }
  getMetrics() { return { session_id: '', timestamp_ms: Date.now(), provider: 'local' as const, error_count: 0, fallback_triggered: false }; }
  resetMetrics() {}
}

class StubASR implements ASRAdapter {
  async initialize() {}
  async destroy() {}
  async start() {}
  async stop() {}
  pushAudio() {}
  isListening() { return false; }
  isInitialized() { return false; }
  getConfig() { return {}; }
  updateConfig() {}
}

class StubTTS implements TTSAdapter {
  async initialize() {}
  async destroy() {}
  async speak() { return 'stub'; }
  async cancel() {}
  async cancelAll() {}
  isSpeaking() { return false; }
  isInitialized() { return false; }
  getActiveSynthesis() { return []; }
  getConfig() { return {}; }
  updateConfig() {}
  async getAvailableVoices() { return []; }
}