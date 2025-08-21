/**
 * Alice Audio Enhancement - Avancerad ljudbehandling för klarare röstinput
 * Implementerar brusreducering, ljudfiltrering och signalförbättring
 */

export class AudioEnhancer {
    constructor(audioContext) {
        this.audioContext = audioContext;
        this.isInitialized = false;
        
        // Audio processing nodes
        this.inputGain = null;
        this.highpassFilter = null;
        this.lowpassFilter = null;
        this.compressor = null;
        this.noiseGate = null;
        this.outputGain = null;
        
        // Noise profile för adaptiv brusreducering
        this.noiseProfile = null;
        this.noiseProfileBuffer = [];
        this.noiseProfileSamples = 0;
        this.maxNoiseProfileSamples = 1000;
        
        // Real-time analysis
        this.analyser = null;
        this.frequencyData = null;
        
        this.setupAudioProcessing();
    }
    
    setupAudioProcessing() {
        try {
            // Input gain - för att justera ingångsnivå
            this.inputGain = this.audioContext.createGain();
            this.inputGain.gain.value = 1.2; // Lite förstärkning
            
            // High-pass filter - ta bort låga frekvenser (rumsbrus, AC-brus)
            this.highpassFilter = this.audioContext.createBiquadFilter();
            this.highpassFilter.type = 'highpass';
            this.highpassFilter.frequency.value = 85; // Filtrera bort <85Hz
            this.highpassFilter.Q.value = 0.7;
            
            // Low-pass filter - ta bort höga frekvenser (hiss, elektroniskt brus)
            this.lowpassFilter = this.audioContext.createBiquadFilter();
            this.lowpassFilter.type = 'lowpass'; 
            this.lowpassFilter.frequency.value = 8000; // Filtrera bort >8kHz
            this.lowpassFilter.Q.value = 0.7;
            
            // Dynamic compressor - jämna ut volymskillnader
            this.compressor = this.audioContext.createDynamicsCompressor();
            this.compressor.threshold.value = -24; // Börja komprimera vid -24dB
            this.compressor.knee.value = 30; // Mjuk knä
            this.compressor.ratio.value = 3; // 3:1 komprimering
            this.compressor.attack.value = 0.003; // Snabb attack för tal
            this.compressor.release.value = 0.25; // Måttlig release
            
            // Noise gate (simulerad med gain control)
            this.noiseGate = this.audioContext.createGain();
            this.noiseGate.gain.value = 1.0;
            
            // Output gain - final nivå justering
            this.outputGain = this.audioContext.createGain();
            this.outputGain.gain.value = 0.9;
            
            // Analyser för real-time monitoring
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 512;
            this.analyser.smoothingTimeConstant = 0.3;
            this.frequencyData = new Uint8Array(this.analyser.frequencyBinCount);
            
            this.isInitialized = true;
            console.log('AudioEnhancer: Audio processing chain initialized');
            
        } catch (error) {
            console.error('AudioEnhancer: Failed to setup audio processing:', error);
            this.isInitialized = false;
        }
    }
    
    /**
     * Koppla in en MediaStream genom förbättringskedjan
     */
    connectSource(source) {
        if (!this.isInitialized) {
            console.warn('AudioEnhancer: Not initialized, returning original source');
            return source;
        }
        
        try {
            // Bygg processing chain
            source
                .connect(this.inputGain)
                .connect(this.highpassFilter)
                .connect(this.lowpassFilter)
                .connect(this.compressor)
                .connect(this.noiseGate)
                .connect(this.outputGain)
                .connect(this.analyser);
            
            console.log('AudioEnhancer: Processing chain connected');
            
            // Starta noise profiling
            this.startNoiseProfileGathering();
            
            return this.outputGain;
            
        } catch (error) {
            console.error('AudioEnhancer: Failed to connect processing chain:', error);
            return source;
        }
    }
    
    /**
     * Samla brusprofile under tystnad för adaptiv brusreducering
     */
    startNoiseProfileGathering() {
        if (!this.analyser) return;
        
        const gatherNoise = () => {
            if (this.noiseProfileSamples >= this.maxNoiseProfileSamples) {
                this.analyzeNoiseProfile();
                return;
            }
            
            this.analyser.getByteFrequencyData(this.frequencyData);
            
            // Detektera om det är "tyst" (låg overall energi)
            const totalEnergy = this.frequencyData.reduce((sum, val) => sum + val, 0);
            const avgEnergy = totalEnergy / this.frequencyData.length;
            
            if (avgEnergy < 30) { // Tystnadsgräns
                // Spara noise sample
                this.noiseProfileBuffer.push([...this.frequencyData]);
                this.noiseProfileSamples++;
            }
            
            // Fortsätt samla i 2 sekunder
            if (this.noiseProfileSamples < this.maxNoiseProfileSamples) {
                setTimeout(gatherNoise, 20); // 50Hz sampling
            }
        };
        
        console.log('AudioEnhancer: Starting noise profile gathering...');
        setTimeout(gatherNoise, 500); // Vänta lite innan vi börjar
    }
    
    /**
     * Analysera insamlad brusprofile
     */
    analyzeNoiseProfile() {
        if (this.noiseProfileBuffer.length === 0) return;
        
        // Beräkna medelvärde för varje frekvensbin
        const avgProfile = new Float32Array(this.frequencyData.length);
        
        this.noiseProfileBuffer.forEach(sample => {
            sample.forEach((val, i) => {
                avgProfile[i] += val;
            });
        });
        
        avgProfile.forEach((val, i) => {
            avgProfile[i] = val / this.noiseProfileBuffer.length;
        });
        
        this.noiseProfile = avgProfile;
        console.log('AudioEnhancer: Noise profile analyzed', avgProfile);
        
        // Justera filter baserat på brusprofile
        this.adaptFiltersToNoiseProfile();
    }
    
