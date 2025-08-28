import WebSocket from 'ws';
import { BaseVoiceProvider, StreamingASRAdapter, StreamingTTSAdapter, AdapterUtils } from '../adapters';
import {
  VoiceProviderConfig,
  AudioChunk,
  TranscriptResult,
  TTSRequest,
  TTSResult,
  AudioFormat,
  PerformanceMetrics,
  OpenAIRealtime,
  ConnectionError,
  ASRError,
  TTSError,
  DEFAULT_AUDIO_FORMAT
} from '../types';

/**
 * OpenAI Realtime API Provider
 * Implements real-time voice conversation using OpenAI's Realtime API
 */
export class OpenAIRealtimeProvider extends BaseVoiceProvider {
  private ws: WebSocket | null = null;
  private sessionConfig: OpenAIRealtime.SessionConfig;
  private audioBuffer: Buffer = Buffer.alloc(0);
  private responseAudioBuffer: Buffer = Buffer.alloc(0);
  private sessionId: string | null = null;
  private conversationId: string | null = null;
  private isSessionActive: boolean = false;

  constructor(config: VoiceProviderConfig) {
    super(config);

    if (!config.openai?.apiKey) {
      throw new Error('OpenAI API key is required');
    }

    // Initialize session configuration
    this.sessionConfig = {
      modalities: ['text', 'audio'],
      instructions: config.openai.instructions || 'You are a helpful AI assistant.',
      voice: config.openai.voice || 'alloy',
      input_audio_format: 'pcm16',
      output_audio_format: 'pcm16',
      input_audio_transcription: {
        model: 'whisper-1'
      },
      turn_detection: {
        type: 'server_vad',
        threshold: 0.5,
        prefix_padding_ms: 300,
        silence_duration_ms: 200
      },
      temperature: config.openai.temperature || 0.8,
      max_response_output_tokens: config.openai.maxTokens || 4096
    };

    // Create ASR and TTS adapters
    this.asrAdapter = new OpenAIRealtimeASRAdapter(this, config);
    this.ttsAdapter = new OpenAIRealtimeTTSAdapter(this, config);

    this.initializeMetrics();
  }

