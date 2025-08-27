import {
  VoiceProviderConfig,
  AudioFormat,
  DEFAULT_AUDIO_FORMAT,
  DEFAULT_VOICE_CONFIG,
  VoiceProviderError
} from '../types';

/**
 * Voice configuration manager with environment variable support
 */
export class VoiceConfig {
  private config: VoiceProviderConfig;
  private static instance: VoiceConfig | null = null;

  constructor(config?: Partial<VoiceProviderConfig>) {
    this.config = this.buildConfig(config);
    this.validateConfig();
  }

  /**
   * Get singleton instance with environment-based configuration
   */
  static getInstance(): VoiceConfig {
    if (!VoiceConfig.instance) {
      VoiceConfig.instance = new VoiceConfig();
    }
    return VoiceConfig.instance;
  }

  /**
   * Create new configuration instance
   */
  static create(config: Partial<VoiceProviderConfig>): VoiceConfig {
    return new VoiceConfig(config);
  }

  /**
   * Get the complete configuration
   */
  getConfig(): VoiceProviderConfig {
    return { ...this.config };
  }

  /**
   * Get provider type
   */
  getProvider(): string {
    return this.config.provider;
  }

  /**
   * Get latency target
   */
  getLatencyTarget(): number {
    return this.config.latencyTarget;
  }

  /**
   * Get audio format
   */
  getAudioFormat(): AudioFormat {
    return { ...this.config.audioFormat! };
  }

  /**
   * Check if metrics are enabled
   */
  isMetricsEnabled(): boolean {
    return this.config.enableMetrics ?? true;
  }

  /**
   * Check if VAD is enabled
   */
  isVADEnabled(): boolean {
    return this.config.enableVAD ?? true;
  }

  /**
   * Get OpenAI configuration
   */
  getOpenAIConfig() {
    return this.config.openai ? { ...this.config.openai } : null;
  }

  /**
   * Get Whisper configuration
   */
  getWhisperConfig() {
    return this.config.whisper ? { ...this.config.whisper } : null;
  }

  /**
   * Get Piper configuration
   */
  getPiperConfig() {
    return this.config.piper ? { ...this.config.piper } : null;
  }

  /**
   * Update configuration
   */
  update(updates: Partial<VoiceProviderConfig>): void {
    this.config = { ...this.config, ...updates };
    this.validateConfig();
  }

  /**
   * Update provider-specific configuration
   */
  updateProviderConfig(provider: string, config: any): void {
    switch (provider.toLowerCase()) {
      case 'openai-realtime':
        this.config.openai = { ...this.config.openai, ...config };
        break;
      case 'whisper':
        this.config.whisper = { ...this.config.whisper, ...config };
        break;
      case 'piper':
        this.config.piper = { ...this.config.piper, ...config };
        break;
      default:
        throw new VoiceProviderError(
          `Unknown provider: ${provider}`,
          'UNKNOWN_PROVIDER',
          'config'
        );
    }
    this.validateConfig();
  }

  /**
   * Reset to default configuration
   */
  reset(): void {
    this.config = this.buildConfig();
    this.validateConfig();
  }

  /**
   * Export configuration to JSON
   */
  toJSON(): string {
    // Remove sensitive information before serializing
    const safeConfig = { ...this.config };
    if (safeConfig.openai?.apiKey) {
      safeConfig.openai.apiKey = `${safeConfig.openai.apiKey.substring(0, 8)}...`;
    }
    return JSON.stringify(safeConfig, null, 2);
  }

  /**
   * Load configuration from JSON
   */
  static fromJSON(json: string): VoiceConfig {
    try {
      const config = JSON.parse(json);
      return new VoiceConfig(config);
    } catch (error) {
      throw new VoiceProviderError(
        'Failed to parse configuration JSON',
        'INVALID_JSON',
        'config',
        error instanceof Error ? error : undefined
      );
    }
  }

