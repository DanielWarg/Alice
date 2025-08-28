/**
 * Alice Voice Pipeline
 * Coordinates ASR → LLM → TTS streaming with sub-500ms latency
 */

import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import { FasterWhisperASR } from './adapters/asr/faster_whisper';
import { GPTOss7BLLM } from './adapters/llm/gpt_oss_7b';
import { PiperTTS } from './adapters/tts/piper';
import { VoiceRouter } from '../router';
import { SafeSummary } from './privacy/safe_summary';
import { MetricsLogger } from './metrics/logger';
import { 
  UpstreamEvent, 
  DownstreamEvent, 
  VoiceMetrics,
  AudioFrameEvent,
  BargeInEvent 
} from '../types/events';

interface PhraseSplitterState {
  accumulated: string;
  wordCount: number;
  lastPunctuation: number;
}

export class VoicePipeline extends EventEmitter {
  private sessionId: string;
  private router: VoiceRouter;
  private metrics: MetricsLogger;
  private safeSummary: SafeSummary;

  // Adapters
  private asr: FasterWhisperASR;
  private llm: GPTOss7BLLM;
  private tts: PiperTTS;

  // State management
  private isActive: boolean = false;
  private currentPlaybackId: string | null = null;
  private turnStartTime: number = 0;
  private currentTurn: VoiceMetrics;
  private phraseSplitter: PhraseSplitterState;

  // Micro-acks
  private ackBuffer: ArrayBuffer; // Pre-baked "Mm?" audio
  private ackSent: boolean = false;

  constructor(
    sessionId: string,
    router: VoiceRouter,
    metrics: MetricsLogger
  ) {
    super();
    
    this.sessionId = sessionId;
    this.router = router;
    this.metrics = metrics;
    this.safeSummary = new SafeSummary();

    // Initialize adapters
    this.asr = new FasterWhisperASR();
    this.llm = new GPTOss7BLLM();
    this.tts = new PiperTTS();

    this.resetTurn();
    this.initializePhraseSplitter();
    this.loadMicroAck();
    this.setupAdapterEvents();

    console.log(`🎙️ Voice pipeline initialized for session ${sessionId}`);
  }

