// Quick WebSocket Test for /ws/alice endpoint
console.log('🧪 Testing WebSocket connection to /ws/alice...');

const sessionId = `quick_test_${Date.now()}`;
const wsUrl = `ws://127.0.0.1:8000/ws/alice`;

console.log('🔗 Connecting to:', wsUrl);

const ws = new WebSocket(wsUrl);
const testStartTime = Date.now();

ws.onopen = () => {
  const connectionTime = Date.now() - testStartTime;
  console.log(`✅ Connected successfully in ${connectionTime}ms`);
  
  // Send test ping
  const pingMessage = { type: 'ping', timestamp: Date.now(), test: true };
  ws.send(JSON.stringify(pingMessage));
  console.log('📤 Sent ping:', pingMessage);
  
  // Send voice test
  const voiceMessage = { type: 'audio_chunk', data: 'test_audio_data' };
  ws.send(JSON.stringify(voiceMessage));
  console.log('📤 Sent voice test:', voiceMessage);
  
  // Close after 3 seconds
  setTimeout(() => {
    console.log('🔌 Closing connection...');
    ws.close(1000, 'test-complete');
  }, 3000);
};

ws.onmessage = (event) => {
  console.log('📨 Received message:', event.data);
  
  try {
    const parsed = JSON.parse(event.data);
    console.log('📨 Parsed message:', parsed);
  } catch (e) {
    console.log('📨 Raw message (not JSON):', event.data);
  }
};

ws.onerror = (event) => {
  console.error('❌ WebSocket error:', event);
};

ws.onclose = (event) => {
  const totalTime = Date.now() - testStartTime;
  console.log(`🔌 Connection closed after ${totalTime}ms`);
  console.log('🔌 Close event:', {
    code: event.code,
    reason: event.reason,
    wasClean: event.wasClean
  });
  
  if (event.wasClean) {
    console.log('✅ WebSocket test completed successfully!');
  } else {
    console.log('⚠️ Connection closed unexpectedly');
  }
};