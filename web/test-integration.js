#!/usr/bin/env node

/**
 * Integration Test Runner
 * Kör mot live server på localhost:3000
 * 
 * Usage: 
 *   npm run test:integration
 *   node test-integration.js
 */

const { spawn } = require('child_process');
const { runIntegrationTests } = require('./tests/integration.test.js');

async function checkServerHealth() {
  try {
    const response = await fetch('http://localhost:3000/api/health/simple');
    const data = await response.json();
    return data.ok === true;
  } catch (error) {
    return false;
  }
}

async function waitForServer(maxWaitMs = 30000) {
  console.log('🔍 Checking if server is running...');
  
  const startTime = Date.now();
  while (Date.now() - startTime < maxWaitMs) {
    const isHealthy = await checkServerHealth();
    if (isHealthy) {
      console.log('✅ Server is healthy and ready for testing\n');
      return true;
    }
    
    console.log('⏳ Waiting for server...');
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  console.log('❌ Server not responding after 30s');
  return false;
}

async function main() {
  console.log('🚀 Alice FAS Integration Test Suite\n');
  
  // Check if server is running
  const serverReady = await waitForServer();
  if (!serverReady) {
    console.log('💡 Start the server with: npm run dev');
    process.exit(1);
  }
  
  // Run integration tests
  try {
    await runIntegrationTests();
  } catch (error) {
    console.error('💥 Integration test suite failed:', error.message);
    process.exit(1);
  }
}

// Add to global fetch if not available (Node < 18)
if (typeof fetch === 'undefined') {
  global.fetch = require('node-fetch');
}

main().catch(error => {
  console.error('💥 Test runner error:', error);
  process.exit(1);
});