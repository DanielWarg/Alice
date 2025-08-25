/**
 * B3 Ambient Voice Client - Always-On Voice Processing
 * Streams continuous audio to Alice backend for ambient transcription
 * Uses WebAudio API for real-time 16kHz PCM frame streaming
 */

class B3AmbientVoiceClient {
    constructor() {
        this.websocket = null;
        this.audioContext = null;
        this.mediaStream = null;
        this.audioWorklet = null;
        this.isActive = false;
        this.isMuted = false;
        this.hardMute = false;
        this.callbacks = {};
        
        // Audio processing parameters
        this.sampleRate = 16000;
        this.frameDurationMs = 20;
        this.frameSize = (this.sampleRate * this.frameDurationMs) / 1000; // 320 samples per frame
        
        // Connection state
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        // Privacy and safety
        this.privacyMode = false;
        
        console.log('B3 Ambient Voice Client initialized');
    }
    
    /**
     * Start ambient voice processing
     */
    async start() {
        try {
            if (this.isActive) {
                console.warn('B3 Ambient voice already active');
                return;
            }
            
            // Request microphone permission
            console.log('Requesting microphone access for ambient voice...');
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: this.sampleRate,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            // Setup audio processing
            await this.setupAudioProcessing();
            
            // Connect to WebSocket
            await this.connectWebSocket();
            
            this.isActive = true;
            this.emit('started');
            console.log('B3 Ambient voice started successfully');
            
        } catch (error) {
            console.error('Failed to start B3 ambient voice:', error);
            this.emit('error', error);
            throw error;
        }
    }
    
    /**
     * Stop ambient voice processing
     */
    async stop() {
        try {
            this.isActive = false;
            
            // Stop audio processing
            if (this.audioWorklet) {
                this.audioWorklet.disconnect();
                this.audioWorklet = null;
            }
            
            if (this.audioContext && this.audioContext.state !== 'closed') {
                await this.audioContext.close();
                this.audioContext = null;
            }
            
            if (this.mediaStream) {
                this.mediaStream.getTracks().forEach(track => track.stop());
                this.mediaStream = null;
            }
            
            // Close WebSocket
            if (this.websocket) {
                this.websocket.close();
                this.websocket = null;
            }
            
            this.emit('stopped');
            console.log('B3 Ambient voice stopped');
            
        } catch (error) {
            console.error('Error stopping B3 ambient voice:', error);
            this.emit('error', error);
        }
    }
    
