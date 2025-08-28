/**
 * Alice Voice Pipeline Server
 * Sub-500ms streaming voice pipeline with WebSocket transport
 */

import WebSocket from 'ws';
import { v4 as uuidv4 } from 'uuid';
import { VoicePipeline } from './pipeline';
import { VoiceRouter } from '../router';
import { MetricsLogger } from './metrics/logger';
import { UpstreamEvent, DownstreamEvent, VoiceConfig, DEFAULT_VOICE_CONFIG } from '../types/events';

interface VoiceSession {
  id: string;
  ws: WebSocket;
  pipeline: VoicePipeline;
  createdAt: number;
  lastActivity: number;
}

export class VoicePipelineServer {
  private server: WebSocket.Server;
  private sessions: Map<string, VoiceSession> = new Map();
  private router: VoiceRouter;
  private metrics: MetricsLogger;
  private config: VoiceConfig;

  constructor(port: number = 8001, config: Partial<VoiceConfig> = {}) {
    this.config = { ...DEFAULT_VOICE_CONFIG, ...config };
    this.router = new VoiceRouter(this.config);
    this.metrics = new MetricsLogger();
    
    this.server = new WebSocket.Server({ 
      port,
      perMessageDeflate: false, // Disable compression for low latency
    });

    this.setupServer();
    console.log(`🎙️ Alice Voice Pipeline Server running on port ${port}`);
  }

  private setupServer(): void {
    this.server.on('connection', (ws: WebSocket) => {
      const sessionId = uuidv4();
      const pipeline = new VoicePipeline(sessionId, this.router, this.metrics);
      
      const session: VoiceSession = {
        id: sessionId,
        ws,
        pipeline,
        createdAt: Date.now(),
        lastActivity: Date.now()
      };

      this.sessions.set(sessionId, session);
      console.log(`🔗 New voice session: ${sessionId}`);

      // Setup pipeline event forwarding
      pipeline.on('downstream', (event: DownstreamEvent) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify(event));
        }
      });

      // Handle incoming messages
      ws.on('message', (data: Buffer) => {
        session.lastActivity = Date.now();
        
        try {
          // Handle binary audio frames
          if (data instanceof Buffer && data.length > 4) {
            const header = data.readUInt32LE(0);
            if (header === 0x41554449) { // 'AUDI' magic number
              const audioFrame: UpstreamEvent = {
                type: 'audio.frame',
                sessionId,
                seq: data.readUInt32LE(4),
                data: data.slice(12),
                timestamp: Date.now()
              };
              pipeline.handleUpstream(audioFrame);
              return;
            }
          }

          // Handle JSON control messages
          const event: UpstreamEvent = JSON.parse(data.toString());
          event.sessionId = sessionId; // Ensure sessionId is set
          pipeline.handleUpstream(event);
          
        } catch (error) {
          console.error(`❌ Error processing message from ${sessionId}:`, error);
          this.sendError(ws, 'Invalid message format');
        }
      });

      ws.on('close', () => {
        console.log(`🔌 Voice session closed: ${sessionId}`);
        pipeline.cleanup();
        this.sessions.delete(sessionId);
      });

      ws.on('error', (error) => {
        console.error(`❌ WebSocket error for ${sessionId}:`, error);
      });

      // Send initial connection confirmation
      ws.send(JSON.stringify({
        type: 'connection.ready',
        sessionId,
        config: this.config,
        timestamp: Date.now()
      }));
    });

    // Cleanup inactive sessions
    setInterval(() => {
      const now = Date.now();
      const staleThreshold = 5 * 60 * 1000; // 5 minutes
      
      for (const [sessionId, session] of this.sessions) {
        if (now - session.lastActivity > staleThreshold) {
          console.log(`🧹 Cleaning up stale session: ${sessionId}`);
          session.ws.terminate();
          session.pipeline.cleanup();
          this.sessions.delete(sessionId);
        }
      }
    }, 60000); // Check every minute
  }

  private sendError(ws: WebSocket, message: string): void {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'error',
        message,
        timestamp: Date.now()
      }));
    }
  }

  public getMetrics(): any {
    return {
      activeSessions: this.sessions.size,
      totalSessions: this.metrics.getTotalSessions(),
      avgLatency: this.metrics.getAverageLatency(),
      performance: this.metrics.getPerformanceStats()
    };
  }

  public close(): void {
    console.log('🛑 Shutting down Voice Pipeline Server...');
    
    // Close all active sessions
    for (const session of this.sessions.values()) {
      session.pipeline.cleanup();
      session.ws.terminate();
    }
    this.sessions.clear();
    
    // Close server
    this.server.close();
  }
}

// Export singleton instance
let serverInstance: VoicePipelineServer | null = null;

export function createVoicePipelineServer(port?: number, config?: Partial<VoiceConfig>): VoicePipelineServer {
  if (serverInstance) {
    throw new Error('Voice Pipeline Server already exists. Use getVoicePipelineServer() instead.');
  }
  
  serverInstance = new VoicePipelineServer(port, config);
  return serverInstance;
}

export function getVoicePipelineServer(): VoicePipelineServer | null {
  return serverInstance;
}

// CLI entry point
if (require.main === module) {
  const port = parseInt(process.env.VOICE_PORT || '8001');
  createVoicePipelineServer(port);
  
  // Graceful shutdown
  process.on('SIGINT', () => {
    if (serverInstance) {
      serverInstance.close();
    }
    process.exit(0);
  });
}