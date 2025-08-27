import {
  VoiceProvider,
  VoiceProviderConfig,
  VoiceProviderFactory as IVoiceProviderFactory,
  VoiceProviderError
} from '../types';

import { OpenAIRealtimeProvider } from './OpenAIRealtimeProvider';
import { WhisperStubProvider, isWhisperAvailable } from './WhisperStubProvider';
import { PiperStubProvider, isPiperAvailable } from './PiperStubProvider';

/**
 * Factory for creating voice provider instances
 */
export class VoiceProviderFactory implements IVoiceProviderFactory {
  private static instance: VoiceProviderFactory;
  private registeredProviders: Map<string, (config: VoiceProviderConfig) => Promise<VoiceProvider>> = new Map();

  constructor() {
    this.registerBuiltInProviders();
  }

  /**
   * Get singleton instance of the factory
   */
  static getInstance(): VoiceProviderFactory {
    if (!VoiceProviderFactory.instance) {
      VoiceProviderFactory.instance = new VoiceProviderFactory();
    }
    return VoiceProviderFactory.instance;
  }

  /**
   * Create a voice provider instance
   */
  async create(type: string, config: VoiceProviderConfig): Promise<VoiceProvider> {
    const normalizedType = type.toLowerCase().trim();
    
    if (!this.registeredProviders.has(normalizedType)) {
      throw new VoiceProviderError(
        `Unknown provider type: ${type}`,
        'UNKNOWN_PROVIDER',
        'factory'
      );
    }

    try {
      // Validate configuration for the provider type
      this.validateConfig(normalizedType, config);

      // Create provider instance
      const factory = this.registeredProviders.get(normalizedType)!;
      const provider = await factory(config);

      console.log(`[VoiceProviderFactory] Created ${type} provider`);
      return provider;

    } catch (error) {
      if (error instanceof VoiceProviderError) {
        throw error;
      }
      
      throw new VoiceProviderError(
        `Failed to create ${type} provider: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'PROVIDER_CREATION_FAILED',
        'factory',
        error instanceof Error ? error : undefined
      );
    }
  }

  /**
   * Get supported provider types
   */
  getSupportedProviders(): string[] {
    return Array.from(this.registeredProviders.keys());
  }

  /**
   * Register a new provider type
   */
  registerProvider(type: string, factory: (config: VoiceProviderConfig) => Promise<VoiceProvider>): void {
    const normalizedType = type.toLowerCase().trim();
    
    if (this.registeredProviders.has(normalizedType)) {
      console.warn(`[VoiceProviderFactory] Overriding existing provider: ${type}`);
    }

    this.registeredProviders.set(normalizedType, factory);
    console.log(`[VoiceProviderFactory] Registered provider: ${type}`);
  }

  /**
   * Unregister a provider type
   */
  unregisterProvider(type: string): void {
    const normalizedType = type.toLowerCase().trim();
    
    if (this.registeredProviders.delete(normalizedType)) {
      console.log(`[VoiceProviderFactory] Unregistered provider: ${type}`);
    }
  }

  /**
   * Check if a provider type is available
   */
  isProviderAvailable(type: string): boolean {
    const normalizedType = type.toLowerCase().trim();
    
    switch (normalizedType) {
      case 'openai-realtime':
        return true; // Always available with API key
      
      case 'whisper':
        return isWhisperAvailable();
      
      case 'piper':
        return isPiperAvailable();
      
      default:
        return this.registeredProviders.has(normalizedType);
    }
  }

  /**
   * Get provider information
   */
  getProviderInfo(type: string): ProviderInfo | null {
    const normalizedType = type.toLowerCase().trim();
    
    switch (normalizedType) {
      case 'openai-realtime':
        return {
          name: 'OpenAI Realtime API',
          description: 'Real-time voice conversation using OpenAI\'s Realtime API',
          capabilities: ['asr', 'tts', 'realtime', 'streaming'],
          requirements: ['openai_api_key'],
          latency: 'sub-500ms',
          quality: 'high',
          status: 'production'
        };
      
      case 'whisper':
        return {
          name: 'OpenAI Whisper',
          description: 'High-accuracy speech recognition using OpenAI Whisper',
          capabilities: ['asr', 'multilingual'],
          requirements: ['whisper_model'],
          latency: '200-500ms',
          quality: 'very-high',
          status: 'stub'
        };
      
      case 'piper':
        return {
          name: 'Piper TTS',
          description: 'Fast neural text-to-speech synthesis',
          capabilities: ['tts', 'multilingual', 'multiple_voices'],
          requirements: ['piper_model'],
          latency: '100-300ms',
          quality: 'high',
          status: 'stub'
        };
      
      default:
        return null;
    }
  }

  /**
   * Get recommended provider for use case
   */
  getRecommendedProvider(useCase: VoiceUseCase): string {
    switch (useCase) {
      case 'realtime-conversation':
        return 'openai-realtime';
      
      case 'high-accuracy-transcription':
        return 'whisper';
      
      case 'fast-tts':
        return 'piper';
      
      case 'multilingual-asr':
        return 'whisper';
      
      case 'low-latency-tts':
        return 'piper';
      
      case 'production-ready':
        return 'openai-realtime';
      
      default:
        return 'openai-realtime';
    }
  }

  /**
   * Register built-in providers
   */
  private registerBuiltInProviders(): void {
    // OpenAI Realtime API Provider
    this.registeredProviders.set('openai-realtime', async (config) => {
      return new OpenAIRealtimeProvider(config);
    });

    // Whisper Stub Provider
    this.registeredProviders.set('whisper', async (config) => {
      return new WhisperStubProvider(config);
    });

    // Piper Stub Provider
    this.registeredProviders.set('piper', async (config) => {
      return new PiperStubProvider(config);
    });
  }

  /**
   * Validate configuration for specific provider type
   */
  private validateConfig(type: string, config: VoiceProviderConfig): void {
    // Basic validation
    if (!config) {
      throw new VoiceProviderError(
        'Configuration is required',
        'INVALID_CONFIG',
        'factory'
      );
    }

    // Provider-specific validation
    switch (type) {
      case 'openai-realtime':
        this.validateOpenAIConfig(config);
        break;
      
      case 'whisper':
        this.validateWhisperConfig(config);
        break;
      
      case 'piper':
        this.validatePiperConfig(config);
        break;
    }
  }

  private validateOpenAIConfig(config: VoiceProviderConfig): void {
    if (!config.openai?.apiKey) {
      throw new VoiceProviderError(
        'OpenAI API key is required',
        'MISSING_API_KEY',
        'openai-realtime'
      );
    }

    if (config.openai.apiKey.length < 20) {
      throw new VoiceProviderError(
        'Invalid OpenAI API key format',
        'INVALID_API_KEY',
        'openai-realtime'
      );
    }

    if (config.openai.model && !config.openai.model.includes('realtime')) {
      console.warn('[VoiceProviderFactory] Model may not support realtime features');
    }

    const validVoices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'];
    if (config.openai.voice && !validVoices.includes(config.openai.voice)) {
      throw new VoiceProviderError(
        `Invalid voice: ${config.openai.voice}. Valid voices: ${validVoices.join(', ')}`,
        'INVALID_VOICE',
        'openai-realtime'
      );
    }
  }

  private validateWhisperConfig(config: VoiceProviderConfig): void {
    if (!config.whisper?.modelPath) {
      throw new VoiceProviderError(
        'Whisper model path is required',
        'MISSING_MODEL_PATH',
        'whisper'
      );
    }

    // TODO: Validate model path exists and is accessible
    // TODO: Validate language code if specified
  }

  private validatePiperConfig(config: VoiceProviderConfig): void {
    if (!config.piper?.modelPath) {
      throw new VoiceProviderError(
        'Piper model path is required',
        'MISSING_MODEL_PATH',
        'piper'
      );
    }

    // TODO: Validate model path exists and is accessible
    // TODO: Validate voice compatibility with model
  }
}

/**
 * Provider information interface
 */
export interface ProviderInfo {
  name: string;
  description: string;
  capabilities: string[];
  requirements: string[];
  latency: string;
  quality: string;
  status: 'production' | 'beta' | 'alpha' | 'stub';
}

/**
 * Voice use case types
 */
export type VoiceUseCase = 
  | 'realtime-conversation'
  | 'high-accuracy-transcription'
  | 'fast-tts'
  | 'multilingual-asr'
  | 'low-latency-tts'
  | 'production-ready';

/**
 * Helper function to create provider factory
 */
export function createVoiceProviderFactory(): VoiceProviderFactory {
  return VoiceProviderFactory.getInstance();
}

/**
 * Convenience function to create a provider directly
 */
export async function createVoiceProvider(
  type: string, 
  config: VoiceProviderConfig
): Promise<VoiceProvider> {
  const factory = VoiceProviderFactory.getInstance();
  return factory.create(type, config);
}

/**
 * Get all available providers with their info
 */
export function getAllProviderInfo(): Array<{ type: string; info: ProviderInfo }> {
  const factory = VoiceProviderFactory.getInstance();
  const providers = factory.getSupportedProviders();
  
  return providers.map(type => ({
    type,
    info: factory.getProviderInfo(type)!
  })).filter(item => item.info !== null);
}

/**
 * Check system requirements for all providers
 */
export function checkSystemRequirements(): Record<string, boolean> {
  const factory = VoiceProviderFactory.getInstance();
  const providers = factory.getSupportedProviders();
  
  const results: Record<string, boolean> = {};
  
  for (const provider of providers) {
    results[provider] = factory.isProviderAvailable(provider);
  }
  
  return results;
}

// Export singleton instance
export const voiceProviderFactory = VoiceProviderFactory.getInstance();