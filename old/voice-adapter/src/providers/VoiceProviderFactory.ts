/**
 * Voice Provider Factory - Real Implementation
 */
import type { VoiceProvider, VoiceConfig, OpenAIRealtimeConfig } from '../types/index.js';
import { OpenAIRealtimeProvider } from './OpenAIRealtimeProvider.js';
import { WhisperStubProvider } from './WhisperStubProvider.js';
import { PiperStubProvider } from './PiperStubProvider.js';
import { VoiceConfigManager } from '../config/VoiceConfig.js';

export interface ProviderFactoryConfig {
  voice: VoiceConfig;
  openai?: OpenAIRealtimeConfig;
}

export class VoiceProviderFactory {
  /**
   * Create voice provider based on configuration
   */
  static createProvider(config: ProviderFactoryConfig): VoiceProvider {
    const { voice, openai } = config;
    
    switch (voice.provider) {
      case 'openai':
        if (!openai) {
          throw new Error('OpenAI configuration required for OpenAI provider');
        }
        return new OpenAIRealtimeProvider(openai);
        
      case 'local':
        // For local mode, we use Whisper for ASR (Piper has no ASR)
        console.warn('Local provider using Whisper stub - not fully implemented');
        return new WhisperStubProvider();
        
      case 'hybrid':
        // Hybrid mode uses OpenAI as primary with local fallback
        console.warn('Hybrid provider not yet implemented - using OpenAI only');
        if (!openai) {
          throw new Error('OpenAI configuration required for hybrid provider');
        }
        return new OpenAIRealtimeProvider(openai);
        
      default:
        throw new Error(`Unknown voice provider: ${voice.provider}`);
    }
  }
  
  /**
   * Create provider with environment-based configuration
   */
  static createFromEnvironment(): VoiceProvider {
    const configManager = VoiceConfigManager.getInstance();
    configManager.loadFromEnvironment();
    
    const voiceConfig = configManager.getConfig();
    
    const factoryConfig: ProviderFactoryConfig = {
      voice: voiceConfig
    };
    
    // Add OpenAI config if provider is openai or hybrid
    if (voiceConfig.provider === 'openai' || voiceConfig.provider === 'hybrid') {
      const openaiConfig = configManager.getOpenAIConfig();
      
      if (!openaiConfig.apiKey) {
        throw new Error('OPENAI_API_KEY environment variable required for OpenAI provider');
      }
      
      factoryConfig.openai = openaiConfig;
    }
    
    return this.createProvider(factoryConfig);
  }
  
  /**
   * Get available providers
   */
  static getAvailableProviders(): Array<{
    id: string;
    name: string;
    description: string;
    available: boolean;
    requirements?: string[];
  }> {
    return [
      {
        id: 'openai',
        name: 'OpenAI Realtime',
        description: 'OpenAI Realtime API with GPT-4 and high-quality voices',
        available: !!process.env.OPENAI_API_KEY,
        requirements: ['OPENAI_API_KEY']
      },
      {
        id: 'local',
        name: 'Local (Whisper + Piper)',
        description: 'Local Whisper ASR + Piper TTS (privacy-first)',
        available: false,
        requirements: ['Local model files', 'Sufficient compute']
      },
      {
        id: 'hybrid',
        name: 'Hybrid',
        description: 'OpenAI primary with local fallback',
        available: false,
        requirements: ['OPENAI_API_KEY', 'Local models']
      }
    ];
  }
  
  /**
   * Validate provider configuration
   */
  static validateConfig(config: ProviderFactoryConfig): string[] {
    const errors: string[] = [];
    
    if (!config.voice) {
      errors.push('Voice configuration is required');
      return errors;
    }
    
    // Validate provider-specific requirements
    switch (config.voice.provider) {
      case 'openai':
      case 'hybrid':
        if (!config.openai) {
          errors.push('OpenAI configuration is required');
        } else {
          if (!config.openai.apiKey) {
            errors.push('OpenAI API key is required');
          }
          if (!config.openai.apiKey.startsWith('sk-')) {
            errors.push('OpenAI API key format appears invalid');
          }
          if (config.openai.maxTokens < 1 || config.openai.maxTokens > 4096) {
            errors.push('OpenAI maxTokens must be between 1 and 4096');
          }
          if (config.openai.temperature !== undefined) {
            if (config.openai.temperature < 0 || config.openai.temperature > 2) {
              errors.push('OpenAI temperature must be between 0 and 2');
            }
          }
          
          const validVoices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'];
          if (!validVoices.includes(config.openai.voice)) {
            errors.push(`OpenAI voice must be one of: ${validVoices.join(', ')}`);
          }
        }
        break;
        
      case 'local':
        // Add local provider validation here when implemented
        break;
    }
    
    // Validate VAD configuration
    if (config.voice.vad.sensitivity < 0 || config.voice.vad.sensitivity > 1) {
      errors.push('VAD sensitivity must be between 0 and 1');
    }
    
    if (config.voice.vad.timeout_ms < 100 || config.voice.vad.timeout_ms > 10000) {
      errors.push('VAD timeout must be between 100ms and 10000ms');
    }
    
    // Validate audio configuration
    const validSampleRates = [8000, 16000, 22050, 24000, 44100, 48000];
    if (!validSampleRates.includes(config.voice.audio.sampleRate)) {
      errors.push(`Audio sample rate must be one of: ${validSampleRates.join(', ')}`);
    }
    
    const validFormats = ['pcm16', 'opus', 'mp3'];
    if (!validFormats.includes(config.voice.audio.format)) {
      errors.push(`Audio format must be one of: ${validFormats.join(', ')}`);
    }
    
    if (config.voice.audio.channels < 1 || config.voice.audio.channels > 2) {
      errors.push('Audio channels must be 1 (mono) or 2 (stereo)');
    }
    
    // Validate metrics configuration
    if (config.voice.metrics.batch_interval_ms < 1000) {
      errors.push('Metrics batch interval must be at least 1000ms');
    }
    
    return errors;
  }
  
  /**
   * Test provider connection
   */
  static async testProvider(config: ProviderFactoryConfig): Promise<{
    success: boolean;
    latency_ms?: number;
    error?: string;
  }> {
    const startTime = Date.now();
    
    try {
      const provider = this.createProvider(config);
      await provider.initialize();
      
      const status = provider.getStatus();
      const latency = Date.now() - startTime;
      
      await provider.destroy();
      
      return {
        success: status.connected,
        latency_ms: latency,
        error: status.error?.message
      };
    } catch (error) {
      return {
        success: false,
        latency_ms: Date.now() - startTime,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }
}