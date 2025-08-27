/**
 * Faster-Whisper ASR Adapter
 * Streaming speech recognition with partial transcription ≤200ms
 */

import { EventEmitter } from 'events';
import { spawn, ChildProcess } from 'child_process';
import { Writable } from 'stream';

interface ASRConfig {
  chunk_ms: number;
  stabilize_ms: number;
  beam_size: number;
  no_speech_threshold: number;
  model: string;
  language: string;
}

const DEFAULT_ASR_CONFIG: ASRConfig = {
  chunk_ms: 200,
  stabilize_ms: 250,
  beam_size: 1,
  no_speech_threshold: 0.6,
  model: 'small',
  language: 'sv'
};

interface TranscriptionResult {
  text: string;
  confidence: number;
  is_partial: boolean;
  timestamp: number;
}

export class FasterWhisperASR extends EventEmitter {
  private config: ASRConfig;
  private pythonProcess: ChildProcess | null = null;
  private audioBuffer: Buffer = Buffer.alloc(0);
  private isListening: boolean = false;
  private lastPartialTime: number = 0;
  private silenceStartTime: number = 0;
  private partialText: string = '';

  // Audio processing state
  private sampleRate: number = 16000; // 16kHz mono
  private bytesPerSample: number = 2; // 16-bit
  private chunkSamples: number;
  private stabilizeSamples: number;

  constructor(config: Partial<ASRConfig> = {}) {
    super();
    
    this.config = { ...DEFAULT_ASR_CONFIG, ...config };
    this.chunkSamples = (this.config.chunk_ms * this.sampleRate) / 1000;
    this.stabilizeSamples = (this.config.stabilize_ms * this.sampleRate) / 1000;

    this.initializeFasterWhisper();
  }

  private async initializeFasterWhisper(): Promise<void> {
    try {
      console.log('🎙️ Initializing faster-whisper ASR...');
      
      // Spawn Python process for faster-whisper streaming
      this.pythonProcess = spawn('python3', [
        '-c', this.getPythonStreamingScript(),
        '--model', this.config.model,
        '--language', this.config.language,
        '--beam_size', this.config.beam_size.toString(),
        '--no_speech_threshold', this.config.no_speech_threshold.toString(),
        '--chunk_ms', this.config.chunk_ms.toString(),
        '--sample_rate', this.sampleRate.toString()
      ]);

      if (!this.pythonProcess.stdout || !this.pythonProcess.stderr || !this.pythonProcess.stdin) {
        throw new Error('Failed to create Python process streams');
      }

      // Handle transcription results
      this.pythonProcess.stdout.on('data', (data: Buffer) => {
        const lines = data.toString().trim().split('\\n');
        for (const line of lines) {
          if (line.trim()) {
            try {
              const result: TranscriptionResult = JSON.parse(line);
              this.handleTranscriptionResult(result);
            } catch (error) {
              console.error('❌ Failed to parse transcription result:', line, error);
            }
          }
        }
      });

      // Handle errors
      this.pythonProcess.stderr.on('data', (data: Buffer) => {
        console.error('🚨 faster-whisper error:', data.toString());
      });

      this.pythonProcess.on('error', (error) => {
        console.error('❌ Python process error:', error);
        this.emit('error', error);
      });

      this.pythonProcess.on('exit', (code) => {
        console.log(`🔚 faster-whisper process exited with code ${code}`);
        this.pythonProcess = null;
      });

      // Wait for initialization
      await this.waitForInitialization();
      
      console.log('✅ faster-whisper ASR initialized');
      this.emit('ready');
      
    } catch (error) {
      console.error('❌ Failed to initialize faster-whisper:', error);
      this.emit('error', error);
    }
  }

