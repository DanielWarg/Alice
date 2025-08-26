/**
 * Complete End-to-End Voice Flow Test with JSONL Logging
 * Simulates: Button Click → WebSocket → Speech Recognition → Backend → TTS → Output
 */

class VoiceEndToEndTester {
  constructor() {
    this.logs = []
    this.sessionId = `e2e_test_${Date.now()}`
    this.startTime = Date.now()
    this.testPhase = 'initializing'
  }

  log(level, event, data = {}) {
    const entry = {
      timestamp: Date.now(),
      iso_timestamp: new Date().toISOString(),
      elapsed_ms: Date.now() - this.startTime,
      session_id: this.sessionId,
      test_phase: this.testPhase,
      level,
      event,
      url: window.location.href,
      user_agent: navigator.userAgent.split(' ')[0],
      ...data
    }
    
    this.logs.push(entry)
    
    const emoji = level === 'error' ? '❌' : level === 'warn' ? '⚠️' : level === 'success' ? '✅' : '📝'
    console.log(`${emoji} [${entry.elapsed_ms}ms] ${event}`, data)
  }

  async saveJsonlLog() {
    const jsonlContent = this.logs
      .map(entry => JSON.stringify(entry))
      .join('\n')
    
    // Download file
    const blob = new Blob([jsonlContent], { type: 'application/jsonl' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `voice-e2e-test-${this.sessionId}.jsonl`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    this.log('info', 'jsonl_log_saved', { 
      entries: this.logs.length,
      filename: `voice-e2e-test-${this.sessionId}.jsonl`
    })
  }

  async runCompleteTest() {
    this.log('info', 'test_suite_started')
    
    try {
      await this.phase1_environment()
      await this.phase2_backend_connectivity()
      await this.phase3_websocket_connection()
      await this.phase4_mic_button_simulation()
      await this.phase5_speech_recognition()
      await this.phase6_alice_command()
      await this.phase7_tts_response()
      
      this.log('success', 'test_suite_completed')
      
    } catch (error) {
      this.log('error', 'test_suite_failed', {
        error: error.message,
        stack: error.stack?.substring(0, 300)
      })
    } finally {
      await this.saveJsonlLog()
    }
  }

  async phase1_environment() {
    this.testPhase = 'environment_check'
    this.log('info', 'phase1_environment_check_started')
    
    // Check browser capabilities
    const capabilities = {
      getUserMedia: !!(navigator.mediaDevices?.getUserMedia),
      webSocket: typeof WebSocket !== 'undefined',
      speechRecognition: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
      speechSynthesis: !!(window.speechSynthesis),
      audioContext: !!(window.AudioContext || window.webkitAudioContext),
      fetch: typeof fetch !== 'undefined',
      isSecureContext: window.isSecureContext,
      protocol: window.location.protocol,
      hostname: window.location.hostname
    }
    
    this.log('info', 'browser_capabilities', capabilities)
    
    // Check DOM elements
    const micButton = this.findMicButton()
    const voiceBox = document.querySelector('[data-testid="voice-box-container"]')
    
    this.log('info', 'dom_elements', {
      mic_button_found: !!micButton,
      mic_button_classes: micButton?.className,
      voice_box_found: !!voiceBox,
      voice_box_classes: voiceBox?.className
    })
    
    // Check environment variables
    const envCheck = {
      nextPublicApiBase: process.env.NEXT_PUBLIC_API_BASE || 'not_set',
      nextPublicVoiceWsBase: process.env.NEXT_PUBLIC_VOICE_WS_BASE || 'not_set',
      nextPublicBackendPort: process.env.NEXT_PUBLIC_BACKEND_PORT || 'not_set'
    }
    
    this.log('info', 'environment_variables', envCheck)
    
    this.log('success', 'phase1_environment_check_completed')
  }

  async phase2_backend_connectivity() {
    this.testPhase = 'backend_connectivity'
    this.log('info', 'phase2_backend_connectivity_started')
    
    const endpoints = [
      { name: 'health', url: 'http://127.0.0.1:8000/api/health', method: 'GET' },
      { name: 'docs', url: 'http://127.0.0.1:8000/docs', method: 'GET' },
      { name: 'alice_command', url: 'http://127.0.0.1:8000/api/alice/command', method: 'POST' }
    ]
    
    for (const endpoint of endpoints) {
      try {
        const startTime = Date.now()
        
        const options = {
          method: endpoint.method,
          headers: endpoint.method === 'POST' ? { 'Content-Type': 'application/json' } : {},
          body: endpoint.method === 'POST' ? JSON.stringify({
            text: 'test connection',
            session_id: this.sessionId
          }) : undefined
        }
        
        const response = await fetch(endpoint.url, options)
        const responseTime = Date.now() - startTime
        
        let responseData = 'non_json'
        let responseSize = 0
        
        try {
          const text = await response.text()
          responseSize = text.length
          
          if (response.headers.get('content-type')?.includes('application/json')) {
            responseData = JSON.parse(text)
          } else {
            responseData = text.substring(0, 100) + (text.length > 100 ? '...' : '')
          }
        } catch (e) {
          responseData = `parse_error: ${e.message}`
        }
        
        this.log('info', 'endpoint_response', {
          endpoint: endpoint.name,
          url: endpoint.url,
          method: endpoint.method,
          status: response.status,
          status_text: response.statusText,
          response_time_ms: responseTime,
          content_type: response.headers.get('content-type'),
          response_size_bytes: responseSize,
          data: responseData
        })
        
      } catch (error) {
        this.log('error', 'endpoint_error', {
          endpoint: endpoint.name,
          url: endpoint.url,
          error: error.message,
          error_name: error.name
        })
      }
    }
    
    this.log('success', 'phase2_backend_connectivity_completed')
  }

  async phase3_websocket_connection() {
    this.testPhase = 'websocket_connection'
    this.log('info', 'phase3_websocket_connection_started')
    
    return new Promise((resolve) => {
      const wsUrl = `ws://127.0.0.1:8000/ws/alice`
      this.log('info', 'websocket_connecting', { url: wsUrl })
      
      const ws = new WebSocket(wsUrl)
      const connectionStartTime = Date.now()
      let messageCount = 0
      
      const cleanup = () => {
        try { ws.close() } catch (e) {}
        resolve()
      }
      
      ws.onopen = () => {
        const connectionTime = Date.now() - connectionStartTime
        this.log('success', 'websocket_connected', {
          connection_time_ms: connectionTime,
          ready_state: ws.readyState,
          protocol: ws.protocol,
          extensions: ws.extensions
        })
        
        // Send test messages
        const testMessages = [
          { type: 'ping', ts: Date.now(), test: 'connection_test' },
          { type: 'audio_chunk', data: 'test_audio_data' },
          { type: 'voice_command', text: 'hej Alice' }
        ]
        
        testMessages.forEach((msg, i) => {
          setTimeout(() => {
            try {
              ws.send(JSON.stringify(msg))
              this.log('info', 'websocket_message_sent', { 
                message: msg,
                message_number: i + 1
              })
            } catch (e) {
              this.log('error', 'websocket_send_error', { error: e.message, message: msg })
            }
          }, i * 500)
        })
        
        // Close after tests
        setTimeout(cleanup, 3000)
      }
      
      ws.onmessage = (event) => {
        messageCount++
        let messageData = event.data
        
        try {
          messageData = JSON.parse(event.data)
        } catch (e) {
          // Keep as string
        }
        
        this.log('info', 'websocket_message_received', {
          message_number: messageCount,
          data: messageData,
          size_bytes: event.data.length,
          timestamp: Date.now()
        })
      }
      
      ws.onerror = (event) => {
        this.log('error', 'websocket_error', {
          error_type: event.type,
          ready_state: ws.readyState,
          url: wsUrl
        })
      }
      
      ws.onclose = (event) => {
        this.log('info', 'websocket_closed', {
          code: event.code,
          reason: event.reason,
          was_clean: event.wasClean,
          messages_received: messageCount
        })
        
        this.log('success', 'phase3_websocket_connection_completed')
        cleanup()
      }
      
      // Timeout fallback
      setTimeout(() => {
        if (ws.readyState !== WebSocket.CLOSED) {
          this.log('warn', 'websocket_timeout')
          cleanup()
        }
      }, 5000)
    })
  }

  findMicButton() {
    const selectors = [
      '[data-testid="mic-button"]',
      'button[title*="röstgateway"]',
      'button[title*="mikrofon"]',
      '.mic-button'
    ]
    
    for (const selector of selectors) {
      const btn = document.querySelector(selector)
      if (btn) return btn
    }
    
    // Search by SVG content
    const buttons = Array.from(document.querySelectorAll('button'))
    return buttons.find(btn => {
      const svg = btn.querySelector('svg')
      if (!svg) return false
      
      const paths = Array.from(svg.querySelectorAll('path'))
      return paths.some(path => 
        path.getAttribute('d')?.includes('M12 2a3 3 0 0 0-3 3v7') // Microphone path
      )
    })
  }

  async phase4_mic_button_simulation() {
    this.testPhase = 'mic_button_simulation'
    this.log('info', 'phase4_mic_button_simulation_started')
    
    const micButton = this.findMicButton()
    
    if (!micButton) {
      this.log('error', 'mic_button_not_found')
      return
    }
    
    this.log('info', 'mic_button_found', {
      tag: micButton.tagName,
      classes: micButton.className,
      title: micButton.title,
      aria_label: micButton.getAttribute('aria-label'),
      text_content: micButton.textContent.trim(),
      has_svg: !!micButton.querySelector('svg')
    })
    
    // Set up mutation observer to track state changes
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        this.log('info', 'dom_mutation_observed', {
          type: mutation.type,
          target: mutation.target.tagName,
          attribute: mutation.attributeName,
          old_value: mutation.oldValue,
          new_value: mutation.target.getAttribute?.(mutation.attributeName)
        })
      })
    })
    
    observer.observe(document.body, {
      attributes: true,
      childList: true,
      subtree: true,
      attributeOldValue: true
    })
    
    // Simulate click
    try {
      this.log('info', 'mic_button_click_attempting')
      micButton.click()
      this.log('success', 'mic_button_clicked')
      
      // Wait for potential state changes
      await new Promise(resolve => setTimeout(resolve, 3000))
      
    } catch (error) {
      this.log('error', 'mic_button_click_failed', { error: error.message })
    } finally {
      observer.disconnect()
    }
    
    this.log('success', 'phase4_mic_button_simulation_completed')
  }

  async phase5_speech_recognition() {
    this.testPhase = 'speech_recognition'
    this.log('info', 'phase5_speech_recognition_started')
    
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition
    
    if (!SpeechRec) {
      this.log('error', 'speech_recognition_not_supported')
      return
    }
    
    return new Promise((resolve) => {
      try {
        const recognition = new SpeechRec()
        
        const config = {
          continuous: true,
          interimResults: true,
          lang: 'sv-SE',
          maxAlternatives: 1
        }
        
        Object.assign(recognition, config)
        
        this.log('info', 'speech_recognition_configured', config)
        
        let resultCount = 0
        const timeout = setTimeout(() => {
          recognition.stop()
          this.log('warn', 'speech_recognition_timeout')
          resolve()
        }, 5000)
        
        recognition.onstart = () => {
          this.log('success', 'speech_recognition_started')
        }
        
        recognition.onend = () => {
          clearTimeout(timeout)
          this.log('info', 'speech_recognition_ended', { results_received: resultCount })
          this.log('success', 'phase5_speech_recognition_completed')
          resolve()
        }
        
        recognition.onerror = (event) => {
          clearTimeout(timeout)
          this.log('error', 'speech_recognition_error', {
            error: event.error,
            message: event.message,
            timestamp: event.timeStamp
          })
          resolve()
        }
        
        recognition.onresult = (event) => {
          resultCount++
          const result = event.results[event.results.length - 1]
          
          this.log('info', 'speech_recognition_result', {
            result_number: resultCount,
            transcript: result[0]?.transcript,
            confidence: result[0]?.confidence,
            is_final: result.isFinal,
            alternatives: result.length
          })
        }
        
        recognition.start()
        
      } catch (error) {
        this.log('error', 'speech_recognition_setup_failed', {
          error: error.message,
          stack: error.stack?.substring(0, 200)
        })
        resolve()
      }
    })
  }

  async phase6_alice_command() {
    this.testPhase = 'alice_command'
    this.log('info', 'phase6_alice_command_started')
    
    const testCommand = 'Hej Alice, vad är klockan?'
    
    try {
      const startTime = Date.now()
      const response = await fetch('http://127.0.0.1:8000/api/alice/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: testCommand,
          session_id: this.sessionId,
          timestamp: new Date().toISOString()
        })
      })
      
      const responseTime = Date.now() - startTime
      
      let responseData = null
      try {
        responseData = await response.json()
      } catch (e) {
        responseData = await response.text()
      }
      
      this.log('info', 'alice_command_response', {
        command: testCommand,
        status: response.status,
        status_text: response.statusText,
        response_time_ms: responseTime,
        response_data: responseData
      })
      
      if (response.ok) {
        this.log('success', 'alice_command_successful')
      } else {
        this.log('error', 'alice_command_failed', { status: response.status })
      }
      
    } catch (error) {
      this.log('error', 'alice_command_error', {
        command: testCommand,
        error: error.message,
        error_name: error.name
      })
    }
    
    this.log('success', 'phase6_alice_command_completed')
  }

  async phase7_tts_response() {
    this.testPhase = 'tts_response'
    this.log('info', 'phase7_tts_response_started')
    
    const testText = 'Hej! Jag är Alice, din svenska AI-assistent.'
    
    // Test enhanced TTS
    try {
      const response = await fetch('http://127.0.0.1:8000/api/tts/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: testText,
          personality: 'alice',
          emotion: 'friendly',
          voice: 'sv_SE-nst-medium',
          cache: true
        })
      })
      
      if (response.ok) {
        const ttsData = await response.json()
        this.log('success', 'enhanced_tts_successful', {
          text: testText,
          voice: ttsData.voice,
          cached: ttsData.cached,
          audio_size: ttsData.audio_data?.length || 0
        })
        
        // Test audio playback (without actually playing)
        if (ttsData.success && ttsData.audio_data) {
          try {
            const audioBuffer = Uint8Array.from(atob(ttsData.audio_data), c => c.charCodeAt(0))
            const blob = new Blob([audioBuffer], { type: 'audio/wav' })
            const audioUrl = URL.createObjectURL(blob)
            
            this.log('info', 'tts_audio_blob_created', {
              blob_size: blob.size,
              blob_type: blob.type,
              audio_url_created: !!audioUrl
            })
            
            URL.revokeObjectURL(audioUrl)
          } catch (e) {
            this.log('error', 'tts_audio_processing_failed', { error: e.message })
          }
        }
      } else {
        this.log('error', 'enhanced_tts_failed', { status: response.status })
      }
    } catch (error) {
      this.log('error', 'enhanced_tts_error', { error: error.message })
    }
    
    // Test browser TTS fallback
    if (window.speechSynthesis) {
      const voices = window.speechSynthesis.getVoices()
      const swedishVoice = voices.find(voice => voice.lang.includes('sv'))
      
      this.log('info', 'browser_tts_available', {
        total_voices: voices.length,
        swedish_voice: swedishVoice?.name || 'none',
        swedish_voice_lang: swedishVoice?.lang || 'none'
      })
      
      // Create utterance (but don't speak to avoid noise)
      const utterance = new SpeechSynthesisUtterance(testText)
      if (swedishVoice) utterance.voice = swedishVoice
      
      this.log('success', 'browser_tts_ready', {
        text: testText,
        voice: utterance.voice?.name || 'default',
        lang: utterance.voice?.lang || 'default',
        rate: utterance.rate,
        pitch: utterance.pitch
      })
    } else {
      this.log('error', 'browser_tts_not_supported')
    }
    
    this.log('success', 'phase7_tts_response_completed')
  }
}

// Auto-start test
console.log('🎯 Starting Complete Voice End-to-End Test...')
console.log('📝 Results will be saved as JSONL file automatically')

const tester = new VoiceEndToEndTester()
window.voiceE2ETester = tester

// Start comprehensive test
tester.runCompleteTest().catch(error => {
  console.error('Test suite failed:', error)
  tester.log('error', 'test_suite_fatal_error', { 
    error: error.message, 
    stack: error.stack?.substring(0, 300) 
  })
  tester.saveJsonlLog()
})