  async connect(): Promise<void> {
    try {
      this.setState('connecting');

      const url = 'wss://api.openai.com/v1/realtime?model=' + 
        (this.config.openai?.model || 'gpt-4o-realtime-preview-2024-10-01');

      this.ws = new WebSocket(url, {
        headers: {
          'Authorization': `Bearer ${this.config.openai?.apiKey}`,
          'OpenAI-Beta': 'realtime=v1'
        }
      });

      await new Promise<void>((resolve, reject) => {
        if (!this.ws) return reject(new Error('WebSocket not initialized'));

        this.ws.on('open', () => {
          this.setupWebSocketHandlers();
          this.setState('connected');
          resolve();
        });

        this.ws.on('error', (error) => {
          reject(new ConnectionError('Failed to connect to OpenAI Realtime API', 'openai-realtime', error));
        });

        // Set timeout for connection
        setTimeout(() => {
          reject(new ConnectionError('Connection timeout', 'openai-realtime'));
        }, 10000);
      });

      // Configure session
      await this.configureSession();

    } catch (error) {
      this.handleError(error instanceof Error ? error : new Error('Unknown connection error'));
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.isSessionActive = false;
    this.sessionId = null;
    this.conversationId = null;
    this.audioBuffer = Buffer.alloc(0);
    this.responseAudioBuffer = Buffer.alloc(0);
    
    this.setState('disconnected');
  }

  async sendAudio(chunk: AudioChunk): Promise<void> {
    if (!this.ws || this.state !== 'connected' || !this.isSessionActive) {
      throw new Error('Provider not connected or session not active');
    }

    try {
      AdapterUtils.validateAudioChunk(chunk);

      // Convert audio to base64
      const audioBase64 = chunk.data.toString('base64');

      // Send audio buffer append event
      const event: OpenAIRealtime.InputAudioBufferAppend = {
        type: 'input_audio_buffer.append',
        audio: audioBase64
      };

      this.sendEvent(event);
      this.emit('audio_input', chunk);

    } catch (error) {
      throw new ASRError('Failed to send audio', error instanceof Error ? error : undefined);
    }
  }

  async sendText(text: string): Promise<void> {
    if (!this.ws || this.state !== 'connected' || !this.isSessionActive) {
      throw new Error('Provider not connected or session not active');
    }

    try {
      // Commit any buffered audio first
      this.sendEvent({ type: 'input_audio_buffer.commit' });

      // Create response with text input
      const event: OpenAIRealtime.ResponseCreate = {
        type: 'response.create',
        response: {
          modalities: ['text', 'audio'],
          instructions: `Respond to this text: "${text}"`
        }
      };

      this.sendEvent(event);

    } catch (error) {
      throw new Error(`Failed to send text: ${error}`);
    }
  }

  async startSession(): Promise<void> {
    if (!this.ws || this.state !== 'connected') {
      throw new Error('Provider not connected');
    }

    this.isSessionActive = true;
    this.setState('active');
    
    if (this.asrAdapter) {
      await this.asrAdapter.start();
    }
    
    if (this.ttsAdapter) {
      await this.ttsAdapter.startStream();
    }
  }

  async endSession(): Promise<void> {
    if (this.asrAdapter) {
      await this.asrAdapter.stop();
    }
    
    if (this.ttsAdapter) {
      await this.ttsAdapter.stopStream();
    }

    this.isSessionActive = false;
    this.setState('connected');
  }

  private async configureSession(): Promise<void> {
    const event = {
      type: 'session.update',
      session: this.sessionConfig
    };

    this.sendEvent(event);
  }

  private setupWebSocketHandlers(): void {
    if (!this.ws) return;

    this.ws.on('message', (data) => {
      try {
        const event = JSON.parse(data.toString());
        this.handleRealtimeEvent(event);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    });

    this.ws.on('close', () => {
      this.setState('disconnected');
      this.emit('disconnected');
    });

    this.ws.on('error', (error) => {
      this.handleError(new ConnectionError('WebSocket error', 'openai-realtime', error));
    });
  }

  private handleRealtimeEvent(event: OpenAIRealtime.RealtimeEvent): void {
    switch (event.type) {
      case 'session.created':
        this.sessionId = event.session?.id;
        break;

      case 'conversation.created':
        this.conversationId = event.conversation?.id;
        break;

      case 'input_audio_buffer.speech_started':
        this.emit('voice_start', {
          isVoiceActive: true,
          confidence: 1.0,
          timestamp: Date.now(),
          energyLevel: 0.5
        });
        break;

      case 'input_audio_buffer.speech_stopped':
        this.emit('voice_end', {
          isVoiceActive: false,
          confidence: 1.0,
          timestamp: Date.now(),
          energyLevel: 0.0
        });
        // Commit the audio buffer
        this.sendEvent({ type: 'input_audio_buffer.commit' });
        break;

      case 'conversation.item.input_audio_transcription.completed':
        const transcriptResult: TranscriptResult = {
          text: event.transcript || '',
          confidence: 0.9,
          isFinal: true,
          timestamp: Date.now()
        };
        this.emit('transcript', transcriptResult);
        break;

      case 'response.audio.delta':
        if (event.delta) {
          const audioData = Buffer.from(event.delta, 'base64');
          this.responseAudioBuffer = Buffer.concat([this.responseAudioBuffer, audioData]);
        }
        break;

      case 'response.audio.done':
        if (this.responseAudioBuffer.length > 0) {
          const audioChunk: AudioChunk = AdapterUtils.createAudioChunk(
            this.responseAudioBuffer,
            DEFAULT_AUDIO_FORMAT,
            Date.now()
          );
          
          this.emit('audio_output', audioChunk);
          this.responseAudioBuffer = Buffer.alloc(0);
        }
        break;

      case 'response.text.delta':
        // Handle streaming text response
        break;

      case 'response.done':
        this.updateMetrics();
        break;

      case 'error':
        this.handleError(new Error(`OpenAI Realtime API error: ${event.error?.message || 'Unknown error'}`));
        break;
    }
  }

  private sendEvent(event: any): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    this.ws.send(JSON.stringify(event));
  }

  private initializeMetrics(): void {
    this.metrics = {
      latency: {
        asr: 0,
        tts: 0,
        endToEnd: 0
      },
      throughput: {
        audioProcessed: 0,
        messagesPerSecond: 0
      },
      quality: {
        audioQuality: 1.0,
        transcriptAccuracy: 0.9
      },
      timestamps: {
        requestStart: 0,
        asrComplete: 0,
        ttsStart: 0,
        ttsComplete: 0,
        responseEnd: 0
      }
    };
  }

  private updateMetrics(): void {
    if (!this.metrics) return;

    const now = Date.now();
    const endToEnd = now - this.metrics.timestamps.requestStart;
    
    this.metrics.latency.endToEnd = endToEnd;
    this.metrics.timestamps.responseEnd = now;
    
    this.emit('metrics', this.metrics);
    this.emit('latency_update', endToEnd, 'endToEnd');
  }

  // Public method to get WebSocket for adapters
  getWebSocket(): WebSocket | null {
    return this.ws;
  }

  // Public method to send events from adapters
  sendRealtimeEvent(event: any): void {
    this.sendEvent(event);
  }
}

/**
 * OpenAI Realtime ASR Adapter
 */
class OpenAIRealtimeASRAdapter extends StreamingASRAdapter {
  constructor(
    private provider: OpenAIRealtimeProvider,
    config: VoiceProviderConfig
  ) {
    super(config);
    this.supportedFormats = [{
      sampleRate: 24000,
      channels: 1,
      bitDepth: 16,
      encoding: 'pcm'
    }];
  }

