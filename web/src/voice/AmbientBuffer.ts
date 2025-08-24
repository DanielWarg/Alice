// Ambient ringbuffer för kontinuerlig transkribering och autosammanfattning
import { FinalEvent, PartialEvent } from './RealtimeASR';
import { scoreImportance, ImportanceScore } from './importance';

export interface AmbientChunk {
  text: string;
  ts: Date;
  speaker?: 'user' | 'assistant';
  confidence: number;
  importance?: ImportanceScore;
  source: 'realtime' | 'whisper' | 'browser';
}

export interface AmbientSummary {
  windowStart: Date;
  windowEnd: Date;
  highlights: Array<{
    text: string;
    score: number;
    ts: Date;
  }>;
  rawRef: string;
  chunkCount: number;
}

export class AmbientBuffer {
  private chunks: AmbientChunk[] = [];
  private maxBufferMinutes = 15;
  private summaryIntervalMs: number;
  private summaryTimer?: NodeJS.Timeout;
  private lastSummaryTime = new Date();
  private subs = new Set<(event: AmbientEvent) => void>();
  
  private config = {
    summaryIntervalMs: parseInt(process.env.NEXT_PUBLIC_AMBIENT_SUMMARY_INTERVAL_MS || '90000'),
    minHighlightScore: 2,
    maxChunksPerSummary: 100,
  };

  constructor() {
    this.summaryIntervalMs = this.config.summaryIntervalMs;
    this.startSummaryTimer();
  }

  on(callback: (event: AmbientEvent) => void): () => void {
    this.subs.add(callback);
    return () => this.subs.delete(callback);
  }

  addPartial(event: PartialEvent): void {
    // Partials används bara för UI-feedback, sparas inte i buffer
    this.emit({
      type: 'partial_received',
      text: event.text,
      ts: event.ts,
      confidence: event.confidence
    });
  }

  addFinal(event: FinalEvent): void {
    const importance = event.importance !== undefined 
      ? { score: event.importance, reasons: [] }
      : scoreImportance(event.text);

    const chunk: AmbientChunk = {
      text: event.text,
      ts: event.ts,
      speaker: 'user', // För nu, senare kan vi detektera speaker
      confidence: event.confidence,
      importance,
      source: event.quality === 'realtime' ? 'realtime' : 'whisper'
    };

    this.chunks.push(chunk);
    this.pruneOldChunks();
    
    this.emit({
      type: 'chunk_added',
      chunk,
      bufferSize: this.chunks.length
    });

    // Skicka rådata till server för persistering
    this.ingestRawChunk(chunk);
  }

  getRecentChunks(windowMinutes: number = 10): AmbientChunk[] {
    const cutoff = new Date(Date.now() - windowMinutes * 60 * 1000);
    return this.chunks.filter(chunk => chunk.ts >= cutoff);
  }

  getHighlights(windowMinutes: number = 10): Array<{ text: string; score: number; ts: Date }> {
    return this.getRecentChunks(windowMinutes)
      .filter(chunk => chunk.importance && chunk.importance.score >= this.config.minHighlightScore)
      .map(chunk => ({
        text: chunk.text,
        score: chunk.importance!.score,
        ts: chunk.ts
      }))
      .slice(-this.config.maxChunksPerSummary);
  }

  private startSummaryTimer(): void {
    this.summaryTimer = setInterval(() => {
      this.generateSummary();
    }, this.summaryIntervalMs);
  }

  private async generateSummary(): Promise<void> {
    const now = new Date();
    const windowMinutes = Math.max(1, this.summaryIntervalMs / 60000);
    
    const recentChunks = this.getRecentChunks(windowMinutes);
    
    if (recentChunks.length === 0) {
      console.log('AmbientBuffer: No chunks for summary');
      return;
    }

    const highlights = this.getHighlights(windowMinutes);
    
    if (highlights.length === 0) {
      console.log('AmbientBuffer: No highlights for summary, skipping');
      return;
    }

    const summary: AmbientSummary = {
      windowStart: this.lastSummaryTime,
      windowEnd: now,
      highlights,
      rawRef: `ambient:${this.lastSummaryTime.toISOString()}`,
      chunkCount: recentChunks.length
    };

    console.log(`AmbientBuffer: Creating summary with ${highlights.length} highlights from ${recentChunks.length} chunks`);

    try {
      await this.submitSummary(summary);
      this.lastSummaryTime = now;
      
      this.emit({
        type: 'summary_created',
        summary,
        ts: now
      });
    } catch (error) {
      console.error('AmbientBuffer: Failed to submit summary:', error);
      this.emit({
        type: 'error',
        error: `Summary submission failed: ${error}`,
        ts: now
      });
    }
  }

  private async ingestRawChunk(chunk: AmbientChunk): Promise<void> {
    try {
      const response = await fetch('/api/memory/ambient/ingest-raw', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chunks: [{
            text: chunk.text,
            ts: chunk.ts.toISOString(),
            conf: chunk.confidence,
            speaker: chunk.speaker,
            source: chunk.source,
            importance: chunk.importance
          }]
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      console.error('AmbientBuffer: Failed to ingest raw chunk:', error);
    }
  }

  private async submitSummary(summary: AmbientSummary): Promise<void> {
    const response = await fetch('/api/memory/ambient/summary', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        windowSec: Math.floor((summary.windowEnd.getTime() - summary.windowStart.getTime()) / 1000),
        highlights: summary.highlights,
        rawRef: summary.rawRef,
        windowStart: summary.windowStart.toISOString(),
        windowEnd: summary.windowEnd.toISOString(),
        chunkCount: summary.chunkCount
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
  }

  private pruneOldChunks(): void {
    const cutoff = new Date(Date.now() - this.maxBufferMinutes * 60 * 1000);
    const originalLength = this.chunks.length;
    this.chunks = this.chunks.filter(chunk => chunk.ts >= cutoff);
    
    if (this.chunks.length < originalLength) {
      console.log(`AmbientBuffer: Pruned ${originalLength - this.chunks.length} old chunks`);
    }
  }

  private emit(event: AmbientEvent): void {
    this.subs.forEach(callback => callback(event));
  }

  stop(): void {
    if (this.summaryTimer) {
      clearInterval(this.summaryTimer);
      this.summaryTimer = undefined;
    }
  }

  // Debugging methods
  getBufferStats(): { totalChunks: number; highScoreChunks: number; oldestChunk?: Date; newestChunk?: Date } {
    const highScoreChunks = this.chunks.filter(
      chunk => chunk.importance && chunk.importance.score >= this.config.minHighlightScore
    ).length;

    return {
      totalChunks: this.chunks.length,
      highScoreChunks,
      oldestChunk: this.chunks.length > 0 ? this.chunks[0].ts : undefined,
      newestChunk: this.chunks.length > 0 ? this.chunks[this.chunks.length - 1].ts : undefined
    };
  }
}

export interface PartialReceivedEvent {
  type: 'partial_received';
  text: string;
  ts: Date;
  confidence: number;
}

export interface ChunkAddedEvent {
  type: 'chunk_added';
  chunk: AmbientChunk;
  bufferSize: number;
}

export interface SummaryCreatedEvent {
  type: 'summary_created';
  summary: AmbientSummary;
  ts: Date;
}

export interface AmbientErrorEvent {
  type: 'error';
  error: string;
  ts: Date;
}

export type AmbientEvent = PartialReceivedEvent | ChunkAddedEvent | SummaryCreatedEvent | AmbientErrorEvent;