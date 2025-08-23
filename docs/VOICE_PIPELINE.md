# 🎙️ Alice Voice Pipeline Architecture

**Complete technical documentation for Alice's Swedish voice pipeline with production-ready specifications.**

## 🏗️ **System Overview**

Alice implements a sophisticated dual-mode voice pipeline optimized for Swedish language interaction with professional-grade audio processing and error resilience.

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Alice Voice Pipeline                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  VoiceBox   │    │ VoiceClient │    │    Agent    │         │
│  │   (Basic)   │◄──►│ (Advanced)  │◄──►│   Bridge    │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                   │                   │               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Browser   │    │   OpenAI    │    │   Alice     │         │
│  │ Speech API  │    │ Realtime API│    │   Agent     │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                   │                   │               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Piper     │    │   WebRTC    │    │ Tool Router │         │
│  │ TTS Engine  │    │  Streaming  │    │  & Memory   │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Voice Modes

1. **VoiceBox Mode** - Browser-based, development-friendly
2. **VoiceClient Mode** - OpenAI Realtime, production-grade  
3. **Dual Mode** - Intelligent fallback system (recommended)

---

## 🎯 **Wake-Word Detection**

### Parameters & Configuration

**Wake Phrase**: `"Hej Alice"` (Swedish)

#### Core Parameters

```javascript
const WAKE_WORD_CONFIG = {
  // Detection sensitivity (0.0 - 1.0)
  sensitivity: 0.7,           // Default: balanced accuracy/false-positives
  
  // Audio processing
  sampleRate: 16000,          // 16kHz for wake-word processing
  frameLength: 512,           // Audio frame size
  hopLength: 256,             // Overlap between frames
  
  // Swedish phoneme optimization
  language: 'sv-SE',
  phonemeWeights: {
    'hej': 0.4,               // Weight for "hej" component
    'alice': 0.6              // Weight for "Alice" component
  },
  
  // Timing constraints
  maxPhraseLength: 2000,      // Max 2 seconds for full phrase
  silenceThreshold: 100,      // Silence detection threshold
  confirmationDelay: 150,     // Delay before activation (ms)
  
  // Performance tuning
  energyThreshold: 0.02,      // Minimum audio energy level
  spectralContrast: 0.15,     // Spectral analysis threshold
  noiseGateLevel: 0.05        // Background noise suppression
}
```

#### Tuning Guidelines

**1. Sensitivity Adjustment**
```javascript
// Conservative (fewer false positives)
sensitivity: 0.8 - 0.9

// Balanced (recommended)  
sensitivity: 0.7 - 0.8

// Aggressive (better detection in noise)
sensitivity: 0.5 - 0.7
```

**2. Environment-Specific Tuning**
- **Quiet office**: sensitivity: 0.8, energyThreshold: 0.01
- **Home environment**: sensitivity: 0.7, energyThreshold: 0.02  
- **Noisy environment**: sensitivity: 0.6, energyThreshold: 0.03

**3. Swedish Pronunciation Variants**
```javascript
const PRONUNCIATION_VARIANTS = [
  { pattern: 'hej alice', confidence: 1.0 },
  { pattern: 'hey alice', confidence: 0.8 },    // English influence
  { pattern: 'hei alice', confidence: 0.9 },    // Norwegian influence
  { pattern: 'hæj alice', confidence: 0.7 }     // Danish influence
]
```

### Performance Targets

| Metric | Target | Measurement |
|--------|---------|-------------|
| **Latency** | < 100ms | Wake detection to activation |
| **Accuracy** | > 95% | True positive rate |
| **False Positives** | < 1/hour | In normal conversation |
| **CPU Usage** | < 5% | Continuous monitoring |
| **Memory** | < 20MB | Background process |

### Testing Checklist

**Manual Testing Protocol**:

- [ ] **Basic Detection**: Say "Hej Alice" in normal voice at 1m distance
- [ ] **Volume Variations**: Test whisper, normal, loud voice levels  
- [ ] **Accent Variations**: Test different Swedish regional accents
- [ ] **Noise Robustness**: Test with background music, typing, conversation
- [ ] **False Positive Test**: Have 10-minute conversation without saying wake phrase
- [ ] **Multi-speaker**: Test detection with multiple people in room
- [ ] **Edge Cases**: Test partial phrases, similar-sounding words