  private getPythonStreamingScript(): string {
    return `
import sys
import json
import argparse
import numpy as np
import threading
import time
from faster_whisper import WhisperModel
from collections import deque
import io

class StreamingWhisperASR:
    def __init__(self, model_size, language, beam_size, no_speech_threshold, chunk_ms, sample_rate):
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.language = language
        self.beam_size = beam_size 
        self.no_speech_threshold = no_speech_threshold
        self.chunk_ms = chunk_ms
        self.sample_rate = sample_rate
        
        self.chunk_samples = int((chunk_ms * sample_rate) / 1000)
        self.audio_buffer = deque()
        self.is_processing = False
        
        print(json.dumps({"type": "ready", "timestamp": time.time()}), flush=True)
        
    def process_audio_chunk(self, audio_data):
        # Convert bytes to numpy array (16-bit PCM)
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Add to buffer
        self.audio_buffer.extend(audio_np)
        
        # Process if we have enough samples
        if len(self.audio_buffer) >= self.chunk_samples:
            chunk = np.array(list(self.audio_buffer)[:self.chunk_samples])
            self.audio_buffer = deque(list(self.audio_buffer)[self.chunk_samples:])
            
            # Transcribe chunk
            self.transcribe_chunk(chunk, is_partial=True)
    
    def transcribe_chunk(self, audio_chunk, is_partial=True):
        try:
            segments, info = self.model.transcribe(
                audio_chunk,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=0.5,
                    min_speech_duration_ms=250,
                    max_speech_duration_s=30,
                    min_silence_duration_ms=self.chunk_ms,
                    speech_pad_ms=30
                )
            )
            
            full_text = ""
            avg_confidence = 0.0
            segment_count = 0
            
            for segment in segments:
                full_text += segment.text.strip() + " "
                avg_confidence += segment.avg_logprob if hasattr(segment, 'avg_logprob') else 0.5
                segment_count += 1
            
            if segment_count > 0:
                avg_confidence /= segment_count
                # Convert log prob to confidence (rough approximation)
                confidence = max(0.0, min(1.0, (avg_confidence + 1.0) / 2.0))
            else:
                confidence = 0.0
                
            result = {
                "text": full_text.strip(),
                "confidence": confidence,
                "is_partial": is_partial,
                "timestamp": time.time(),
                "no_speech_prob": info.no_speech_prob if hasattr(info, 'no_speech_prob') else 0.0
            }
            
            # Only emit if we have actual speech
            if result["text"] and info.no_speech_prob < self.no_speech_threshold:
                print(json.dumps(result), flush=True)
                
        except Exception as e:
            print(json.dumps({
                "type": "error", 
                "message": str(e),
                "timestamp": time.time()
            }), file=sys.stderr, flush=True)
    
    def finalize_transcription(self):
        # Process remaining buffer as final
        if len(self.audio_buffer) > 0:
            remaining = np.array(list(self.audio_buffer))
            self.transcribe_chunk(remaining, is_partial=False)
            self.audio_buffer.clear()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='small')
    parser.add_argument('--language', default='sv')
    parser.add_argument('--beam_size', type=int, default=1)
    parser.add_argument('--no_speech_threshold', type=float, default=0.6)
    parser.add_argument('--chunk_ms', type=int, default=200)
    parser.add_argument('--sample_rate', type=int, default=16000)
    args = parser.parse_args()
    
    asr = StreamingWhisperASR(
        args.model, args.language, args.beam_size, 
        args.no_speech_threshold, args.chunk_ms, args.sample_rate
    )
    
    # Read binary audio from stdin
    while True:
        try:
            # Read chunk size (4 bytes)
            size_bytes = sys.stdin.buffer.read(4)
            if len(size_bytes) < 4:
                break
                
            chunk_size = int.from_bytes(size_bytes, 'little')
            if chunk_size <= 0:
                continue
                
            # Read audio chunk
            audio_data = sys.stdin.buffer.read(chunk_size)
            if len(audio_data) < chunk_size:
                break
                
            asr.process_audio_chunk(audio_data)
            
        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            print(json.dumps({
                "type": "error",
                "message": f"Processing error: {str(e)}",
                "timestamp": time.time()
            }), file=sys.stderr, flush=True)
    
    # Finalize any remaining audio
    asr.finalize_transcription()

if __name__ == "__main__":
    main()
`;
  }

  private async waitForInitialization(): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('faster-whisper initialization timeout'));
      }, 30000); // 30 second timeout

      const onReady = () => {
        clearTimeout(timeout);
        this.off('error', onError);
        resolve();
      };

      const onError = (error: Error) => {
        clearTimeout(timeout);
        this.off('ready', onReady);
        reject(error);
      };

      this.once('ready', onReady);
      this.once('error', onError);
    });
  }

  private handleTranscriptionResult(result: TranscriptionResult): void {
    const now = Date.now();

    if (result.is_partial) {
      // Emit partial transcription
      this.partialText = result.text;
      this.lastPartialTime = now;
      
      this.emit('partial', result.text, result.confidence);
      
      // Check for silence to trigger final
      if (result.text.trim() === '' || result.confidence < 0.3) {
        if (this.silenceStartTime === 0) {
          this.silenceStartTime = now;
        } else if (now - this.silenceStartTime >= this.config.stabilize_ms) {
          // Emit final transcription after silence period
          if (this.partialText.trim()) {
            this.emit('final', this.partialText, result.confidence);
            this.partialText = '';
          }
          this.silenceStartTime = 0;
        }
      } else {
        this.silenceStartTime = 0; // Reset silence timer on speech
      }
      
    } else {
      // Final transcription
      this.emit('final', result.text, result.confidence);
      this.partialText = '';
      this.silenceStartTime = 0;
    }
  }

  public processAudio(audioData: ArrayBuffer): void {
    if (!this.isListening || !this.pythonProcess?.stdin) {
      return;
    }

    try {
      // Convert ArrayBuffer to Buffer
      const audioBuffer = Buffer.from(audioData);
      
      // Send chunk size followed by audio data
      const sizeBuffer = Buffer.alloc(4);
      sizeBuffer.writeUInt32LE(audioBuffer.length, 0);
      
      this.pythonProcess.stdin.write(sizeBuffer);
      this.pythonProcess.stdin.write(audioBuffer);
      
    } catch (error) {
      console.error('❌ Error processing audio:', error);
    }
  }

  public startListening(): void {
    if (this.isListening) {
      return;
    }

    console.log('👂 faster-whisper started listening');
    this.isListening = true;
    this.partialText = '';
    this.silenceStartTime = 0;
    this.lastPartialTime = 0;
  }

  public stopListening(): void {
    if (!this.isListening) {
      return;
    }

    console.log('🔇 faster-whisper stopped listening');
    this.isListening = false;
    
    // Send any remaining partial as final
    if (this.partialText.trim()) {
      this.emit('final', this.partialText, 0.8);
      this.partialText = '';
    }
  }

  public cleanup(): void {
    console.log('🧹 Cleaning up faster-whisper ASR');
    
    this.isListening = false;
    
    if (this.pythonProcess) {
      this.pythonProcess.kill('SIGTERM');
      this.pythonProcess = null;
    }
    
    this.removeAllListeners();
  }

  public isReady(): boolean {
    return this.pythonProcess !== null && !this.pythonProcess.killed;
  }
}