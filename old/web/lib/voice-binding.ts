/**
 * Voice UI Binding - Connects voice-adapter to Alice UI
 * Handles mic capture, audio playback, and UI state management
 * Now with GDPR-compliant consent and content filtering
 */
import { 
  initVoiceAdapter, 
  type VoiceProvider, 
  type VoiceMetrics, 
  type ASROptions, 
  type TTSOptions 
} from '@alice/voice-adapter';
import { ConsentStore } from './consent-store';
import { ContentFilter } from './content-filter';
import { AgentClient, type AgentMetrics } from './agent-client';

export type VoiceState = 'idle' | 'listening' | 'thinking' | 'thinking_tools' | 'speaking' | 'error';

export interface VoiceUICallbacks {
  onStateChange: (state: VoiceState) => void;
  onPartialTranscript: (text: string, confidence: number) => void;
  onFinalTranscript: (text: string, confidence: number) => void;
  onSpeakingStart: () => void;
  onSpeakingEnd: () => void;
  onError: (error: string) => void;
  onMetrics: (metrics: VoiceMetrics) => void;
}

export class VoiceUIBinding {
  private provider: VoiceProvider | null = null;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private audioWorklet: AudioWorkletNode | null = null;
  private state: VoiceState = 'idle';
  private callbacks: VoiceUICallbacks;
  private isInitialized = false;
  private vadEnabled = true;
  private vadThreshold = 0.01; // RMS energy threshold for voice detection
  private vadGracePeriod = 300; // ms to wait before triggering barge-in
  private lastVadActivity = 0;
  private bargeInTimeout: NodeJS.Timeout | null = null;
  private audioQueue: AudioBuffer[] = [];
  private audioSource: AudioBufferSourceNode | null = null;
  private isPlayingAudio = false;
  private agentClient: AgentClient;
  private currentToolName: string | null = null;
  
  constructor(callbacks: VoiceUICallbacks) {
    this.callbacks = callbacks;
    this.agentClient = new AgentClient();
  }
  
  async initialize(): Promise<void> {
    if (this.isInitialized) return;
    
    // Check consent before initializing
    if (ConsentStore.isConsentRequired() && !ConsentStore.hasValidConsent()) {
      throw new Error('CONSENT_REQUIRED');
    }
    
    try {
      // Initialize voice provider
      this.provider = await initVoiceAdapter({
        provider: process.env.NEXT_PUBLIC_VOICE_PROVIDER || 'openai',
        openaiApiKey: process.env.NEXT_PUBLIC_OPENAI_API_KEY,
        metricsEndpoint: process.env.NEXT_PUBLIC_METRICS_EXPORT_ENDPOINT
      });
      
      // Set up event listeners
      this.setupProviderEvents();
      
      // Initialize audio context
      this.audioContext = new AudioContext({
        sampleRate: parseInt(process.env.NEXT_PUBLIC_AUDIO_SAMPLE_RATE || '16000')
      });
      
      // Load audio worklet for processing
      await this.setupAudioWorklet();
      
      this.isInitialized = true;
      this.setState('idle');
      
    } catch (error) {
      console.error('Failed to initialize voice binding:', error);
      this.setState('error');
      this.callbacks.onError(`Initieringen misslyckades: ${error}`);
    }
  }
  
  private async setupAudioWorklet(): Promise<void> {
    if (!this.audioContext) throw new Error('AudioContext not initialized');
    
    // For now, use ScriptProcessorNode (deprecated but widely supported)
    // In production, we'd want to use AudioWorklet
    this.setupScriptProcessor();
  }
  
  private setupScriptProcessor(): void {
    if (!this.audioContext) return;
    
    // Create a simple processor for audio capture
    const bufferSize = 4096;
    const processor = this.audioContext.createScriptProcessor(bufferSize, 1, 1);
    
    processor.onaudioprocess = (event) => {
      if (!this.provider?.asr.isListening()) return;
      
      const inputBuffer = event.inputBuffer;
      const inputData = inputBuffer.getChannelData(0);
      
      // Calculate RMS for VAD
      let rms = 0;
      for (let i = 0; i < inputData.length; i++) {
        rms += inputData[i] * inputData[i];
      }
      rms = Math.sqrt(rms / inputData.length);
      
      // Handle VAD for barge-in detection
      this.handleVAD(rms > this.vadThreshold, rms);
      
      // Convert Float32Array to Int16Array for voice provider
      const int16Data = new Int16Array(inputData.length);
      for (let i = 0; i < inputData.length; i++) {
        int16Data[i] = Math.round(inputData[i] * 32767);
      }
      
      // Send to voice provider
      this.provider?.asr.pushAudio(int16Data);
    };
    
    this.audioWorklet = processor as any; // Type compatibility
  }
  