  private setupAdapterEvents(): void {
    // ASR Events
    this.asr.on('partial', (text: string, confidence: number) => {
      const now = Date.now();
      
      // Emit partial transcript
      this.emit('downstream', {
        type: 'stt.partial',
        text,
        confidence,
        timestamp: now
      });

      // Record first partial timing
      if (!this.currentTurn.first_partial_ms) {
        this.currentTurn.first_partial_ms = now - this.turnStartTime;
      }

      // Send micro-ack on first meaningful partial
      if (!this.ackSent && this.shouldSendMicroAck(text)) {
        this.sendMicroAck();
      }
    });

    this.asr.on('final', (text: string, confidence: number) => {
      const now = Date.now();
      
      // Emit final transcript
      this.emit('downstream', {
        type: 'stt.final',
        text,
        confidence,
        timestamp: now
      });

      // Route to appropriate LLM path
      const route = this.router.determineRoute(text, this.sessionId);
      this.currentTurn.route = route;

      if (route === 'local_fast') {
        this.processWithLocalLLM(text);
      } else {
        // TODO: Implement cloud_complex routing
        console.warn(`Route ${route} not yet implemented, falling back to local_fast`);
        this.processWithLocalLLM(text);
      }
    });

    // LLM Events  
    this.llm.on('first_token', (text: string) => {
      const now = Date.now();
      
      // Record time to first token
      if (!this.currentTurn.ttft_ms) {
        this.currentTurn.ttft_ms = now - this.turnStartTime;
      }

      // Stop micro-ack if playing
      if (this.ackSent) {
        this.stopMicroAck();
      }

      // Start phrase accumulation
      this.phraseSplitter.accumulated = text;
      this.phraseSplitter.wordCount = text.split(' ').length;
    });

    this.llm.on('delta', (text: string) => {
      // Emit LLM delta
      this.emit('downstream', {
        type: 'llm.delta',
        text,
        timestamp: Date.now()
      });

      // Accumulate for phrase splitting
      this.updatePhraseSplitter(text);
    });

    this.llm.on('complete', () => {
      // Send any remaining text to TTS
      if (this.phraseSplitter.accumulated.trim()) {
        this.sendToTTS(this.phraseSplitter.accumulated.trim());
      }
      
      this.finalizeTurn();
    });

    // TTS Events
    this.tts.on('first_chunk', (playbackId: string, data: ArrayBuffer) => {
      const now = Date.now();
      
      // Record first TTS chunk timing
      if (!this.currentTurn.tts_first_chunk_ms) {
        this.currentTurn.tts_first_chunk_ms = now - this.turnStartTime;
      }

      // Emit TTS events
      this.emit('downstream', {
        type: 'tts.begin',
        playbackId,
        timestamp: now
      });

      this.emit('downstream', {
        type: 'tts.active',
        playbackId,
        active: true,
        timestamp: now
      });

      this.emit('downstream', {
        type: 'tts.audio_chunk',
        playbackId,
        seq: 0,
        data,
        timestamp: now
      });

      this.currentPlaybackId = playbackId;
    });

    this.tts.on('chunk', (playbackId: string, seq: number, data: ArrayBuffer) => {
      this.emit('downstream', {
        type: 'tts.audio_chunk',
        playbackId,
        seq,
        data,
        timestamp: Date.now()
      });
    });

    this.tts.on('complete', (playbackId: string) => {
      this.emit('downstream', {
        type: 'tts.end',
        playbackId,
        timestamp: Date.now()
      });

      this.emit('downstream', {
        type: 'tts.active',
        playbackId,
        active: false,
        timestamp: Date.now()
      });

      if (this.currentPlaybackId === playbackId) {
        this.currentPlaybackId = null;
      }
    });
  }

  public handleUpstream(event: UpstreamEvent): void {
    switch (event.type) {
      case 'audio.frame':
        this.handleAudioFrame(event);
        break;
        
      case 'control.barge_in':
        this.handleBargeIn(event);
        break;
        
      case 'control.mic':
        if (event.action === 'open') {
          this.startListening();
        } else {
          this.stopListening();
        }
        break;
    }
  }

  private handleAudioFrame(event: AudioFrameEvent): void {
    if (!this.isActive) {
      this.startTurn();
    }

    // Feed audio to ASR
    this.asr.processAudio(event.data);
  }

  private handleBargeIn(event: BargeInEvent): void {
    const now = Date.now();
    
    console.log(`🚫 Barge-in detected for playback ${event.playbackId}`);
    
    // Cancel current TTS playback
    if (this.currentPlaybackId) {
      const cutTime = this.tts.cancel(this.currentPlaybackId);
      this.currentTurn.barge_in_cut_ms = cutTime;
    }

    // Reset for new turn
    this.resetTurn();
    this.turnStartTime = now;
  }

  private startTurn(): void {
    this.isActive = true;
    this.turnStartTime = Date.now();
    this.resetTurn();
    this.ackSent = false;
    
    console.log(`🎯 Starting new voice turn for session ${this.sessionId}`);
  }

  private processWithLocalLLM(text: string): void {
    console.log(`🧠 Processing with local LLM: "${text}"`);
    
    // Apply safe summary if needed (for tool outputs)
    const processedText = this.safeSummary.filter(text);
    
    // Generate response with streaming
    this.llm.generateStreaming(processedText, {
      max_tokens: 40,
      temperature: 0.2,
      top_p: 0.9,
      system_prompt: "Respond in spoken style, ≤2 sentences, concise. Don't wait for punctuation to start speaking."
    });
  }

  private shouldSendMicroAck(text: string): boolean {
    const words = text.trim().split(/\\s+/);
    return words.length >= 2 || text.length >= 8;
  }