    /**
     * Anpassa filter baserat på uppmätt brusprofile
     */
    adaptFiltersToNoiseProfile() {
        if (!this.noiseProfile || !this.isInitialized) return;
        
        try {
            // Analysera var bruset är starkast
            const maxNoise = Math.max(...this.noiseProfile);
            const lowFreqNoise = this.noiseProfile.slice(0, 10).reduce((a, b) => a + b) / 10;
            const highFreqNoise = this.noiseProfile.slice(-10).reduce((a, b) => a + b) / 10;
            
            // Justera high-pass filter om mycket lågt brus
            if (lowFreqNoise > maxNoise * 0.3) {
                this.highpassFilter.frequency.value = Math.min(120, this.highpassFilter.frequency.value + 10);
                console.log('AudioEnhancer: Increased highpass to', this.highpassFilter.frequency.value, 'Hz due to low-freq noise');
            }
            
            // Justera low-pass filter om mycket högt brus  
            if (highFreqNoise > maxNoise * 0.3) {
                this.lowpassFilter.frequency.value = Math.max(6000, this.lowpassFilter.frequency.value - 500);
                console.log('AudioEnhancer: Decreased lowpass to', this.lowpassFilter.frequency.value, 'Hz due to high-freq noise');
            }
            
            // Justera kompressor threshold baserat på total brusnivå
            const avgNoise = this.noiseProfile.reduce((a, b) => a + b) / this.noiseProfile.length;
            if (avgNoise > 20) {
                this.compressor.threshold.value = Math.max(-30, this.compressor.threshold.value - 3);
                console.log('AudioEnhancer: Lowered compressor threshold to', this.compressor.threshold.value, 'dB due to noise');
            }
            
        } catch (error) {
            console.error('AudioEnhancer: Error adapting filters:', error);
        }
    }
    
    /**
     * Real-time noise gate baserat på current audio level
     */
    updateNoiseGate() {
        if (!this.analyser || !this.noiseGate) return;
        
        this.analyser.getByteFrequencyData(this.frequencyData);
        
        // Beräkna current signal strength
        const totalEnergy = this.frequencyData.reduce((sum, val) => sum + val, 0);
        const avgEnergy = totalEnergy / this.frequencyData.length;
        
        // Adaptive noise gate threshold
        const baseThreshold = this.noiseProfile ? 
            (this.noiseProfile.reduce((a, b) => a + b) / this.noiseProfile.length) + 5 : 
            25;
        
        // Smooth gate operation
        const targetGain = avgEnergy > baseThreshold ? 1.0 : 0.1;
        const currentGain = this.noiseGate.gain.value;
        const newGain = currentGain + (targetGain - currentGain) * 0.1; // Smooth transition
        
        this.noiseGate.gain.value = newGain;
    }
    
    /**
     * Starta real-time noise gate processing
     */
    startRealTimeProcessing() {
        if (!this.isInitialized) return;
        
        const processFrame = () => {
            this.updateNoiseGate();
            requestAnimationFrame(processFrame);
        };
        
        console.log('AudioEnhancer: Starting real-time processing');
        requestAnimationFrame(processFrame);
    }
    
    /**
     * Hämta current audio quality metrics
     */
    getAudioMetrics() {
        if (!this.analyser) return null;
        
        this.analyser.getByteFrequencyData(this.frequencyData);
        
        const totalEnergy = this.frequencyData.reduce((sum, val) => sum + val, 0);
        const avgEnergy = totalEnergy / this.frequencyData.length;
        const maxEnergy = Math.max(...this.frequencyData);
        
        // Beräkna signal-to-noise ratio om vi har noise profile
        let snr = null;
        if (this.noiseProfile) {
            const avgNoise = this.noiseProfile.reduce((a, b) => a + b) / this.noiseProfile.length;
            snr = avgEnergy > 0 ? 20 * Math.log10(avgEnergy / Math.max(avgNoise, 1)) : 0;
        }
        
        return {
            avgEnergy,
            maxEnergy,
            signalToNoiseRatio: snr,
            noiseGateLevel: this.noiseGate?.gain.value || 1,
            hasNoiseProfile: !!this.noiseProfile,
            quality: this.assessAudioQuality(avgEnergy, snr)
        };
    }
    
    assessAudioQuality(avgEnergy, snr) {
        if (avgEnergy < 10) return 'too_quiet';
        if (avgEnergy > 200) return 'too_loud'; 
        if (snr !== null && snr < 10) return 'noisy';
        if (snr !== null && snr > 20) return 'excellent';
        return 'good';
    }
    
    /**
     * Cleanup resources
     */
    dispose() {
        if (this.inputGain) this.inputGain.disconnect();
        if (this.highpassFilter) this.highpassFilter.disconnect();
        if (this.lowpassFilter) this.lowpassFilter.disconnect(); 
        if (this.compressor) this.compressor.disconnect();
        if (this.noiseGate) this.noiseGate.disconnect();
        if (this.outputGain) this.outputGain.disconnect();
        if (this.analyser) this.analyser.disconnect();
        
        this.isInitialized = false;
        console.log('AudioEnhancer: Disposed');
    }
}

// Utility function för enkel användning
export function createAudioEnhancer(audioContext) {
    return new AudioEnhancer(audioContext);
}