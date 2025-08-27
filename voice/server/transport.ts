#!/usr/bin/env node
/**
 * 🚀 Voice Transport Server - Binary Audio Frame WebSocket/DataChannel
 * First roadmap item: WebSocket server with binary audio frame handling
 */

import WebSocket from 'ws';
import { EventEmitter } from 'events';
import { createServer } from 'http';

// Transport configuration
interface TransportConfig {
  port: number;
  frameSize: number;        // 20ms frames at 16kHz = 320 samples
  sampleRate: number;       // 16kHz for whisper compatibility
  channels: number;         // Mono
  vadAggressiveness: number; // 0-3, 2 recommended for real-time
}

// Audio frame metadata
interface AudioFrame {
  timestamp: number;
  samples: Float32Array;
  energy: number;
  isVoiced: boolean;
}

// WebSocket message types
type ClientMessage = 
  | { type: 'audio.frame'; data: ArrayBuffer; timestamp: number }
  | { type: 'control.barge_in'; timestamp: number }
  | { type: 'control.mic'; enabled: boolean };

type ServerMessage = 
  | { type: 'audio.chunk'; data: ArrayBuffer; timestamp: number }
  | { type: 'tts.begin'; sessionId: string }
  | { type: 'tts.end'; sessionId: string }
  | { type: 'stt.partial'; text: string; confidence: number }
  | { type: 'stt.final'; text: string; confidence: number }
  | { type: 'llm.delta'; text: string; done: boolean }
  | { type: 'metrics'; latency: number; stage: string };

/**
 * Voice Transport Server
 * Handles binary audio streaming with VAD and routing
 */
export class VoiceTransportServer extends EventEmitter {
  private server: WebSocket.Server;
  private httpServer: any;
  private config: TransportConfig;
  private sessions: Map<string, WebSocket> = new Map();
  private audioBuffers: Map<string, AudioFrame[]> = new Map();

  constructor(config: Partial<TransportConfig> = {}) {
    super();
    
    this.config = {
      port: 8001,
      frameSize: 320,      // 20ms at 16kHz
      sampleRate: 16000,
      channels: 1,
      vadAggressiveness: 2,
      ...config
    };

    this.httpServer = createServer();
    this.server = new WebSocket.Server({ server: this.httpServer });
    
    this.setupWebSocketHandling();
    console.log(`🎙️ Voice Transport Server ready on ws://localhost:${this.config.port}`);
  }

  /**
   * Start the transport server
   */
  async start(): Promise<void> {
    return new Promise((resolve) => {
      this.httpServer.listen(this.config.port, () => {
        console.log(`✅ Voice Transport listening on port ${this.config.port}`);
        console.log(`📊 Config: ${this.config.frameSize} samples/frame, ${this.config.sampleRate}Hz`);
        resolve();
      });
    });
  }

  /**
   * Setup WebSocket connection handling
   */
  private setupWebSocketHandling(): void {
    this.server.on('connection', (ws: WebSocket, request) => {
      const sessionId = this.generateSessionId();
      const clientIP = request.socket.remoteAddress;
      
      console.log(`🔌 New voice session: ${sessionId} from ${clientIP}`);
      
      // Register session
      this.sessions.set(sessionId, ws);
      this.audioBuffers.set(sessionId, []);
      
      // Setup message handling
      ws.on('message', (data: WebSocket.Data) => {
        this.handleClientMessage(sessionId, data);
      });
      
      // Cleanup on disconnect
      ws.on('close', () => {
        console.log(`🔌 Session ${sessionId} disconnected`);
        this.sessions.delete(sessionId);
        this.audioBuffers.delete(sessionId);
      });
      
      ws.on('error', (error) => {
        console.error(`❌ WebSocket error for ${sessionId}:`, error);
      });
      
      // Send initial handshake
      this.sendToClient(sessionId, {
        type: 'handshake',
        sessionId,
        config: this.config
      } as any);
      
      this.emit('session.start', sessionId);
    });
  }

  /**
   * Handle incoming client messages
   */
  private handleClientMessage(sessionId: string, data: WebSocket.Data): void {
    try {
      // Handle binary audio frames
      if (data instanceof ArrayBuffer || Buffer.isBuffer(data)) {
        this.handleAudioFrame(sessionId, data as ArrayBuffer);
        return;
      }
      
      // Handle text control messages
      if (typeof data === 'string') {
        const message: ClientMessage = JSON.parse(data);
        this.handleControlMessage(sessionId, message);
        return;
      }
      
    } catch (error) {
      console.error(`❌ Message handling error for ${sessionId}:`, error);
    }
  }

