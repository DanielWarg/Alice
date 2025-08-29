# Opus Voice Module Plan
## Production-Ready Swedish Voice Assistant Implementation

**Status:** 🚀 Ready to implement - "nu fan kör vi!"

---

## Overview
Transform Alice Voice Module from proof-of-concept to production-ready Swedish voice assistant with real TTS, optimized browser compatibility, and comprehensive E2E testing.

## Current Status Analysis
✅ **Working Components:**
- Whisper ASR (Swedish transcription)
- NLU Intent Classification (Swedish patterns)
- 128kbps CBR LAME MP3 encoding (Chrome compatibility fixed)
- WebSocket ASR streaming
- Browser microphone integration
- HTTP TTS API with caching

❌ **Critical Issue Identified:**
- **TTS generates 440Hz sine wave tones instead of Swedish speech**
- Files: `piper_sim_audio.py:65` - `sine=frequency=440:duration=X`
- Users hear beeping instead of Alice speaking Swedish

---

## Implementation Plan

### FAS 1: Real Piper TTS Implementation 🎯
**Priority:** CRITICAL - Replace mock TTS immediately

**Target:**
- Install Piper TTS with KBLab Swedish voices
- Generate actual Swedish speech instead of sine wave tones
- Maintain 128kbps CBR LAME encoding for browser compatibility

**Implementation Steps:**
1. Install Piper TTS system
   ```bash
   # macOS with Homebrew
   brew install piper-tts
   # or download binaries
   ```

2. Download Swedish voice models
   ```bash
   # KBLab Swedish voices (recommended)
   wget https://huggingface.co/rhasspy/piper-voices/resolve/main/sv/sv_SE/nst/medium/sv_SE-nst-medium.onnx
   wget https://huggingface.co/rhasspy/piper-voices/resolve/main/sv/sv_SE/nst/medium/sv_SE-nst-medium.onnx.json
   ```

3. Create `server/tts_engine.py` - Real TTS engine
4. Update `server/piper_sim_audio.py` to use real TTS
5. Test Swedish phrases: "Hej Alice", "Du har 3 nya email"

**Validation Commands:**
```bash
# Test current issue (should hear 440Hz tone):
ffplay -autoexit -nodisp server/voice/audio/tts_*.mp3

# After fix (should hear Swedish speech):
curl -X POST http://localhost:8000/api/tts/ \
  -H "Content-Type: application/json" \
  -d '{"text":"Hej, jag heter Alice","voice":"nova","rate":1.0}'
ffplay -autoexit -nodisp server/voice/audio/tts_*.mp3
```

### FAS 2: Browser Playback Resilience
**Target:** Bulletproof audio playback with fallbacks

**Features:**
- Retry mechanism for failed audio loads
- Manual play button as backup
- Multiple audio format support (MP3 → WAV fallback)
- Better error logging and user feedback

### FAS 3: End-to-End Voice Testing
**Target:** Comprehensive real-world testing

**Test Scenarios:**
1. Swedish microphone input → Whisper ASR → NLU → Response → Piper TTS
2. Various Swedish phrases and intents
3. Cross-browser compatibility (Chrome, Safari, Firefox)
4. Network issues and audio codec edge cases

### FAS 4: ASR + NLU Improvements
**Target:** Production-grade speech understanding

**Enhancements:**
- Whisper model optimization (base → small/medium)
- Enhanced Swedish NLU patterns
- Context awareness for conversations
- Confidence scoring and error handling

### FAS 5: Production Polish
**Target:** Enterprise-ready deployment

**Features:**
- Redis caching for TTS/ASR results
- Metrics and monitoring
- Rate limiting and security
- Proper logging and debugging
- Health checks and graceful degradation

---

## Technical Architecture

### Current Voice Pipeline
```
[Microphone] → [WebRTC/getUserMedia] → [Whisper ASR] → [Swedish Text]
                                                            ↓
[Browser Audio] ← [LAME MP3] ← [Piper TTS] ← [Response] ← [NLU Intent] 
```

### File Structure
```
server/
├── piper_sim_audio.py      # Mock TTS (NEEDS REPLACEMENT)
├── tts_engine.py           # Real Piper TTS (TO CREATE)
├── real_whisper_asr.py     # Whisper integration ✅
├── nlu_intent_classifier.py # Swedish NLU ✅
└── app_minimal.py          # Main FastAPI server ✅

web/public/
└── voice-complete.html     # Browser interface ✅
```

### Key Technical Decisions
- **TTS Engine:** Piper with KBLab Swedish voices (local, fast, high-quality)
- **Audio Format:** 128kbps CBR LAME MP3 (Chrome compatibility)
- **ASR Model:** Whisper base (139MB, good Swedish performance)
- **NLU Strategy:** Rule-based + LLM fallback for Swedish
- **Browser Compatibility:** Blob URLs with Range/HEAD support

---

## Critical Success Metrics

### Functional Requirements
- ✅ Swedish speech recognition accuracy >90%
- ❌ **Swedish TTS output (currently 440Hz tones)**
- ✅ Chrome audio playback without DEMUXER errors
- ⏳ E2E voice interaction <3 seconds latency
- ⏳ Cross-browser compatibility (Chrome/Safari/Firefox)

### Performance Requirements
- TTS generation: <1000ms per response
- Audio file size: <50KB for typical responses
- Memory usage: <500MB for voice services
- CPU usage: <50% during active conversations

---

## Next Immediate Action

**Execute FAS 1 immediately:**
1. Install Piper TTS with Swedish voices
2. Create `tts_engine.py` with real speech synthesis
3. Replace sine wave generation in `piper_sim_audio.py`
4. Test with: "Hej Alice, kolla min email" → Hear actual Swedish response

**Validation Test:**
```bash
python3 claude_live_voice_test.py
# Should hear Swedish speech, not 440Hz beeps
```

---

## Implementation Notes

**Security Requirements:**
- ✅ Never expose API keys in code (use .env files)
- All secrets in environment variables
- Proper CORS and security headers

**Swedish Language Support:**
- NLU patterns: "kolla min email", "vad är klockan", "tänd lamporna"
- TTS voices: KBLab Swedish (nst-medium recommended)
- ASR model: Whisper base with Swedish language detection

**Browser Compatibility:**
- Fixed: Chrome DEMUXER_ERROR with proper LAME encoding
- TODO: Safari autoplay policies
- TODO: Firefox audio codec edge cases

---

**Status:** Ready for implementation - "du ser opus plan? nu fan kör vi!" 🚀