---
name: 🎤 Voice & Audio Issue
about: Report issues with voice recognition, TTS, or audio functionality
title: '[VOICE] '
labels: ['voice', 'audio', 'needs-triage']
assignees: ''
---

## 🎤 Voice Issue Summary
A clear description of the voice/audio problem you're experiencing.

## 🔧 Voice Pipeline Configuration
**Pipeline Mode:** [dual/voicebox/voiceclient]
**Voice System:** [OpenAI Realtime/Local TTS/Hybrid]
**Audio Backend:** [WebRTC/WebAudio/MediaDevices]

## 🎯 Issue Type
- [ ] 👂 **Speech Recognition (STT)** - Alice doesn't understand my voice
- [ ] 🗣️ **Text-to-Speech (TTS)** - Alice's voice output issues
- [ ] 🔊 **Audio Quality** - Distorted, choppy, or unclear audio
- [ ] ⚡ **Latency Issues** - Delays in voice processing
- [ ] 🎵 **Audio Interruption** - Cutting off or breaking audio
- [ ] 🔇 **No Audio** - Complete silence or no response
- [ ] 🎚️ **Volume/Gain Issues** - Too quiet, too loud, or inconsistent
- [ ] 🌐 **WebRTC Connection** - Real-time communication problems
- [ ] 🇸🇪 **Swedish Language** - Language-specific voice issues

## 🗣️ Speech Recognition Details (if STT issue)
**What you said:** ___________
**Language:** [Swedish/English/Other]
**Accent/Dialect:** [Stockholm/Gothenburg/Malmö/Other/Non-native]
**What Alice heard:** ___________
**Expected interpretation:** ___________

**Voice Characteristics:**
- **Speaking speed:** [Fast/Normal/Slow]
- **Volume level:** [Quiet/Normal/Loud]
- **Background noise:** [Silent/Quiet/Noisy]
- **Speaking style:** [Clear/Casual/Mumbled]

## 🔊 Text-to-Speech Details (if TTS issue)
**Text Alice tried to say:** ___________
**Expected voice:** [Swedish Female/Swedish Male/Other]
**Actual behavior:** [Silent/Distorted/Wrong language/Other]
**Voice personality:** [Standard/Professional/Friendly]

## 🎧 Audio Setup
**Microphone:**
- Type: [Built-in/USB/Bluetooth/Headset]
- Model: ___________
- Working in other apps: [Yes/No]

**Speakers/Headphones:**
- Type: [Built-in/USB/Bluetooth/Headset]
- Model: ___________
- Working with other apps: [Yes/No]

**Audio Permissions:**
- [ ] Browser microphone permission granted
- [ ] Browser speaker permission granted
- [ ] OS-level audio permissions granted

## 🌐 Browser & Network
**Browser:** [Chrome/Safari/Firefox/Edge] version ___________
**Connection:** [WiFi/Ethernet/Mobile data]
**Speed:** [Fast/Medium/Slow]
**Behind firewall/proxy:** [Yes/No]
**HTTPS enabled:** [Yes/No]

## 📊 Audio Quality Metrics
**Voice Activity Detection:** [Working/Not working/Intermittent]
**Wake Word Detection:** [Working/Not working/False positives]
**Background Noise:** [None/Low/Medium/High]
**Echo/Feedback:** [None/Slight/Noticeable/Severe]

## 🔧 Technical Diagnostics

### Browser Console Errors
```
Please paste any browser console errors related to audio/voice
```

### Server Logs
```
Please paste any server logs during the voice issue
```

### Network Debug
**WebRTC Status:** [Connected/Disconnected/Failed]
**WebSocket Status:** [Connected/Disconnected/Reconnecting]
**Audio Stream Status:** [Active/Inactive/Error]

## 🧪 Testing Steps
**Steps to reproduce:**
1. 
2. 
3. 

**Frequency:** [Always/Sometimes/Rarely/Once]
**Time of day:** [Morning/Afternoon/Evening/Night]
**Duration before issue:** [Immediate/After 5min/After 30min/Random]

## 🎛️ Workarounds Tried
- [ ] Refreshed the page
- [ ] Restarted browser
- [ ] Cleared browser cache
- [ ] Disabled browser extensions
- [ ] Tried different microphone
- [ ] Tried different speakers
- [ ] Tested in private/incognito mode
- [ ] Restarted Alice server
- [ ] Checked audio permissions

## 🇸🇪 Swedish Voice Specifics
**Swedish phrases that fail:** ___________
**Swedish pronunciation issues:** ___________
**Regional dialect:** [Stockholm/West Coast/South/North/Finland-Swedish]
**Swedish cultural context:** ___________

## 📱 Environment Details
**OS:** ___________
**Alice Version:** ___________
**Ollama Version:** ___________
**OpenAI API:** [Enabled/Disabled]
**Voice Models:** [Piper-TTS/OpenAI-Voice/Both]

## ⚡ Performance Impact
**CPU usage during voice:** [Low/Medium/High]
**Memory usage:** [Low/Medium/High]
**Battery drain:** [Normal/Increased/Severe]
**Other apps affected:** [Yes/No]

## 🔊 Audio Sample (Optional)
If possible, please provide:
- [ ] Recording of what you said
- [ ] Recording of Alice's response
- [ ] Screenshot of browser audio settings

## ✅ Troubleshooting Checklist
- [ ] Audio works in other applications
- [ ] Browser permissions are granted
- [ ] No other audio applications are interfering
- [ ] Alice server is running without errors
- [ ] Internet connection is stable
- [ ] Using supported browser (Chrome/Safari/Firefox)
- [ ] Tested with different voice commands

## 🎯 Expected Behavior
Describe what should happen with voice/audio:

## 📝 Additional Context
Any other relevant information about your voice/audio setup or usage patterns: