#!/usr/bin/env node
/**
 * 🔊 Jitter Buffer - Smooth audio playback with cross-fade
 * Roadmap: 100ms jitter buffering & 80ms cross-fade transitions
 */

import { EventEmitter } from 'events';

// Audio chunk with metadata
interface AudioChunk {
  id: string;
  timestamp: number;
  samples: Float32Array;
  duration: number;
  sequence: number;
}

// Playback statistics
interface PlaybackStats {
  bufferedMs: number;
  droppedChunks: number;
  underruns: number;
  crossFades: number;
  avgLatency: number;
}

// Cross-fade configuration
interface CrossFadeConfig {
  durationMs: number;    // 80ms cross-fade
  curve: 'linear' | 'exponential';
}

/**
 * Jitter Buffer for smooth audio playback
 * Buffers incoming audio chunks and plays them with cross-fade transitions
 */
export class JitterBuffer extends EventEmitter {
  private audioContext: AudioContext;
  private gainNode: GainNode;
  private buffer: Map<number, AudioChunk> = new Map();
  
  // Configuration
  private readonly bufferSizeMs = 100;  // 100ms buffer per roadmap
  private readonly crossFadeMs = 80;    // 80ms cross-fade per roadmap
  private readonly sampleRate = 16000;  // 16kHz
  
  // Playback state
  private isPlaying = false;
  private nextPlayTime = 0;
  private sequenceCounter = 0;
  private expectedSequence = 0;
  
  // Cross-fade management
  private currentFadeNode: GainNode | null = null;
  private fadeConfig: CrossFadeConfig;
  
  // Statistics
  private stats: PlaybackStats = {
    bufferedMs: 0,
    droppedChunks: 0,
    underruns: 0,
    crossFades: 0,
    avgLatency: 0
  };
  
  // Latency tracking
  private latencyMeasurements: number[] = [];

  constructor(audioContext: AudioContext) {
    super();
    
    this.audioContext = audioContext;
    
    // Create master gain node for volume control
    this.gainNode = this.audioContext.createGain();
    this.gainNode.connect(this.audioContext.destination);
    
    this.fadeConfig = {
      durationMs: this.crossFadeMs,
      curve: 'exponential'
    };
    
    console.log(`🔊 Jitter Buffer initialized: ${this.bufferSizeMs}ms buffer, ${this.crossFadeMs}ms cross-fade`);
  }

  /**
   * Add audio chunk to buffer
   */
  addChunk(audioData: ArrayBuffer, timestamp: number): void {
    const samples = new Float32Array(audioData);
    const duration = (samples.length / this.sampleRate) * 1000; // ms
    
    const chunk: AudioChunk = {
      id: `chunk_${this.sequenceCounter}`,
      timestamp,
      samples,
      duration,
      sequence: this.sequenceCounter++
    };
    
    // Add to buffer
    this.buffer.set(chunk.sequence, chunk);
    
    // Update stats
    this.updateBufferStats();
    
    // Start playback if not already playing
    if (!this.isPlaying && this.buffer.size >= this.getMinBufferChunks()) {
      this.startPlayback();
    }
    
    // Trigger playback of ready chunks
    this.playReadyChunks();
    
    this.emit('chunk.added', chunk.id, duration);
  }

  /**
   * Start playback when buffer has enough data
   */
  private startPlayback(): void {
    if (this.isPlaying) return;
    
    this.isPlaying = true;
    this.nextPlayTime = this.audioContext.currentTime + (this.bufferSizeMs / 1000);
    
    console.log(`▶️ Jitter buffer playback started (${this.bufferSizeMs}ms delay)`);
    this.emit('playback.start');
  }

  /**
   * Play chunks that are ready for playback
   */
  private playReadyChunks(): void {
    if (!this.isPlaying) return;
    
    const currentTime = this.audioContext.currentTime;
    
    // Process chunks in sequence order
    const sortedChunks = Array.from(this.buffer.values())
      .sort((a, b) => a.sequence - b.sequence);
    
    for (const chunk of sortedChunks) {
      if (chunk.sequence === this.expectedSequence) {
        // Check if it's time to play this chunk
        const playbackDelay = (this.bufferSizeMs / 1000);
        const chunkAge = (Date.now() - chunk.timestamp) / 1000;
        
        if (chunkAge >= playbackDelay) {
          this.playChunk(chunk);
          this.buffer.delete(chunk.sequence);
          this.expectedSequence++;
        }
      } else if (chunk.sequence < this.expectedSequence) {
        // Late chunk - drop it
        console.warn(`⚠️ Dropping late chunk ${chunk.id} (seq: ${chunk.sequence}, expected: ${this.expectedSequence})`);
        this.buffer.delete(chunk.sequence);
        this.stats.droppedChunks++;
      }
    }
    
    // Check for buffer underrun
    if (this.buffer.size === 0 && this.isPlaying) {
      console.warn('⚠️ Buffer underrun - pausing playback');
      this.stats.underruns++;
      this.pausePlayback();
    }
  }

  /**
   * Play individual audio chunk with cross-fade
   */
  private playChunk(chunk: AudioChunk): void {
    try {
      // Create audio buffer
      const audioBuffer = this.audioContext.createBuffer(
        1, // mono
        chunk.samples.length,
        this.sampleRate
      );
      audioBuffer.getChannelData(0).set(chunk.samples);
      
      // Create source node
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      
      // Create gain node for this chunk
      const chunkGain = this.audioContext.createGain();
      source.connect(chunkGain);
      chunkGain.connect(this.gainNode);
      
      // Apply cross-fade if there's a previous chunk playing
      if (this.currentFadeNode) {
        this.applyCrossFade(this.currentFadeNode, chunkGain);
      } else {
        // Fade in first chunk
        chunkGain.gain.setValueAtTime(0, this.nextPlayTime);
        chunkGain.gain.linearRampToValueAtTime(1, this.nextPlayTime + 0.01); // 10ms fade-in
      }
      
      // Schedule playback
      source.start(this.nextPlayTime);
      
      // Update timing for next chunk
      this.nextPlayTime += chunk.duration / 1000;
      this.currentFadeNode = chunkGain;
      
      // Calculate and track latency
      const latency = Date.now() - chunk.timestamp;
      this.trackLatency(latency);
      
      this.emit('chunk.played', chunk.id, latency);
      
    } catch (error) {
      console.error(`❌ Error playing chunk ${chunk.id}:`, error);
    }
  }

