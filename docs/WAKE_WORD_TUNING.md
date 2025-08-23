# Alice Wake-Word Parameter Tuning Guide

Comprehensive guide for configuring and tuning Alice's Swedish wake-word detection system for optimal performance.

## Overview

Alice's wake-word detection system is designed to recognize "Alice" and variants in Swedish with high accuracy while minimizing false positives. The system uses a hybrid approach combining browser Speech Recognition API with fuzzy matching algorithms optimized for Swedish pronunciation patterns.

## Configuration Parameters

### Core Wake-Word Settings

```javascript
const wakeWordConfig = {
  // Primary wake-words (order by priority)
  wakeWords: ['alice', 'allis', 'alis', 'alicia'], // Default Swedish variants
  
  // Detection sensitivity (0.0 - 1.0)
  sensitivity: 0.7,  // Default: 0.7, Lower = more sensitive, Higher = more strict
  
  // Cooldown between detections (milliseconds)
  cooldownMs: 2000,  // Default: 2000ms, Prevents rapid-fire detections
  
  // Maximum recording time for each attempt
  maxRecordingMs: 3000,  // Default: 3000ms
  
  // Language model
  language: 'sv-SE',  // Swedish (Sweden)
  
  // Continuous listening mode
  continuous: true,   // Default: true, Auto-restart after detection
}
```

### Advanced Tuning Parameters

```javascript
const advancedConfig = {
  // Speech Recognition optimizations
  recognition: {
    interimResults: true,           // Enable interim results for faster detection
    maxAlternatives: 3,             // Number of recognition alternatives to consider
    serviceURI: 'wss://...',        // Custom recognition service (Chrome)
  },
  
  // Matching algorithm settings
  matching: {
    exactMatchThreshold: 0.5,       // Confidence threshold for exact matches (lower = easier)
    fuzzyMatchThreshold: 0.7,       // Confidence threshold for fuzzy matches
    partialMatchThreshold: 1.2,     // Confidence threshold for partial matches (higher = harder)
    fuzzyMatchSimilarity: 0.75,     // Levenshtein similarity threshold (0-1)
    maxWordLengthDiff: 2,           // Max character difference for partial matching
  },
  
  // Audio processing
  audio: {
    noiseGateLevel: 0.02,           // Minimum audio level to process
    ambientNoiseAdaptation: true,   // Adapt to background noise levels
    voiceActivityMinDuration: 200,  // Minimum voice activity duration (ms)
  }
}
```

## Tuning Guidelines

### 1. Sensitivity Tuning

**High Sensitivity (0.3-0.5)** - Use when:
- Quiet environments with minimal background noise
- Users with clear pronunciation
- Need maximum responsiveness
- Risk: Higher false positive rate

**Medium Sensitivity (0.6-0.8)** - Use when (Recommended):
- Normal household environments
- Mixed acoustic conditions  
- Balance between accuracy and responsiveness
- Default production setting

**Low Sensitivity (0.9-1.0)** - Use when:
- Noisy environments (TV, music, conversations)
- Users with accented or unclear speech
- Need minimum false positives
- Risk: May miss legitimate wake-words

### 2. Swedish Pronunciation Optimization

```javascript
// Swedish-specific wake-word variants prioritized by common pronunciation
const swedishWakeWords = {
  // Standard pronunciation
  primary: ['alice'],
  
  // Common Swedish mispronunciations  
  variants: ['allis', 'alis'],
  
  // International variants (lower priority)
  international: ['alicia', 'alex'],
  
  // Context-aware phrases
  contextual: ['hej alice', 'hallå alice'],
}
```

**Pronunciation Mapping:**
- "Alice" → Standard Swedish: "Ah-li-se" 
- Regional variants: "A-lis", "A-li-sa"
- Common mishears: "Ellis", "Allis", "Alis"

### 3. Acoustic Environment Tuning

#### Quiet Environment (< 40dB background)
```javascript
const quietEnvironmentConfig = {
  sensitivity: 0.5,        // More sensitive
  cooldownMs: 1500,        // Shorter cooldown
  fuzzyMatchSimilarity: 0.8, // Stricter matching
}
```