  private handleVAD(voiceActivity: boolean, rms: number): void {
    if (!this.vadEnabled) return;
    
    const now = Date.now();
    
    if (voiceActivity) {
      this.lastVadActivity = now;
      
      // If we're currently speaking (TTS playback), trigger barge-in
      if (this.state === 'speaking' && this.isPlayingAudio) {
        if (this.bargeInTimeout) {
          clearTimeout(this.bargeInTimeout);
        }
        
        // Start grace period before actual barge-in
        this.bargeInTimeout = setTimeout(() => {
          this.triggerBargeIn();
        }, this.vadGracePeriod);
      }
    } else {
      // Cancel barge-in if voice activity stops within grace period
      if (this.bargeInTimeout && (now - this.lastVadActivity) > 100) {
        clearTimeout(this.bargeInTimeout);
        this.bargeInTimeout = null;
      }
    }
  }
  
  private async triggerBargeIn(): Promise<void> {
    console.log('🎯 Barge-in triggered - cancelling TTS and restarting ASR');
    
    // Cancel current TTS playback
    await this.cancel();
    
    // Clear the barge-in timeout
    if (this.bargeInTimeout) {
      clearTimeout(this.bargeInTimeout);
      this.bargeInTimeout = null;
    }
    
    // Immediately restart ASR for new input
    if (this.provider && this.mediaStream) {
      this.setState('listening');
      
      // Restart ASR with fresh state
      const asrOptions: ASROptions = {
        language: 'sv-SE',
        continuous: true,
        interimResults: true,
        sampleRate: this.audioContext?.sampleRate || 24000
      };
      
      await this.provider.asr.start(asrOptions, {
        onStart: () => {
          console.log('🎤 ASR restarted after barge-in');
        },
        onPartial: (result) => {
          this.callbacks.onPartialTranscript(result.text, result.confidence);
        },
        onFinal: (result) => {
          this.callbacks.onFinalTranscript(result.text, result.confidence);
          this.setState('thinking');
          
          // Process with agent instead of echo
          this.processWithAgent(result.text);
        },
        onError: (error) => {
          this.callbacks.onError(error.message);
          this.setState('error');
        }
      });
    }
  }
  
  private setupProviderEvents(): void {
    if (!this.provider) return;
    
    // ASR Events
    this.provider.on('asr:partial', (result) => {
      this.callbacks.onPartialTranscript(result.text, result.confidence);
    });
    
    this.provider.on('asr:final', (result) => {
      this.callbacks.onFinalTranscript(result.text, result.confidence);
      this.setState('thinking');
    });
    
    // TTS Events
    this.provider.on('tts:start', () => {
      this.setState('speaking');
      this.callbacks.onSpeakingStart();
    });
    
    this.provider.on('tts:chunk', (chunk) => {
      this.handleAudioChunk(chunk.data);
    });
    
    this.provider.on('tts:end', () => {
      this.setState('idle');
      this.callbacks.onSpeakingEnd();
    });
    
    // Metrics Events
    this.provider.on('metrics:collected', (metrics) => {
      this.callbacks.onMetrics(metrics);
      // Send metrics to shadow report API
      this.sendMetricsToAPI(metrics).catch(console.error);
    });
    
    // Error Events
    this.provider.on('error', (error) => {
      console.error('Voice provider error:', error);
      this.setState('error');
      this.callbacks.onError(error.message);
    });
  }
  
  async startListening(): Promise<void> {
    if (!this.isInitialized || !this.provider || !this.audioContext) {
      throw new Error('Voice binding not initialized');
    }
    
    if (this.state !== 'idle') {
      console.warn('Cannot start listening - not in idle state');
      return;
    }
    
    try {
      // Request microphone access
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.audioContext.sampleRate,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      
      // Connect microphone to audio processing
      const source = this.audioContext.createMediaStreamSource(this.mediaStream);
      if (this.audioWorklet) {
        source.connect(this.audioWorklet);
        this.audioWorklet.connect(this.audioContext.destination);
      }
      
      // Start ASR
      const asrOptions: ASROptions = {
        language: 'sv-SE',
        continuous: true,
        interimResults: true,
        sampleRate: this.audioContext.sampleRate
      };
      
      await this.provider.asr.start(asrOptions, {
        onStart: () => {
          this.setState('listening');
        },
        onPartial: (result) => {
          this.callbacks.onPartialTranscript(result.text, result.confidence);
        },
        onFinal: (result) => {
          this.callbacks.onFinalTranscript(result.text, result.confidence);
          this.setState('thinking');
          
          // Process with agent instead of echo
          this.processWithAgent(result.text);
        },
        onError: (error) => {
          this.callbacks.onError(error.message);
          this.setState('error');
        }
      });
      
    } catch (error) {
      console.error('Failed to start listening:', error);
      this.setState('error');
      this.callbacks.onError('Mikrofonåtkomst nekades. Tillåt åtkomst i webbläsaren och försök igen.');
    }
  }
  