  protected async initializeStream(): Promise<void> {
    // Stream initialization handled by provider
  }

  protected async cleanupStream(): Promise<void> {
    // Stream cleanup handled by provider
  }

  protected async processBufferedAudio(timestamp: number): Promise<void> {
    if (this.audioBuffer.length === 0) return;

    try {
      const chunk = AdapterUtils.createAudioChunk(
        this.audioBuffer,
        this.supportedFormats[0]!,
        timestamp,
        this.getNextSequenceId()
      );

      await this.provider.sendAudio(chunk);
      this.audioBuffer = Buffer.alloc(0);

    } catch (error) {
      this.handleError(error instanceof Error ? error : new Error('Audio processing failed'));
    }
  }
}

/**
 * OpenAI Realtime TTS Adapter
 */
class OpenAIRealtimeTTSAdapter extends StreamingTTSAdapter {
  constructor(
    private provider: OpenAIRealtimeProvider,
    config: VoiceProviderConfig
  ) {
    super(config);
    this.supportedFormats = [{
      sampleRate: 24000,
      channels: 1,
      bitDepth: 16,
      encoding: 'pcm'
    }];
    this.availableVoices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'];
    this.currentVoice = config.openai?.voice || 'alloy';
  }

  async synthesize(request: TTSRequest): Promise<TTSResult> {
    try {
      await this.provider.sendText(request.text);

      // Return a promise that resolves when audio is received
      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new TTSError('TTS synthesis timeout'));
        }, 10000);

        this.provider.once('audio_output', (audioChunk: AudioChunk) => {
          clearTimeout(timeout);
          resolve({
            audio: audioChunk,
            text: request.text,
            voice: this.currentVoice,
            metadata: {
              duration: audioChunk.duration
            }
          });
        });

        this.provider.once('error', (error) => {
          clearTimeout(timeout);
          reject(new TTSError('TTS synthesis failed', error));
        });
      });

    } catch (error) {
      throw new TTSError('Failed to synthesize speech', error instanceof Error ? error : undefined);
    }
  }

  protected async initializeStream(): Promise<void> {
    // Stream initialization handled by provider
  }

  protected async cleanupStream(): Promise<void> {
    this.textQueue = [];
  }

  protected async processTextQueue(): Promise<void> {
    while (this.textQueue.length > 0) {
      const text = this.textQueue.shift();
      if (text) {
        await this.provider.sendText(text);
      }
    }
  }

  protected async flushTextQueue(): Promise<void> {
    await this.processTextQueue();
  }
}