**Automated Testing**:
```bash
# Run wake-word performance tests
python test_wake_word_detection.py --sensitivity 0.7 --test-duration 300

# Expected output:
# Wake-word Detection Test Results:
# - True positives: 98/100 (98%)
# - False positives: 0/3600 samples
# - Average latency: 87ms
# - CPU usage: 3.2%
```

---

## 🎧 **Speech-to-Text (Whisper)**

### Swedish Model Configuration

**Primary Model**: `faster-whisper small` optimized for Swedish

```python
WHISPER_CONFIG = {
    # Model settings
    'model_name': 'small',                    # Balance of speed/accuracy
    'language': 'sv',                         # Swedish language code
    'device': 'cpu',                          # Primary compute device
    'compute_type': 'int8',                   # Quantization for efficiency
    
    # Swedish optimization
    'beam_size': 5,                          # Search beam width
    'best_of': 3,                            # Generate N candidates
    'temperature': 0.0,                      # Deterministic output
    'condition_on_previous_text': True,      # Context awareness
    'initial_prompt': 'Detta är svenska tal med kommandon till AI-assistenten Alice.',
    
    # Performance tuning
    'word_timestamps': True,                 # Enable word-level timing
    'vad_filter': True,                      # Voice activity detection
    'vad_parameters': {
        'threshold': 0.5,
        'min_speech_duration_ms': 250,
        'max_speech_duration_s': 30,
        'min_silence_duration_ms': 1000,
        'speech_pad_ms': 400
    }
}
```

### Performance Targets

| Metric | Target | Fallback | Measurement |
|--------|---------|----------|-------------|
| **Latency** | < 500ms | < 1000ms | Audio end to transcript |
| **Accuracy** | > 92% | > 85% | Word error rate (WER) |
| **Real-time Factor** | < 0.3 | < 0.5 | Processing/audio duration |
| **Memory Usage** | < 500MB | < 1GB | Peak model memory |
| **Swedish WER** | < 8% | < 15% | Swedish-specific accuracy |

### Model Fallback Strategy

**CPU/GPU Fallback Chain**:

```python
FALLBACK_CHAIN = [
    {
        'name': 'primary',
        'model': 'small',
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'compute_type': 'float16' if torch.cuda.is_available() else 'int8',
        'timeout': 2000  # 2 second timeout
    },
    {
        'name': 'cpu_optimized', 
        'model': 'small',
        'device': 'cpu',
        'compute_type': 'int8',
        'beam_size': 1,  # Faster, less accurate
        'timeout': 5000
    },
    {
        'name': 'tiny_fallback',
        'model': 'tiny',
        'device': 'cpu', 
        'compute_type': 'int8',
        'beam_size': 1,
        'timeout': 10000
    }
]
```

### Swedish Language Optimization

**Post-Processing Rules**:

```python
SWEDISH_CORRECTIONS = {
    # Common Whisper Swedish errors
    'alice s': 'Alice',
    'allis': 'Alice', 
    'alis': 'Alice',
    'okay': 'okej',
    'ok': 'okej',
    'hello': 'hej',
    'bye': 'hej då',
    'play music': 'spela musik',
    'send email': 'skicka mejl',
    
    # Swedish grammar corrections
    'vad tid är det': 'vad är klockan',
    'skicka mail': 'skicka mejl',
    'google kalender': 'Google Calendar'
}

SWEDISH_PHONEME_MAP = {
    # Handle Swedish characters that Whisper might miss
    'å': ['o', 'aa', 'aw'],
    'ä': ['a', 'ae', 'eh'], 
    'ö': ['o', 'oe', 'ur']
}
```

### Quality Assessment

**Audio Quality Metrics**:

```python
def assess_audio_quality(info) -> Dict[str, Any]:
    return {
        'overall_score': 'good' | 'fair' | 'poor',
        'duration': float,                    # Audio length in seconds
        'language_probability': float,        # 0.0 - 1.0 confidence  
        'detected_language': str,             # Should be 'sv'
        'issues': List[str],                  # Quality issues detected
        'recommendations': List[str],         # Improvement suggestions
        'noise_level': float,                 # Background noise estimate
        'speech_rate': float,                 # Words per minute
        'clarity_score': float               # 0.0 - 1.0 speech clarity
    }
```

---

## 🗣️ **Text-to-Speech (Piper)**

### Voice Model Licensing

**Swedish Voice Models**:

| Model | License | Commercial Use | Attribution |
|-------|---------|---------------|-------------|
| `sv_SE-nst-medium` | MIT | ✅ Yes | NST (KTH Royal Institute) |
| `sv_SE-nst-high` | MIT | ✅ Yes | NST (KTH Royal Institute) |
| `sv_SE-lisa-medium` | Apache 2.0 | ✅ Yes | Piper Community |

**License Compliance**:
```python
VOICE_LICENSES = {
    'sv_SE-nst-medium': {
        'license': 'MIT',
        'source': 'https://github.com/kth-speech/piper-voices',
        'attribution': 'NST Swedish Dataset - KTH Royal Institute of Technology',
        'commercial': True,
        'redistribution': True,
        'modification': True
    }
}
```

### Cache Policy

**TTS Cache Strategy**:

```python
TTS_CACHE_CONFIG = {
    # Cache settings
    'enabled': True,
    'backend': 'filesystem',              # filesystem | redis | memory
    'max_size_mb': 1000,                  # 1GB cache limit
    'max_entries': 10000,                 # Maximum cached utterances
    'ttl_hours': 168,                     # 1 week cache lifetime
    
    # Cache keys (MD5 hash of)
    'key_components': [
        'text',                           # Utterance text
        'voice',                          # Voice model name
        'personality',                    # Alice personality
        'emotion',                        # Emotional tone
        'speed',                          # Speech rate
        'pitch'                           # Pitch adjustment
    ],
    
    # Performance optimization
    'compression': 'gzip',                # Compress cached audio
    'async_write': True,                  # Non-blocking cache writes
    'preload_common': True,               # Preload frequent phrases
    'batch_cleanup': True                 # Batch cache maintenance
}
```

**Cache Performance Targets**:

| Metric | Target | Impact |
|--------|---------|--------|
| **Cache Hit Rate** | > 70% | 3-10x faster response |
| **Cache Lookup** | < 5ms | Real-time performance |
| **Storage Efficiency** | 60-80% | Compression ratio |
| **Memory Overhead** | < 100MB | Cache metadata |

### Quality Targets

**Audio Quality Specifications**:

```python
TTS_QUALITY_TARGETS = {
    # Audio specifications
    'sample_rate': 22050,                 # CD-quality sample rate
    'bit_depth': 16,                      # 16-bit audio depth
    'channels': 1,                        # Mono audio
    'format': 'wav',                      # Uncompressed audio
    
    # Swedish voice quality
    'naturalness': 8.5,                   # 0-10 MOS scale
    'intelligibility': 9.2,               # Swedish comprehension
    'emotional_range': 7.8,               # Emotional expression
    'consistency': 9.0,                   # Voice stability
    
    # Performance requirements
    'latency_ms': {
        'cached': 50,                     # Cache hit response
        'synthesis': 300,                 # Real-time synthesis
        'streaming': 150                  # Streaming first chunk
    },
    
    # Volume and dynamics
    'peak_level_db': -3.0,                # Prevent clipping
    'loudness_lufs': -16.0,               # Broadcast loudness
    'dynamic_range_db': 12.0              # Natural speech dynamics
}
```

### Personality System

**Voice Personalities**:

```python
PERSONALITY_SETTINGS = {
    'alice': {
        'speed': 1.05,                    # Slightly faster
        'pitch': 1.02,                    # Slightly higher
        'emotion_bias': 'friendly',       # Default emotional tone
        'formality': 'casual',            # Conversational style
        'pronunciation': 'standard'       # Standard Swedish
    },
    'formal': {
        'speed': 0.95,                    # Slower, more deliberate
        'pitch': 0.98,                    # Slightly lower
        'emotion_bias': 'neutral',        # Professional tone
        'formality': 'formal',            # Formal Swedish
        'pronunciation': 'precise'        # Clear articulation
    },
    'casual': {
        'speed': 1.15,                    # Faster, energetic
        'pitch': 1.05,                    # Higher pitch
        'emotion_bias': 'happy',          # Upbeat tone
        'formality': 'very_casual',       # Colloquial Swedish
        'pronunciation': 'relaxed'        # Natural flow
    }
}

EMOTIONAL_TONES = {
    'neutral': {'pitch_mod': 0.0, 'speed_mod': 0.0, 'energy': 0.5},
    'happy': {'pitch_mod': 0.08, 'speed_mod': 0.1, 'energy': 0.8},
    'calm': {'pitch_mod': -0.05, 'speed_mod': -0.1, 'energy': 0.3},
    'confident': {'pitch_mod': -0.03, 'speed_mod': 0.05, 'energy': 0.7},
    'friendly': {'pitch_mod': 0.03, 'speed_mod': 0.02, 'energy': 0.6}
}
```

---

## 🎛️ **VoiceBox Component**

### Data Test IDs

**Component Test Attributes**:

```typescript
const VOICE_BOX_TEST_IDS = {
    // Main container
    container: 'voice-box-container',
    
    // Audio visualization
    barsContainer: 'voice-box-bars',
    audioBar: (index: number) => `voice-box-bar-${index}`,
    
    // Controls
    startButton: 'voice-box-start',
    stopButton: 'voice-box-stop', 
    testTtsButton: 'voice-box-test-tts',
    
    // Status indicators
    statusIndicator: 'voice-box-status',
    errorMessage: 'voice-box-error',
    ttsStatus: 'voice-box-tts-status',
    
    // Settings
    personalitySelect: 'voice-box-personality-select',
    emotionSelect: 'voice-box-emotion-select',
    qualitySelect: 'voice-box-quality-select',
    
    // Audio levels
    microphoneLevel: 'voice-box-mic-level',
    voiceActivityIndicator: 'voice-box-vad'
}
```

### E2E Test Specifications

**Playwright Test Suite**:

```typescript
// tests/e2e/voice-box.spec.ts
describe('VoiceBox Component', () => {
    test('should render audio visualization bars', async ({ page }) => {
        await page.goto('/voice')
        
        // Check bars container exists
        const barsContainer = page.getByTestId('voice-box-bars')
        await expect(barsContainer).toBeVisible()
        
        // Verify correct number of bars
        const bars = page.getByTestId(/voice-box-bar-\d+/)
        await expect(bars).toHaveCount(7) // Default 7 bars
        
        // Check bars have proper styling
        for (let i = 0; i < 7; i++) {
            const bar = page.getByTestId(`voice-box-bar-${i}`)
            await expect(bar).toHaveClass(/bar/)
            await expect(bar).toHaveCSS('height', /.+/)
        }
    })
    
    test('should handle microphone permissions', async ({ page, context }) => {
        // Grant microphone permission
        await context.grantPermissions(['microphone'])
        await page.goto('/voice')
        
        const startButton = page.getByTestId('voice-box-start')
        await startButton.click()
        
        // Should transition to live mode
        await expect(page.getByTestId('voice-box-status')).toContainText('LIVE')
        
        // Bars should start animating
        const bar = page.getByTestId('voice-box-bar-0')
        const initialHeight = await bar.evaluate(el => el.style.height)
        
        // Wait for animation
        await page.waitForTimeout(1000)
        
        const newHeight = await bar.evaluate(el => el.style.height)
        expect(newHeight).not.toBe(initialHeight)
    })
    
    test('should fallback to demo mode when mic denied', async ({ page, context }) => {
        // Deny microphone permission
        await context.grantPermissions([])
        await page.goto('/voice')
        
        const startButton = page.getByTestId('voice-box-start')
        await startButton.click()
        
        // Should show demo mode error
        const errorMsg = page.getByTestId('voice-box-error')
        await expect(errorMsg).toContainText('demo‑läge')
        
        // Should still show live status
        await expect(page.getByTestId('voice-box-status')).toContainText('LIVE')
    })
    
    test('should test TTS functionality', async ({ page }) => {
        await page.goto('/voice')
        
        const testButton = page.getByTestId('voice-box-test-tts')
        await testButton.click()
        
        // Should show TTS status
        const ttsStatus = page.getByTestId('voice-box-tts-status')
        await expect(ttsStatus).toContainText('Testar Alice röst')
        
        // Status should update during playback
        await expect(ttsStatus).toContainText('Spelar', { timeout: 5000 })
    })
    
    test('should change personality settings', async ({ page }) => {
        await page.goto('/voice')
        
        const personalitySelect = page.getByTestId('voice-box-personality-select')
        await personalitySelect.selectOption('formal')
        
        // Should log personality change
        const consolePromise = page.waitForEvent('console', msg => 
            msg.text().includes('Personality change: formal'))
        await expect(consolePromise).resolves.toBeTruthy()
        
        // Test TTS with new personality
        const testButton = page.getByTestId('voice-box-test-tts')
        await testButton.click()
        
        const ttsStatus = page.getByTestId('voice-box-tts-status')
        await expect(ttsStatus).toContainText('formal')
    })
})
```

