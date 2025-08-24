# 🔧 Alice Voice Pipeline Troubleshooting Guide

Comprehensive troubleshooting guide for Alice's voice pipeline, covering common issues, diagnostics, and solutions.

## 🚨 **Quick Diagnostics**

### System Health Check

```bash
# Run complete system diagnostics
cd server && python -c "
import subprocess
import requests
import json

print('=== Alice Voice Pipeline Health Check ===')

# Backend health
try:
    r = requests.get('http://localhost:8000/api/health', timeout=5)
    print(f'✅ Backend: {r.status_code} - {r.json().get(\"status\", \"unknown\")}')
except:
    print('❌ Backend: Not responding')

# Frontend health  
try:
    r = requests.get('http://localhost:3000', timeout=5)
    print(f'✅ Frontend: {r.status_code} - Running')
except:
    print('❌ Frontend: Not responding')

# OpenAI API test
import os
if os.getenv('OPENAI_API_KEY'):
    try:
        import openai
        client = openai.OpenAI()
        models = client.models.list()
        print('✅ OpenAI: API key valid')
    except:
        print('❌ OpenAI: API key invalid or rate limited')
else:
    print('⚠️  OpenAI: API key not configured')

print('=== End Health Check ===')
"
```

### Voice Component Status

```javascript
// Browser console diagnostic (paste in browser)
console.log('=== Voice Pipeline Diagnostics ===');

// Check WebRTC support
console.log('WebRTC Support:', {
  'RTCPeerConnection': 'RTCPeerConnection' in window,
  'getUserMedia': navigator.mediaDevices?.getUserMedia !== undefined,
  'AudioContext': 'AudioContext' in window || 'webkitAudioContext' in window
});

// Check Speech API support
console.log('Speech API Support:', {
  'SpeechRecognition': 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window,
  'speechSynthesis': 'speechSynthesis' in window
});

// Check permissions
navigator.permissions?.query({name: 'microphone'}).then(result => {
  console.log('Microphone Permission:', result.state);
});

// Check Alice Voice Client
if (window.AliceVoiceClient) {
  const client = new window.AliceVoiceClient();
  console.log('Alice Voice Status:', client.getStatus());
}

console.log('=== End Diagnostics ===');
```

## 🎤 **Voice Recognition Issues**

### Problem: Microphone Access Denied

**Symptoms:**
- "Mikrofon nekad" error message
- VoiceBox shows error state
- No audio visualization

**Solutions:**

**1. HTTPS Requirement (Most Common)**
```bash
# Development with HTTPS
HTTPS=true npm run dev

# Or use mkcert for local SSL
npm install -g mkcert
mkcert -install
mkcert localhost

# Update package.json
"dev": "next dev --experimental-https --experimental-https-key ./localhost-key.pem --experimental-https-cert ./localhost.pem"
```

**2. Browser Permissions**
```bash
# Chrome
# 1. Click lock icon in address bar
# 2. Set microphone to "Allow"
# 3. Refresh page

# Firefox  
# 1. Click shield icon in address bar
# 2. Turn off enhanced tracking protection
# 3. Allow microphone access

# Safari
# 1. Safari > Preferences > Websites > Microphone
# 2. Set localhost to "Allow"
```

**3. System Permissions (macOS)**
```bash
# Check microphone access
sudo sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db \
  "SELECT client,auth_value FROM access WHERE service='kTCCServiceMicrophone';"

# Reset permissions if needed
sudo tccutil reset Microphone com.google.Chrome
sudo tccutil reset Microphone com.apple.Safari
```

**4. Corporate/School Networks**
```bash
# Often block getUserMedia() API
# Solutions:
# 1. Use different network
# 2. Use VPN
# 3. Contact IT to whitelist WebRTC
# 4. Use VoiceBox demo mode: allowDemo={true}
```

### Problem: Poor Speech Recognition Accuracy

**Symptoms:**
- Incorrect transcriptions
- Commands not recognized
- Swedish words transcribed as English

**Solutions:**

**1. Audio Quality Optimization**
```javascript
// In VoiceBox component
<VoiceBox
  smoothing={0.1}              // Faster response
  enableWakeWord={false}       // Reduce false triggers
  wakeWordSensitivity={0.8}    // Higher accuracy
/>
```

**2. Microphone Settings**
```bash
# Check microphone levels (Linux)
alsamixer

# Check microphone levels (macOS)
# System Preferences > Sound > Input > Input Level

# Test microphone quality
# Use built-in voice recorder to test audio clarity
```

