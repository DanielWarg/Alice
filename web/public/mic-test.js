// Simple Mic Button Test - Paste in browser console

console.log('🎤 Testing mic button...');

// Find the mic button
function findMicButton() {
  // Try various selectors
  let btn = document.querySelector('button[title*="röstgateway"]');
  if (btn) return { btn, method: 'title-selector' };
  
  // Look for button with microphone SVG
  const buttons = Array.from(document.querySelectorAll('button'));
  btn = buttons.find(button => {
    const svg = button.querySelector('svg');
    if (!svg) return false;
    const paths = Array.from(svg.querySelectorAll('path'));
    return paths.some(path => 
      path.getAttribute('d')?.includes('M12 2a3 3 0 0 0-3 3v7') // Mic path
    );
  });
  
  if (btn) return { btn, method: 'svg-search' };
  return null;
}

const result = findMicButton();
if (!result) {
  console.error('❌ Mic button not found');
} else {
  console.log('✅ Mic button found via:', result.method);
  console.log('Button element:', result.btn);
  console.log('Button classes:', result.btn.className);
  console.log('Button title:', result.btn.title);
  
  // Test clicking the button
  console.log('🖱️ Clicking mic button...');
  
  // Listen for WebSocket activity
  const originalWebSocket = window.WebSocket;
  let wsConnections = [];
  
  window.WebSocket = function(...args) {
    console.log('🌐 New WebSocket connection:', args[0]);
    const ws = new originalWebSocket(...args);
    wsConnections.push({ url: args[0], ws, created: Date.now() });
    
    ws.addEventListener('open', () => {
      console.log('✅ WebSocket opened:', args[0]);
    });
    
    ws.addEventListener('close', (event) => {
      console.log('🔌 WebSocket closed:', args[0], 'Code:', event.code, 'Reason:', event.reason);
    });
    
    ws.addEventListener('error', (event) => {
      console.error('❌ WebSocket error:', args[0], event);
    });
    
    ws.addEventListener('message', (event) => {
      console.log('📨 WebSocket message:', args[0], event.data);
    });
    
    return ws;
  };
  
  // Click the button
  try {
    result.btn.click();
    console.log('✅ Button clicked successfully');
    
    // Wait and report results
    setTimeout(() => {
      console.log('📊 WebSocket connections created:', wsConnections.length);
      wsConnections.forEach((conn, i) => {
        console.log(`  ${i + 1}. ${conn.url} (${conn.ws.readyState === 1 ? 'OPEN' : 'CLOSED'})`);
      });
      
      // Restore original WebSocket
      window.WebSocket = originalWebSocket;
    }, 3000);
    
  } catch (error) {
    console.error('❌ Failed to click button:', error);
  }
}