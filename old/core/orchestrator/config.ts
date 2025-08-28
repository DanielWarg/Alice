/**
 * Orchestrator Configuration
 * 
 * Central configuration management for Alice's orchestrator.
 * Supports environment variables, config files, and runtime overrides.
 */

import fs from "fs";
import path from "path";

// Default configuration values
const DEFAULT_CONFIG = {
  // Performance settings
  jitterMs: 100,
  asrChunkMs: 200,
  asrStabilizeMs: 250,
  llmMaxNewTokens: 40,
  llmTemperature: 0.2,
  ttsChunkMs: 60,
  bargeInFadeMs: 100,
  
  // Privacy settings
  safeSummaryMaxLen: 300,
  allowCloud: false,
  cloudTtfaDegradeMs: 600,
  
  // Feature flags
  allowVision: true,
  allowPatternLLM: false,
  
  // Rate limiting
  maxTurnsPerMinute: 60,
  maxToolCallsPerTurn: 5,
  
  // Language settings
  defaultLanguage: "sv-SE",
  supportedLanguages: ["sv-SE", "en-US"],
  
  // Logging
  logLevel: "info",
  enableMetrics: true,
  metricsRotationHours: 24,
  
  // Security
  enableRateLimiting: true,
  enableCORS: true,
  maxRequestSize: "10mb",
  
  // External services
  homeAssistant: {
    enabled: false,
    wsUrl: "ws://localhost:8123/api/websocket",
    token: "",
    retryInterval: 5000,
    maxRetries: 3
  },
  
  // Camera/vision settings
  vision: {
    enabled: true,
    maxImageSize: 1024 * 1024, // 1MB
    supportedFormats: ["jpeg", "png", "webp"],
    defaultQuality: 80
  }
};

// Configuration interface
export interface OrchestratorConfig {
  // Performance settings
  jitterMs: number;
  asrChunkMs: number;
  asrStabilizeMs: number;
  llmMaxNewTokens: number;
  llmTemperature: number;
  ttsChunkMs: number;
  bargeInFadeMs: number;
  
  // Privacy settings
  safeSummaryMaxLen: number;
  allowCloud: boolean;
  cloudTtfaDegradeMs: number;
  
  // Feature flags
  allowVision: boolean;
  allowPatternLLM: boolean;
  
  // Rate limiting
  maxTurnsPerMinute: number;
  maxToolCallsPerTurn: number;
  
  // Language settings
  defaultLanguage: string;
  supportedLanguages: string[];
  
  // Logging
  logLevel: string;
  enableMetrics: boolean;
  metricsRotationHours: number;
  
  // Security
  enableRateLimiting: boolean;
  enableCORS: boolean;
  maxRequestSize: string;
  
  // External services
  homeAssistant: {
    enabled: boolean;
    wsUrl: string;
    token: string;
    retryInterval: number;
    maxRetries: number;
  };
  
  // Camera/vision settings
  vision: {
    enabled: boolean;
    maxImageSize: number;
    supportedFormats: string[];
    defaultQuality: number;
  };
}

class ConfigManager {
  private config: OrchestratorConfig;
  private configFile: string;
  private envPrefix: string = "ALICE_";

  constructor(configFile?: string) {
    this.configFile = configFile || "config/orchestrator.ini";
    this.config = this.loadConfiguration();
  }

  /**
   * Load configuration from multiple sources
   */
  private loadConfiguration(): OrchestratorConfig {
    // Start with defaults
    let config = { ...DEFAULT_CONFIG };

    // Load from config file
    config = this.loadFromFile(config);

    // Load from environment variables
    config = this.loadFromEnvironment(config);

    // Load from command line arguments
    config = this.loadFromCommandLine(config);

    return config;
  }

  /**
   * Load configuration from file
   */
  private loadFromFile(config: OrchestratorConfig): OrchestratorConfig {
    try {
      if (fs.existsSync(this.configFile)) {
        const fileContent = fs.readFileSync(this.configFile, "utf8");
        const fileConfig = this.parseConfigFile(fileContent);
        
        // Merge file config with defaults
        config = { ...config, ...fileConfig };
        console.log(`📁 Loaded config from: ${this.configFile}`);
      } else {
        console.log(`📁 Config file not found: ${this.configFile}`);
      }
    } catch (error) {
      console.warn(`⚠️ Failed to load config file: ${error}`);
    }

    return config;
  }