**3. Environment Optimization**
- **Distance**: 15-30cm from microphone
- **Noise**: Minimize background noise
- **Position**: Speak directly toward microphone
- **Speed**: Speak clearly at normal pace
- **Language**: Use Swedish words Alice recognizes

**4. Swedish Language Optimization**
```javascript
// Enhanced Swedish post-processing
const enhancedCorrections = {
  // Common Swedish phrases
  'spela musik': ['play music', 'spela muzik'],
  'pausa musik': ['pause music', 'pausa muzik'],
  'höj volymen': ['raise volume', 'höj volym'],
  'sänk volymen': ['lower volume', 'sänk volym'],
  'vad är klockan': ['what time is it', 'vad är tiden'],
  // Add more as needed
};
```

### Problem: WebRTC Connection Failures

**Symptoms:**
- VoiceClient fails to connect
- "WebRTC setup failed" error
- No OpenAI Realtime connection

**Solutions:**

**1. STUN Server Configuration**
```javascript
// Test different STUN servers
const stunServers = [
  'stun:stun.l.google.com:19302',
  'stun:stun1.l.google.com:19302', 
  'stun:stun2.l.google.com:19302',
  'stun:stun.services.mozilla.com'
];

// Test connectivity
for (const server of stunServers) {
  const pc = new RTCPeerConnection({iceServers: [{urls: server}]});
  // Test connection...
}
```

**2. Network Configuration**
```bash
# Check firewall settings
sudo ufw status

# Common ports to open:
# - 80, 443 (HTTP/HTTPS)
# - 3000 (Frontend)
# - 8000 (Backend)  
# - UDP 1024-65535 (WebRTC)

# Test with different networks
# Corporate networks often block WebRTC
```

**3. Browser-Specific Issues**
```bash
# Chrome WebRTC debug
# Open chrome://webrtc-internals/
# Check for connection errors

# Firefox WebRTC debug  
# Open about:webrtc
# Check ICE connection state

# Safari WebRTC
# May have limited support
# Consider using VoiceBox mode instead
```

## 🔊 **Audio Output Issues**

### Problem: No TTS Audio

**Symptoms:**
- Text appears but no audio
- Silent TTS playback
- Audio initialization errors

**Solutions:**

**1. Audio Device Check**
```javascript
// Browser console test
const audio = new Audio();
audio.src = 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEA...';
audio.play().then(() => {
  console.log('✅ Audio playback working');
}).catch(err => {
  console.log('❌ Audio playback failed:', err);
});
```

**2. Browser Audio Policy**
```javascript
// Must be triggered by user interaction
document.addEventListener('click', async () => {
  try {
    const audioContext = new AudioContext();
    if (audioContext.state === 'suspended') {
      await audioContext.resume();
      console.log('✅ Audio context resumed');
    }
  } catch (err) {
    console.log('❌ Audio context failed:', err);
  }
}, { once: true });
```

**3. TTS Backend Issues**
```bash
# Test TTS endpoint directly
curl -X POST http://localhost:8000/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Test svenska röst",
    "personality": "alice",
    "emotion": "neutral"
  }' | jq '.success'

# Should return: true

# Check TTS model files
ls -la server/models/tts/
# Should show .onnx and .onnx.json files
```

**4. Audio Format Issues**
```javascript
// Test different audio formats
const formats = ['audio/wav', 'audio/mp3', 'audio/ogg'];
formats.forEach(format => {
  const audio = new Audio();
  const canPlay = audio.canPlayType(format);
  console.log(`${format}: ${canPlay}`);
});
```

### Problem: Distorted or Choppy Audio

**Symptoms:**
- Audio cutting out
- Robotic voice quality  
- Delayed audio playback

**Solutions:**

**1. Audio Buffer Optimization**
```javascript
// Increase audio buffer size
const audioContext = new AudioContext({
  sampleRate: 24000,
  latencyHint: 'balanced' // or 'playback' for quality
});
```

**2. Network Quality**
```bash
# Test network latency
ping -c 10 api.openai.com

# Test bandwidth
# Use speedtest.net or similar

# For streaming TTS:
# - Minimum: 1 Mbps upload/download
# - Recommended: 5+ Mbps for WebRTC
```

