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
            const transcript = result[0].transcript;
            const isFinal = result.isFinal;
            
            if (isFinal) {
                console.log('Voice input (final):', transcript);
                this.sendVoiceInput(transcript);
                this.emit('voice_input', { text: transcript, final: true });
            } else {
                this.emit('voice_input', { text: transcript, final: false });
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
    
    speak(text) {
        if (!text || !this.synthesis) {
            return;
        }
        
        // Cancel any ongoing speech
        this.synthesis.cancel();
        
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
            voice: this.voice?.name || 'Unknown'
        };
    }
}

// Export for use in applications
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AliceVoiceClient;
} else {
    window.AliceVoiceClient = AliceVoiceClient;
}