/**
 * Piper TTS Adapter
 * Pre-warmed TTS with streaming 40-80ms PCM chunks, first chunk ≤150ms
 */

import { EventEmitter } from 'events';
import { spawn, ChildProcess } from 'child_process';
import { v4 as uuidv4 } from 'uuid';
import { Writable } from 'stream';
import * as fs from 'fs';
import * as path from 'path';

interface TTSConfig {
  model_path: string;
  voice: string;
  sample_rate: number;
  chunk_size_ms: number;
  quality: 'x-low' | 'low' | 'medium' | 'high';
  speaker_id?: number;
}

const DEFAULT_TTS_CONFIG: TTSConfig = {
  model_path: 'server/models/tts/sv_SE-nst-medium.onnx',
  voice: 'sv-SE-nst',
  sample_rate: 22050,
  chunk_size_ms: 60,
  quality: 'medium'
};

interface SynthesisOptions {
  voice?: string;
  rate?: number;
  chunk_ms?: number;
  speaker_id?: number;
}

interface TTSChunk {
  playbackId: string;
  seq: number;
  data: ArrayBuffer;
  timestamp: number;
  isFirst: boolean;
  isLast: boolean;
}

export class PiperTTS extends EventEmitter {
  private config: TTSConfig;
  private piperProcess: ChildProcess | null = null;
  private isReady: boolean = false;
  private synthesisQueue: Array<{ text: string; options: SynthesisOptions; playbackId: string }> = [];
  private activePlaybacks: Map<string, { startTime: number; seq: number }> = new Map();
  private isWarmedUp: boolean = false;

  // Pre-warming and chunk management
  private chunkSizeBytes: number;
  private cancelledPlaybacks: Set<string> = new Set();

  constructor(config: Partial<TTSConfig> = {}) {
    super();
    
    this.config = { ...DEFAULT_TTS_CONFIG, ...config };
    this.chunkSizeBytes = Math.floor((this.config.chunk_size_ms * this.config.sample_rate * 2) / 1000); // 16-bit samples
    
    this.initializePiper();
  }

  private async initializePiper(): Promise<void> {
    try {
      console.log('🔊 Initializing Piper TTS...');
      
      // Check if model exists
      if (!fs.existsSync(this.config.model_path)) {
        throw new Error(`Piper model not found: ${this.config.model_path}`);
      }

      // Start Piper process in server mode
      this.piperProcess = spawn('piper', [
        '--model', this.config.model_path,
        '--config', this.config.model_path + '.json',
        '--output-raw', // Output raw PCM
        '--server', // Server mode for persistent process
        '--port', '5050',
        '--host', '127.0.0.1'
      ]);

      if (!this.piperProcess.stdout || !this.piperProcess.stderr) {
        throw new Error('Failed to create Piper process streams');
      }

      // Handle server status
      this.piperProcess.stdout.on('data', (data: Buffer) => {
        const output = data.toString();
        if (output.includes('Server listening on')) {
          console.log('✅ Piper TTS server ready');
          this.isReady = true;
          this.warmUp();
        }
      });

      this.piperProcess.stderr.on('data', (data: Buffer) => {
        console.error('🚨 Piper error:', data.toString());
      });

      this.piperProcess.on('error', (error) => {
        console.error('❌ Piper process error:', error);
        this.emit('error', error);
      });

      this.piperProcess.on('exit', (code) => {
        console.log(`🔚 Piper TTS server exited with code ${code}`);
        this.piperProcess = null;
        this.isReady = false;
      });

      // Wait for server ready
      await this.waitForReady();
      
    } catch (error) {
      console.error('❌ Failed to initialize Piper TTS:', error);
      this.emit('error', error);
    }
  }

