/**
 * @alice/voice-adapter
 * Main entry point for the voice adapter module
 */

// Core types and interfaces
export * from './types';

// Adapter base classes and utilities
export * from './adapters';

// Voice providers
export { OpenAIRealtimeProvider } from './providers/OpenAIRealtimeProvider';
export { WhisperStubProvider, isWhisperAvailable, getSupportedWhisperModels, getSupportedWhisperLanguages, createWhisperProvider } from './providers/WhisperStubProvider';
export { PiperStubProvider, isPiperAvailable, getPiperVoicesByLanguage, getPiperQualityLevels, validatePiperConfig, createPiperProvider } from './providers/PiperStubProvider';
export {
  VoiceProviderFactory,
  ProviderInfo,
  VoiceUseCase,
  createVoiceProviderFactory,
  createVoiceProvider,
  getAllProviderInfo,
  checkSystemRequirements,
  voiceProviderFactory
} from './providers/VoiceProviderFactory';

// Configuration
export {
  VoiceConfig,
  VoiceConfigBuilder,
  createVoiceConfigBuilder,
  EnvironmentConfigLoader
} from './config/VoiceConfig';

// Metrics and performance monitoring
export {
  LatencyTracker,
  LatencyStats,
  PerformanceSummary,
  createLatencyTracker,
  LatencyMonitor
} from './metrics/LatencyTracker';
export {
  MetricsCollector,
  DetailedMetricsReport,
  MetricsSummary,
  createMetricsCollector,
  MetricsMonitor
} from './metrics/MetricsCollector';

// Audio utilities
export {
  AudioUtils,
  audioUtils,
  createAudioChunk,
  isAudioFormatSupported,
  getOptimalAudioFormat
} from './utils/AudioUtils';

// Voice Activity Detection
export {
  VAD,
  AdvancedVAD,
  WebRTCVAD,
  VADFactory,
  VADUtils,
  createVAD,
  createAdvancedVAD,
  createWebRTCVAD
} from './utils/VAD';

// Convenience exports for common use cases
import { VoiceConfig } from './config/VoiceConfig';
import { VoiceProviderFactory } from './providers/VoiceProviderFactory';
import { MetricsCollector } from './metrics/MetricsCollector';
import { VAD } from './utils/VAD';
import { AudioUtils } from './utils/AudioUtils';
import {
  VoiceProvider,
  VoiceProviderConfig,
  AudioChunk,
  AudioFormat,
  DEFAULT_AUDIO_FORMAT,
  DEFAULT_VOICE_CONFIG
} from './types';

/**
 * Main Voice Adapter class for easy setup and usage
 */
export class VoiceAdapter {
  private config: VoiceConfig;
  private provider: VoiceProvider | null = null;
  private metricsCollector: MetricsCollector | null = null;
  private vadInstance: VAD | null = null;
  private audioUtils: AudioUtils;
  private isInitialized: boolean = false;

  constructor(config?: Partial<VoiceProviderConfig>) {
    this.config = config ? VoiceConfig.create(config) : VoiceConfig.getInstance();
    this.audioUtils = AudioUtils.getInstance();
  }

  /**
   * Initialize the voice adapter with the configured provider
   */
  async initialize(): Promise<void> {
    try {
      // Create provider
      const factory = VoiceProviderFactory.getInstance();
      this.provider = await factory.create(this.config.getProvider(), this.config.getConfig());

      // Initialize metrics collector if enabled
      if (this.config.isMetricsEnabled()) {
        this.metricsCollector = new MetricsCollector(this.config.getLatencyTarget());
        this.setupMetricsIntegration();
      }

      // Initialize VAD if enabled
      if (this.config.isVADEnabled()) {
        this.vadInstance = new VAD({
          sampleRate: this.config.getAudioFormat().sampleRate,
          threshold: 0.3
        });
        this.vadInstance.initialize();
        this.setupVADIntegration();
      }

      // Connect to the provider
      await this.provider.connect();

      this.isInitialized = true;
      console.log(`[VoiceAdapter] Initialized with provider: ${this.config.getProvider()}`);

    } catch (error) {
      console.error('[VoiceAdapter] Initialization failed:', error);
      throw error;
    }
  }