  async stopListening(): Promise<void> {
    if (this.provider?.asr.isListening()) {
      await this.provider.asr.stop();
    }
    
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }
    
    this.setState('idle');
  }
  
  async speakText(text: string): Promise<void> {
    if (!this.provider || !this.isInitialized) {
      throw new Error('Voice binding not initialized');
    }
    
    // Content filtering before TTS
    const filterResult = await ContentFilter.filterText(text);
    if (!filterResult.allowed) {
      this.setState('error');
      this.callbacks.onError(`Innehåll blockerat: ${filterResult.reason}${filterResult.suggestion ? `. ${filterResult.suggestion}` : ''}`);
      return;
    }
    
    // Log voice usage for compliance
    await ConsentStore.logVoiceUsage(
      process.env.NEXT_PUBLIC_VOICE_PROVIDER || 'openai',
      process.env.NEXT_PUBLIC_OPENAI_REALTIME_MODEL || 'gpt-4o-realtime-preview'
    );
    
    const ttsOptions: TTSOptions = {
      text,
      voiceId: process.env.NEXT_PUBLIC_OPENAI_REALTIME_VOICE || 'nova',
      format: 'pcm16',
      sampleRate: this.audioContext?.sampleRate || 24000
    };
    
    await this.provider.tts.speak(ttsOptions, {
      onStart: (playbackId) => {
        this.setState('speaking');
        this.callbacks.onSpeakingStart();
      },
      onAudioChunk: (chunk) => {
        this.handleAudioChunk(chunk.data);
      },
      onEnd: (playbackId) => {
        this.setState('idle');
        this.callbacks.onSpeakingEnd();
      },
      onError: (error, playbackId) => {
        console.error('TTS error:', error);
        this.callbacks.onError(error.message);
        this.setState('error');
      }
    });
  }
  
  private handleAudioChunk(audioData: ArrayBuffer): void {
    if (!this.audioContext) return;
    
    // Convert PCM16 to AudioBuffer for playback
    this.audioContext.decodeAudioData(audioData.slice(0)).then(audioBuffer => {
      this.playAudioBuffer(audioBuffer);
    }).catch(error => {
      console.warn('Failed to decode audio chunk:', error);
      // Try alternative approach for PCM16
      this.playPCM16Audio(audioData);
    });
  }
  
  private playAudioBuffer(buffer: AudioBuffer): void {
    if (!this.audioContext) return;
    
    // Don't play if we're not in speaking state (interrupted)
    if (this.state !== 'speaking') return;
    
    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioContext.destination);
    
    source.onended = () => {
      this.isPlayingAudio = false;
      this.audioSource = null;
    };
    
    source.start();
    this.audioSource = source;
    this.isPlayingAudio = true;
  }
  
  private playPCM16Audio(pcmData: ArrayBuffer): void {
    if (!this.audioContext) return;
    
    // Convert PCM16 to Float32 for Web Audio API
    const int16Array = new Int16Array(pcmData);
    const float32Array = new Float32Array(int16Array.length);
    
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32767;
    }
    
    // Create audio buffer
    const audioBuffer = this.audioContext.createBuffer(1, float32Array.length, this.audioContext.sampleRate);
    audioBuffer.getChannelData(0).set(float32Array);
    
    this.playAudioBuffer(audioBuffer);
  }
  
  async cancel(): Promise<void> {
    console.log('🛑 Cancelling current TTS playback');
    
    // Stop current audio playback immediately
    if (this.audioSource) {
      this.audioSource.stop();
      this.audioSource = null;
    }
    this.isPlayingAudio = false;
    
    // Cancel TTS at provider level
    if (this.provider?.tts.isSpeaking()) {
      await this.provider.tts.cancelAll();
    }
    
    // Clear any barge-in timeouts
    if (this.bargeInTimeout) {
      clearTimeout(this.bargeInTimeout);
      this.bargeInTimeout = null;
    }
    
    // If we were listening, keep listening - don't stop ASR for barge-in
    if (!this.provider?.asr.isListening()) {
      this.setState('idle');
    }
  }
  
  private setState(newState: VoiceState): void {
    if (this.state !== newState) {
      this.state = newState;
      this.callbacks.onStateChange(newState);
    }
  }
  
  getState(): VoiceState {
    return this.state;
  }
  
  async getMetrics(): Promise<VoiceMetrics | null> {
    if (!this.provider) return null;
    return this.provider.getMetrics();
  }
  
  private async sendMetricsToAPI(metrics: VoiceMetrics): Promise<void> {
    try {
      const endpoint = process.env.NEXT_PUBLIC_METRICS_EXPORT_ENDPOINT || '/api/metrics/voice';
      
      await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          timestamp_ms: metrics.timestamp_ms,
          session_id: metrics.session_id,
          asr_partial_latency_ms: metrics.asr_partial_latency_ms,
          asr_final_latency_ms: metrics.asr_final_latency_ms,
          llm_latency_ms: metrics.llm_latency_ms,
          tts_ttfa_ms: metrics.tts_ttfa_ms,
          e2e_roundtrip_ms: metrics.e2e_roundtrip_ms,
          provider: metrics.provider,
          error_count: metrics.error_count
        })
      });
    } catch (error) {
      console.warn('Failed to send metrics to API:', error);
    }
  }
  
  // Barge-in configuration methods
  setVADEnabled(enabled: boolean): void {
    this.vadEnabled = enabled;
    console.log(`🎯 VAD/Barge-in ${enabled ? 'enabled' : 'disabled'}`);
  }
  
  setVADThreshold(threshold: number): void {
    this.vadThreshold = Math.max(0.001, Math.min(0.1, threshold));
    console.log(`🎯 VAD threshold set to ${this.vadThreshold}`);
  }
  
  setVADGracePeriod(ms: number): void {
    this.vadGracePeriod = Math.max(100, Math.min(1000, ms));
    console.log(`🎯 VAD grace period set to ${this.vadGracePeriod}ms`);
  }
  
  getBargeInConfig(): { enabled: boolean; threshold: number; gracePeriod: number } {
    return {
      enabled: this.vadEnabled,
      threshold: this.vadThreshold,
      gracePeriod: this.vadGracePeriod
    };
  }
  
  async destroy(): Promise<void> {
    await this.cancel();
    
    // Clear any pending timeouts
    if (this.bargeInTimeout) {
      clearTimeout(this.bargeInTimeout);
      this.bargeInTimeout = null;
    }
    
    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }
    
    if (this.provider) {
      await this.provider.destroy();
      this.provider = null;
    }
    
    this.isInitialized = false;
  }

  // Process user input with agent (replaces echo behavior)
  private async processWithAgent(userText: string): Promise<void> {
    try {
      console.log(`🤖 Processing with agent: "${userText}"`);
      
      const result = await this.agentClient.processUserMessage(
        userText,
        // onThinking callback
        () => {
          console.log('🤔 Agent thinking...');
          this.setState('thinking');
        },
        // onToolExecution callback  
        (toolName: string, toolArgs: any) => {
          console.log(`🔧 Executing tool: ${toolName}`, toolArgs);
          this.currentToolName = toolName;
          this.setState('thinking_tools');
        },
        // onProgress callback
        (metrics) => {
          console.log('📊 Agent progress:', metrics);
          // Could emit progress events here if needed
        }
      );

      // Agent processing complete, speak the response
      console.log(`💬 Agent response: "${result.text}"`);
      this.currentToolName = null;
      
      // Enhanced metrics with agent data
      const enhancedMetrics: VoiceMetrics = {
        session_id: this.agentClient.getSessionId(),
        asr_partial_latency_ms: 0, // These would come from ASR
        asr_final_latency_ms: 0,
        llm_latency_ms: result.metrics.llm_latency_ms,
        tts_ttfa_ms: 0, // Will be set by TTS
        e2e_roundtrip_ms: Date.now() - (result.metrics.phase_timestamps.asr_final_ts || Date.now()),
        tool_duration_ms: result.metrics.tool_duration_ms,
        tool_call_count: result.metrics.tool_call_count,
        tool_error_count: result.metrics.tool_error_count,
        provider: 'agent+openai'
      };

      // Update metrics callback
      this.callbacks.onMetrics(enhancedMetrics);

      // Speak the agent response
      await this.speakText(result.text);

    } catch (error) {
      console.error('❌ Agent processing failed:', error);
      this.setState('error');
      this.callbacks.onError(`Agent error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  // Get current tool name (for UI display)
  getCurrentToolName(): string | null {
    return this.currentToolName;
  }

  // Get agent session info  
  getAgentSessionId(): string {
    return this.agentClient.getSessionId();
  }

  // Clear conversation history
  clearAgentHistory(): void {
    this.agentClient.clearConversation();
  }
}