**3. System Performance**
```bash
# Check CPU usage
top -p $(pgrep -f "python.*run.py")

# Check memory usage
ps aux | grep -E "(python.*run|node.*next)"

# Optimize if needed:
# - Close other applications
# - Use production build (npm run build)
# - Adjust TTS quality settings
```

## 🔑 **API Integration Issues**

### Problem: OpenAI API Errors

**Symptoms:**
- "Failed to create ephemeral session" 
- 401 Unauthorized errors
- Rate limit exceeded

**Solutions:**

**1. API Key Validation**
```bash
# Test API key directly
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Expected: List of available models
# Error: Check API key format and permissions
```

**2. Rate Limiting**
```bash
# Check current usage
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/usage

# Implement rate limiting in code:
# - Retry with exponential backoff
# - Queue requests
# - Use fallback to Alice TTS
```

**3. Model Access**
```bash
# Check Realtime API access
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models/gpt-4o-realtime-preview

# May require:
# - API key with Realtime access
# - Paid OpenAI account
# - Special model permissions
```

**4. Billing Issues**
```bash
# Check billing status
# Visit: https://platform.openai.com/account/billing

# Common issues:
# - Insufficient credits
# - Expired payment method
# - Usage limits exceeded
```

### Problem: Backend Connection Issues

**Symptoms:**
- Frontend can't reach backend
- CORS errors
- 502/503 errors

**Solutions:**

**1. Service Status**
```bash
# Check if backend is running
curl -v http://localhost:8000/api/health

# Check if frontend is running  
curl -v http://localhost:3000

# Check processes
ps aux | grep -E "(python.*run|node.*next)"
```

**2. Port Configuration**
```bash
# Check port conflicts
netstat -tulpn | grep -E ":3000|:8000"

# Change ports if needed:
# Backend: PORT=8001 python run.py
# Frontend: PORT=3000 npm run dev
```

**3. CORS Configuration**
```python
# In backend app.py, ensure CORS is properly configured
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**4. Firewall/Network**
```bash
# Check firewall (Linux)
sudo ufw status
sudo ufw allow 8000/tcp
sudo ufw allow 3000/tcp

# Check firewall (macOS)  
sudo pfctl -s all | grep -E ":3000|:8000"

# Test local connection
telnet localhost 8000
telnet localhost 3000
```

## 🗄️ **Database & Storage Issues**

### Problem: Database Connection Errors

**Symptoms:**
- "Database connection failed"
- Memory/conversation history lost
- TTS cache not working

**Solutions:**

**1. SQLite Issues**
```bash
# Check database file
ls -la server/data/alice.db

# Test database connection
sqlite3 server/data/alice.db ".tables"

# Repair if corrupted
sqlite3 server/data/alice.db ".recover" > alice_recovered.sql
sqlite3 new_alice.db < alice_recovered.sql
```

**2. Permissions Issues**
```bash
# Fix database permissions
chmod 664 server/data/alice.db
chown $USER:$USER server/data/alice.db

# Fix directory permissions
chmod 755 server/data/
```

**3. Disk Space**
```bash
# Check available space
df -h

# Clean up if needed
# - Clear TTS cache: rm -rf server/data/tts_cache/*
# - Clear logs: truncate -s 0 server/server.log
# - Clear browser cache
```

### Problem: TTS Cache Issues

**Symptoms:**
- Slow TTS response times
- Repeated TTS synthesis
- Cache miss errors

**Solutions:**

**1. Cache Configuration**
```bash
# Check cache status
ls -la server/data/tts_cache/