  /**
   * Process binary audio frame
   */
  private handleAudioFrame(sessionId: string, audioData: ArrayBuffer): void {
    const timestamp = Date.now();
    
    // Convert to Float32Array (expecting 32-bit float PCM)
    const samples = new Float32Array(audioData);
    
    // Validate frame size
    if (samples.length !== this.config.frameSize) {
      console.warn(`⚠️ Invalid frame size: ${samples.length}, expected ${this.config.frameSize}`);
      return;
    }
    
    // Calculate energy for VAD
    const energy = this.calculateAudioEnergy(samples);
    const isVoiced = this.simpleVAD(energy);
    
    const frame: AudioFrame = {
      timestamp,
      samples,
      energy,
      isVoiced
    };
    
    // Buffer the frame
    const buffer = this.audioBuffers.get(sessionId) || [];
    buffer.push(frame);
    this.audioBuffers.set(sessionId, buffer);
    
    // Emit for pipeline processing
    this.emit('audio.frame', sessionId, frame);
    
    // Trigger pipeline on voice detection
    if (isVoiced) {
      this.emit('voice.detected', sessionId, frame);
    }
    
    // Auto-cleanup old frames (keep last 5 seconds)
    const maxFrames = (5 * 1000) / 20; // 5 seconds of 20ms frames
    if (buffer.length > maxFrames) {
      buffer.splice(0, buffer.length - maxFrames);
    }
  }

  /**
   * Handle control messages
   */
  private handleControlMessage(sessionId: string, message: ClientMessage): void {
    switch (message.type) {
      case 'control.barge_in':
        console.log(`🛑 Barge-in detected for ${sessionId}`);
        this.emit('barge.in', sessionId, message.timestamp);
        break;
        
      case 'control.mic':
        console.log(`🎤 Mic ${message.enabled ? 'enabled' : 'disabled'} for ${sessionId}`);
        this.emit('mic.control', sessionId, message.enabled);
        break;
    }
  }

  /**
   * Send message to specific client
   */
  sendToClient(sessionId: string, message: ServerMessage): void {
    const ws = this.sessions.get(sessionId);
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }
    
    try {
      if (message.type === 'audio.chunk') {
        // Send binary audio data
        ws.send(message.data);
      } else {
        // Send JSON control message
        ws.send(JSON.stringify(message));
      }
    } catch (error) {
      console.error(`❌ Send error to ${sessionId}:`, error);
    }
  }

  /**
   * Broadcast to all connected clients
   */
  broadcast(message: ServerMessage): void {
    for (const sessionId of this.sessions.keys()) {
      this.sendToClient(sessionId, message);
    }
  }

  /**
   * Get audio frames for session
   */
  getAudioFrames(sessionId: string, since?: number): AudioFrame[] {
    const frames = this.audioBuffers.get(sessionId) || [];
    if (!since) return frames;
    
    return frames.filter(frame => frame.timestamp >= since);
  }

  /**
   * Simple energy-based VAD
   */
  private simpleVAD(energy: number): boolean {
    const threshold = 0.01; // Adjust based on testing
    return energy > threshold;
  }

  /**
   * Calculate RMS energy of audio frame
   */
  private calculateAudioEnergy(samples: Float32Array): number {
    let sum = 0;
    for (let i = 0; i < samples.length; i++) {
      sum += samples[i] * samples[i];
    }
    return Math.sqrt(sum / samples.length);
  }

  /**
   * Generate unique session ID
   */
  private generateSessionId(): string {
    return `voice_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  }

  /**
   * Get server statistics
   */
  getStats() {
    return {
      activeSessions: this.sessions.size,
      totalFramesBuffered: Array.from(this.audioBuffers.values())
        .reduce((sum, frames) => sum + frames.length, 0),
      config: this.config
    };
  }

  /**
   * Cleanup and shutdown
   */
  async shutdown(): Promise<void> {
    console.log('🛑 Shutting down Voice Transport Server...');
    
    // Close all WebSocket connections
    for (const [sessionId, ws] of this.sessions) {
      ws.close(1000, 'Server shutdown');
    }
    
    // Clear data
    this.sessions.clear();
    this.audioBuffers.clear();
    
    // Close server
    return new Promise((resolve) => {
      this.httpServer.close(() => {
        console.log('✅ Voice Transport Server shutdown complete');
        resolve();
      });
    });
  }
}

// Export for use in pipeline
export type { TransportConfig, AudioFrame, ClientMessage, ServerMessage };