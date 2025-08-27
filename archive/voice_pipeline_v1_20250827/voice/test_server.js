#!/usr/bin/env node
/**
 * 🎙️ Test Server för Voice Pipeline
 * Kör både WebSocket voice server och HTTP server för browser test
 */

import { WebSocket, WebSocketServer } from 'ws';
import { createServer } from 'http';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

console.log('🎙️ Alice Voice Pipeline Test Server');
console.log('='.repeat(50));

/**
 * Voice WebSocket Server (port 8001)
 */
class VoiceServer {
  constructor() {
    this.sessions = new Map();
    this.audioFrames = [];
    this.totalFrames = 0;
    
    // HTTP server för WebSocket
    this.httpServer = createServer();
    this.wsServer = new WebSocketServer({ server: this.httpServer });
    
    this.setupWebSocket();
  }
  
  setupWebSocket() {
    this.wsServer.on('connection', (ws, req) => {
      const sessionId = `session_${Date.now()}`;
      const clientIP = req.socket.remoteAddress;
      
      console.log(`🔌 New voice session: ${sessionId} from ${clientIP}`);
      this.sessions.set(sessionId, ws);
      
      // Skicka handshake
      ws.send(JSON.stringify({
        type: 'handshake',
        sessionId,
        timestamp: Date.now(),
        config: {
          sampleRate: 16000,
          frameSize: 320
        }
      }));
      
      // Hantera meddelanden
      ws.on('message', (data) => {
        if (data instanceof Buffer || data instanceof ArrayBuffer) {
          // Binary audio frame
          let audioBuffer;
          if (data instanceof Buffer) {
            audioBuffer = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
          } else {
            audioBuffer = data;
          }
          
          // Check if buffer size is valid for Float32Array (multiple of 4)
          if (audioBuffer.byteLength % 4 !== 0) {
            console.warn(`⚠️ Invalid audio buffer size: ${audioBuffer.byteLength} bytes (not multiple of 4)`);
            return;
          }
          
          const frame = {
            sessionId,
            timestamp: Date.now(),
            size: audioBuffer.byteLength,
            samples: new Float32Array(audioBuffer)
          };
          
          // Analysera audio
          const energy = this.calculateEnergy(frame.samples);
          const isVoiced = energy > 0.01;
          
          this.audioFrames.push(frame);
          this.totalFrames++;
          
          if (this.totalFrames % 50 === 0 || isVoiced) {
            console.log(`📡 Frame ${this.totalFrames}: ${frame.size}B, energy: ${energy.toFixed(4)}, voiced: ${isVoiced ? '🗣️' : '🔇'}`);
          }
          
          // Simulera server svar för TTS
          if (isVoiced && Math.random() < 0.1) { // 10% chans för demo
            console.log('🗣️ Voice detected, simulerar TTS response...');
            ws.send(JSON.stringify({ type: 'tts.begin', sessionId }));
            
            setTimeout(() => {
              ws.send(JSON.stringify({ type: 'tts.end', sessionId }));
            }, 2000);
          }
          
        } else {
          // JSON control message
          try {
            const message = JSON.parse(data);
            console.log(`💬 Control [${sessionId}]: ${message.type}`);
            
            switch (message.type) {
              case 'control.barge_in':
                console.log('🛑 Barge-in received!');
                break;
              case 'control.mic':
                console.log(`🎤 Mic ${message.enabled ? 'enabled' : 'disabled'}`);
                break;
            }
          } catch (e) {
            console.log(`📝 Text [${sessionId}]: ${data}`);
          }
        }
      });
      
      ws.on('close', () => {
        console.log(`🔌 Session ${sessionId} disconnected`);
        this.sessions.delete(sessionId);
      });
      
      ws.on('error', (error) => {
        console.error(`❌ WebSocket error [${sessionId}]:`, error);
      });
    });
  }
  
  calculateEnergy(samples) {
    let sum = 0;
    for (let i = 0; i < samples.length; i++) {
      sum += samples[i] * samples[i];
    }
    return Math.sqrt(sum / samples.length);
  }
  
  async start() {
    return new Promise((resolve) => {
      this.httpServer.listen(8001, () => {
        console.log('✅ Voice WebSocket Server listening on ws://localhost:8001');
        resolve();
      });
    });
  }
  
  getStats() {
    return {
      activeSessions: this.sessions.size,
      totalFrames: this.totalFrames,
      bufferedFrames: this.audioFrames.length
    };
  }
}

/**
 * HTTP Server för browser test (port 8080)
 */
class TestHTTPServer {
  constructor() {
    this.server = createServer((req, res) => {
      if (req.url === '/' || req.url === '/test') {
        // Servera test HTML
        try {
          const html = readFileSync(join(__dirname, 'test_browser.html'), 'utf8');
          res.writeHead(200, { 
            'Content-Type': 'text/html',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
          });
          res.end(html);
        } catch (error) {
          res.writeHead(404);
          res.end('test_browser.html not found');
        }
        
      } else if (req.url === '/stats') {
        // API för statistik
        const stats = voiceServer.getStats();
        res.writeHead(200, { 
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        });
        res.end(JSON.stringify(stats, null, 2));
        
      } else {
        res.writeHead(404);
        res.end('Not found');
      }
    });
  }
  
  async start() {
    return new Promise((resolve) => {
      this.server.listen(8080, () => {
        console.log('✅ HTTP Test Server listening on http://localhost:8080');
        resolve();
      });
    });
  }
}

// Starta servrar
const voiceServer = new VoiceServer();
const httpServer = new TestHTTPServer();

async function startServers() {
  try {
    await voiceServer.start();
    await httpServer.start();
    
    console.log('');
    console.log('🎉 Alice Voice Pipeline Test Ready!');
    console.log('');
    console.log('📋 Test Options:');
    console.log('   🌐 Browser Test: http://localhost:8080');
    console.log('   🔌 WebSocket:    ws://localhost:8001');
    console.log('   📊 Stats API:    http://localhost:8080/stats');
    console.log('');
    console.log('🧪 Simple Test:   npm test (i annan terminal)');
    console.log('');
    console.log('🛑 Press Ctrl+C to stop servers');
    
    // Stats logging varje 30 sekunder
    setInterval(() => {
      const stats = voiceServer.getStats();
      if (stats.activeSessions > 0 || stats.totalFrames > 0) {
        console.log(`📊 Stats: ${stats.activeSessions} sessions, ${stats.totalFrames} total frames`);
      }
    }, 30000);
    
  } catch (error) {
    console.error('❌ Server startup error:', error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down servers...');
  process.exit(0);
});

startServers();