  /**
   * Build configuration from partial config and environment variables
   */
  private buildConfig(partial?: Partial<VoiceProviderConfig>): VoiceProviderConfig {
    // Start with default configuration
    const config: VoiceProviderConfig = {
      ...DEFAULT_VOICE_CONFIG,
      provider: 'openai-realtime',
      latencyTarget: 500,
      audioFormat: DEFAULT_AUDIO_FORMAT,
      ...partial
    };

    // Load from environment variables
    const envProvider = this.getEnvString('VOICE_PROVIDER', config.provider);
    if (envProvider === 'openai-realtime' || envProvider === 'whisper' || envProvider === 'piper') {
      config.provider = envProvider;
    }
    config.latencyTarget = this.getEnvNumber('VOICE_LATENCY_TARGET', config.latencyTarget);
    config.enableMetrics = this.getEnvBoolean('VOICE_ENABLE_METRICS', config.enableMetrics);
    config.enableVAD = this.getEnvBoolean('VOICE_ENABLE_VAD', config.enableVAD);

    // OpenAI configuration from environment
    if (config.provider === 'openai-realtime' || this.getEnvString('OPENAI_API_KEY')) {
      config.openai = {
        apiKey: this.getEnvString('OPENAI_API_KEY', config.openai?.apiKey || ''),
        model: this.getEnvString('OPENAI_VOICE_MODEL', config.openai?.model || 'gpt-4o-realtime-preview-2024-10-01'),
        voice: this.getEnvString('OPENAI_VOICE', config.openai?.voice) as any,
        temperature: this.getEnvNumber('OPENAI_TEMPERATURE', config.openai?.temperature),
        maxTokens: this.getEnvNumber('OPENAI_MAX_TOKENS', config.openai?.maxTokens),
        instructions: this.getEnvString('OPENAI_INSTRUCTIONS', config.openai?.instructions),
        ...config.openai
      };
    }

    // Whisper configuration from environment
    if (config.provider === 'whisper' || this.getEnvString('WHISPER_MODEL_PATH')) {
      config.whisper = {
        modelPath: this.getEnvString('WHISPER_MODEL_PATH', config.whisper?.modelPath || ''),
        language: this.getEnvString('WHISPER_LANGUAGE', config.whisper?.language),
        temperature: this.getEnvNumber('WHISPER_TEMPERATURE', config.whisper?.temperature),
        initialPrompt: this.getEnvString('WHISPER_INITIAL_PROMPT', config.whisper?.initialPrompt),
        ...config.whisper
      };
    }

    // Piper configuration from environment
    if (config.provider === 'piper' || this.getEnvString('PIPER_MODEL_PATH')) {
      config.piper = {
        modelPath: this.getEnvString('PIPER_MODEL_PATH', config.piper?.modelPath || ''),
        voice: this.getEnvString('PIPER_VOICE', config.piper?.voice),
        speakingRate: this.getEnvNumber('PIPER_SPEAKING_RATE', config.piper?.speakingRate),
        ...config.piper
      };
    }

    return config;
  }

  /**
   * Validate the complete configuration
   */
  private validateConfig(): void {
    if (!this.config.provider) {
      throw new VoiceProviderError(
        'Provider is required',
        'MISSING_PROVIDER',
        'config'
      );
    }

    if (this.config.latencyTarget <= 0) {
      throw new VoiceProviderError(
        'Latency target must be positive',
        'INVALID_LATENCY_TARGET',
        'config'
      );
    }

    // Validate provider-specific configuration
    switch (this.config.provider) {
      case 'openai-realtime':
        this.validateOpenAIConfig();
        break;
      case 'whisper':
        this.validateWhisperConfig();
        break;
      case 'piper':
        this.validatePiperConfig();
        break;
    }

    // Validate audio format
    if (this.config.audioFormat) {
      this.validateAudioFormat(this.config.audioFormat);
    }
  }

  private validateOpenAIConfig(): void {
    if (!this.config.openai?.apiKey) {
      throw new VoiceProviderError(
        'OpenAI API key is required',
        'MISSING_API_KEY',
        'config'
      );
    }

    if (this.config.openai.temperature !== undefined) {
      if (this.config.openai.temperature < 0 || this.config.openai.temperature > 2) {
        throw new VoiceProviderError(
          'OpenAI temperature must be between 0 and 2',
          'INVALID_TEMPERATURE',
          'config'
        );
      }
    }
  }

  private validateWhisperConfig(): void {
    if (!this.config.whisper?.modelPath) {
      throw new VoiceProviderError(
        'Whisper model path is required',
        'MISSING_MODEL_PATH',
        'config'
      );
    }
  }

  private validatePiperConfig(): void {
    if (!this.config.piper?.modelPath) {
      throw new VoiceProviderError(
        'Piper model path is required',
        'MISSING_MODEL_PATH',
        'config'
      );
    }
  }

  private validateAudioFormat(format: AudioFormat): void {
    if (format.sampleRate <= 0) {
      throw new VoiceProviderError(
        'Sample rate must be positive',
        'INVALID_SAMPLE_RATE',
        'config'
      );
    }

    if (format.channels <= 0) {
      throw new VoiceProviderError(
        'Channel count must be positive',
        'INVALID_CHANNELS',
        'config'
      );
    }

    if (![16, 24, 32].includes(format.bitDepth)) {
      throw new VoiceProviderError(
        'Bit depth must be 16, 24, or 32',
        'INVALID_BIT_DEPTH',
        'config'
      );
    }

    const validEncodings = ['pcm', 'mp3', 'opus', 'wav'];
    if (!validEncodings.includes(format.encoding)) {
      throw new VoiceProviderError(
        `Invalid encoding: ${format.encoding}. Valid encodings: ${validEncodings.join(', ')}`,
        'INVALID_ENCODING',
        'config'
      );
    }
  }

  /**
   * Get string from environment variable with fallback
   */
  private getEnvString(key: string, fallback?: string): string {
    const value = process.env[key];
    return value !== undefined ? value : (fallback || '');
  }

