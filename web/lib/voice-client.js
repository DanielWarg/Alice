/**
 * Alice Voice Client - Browser-native speech interface
 * Hybrid approach: Browser Speech API + WebSocket to Alice backend
 */

class AliceVoiceClient {
    constructor(sessionId = null) {
        this.sessionId = sessionId || this.generateSessionId();
        this.websocket = null;
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.isListening = false;
        this.isConnected = false;
        this.callbacks = {};
        
        this.setupSpeechRecognition();
        this.setupSpeechSynthesis();
    }
    
    generateSessionId() {
        return 'voice_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    setupSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.error('Speech recognition not supported in this browser');
            return;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'sv-SE';
        this.recognition.maxAlternatives = 1;
        
        // Real-time optimeringar
        if (this.recognition.webkitSpeechRecognition) {
            this.recognition.serviceURI = 'wss://www.google.com/speech-api/v2/recognize';
        }
        
        // Svensk-specifika inställningar
        this.recognition.grammars = null;  // Använd inte grammatikbegränsningar
        
        this.recognition.onstart = () => {
            this.isListening = true;
            this.emit('listening_started');
        };
        
        this.recognition.onend = () => {
            this.isListening = false;
            this.emit('listening_stopped');
        };
        
        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.emit('recognition_error', event.error);
        };
        