    /**
     * Setup WebAudio pipeline for continuous processing
     */
    async setupAudioProcessing() {
        // Create audio context
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: this.sampleRate,
            latencyHint: 'interactive'
        });
        
        // Create media source
        const source = this.audioContext.createMediaStreamSource(this.mediaStream);
        
        // Setup audio worklet for frame processing
        try {
            // Load audio worklet processor
            await this.audioContext.audioWorklet.addModule('/lib/b3-audio-processor.js');
            
            // Create worklet node
            this.audioWorklet = new AudioWorkletNode(this.audioContext, 'b3-audio-processor', {
                processorOptions: {
                    frameDurationMs: this.frameDurationMs,
                    sampleRate: this.sampleRate
                }
            });
            
            // Handle processed audio frames
            this.audioWorklet.port.onmessage = (event) => {
                if (event.data.type === 'audio_frame' && !this.isMuted && !this.hardMute) {
                    this.sendAudioFrame(event.data.frame, event.data.timestamp);
                }
            };
            
            // Connect audio pipeline
            source.connect(this.audioWorklet);
            this.audioWorklet.connect(this.audioContext.destination);
            
        } catch (error) {
            console.error('Failed to setup audio worklet, using fallback:', error);
            // TODO: Implement ScriptProcessorNode fallback for older browsers
            await this.setupFallbackAudioProcessing(source);
        }
    }
    
    /**
     * Fallback audio processing using ScriptProcessorNode
     */
    async setupFallbackAudioProcessing(source) {
        console.log('Using ScriptProcessorNode fallback for audio processing');
        
        // Create script processor (deprecated but more compatible)
        const bufferSize = 4096;
        const processor = this.audioContext.createScriptProcessor(bufferSize, 1, 1);
        
        let frameBuffer = [];
        
        processor.onaudioprocess = (event) => {
            if (this.isMuted || this.hardMute) return;
            
            const inputBuffer = event.inputBuffer;
            const inputData = inputBuffer.getChannelData(0);
            
            // Accumulate samples into frames
            for (let i = 0; i < inputData.length; i++) {
                frameBuffer.push(inputData[i]);
                
                // Send frame when buffer is full
                if (frameBuffer.length >= this.frameSize) {
                    const frame = new Float32Array(frameBuffer.slice(0, this.frameSize));
                    this.sendAudioFrame(frame, this.audioContext.currentTime);
                    
                    // Keep overlap for better processing
                    frameBuffer = frameBuffer.slice(this.frameSize - 32); // Keep 32 samples overlap
                }
            }
        };
        
        // Connect pipeline
        source.connect(processor);
        processor.connect(this.audioContext.destination);
        
        this.audioWorklet = processor; // Store for cleanup
    }
    
    /**
     * Connect to WebSocket backend
     */
    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            const wsUrl = `ws://localhost:8000/ws/voice/ambient`;
            console.log('Connecting to B3 ambient voice WebSocket:', wsUrl);
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('B3 ambient voice WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.emit('connected');
                resolve();
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('B3 ambient voice WebSocket disconnected');
                this.isConnected = false;
                this.emit('disconnected');
                
                // Attempt reconnection if still active
                if (this.isActive && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`);
                    setTimeout(() => this.connectWebSocket(), 2000 * this.reconnectAttempts);
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error('B3 ambient voice WebSocket error:', error);
                this.emit('error', error);
                reject(error);
            };
        });
    }
    
    /**
     * Handle WebSocket messages from backend
     */
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'status_update':
                this.handleStatusUpdate(data);
                break;
                
            case 'transcription_partial':
                this.emit('transcription_partial', data);
                break;
                
            case 'transcription_final':
                this.emit('transcription_final', data);
                break;
                
            case 'ambient_summary':
                this.emit('ambient_summary', data);
                break;
                
            case 'proactive_trigger':
                this.emit('proactive_trigger', data);
                break;
                
            case 'keepalive':
                // Respond to keepalive
                this.sendMessage({ type: 'pong', timestamp: Date.now() / 1000 });
                break;
                
            case 'error':
                console.error('B3 backend error:', data.message);
                this.emit('error', new Error(data.message));
                break;
                
            default:
                console.log('Unknown B3 message type:', data.type);
        }
    }
    
    /**
     * Handle status updates from backend
     */
    handleStatusUpdate(data) {
        this.hardMute = data.hard_mute;
        
        // Emit status change
        this.emit('status_update', {
            isActive: data.is_active,
            isMuted: data.is_muted,
            hardMute: data.hard_mute,
            framesProcessed: data.frames_processed,
            bufferSize: data.buffer_size,
            sessionDuration: data.session_duration\n        });
    }
    
    /**
     * Send audio frame to backend\n     */
    sendAudioFrame(frameData, timestamp) {
        if (!this.isConnected || !this.websocket) return;
        
        // Convert Float32Array to base64 encoded PCM
        const pcmData = new Int16Array(frameData.length);
        for (let i = 0; i < frameData.length; i++) {
            pcmData[i] = Math.max(-32768, Math.min(32767, frameData[i] * 32768));
        }
        
        const base64Data = this.arrayBufferToBase64(pcmData.buffer);
        
        const message = {
            type: 'audio_frame',
            audio_data: base64Data,
            timestamp: timestamp,
            sample_rate: this.sampleRate,
            duration_ms: this.frameDurationMs
        };
        
        this.sendMessage(message);
    }
    
    /**
     * Send control message to backend
     */
    sendControlMessage(command, params = {}) {
        const message = {
            type: 'control',
            command: command,
            ...params
        };
        
        this.sendMessage(message);
    }
    
    /**
     * Send message to WebSocket
     */
    sendMessage(message) {
        if (this.isConnected && this.websocket) {
            this.websocket.send(JSON.stringify(message));
        }
    }
    
    /**
     * Mute ambient voice (soft mute)
     */
    mute() {
        this.isMuted = true;
        this.sendControlMessage('mute');
        this.emit('muted');
    }
    
    /**
     * Unmute ambient voice
     */
    unmute() {
        if (!this.hardMute) {
            this.isMuted = false;
            this.sendControlMessage('unmute');
            this.emit('unmuted');
        }
    }
    
    /**
     * Enable hard mute (cannot be overridden)
     */
    hardMuteEnable() {
        this.sendControlMessage('hard_mute');
        this.emit('hard_mute_enabled');
    }
    
    /**
     * Disable hard mute
     */
    hardMuteDisable() {
        this.sendControlMessage('hard_unmute');
        this.emit('hard_mute_disabled');
    }
    
    /**
     * Clear ambient memory
     */
    clearMemory() {
        this.sendControlMessage('clear_memory');
        this.emit('memory_cleared');
    }
    
    /**
     * Convert ArrayBuffer to base64
     */
    arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return window.btoa(binary);
    }
    
    /**
     * Event system
     */
    on(event, callback) {
        if (!this.callbacks[event]) {
            this.callbacks[event] = [];
        }
        this.callbacks[event].push(callback);
    }
    
    off(event, callback) {
        if (this.callbacks[event]) {
            this.callbacks[event] = this.callbacks[event].filter(cb => cb !== callback);
        }
    }
    
    emit(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in event callback for ${event}:`, error);
                }
            });
        }
    }
}

// Export for use in other modules
window.B3AmbientVoiceClient = B3AmbientVoiceClient;