### Performance Testing

```typescript
test('voice box performance under load', async ({ page }) => {
    await page.goto('/voice')
    await page.getByTestId('voice-box-start').click()
    
    // Measure animation frame rate
    const fps = await page.evaluate(() => {
        return new Promise(resolve => {
            let frames = 0
            const start = performance.now()
            
            function countFrames() {
                frames++
                if (frames < 60) {
                    requestAnimationFrame(countFrames)
                } else {
                    const duration = performance.now() - start
                    resolve(Math.round(60000 / duration))
                }
            }
            requestAnimationFrame(countFrames)
        })
    })
    
    // Should maintain at least 30 FPS
    expect(fps).toBeGreaterThan(30)
})
```

---

## 🛡️ **Error Handling & Resilience**

### Microphone Error Handling

**Error Categories**:

```typescript
enum VoiceError {
    // Permission errors
    MICROPHONE_DENIED = 'microphone_access_denied',
    MICROPHONE_NOT_FOUND = 'microphone_not_found', 
    MICROPHONE_IN_USE = 'microphone_already_in_use',
    
    // Hardware errors
    HARDWARE_FAILURE = 'audio_hardware_failure',
    DRIVER_ERROR = 'audio_driver_error',
    
    // Browser/environment errors
    WEBRTC_NOT_SUPPORTED = 'webrtc_not_supported',
    HTTPS_REQUIRED = 'https_required_for_microphone',
    CONTEXT_SUSPENDED = 'audio_context_suspended',
    
    // Network errors
    CONNECTION_FAILED = 'network_connection_failed',
    API_RATE_LIMITED = 'api_rate_limited',
    SERVICE_UNAVAILABLE = 'service_temporarily_unavailable',
    
    // Processing errors
    TRANSCRIPTION_FAILED = 'speech_transcription_failed',
    TTS_SYNTHESIS_FAILED = 'speech_synthesis_failed',
    AUDIO_PROCESSING_ERROR = 'audio_processing_error'
}
```

### Resilient Error Handling

**Error Recovery Strategy**:

```typescript
class VoiceErrorHandler {
    private retryAttempts = new Map<string, number>()
    private maxRetries = 3
    private retryDelays = [1000, 2000, 5000] // Progressive backoff
    
    async handleVoiceError(error: VoiceError, context: any): Promise<boolean> {
        const attemptKey = `${error}_${Date.now()}`
        const attempts = this.retryAttempts.get(error) || 0
        
        // Log error with context
        this.logError(error, context, attempts)
        
        // Check if we should retry
        if (attempts >= this.maxRetries) {
            return this.fallbackToFailsafe(error, context)
        }
        
        // Increment retry counter
        this.retryAttempts.set(error, attempts + 1)
        
        // Apply error-specific recovery
        switch (error) {
            case VoiceError.MICROPHONE_DENIED:
                return this.handleMicrophoneDenied(context)
                
            case VoiceError.MICROPHONE_NOT_FOUND:
                return this.handleMicrophoneNotFound(context)
                
            case VoiceError.CONNECTION_FAILED:
                return this.handleConnectionFailed(context, attempts)
                
            case VoiceError.TRANSCRIPTION_FAILED:
                return this.handleTranscriptionFailed(context, attempts)
                
            default:
                return this.handleGenericError(error, context, attempts)
        }
    }
    
    private async handleMicrophoneDenied(context: any): Promise<boolean> {
        // Show user-friendly permission request
        this.showPermissionDialog()
        
        // Try demo mode as fallback
        if (context.allowDemo) {
            return context.startDemo()
        }
        
        // Final fallback to pseudo mode
        if (context.allowPseudo) {
            return context.startPseudo()
        }
        
        return false
    }
    
    private async handleConnectionFailed(context: any, attempts: number): Promise<boolean> {
        // Wait with exponential backoff
        await this.delay(this.retryDelays[attempts] || 5000)
        
        // Try different endpoint/mode
        if (attempts === 0) {
            return context.retryWithFallbackEndpoint()
        }
        
        // Switch to offline mode
        return context.switchToOfflineMode()
    }
    
    private logError(error: VoiceError, context: any, attempts: number) {
        const errorData = {
            error,
            attempts,
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            context: {
                voiceMode: context.mode,
                connectionState: context.connectionState,
                permissions: this.getPermissionStatus()
            }
        }
        
        // Log to console for development
        console.error('Voice Error:', errorData)
        
        // Send to monitoring service in production
        if (process.env.NODE_ENV === 'production') {
            this.sendErrorToMonitoring(errorData)
        }
    }
}
```

### UI Error States

**Error Display Components**:

```typescript
const ErrorDisplay: React.FC<{ error: VoiceError, onRetry: () => void }> = ({ error, onRetry }) => {
    const getErrorMessage = (error: VoiceError) => {
        const messages = {
            [VoiceError.MICROPHONE_DENIED]: {
                title: 'Mikrofon åtkomst nekad',
                message: 'Alice behöver mikrofon för röstinput. Klicka på mikrofon-ikonen i adressfältet och välj "Tillåt".',
                action: 'Försök igen',
                canRetry: true
            },
            [VoiceError.MICROPHONE_NOT_FOUND]: {
                title: 'Ingen mikrofon hittades',
                message: 'Kontrollera att en mikrofon är ansluten och fungerar.',
                action: 'Kontrollera mikrofon',
                canRetry: true
            },
            [VoiceError.CONNECTION_FAILED]: {
                title: 'Anslutning misslyckades',
                message: 'Kunde inte ansluta till röstservicen. Kontrollera internetanslutningen.',
                action: 'Försök igen',
                canRetry: true
            },
            [VoiceError.SERVICE_UNAVAILABLE]: {
                title: 'Service tillfälligt otillgänglig',
                message: 'Röstservicen är för närvarande otillgänglig. Försök igen om en stund.',
                action: 'Försök igen',
                canRetry: true
            }
        }
        
        return messages[error] || {
            title: 'Okänt fel',
            message: 'Ett oväntat fel inträffade. Ladda om sidan och försök igen.',
            action: 'Ladda om',
            canRetry: false
        }
    }
    
    const errorInfo = getErrorMessage(error)
    
    return (
        <div className="voice-error-container" data-testid="voice-error">
            <div className="error-icon">⚠️</div>
            <h3 className="error-title">{errorInfo.title}</h3>
            <p className="error-message">{errorInfo.message}</p>
            {errorInfo.canRetry && (
                <button 
                    onClick={onRetry}
                    className="retry-button"
                    data-testid="voice-error-retry"
                >
                    {errorInfo.action}
                </button>
            )}
        </div>
    )
}
```

### Logging Strategy

**Structured Voice Logging**:

```python
import structlog
import uuid
from datetime import datetime

logger = structlog.get_logger("alice.voice")

class VoiceLogger:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
    
    def log_voice_session_start(self, mode: str, settings: dict):
        logger.info(
            "voice_session_started",
            session_id=self.session_id,
            voice_mode=mode,
            settings=settings,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def log_transcription(self, audio_duration: float, text: str, confidence: float):
        logger.info(
            "transcription_completed",
            session_id=self.session_id,
            audio_duration_seconds=audio_duration,
            transcript_length=len(text),
            confidence_score=confidence,
            language_detected="sv",
            processing_time_ms=self._get_processing_time()
        )
    
    def log_tts_synthesis(self, text: str, voice: str, cached: bool, duration: float):
        logger.info(
            "tts_synthesis",
            session_id=self.session_id,
            text_length=len(text),
            voice_model=voice,
            cache_hit=cached,
            synthesis_duration_ms=duration,
            audio_quality_score=self._assess_audio_quality()
        )
    
    def log_error(self, error_type: str, error_details: dict, recovery_attempted: bool):
        logger.error(
            "voice_error",
            session_id=self.session_id,
            error_type=error_type,
            error_details=error_details,
            recovery_attempted=recovery_attempted,
            stack_trace=self._get_stack_trace(),
            user_agent=self._get_user_agent(),
            system_info=self._get_system_info()
        )
```

### Monitoring & Alerts

**Health Checks**:

```python
async def voice_pipeline_health_check() -> dict:
    """Comprehensive voice pipeline health assessment"""
    health = {
        'timestamp': datetime.utcnow().isoformat(),
        'overall_status': 'healthy',
        'components': {}
    }
    
    # Check Whisper STT
    try:
        stt_latency = await test_whisper_latency()
        health['components']['whisper'] = {
            'status': 'healthy' if stt_latency < 1000 else 'degraded',
            'latency_ms': stt_latency,
            'model_loaded': is_whisper_model_loaded()
        }
    except Exception as e:
        health['components']['whisper'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # Check TTS Pipeline
    try:
        tts_latency = await test_tts_synthesis("Hälsotest")
        health['components']['tts'] = {
            'status': 'healthy' if tts_latency < 500 else 'degraded',
            'latency_ms': tts_latency,
            'cache_hit_rate': get_tts_cache_hit_rate()
        }
    except Exception as e:
        health['components']['tts'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # Check OpenAI Realtime API
    try:
        openai_status = await check_openai_realtime_status()
        health['components']['openai_realtime'] = openai_status
    except Exception as e:
        health['components']['openai_realtime'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # Determine overall status
    component_statuses = [c.get('status', 'unhealthy') for c in health['components'].values()]
    if 'unhealthy' in component_statuses:
        health['overall_status'] = 'unhealthy'
    elif 'degraded' in component_statuses:
        health['overall_status'] = 'degraded'
    
    return health
```

---

## 📊 **Performance Monitoring**

### Key Metrics

**Voice Pipeline KPIs**:

| Metric | Target | Critical Threshold | Monitoring Interval |
|--------|---------|-------------------|-------------------|
| **End-to-End Latency** | < 800ms | > 2000ms | Real-time |
| **Wake Word Accuracy** | > 95% | < 85% | Daily |
| **STT Word Error Rate** | < 8% | > 15% | Daily |
| **TTS Cache Hit Rate** | > 70% | < 50% | Hourly |
| **Audio Quality Score** | > 8.5/10 | < 7.0/10 | Per request |
| **Error Rate** | < 2% | > 10% | Real-time |
| **Resource Usage** | < 200MB | > 500MB | Minutely |

### Performance Testing Suite

```bash
#!/bin/bash
# Voice pipeline performance test suite

echo "🎙️ Running Alice Voice Pipeline Performance Tests"

# Wake-word performance
python test_wake_word_performance.py --duration 300 --target-accuracy 0.95

# STT latency test  
python test_stt_latency.py --audio-samples ./test-audio/swedish/ --target-latency 500

# TTS quality and speed test
python test_tts_performance.py --personalities alice,formal,casual --target-quality 8.5

# Cache performance test
python test_cache_performance.py --cache-size 1000 --target-hit-rate 0.7

# Error resilience test
python test_error_resilience.py --error-scenarios all --recovery-target 90

echo "✅ Performance test suite completed"
```

