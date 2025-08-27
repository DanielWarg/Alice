/**
 * Real-time Audio Generator for Autonomous Testing
 * Generates realistic Swedish speech for voice pipeline testing
 */

import { EventEmitter } from 'events';
import { spawn, ChildProcess } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

interface AudioGeneratorConfig {
  sample_rate: number;
  chunk_size_ms: number;
  use_synthetic_voice: boolean;
  use_recorded_samples: boolean;
  voice_model: string;
  background_noise_level: number;
}

const DEFAULT_AUDIO_CONFIG: AudioGeneratorConfig = {
  sample_rate: 16000,
  chunk_size_ms: 20,
  use_synthetic_voice: true,
  use_recorded_samples: true,
  voice_model: 'sv-SE-nst-medium',
  background_noise_level: 0.05
};

export class RealtimeAudioGenerator extends EventEmitter {
  private config: AudioGeneratorConfig;
  private piperProcess: ChildProcess | null = null;
  private audioClients: Map<string, TestAudioClient> = new Map();
  private recordedSamples: Map<string, ArrayBuffer> = new Map();

  constructor(config: Partial<AudioGeneratorConfig> = {}) {
    super();
    this.config = { ...DEFAULT_AUDIO_CONFIG, ...config };
    this.initializePiper();
    this.loadRecordedSamples();
  }

  private async initializePiper(): Promise<void> {
    if (!this.config.use_synthetic_voice) {
      return;
    }

    try {
      console.log('🎤 Initializing Piper for test audio generation...');
      
      this.piperProcess = spawn('piper', [
        '--model', `server/models/tts/${this.config.voice_model}.onnx`,
        '--config', `server/models/tts/${this.config.voice_model}.onnx.json`,
        '--output-raw',
        '--sample-rate', this.config.sample_rate.toString()
      ]);

      if (this.piperProcess.stderr) {
        this.piperProcess.stderr.on('data', (data) => {
          console.warn('Piper TTS warning:', data.toString());
        });
      }

      console.log('✅ Piper TTS ready for test audio generation');
    } catch (error) {
      console.error('❌ Failed to initialize Piper for testing:', error);
      this.config.use_synthetic_voice = false; // Fall back to recorded samples
    }
  }

  private async loadRecordedSamples(): Promise<void> {
    if (!this.config.use_recorded_samples) {
      return;
    }

    const samplesDir = 'core/talk/tests/fixtures/audio';
    
    try {
      // Ensure samples directory exists
      await fs.promises.mkdir(samplesDir, { recursive: true });
      
      // Create sample audio files if they don't exist
      await this.createSampleAudioFiles(samplesDir);
      
      // Load existing samples
      const files = await fs.promises.readdir(samplesDir);
      const audioFiles = files.filter(f => f.endsWith('.wav') || f.endsWith('.raw'));
      
      for (const file of audioFiles) {
        const filePath = path.join(samplesDir, file);
        const audioData = await fs.promises.readFile(filePath);
        const sampleName = path.basename(file, path.extname(file));
        
        // Convert to ArrayBuffer
        this.recordedSamples.set(sampleName, audioData.buffer.slice(audioData.byteOffset, audioData.byteOffset + audioData.byteLength));
      }
      
      console.log(`📁 Loaded ${this.recordedSamples.size} recorded audio samples`);
    } catch (error) {
      console.error('❌ Failed to load recorded samples:', error);
    }
  }

  private async createSampleAudioFiles(samplesDir: string): Promise<void> {
    const samples = [
      { name: 'hello', text: 'Hej Alice, vad är klockan?' },
      { name: 'weather', text: 'Hur är vädret idag?' },
      { name: 'music', text: 'Spela lite musik, tack' },
      { name: 'email_pii', text: 'Min epost är test@example.com' },
      { name: 'phone_pii', text: 'Ring mig på 070-123-4567' },
      { name: 'interrupt', text: 'Stopp, tack så mycket' },
      { name: 'tool_request', text: 'Skicka ett mejl till teamet' },
      { name: 'long_query', text: 'Kan du förklara i detalj hur artificiell intelligens fungerar och vad det innebär för framtiden av mänskligheten?' }
    ];

    for (const sample of samples) {
      const filePath = path.join(samplesDir, `${sample.name}.wav`);
      
      if (!fs.existsSync(filePath) && this.config.use_synthetic_voice) {
        try {
          const audioData = await this.synthesizeText(sample.text);
          await fs.promises.writeFile(filePath, Buffer.from(audioData));
          console.log(`🎵 Generated sample: ${sample.name}.wav`);
        } catch (error) {
          console.warn(`⚠️ Failed to generate sample ${sample.name}:`, error);
        }
      }
    }
  }

  public async generateSpeech(text: string, addNoise: boolean = true): Promise<ArrayBuffer> {
    if (this.config.use_synthetic_voice && this.piperProcess) {
      return await this.synthesizeText(text, addNoise);
    } else if (this.config.use_recorded_samples) {
      return this.getRecordedSample(text) || this.generateSilence(1000);
    } else {
      // Generate simple tone or silence as fallback
      return this.generateTestTone(text.length * 50); // ~50ms per character
    }
  }

