/**
 * Alice Voice Activity Detection (VAD)
 * Intelligent detection av när användaren talar för automatisk start/stopp av lysning
 */

export class VoiceActivityDetector {
    constructor(audioContext, options = {}) {
        this.audioContext = audioContext;
        this.isInitialized = false;
        this.isRunning = false;
        this.callbacks = {};
        
        // VAD konfiguration
        this.config = {
            // Energi-thresholds
            silenceThreshold: options.silenceThreshold || 25,
            speechThreshold: options.speechThreshold || 40,
            
            // Timing parametrar
            minSilenceDuration: options.minSilenceDuration || 800,  // ms tystnad innan stopp
            minSpeechDuration: options.minSpeechDuration || 200,   // ms tal innan start
            maxSpeechDuration: options.maxSpeechDuration || 30000, // ms max tal-session
            
            // Frekvens analys
            speechFreqRangeLow: options.speechFreqRangeLow || 85,   // Hz - låg gräns för tal
            speechFreqRangeHigh: options.speechFreqRangeHigh || 3400, // Hz - hög gräns för tal
            
            // Adaptivitet
            adaptiveThreshold: options.adaptiveThreshold !== false, // Default true
            learningRate: options.learningRate || 0.1,
        };
        
        // State tracking
        this.state = {
            currentEnergy: 0,
            avgEnergy: 0,
            isSpeechActive: false,
            lastSpeechTime: 0,
            lastSilenceTime: 0,
            speechStartTime: 0,
            consecutiveSpeechFrames: 0,
            consecutiveSilenceFrames: 0,
        };
        
        // Audio processing
        this.analyser = null;
        this.frequencyData = null;
        this.timeData = null;
        
        // Adaptiv threshold learning
        this.energyHistory = [];
        this.maxHistoryLength = 1000;
        
        this.setupVAD();
    }
    
    setupVAD() {
        try {
            // Skapa analyser optimerad för VAD
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 512; 
            this.analyser.smoothingTimeConstant = 0.2; // Snabb respons för VAD
            this.analyser.minDecibels = -80;
            this.analyser.maxDecibels = -10;
            
            // Buffer för frekvens och tidsdomän data
            this.frequencyData = new Uint8Array(this.analyser.frequencyBinCount);
            this.timeData = new Float32Array(this.analyser.fftSize);
            
            this.isInitialized = true;
            console.log('VAD: Voice Activity Detector initialized');
            
        } catch (error) {
            console.error('VAD: Failed to setup VAD:', error);
            this.isInitialized = false;
        }
    }
    
    /**
     * Anslut audio source för VAD analys
     */
    connectSource(source) {
        if (!this.isInitialized) {
            console.warn('VAD: Not initialized');
            return false;
        }
        
        try {
            source.connect(this.analyser);
            console.log('VAD: Audio source connected');
            return true;
        } catch (error) {
            console.error('VAD: Failed to connect audio source:', error);
            return false;
        }
    }
    
    /**
     * Starta VAD processing
     */
    start() {
        if (!this.isInitialized || this.isRunning) {
            return false;
        }
        
        this.isRunning = true;
        this.state.lastSilenceTime = Date.now();
        this.processFrame();
        
        console.log('VAD: Started voice activity detection');
        this.emit('vad_started');
        return true;
    }
    
    /**
     * Stoppa VAD processing  
     */
    stop() {
        this.isRunning = false;
        this.state.isSpeechActive = false;
        console.log('VAD: Stopped voice activity detection');
        this.emit('vad_stopped');
    }
    
    /**
     * Huvud-processing loop för VAD
     */
    processFrame() {
        if (!this.isRunning) return;
        
        // Hämta audio data
        this.analyser.getByteFrequencyData(this.frequencyData);
        this.analyser.getFloatTimeDomainData(this.timeData);
        
        // Beräkna energy metrics
        const energy = this.calculateEnergy();
        const speechLikelihood = this.analyzeSpeechCharacteristics();
        
        // Uppdatera state
        this.updateEnergyHistory(energy);
        this.state.currentEnergy = energy;
        
        // VAD beslut
        const wasActive = this.state.isSpeechActive;
        const isActive = this.detectVoiceActivity(energy, speechLikelihood);
        
        this.state.isSpeechActive = isActive;
        
        // State change events
        if (isActive && !wasActive) {
            this.onSpeechStart();
        } else if (!isActive && wasActive) {
            this.onSpeechEnd();
        }
        
        // Timeout check
        this.checkTimeouts();
        
        // Fortsätt processing
        requestAnimationFrame(() => this.processFrame());
    }
    