#### Normal Environment (40-60dB background)
```javascript
const normalEnvironmentConfig = {
  sensitivity: 0.7,        // Default sensitivity  
  cooldownMs: 2000,        // Standard cooldown
  fuzzyMatchSimilarity: 0.75, // Balanced matching
}
```

#### Noisy Environment (> 60dB background)
```javascript
const noisyEnvironmentConfig = {
  sensitivity: 0.9,        // Less sensitive
  cooldownMs: 3000,        // Longer cooldown
  fuzzyMatchSimilarity: 0.7, // More permissive matching
  ambientNoiseAdaptation: true, // Enable noise adaptation
}
```

## Performance Tuning

### Latency Optimization

**Target Metrics:**
- Wake-word detection: < 500ms
- Ready-to-listen: < 200ms additional
- End-to-end (wake → response): < 2000ms

**Optimization strategies:**
1. Enable interim results for faster detection
2. Use local processing when possible  
3. Optimize audio buffer sizes
4. Reduce speech recognition alternatives

```javascript
// Low-latency configuration
const lowLatencyConfig = {
  recognition: {
    interimResults: true,
    maxAlternatives: 1,        // Reduce alternatives for speed
  },
  audio: {
    bufferSize: 1024,          // Smaller buffer for faster processing
    sampleRate: 16000,         // Lower sample rate if acceptable
  }
}
```

### Resource Usage Optimization

**CPU Usage Target:** < 15% average
**Memory Usage Target:** < 50MB growth over 30 minutes

```javascript
// Resource-optimized configuration
const resourceOptimizedConfig = {
  cooldownMs: 3000,            // Longer cooldown reduces processing
  maxRecordingMs: 2000,        // Shorter max recording time
  recognition: {
    maxAlternatives: 1,        // Single alternative
  },
  continuous: false,           // Manual restart mode for lower resource usage
}
```

## Swedish Dialect Support

### Regional Accent Configurations

#### Stockholm (Standard Swedish)
```javascript
const stockholmConfig = {
  wakeWords: ['alice', 'allis'],
  sensitivity: 0.7,
  fuzzyMatchSimilarity: 0.75,
}
```

#### Göteborg (West Swedish)  
```javascript
const göteborgConfig = {
  wakeWords: ['alice', 'alis', 'allis'],
  sensitivity: 0.6,              // More permissive for accent variation
  fuzzyMatchSimilarity: 0.7,     // More tolerant matching
}
```

#### Skåne (Southern Swedish)
```javascript
const skåneConfig = {
  wakeWords: ['alice', 'alis', 'ales'],
  sensitivity: 0.6,
  fuzzyMatchSimilarity: 0.65,    // Most tolerant for distinctive accent
}
```

#### Finland Swedish
```javascript
const finlandSwedishConfig = {
  wakeWords: ['alice', 'alise', 'alis'],
  sensitivity: 0.65,
  fuzzyMatchSimilarity: 0.7,
}
```

## Testing and Validation

### Automated Testing

```bash
# Run wake-word detection tests
npm run test:wake-word

# Performance benchmarking
npm run benchmark:wake-word

# Swedish accent testing
npm run test:swedish-accents
```

### Manual Testing Checklist

See [wake_word_testing_checklist.md](../tests/wake_word_testing_checklist.md) for comprehensive manual testing procedures.

**Critical Test Scenarios:**
1. Standard pronunciation in quiet environment
2. Swedish regional accents
3. Background noise (TV, music, conversation)
4. Distance testing (0.5m, 2m, 4m)
5. False positive prevention
6. Continuous operation stability

### Performance Monitoring

```javascript
// Enable performance monitoring
const monitoring = {
  logDetections: true,
  measureLatency: true,
  trackFalsePositives: true,
  cpuUsageMonitoring: true,
}

// Access performance metrics
const metrics = wakeWordDetector.getPerformanceMetrics();
console.log('Detection rate:', metrics.detectionRate);
console.log('False positive rate:', metrics.falsePositiveRate);
console.log('Average latency:', metrics.averageLatency);
```

## Troubleshooting

### Common Issues and Solutions

#### Low Detection Rate (< 90%)

