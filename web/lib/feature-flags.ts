/**
 * Feature Flags Configuration
 * Controls release-readiness features with environment overrides
 */

export interface FeatureFlags {
  // Core Voice Features
  voice_enabled: boolean;
  voice_agent_mode: boolean;
  voice_toolcalling: boolean;
  voice_realtime_mode: boolean;
  
  // Advanced Features
  voice_barge_in: boolean;
  voice_wake_word: boolean;
  voice_ambient_mode: boolean;
  voice_streaming_tts: boolean;
  
  // Content & Safety
  content_filtering: boolean;
  consent_required: boolean;
  synthetic_voice_badge: boolean;
  privacy_mode: 'strict' | 'balanced' | 'permissive';
  
  // Development & Debug
  voice_debug_mode: boolean;
  mock_responses: boolean;
  bypass_rate_limits: boolean;
  extended_timeouts: boolean;
  
  // Performance & Reliability
  fallback_enabled: boolean;
  circuit_breaker: boolean;
  metrics_collection: boolean;
  error_reporting: boolean;
}

const DEFAULT_FLAGS: FeatureFlags = {
  // Core Voice Features
  voice_enabled: true,
  voice_agent_mode: true,
  voice_toolcalling: true,
  voice_realtime_mode: false, // Disabled pending performance validation
  
  // Advanced Features
  voice_barge_in: false, // Beta feature
  voice_wake_word: false, // Beta feature
  voice_ambient_mode: false, // Beta feature
  voice_streaming_tts: true,
  
  // Content & Safety
  content_filtering: true,
  consent_required: true,
  synthetic_voice_badge: true,
  privacy_mode: 'balanced',
  
  // Development & Debug
  voice_debug_mode: false,
  mock_responses: false,
  bypass_rate_limits: false,
  extended_timeouts: false,
  
  // Performance & Reliability
  fallback_enabled: true,
  circuit_breaker: true,
  metrics_collection: true,
  error_reporting: true
};

/**
 * Get feature flag value with environment override support
 */
function getEnvFlag(key: string, defaultValue: any): any {
  if (typeof window !== 'undefined') {
    // Client-side: only access NEXT_PUBLIC_ variables
    const envKey = `NEXT_PUBLIC_FEATURE_${key.toUpperCase()}`;
    const envValue = process.env[envKey];
    
    if (envValue !== undefined) {
      if (typeof defaultValue === 'boolean') {
        return envValue === 'true' || envValue === '1' || envValue === 'on';
      }
      if (typeof defaultValue === 'string') {
        return envValue;
      }
    }
  }
  
  return defaultValue;
}

/**
 * Load feature flags with environment overrides
 */
export function loadFeatureFlags(): FeatureFlags {
  const flags: FeatureFlags = {} as FeatureFlags;
  
  // Load each flag with environment override
  for (const [key, defaultValue] of Object.entries(DEFAULT_FLAGS)) {
    flags[key as keyof FeatureFlags] = getEnvFlag(key, defaultValue);
  }
  
  return flags;
}

/**
 * Global feature flags instance
 */
export const FEATURE_FLAGS = loadFeatureFlags();

/**
 * Feature flag checker functions
 */
export const FeatureFlag = {
  // Core Voice Features
  isVoiceEnabled: () => FEATURE_FLAGS.voice_enabled,
  isAgentModeEnabled: () => FEATURE_FLAGS.voice_agent_mode,
  isToolcallingEnabled: () => FEATURE_FLAGS.voice_toolcalling,
  isRealtimeModeEnabled: () => FEATURE_FLAGS.voice_realtime_mode,
  
  // Advanced Features
  isBargeInEnabled: () => FEATURE_FLAGS.voice_barge_in,
  isWakeWordEnabled: () => FEATURE_FLAGS.voice_wake_word,
  isAmbientModeEnabled: () => FEATURE_FLAGS.voice_ambient_mode,
  isStreamingTTSEnabled: () => FEATURE_FLAGS.voice_streaming_tts,
  
  // Content & Safety
  isContentFilteringEnabled: () => FEATURE_FLAGS.content_filtering,
  isConsentRequired: () => FEATURE_FLAGS.consent_required,
  isSyntheticBadgeEnabled: () => FEATURE_FLAGS.synthetic_voice_badge,
  getPrivacyMode: () => FEATURE_FLAGS.privacy_mode,
  
  // Development & Debug
  isDebugModeEnabled: () => FEATURE_FLAGS.voice_debug_mode,
  isMockResponsesEnabled: () => FEATURE_FLAGS.mock_responses,
  isBypassRateLimitsEnabled: () => FEATURE_FLAGS.bypass_rate_limits,
  isExtendedTimeoutsEnabled: () => FEATURE_FLAGS.extended_timeouts,
  
  // Performance & Reliability
  isFallbackEnabled: () => FEATURE_FLAGS.fallback_enabled,
  isCircuitBreakerEnabled: () => FEATURE_FLAGS.circuit_breaker,
  isMetricsCollectionEnabled: () => FEATURE_FLAGS.metrics_collection,
  isErrorReportingEnabled: () => FEATURE_FLAGS.error_reporting,
  
  // Helper for development
  getAllFlags: () => FEATURE_FLAGS,
  
  // Environment detection
  isDevelopment: () => process.env.NODE_ENV === 'development',
  isProduction: () => process.env.NODE_ENV === 'production',
  
  // Safety checks for critical features
  canUseVoice: () => FeatureFlag.isVoiceEnabled() && (
    FeatureFlag.isDevelopment() || 
    FeatureFlag.isConsentRequired() || 
    !FeatureFlag.isVoiceEnabled()
  ),
  
  canUseAgent: () => FeatureFlag.isAgentModeEnabled() && FeatureFlag.canUseVoice(),
  
  canUseTools: () => FeatureFlag.isToolcallingEnabled() && FeatureFlag.canUseAgent()
};

/**
 * Runtime feature flag override (for admin/testing)
 */
export function overrideFeatureFlag(key: keyof FeatureFlags, value: any) {
  if (FeatureFlag.isDevelopment()) {
    (FEATURE_FLAGS as any)[key] = value;
    console.log(`🚩 Feature flag overridden: ${key} = ${value}`);
  } else {
    console.warn('🚩 Feature flag override denied in production');
  }
}

/**
 * Export current flags for debugging
 */
export function exportFeatureFlags(): Record<string, any> {
  return {
    ...FEATURE_FLAGS,
    environment: process.env.NODE_ENV,
    timestamp: new Date().toISOString(),
    overrides_available: FeatureFlag.isDevelopment()
  };
}