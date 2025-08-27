/**
 * @alice/voice-adapter - Main Module Entry Point
 * 
 * Modular voice interface supporting OpenAI Realtime API and future local providers
 */

// Core types
export * from './types/index.js';

// Adapter interfaces
export * from './adapters/index.js';

// Providers
export { OpenAIRealtimeProvider } from './providers/OpenAIRealtimeProvider.js';
export { WhisperStubProvider } from './providers/WhisperStubProvider.js';
export { PiperStubProvider } from './providers/PiperStubProvider.js';
export { VoiceProviderFactory } from './providers/VoiceProviderFactory.js';
export type { ProviderFactoryConfig } from './providers/VoiceProviderFactory.js';

// Utilities
export { SimpleVAD } from './utils/VAD.js';
export { AudioUtils } from './utils/AudioUtils.js';

// Metrics
export { LatencyTracker } from './metrics/LatencyTracker.js';
export { MetricsCollector } from './metrics/MetricsCollector.js';

// Configuration
export { VoiceConfigManager, getVoiceConfig, getOpenAIConfig } from './config/VoiceConfig.js';

// Main factory function - primary API
export function createVoiceAdapter(): import('./types/index.js').VoiceProvider {
  return VoiceProviderFactory.createFromEnvironment();
}

// Convenience initialization function
export async function initVoiceAdapter(config?: {
  provider?: string;
  openaiApiKey?: string;
  metricsEndpoint?: string;
}): Promise<import('./types/index.js').VoiceProvider> {
  // Set environment variables if provided
  if (config?.provider) {
    process.env.VOICE_PROVIDER = config.provider;
  }
  if (config?.openaiApiKey) {
    process.env.OPENAI_API_KEY = config.openaiApiKey;
  }
  if (config?.metricsEndpoint) {
    process.env.METRICS_EXPORT_ENDPOINT = config.metricsEndpoint;
  }
  
  const provider = createVoiceAdapter();
  await provider.initialize();
  
  return provider;
}

// Development utilities
export function getProviderInfo() {
  return VoiceProviderFactory.getAvailableProviders();
}

export function validateEnvironment(): { valid: boolean; errors: string[] } {
  try {
    const configManager = VoiceConfigManager.getInstance();
    configManager.loadFromEnvironment();
    
    const config = {
      voice: configManager.getConfig(),
      openai: configManager.getOpenAIConfig()
    };
    
    const errors = VoiceProviderFactory.validateConfig(config);
    
    return {
      valid: errors.length === 0,
      errors
    };
  } catch (error) {
    return {
      valid: false,
      errors: [error instanceof Error ? error.message : 'Unknown validation error']
    };
  }
}

// Test provider connection
export async function testVoiceConnection(config?: {
  provider?: string;
  openaiApiKey?: string;
}): Promise<{
  success: boolean;
  latency_ms?: number;
  error?: string;
}> {
  try {
    // Set temporary environment if config provided
    const originalProvider = process.env.VOICE_PROVIDER;
    const originalApiKey = process.env.OPENAI_API_KEY;
    
    if (config?.provider) {
      process.env.VOICE_PROVIDER = config.provider;
    }
    if (config?.openaiApiKey) {
      process.env.OPENAI_API_KEY = config.openaiApiKey;
    }
    
    const configManager = VoiceConfigManager.getInstance();
    configManager.loadFromEnvironment();
    
    const factoryConfig = {
      voice: configManager.getConfig(),
      openai: configManager.getOpenAIConfig()
    };
    
    const result = await VoiceProviderFactory.testProvider(factoryConfig);
    
    // Restore original environment
    if (originalProvider !== undefined) {
      process.env.VOICE_PROVIDER = originalProvider;
    }
    if (originalApiKey !== undefined) {
      process.env.OPENAI_API_KEY = originalApiKey;
    }
    
    return result;
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown test error'
    };
  }
}

// Version and metadata
export const version = '1.0.0';
export const name = '@alice/voice-adapter';
export const description = 'Modular voice adapter with OpenAI Realtime and local provider support';