  /**
   * Get number from environment variable with fallback
   */
  private getEnvNumber(key: string, fallback?: number): number {
    const value = process.env[key];
    if (value !== undefined) {
      const parsed = parseFloat(value);
      if (!isNaN(parsed)) {
        return parsed;
      }
    }
    return fallback || 0;
  }

  /**
   * Get boolean from environment variable with fallback
   */
  private getEnvBoolean(key: string, fallback?: boolean): boolean {
    const value = process.env[key];
    if (value !== undefined) {
      return value.toLowerCase() === 'true';
    }
    return fallback || false;
  }
}

/**
 * Configuration builder for fluent interface
 */
export class VoiceConfigBuilder {
  private config: Partial<VoiceProviderConfig> = {};

  provider(provider: string): VoiceConfigBuilder {
    this.config.provider = provider as any;
    return this;
  }

  latencyTarget(ms: number): VoiceConfigBuilder {
    this.config.latencyTarget = ms;
    return this;
  }

  audioFormat(format: AudioFormat): VoiceConfigBuilder {
    this.config.audioFormat = format;
    return this;
  }

  enableMetrics(enabled: boolean = true): VoiceConfigBuilder {
    this.config.enableMetrics = enabled;
    return this;
  }

  enableVAD(enabled: boolean = true): VoiceConfigBuilder {
    this.config.enableVAD = enabled;
    return this;
  }

  openai(config: Partial<NonNullable<VoiceProviderConfig['openai']>>): VoiceConfigBuilder {
    this.config.openai = { ...this.config.openai, ...config };
    return this;
  }

  whisper(config: Partial<NonNullable<VoiceProviderConfig['whisper']>>): VoiceConfigBuilder {
    this.config.whisper = { ...this.config.whisper, ...config };
    return this;
  }

  piper(config: Partial<NonNullable<VoiceProviderConfig['piper']>>): VoiceConfigBuilder {
    this.config.piper = { ...this.config.piper, ...config };
    return this;
  }

  build(): VoiceConfig {
    return new VoiceConfig(this.config);
  }
}

/**
 * Create a new configuration builder
 */
export function createVoiceConfigBuilder(): VoiceConfigBuilder {
  return new VoiceConfigBuilder();
}

/**
 * Environment variable configuration loader
 */
export class EnvironmentConfigLoader {
  /**
   * Load configuration from environment variables
   */
  static load(): VoiceConfig {
    return VoiceConfig.getInstance();
  }

  /**
   * Get all relevant environment variables
   */
  static getEnvironmentVariables(): Record<string, string | undefined> {
    return {
      // General
      VOICE_PROVIDER: process.env.VOICE_PROVIDER,
      VOICE_LATENCY_TARGET: process.env.VOICE_LATENCY_TARGET,
      VOICE_ENABLE_METRICS: process.env.VOICE_ENABLE_METRICS,
      VOICE_ENABLE_VAD: process.env.VOICE_ENABLE_VAD,

      // OpenAI
      OPENAI_API_KEY: process.env.OPENAI_API_KEY,
      OPENAI_VOICE_MODEL: process.env.OPENAI_VOICE_MODEL,
      OPENAI_VOICE: process.env.OPENAI_VOICE,
      OPENAI_TEMPERATURE: process.env.OPENAI_TEMPERATURE,
      OPENAI_MAX_TOKENS: process.env.OPENAI_MAX_TOKENS,
      OPENAI_INSTRUCTIONS: process.env.OPENAI_INSTRUCTIONS,

      // Whisper
      WHISPER_MODEL_PATH: process.env.WHISPER_MODEL_PATH,
      WHISPER_LANGUAGE: process.env.WHISPER_LANGUAGE,
      WHISPER_TEMPERATURE: process.env.WHISPER_TEMPERATURE,
      WHISPER_INITIAL_PROMPT: process.env.WHISPER_INITIAL_PROMPT,

      // Piper
      PIPER_MODEL_PATH: process.env.PIPER_MODEL_PATH,
      PIPER_VOICE: process.env.PIPER_VOICE,
      PIPER_SPEAKING_RATE: process.env.PIPER_SPEAKING_RATE
    };
  }

  /**
   * Check if minimum required environment variables are set
   */
  static checkRequiredEnvironmentVariables(): { valid: boolean; missing: string[] } {
    const missing: string[] = [];
    
    const provider = process.env.VOICE_PROVIDER || 'openai-realtime';
    
    switch (provider) {
      case 'openai-realtime':
        if (!process.env.OPENAI_API_KEY) {
          missing.push('OPENAI_API_KEY');
        }
        break;
      
      case 'whisper':
        if (!process.env.WHISPER_MODEL_PATH) {
          missing.push('WHISPER_MODEL_PATH');
        }
        break;
      
      case 'piper':
        if (!process.env.PIPER_MODEL_PATH) {
          missing.push('PIPER_MODEL_PATH');
        }
        break;
    }

    return {
      valid: missing.length === 0,
      missing
    };
  }
}