  private async synthesizeText(text: string, addNoise: boolean = true): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      if (!this.piperProcess?.stdin || !this.piperProcess?.stdout) {
        reject(new Error('Piper process not available'));
        return;
      }

      const chunks: Buffer[] = [];
      
      // Set up stdout handler
      const onData = (data: Buffer) => {
        chunks.push(data);
      };
      
      const onEnd = () => {
        this.piperProcess!.stdout!.off('data', onData);
        this.piperProcess!.stdout!.off('end', onEnd);
        
        let audioData = Buffer.concat(chunks);
        
        // Add background noise if requested
        if (addNoise) {
          audioData = this.addBackgroundNoise(audioData);
        }
        
        resolve(audioData.buffer.slice(audioData.byteOffset, audioData.byteOffset + audioData.byteLength));
      };
      
      this.piperProcess.stdout.on('data', onData);
      this.piperProcess.stdout.on('end', onEnd);
      
      // Send text to Piper
      this.piperProcess.stdin.write(text + '\\n');
      this.piperProcess.stdin.end();
      
      // Timeout after 10 seconds
      setTimeout(() => {
        reject(new Error('TTS synthesis timeout'));
      }, 10000);
    });
  }

  private getRecordedSample(text: string): ArrayBuffer | null {
    // Simple keyword matching to select appropriate sample
    const keywords = [
      { words: ['hej', 'hello', 'hallå'], sample: 'hello' },
      { words: ['väder', 'weather'], sample: 'weather' },
      { words: ['musik', 'music', 'spela'], sample: 'music' },
      { words: ['epost', 'email', '@'], sample: 'email_pii' },
      { words: ['telefon', 'ring', 'phone'], sample: 'phone_pii' },
      { words: ['stopp', 'stop', 'avbryt'], sample: 'interrupt' },
      { words: ['mejl', 'skicka', 'tool'], sample: 'tool_request' },
      { words: ['förklara', 'detalj', 'artificiell'], sample: 'long_query' }
    ];
    
    const lowerText = text.toLowerCase();
    
    for (const { words, sample } of keywords) {
      if (words.some(word => lowerText.includes(word))) {
        const audioData = this.recordedSamples.get(sample);
        if (audioData) {
          return audioData;
        }
      }
    }
    
    // Default to first available sample
    const firstSample = this.recordedSamples.values().next().value;
    return firstSample || null;
  }

  private generateTestTone(durationMs: number): ArrayBuffer {
    const sampleCount = Math.floor((durationMs * this.config.sample_rate) / 1000);
    const buffer = new ArrayBuffer(sampleCount * 2); // 16-bit samples
    const view = new Int16Array(buffer);
    
    const frequency = 440; // A note
    const amplitude = 16000;
    
    for (let i = 0; i < sampleCount; i++) {
      const t = i / this.config.sample_rate;
      view[i] = amplitude * Math.sin(2 * Math.PI * frequency * t);
    }
    
    return buffer;
  }

  private generateSilence(durationMs: number): ArrayBuffer {
    const sampleCount = Math.floor((durationMs * this.config.sample_rate) / 1000);
    const buffer = new ArrayBuffer(sampleCount * 2); // 16-bit samples
    // ArrayBuffer is already zero-filled
    return buffer;
  }

  private addBackgroundNoise(audioBuffer: Buffer): Buffer {
    const view = new Int16Array(audioBuffer.buffer, audioBuffer.byteOffset, audioBuffer.byteLength / 2);
    const noisedView = new Int16Array(view.length);
    
    for (let i = 0; i < view.length; i++) {
      // Add white noise
      const noise = (Math.random() - 0.5) * 2 * this.config.background_noise_level * 32767;
      noisedView[i] = Math.max(-32768, Math.min(32767, view[i] + noise));
    }
    
    return Buffer.from(noisedView.buffer);
  }

  public async createTestClient(sessionId: string, scenario: string): Promise<TestAudioClient> {
    const client = new TestAudioClient(sessionId, scenario, this);
    await client.initialize();
    
    this.audioClients.set(sessionId, client);
    return client;
  }

  public async cleanup(): Promise<void> {
    console.log('🧹 Cleaning up audio generator...');
    
    // Cleanup all clients
    for (const client of this.audioClients.values()) {
      await client.cleanup();
    }
    this.audioClients.clear();
    
    // Cleanup Piper process
    if (this.piperProcess) {
      this.piperProcess.kill('SIGTERM');
      this.piperProcess = null;
    }
    
    console.log('✅ Audio generator cleanup completed');
  }
}

class TestAudioClient extends EventEmitter {
  private sessionId: string;
  private scenario: string;
  private audioGenerator: RealtimeAudioGenerator;
  private wsConnection: any = null; // WebSocket connection to voice pipeline
  private metrics: any = {};
  