---

## 🚀 **Production Deployment**

### Environment Configuration

**Production Voice Settings**:

```yaml
# production.yml
voice_pipeline:
  mode: voiceclient                    # Use OpenAI Realtime for production
  wake_word:
    enabled: true
    sensitivity: 0.75                  # Balanced for production
    background_monitoring: true
  
  stt:
    provider: whisper
    model: small
    fallback_enabled: true
    cache_enabled: true
    
  tts:
    provider: piper
    default_voice: sv_SE-nst-medium
    cache_enabled: true
    compression: true
    
  monitoring:
    health_check_interval: 30
    metrics_collection: true
    error_reporting: true
    performance_tracking: true
```

### Scaling Considerations

**Resource Requirements**:

- **CPU**: 2-4 cores for concurrent voice processing
- **Memory**: 1-2GB for models and cache
- **Storage**: 5GB for voice models and cache
- **Network**: Low latency connection for real-time processing

**Load Balancing**:
- Sticky sessions for voice continuity
- Model sharing across instances
- Cache synchronization strategy

---

## 🔧 **Development Guide**

### Local Development Setup

```bash
# Install voice pipeline dependencies
pip install faster-whisper piper-tts pyaudio

# Download Swedish models
python download_voice_models.py --language sv

# Start development server with voice debugging
VOICE_DEBUG=true python run.py

# Run voice pipeline tests
pytest tests/voice/ -v
```

### Testing Voice Components

```typescript
// Mock voice APIs for testing
export const mockVoiceAPIs = {
    SpeechRecognition: MockSpeechRecognition,
    speechSynthesis: MockSpeechSynthesis,
    getUserMedia: mockGetUserMedia
}

// Test voice component in isolation
describe('VoiceBox', () => {
    beforeEach(() => {
        global.navigator.mediaDevices = { getUserMedia: mockGetUserMedia }
        global.window.SpeechRecognition = MockSpeechRecognition
    })
    
    test('handles microphone permission gracefully', async () => {
        // Test implementation
    })
})
```

### Debugging Voice Issues

**Common Debug Commands**:

```bash
# Test microphone access
python -c "import pyaudio; print('Microphone available:', pyaudio.PyAudio().get_device_count())"

# Test Whisper model
python -c "from voice_stt import get_whisper_model; print('Model loaded:', get_whisper_model() is not None)"

# Test TTS synthesis
curl -X POST localhost:8000/api/tts/synthesize -H "Content-Type: application/json" -d '{"text":"Test"}'

# Check browser voice support
# Open browser console: console.log('SpeechRecognition:', 'SpeechRecognition' in window)
```

---

## 📋 **Quality Assurance**

### Manual Testing Checklist

**Voice Pipeline QA**:

- [ ] Wake-word detection works in quiet environment
- [ ] Wake-word detection works with background noise  
- [ ] STT accurately transcribes Swedish commands
- [ ] TTS produces natural Swedish speech
- [ ] Voice switching between personalities works
- [ ] Error recovery works for microphone issues
- [ ] Cache improves TTS response times
- [ ] Voice pipeline integrates with agent correctly
- [ ] WebRTC streaming works without audio gaps
- [ ] Browser compatibility (Chrome, Firefox, Safari)

### Automated Quality Gates

**CI/CD Voice Tests**:

```yaml
# .github/workflows/voice-tests.yml
voice-quality-gates:
  - name: Wake Word Accuracy Test
    command: python test_wake_word.py --min-accuracy 0.95
    
  - name: Swedish STT Quality Test  
    command: python test_swedish_stt.py --max-wer 0.08
    
  - name: TTS Quality Assessment
    command: python test_tts_quality.py --min-mos 8.5
    
  - name: Voice Pipeline Integration
    command: playwright test tests/e2e/voice-integration.spec.ts
```

---

This comprehensive documentation provides production-ready specifications for Alice's Swedish voice pipeline, covering all aspects from wake-word detection to error resilience and performance monitoring.