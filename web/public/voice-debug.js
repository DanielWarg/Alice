// Alice Voice System Debug Script
// Paste this script into the browser console to debug voice issues

console.log('=== ALICE VOICE DEBUG SCRIPT ===');

// 1. Check browser compatibility
console.log('1. Browser Compatibility Check:');
const browserCheck = {
  userAgent: navigator.userAgent,
  platform: navigator.platform,
  language: navigator.language,
  languages: navigator.languages,
  isSecureContext: window.isSecureContext,
  protocol: window.location.protocol,
  hostname: window.location.hostname,
  port: window.location.port,
  webkitSpeechRecognition: !!(window.webkitSpeechRecognition),
  SpeechRecognition: !!(window.SpeechRecognition),
  mediaDevices: !!(navigator.mediaDevices),
  getUserMedia: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
};
console.table(browserCheck);

// 2. Test microphone access
console.log('2. Testing Microphone Access:');
if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      console.log('✅ Microphone access granted:', {
        audioTracks: stream.getAudioTracks().length,
        trackSettings: stream.getAudioTracks()[0]?.getSettings(),
        trackCapabilities: stream.getAudioTracks()[0]?.getCapabilities()
      });
      // Stop the stream to free up the microphone
      stream.getTracks().forEach(track => track.stop());
    })
    .catch(error => {
      console.error('❌ Microphone access denied:', {
        name: error.name,
        message: error.message,
        constraint: error.constraint
      });
    });
} else {
  console.error('❌ getUserMedia not supported');
}

// 3. Test Speech Recognition
console.log('3. Testing Speech Recognition:');
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
  try {
    const recognition = new SpeechRecognition();
    console.log('✅ Speech Recognition created:', {
      continuous: recognition.continuous,
      interimResults: recognition.interimResults,
      lang: recognition.lang,
      maxAlternatives: recognition.maxAlternatives,
      serviceURI: recognition.serviceURI,
      grammars: recognition.grammars
    });
    
    // Test properties
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'sv-SE';
    recognition.maxAlternatives = 1;
    
    console.log('Properties set successfully:', {
      continuous: recognition.continuous,
      interimResults: recognition.interimResults,
      lang: recognition.lang,
      maxAlternatives: recognition.maxAlternatives
    });
    
  } catch (error) {
    console.error('❌ Failed to create Speech Recognition:', {
      name: error.name,
      message: error.message,
      stack: error.stack
    });
  }
} else {
  console.error('❌ Speech Recognition not supported');
}

// 4. Test backend connectivity
console.log('4. Testing Backend Connectivity:');
const testEndpoints = [
  'http://127.0.0.1:8000/api/alice/command',
  'http://127.0.0.1:8000/api/chat',
  'http://127.0.0.1:8000/api/ai/media_act'
];

testEndpoints.forEach(url => {
  fetch(url, { 
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: 'debug test', type: 'debug' })
  })
  .then(response => {
    console.log(`✅ ${url} - Status: ${response.status} ${response.statusText}`);
    return response.json();
  })
  .then(data => {
    console.log(`✅ ${url} - Response:`, data);
  })
  .catch(error => {
    console.error(`❌ ${url} - Error:`, {
      name: error.name,
      message: error.message,
      stack: error.stack.substring(0, 200)
    });
  });
});

// 5. Check CSP (Content Security Policy)
console.log('5. Content Security Policy Check:');
const metaTags = Array.from(document.querySelectorAll('meta')).map(meta => ({
  name: meta.name,
  content: meta.content,
  'http-equiv': meta.httpEquiv
}));
console.log('Meta tags:', metaTags);

// 6. VoiceBox component state check
console.log('6. VoiceBox Component State Check:');
setTimeout(() => {
  // Try to find VoiceBox related elements
  const micButton = document.querySelector('button[title*="inspelning"], button[title*="recording"], .mic-button, [data-testid="mic-button"]');
  const voiceBox = document.querySelector('.voice-box, [data-testid="voice-box"]');
  
  console.log('VoiceBox Elements Found:', {
    micButton: !!micButton,
    voiceBox: !!voiceBox,
    micButtonDetails: micButton ? {
      tagName: micButton.tagName,
      className: micButton.className,
      title: micButton.title,
      disabled: micButton.disabled
    } : null
  });
}, 1000);

// 7. Performance and memory check
console.log('7. Performance Check:');
console.log('Memory:', {
  usedJSHeapSize: (performance as any).memory?.usedJSHeapSize,
  totalJSHeapSize: (performance as any).memory?.totalJSHeapSize,
  jsHeapSizeLimit: (performance as any).memory?.jsHeapSizeLimit
});

console.log('=== DEBUG SCRIPT COMPLETED ===');
console.log('Check the results above for any ❌ errors that need to be fixed.');
console.log('To test live voice recognition, click the microphone button and speak in Swedish.');