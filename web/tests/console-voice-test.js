// Quick Console Voice Test - Paste this into browser console
console.log('🎯 Starting Quick Voice Test...');

const sessionId = `console_test_${Date.now()}`;
const logs = [];

function log(event, data = {}) {
  const entry = {
    timestamp: Date.now(),
    event,
    ...data
  };
  logs.push(entry);
  console.log(`📝 ${event}:`, data);
}

// Test 1: Check if VoiceGateway components exist
log('checking_voice_components');
const voiceBox = document.querySelector('[class*="VoiceBox"]') || document.querySelector('[class*="voice"]');
log('voicebox_found', { found: !!voiceBox, element: voiceBox?.className });

// Test 2: Look for mic button
const micSelectors = ['[data-testid="mic-button"]', 'button[aria-label*="ikrofon"]', '.mic-button', 'button:has(svg)'];
let micButton = null;

for (const selector of micSelectors) {
  try {
    micButton = document.querySelector(selector);
    if (micButton) {
      log('mic_button_found', { selector, classes: micButton.className });
      break;
    }
  } catch (e) {
    // Skip invalid selectors
  }
}

if (!micButton) {
  // Search by SVG content or classes
  const buttons = Array.from(document.querySelectorAll('button'));
  micButton = buttons.find(btn => 
    btn.querySelector('svg') || 
    btn.className.toLowerCase().includes('mic') ||
    btn.textContent.toLowerCase().includes('mic')
  );
  log('mic_button_found_by_search', { found: !!micButton });
}

// Test 3: WebSocket connection test
log('testing_websocket');
const wsUrl = `ws://127.0.0.1:8000/ws/voice-gateway/${sessionId}`;
const testWs = new WebSocket(wsUrl);

testWs.onopen = () => {
  log('websocket_connected');
  testWs.send(JSON.stringify({ type: 'ping', test: true }));
  setTimeout(() => testWs.close(), 1000);
};

testWs.onmessage = (event) => {
  log('websocket_message', { data: event.data });
};

testWs.onerror = (event) => {
  log('websocket_error', { type: event.type });
};

testWs.onclose = (event) => {
  log('websocket_closed', { code: event.code, reason: event.reason });
};

// Test 4: Try clicking mic button if found
if (micButton) {
  setTimeout(() => {
    log('clicking_mic_button');
    
    // Set up mutation observer to catch state changes
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        log('dom_change', {
          type: mutation.type,
          target: mutation.target.tagName,
          attribute: mutation.attributeName
        });
      });
    });
    
    observer.observe(document.body, { attributes: true, subtree: true });
    
    try {
      micButton.click();
      log('mic_button_clicked');
    } catch (e) {
      log('mic_click_error', { error: e.message });
    }
    
    setTimeout(() => {
      observer.disconnect();
      log('test_complete');
      
      // Output JSONL
      console.log('\n📋 Test Results (JSONL format):');
      logs.forEach(entry => console.log(JSON.stringify(entry)));
      
      // Create downloadable log
      const jsonl = logs.map(entry => JSON.stringify(entry)).join('\n');
      const blob = new Blob([jsonl], { type: 'application/jsonl' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'console-voice-test.jsonl';
      a.click();
      URL.revokeObjectURL(url);
      
    }, 3000);
    
  }, 2000);
}

// Test 5: Backend connectivity
log('testing_backend_endpoints');
fetch('http://127.0.0.1:8000/health')
  .then(r => r.json())
  .then(data => log('backend_health', data))
  .catch(e => log('backend_health_error', { error: e.message }));

setTimeout(() => {
  if (logs.length === 0) {
    console.log('❌ No logs generated - something went wrong');
  }
}, 5000);