  private sendMicroAck(): void {
    if (this.ackBuffer && !this.ackSent) {
      console.log(`🎵 Sending micro-ack for session ${this.sessionId}`);
      
      const ackPlaybackId = uuidv4();
      
      this.emit('downstream', {
        type: 'tts.begin',
        playbackId: ackPlaybackId,
        timestamp: Date.now()
      });

      this.emit('downstream', {
        type: 'tts.audio_chunk',
        playbackId: ackPlaybackId,
        seq: 0,
        data: this.ackBuffer,
        timestamp: Date.now()
      });

      this.ackSent = true;
      
      // Auto-stop after ack duration (~180ms)
      setTimeout(() => {
        this.emit('downstream', {
          type: 'tts.end',
          playbackId: ackPlaybackId,
          timestamp: Date.now()
        });
      }, 200);
    }
  }

  private stopMicroAck(): void {
    // Micro-ack is automatically stopped by timeout
    // This is called when first real TTS chunk arrives
    console.log(`🔇 Cross-fading from micro-ack to TTS`);
  }

  private updatePhraseSplitter(deltaText: string): void {
    this.phraseSplitter.accumulated += deltaText;
    const words = this.phraseSplitter.accumulated.split(/\\s+/);
    this.phraseSplitter.wordCount = words.length;

    // Check for phrase boundary (10-25 words or minor punctuation)
    const shouldSplit = 
      this.phraseSplitter.wordCount >= 10 && 
      (this.phraseSplitter.wordCount >= 25 || 
       deltaText.match(/[,;:]/) ||
       (this.phraseSplitter.wordCount >= 15 && deltaText.match(/[.!?]/)));

    if (shouldSplit) {
      const phrase = this.phraseSplitter.accumulated.trim();
      console.log(`📝 Splitting phrase (${this.phraseSplitter.wordCount} words): "${phrase}"`);
      
      this.sendToTTS(phrase);
      this.initializePhraseSplitter();
    }
  }

  private sendToTTS(text: string): void {
    if (text.trim()) {
      console.log(`🔊 Sending to TTS: "${text}"`);
      this.tts.synthesize(text, {
        voice: 'sv-SE-nst',
        rate: 1.0,
        chunk_ms: 60
      });
    }
  }

  private finalizeTurn(): void {
    const now = Date.now();
    this.currentTurn.total_latency_ms = now - this.turnStartTime;
    
    // Log metrics
    this.metrics.recordTurn(this.currentTurn);
    
    console.log(`✅ Voice turn completed in ${this.currentTurn.total_latency_ms}ms`);
    
    this.isActive = false;
  }

  private resetTurn(): void {
    this.currentTurn = {
      sessionId: this.sessionId,
      timestamp: Date.now(),
      route: 'local_fast'
    };
  }

  private initializePhraseSplitter(): void {
    this.phraseSplitter = {
      accumulated: '',
      wordCount: 0,
      lastPunctuation: 0
    };
  }

  private loadMicroAck(): void {
    // TODO: Load pre-baked "Mm?" audio file (~180ms PCM)
    // For now, create a placeholder buffer
    this.ackBuffer = new ArrayBuffer(16384); // ~180ms at 44.1kHz mono
  }

  private startListening(): void {
    console.log(`👂 Started listening for session ${this.sessionId}`);
    this.asr.startListening();
  }

  private stopListening(): void {
    console.log(`🔇 Stopped listening for session ${this.sessionId}`);
    this.asr.stopListening();
  }

  public cleanup(): void {
    console.log(`🧹 Cleaning up voice pipeline for session ${this.sessionId}`);
    
    // Cancel any active TTS
    if (this.currentPlaybackId) {
      this.tts.cancel(this.currentPlaybackId);
    }

    // Cleanup adapters
    this.asr.cleanup();
    this.llm.cleanup(); 
    this.tts.cleanup();

    // Remove all listeners
    this.removeAllListeners();
  }
}