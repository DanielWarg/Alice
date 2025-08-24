// Huvudorchestrator för Always-On Voice systemet
import { RealtimeASR, ASREvent } from './RealtimeASR';
import { AmbientBuffer, AmbientEvent } from './AmbientBuffer';

export interface OrchestratorConfig {
  voiceMode: 'always' | 'ptt';
  asrBackend: 'realtime' | 'browser';
  ambientEnabled: boolean;
  echoCancellation: boolean;
  noiseSuppression: boolean;
  autoGainControl: boolean;
}

export interface OrchestratorStatus {
  micPermission: 'pending' | 'granted' | 'denied';
  asrStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  isListening: boolean;
  lastPartial?: string;
  bufferStats?: {
    totalChunks: number;
    highScoreChunks: number;
  };
}

export interface OrchestratorEvent {
  type: 'status_change';
  status: OrchestratorStatus;
  ts: Date;
}

export class Orchestrator {
  private config: OrchestratorConfig;
  private status: OrchestratorStatus;
  private realtimeASR: RealtimeASR;
  private ambientBuffer: AmbientBuffer;
  private mediaStream: MediaStream | null = null;
  private subs = new Set<(event: OrchestratorEvent) => void>();

  constructor(config?: Partial<OrchestratorConfig>) {
    this.config = {
      voiceMode: (process.env.NEXT_PUBLIC_VOICE_MODE as 'always' | 'ptt') || 'always',
      asrBackend: (process.env.NEXT_PUBLIC_ASR_BACKEND as 'realtime' | 'browser') || 'realtime',
      ambientEnabled: process.env.NEXT_PUBLIC_AMBIENT_ENABLED === 'true',
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      ...config
    };

    this.status = {
      micPermission: 'pending',
      asrStatus: 'disconnected',
      isListening: false
    };

    this.realtimeASR = new RealtimeASR();
    this.ambientBuffer = new AmbientBuffer();

    this.setupEventHandlers();

    // Auto-start om always mode
    if (this.config.voiceMode === 'always') {
      this.start().catch(error => {
        console.error('Orchestrator: Auto-start failed:', error);
      });
    }
  }

  on(callback: (event: OrchestratorEvent) => void): () => void {
    this.subs.add(callback);
    return () => this.subs.delete(callback);
  }

  async start(): Promise<void> {
    try {
      console.log('Orchestrator: Starting always-on voice system...');
      
      // Be om mikrofonåtkomst
      await this.requestMicrophonePermission();
      
      // Starta ASR
      if (this.config.asrBackend === 'realtime' && this.mediaStream) {
        await this.realtimeASR.start(this.mediaStream);
      }

      this.updateStatus({ isListening: true });
      console.log('Orchestrator: Always-on voice system started');
      
    } catch (error) {
      console.error('Orchestrator: Failed to start:', error);
      this.updateStatus({ 
        micPermission: 'denied',
        asrStatus: 'error',
        isListening: false 
      });
      throw error;
    }
  }

  async stop(): Promise<void> {
    console.log('Orchestrator: Stopping voice system...');
    
    await this.realtimeASR.stop();
    this.ambientBuffer.stop();
    
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }

    this.updateStatus({
      asrStatus: 'disconnected',
      isListening: false,
      lastPartial: undefined
    });
  }

  toggleListening(): Promise<void> {
    return this.status.isListening ? this.stop() : this.start();
  }

  getStatus(): OrchestratorStatus {
    return { 
      ...this.status, 
      bufferStats: this.ambientBuffer.getBufferStats() 
    };
  }

  private async requestMicrophonePermission(): Promise<void> {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error('getUserMedia is not supported in this browser');
    }

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: this.config.echoCancellation,
          noiseSuppression: this.config.noiseSuppression,
          autoGainControl: this.config.autoGainControl,
          channelCount: 1,
          sampleRate: 16000
        }
      });

      this.updateStatus({ micPermission: 'granted' });
      console.log('Orchestrator: Microphone access granted');
      
    } catch (error) {
      this.updateStatus({ micPermission: 'denied' });
      console.error('Orchestrator: Microphone access denied:', error);
      throw new Error(`Microphone access denied: ${error}`);
    }
  }

  private setupEventHandlers(): void {
    // ASR events
    this.realtimeASR.on((event: ASREvent) => {
      switch (event.type) {
        case 'status':
          this.updateStatus({ asrStatus: event.status });
          break;
          
        case 'partial':
          this.updateStatus({ lastPartial: event.text });
          if (this.config.ambientEnabled) {
            this.ambientBuffer.addPartial(event);
          }
          break;
          
        case 'final':
          if (this.config.ambientEnabled) {
            this.ambientBuffer.addFinal(event);
          }
          break;
          
        case 'error':
          console.error('Orchestrator: ASR error:', event.error);
          this.updateStatus({ asrStatus: 'error' });
          break;
      }
    });

    // Ambient buffer events
    this.ambientBuffer.on((event: AmbientEvent) => {
      switch (event.type) {
        case 'chunk_added':
          console.log(`Ambient: Added chunk (${event.chunk.importance?.score}/3): "${event.chunk.text.slice(0, 50)}..."`);
          break;
          
        case 'summary_created':
          console.log(`Ambient: Created summary with ${event.summary.highlights.length} highlights`);
          break;
          
        case 'error':
          console.error('Orchestrator: Ambient error:', event.error);
          break;
      }
    });
  }

  private updateStatus(updates: Partial<OrchestratorStatus>): void {
    const prevStatus = { ...this.status };
    this.status = { ...this.status, ...updates };
    
    // Emit bara om något faktiskt ändrats
    const hasChanged = Object.keys(updates).some(
      key => prevStatus[key as keyof OrchestratorStatus] !== this.status[key as keyof OrchestratorStatus]
    );
    
    if (hasChanged) {
      this.emit({
        type: 'status_change',
        status: this.getStatus(),
        ts: new Date()
      });
    }
  }

  private emit(event: OrchestratorEvent): void {
    this.subs.forEach(callback => callback(event));
  }

  // Debug methods
  async testMicrophone(): Promise<boolean> {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(track => track.stop());
      return true;
    } catch {
      return false;
    }
  }

  getConfig(): OrchestratorConfig {
    return { ...this.config };
  }

  updateConfig(updates: Partial<OrchestratorConfig>): void {
    const needsRestart = this.status.isListening && (
      updates.asrBackend || 
      updates.voiceMode ||
      updates.echoCancellation !== undefined ||
      updates.noiseSuppression !== undefined ||
      updates.autoGainControl !== undefined
    );

    this.config = { ...this.config, ...updates };

    if (needsRestart) {
      console.log('Orchestrator: Config changed, restarting...');
      this.stop().then(() => this.start()).catch(console.error);
    }
  }
}