  constructor(sessionId: string, scenario: string, audioGenerator: RealtimeAudioGenerator) {
    super();
    this.sessionId = sessionId;
    this.scenario = scenario;
    this.audioGenerator = audioGenerator;
  }

  public async initialize(): Promise<void> {
    // Connect to voice pipeline server
    const WebSocket = require('ws');
    this.wsConnection = new WebSocket('ws://localhost:8002');
    
    return new Promise((resolve, reject) => {
      this.wsConnection.on('open', () => {
        console.log(`🔗 Test client connected: ${this.sessionId}`);
        this.setupMessageHandlers();
        resolve();
      });
      
      this.wsConnection.on('error', (error: Error) => {
        console.error(`❌ Test client connection error: ${this.sessionId}`, error);
        reject(error);
      });
      
      // Connection timeout
      setTimeout(() => {
        if (this.wsConnection.readyState !== 1) { // Not OPEN
          reject(new Error('Connection timeout'));
        }
      }, 5000);
    });
  }

  private setupMessageHandlers(): void {
    this.wsConnection.on('message', (data: Buffer) => {
      try {
        const event = JSON.parse(data.toString());
        this.handleVoiceEvent(event);
      } catch (error) {
        console.error(`❌ Failed to parse voice event in ${this.sessionId}:`, error);
      }
    });
  }

  private handleVoiceEvent(event: any): void {
    const timestamp = Date.now();
    
    switch (event.type) {
      case 'stt.partial':
        if (!this.metrics.first_partial_ms) {
          this.metrics.first_partial_ms = timestamp - this.metrics.start_time;
        }
        break;
        
      case 'stt.final':
        this.metrics.transcription_final_ms = timestamp - this.metrics.start_time;
        break;
        
      case 'llm.delta':
        if (!this.metrics.ttft_ms) {
          this.metrics.ttft_ms = timestamp - this.metrics.start_time;
        }
        break;
        
      case 'tts.audio_chunk':
        if (event.seq === 0 && !this.metrics.tts_first_chunk_ms) {
          this.metrics.tts_first_chunk_ms = timestamp - this.metrics.start_time;
        }
        break;
        
      case 'tts.end':
        this.metrics.total_latency_ms = timestamp - this.metrics.start_time;
        this.metrics.complete = true;
        this.emit('turn_complete', this.metrics);
        break;
    }
  }

  public async sendAudioAndMeasure(audioData: ArrayBuffer): Promise<any> {
    this.metrics = {
      start_time: Date.now(),
      sessionId: this.sessionId,
      scenario: this.scenario
    };
    
    // Send audio in realistic chunks
    const chunkSizeBytes = Math.floor((20 * 16000 * 2) / 1000); // 20ms chunks
    const audioView = new Uint8Array(audioData);
    
    for (let offset = 0; offset < audioView.length; offset += chunkSizeBytes) {
      const chunkSize = Math.min(chunkSizeBytes, audioView.length - offset);
      const chunk = audioView.slice(offset, offset + chunkSize);
      
      // Create binary frame with magic header
      const frame = new ArrayBuffer(12 + chunk.length);
      const frameView = new DataView(frame);
      
      frameView.setUint32(0, 0x41554449, true); // 'AUDI' magic
      frameView.setUint32(4, Math.floor(offset / chunkSizeBytes), true); // Sequence
      frameView.setUint32(8, chunk.length, true); // Chunk size
      
      // Copy audio data
      new Uint8Array(frame, 12).set(chunk);
      
      // Send via WebSocket
      if (this.wsConnection.readyState === 1) { // OPEN
        this.wsConnection.send(frame);
      }
      
      // Realistic timing - 20ms between chunks
      await this.sleep(20);
    }
    
    // Wait for completion or timeout
    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        this.metrics.timeout = true;
        this.metrics.total_latency_ms = Date.now() - this.metrics.start_time;
        resolve(this.metrics);
      }, 10000); // 10 second timeout
      
      this.once('turn_complete', (metrics) => {
        clearTimeout(timeout);
        resolve(metrics);
      });
    });
  }

  public async sendBargeInAndMeasure(audioData: ArrayBuffer): Promise<any> {
    // Send barge-in signal first
    const bargeInEvent = {
      type: 'control.barge_in',
      sessionId: this.sessionId,
      playbackId: 'current', // Interrupt current playback
      timestamp: Date.now()
    };
    
    if (this.wsConnection.readyState === 1) {
      this.wsConnection.send(JSON.stringify(bargeInEvent));
    }
    
    // Small delay to measure barge-in response
    await this.sleep(50);
    
    // Then send new audio
    return await this.sendAudioAndMeasure(audioData);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  public async cleanup(): Promise<void> {
    if (this.wsConnection) {
      this.wsConnection.close();
      this.wsConnection = null;
    }
    
    this.removeAllListeners();
  }
}