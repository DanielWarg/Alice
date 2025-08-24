/**
 * Comprehensive Voice Flow Test Script
 * Simulates the entire voice pipeline from button press to output
 * Logs all events to voice-flow-test.jsonl
 */

class VoiceFlowTester {
  constructor() {
    this.logFile = [];
    this.sessionId = `test_${Date.now()}`;
    this.startTime = Date.now();
  }

  log(event, data = {}) {
    const logEntry = {
      timestamp: Date.now(),
      elapsed_ms: Date.now() - this.startTime,
      session_id: this.sessionId,
      event,
      ...data
    };
    
    this.logFile.push(logEntry);
    console.log(`📝 [${logEntry.elapsed_ms}ms] ${event}:`, data);
  }

  async saveLog() {
    const jsonlContent = this.logFile
      .map(entry => JSON.stringify(entry))
      .join('\n');
    
    // Create a downloadable blob for browser
    const blob = new Blob([jsonlContent], { type: 'application/jsonl' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'voice-flow-test.jsonl';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    console.log('💾 Log file saved as voice-flow-test.jsonl');
  }

  async testFullVoiceFlow() {
    this.log('test_start', {
      user_agent: navigator.userAgent,
      url: window.location.href,
      timestamp_iso: new Date().toISOString()
    });

    // Phase 1: Test environment setup
    await this.testEnvironment();
    
    // Phase 2: Test WebSocket connection
    await this.testWebSocketConnection();
    
    // Phase 3: Test mic button interaction
    await this.testMicButtonInteraction();
    
    // Phase 4: Test audio flow (if possible)
    await this.testAudioFlow();
    
    // Phase 5: Test backend integration
    await this.testBackendIntegration();

    this.log('test_complete');
    await this.saveLog();
  }

  async testEnvironment() {
    this.log('environment_check_start');
    
    // Check if required components exist
    const micButton = document.querySelector('[data-testid="mic-button"]') || 
                     document.querySelector('button[aria-label="Mikrofon"]') ||
                     document.querySelector('.mic-button') ||
                     document.querySelector('button:has(svg)');
    
    this.log('mic_button_check', {
      found: !!micButton,
      element: micButton?.tagName,
      classes: micButton?.className,
      aria_label: micButton?.getAttribute('aria-label')
    });

    // Check environment variables
    const envVars = {
      NEXT_PUBLIC_API_BASE: window.location.origin, // Since it's client-side
      NEXT_PUBLIC_VOICE_WS_BASE: 'ws://127.0.0.1:8000',
      NEXT_PUBLIC_BACKEND_PORT: '8000'
    };
    
    this.log('environment_vars', envVars);

    // Check WebSocket support
    this.log('websocket_support', {
      supported: typeof WebSocket !== 'undefined',
      constructor: WebSocket?.name
    });

    // Check speech recognition support
    this.log('speech_recognition_support', {
      webkitSpeechRecognition: typeof webkitSpeechRecognition !== 'undefined',
      SpeechRecognition: typeof SpeechRecognition !== 'undefined'
    });
  }

  async testWebSocketConnection() {
    this.log('websocket_test_start');
    
    return new Promise((resolve) => {
      const wsUrl = `ws://127.0.0.1:8000/ws/voice-gateway/${this.sessionId}`;
      this.log('websocket_url_constructed', { url: wsUrl });

      const ws = new WebSocket(wsUrl);
      let connectionStartTime = Date.now();

      ws.onopen = (event) => {
        const connectionTime = Date.now() - connectionStartTime;
        this.log('websocket_connected', { 
          connection_time_ms: connectionTime,
          ready_state: ws.readyState
        });

        // Send test ping
        const pingData = { type: 'ping', ts: Date.now(), test: true };
        ws.send(JSON.stringify(pingData));
        this.log('websocket_ping_sent', pingData);

        // Close after test
        setTimeout(() => {
          ws.close(1000, 'test-complete');
        }, 1000);
      };

      ws.onmessage = (event) => {
        let messageData;
        try {
          messageData = JSON.parse(event.data);
        } catch (e) {
          messageData = event.data;
        }
        this.log('websocket_message_received', { 
          data: messageData,
          size: event.data.length
        });
      };

      ws.onerror = (event) => {
        this.log('websocket_error', { 
          error: event.type,
          ready_state: ws.readyState
        });
      };

      ws.onclose = (event) => {
        this.log('websocket_closed', { 
          code: event.code,
          reason: event.reason,
          was_clean: event.wasClean
        });
        resolve();
      };

      // Timeout fallback
      setTimeout(() => {
        if (ws.readyState !== WebSocket.CLOSED) {
          this.log('websocket_timeout');
          ws.close();
        }
        resolve();
      }, 5000);
    });
  }

  async testMicButtonInteraction() {
    this.log('mic_button_test_start');
    
    // Try to find mic button with various selectors
    const selectors = [
      '[data-testid="mic-button"]',
      'button[aria-label="Mikrofon"]',
      '.mic-button',
      'button:has(svg)',
      'button:has(.mic-icon)',
      '[class*="mic"]',
      '[id*="mic"]'
    ];

    let micButton = null;
    for (const selector of selectors) {
      try {
        micButton = document.querySelector(selector);
        if (micButton) {
          this.log('mic_button_found', { selector, element: micButton.tagName });
          break;
        }
      } catch (e) {
        this.log('selector_error', { selector, error: e.message });
      }
    }

    if (!micButton) {
      // Try to find by text content or SVG
      const buttons = document.querySelectorAll('button');
      for (const btn of buttons) {
        if (btn.querySelector('svg') || 
            btn.textContent.toLowerCase().includes('mic') ||
            btn.className.toLowerCase().includes('mic')) {
          micButton = btn;
          this.log('mic_button_found_by_content', { 
            text: btn.textContent,
            classes: btn.className
          });
          break;
        }
      }
    }

    if (micButton) {
      // Test button click
      this.log('mic_button_click_attempt');
      
      // Listen for any state changes
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          this.log('dom_mutation', {
            type: mutation.type,
            target: mutation.target.tagName,
            attribute: mutation.attributeName,
            old_value: mutation.oldValue,
            new_value: mutation.target.getAttribute?.(mutation.attributeName)
          });
        });
      });