  /**
   * Start a voice session
   */
  async startSession(sessionId?: string): Promise<void> {
    if (!this.isInitialized || !this.provider) {
      throw new Error('Voice adapter not initialized');
    }

    const id = sessionId || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    if (this.metricsCollector) {
      this.metricsCollector.startSession(id);
    }

    await this.provider.startSession();
    console.log(`[VoiceAdapter] Started voice session: ${id}`);
  }

  /**
   * End current voice session
   */
  async endSession(): Promise<void> {
    if (!this.provider) {
      throw new Error('Voice adapter not initialized');
    }

    await this.provider.endSession();

    if (this.metricsCollector) {
      this.metricsCollector.endSession();
    }

    console.log('[VoiceAdapter] Ended voice session');
  }

  /**
   * Send audio input
   */
  async sendAudio(audio: Buffer | AudioChunk): Promise<void> {
    if (!this.provider) {
      throw new Error('Voice adapter not initialized');
    }

    let audioChunk: AudioChunk;

    if (Buffer.isBuffer(audio)) {
      audioChunk = {
        data: audio,
        format: this.config.getAudioFormat(),
        timestamp: Date.now(),
        duration: this.audioUtils.getDuration({
          data: audio,
          format: this.config.getAudioFormat()
        } as AudioChunk)
      };
    } else {
      audioChunk = audio;
    }

    // Process through VAD if enabled
    if (this.vadInstance) {
      const vadResult = this.vadInstance.processAudio(audioChunk);
      
      // Only send audio if voice is active or VAD is not confident
      if (!vadResult.isVoiceActive && vadResult.confidence > 0.7) {
        return; // Skip silent audio
      }
    }

    // Record metrics
    if (this.metricsCollector) {
      this.metricsCollector.recordAudioInput(audioChunk);
    }

    await this.provider.sendAudio(audioChunk);
  }

  /**
   * Send text input
   */
  async sendText(text: string): Promise<void> {
    if (!this.provider) {
      throw new Error('Voice adapter not initialized');
    }

    await this.provider.sendText(text);
  }

  /**
   * Get current provider
   */
  getProvider(): VoiceProvider | null {
    return this.provider;
  }

  /**
   * Get metrics collector
   */
  getMetricsCollector(): MetricsCollector | null {
    return this.metricsCollector;
  }

  /**
   * Get VAD instance
   */
  getVAD(): VAD | null {
    return this.vadInstance;
  }

  /**
   * Get audio utilities
   */
  getAudioUtils(): AudioUtils {
    return this.audioUtils;
  }

  /**
   * Get configuration
   */
  getConfig(): VoiceConfig {
    return this.config;
  }

  /**
   * Update configuration
   */
  updateConfig(updates: Partial<VoiceProviderConfig>): void {
    this.config.update(updates);
    
    if (this.provider) {
      this.provider.updateConfig(updates);
    }
  }

  /**
   * Check if adapter is ready
   */
  isReady(): boolean {
    return this.isInitialized && this.provider !== null && this.provider.getState() === 'connected';
  }

  /**
   * Get current session state
   */
  getState(): string {
    return this.provider?.getState() || 'disconnected';
  }

  /**
   * Disconnect and cleanup
   */
  async disconnect(): Promise<void> {
    if (this.provider) {
      await this.provider.disconnect();
    }

    if (this.metricsCollector) {
      this.metricsCollector.endSession();
    }

    if (this.vadInstance) {
      this.vadInstance.reset();
    }

    this.isInitialized = false;
    console.log('[VoiceAdapter] Disconnected and cleaned up');
  }

  /**
   * Setup metrics integration with provider
   */
  private setupMetricsIntegration(): void {
    if (!this.provider || !this.metricsCollector) return;

    this.provider.on('transcript', (result) => {
      this.metricsCollector!.recordTranscript(result);
    });

    this.provider.on('tts_result', (result) => {
      this.metricsCollector!.recordTTSSynthesis(result);
    });

    this.provider.on('audio_output', (chunk) => {
      this.metricsCollector!.recordAudioOutput(chunk);
    });

    this.provider.on('error', (error) => {
      this.metricsCollector!.recordError(error, this.config.getProvider());
    });

    this.provider.on('latency_update', (latency, type) => {
      this.metricsCollector!.recordLatency(type, latency);
    });
  }

