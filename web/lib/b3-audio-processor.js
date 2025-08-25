/**
 * B3 Audio Processor - AudioWorklet for continuous audio frame processing
 * Processes audio in 20ms frames at 16kHz for ambient voice streaming
 */

class B3AudioProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super();
        
        // Audio processing parameters
        this.sampleRate = options.processorOptions.sampleRate || 16000;
        this.frameDurationMs = options.processorOptions.frameDurationMs || 20;
        this.frameSize = (this.sampleRate * this.frameDurationMs) / 1000; // 320 samples at 16kHz/20ms
        
        // Frame buffer for accumulating samples
        this.frameBuffer = [];
        this.frameCounter = 0;
        
        // VAD (Voice Activity Detection) parameters
        this.vadThreshold = 0.01; // Energy threshold for voice detection
        this.vadSmoothingFactor = 0.95;
        this.vadEnergy = 0;
        
        console.log(`B3AudioProcessor initialized: ${this.sampleRate}Hz, ${this.frameDurationMs}ms frames`);
    }
    
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        
        // Pass through audio (for monitoring)
        if (input.length > 0 && output.length > 0) {
            for (let channel = 0; channel < output.length; ++channel) {
                output[channel].set(input[channel] || input[0]);
            }
        }
        
        // Process input for frame extraction
        if (input.length > 0 && input[0]) {
            this.processAudioInput(input[0]);
        }
        
        return true; // Keep processor alive
    }
    
    processAudioInput(audioData) {
        // Add samples to frame buffer
        for (let i = 0; i < audioData.length; i++) {
            this.frameBuffer.push(audioData[i]);
            
            // When frame buffer is full, process frame
            if (this.frameBuffer.length >= this.frameSize) {
                this.processFrame();
            }
        }
    }
    
    processFrame() {
        // Extract frame from buffer
        const frame = new Float32Array(this.frameBuffer.slice(0, this.frameSize));
        
        // Calculate frame energy for VAD
        const energy = this.calculateFrameEnergy(frame);
        
        // Smooth energy with exponential moving average
        this.vadEnergy = this.vadSmoothingFactor * this.vadEnergy + 
                         (1 - this.vadSmoothingFactor) * energy;
        
        // Voice activity detection
        const hasVoiceActivity = this.vadEnergy > this.vadThreshold;
        
        // Send frame to main thread
        this.port.postMessage({
            type: 'audio_frame',
            frame: frame,
            timestamp: currentTime,
            frameCounter: this.frameCounter++,
            energy: energy,
            vadEnergy: this.vadEnergy,
            hasVoiceActivity: hasVoiceActivity
        });
        
        // Remove processed samples, keep overlap for better processing
        const overlap = Math.floor(this.frameSize * 0.1); // 10% overlap
        this.frameBuffer = this.frameBuffer.slice(this.frameSize - overlap);
    }
    
    calculateFrameEnergy(frame) {
        let energy = 0;
        for (let i = 0; i < frame.length; i++) {
            energy += frame[i] * frame[i];
        }
        return energy / frame.length; // RMS energy
    }
}

// Register the processor
registerProcessor('b3-audio-processor', B3AudioProcessor);