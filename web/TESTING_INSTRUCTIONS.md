# Voice System Testing Instructions

## 🎯 Complete Voice Flow Test

I have fixed the WebSocket endpoint issue and created comprehensive testing scripts. Here's how to test the entire voice system:

### 1. Quick Test (Browser Console)

1. Open browser to `http://localhost:3000`
2. Open DevTools Console (F12)
3. Paste and run this script:

```javascript
// Load the quick test script
fetch('/quick-ws-test.js').then(r => r.text()).then(code => eval(code))
```

### 2. Complete End-to-End Test with JSONL Logging

1. In browser console, paste and run:

```javascript
// Load the comprehensive test
fetch('/voice-end-to-end-test.js').then(r => r.text()).then(code => eval(code))
```

This will:
- ✅ Test browser capabilities 
- ✅ Check backend connectivity
- ✅ Test WebSocket connection to `/ws/alice`
- ✅ Simulate mic button click
- ✅ Test speech recognition
- ✅ Send Alice command
- ✅ Test TTS response
- 💾 Download complete JSONL log file

### 3. Manual UI Test

1. Go to `http://localhost:3000`
2. Click the microphone icon in the top-right of the VoiceBox
3. Check browser console for logs:
   - `🌐 [VoiceGateway] Connecting to: ws://127.0.0.1:8000/ws/alice`
   - `✅ [VoiceGateway] Connected successfully`
   - `✅ [VoiceBox] VoiceGateway connected`

### 4. Backend Logs Monitoring

Watch backend terminal for:
```
INFO:     connection open
INFO:     127.0.0.1:XXXXX - "WebSocket /ws/alice" [accepted]
```

## 🔧 What Was Fixed

1. **WebSocket Endpoint**: Changed from `/ws/voice-gateway` to `/ws/alice` (line 1023 in VoiceBox.tsx)
2. **URL Construction**: Enhanced `buildWsUrl` function with proper fallbacks
3. **Error Handling**: Added comprehensive debugging and error recovery
4. **Testing Suite**: Created complete end-to-end test with JSONL logging

## 📊 Expected Test Results

### Success Indicators:
- ✅ WebSocket connects to `ws://127.0.0.1:8000/ws/alice`
- ✅ Mic button changes to red with animation
- ✅ Backend logs show "connection open"
- ✅ No "TypeError: Failed to fetch" errors
- ✅ JSONL file downloads with complete test results

### Failure Indicators:
- ❌ WebSocket connection refused
- ❌ "TypeError: Failed to fetch" errors persist
- ❌ Backend shows no connection activity
- ❌ Mic button doesn't change state

## 🚀 Next Steps

After successful WebSocket connection:
1. Test actual audio streaming
2. Verify speech recognition integration
3. Test Alice command processing
4. Verify TTS response playback
5. Implement Phase 3: Advanced context-aware routing

## 📋 Test Files Created

- `voice-end-to-end-test.js` - Complete E2E test with JSONL logging
- `quick-ws-test.js` - Simple WebSocket connectivity test
- `console-voice-test.js` - Browser console test script
- `voice-flow-test.js` - Original flow test script

All test files will be available at `http://localhost:3000/[filename]` in the browser.