  /**
   * Setup VAD integration with provider
   */
  private setupVADIntegration(): void {
    if (!this.vadInstance) return;

    this.vadInstance.on('voice_start', (result) => {
      console.log('[VoiceAdapter] Voice activity started');
    });

    this.vadInstance.on('voice_end', (result) => {
      console.log('[VoiceAdapter] Voice activity ended');
    });

    if (this.metricsCollector) {
      this.vadInstance.on('vad_result', (result) => {
        this.metricsCollector!.recordVADEvent(result);
      });
    }
  }
}

/**
 * Create a pre-configured voice adapter for common use cases
 */
export function createVoiceAdapter(config?: Partial<VoiceProviderConfig>): VoiceAdapter {
  return new VoiceAdapter(config);
}

/**
 * Create a voice adapter for OpenAI Realtime API
 */
export function createOpenAIVoiceAdapter(apiKey: string, options?: {
  model?: string;
  voice?: string;
  latencyTarget?: number;
}): VoiceAdapter {
  const config: Partial<VoiceProviderConfig> = {
    provider: 'openai-realtime',
    latencyTarget: options?.latencyTarget || 500,
    openai: {
      apiKey,
      model: options?.model || 'gpt-4o-realtime-preview-2024-10-01',
      voice: options?.voice as any || 'alloy'
    }
  };

  return new VoiceAdapter(config);
}

/**
 * Create a voice adapter for Whisper ASR
 */
export function createWhisperVoiceAdapter(modelPath: string, options?: {
  language?: string;
  latencyTarget?: number;
}): VoiceAdapter {
  const config: Partial<VoiceProviderConfig> = {
    provider: 'whisper',
    latencyTarget: options?.latencyTarget || 300,
    whisper: {
      modelPath,
      language: options?.language
    }
  };

  return new VoiceAdapter(config);
}

/**
 * Create a voice adapter for Piper TTS
 */
export function createPiperVoiceAdapter(modelPath: string, options?: {
  voice?: string;
  latencyTarget?: number;
}): VoiceAdapter {
  const config: Partial<VoiceProviderConfig> = {
    provider: 'piper',
    latencyTarget: options?.latencyTarget || 200,
    piper: {
      modelPath,
      voice: options?.voice
    }
  };

  return new VoiceAdapter(config);
}

/**
 * Utility function to quickly test voice adapter setup
 */
export async function testVoiceAdapter(
  adapter: VoiceAdapter,
  testAudio?: Buffer
): Promise<{
  success: boolean;
  details: {
    initialization: boolean;
    connection: boolean;
    audioProcessing: boolean;
    metrics: boolean;
    vad: boolean;
  };
  errors: string[];
}> {
  const results = {
    success: false,
    details: {
      initialization: false,
      connection: false,
      audioProcessing: false,
      metrics: false,
      vad: false
    },
    errors: [] as string[]
  };

  try {
    // Test initialization
    await adapter.initialize();
    results.details.initialization = true;

    // Test connection
    results.details.connection = adapter.isReady();
    if (!results.details.connection) {
      results.errors.push('Adapter not ready after initialization');
    }

    // Test session management
    await adapter.startSession('test_session');

    // Test metrics
    const metricsCollector = adapter.getMetricsCollector();
    results.details.metrics = metricsCollector !== null;

    // Test VAD
    const vad = adapter.getVAD();
    results.details.vad = vad !== null;

    // Test audio processing if test audio provided
    if (testAudio) {
      try {
        await adapter.sendAudio(testAudio);
        results.details.audioProcessing = true;
      } catch (error) {
        results.errors.push(`Audio processing failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    } else {
      results.details.audioProcessing = true; // Skip test if no audio provided
    }

    await adapter.endSession();

    // Overall success
    results.success = Object.values(results.details).every(detail => detail);

  } catch (error) {
    results.errors.push(`Test failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  } finally {
    try {
      await adapter.disconnect();
    } catch (error) {
      results.errors.push(`Cleanup failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  return results;
}

// Default exports for convenience
export default VoiceAdapter;

// Version information
export const VERSION = '1.0.0';
export const AUTHOR = 'Alice AI System';

console.log(`[@alice/voice-adapter] Module loaded (v${VERSION})`);