  /**
   * Parse INI-style config file
   */
  private parseConfigFile(content: string): Partial<OrchestratorConfig> {
    const config: any = {};
    let currentSection = "";

    const lines = content.split("\n");
    
    for (const line of lines) {
      const trimmed = line.trim();
      
      // Skip empty lines and comments
      if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith(";")) {
        continue;
      }

      // Section header
      if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
        currentSection = trimmed.slice(1, -1);
        continue;
      }

      // Key-value pair
      const [key, value] = trimmed.split("=", 2).map(s => s.trim());
      if (key && value !== undefined) {
        if (currentSection) {
          if (!config[currentSection]) {
            config[currentSection] = {};
          }
          config[currentSection][key] = this.parseValue(value);
        } else {
          config[key] = this.parseValue(value);
        }
      }
    }

    return config;
  }

  /**
   * Parse config value
   */
  private parseValue(value: string): any {
    // Boolean values
    if (value.toLowerCase() === "true") return true;
    if (value.toLowerCase() === "false") return false;
    
    // Numeric values
    if (!isNaN(Number(value))) return Number(value);
    
    // Array values (comma-separated)
    if (value.includes(",")) {
      return value.split(",").map(v => v.trim());
    }
    
    // String values
    return value;
  }

  /**
   * Load configuration from environment variables
   */
  private loadFromEnvironment(config: OrchestratorConfig): OrchestratorConfig {
    const env = process.env;
    
    // Performance settings
    if (env[`${this.envPrefix}JITTER_MS`]) {
      config.jitterMs = Number(env[`${this.envPrefix}JITTER_MS`]);
    }
    if (env[`${this.envPrefix}ASR_CHUNK_MS`]) {
      config.asrChunkMs = Number(env[`${this.envPrefix}ASR_CHUNK_MS`]);
    }
    if (env[`${this.envPrefix}ASR_STABILIZE_MS`]) {
      config.asrStabilizeMs = Number(env[`${this.envPrefix}ASR_STABILIZE_MS`]);
    }
    if (env[`${this.envPrefix}LLM_MAX_NEW_TOKENS`]) {
      config.llmMaxNewTokens = Number(env[`${this.envPrefix}LLM_MAX_NEW_TOKENS`]);
    }
    if (env[`${this.envPrefix}LLM_TEMPERATURE`]) {
      config.llmTemperature = Number(env[`${this.envPrefix}LLM_TEMPERATURE`]);
    }
    if (env[`${this.envPrefix}TTS_CHUNK_MS`]) {
      config.ttsChunkMs = Number(env[`${this.envPrefix}TTS_CHUNK_MS`]);
    }
    if (env[`${this.envPrefix}BARGE_IN_FADE_MS`]) {
      config.bargeInFadeMs = Number(env[`${this.envPrefix}BARGE_IN_FADE_MS`]);
    }

    // Privacy settings
    if (env[`${this.envPrefix}SAFE_SUMMARY_MAXLEN`]) {
      config.safeSummaryMaxLen = Number(env[`${this.envPrefix}SAFE_SUMMARY_MAXLEN`]);
    }
    if (env[`${this.envPrefix}ALLOW_CLOUD`]) {
      config.allowCloud = env[`${this.envPrefix}ALLOW_CLOUD`].toLowerCase() === "true";
    }
    if (env[`${this.envPrefix}CLOUD_TTFA_DEGRADE_MS`]) {
      config.cloudTtfaDegradeMs = Number(env[`${this.envPrefix}CLOUD_TTFA_DEGRADE_MS`]);
    }

    // Feature flags
    if (env[`${this.envPrefix}ALLOW_VISION`]) {
      config.allowVision = env[`${this.envPrefix}ALLOW_VISION`].toLowerCase() === "true";
    }
    if (env[`${this.envPrefix}ALLOW_PATTERN_LLM`]) {
      config.allowPatternLLM = env[`${this.envPrefix}ALLOW_PATTERN_LLM`].toLowerCase() === "true";
    }

    // Home Assistant
    if (env[`${this.envPrefix}HA_WS_URL`]) {
      config.homeAssistant.wsUrl = env[`${this.envPrefix}HA_WS_URL`];
    }
    if (env[`${this.envPrefix}HA_TOKEN`]) {
      config.homeAssistant.token = env[`${this.envPrefix}HA_TOKEN`];
      config.homeAssistant.enabled = true;
    }

    // Language
    if (env[`${this.envPrefix}LANG`]) {
      config.defaultLanguage = env[`${this.envPrefix}LANG`];
    }

    return config;
  }

  /**
   * Load configuration from command line arguments
   */
  private loadFromCommandLine(config: OrchestratorConfig): OrchestratorConfig {
    const args = process.argv.slice(2);
    
    for (let i = 0; i < args.length; i++) {
      const arg = args[i];
      
      if (arg.startsWith("--")) {
        const key = arg.slice(2);
        const value = args[i + 1];
        
        if (value && !value.startsWith("--")) {
          // Handle different value types
          if (key === "allow-cloud") {
            config.allowCloud = value.toLowerCase() === "true";
          } else if (key === "allow-vision") {
            config.allowVision = value.toLowerCase() === "true";
          } else if (key === "log-level") {
            config.logLevel = value;
          } else if (key === "lang") {
            config.defaultLanguage = value;
          }
          
          i++; // Skip next argument
        }
      }
    }

    return config;
  }

  /**
   * Get configuration value
   */
  get<K extends keyof OrchestratorConfig>(key: K): OrchestratorConfig[K] {
    return this.config[key];
  }

  /**
   * Set configuration value
   */
  set<K extends keyof OrchestratorConfig>(key: K, value: OrchestratorConfig[K]): void {
    this.config[key] = value;
  }

  /**
   * Get entire configuration
   */
  getAll(): OrchestratorConfig {
    return { ...this.config };
  }

  /**
   * Save configuration to file
   */
  saveToFile(): void {
    try {
      const configDir = path.dirname(this.configFile);
      if (!fs.existsSync(configDir)) {
        fs.mkdirSync(configDir, { recursive: true });
      }

      const content = this.generateConfigFile();
      fs.writeFileSync(this.configFile, content, "utf8");
      
      console.log(`💾 Configuration saved to: ${this.configFile}`);
    } catch (error) {
      console.error(`❌ Failed to save configuration: ${error}`);
    }
  }

  /**
   * Generate config file content
   */
  private generateConfigFile(): string {
    let content = "# Alice Orchestrator Configuration\n";
    content += "# Generated automatically\n\n";

    // Performance settings
    content += "[performance]\n";
    content += `jitterMs = ${this.config.jitterMs}\n`;
    content += `asrChunkMs = ${this.config.asrChunkMs}\n`;
    content += `asrStabilizeMs = ${this.config.asrStabilizeMs}\n`;
    content += `llmMaxNewTokens = ${this.config.llmMaxNewTokens}\n`;
    content += `llmTemperature = ${this.config.llmTemperature}\n`;
    content += `ttsChunkMs = ${this.config.ttsChunkMs}\n`;
    content += `bargeInFadeMs = ${this.config.bargeInFadeMs}\n\n`;

    // Privacy settings
    content += "[privacy]\n";
    content += `safeSummaryMaxLen = ${this.config.safeSummaryMaxLen}\n`;
    content += `allowCloud = ${this.config.allowCloud}\n`;
    content += `cloudTtfaDegradeMs = ${this.config.cloudTtfaDegradeMs}\n\n`;

    // Feature flags
    content += "[features]\n";
    content += `allowVision = ${this.config.allowVision}\n`;
    content += `allowPatternLLM = ${this.config.allowPatternLLM}\n\n`;

    // Language settings
    content += "[language]\n";
    content += `defaultLanguage = ${this.config.defaultLanguage}\n`;
    content += `supportedLanguages = ${this.config.supportedLanguages.join(", ")}\n\n`;

    return content;
  }

  /**
   * Validate configuration
   */
  validate(): { valid: boolean; errors: string[]; warnings: string[] } {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Check required values
    if (this.config.jitterMs < 0) {
      errors.push("jitterMs must be non-negative");
    }
    if (this.config.asrChunkMs < 50) {
      warnings.push("asrChunkMs < 50ms may cause performance issues");
    }
    if (this.config.llmTemperature < 0 || this.config.llmTemperature > 2) {
      errors.push("llmTemperature must be between 0 and 2");
    }

    // Check Home Assistant configuration
    if (this.config.homeAssistant.enabled && !this.config.homeAssistant.token) {
      errors.push("Home Assistant token required when enabled");
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Reload configuration
   */
  reload(): void {
    this.config = this.loadConfiguration();
    console.log("🔄 Configuration reloaded");
  }
}

// Create singleton config manager
export const configManager = new ConfigManager();

// Export configuration getters
export const getConfig = <K extends keyof OrchestratorConfig>(key: K) => configManager.get(key);
export const setConfig = <K extends keyof OrchestratorConfig>(key: K, value: OrchestratorConfig[K]) => configManager.set(key, value);
export const getAllConfig = () => configManager.getAll();

// Export default configuration
export const defaultConfig = DEFAULT_CONFIG;

export default configManager;