      observer.observe(document.body, {
        attributes: true,
        childList: true,
        subtree: true,
        attributeOldValue: true
      });

      // Simulate click
      try {
        micButton.click();
        this.log('mic_button_clicked');
        
        // Wait for potential state changes
        await new Promise(resolve => setTimeout(resolve, 2000));
        
      } catch (e) {
        this.log('mic_button_click_error', { error: e.message });
      } finally {
        observer.disconnect();
      }
    } else {
      this.log('mic_button_not_found');
    }
  }

  async testAudioFlow() {
    this.log('audio_flow_test_start');

    // Test getUserMedia support
    if (navigator.mediaDevices?.getUserMedia) {
      try {
        this.log('requesting_microphone_permission');
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.log('microphone_access_granted', {
          tracks: stream.getAudioTracks().length,
          track_settings: stream.getAudioTracks()[0]?.getSettings()
        });
        
        // Stop the stream immediately
        stream.getTracks().forEach(track => track.stop());
        this.log('microphone_stream_stopped');
        
      } catch (e) {
        this.log('microphone_access_error', { error: e.message, name: e.name });
      }
    } else {
      this.log('getusermedia_not_supported');
    }

    // Test Web Speech API
    if (typeof webkitSpeechRecognition !== 'undefined' || typeof SpeechRecognition !== 'undefined') {
      this.log('speech_recognition_available');
      
      try {
        const SpeechRecog = webkitSpeechRecognition || SpeechRecognition;
        const recognition = new SpeechRecog();
        recognition.lang = 'sv-SE';
        recognition.continuous = false;
        recognition.interimResults = false;

        this.log('speech_recognition_configured', {
          lang: recognition.lang,
          continuous: recognition.continuous,
          interim_results: recognition.interimResults
        });

      } catch (e) {
        this.log('speech_recognition_error', { error: e.message });
      }
    } else {
      this.log('speech_recognition_not_supported');
    }
  }

  async testBackendIntegration() {
    this.log('backend_test_start');

    // Test API endpoints
    const endpoints = [
      'http://127.0.0.1:8000/health',
      'http://127.0.0.1:8000/api/alice/command',
      'http://127.0.0.1:8000/docs'
    ];

    for (const endpoint of endpoints) {
      try {
        this.log('testing_endpoint', { url: endpoint });
        const startTime = Date.now();
        
        const response = await fetch(endpoint, {
          method: endpoint.includes('/command') ? 'POST' : 'GET',
          headers: endpoint.includes('/command') ? {
            'Content-Type': 'application/json'
          } : {},
          body: endpoint.includes('/command') ? JSON.stringify({
            text: "test message",
            session_id: this.sessionId
          }) : undefined
        });

        const responseTime = Date.now() - startTime;
        const contentType = response.headers.get('content-type');
        
        let responseData = null;
        try {
          if (contentType?.includes('application/json')) {
            responseData = await response.json();
          } else {
            responseData = await response.text();
          }
        } catch (e) {
          responseData = `Error reading response: ${e.message}`;
        }

        this.log('endpoint_response', {
          url: endpoint,
          status: response.status,
          status_text: response.statusText,
          response_time_ms: responseTime,
          content_type: contentType,
          data: responseData
        });

      } catch (e) {
        this.log('endpoint_error', {
          url: endpoint,
          error: e.message,
          name: e.name
        });
      }
    }
  }
}

// Auto-start test when script loads
const tester = new VoiceFlowTester();

// Export for manual use
window.voiceFlowTester = tester;

// Start test automatically
console.log('🎯 Starting Voice Flow Test...');
console.log('📝 Results will be logged to voice-flow-test.jsonl');
console.log('🔗 Access tester manually via: window.voiceFlowTester');

tester.testFullVoiceFlow().catch(error => {
  tester.log('test_fatal_error', { error: error.message, stack: error.stack });
  tester.saveLog();
});