  private async waitForReady(): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Piper TTS initialization timeout'));
      }, 30000);

      const checkReady = () => {
        if (this.isReady) {
          clearTimeout(timeout);
          resolve();
        } else {
          setTimeout(checkReady, 100);
        }
      };

      checkReady();
    });
  }

  private async warmUp(): Promise<void> {
    if (this.isWarmedUp) {
      return;
    }

    try {
      console.log('🔥 Warming up Piper TTS with silent audio...');
      
      // Synthesize 100ms of silence to warm up the model
      const silenceText = ' '; // Minimal text
      const response = await this.synthesizeInternal(silenceText, {});
      
      // Discard the audio but keep the model loaded
      console.log('✅ Piper TTS warmed up');
      this.isWarmedUp = true;
      this.emit('ready');
      
    } catch (error) {
      console.error('❌ Failed to warm up Piper TTS:', error);
    }
  }

  public synthesize(text: string, options: SynthesisOptions = {}): string {
    const playbackId = uuidv4();
    
    if (!this.isReady || !this.isWarmedUp) {
      console.warn('⚠️ Piper TTS not ready, queuing synthesis');
      this.synthesisQueue.push({ text, options, playbackId });
      return playbackId;
    }

    console.log(`🔊 Synthesizing (${playbackId}): "${text.substring(0, 50)}..."`);
    
    this.activePlaybacks.set(playbackId, { startTime: Date.now(), seq: 0 });
    
    // Process synthesis asynchronously
    this.processSynthesis(text, options, playbackId);
    
    return playbackId;
  }

  private async processSynthesis(text: string, options: SynthesisOptions, playbackId: string): Promise<void> {
    try {
      if (this.cancelledPlaybacks.has(playbackId)) {
        console.log(`🚫 Synthesis cancelled before start: ${playbackId}`);
        return;
      }

      const audioBuffer = await this.synthesizeInternal(text, options);
      
      if (this.cancelledPlaybacks.has(playbackId)) {
        console.log(`🚫 Synthesis cancelled after generation: ${playbackId}`);
        this.cancelledPlaybacks.delete(playbackId);
        return;
      }

      await this.streamAudioChunks(audioBuffer, playbackId);
      
    } catch (error) {
      console.error(`❌ Synthesis error for ${playbackId}:`, error);
      this.emit('error', error);
    } finally {
      this.activePlaybacks.delete(playbackId);
    }
  }

  private async synthesizeInternal(text: string, options: SynthesisOptions): Promise<ArrayBuffer> {
    const requestPayload = {
      text: this.preprocessText(text),
      voice: options.voice || this.config.voice,
      rate: options.rate || 1.0,
      speaker_id: options.speaker_id || this.config.speaker_id || 0,
      output_format: 'wav' // Request WAV format for easier parsing
    };

    const response = await fetch('http://127.0.0.1:5050/synthesize', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestPayload)
    });

    if (!response.ok) {
      throw new Error(`Piper HTTP ${response.status}: ${response.statusText}`);
    }

    const audioBuffer = await response.arrayBuffer();
    
    // Convert WAV to raw PCM (skip 44-byte WAV header)
    return audioBuffer.slice(44);
  }

  private async streamAudioChunks(audioBuffer: ArrayBuffer, playbackId: string): Promise<void> {
    const playback = this.activePlaybacks.get(playbackId);
    if (!playback) {
      return;
    }

    const audioData = new Uint8Array(audioBuffer);
    const totalChunks = Math.ceil(audioData.length / this.chunkSizeBytes);
    let seq = 0;

    console.log(`📦 Streaming ${totalChunks} chunks for ${playbackId}`);

    for (let offset = 0; offset < audioData.length; offset += this.chunkSizeBytes) {
      // Check if playback was cancelled
      if (this.cancelledPlaybacks.has(playbackId)) {
        console.log(`🚫 Streaming cancelled for ${playbackId} at chunk ${seq}`);
        this.cancelledPlaybacks.delete(playbackId);
        return;
      }

      const chunkSize = Math.min(this.chunkSizeBytes, audioData.length - offset);
      const chunkData = audioData.slice(offset, offset + chunkSize);
      const isFirst = seq === 0;
      const isLast = offset + chunkSize >= audioData.length;

      // Emit first chunk event with timing
      if (isFirst) {
        const firstChunkTime = Date.now() - playback.startTime;
        console.log(`⚡ First TTS chunk in ${firstChunkTime}ms for ${playbackId}`);
        this.emit('first_chunk', playbackId, chunkData.buffer.slice(chunkData.byteOffset, chunkData.byteOffset + chunkData.byteLength));
      } else {
        this.emit('chunk', playbackId, seq, chunkData.buffer.slice(chunkData.byteOffset, chunkData.byteOffset + chunkData.byteLength));
      }

      // Update sequence
      playback.seq = seq;
      seq++;

      // Throttle streaming to maintain real-time playback
      if (!isLast && !isFirst) {
        await this.sleep(this.config.chunk_size_ms * 0.8); // Slightly faster than real-time
      }
    }

    // Emit completion
    this.emit('complete', playbackId);
    console.log(`✅ TTS streaming completed for ${playbackId} (${seq} chunks)`);
  }

  private preprocessText(text: string): string {
    // Optimize text for spoken output
    return text
      .replace(/([.!?])\\s+/g, '$1 ') // Normalize sentence spacing
      .replace(/\\s+/g, ' ') // Collapse multiple spaces
      .replace(/([,;:])(?!\\s)/g, '$1 ') // Add space after punctuation
      .trim();
  }

  public cancel(playbackId: string): number {
    const playback = this.activePlaybacks.get(playbackId);
    if (!playback) {
      console.warn(`⚠️ Cannot cancel unknown playback: ${playbackId}`);
      return 0;
    }

    const cancelTime = Date.now();
    const fadeTime = 100; // 100ms fade-out time
    
    console.log(`🛑 Cancelling TTS playback: ${playbackId}`);
    
    // Mark as cancelled for streaming interruption
    this.cancelledPlaybacks.add(playbackId);
    
    // Remove from active playbacks after fade period
    setTimeout(() => {
      this.activePlaybacks.delete(playbackId);
      this.cancelledPlaybacks.delete(playbackId);
    }, fadeTime);

    return fadeTime;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  public isReadyToSynthesize(): boolean {
    return this.isReady && this.isWarmedUp;
  }

  public getActivePlaybacks(): string[] {
    return Array.from(this.activePlaybacks.keys());
  }

  public async getVoices(): Promise<string[]> {
    try {
      const response = await fetch('http://127.0.0.1:5050/voices');
      const voices = await response.json();
      return voices.map((v: any) => v.name);
    } catch (error) {
      console.error('❌ Error getting voices:', error);
      return [this.config.voice];
    }
  }

  public cleanup(): void {
    console.log('🧹 Cleaning up Piper TTS');
    
    // Cancel all active playbacks
    for (const playbackId of this.activePlaybacks.keys()) {
      this.cancel(playbackId);
    }
    
    this.isReady = false;
    this.isWarmedUp = false;
    
    if (this.piperProcess) {
      this.piperProcess.kill('SIGTERM');
      
      // Force kill after 3 seconds
      setTimeout(() => {
        if (this.piperProcess && !this.piperProcess.killed) {
          console.warn('⚠️ Force killing Piper TTS server');
          this.piperProcess.kill('SIGKILL');
        }
      }, 3000);
      
      this.piperProcess = null;
    }
    
    this.removeAllListeners();
  }
}