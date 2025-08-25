# 🎙️ B2 Requirements Analysis - Barge-in & Echo-skydd

**Datum:** 2025-08-24  
**Systemversion:** B2 - Barge-in & Echo-skydd  
**Bas:** B1 - Always-On Voice + Ambient Memory (100% working)  
**Analyserad av:** Claude Code  

---

## 📋 B2 Requirements Overview

**Primary Goals:**
1. **Barge-in Detection** - Upptäck när användaren avbryter Alice mitt i tal
2. **Echo Cancellation** - Förhindra feedback loops från Alice's egen röst
3. **Seamless Integration** - Bygga på B1's stabila foundation

---

## 🎯 Functional Requirements

### 1. Barge-in Detection System
```
REQUIREMENT: När Alice talar och användaren börjar prata samtidigt
- Upptäck användaren's röst inom <200ms
- Stoppa Alice's pågående tal omedelbart
- Övergå till lyssnande läge för användarens meddelande
- Behåll kontext från det avbrutna talet
```

### 2. Echo Cancellation & Feedback Prevention
```
REQUIREMENT: När Alice spelar upp ljud
- Förhindra att Alice's egen röst triggrar speech detection
- Implementera acoustic echo cancellation (AEC)
- Separera inkommande mic input från utgående speaker output
- Dynamisk volym-justering baserat på echo-nivåer
```

### 3. Audio Pipeline Management
```
REQUIREMENT: Hantera parallella audio streams
- Simultaneous recording (mic in) + playback (speaker out)
- Real-time audio processing med low latency (<100ms)
- Buffer management för smooth transitions
- Cross-platform audio device handling
```

### 4. State Management
```
REQUIREMENT: Conversation flow states
- LISTENING: Normal always-on listening mode
- SPEAKING: Alice talking, monitoring för barge-in  
- INTERRUPTED: User barged in, stop Alice, switch to listening
- PROCESSING: Analyzing user input, preparing response
```

---

## 🏗️ Technical Architecture Design

### Audio Processing Pipeline
```
[Microphone] → [Echo Cancellation] → [VAD] → [Speech Detection] → [Transcription]
                       ↑
[Speaker] ← [Audio Output] ← [Alice Response] ← [TTS/Audio Generation]
```

### Core Components Needed

#### 1. EchoCanceller Class
```typescript
interface EchoCanceller {
  initialize(micStream: MediaStream, speakerRef: AudioContext): void;
  process(inputAudio: Float32Array): Float32Array; // Returns cleaned audio
  calibrate(): void; // Auto-adjust för current environment
  setPlaybackLevel(volume: number): void; // Inform about outgoing audio
}
```

#### 2. BargeInDetector Class
```typescript
interface BargeInDetector {
  startMonitoring(audioStream: MediaStream): void;
  onBargeInDetected: (confidence: number) => void;
  setSensitivity(level: number): void; // 0.0-1.0
  isCurrentlySpeaking: boolean; // Alice talking state
}
```

#### 3. AudioStateManager Class
```typescript
interface AudioStateManager {
  currentState: 'listening' | 'speaking' | 'interrupted' | 'processing';
  transitionTo(newState: string, context?: any): void;
  onStateChange: (oldState: string, newState: string) => void;
}
```

#### 4. Enhanced Orchestrator
```typescript
// Extend existing Orchestrator from B1
class EnhancedOrchestrator extends Orchestrator {
  private echoCanceller: EchoCanceller;
  private bargeInDetector: BargeInDetector;
  private audioStateManager: AudioStateManager;
  
  handleBargeIn(userInput: string): void;
  resumeAfterInterruption(): void;
}
```

---

## 🧪 Testing Strategy

### Test Categories

#### 1. Echo Cancellation Tests
```bash
✅ Basic echo removal - Alice's voice doesn't trigger speech detection
✅ Volume adaptation - Different speaker volumes don't cause feedback
✅ Latency test - Echo cancellation adds <50ms delay
✅ Background noise - Works with ambient noise present
✅ Multiple audio sources - Handles music + speech simultaneously
```