# Clear cache if corrupted
rm -rf server/data/tts_cache/*
mkdir -p server/data/tts_cache/

# Verify cache settings in .env
TTS_CACHE_ENABLED=true
TTS_CACHE_SIZE=1000  # MB
```

**2. Cache Performance**
```python
# Monitor cache hit rate
import sqlite3
conn = sqlite3.connect('server/data/alice.db')
cursor = conn.execute("""
  SELECT 
    COUNT(*) as total_requests,
    SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) as cache_hits
  FROM tts_requests 
  WHERE created_at > datetime('now', '-1 day')
""")
stats = cursor.fetchone()
hit_rate = stats[1] / stats[0] * 100 if stats[0] > 0 else 0
print(f"TTS Cache Hit Rate: {hit_rate:.1f}%")
```

## 🌐 **Browser-Specific Issues**

### Chrome Issues

**Common Problems:**
- Autoplay policy blocks TTS
- CORS errors in development
- WebRTC connection issues

**Solutions:**
```bash
# Chrome flags for development
google-chrome \
  --use-fake-ui-for-media-stream \
  --use-fake-device-for-media-stream \
  --autoplay-policy=no-user-gesture-required \
  --disable-web-security \
  --user-data-dir=/tmp/chrome-dev

# Or add to chrome://flags/:
# - Autoplay policy: No user gesture required
# - Insecure origins treated as secure: http://localhost:3000
```

### Firefox Issues  

**Common Problems:**
- WebRTC may be disabled by default
- Different Speech API behavior
- Stricter security policies

**Solutions:**
```bash
# Firefox about:config settings
# - media.navigator.streams.fake: true (for testing)
# - media.peerconnection.enabled: true
# - media.getusermedia.insecure.enabled: true (for localhost)
```

### Safari Issues

**Common Problems:**
- Limited WebRTC support
- Webkit-specific Speech API
- iOS voice limitations

**Solutions:**
```javascript
// Safari-specific handling
const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
if (isSafari) {
  // Use VoiceBox mode instead of VoiceClient
  // Fallback to browser TTS
  // Handle webkit-prefixed APIs
}
```

## 🔧 **Performance Optimization**

### High CPU Usage

**Diagnosis:**
```bash
# Monitor CPU usage
top -p $(pgrep -f "python.*run.py")
htop  # If available

# Profile Python code
pip install py-spy
py-spy top --pid $(pgrep -f "python.*run.py")
```

**Solutions:**
```bash
# Reduce audio processing
AUDIO_ENHANCEMENT_ENABLED=false
NOISE_REDUCTION=false
ECHO_CANCELLATION=false

# Optimize TTS caching
TTS_CACHE_ENABLED=true
TTS_CACHE_SIZE=2000

# Use production builds
cd web && npm run build && npm run start
```

### Memory Issues

**Diagnosis:**
```bash
# Monitor memory usage
ps aux | grep -E "(python|node)" | sort -k4 -nr

# Check for memory leaks
# Use browser dev tools > Performance tab
# Monitor over time
```

**Solutions:**
```bash
# Limit concurrent connections
# In backend configuration
MAX_WEBSOCKET_CONNECTIONS=10
MAX_CONCURRENT_TTS=3

# Clear caches periodically
# Implement cache rotation
# Monitor and restart services if needed
```

### Network Issues

**Diagnosis:**
```bash
# Test network connectivity
ping -c 5 api.openai.com
curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8000/api/health

# Monitor bandwidth usage
# Use browser dev tools > Network tab
# Check for large/slow requests
```

**Solutions:**
```bash
# Optimize API calls
# - Batch requests when possible  
# - Implement request caching
# - Use compression
# - Reduce audio bitrate for streaming
```

## 📋 **Debugging Tools & Commands**

### Comprehensive Debug Script

```bash
#!/bin/bash
# debug-alice.sh - Complete Alice diagnostics

echo "=== Alice Voice Pipeline Debug Report ==="
echo "Generated: $(date)"
echo

# System info
echo "=== System Information ==="
uname -a
echo "Python: $(python3 --version)"
echo "Node: $(node --version)"
echo "NPM: $(npm --version)"
echo

# Process status
echo "=== Process Status ==="
echo "Alice Backend:"
ps aux | grep -E "python.*run\.py" | grep -v grep
echo "Alice Frontend:"  
ps aux | grep -E "node.*next" | grep -v grep
echo

# Network status
echo "=== Network Status ==="
echo "Port 8000 (Backend):"
netstat -tulpn | grep :8000
echo "Port 3000 (Frontend):"
netstat -tulpn | grep :3000
echo

# Service health
echo "=== Service Health ==="
echo "Backend health:"
curl -s http://localhost:8000/api/health | jq '.' 2>/dev/null || echo "Backend not responding"
echo "Frontend status:"
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "Frontend not responding"
echo

# File system status
echo "=== File System Status ==="
echo "Database files:"
ls -la server/data/*.db 2>/dev/null || echo "No database files found"
echo "TTS models:"
ls -la server/models/tts/ 2>/dev/null || echo "No TTS models found"  
echo "TTS cache:"
du -sh server/data/tts_cache/ 2>/dev/null || echo "No TTS cache found"
echo

# Configuration status
echo "=== Configuration Status ==="
echo "Backend environment:"
grep -E "(OPENAI_API_KEY|VOICE_PIPELINE_MODE|TTS_)" server/.env 2>/dev/null | sed 's/OPENAI_API_KEY=.*/OPENAI_API_KEY=***HIDDEN***/'
echo "Frontend environment:"
grep -E "(OPENAI_API_KEY|VOICE_MODE|ALICE_BACKEND)" web/.env.local 2>/dev/null | sed 's/OPENAI_API_KEY=.*/OPENAI_API_KEY=***HIDDEN***/'
echo

