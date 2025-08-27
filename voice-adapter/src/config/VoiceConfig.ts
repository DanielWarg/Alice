/**
 * Voice Configuration - minimal implementation
 */
import type { VoiceConfig } from '../types/index.js';

export class VoiceConfigManager {
  private static instance: VoiceConfigManager;
  
  static getInstance() {
    if (!VoiceConfigManager.instance) {
      VoiceConfigManager.instance = new VoiceConfigManager();
    }
    return VoiceConfigManager.instance;
  }
  
  getConfig(): VoiceConfig {
    return {
      provider: 'openai',
      vad: { enabled: true, sensitivity: 0.6, timeout_ms: 1500, rmsThreshold: 0.01 },
      metrics: { enabled: true, batch_interval_ms: 5000 },
      audio: { sampleRate: 16000, format: 'pcm16', channels: 1 }
    };
  }
  
  getOpenAIConfig() {
    return {
      apiKey: process.env.OPENAI_API_KEY || '',
      model: 'gpt-4o-realtime-preview-2024-12-17',
      voice: 'alloy' as const,
      maxTokens: 150,
      temperature: 0.8
    };
  }
}

export function getVoiceConfig(): VoiceConfig {
  return VoiceConfigManager.getInstance().getConfig();
}

export function getOpenAIConfig() {
  return VoiceConfigManager.getInstance().getOpenAIConfig();
}