#### 2. Barge-in Detection Tests
```bash
✅ Fast interruption - Detect user speech within 200ms
✅ Confidence levels - Distinguish speech from noise (>80% accuracy)
✅ Context preservation - Remember Alice's interrupted message
✅ Smooth transition - Seamless switch from speaking to listening
✅ False positive prevention - Don't trigger on background sounds
```

#### 3. Integration Tests
```bash
✅ B1 compatibility - All existing ambient memory features work
✅ Performance impact - B2 features don't slow down B1 (<10% overhead)
✅ Error recovery - Graceful handling of audio device failures
✅ Cross-platform - Works on macOS, Windows, Linux
✅ Long session stability - No memory leaks during extended use
```

#### 4. Real-world Scenarios
```bash
✅ Noisy environment test - Coffee shop ambient noise
✅ Multiple speakers - Several people talking nearby
✅ Various microphone qualities - Built-in laptop mic vs external
✅ Different room acoustics - Echoey room vs dampened space
✅ Network interruptions - WebSocket reconnection during conversation
```

---

## 🚀 Implementation Plan

### Phase 1: Audio Foundation (Week 1)
- Set up Web Audio API pipeline
- Basic echo cancellation implementation
- Audio device enumeration and selection
- Low-latency buffer management

### Phase 2: Detection Logic (Week 1)
- Voice Activity Detection (VAD) enhancement
- Barge-in detection algorithm
- Confidence scoring system
- State transition logic

### Phase 3: Integration (Week 1)
- Extend B1 Orchestrator with B2 features
- Update RealtimeASR for barge-in handling
- Modify AmbientBuffer for interrupted conversations
- WebSocket protocol enhancements

### Phase 4: Testing & Polish (Week 1)
- Comprehensive test suite creation
- Performance optimization
- Cross-platform testing
- User experience refinement

---

## 📊 Success Metrics

### Performance Targets
```
🎯 Echo Cancellation: >95% reduction in feedback loops
🎯 Barge-in Detection: <200ms response time
🎯 Audio Latency: <100ms total pipeline delay
🎯 False Positive Rate: <5% incorrect barge-in triggers
🎯 Integration Impact: <10% performance overhead on B1 features
🎯 Test Coverage: 100% success rate on all B2 test scenarios
```

### Quality Gates
```
✅ No regression on B1 functionality
✅ Clean audio with echo cancellation active
✅ Reliable barge-in detection in various environments
✅ Smooth conversation flow with interruptions
✅ Stable long-term operation (>1 hour continuous use)
```

---

## 🔧 Technical Challenges & Solutions

### Challenge 1: Browser Audio Limitations
**Problem:** Web browsers have limited low-level audio access
**Solution:** 
- Use Web Audio API with AudioWorklet for real-time processing
- Implement WASM-based audio processing for performance
- Fallback to simpler detection methods on older browsers

### Challenge 2: Echo Cancellation Accuracy
**Problem:** Acoustic echo cancellation is computationally expensive
**Solution:**
- Adaptive filtering with NLMS (Normalized Least Mean Squares)
- Pre-configured profiles for common scenarios
- Dynamic adjustment based on detected echo patterns

### Challenge 3: Barge-in False Positives
**Problem:** Background noise may trigger false barge-ins
**Solution:**
- Multi-layered detection (energy, spectral, temporal features)
- Machine learning-based confidence scoring
- User-configurable sensitivity settings

### Challenge 4: State Synchronization
**Problem:** Complex state management across audio, WebSocket, and UI
**Solution:**
- Centralized state machine with clear transition rules
- Event-driven architecture with proper error boundaries
- Comprehensive logging for debugging state issues

---

## 🎉 Expected Outcomes

After B2 implementation, Alice will have:

✅ **Natural Conversation Flow** - Users can interrupt Alice naturally  
✅ **Clean Audio Pipeline** - No feedback or echo issues  
✅ **Robust Detection** - Reliable barge-in without false triggers  
✅ **Seamless Integration** - B2 enhances B1 without breaking existing features  
✅ **Production Quality** - Ready for real-world usage scenarios  

**Next Phase:** B3 - Advanced Context & Multi-modal Interaction

---

*Requirements Analysis by Claude Code • 2025-08-24*  
*Alice B2 - Barge-in & Echo-skydd Technical Specification*