  /**
   * Apply cross-fade between two audio chunks
   */
  private applyCrossFade(fadeOutNode: GainNode, fadeInNode: GainNode): void {
    const currentTime = this.audioContext.currentTime;
    const fadeTime = this.fadeConfig.durationMs / 1000; // Convert to seconds
    
    if (this.fadeConfig.curve === 'exponential') {
      // Exponential cross-fade (more natural)
      fadeOutNode.gain.exponentialRampToValueAtTime(0.001, currentTime + fadeTime);
      fadeInNode.gain.setValueAtTime(0.001, currentTime);
      fadeInNode.gain.exponentialRampToValueAtTime(1, currentTime + fadeTime);
    } else {
      // Linear cross-fade
      fadeOutNode.gain.linearRampToValueAtTime(0, currentTime + fadeTime);
      fadeInNode.gain.setValueAtTime(0, currentTime);
      fadeInNode.gain.linearRampToValueAtTime(1, currentTime + fadeTime);
    }
    
    this.stats.crossFades++;
    this.emit('crossfade.applied', fadeTime * 1000);
  }

  /**
   * Pause playback (buffer underrun recovery)
   */
  private pausePlayback(): void {
    this.isPlaying = false;
    this.currentFadeNode = null;
    this.emit('playback.pause');
  }

  /**
   * Resume playback when buffer is filled
   */
  resumePlayback(): void {
    if (!this.isPlaying && this.buffer.size >= this.getMinBufferChunks()) {
      this.startPlayback();
      this.emit('playback.resume');
    }
  }

  /**
   * Stop all playback and clear buffer
   */
  stop(): void {
    this.isPlaying = false;
    this.buffer.clear();
    this.nextPlayTime = 0;
    this.expectedSequence = 0;
    this.currentFadeNode = null;
    
    console.log('🛑 Jitter buffer stopped');
    this.emit('playback.stop');
  }

  /**
   * Set master volume
   */
  setVolume(volume: number): void {
    if (volume < 0 || volume > 1) {
      throw new Error('Volume must be between 0 and 1');
    }
    
    this.gainNode.gain.setValueAtTime(volume, this.audioContext.currentTime);
    this.emit('volume.changed', volume);
  }

  /**
   * Apply audio ducking (reduce volume during TTS)
   */
  duck(enabled: boolean, duckLevel: number = 0.125): void { // -18dB ≈ 0.125
    const targetGain = enabled ? duckLevel : 1.0;
    const rampTime = 0.1; // 100ms duck transition
    
    this.gainNode.gain.exponentialRampToValueAtTime(
      Math.max(targetGain, 0.001), // Avoid zero for exponential ramp
      this.audioContext.currentTime + rampTime
    );
    
    console.log(`🦆 Audio ducking: ${enabled ? 'ON' : 'OFF'} (${enabled ? -Math.round(20 * Math.log10(duckLevel)) : 0}dB)`);
    this.emit('ducking.changed', enabled, duckLevel);
  }

  /**
   * Get minimum buffer chunks needed before starting playback
   */
  private getMinBufferChunks(): number {
    // Assume 20ms chunks, need 100ms buffer = 5 chunks minimum
    return Math.ceil(this.bufferSizeMs / 20);
  }

  /**
   * Update buffer statistics
   */
  private updateBufferStats(): void {
    const totalDuration = Array.from(this.buffer.values())
      .reduce((sum, chunk) => sum + chunk.duration, 0);
    
    this.stats.bufferedMs = totalDuration;
  }

  /**
   * Track latency measurements
   */
  private trackLatency(latency: number): void {
    this.latencyMeasurements.push(latency);
    
    // Keep only last 100 measurements
    if (this.latencyMeasurements.length > 100) {
      this.latencyMeasurements.shift();
    }
    
    // Calculate average
    this.stats.avgLatency = this.latencyMeasurements.reduce((a, b) => a + b, 0) / this.latencyMeasurements.length;
  }

  /**
   * Get buffer and playback statistics
   */
  getStats(): PlaybackStats {
    return { ...this.stats };
  }

  /**
   * Get detailed buffer info
   */
  getBufferInfo() {
    return {
      size: this.buffer.size,
      bufferedMs: this.stats.bufferedMs,
      isPlaying: this.isPlaying,
      expectedSequence: this.expectedSequence,
      nextPlayTime: this.nextPlayTime,
      currentTime: this.audioContext.currentTime,
      bufferHealth: Math.min(this.stats.bufferedMs / this.bufferSizeMs, 1.0) // 0-1
    };
  }

  /**
   * Clear old chunks to prevent memory buildup
   */
  cleanup(): void {
    const now = Date.now();
    const maxAge = 5000; // 5 seconds
    
    for (const [sequence, chunk] of this.buffer) {
      if (now - chunk.timestamp > maxAge) {
        this.buffer.delete(sequence);
        console.log(`🧹 Cleaned up old chunk ${chunk.id}`);
      }
    }
  }
}

// Export types
export type { AudioChunk, PlaybackStats, CrossFadeConfig };