**Possible causes:**
- Sensitivity too high (increase sensitivity: lower value)
- Fuzzy matching too strict
- Background noise interfering
- Microphone quality issues

**Solutions:**
```javascript
// Increase sensitivity (lower threshold)
wakeWordConfig.sensitivity = 0.5;  // From 0.7

// More permissive fuzzy matching  
wakeWordConfig.fuzzyMatchSimilarity = 0.7;  // From 0.75

// Add more wake-word variants
wakeWordConfig.wakeWords = ['alice', 'allis', 'alis', 'alicia', 'alex'];
```

#### High False Positive Rate (> 2%)

**Possible causes:**
- Sensitivity too low (decrease sensitivity: higher value)
- Too many wake-word variants
- Background audio triggering detection

**Solutions:**
```javascript
// Decrease sensitivity (higher threshold)
wakeWordConfig.sensitivity = 0.8;  // From 0.7

// Stricter fuzzy matching
wakeWordConfig.fuzzyMatchSimilarity = 0.8;  // From 0.75

// Reduce wake-word variants
wakeWordConfig.wakeWords = ['alice'];  // Only primary variant
```

#### High Latency (> 1000ms)

**Possible causes:**
- Network latency to speech recognition service
- CPU resource constraints
- Large audio buffers

**Solutions:**
```javascript
// Enable interim results
wakeWordConfig.recognition.interimResults = true;

// Reduce alternatives
wakeWordConfig.recognition.maxAlternatives = 1;

// Shorter recording time
wakeWordConfig.maxRecordingMs = 2000;  // From 3000
```

### Debug Tools

```javascript
// Enable debug logging
localStorage.setItem('alice_wake_word_debug', 'true');

// Test wake-word matching
wakeWordDetector.testWakeWord('alice', 0.8);
wakeWordDetector.testWakeWord('allis', 0.7);  
wakeWordDetector.testWakeWord('alis', 0.6);

// Monitor real-time performance
wakeWordDetector.on('debug_metrics', (metrics) => {
  console.log('Real-time metrics:', metrics);
});

// Check detection history
const history = wakeWordDetector.getDetectionHistory();
console.log('Recent detections:', history);
```

## Production Recommendations

### Recommended Production Configuration

```javascript
const productionConfig = {
  // Balanced settings for Swedish users
  wakeWords: ['alice', 'allis', 'alis'],
  sensitivity: 0.7,
  cooldownMs: 2000,
  maxRecordingMs: 3000,
  language: 'sv-SE',
  continuous: true,
  
  // Optimized matching
  matching: {
    exactMatchThreshold: 0.5,
    fuzzyMatchThreshold: 0.7,
    partialMatchThreshold: 1.2,
    fuzzyMatchSimilarity: 0.75,
  },
  
  // Performance optimizations
  recognition: {
    interimResults: true,
    maxAlternatives: 2,
  },
  
  // Audio processing
  audio: {
    noiseGateLevel: 0.02,
    ambientNoiseAdaptation: true,
  }
};
```

### Quality Assurance Metrics

**Minimum Acceptance Criteria:**
- Wake-word Detection Rate: ≥ 95%
- False Positive Rate: ≤ 2% 
- Response Latency: ≤ 500ms
- Swedish Accent Support: ≥ 90% for major dialects
- Noise Robustness: Functions with background noise up to 65dB
- Resource Usage: < 15% CPU, < 50MB memory growth/30min

### Deployment Checklist

- [ ] Configuration reviewed and approved
- [ ] Manual testing checklist completed (≥ 90% pass rate)
- [ ] Performance benchmarks meet targets
- [ ] Swedish accent testing completed
- [ ] False positive testing completed
- [ ] Production environment testing completed
- [ ] Rollback plan prepared
- [ ] Monitoring and alerting configured

## References

- [Swedish Wake-Word Testing Checklist](../tests/wake_word_testing_checklist.md)
- [Audio Enhancement Guide](./AUDIO_ENHANCEMENT.md) 
- [Voice Pipeline Architecture](./VOICE_PIPELINE.md)
- [Browser Speech API Documentation](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition)

---

**Last Updated:** 2025-01-22  
**Version:** 1.0  
**Tested With:** Chrome 120+, Firefox 120+, Safari 17+