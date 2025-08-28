// OpenAI Realtime API integration för kontinuerlig transkribering
import { scoreImportance } from './importance';

export interface PartialEvent {
  type: 'partial';
  text: string;
  ts: Date;
  confidence: number;
}

export interface FinalEvent {
  type: 'final';
  text: string;
  ts: Date;
  quality: 'realtime' | 'whisper';
  confidence: number;
  importance?: number;
}

export interface ErrorEvent {
  type: 'error';
  error: string;
  ts: Date;
}

export interface StatusEvent {
  type: 'status';
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  ts: Date;
}

export type ASREvent = PartialEvent | FinalEvent | ErrorEvent | StatusEvent;

export class RealtimeASR {
  private ws: WebSocket | null = null;
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private subs = new Set<(event: ASREvent) => void>();
  private reconnectTimer?: NodeJS.Timeout;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private baseReconnectDelay = 1000;
  
  private config = {
    apiKey: process.env.NEXT_PUBLIC_OPENAI_API_KEY,
    minPartialLength: parseInt(process.env.NEXT_PUBLIC_MIN_PARTIAL_LEN || '8'),
    partialTimeoutMs: 300,
    finalTimeoutMs: 3000,
  };

  constructor() {
    if (!this.config.apiKey) {
      console.error('RealtimeASR: Missing NEXT_PUBLIC_OPENAI_API_KEY');
    }
  }

  on(callback: (event: ASREvent) => void): () => void {
    this.subs.add(callback);
    return () => this.subs.delete(callback);
  }

  async start(mediaStream: MediaStream): Promise<void> {
    if (this.ws || this.mediaStream) {
      await this.stop();
    }

    this.mediaStream = mediaStream;
    this.emit({ type: 'status', status: 'connecting', ts: new Date() });
    
    await this.connectWebSocket();
    await this.setupAudioProcessing();
  }

  async stop(): Promise<void> {
    this.cleanup();
    this.emit({ type: 'status', status: 'disconnected', ts: new Date() });
  }

  private async connectWebSocket(): Promise<void> {
    if (!this.config.apiKey) {
      throw new Error('OpenAI API key not configured');
    }

    // För nu använder vi en mock WebSocket endpoint tills vi har riktigt Realtime API
    // I produktion: wss://api.openai.com/v1/realtime
    const wsUrl = process.env.NEXT_PUBLIC_REALTIME_WS || 'ws://127.0.0.1:8000/ws/realtime-asr';
    
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => {
      console.log('RealtimeASR: Connected');
      this.reconnectAttempts = 0;
      this.emit({ type: 'status', status: 'connected', ts: new Date() });
      
      // Send initial configuration
      this.send({
        type: 'session.update',
        session: {
          modalities: ['text', 'audio'],
          instructions: 'Transkribera svenska tal i realtid. Ge partial och final resultat.',
          voice: 'alloy',
          input_audio_format: 'pcm16',
          output_audio_format: 'pcm16',
          input_audio_transcription: {
            model: 'whisper-1'
          }
        }
      });
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleRealtimeEvent(data);
      } catch (e) {
        console.warn('RealtimeASR: Invalid JSON:', event.data);
      }
    };

    this.ws.onclose = () => {
      console.log('RealtimeASR: Disconnected');
      this.ws = null;
      this.emit({ type: 'status', status: 'disconnected', ts: new Date() });
      this.scheduleReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('RealtimeASR: WebSocket error:', error);
      this.emit({ type: 'error', error: 'WebSocket connection failed', ts: new Date() });
    };
  }

  private async setupAudioProcessing(): Promise<void> {
    if (!this.mediaStream) return;

    this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
      sampleRate: 16000
    });

    const source = this.audioContext.createMediaStreamSource(this.mediaStream);
    
    // Use ScriptProcessorNode for now, will migrate to AudioWorklet later
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
    
    this.processor.onaudioprocess = (event) => {
      const inputBuffer = event.inputBuffer.getChannelData(0);
      
      // Convert to 16-bit PCM
      const pcmData = new Int16Array(inputBuffer.length);
      for (let i = 0; i < inputBuffer.length; i++) {
        pcmData[i] = Math.max(-32768, Math.min(32767, inputBuffer[i] * 32767));
      }
      
      // Send to realtime API
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({
          type: 'input_audio_buffer.append',
          audio: this.arrayBufferToBase64(pcmData.buffer)
        });
      }
    };

    source.connect(this.processor);
    this.processor.connect(this.audioContext.destination);
  }

  private handleRealtimeEvent(data: any): void {
    const now = new Date();
    
    switch (data.type) {
      case 'input_audio_buffer.speech_started':
        // Speech detection началось
        break;
        
      case 'input_audio_buffer.speech_stopped':
        // Speech detection закончилось, trigger finalization
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.send({ type: 'input_audio_buffer.commit' });
          this.send({ type: 'response.create' });
        }
        break;
        
      case 'conversation.item.input_audio_transcription.completed':
        // Partial transcription
        if (data.transcript && data.transcript.length >= this.config.minPartialLength) {
          this.emit({
            type: 'partial',
            text: data.transcript,
            ts: now,
            confidence: 0.8 // Mock confidence, real API provides this
          });
        }
        break;
        
      case 'response.audio_transcript.done':
        // Final transcription
        if (data.transcript) {
          const importance = scoreImportance(data.transcript);
          this.emit({
            type: 'final',
            text: data.transcript,
            ts: now,
            quality: 'realtime',
            confidence: 0.9,
            importance: importance.score
          });
        }
        break;
        
      case 'error':
        this.emit({
          type: 'error',
          error: data.error?.message || 'Unknown realtime error',
          ts: now
        });
        break;
    }
  }

  private send(message: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.emit({ 
        type: 'error', 
        error: 'Max reconnection attempts reached', 
        ts: new Date() 
      });
      return;
    }

    const delay = this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;

    this.reconnectTimer = setTimeout(async () => {
      if (this.mediaStream) {
        try {
          await this.connectWebSocket();
        } catch (error) {
          console.error('RealtimeASR: Reconnection failed:', error);
        }
      }
    }, delay);
  }

  private cleanup(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = undefined;
    }

    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }

    this.reconnectAttempts = 0;
  }

  private emit(event: ASREvent): void {
    this.subs.forEach(callback => callback(event));
  }

  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }
}