    /**
     * Beräkna total audio energy
     */
    calculateEnergy() {
        // RMS energy från time domain
        let rms = 0;
        for (let i = 0; i < this.timeData.length; i++) {
            rms += this.timeData[i] * this.timeData[i];
        }
        rms = Math.sqrt(rms / this.timeData.length);
        
        // Konvertera till decibel-skala för lättare hantering
        const db = 20 * Math.log10(Math.max(rms, 1e-10));
        
        // Normalisera till 0-100 skala
        return Math.max(0, Math.min(100, (db + 60) * 100 / 60));
    }
    
    /**
     * Analysera om ljudet har tal-liknande egenskaper
     */
    analyzeSpeechCharacteristics() {
        // Analysera frekvensfördelning inom tal-området
        const nyquist = this.audioContext.sampleRate / 2;
        const binWidth = nyquist / this.frequencyData.length;
        
        const speechBinStart = Math.floor(this.config.speechFreqRangeLow / binWidth);
        const speechBinEnd = Math.floor(this.config.speechFreqRangeHigh / binWidth);
        
        let speechEnergy = 0;
        let totalEnergy = 0;
        
        for (let i = 0; i < this.frequencyData.length; i++) {
            const energy = this.frequencyData[i];
            totalEnergy += energy;
            
            if (i >= speechBinStart && i <= speechBinEnd) {
                speechEnergy += energy;
            }\n        }
        \n        // Speech likelihood baserat på frekvensfördelning\n        const speechRatio = totalEnergy > 0 ? speechEnergy / totalEnergy : 0;\n        \n        // Analysera spektral centroid (tyngdpunkt i frekvensspektrum)\n        let centroid = 0;\n        let magnitude = 0;\n        \n        for (let i = 0; i < this.frequencyData.length; i++) {\n            const freq = i * binWidth;\n            const amp = this.frequencyData[i];\n            centroid += freq * amp;\n            magnitude += amp;\n        }\n        \n        if (magnitude > 0) {\n            centroid /= magnitude;\n        }\n        \n        // Tal har typiskt spektral centroid inom tal-området\n        const centroidScore = (centroid >= this.config.speechFreqRangeLow && \n                              centroid <= this.config.speechFreqRangeHigh) ? 1.0 : 0.5;\n        \n        // Kombinera metrics för speech likelihood\n        return (speechRatio * 0.7 + centroidScore * 0.3);\n    }\n    \n    /**\n     * Detektera voice activity baserat på energy och characteristics\n     */\n    detectVoiceActivity(energy, speechLikelihood) {\n        const now = Date.now();\n        \n        // Adaptiva thresholds\n        let silenceThreshold = this.config.silenceThreshold;\n        let speechThreshold = this.config.speechThreshold;\n        \n        if (this.config.adaptiveThreshold && this.energyHistory.length > 100) {\n            const avgEnergy = this.energyHistory.reduce((a, b) => a + b) / this.energyHistory.length;\n            const energyStd = Math.sqrt(\n                this.energyHistory.reduce((sum, val) => sum + Math.pow(val - avgEnergy, 2), 0) / \n                this.energyHistory.length\n            );\n            \n            // Justera thresholds baserat på ambient noise\n            silenceThreshold = Math.max(15, avgEnergy - energyStd);\n            speechThreshold = Math.max(25, avgEnergy + energyStd * 0.5);\n        }\n        \n        // Kombinera energy och speech characteristics\n        const combinedScore = energy * speechLikelihood;\n        \n        // State machine för VAD\n        if (this.state.isSpeechActive) {\n            // Currently active - look for silence\n            if (combinedScore < silenceThreshold) {\n                this.state.consecutiveSilenceFrames++;\n                this.state.consecutiveSpeechFrames = 0;\n                \n                // Require sustained silence to stop\n                const silenceDuration = this.state.consecutiveSilenceFrames * (1000/60); // ~60fps\n                return silenceDuration < this.config.minSilenceDuration;\n                \n            } else {\n                this.state.consecutiveSpeechFrames++;\n                this.state.consecutiveSilenceFrames = 0;\n                return true;\n            }\n            \n        } else {\n            // Currently inactive - look for speech\n            if (combinedScore > speechThreshold) {\n                this.state.consecutiveSpeechFrames++;\n                this.state.consecutiveSilenceFrames = 0;\n                \n                // Require sustained speech to start\n                const speechDuration = this.state.consecutiveSpeechFrames * (1000/60);\n                return speechDuration >= this.config.minSpeechDuration;\n                \n            } else {\n                this.state.consecutiveSilenceFrames++;\n                this.state.consecutiveSpeechFrames = 0;\n                return false;\n            }\n        }\n    }\n    \n    /**\n     * Uppdatera energy history för adaptive thresholds\n     */\n    updateEnergyHistory(energy) {\n        this.energyHistory.push(energy);\n        \n        if (this.energyHistory.length > this.maxHistoryLength) {\n            this.energyHistory.shift();\n        }\n        \n        // Uppdatera rolling average\n        const recentHistory = this.energyHistory.slice(-100); // Last 100 frames\n        this.state.avgEnergy = recentHistory.reduce((a, b) => a + b) / recentHistory.length;\n    }\n    \n    /**\n     * Speech start event\n     */\n    onSpeechStart() {\n        const now = Date.now();\n        this.state.lastSpeechTime = now;\n        this.state.speechStartTime = now;\n        \n        console.log('VAD: Speech detected');\n        this.emit('speech_start', {\n            timestamp: now,\n            energy: this.state.currentEnergy\n        });\n    }\n    \n    /**\n     * Speech end event\n     */\n    onSpeechEnd() {\n        const now = Date.now();\n        this.state.lastSilenceTime = now;\n        \n        const speechDuration = now - this.state.speechStartTime;\n        \n        console.log('VAD: Speech ended, duration:', speechDuration, 'ms');\n        this.emit('speech_end', {\n            timestamp: now,\n            duration: speechDuration,\n            energy: this.state.currentEnergy\n        });\n    }\n    \n    /**\n     * Kontrollera timeouts\n     */\n    checkTimeouts() {\n        const now = Date.now();\n        \n        // Max speech duration timeout\n        if (this.state.isSpeechActive && \n            now - this.state.speechStartTime > this.config.maxSpeechDuration) {\n            \n            console.log('VAD: Max speech duration reached, forcing speech end');\n            this.emit('speech_timeout', {\n                timestamp: now,\n                duration: now - this.state.speechStartTime\n            });\n            \n            this.state.isSpeechActive = false;\n            this.onSpeechEnd();\n        }\n    }\n    \n    /**\n     * Hämta current VAD status\n     */\n    getStatus() {\n        return {\n            isRunning: this.isRunning,\n            isSpeechActive: this.state.isSpeechActive,\n            currentEnergy: this.state.currentEnergy,\n            avgEnergy: this.state.avgEnergy,\n            adaptiveThreshold: this.config.adaptiveThreshold,\n            thresholds: {\n                silence: this.config.silenceThreshold,\n                speech: this.config.speechThreshold\n            },\n            timing: {\n                lastSpeech: this.state.lastSpeechTime,\n                lastSilence: this.state.lastSilenceTime,\n                currentSessionDuration: this.state.isSpeechActive ? \n                    Date.now() - this.state.speechStartTime : 0\n            }\n        };\n    }\n    \n    /**\n     * Uppdatera VAD konfiguration runtime\n     */\n    updateConfig(newConfig) {\n        this.config = { ...this.config, ...newConfig };\n        console.log('VAD: Configuration updated:', newConfig);\n    }\n    \n    /**\n     * Event system\n     */\n    on(event, callback) {\n        if (!this.callbacks[event]) {\n            this.callbacks[event] = [];\n        }\n        this.callbacks[event].push(callback);\n    }\n    \n    off(event, callback) {\n        if (this.callbacks[event]) {\n            const index = this.callbacks[event].indexOf(callback);\n            if (index > -1) {\n                this.callbacks[event].splice(index, 1);\n            }\n        }\n    }\n    \n    emit(event, data = null) {\n        if (this.callbacks[event]) {\n            this.callbacks[event].forEach(callback => {\n                try {\n                    callback(data);\n                } catch (error) {\n                    console.error('VAD: Event callback error:', error);\n                }\n            });\n        }\n    }\n    \n    /**\n     * Cleanup resources\n     */\n    dispose() {\n        this.stop();\n        if (this.analyser) {\n            this.analyser.disconnect();\n        }\n        this.callbacks = {};\n        this.isInitialized = false;\n        console.log('VAD: Disposed');\n    }\n}\n\n// Utility function\nexport function createVoiceActivityDetector(audioContext, options = {}) {\n    return new VoiceActivityDetector(audioContext, options);\n}"