echo "=== End Debug Report ==="
```

### Browser Debug Console Commands

```javascript
// Paste in browser console for comprehensive debugging

window.AliceDebug = {
  // Test voice components
  testVoiceSupport() {
    console.log('=== Voice Support Test ===');
    console.log('WebRTC:', 'RTCPeerConnection' in window);
    console.log('getUserMedia:', navigator.mediaDevices?.getUserMedia !== undefined);
    console.log('AudioContext:', 'AudioContext' in window || 'webkitAudioContext' in window);
    console.log('SpeechRecognition:', 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window);
    console.log('speechSynthesis:', 'speechSynthesis' in window);
  },

  // Test API endpoints
  async testAPIs() {
    console.log('=== API Test ===');
    
    // Backend health
    try {
      const health = await fetch('/api/health');
      console.log('Backend Health:', health.status, await health.json());
    } catch (e) {
      console.log('Backend Health: Failed', e);
    }

    // OpenAI ephemeral
    try {
      const ephemeral = await fetch('/api/realtime/ephemeral');
      console.log('OpenAI Ephemeral:', ephemeral.status);
    } catch (e) {
      console.log('OpenAI Ephemeral: Failed', e);
    }
  },

  // Test audio playback
  async testAudio() {
    console.log('=== Audio Test ===');
    try {
      const tts = await fetch('/api/tts/synthesize', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text: 'Test', personality: 'alice'})
      });
      const data = await tts.json();
      console.log('TTS Test:', data.success);
      
      if (data.success && data.audio_data) {
        const audioBuffer = Uint8Array.from(atob(data.audio_data), c => c.charCodeAt(0));
        const blob = new Blob([audioBuffer], {type: 'audio/wav'});
        const audio = new Audio(URL.createObjectURL(blob));
        await audio.play();
        console.log('Audio Playback: Success');
      }
    } catch (e) {
      console.log('Audio Test: Failed', e);
    }
  },

  // Get full status
  async fullDiagnostic() {
    console.log('=== Alice Full Diagnostic ===');
    this.testVoiceSupport();
    await this.testAPIs();
    await this.testAudio();
    
    // Permissions
    try {
      const mic = await navigator.permissions.query({name: 'microphone'});
      console.log('Microphone Permission:', mic.state);
    } catch (e) {
      console.log('Permission API not supported');
    }
    
    console.log('=== End Diagnostic ===');
  }
};

// Run full diagnostic
AliceDebug.fullDiagnostic();
```

## 📞 **Getting Help**

### Log Collection

Before reporting issues, collect these logs:

```bash
# Backend logs
tail -100 server/server.log > alice-backend.log

# Frontend logs (browser console)
# Open dev tools > Console > Save console output

# System logs
journalctl -u alice-backend --since "1 hour ago" > alice-system.log

# Configuration (redact sensitive info)
env | grep -E "(ALICE|VOICE|OPENAI)" | sed 's/=.*/=***/' > alice-env.txt
```

### Issue Reporting Template

```markdown
**Issue Description:**
Brief description of the problem

**Environment:**
- OS: [Linux/macOS/Windows + version]
- Browser: [Chrome/Firefox/Safari + version]
- Alice Version: [git commit hash]
- Python Version: [python --version]
- Node Version: [node --version]

**Configuration:**
- Voice Mode: [dual/voicebox/voiceclient]  
- OpenAI API: [configured/not configured]
- HTTPS: [enabled/disabled]

**Steps to Reproduce:**
1. Step one
2. Step two
3. Step three

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Error Messages:**
```
Paste any error messages here
```

**Logs:**
Attach log files or paste relevant excerpts

**Additional Context:**
Any other information that might be helpful
```

### Support Resources

- **Documentation**: Check all README files in the repository
- **Issues**: Search existing GitHub issues for similar problems
- **Community**: Alice community forums or Discord
- **Stack Overflow**: Tag questions with `alice-ai` and `voice-pipeline`

---

**For immediate help with common issues, try the Quick Diagnostics section at the top of this guide.**