        this.recognition.onresult = (event) => {
            const result = event.results[event.results.length - 1];
            let transcript = result[0].transcript;
            const confidence = result[0].confidence || 0;
            const isFinal = result.isFinal;
            
            // Post-processing för svensk text (matchar VoiceBox)
            if (isFinal) {
                transcript = this.postProcessSwedishSpeech(transcript.trim());
                if (transcript) {
                    console.log('Voice input (final):', transcript, 'confidence:', confidence);
                    this.sendVoiceInput(transcript);
                    this.emit('voice_input', { text: transcript, final: true, confidence });
                }
            } else {
                // Interim results för real-time feedback
                this.emit('voice_input', { text: transcript, final: false, confidence });
            }
        };
    }
    
    setupSpeechSynthesis() {
        // Wait for voices to be loaded
        if (this.synthesis.getVoices().length === 0) {
            this.synthesis.onvoiceschanged = () => {
                this.selectSwedishVoice();
            };
        } else {
            this.selectSwedishVoice();
        }
    }
    
    selectSwedishVoice() {
        const voices = this.synthesis.getVoices();
        
        // Prioritera svenska röster
        this.voice = voices.find(voice => 
            voice.lang.includes('sv') || 
            voice.name.toLowerCase().includes('swedish') ||
            voice.name.toLowerCase().includes('svenska')
        ) || voices.find(voice => 
            voice.lang.includes('en') && voice.name.toLowerCase().includes('female')
        ) || voices[0];
        
        console.log('Selected voice:', this.voice?.name, this.voice?.lang);
    }
    
    async connect() {
        if (this.isConnected) {
            return;
        }
        
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host.replace(':3100', ':8000'); // Frontend port -> Backend port
            const wsUrl = `${protocol}//${host}/ws/voice/${this.sessionId}`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.isConnected = true;
                console.log('Alice voice connection established');
                this.emit('connected');
                
                // Send ping to test connection
                this.websocket.send(JSON.stringify({ type: 'ping' }));
            };
            
            this.websocket.onclose = () => {
                this.isConnected = false;
                console.log('Alice voice connection closed');
                this.emit('disconnected');
            };
            
            this.websocket.onerror = (error) => {
                console.error('Alice voice connection error:', error);
                this.emit('connection_error', error);
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleAliceMessage(data);
                } catch (error) {
                    console.error('Failed to parse Alice message:', error);
                }
            };
            
        } catch (error) {
            console.error('Failed to connect to Alice:', error);
            this.emit('connection_error', error);
        }
    }
    
    handleAliceMessage(data) {
        console.log('Alice message:', data);
        
        switch (data.type) {
            case 'pong':
                // Connection heartbeat
                break;
                
            case 'heard':
                this.emit('alice_heard', data.text);
                break;
                
            case 'acknowledge':
                this.emit('alice_acknowledge', data.message);
                this.speak(data.message);
                break;
                
            case 'speak':
                this.emit('alice_response', {
                    text: data.text,
                    partial: data.partial,
                    final: data.final
                });
                
                if (data.final) {
                    this.speak(data.text);
                }
                break;
                
            case 'tool_success':
                this.emit('tool_executed', {
                    tool: data.tool,
                    message: data.message,
                    result: data.result
                });
                
                if (data.message) {
                    this.speak(data.message);
                }
                break;
                
            case 'tool_error':
                this.emit('tool_error', data.message);
                this.speak(data.message);
                break;
                
            case 'error':
                this.emit('error', data.message);
                break;
        }
    }
    
    sendVoiceInput(text) {
        if (!this.isConnected || !this.websocket) {
            console.warn('Not connected to Alice');
            return;
        }
        
        this.websocket.send(JSON.stringify({
            type: 'voice_input',
            text: text,
            timestamp: Date.now()
        }));
    }
    
    async speak(text, options = {}) {
        if (!text) {
            return;
        }
        
        // Cancel any ongoing speech
        if (this.synthesis) {
            this.synthesis.cancel();
        }
        
        try {
            // Try Alice's enhanced TTS first
            const ttsResponse = await this.synthesizeWithAlice(text, options);
            if (ttsResponse && ttsResponse.success) {
                await this.playAudioData(ttsResponse.audio_data);
                return;
            }
        } catch (error) {
            console.warn('Alice TTS failed, falling back to browser synthesis:', error);
        }
        
        // Fallback to browser synthesis
        this.fallbackSpeak(text);
    }
    
    async synthesizeWithAlice(text, options = {}) {
        const requestData = {
            text: text,
            voice: options.voice || 'sv_SE-nst-medium',
            speed: options.speed || 1.0,
            emotion: options.emotion || 'friendly',
            personality: options.personality || 'alice',
            pitch: options.pitch || 1.0,
            volume: options.volume || 1.0,
            cache: options.cache !== false
        };
        
        const response = await fetch('/api/tts/synthesize', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            throw new Error(`TTS request failed: ${response.status}`);
        }
        
        return await response.json();
    }
    
    async playAudioData(audioBase64) {
        return new Promise((resolve, reject) => {
            try {
                const audioBuffer = Uint8Array.from(atob(audioBase64), c => c.charCodeAt(0));
                const blob = new Blob([audioBuffer], { type: 'audio/wav' });
                const audioUrl = URL.createObjectURL(blob);
                const audio = new Audio(audioUrl);
                
                audio.onloadeddata = () => {
                    this.emit('speaking_started');
                };
                
                audio.onended = () => {
                    URL.revokeObjectURL(audioUrl);
                    this.emit('speaking_ended');
                    resolve();
                };
                
                audio.onerror = (error) => {
                    URL.revokeObjectURL(audioUrl);
                    this.emit('speech_error', error);
                    reject(error);
                };
                
                audio.play().catch(reject);
                
            } catch (error) {
                this.emit('speech_error', error);
                reject(error);
            }
        });
    }
    
    fallbackSpeak(text) {
        if (!this.synthesis) {
            return;
        }
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.voice = this.voice;
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        
        utterance.onstart = () => {
            this.emit('speaking_started', text);
        };
        
        utterance.onend = () => {
            this.emit('speaking_ended', text);
        };
        
        utterance.onerror = (error) => {
            console.error('Speech synthesis error:', error);
            this.emit('speech_error', error);
        };
        
        this.synthesis.speak(utterance);
    }
    
    async getAvailableVoices() {
        try {
            const response = await fetch('/api/tts/voices');
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Failed to get available voices:', error);
        }
        return null;
    }
    
    async getPersonalitySettings(personality) {
        try {
            const response = await fetch(`/api/tts/personality/${personality}`);
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Failed to get personality settings:', error);
        }
        return null;
    }
    
    startListening() {
        if (!this.recognition) {
            console.error('Speech recognition not available');
            return;
        }
        
        if (this.isListening) {
            return;
        }
        
        try {
            this.recognition.start();
        } catch (error) {
            console.error('Failed to start listening:', error);
        }
    }
    
    stopListening() {
        if (!this.recognition || !this.isListening) {
            return;
        }
        
        try {
            this.recognition.stop();
        } catch (error) {
            console.error('Failed to stop listening:', error);
        }
    }
    
    stopSpeaking() {
        if (this.synthesis) {
            this.synthesis.cancel();
        }
    }
    
    disconnect() {
        this.stopListening();
        this.stopSpeaking();
        
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        this.isConnected = false;
    }
    
    // Event system
    on(event, callback) {
        if (!this.callbacks[event]) {
            this.callbacks[event] = [];
        }
        this.callbacks[event].push(callback);
    }
    
    off(event, callback) {
        if (!this.callbacks[event]) {
            return;
        }
        
        const index = this.callbacks[event].indexOf(callback);
        if (index > -1) {
            this.callbacks[event].splice(index, 1);
        }
    }
    
    emit(event, data = null) {
        if (!this.callbacks[event]) {
            return;
        }
        
        this.callbacks[event].forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error('Event callback error:', error);
            }
        });
    }
    
    postProcessSwedishSpeech(text) {
        if (!text) return text;
        
        // Samma korrigeringar som i VoiceBox för konsistens
        const corrections = {
            // Engelska -> Svenska
            'okay': 'okej',
            'ok': 'okej',
            'hello': 'hej',
            'hi': 'hej', 
            'bye': 'hej då',
            'yes': 'ja',
            'no': 'nej',
            'please': 'tack',
            'thank you': 'tack',
            'sorry': 'förlåt',
            
            // AI-kommandon
            'allis': 'Alice',
            'alis': 'Alice', 
            'play music': 'spela musik',
            'stop music': 'stoppa musik',
            'pause music': 'pausa musik',
            'send email': 'skicka mejl',
            'read email': 'läs mejl',
            'what time': 'vad är klockan',
            "what's the time": 'vad är klockan',
            
            // Vanliga mishörningar
            'alice s': 'Alice',
            'alice,': 'Alice', 
            'alice.': 'Alice',
        };
        
        let corrected = text.toLowerCase();
        
        // Applicera korrigeringar
        Object.entries(corrections).forEach(([wrong, right]) => {
            const regex = new RegExp(`\\b${wrong.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
            corrected = corrected.replace(regex, right);
        });
        
        // Alice ska alltid ha stor bokstav
        corrected = corrected.replace(/\balice\b/gi, 'Alice');
        
        // Kapitaliera första bokstaven
        corrected = corrected.charAt(0).toUpperCase() + corrected.slice(1);
        
        return corrected.trim();
    }
    
    // Utility methods
    isSupported() {
        return !!(
            ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) &&
            window.speechSynthesis
        );
    }
    
    getStatus() {
        return {
            supported: this.isSupported(),
            connected: this.isConnected,
            listening: this.isListening,
            speaking: this.synthesis?.speaking || false,
            voice: this.voice?.name || 'Unknown',
            features: {
                swedish_optimization: true,
                real_time_processing: true,
                post_processing: true,
                interim_results: this.recognition?.interimResults || false
            }
        };
    }
}

// Export for use in applications
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AliceVoiceClient;
} else {
    window.AliceVoiceClient = AliceVoiceClient;
}