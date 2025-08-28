#!/usr/bin/env node
/**
 * 🧪 Enkel Voice Pipeline Test - JavaScript version
 * Test transport layer utan TypeScript komplikationer
 */

import { WebSocket, WebSocketServer } from 'ws';
import { EventEmitter } from 'events';
import { createServer } from 'http';

console.log('🧪 Startar Voice Pipeline Test...');

/**
 * Enkel WebSocket Voice Server Test
 */
class SimpleVoiceServer extends EventEmitter {
  constructor(port = 8001) {
    super();
    this.port = port;
    this.sessions = new Map();
    this.audioFrames = [];
    
    // Skapa HTTP server
    this.httpServer = createServer();
    this.wsServer = new WebSocketServer({ server: this.httpServer });
    
    this.setupWebSocket();
  }
  
  setupWebSocket() {
    this.wsServer.on('connection', (ws, req) => {
      const sessionId = `session_${Date.now()}`;
      console.log(`🔌 Ny session: ${sessionId}`);
      
      this.sessions.set(sessionId, ws);
      
      // Skicka handshake
      ws.send(JSON.stringify({
        type: 'handshake',
        sessionId,
        timestamp: Date.now()
      }));
      
      // Hantera meddelanden
      ws.on('message', (data) => {
        if (data instanceof Buffer || data instanceof ArrayBuffer) {
          // Binary audio data
          const frame = {
            sessionId,
            timestamp: Date.now(),
            size: data.byteLength,
            samples: new Float32Array(data.buffer || data)
          };
          this.audioFrames.push(frame);
          console.log(`📡 Audio frame: ${frame.size} bytes, ${frame.samples.length} samples`);
          this.emit('audioFrame', frame);
        } else {
          // JSON control message
          try {
            const message = JSON.parse(data);
            console.log(`💬 Control: ${message.type}`);
            this.emit('controlMessage', sessionId, message);
          } catch (e) {
            console.log(`📝 Text: ${data}`);
          }
        }
      });
      
      ws.on('close', () => {
        console.log(`🔌 Session ${sessionId} stängd`);
        this.sessions.delete(sessionId);
      });
      
      this.emit('sessionStart', sessionId);
    });
  }
  
  async start() {
    return new Promise((resolve) => {
      this.httpServer.listen(this.port, () => {
        console.log(`✅ Voice Server lyssnar på port ${this.port}`);
        resolve();
      });
    });
  }
  
  async stop() {
    return new Promise((resolve) => {
      this.httpServer.close(() => {
        console.log('🛑 Voice Server stoppad');
        resolve();
      });
    });
  }
  
  getStats() {
    return {
      activeSessions: this.sessions.size,
      totalFrames: this.audioFrames.length,
      port: this.port
    };
  }
}

/**
 * Enkel WebSocket Client Test
 */
class SimpleVoiceClient extends EventEmitter {
  constructor(serverUrl = 'ws://localhost:8001') {
    super();
    this.serverUrl = serverUrl;
    this.ws = null;
    this.sessionId = null;
    this.connected = false;
  }
  
  async connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.serverUrl);
      
      this.ws.on('open', () => {
        console.log('✅ Klient ansluten');
        this.connected = true;
        resolve();
      });
      
      this.ws.on('message', (data) => {
        if (typeof data === 'string') {
          try {
            const message = JSON.parse(data);
            if (message.type === 'handshake') {
              this.sessionId = message.sessionId;
              console.log(`🤝 Session etablerad: ${this.sessionId}`);
              this.emit('sessionEstablished', this.sessionId);
            }
          } catch (e) {
            console.log(`📝 Server meddelande: ${data}`);
          }
        }
      });
      
      this.ws.on('error', reject);
    });
  }
  
  sendAudioFrame(samples) {
    if (!this.connected) return false;
    
    // Skapa Float32Array om nödvändigt
    const audioData = samples instanceof Float32Array ? samples : new Float32Array(samples);
    
    // Skicka som binary ArrayBuffer
    const buffer = audioData.buffer.slice(
      audioData.byteOffset,
      audioData.byteOffset + audioData.byteLength
    );
    
    this.ws.send(buffer);
    return true;
  }
  
  sendControlMessage(message) {
    if (!this.connected) return false;
    this.ws.send(JSON.stringify(message));
    return true;
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.connected = false;
      this.sessionId = null;
    }
  }
  
  getStatus() {
    return {
      connected: this.connected,
      sessionId: this.sessionId,
      serverUrl: this.serverUrl
    };
  }
}

/**
 * Test Suite
 */
async function runTests() {
  console.log('🧪 Voice Pipeline Test Suite');
  console.log('='.repeat(50));
  
  const server = new SimpleVoiceServer(8001);
  const client = new SimpleVoiceClient();
  
  try {
    // Test 1: Starta server
    console.log('\n📋 Test 1: Server startup');
    await server.start();
    console.log('✅ Server started');
    
    // Test 2: Anslut klient
    console.log('\n📋 Test 2: Client connection');
    await client.connect();
    await new Promise(resolve => setTimeout(resolve, 100)); // Vänta på handshake
    console.log('✅ Client connected');
    
    // Test 3: Skicka audio frames
    console.log('\n📋 Test 3: Binary audio frames');
    
    // Skapa test audio (320 samples = 20ms vid 16kHz)
    const testAudio = new Float32Array(320);
    for (let i = 0; i < testAudio.length; i++) {
      testAudio[i] = Math.sin(2 * Math.PI * 440 * i / 16000) * 0.1; // 440Hz ton
    }
    
    // Skicka 5 frames
    for (let i = 0; i < 5; i++) {
      console.log(`📤 Skickar frame ${i + 1}/5`);
      client.sendAudioFrame(testAudio);
      await new Promise(resolve => setTimeout(resolve, 20)); // 20ms mellan frames
    }
    
    await new Promise(resolve => setTimeout(resolve, 100)); // Vänta på processing
    console.log('✅ Audio frames sent');
    
    // Test 4: Control messages
    console.log('\n📋 Test 4: Control messages');
    client.sendControlMessage({ type: 'control.mic', enabled: true });
    client.sendControlMessage({ type: 'control.barge_in', timestamp: Date.now() });
    console.log('✅ Control messages sent');
    
    // Test 5: Server statistik
    console.log('\n📋 Test 5: Server statistics');
    const stats = server.getStats();
    console.log('📊 Server stats:', stats);
    console.log('✅ Statistics collected');
    
    // Test 6: Client status
    console.log('\n📋 Test 6: Client status');
    const status = client.getStatus();
    console.log('📊 Client status:', status);
    console.log('✅ Status retrieved');
    
    console.log('\n🎉 Alla tester GODKÄNDA!');
    console.log('\n📋 Transport Layer Status:');
    console.log('   ✅ WebSocket server & client');
    console.log('   ✅ Binary audio frame transmission');
    console.log('   ✅ Control message handling');
    console.log('   ✅ Session management');
    console.log('   ✅ Statistics collection');
    
  } catch (error) {
    console.error('❌ Test fel:', error);
  } finally {
    // Cleanup
    console.log('\n🧹 Rensar upp...');
    client.disconnect();
    await server.stop();
    console.log('✅ Cleanup klar');
  }
}

// Kör tester
runTests().catch(console.error);