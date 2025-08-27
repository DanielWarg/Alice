/**
 * E2E Integration Tests - Testar riktiga endpoints mot live system
 * Dessa tester kör mot localhost:3000 och validerar hela kedjan
 */

const BASE_URL = 'http://localhost:3000';

// Helper function för HTTP requests
async function apiCall(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  });
  
  if (!response.ok) {
    throw new Error(`API call failed: ${response.status} ${response.statusText}\nURL: ${url}`);
  }
  
  return response.json();
}

// Test suite
async function runIntegrationTests() {
  console.log('🧪 Starting E2E Integration Tests...\n');
  
  const results = {
    total: 0,
    passed: 0,
    failed: 0,
    failures: []
  };

  // Test function wrapper
  async function test(name, testFn) {
    results.total++;
    console.log(`🔄 Running: ${name}`);
    
    try {
      await testFn();
      results.passed++;
      console.log(`✅ PASS: ${name}\n`);
    } catch (error) {
      results.failed++;
      results.failures.push({ name, error: error.message });
      console.log(`❌ FAIL: ${name}`);
      console.log(`   Error: ${error.message}\n`);
    }
  }

  // === KRITISKA E2E TESTS ===

  // Test 1: Health Check (FAS 0)
  await test('Health endpoints respond correctly', async () => {
    const health = await apiCall('/api/health/simple');
    if (!health.ok || !health.timestamp) {
      throw new Error(`Invalid health response: ${JSON.stringify(health)}`);
    }
  });

  // Test 2: Memory Write/Read Cycle (FAS 3)
  await test('Memory system stores and retrieves data', async () => {
    const testArtifact = {
      user_id: 'integration_test_user',
      text: `Integration test artifact ${Date.now()}`,
      kind: 'test_data',
      score: 0.95
    };

    // Write to memory
    const writeResult = await apiCall('/api/memory/write', {
      method: 'POST',
      body: JSON.stringify(testArtifact)
    });
    
    if (!writeResult.ok) {
      throw new Error(`Memory write failed: ${JSON.stringify(writeResult)}`);
    }

    // Read from memory
    const fetchResult = await apiCall('/api/memory/fetch', {
      method: 'POST', 
      body: JSON.stringify({
        user_id: 'integration_test_user',
        k: 10
      })
    });

    if (!fetchResult.artifacts || fetchResult.artifacts.length === 0) {
      throw new Error(`Memory fetch failed: no artifacts returned`);
    }

    // Verify our artifact exists
    const found = fetchResult.artifacts.some(a => a.text === testArtifact.text);
    if (!found) {
      throw new Error(`Test artifact not found in memory results`);
    }
  });

  // Test 3: Brain Compose Full Flow (FAS 1+4)
  await test('Brain compose with context injection works end-to-end', async () => {
    const request = {
      user_id: 'integration_test_user',
      session_id: `integration_test_${Date.now()}`,
      message: 'Hej Alice! Vad heter du och vad kan du hjälpa mig med?',
      locale: 'sv-SE'
    };

    const response = await apiCall('/api/brain/compose', {
      method: 'POST',
      body: JSON.stringify(request)
    });

    // Validate response structure
    if (!response.spoken_text || !response.meta) {
      throw new Error(`Invalid brain response structure: ${JSON.stringify(response)}`);
    }

    // Validate budget compliance (FAS 4)
    const injectionPct = response.meta.injected_tokens_pct;
    if (injectionPct > 25) {
      throw new Error(`Budget violation: ${injectionPct}% > 25%`);
    }

    // Validate content quality
    if (response.spoken_text.length < 10) {
      throw new Error(`Response too short: "${response.spoken_text}"`);
    }

    console.log(`   📊 Budget: ${injectionPct}%, Artifacts: ${response.meta.artifacts_used || 0}`);
  });

  // Test 4: Metrics Collection (FAS 2)
  await test('Metrics system collects telemetry data', async () => {
    const metrics = await apiCall('/api/metrics/summary');
    
    if (!metrics.ok || !metrics.metrics) {
      throw new Error(`Invalid metrics response: ${JSON.stringify(metrics)}`);
    }

    // Verify metrics structure
    const { e2e_latency, injection_budget, artifacts_usage } = metrics.metrics;
    if (!e2e_latency || !injection_budget || !artifacts_usage) {
      throw new Error(`Missing metrics sections`);
    }

    console.log(`   📈 Events: ${e2e_latency.count}, Compliance: ${injection_budget.budget_compliance_rate}`);
  });

  // Test 5: Weather Tool Integration
  await test('Weather tool returns valid data', async () => {
    const weather = await apiCall('/api/tools/weather.get', {
      method: 'POST',
      body: JSON.stringify({
        location: 'Stockholm'
      })
    });

    // Check new API structure
    if (!weather.ok || !weather.now?.temp || !weather.now?.condition) {
      throw new Error(`Invalid weather response: ${JSON.stringify(weather)}`);
    }

    console.log(`   🌤️ Weather: ${weather.location_resolved?.name} ${weather.now.temp}°C`);
  });

  // Test 6: Agent Integration Full Flow
  await test('Agent processes request with tools', async () => {
    const request = {
      session_id: `agent_test_${Date.now()}`,
      messages: [
        { role: 'user', content: 'Hej Alice, vad heter du?' }
      ],
      allow_tools: true
    };

    const response = await apiCall('/api/agent', {
      method: 'POST',
      body: JSON.stringify(request)
    });

    // Agent can either respond directly or make tool calls
    if (!response.session_id || (!response.assistant?.content && !response.assistant?.tool_calls)) {
      throw new Error(`Invalid agent response: ${JSON.stringify(response)}`);
    }

    // If tool_call response, that's valid
    if (response.next_action === 'tool_call') {
      console.log(`   🔧 Agent tool calls: ${response.assistant?.tool_calls?.length || 0}`);
    } else {
      console.log(`   💬 Agent response: "${response.assistant?.content?.substring(0, 50) || ''}..."`);
    }

    console.log(`   🤖 Agent latency: ${response.metrics?.llm_latency_ms || 'N/A'}ms`);
  });

  // === RESULTS SUMMARY ===
  console.log('\n' + '='.repeat(50));
  console.log('🧪 INTEGRATION TEST RESULTS');
  console.log('='.repeat(50));
  console.log(`Total Tests: ${results.total}`);
  console.log(`✅ Passed: ${results.passed}`);
  console.log(`❌ Failed: ${results.failed}`);
  
  if (results.failures.length > 0) {
    console.log('\n💥 FAILURES:');
    results.failures.forEach(f => {
      console.log(`   • ${f.name}: ${f.error}`);
    });
  }

  console.log(`\n🎯 Success Rate: ${Math.round((results.passed / results.total) * 100)}%`);
  
  // Exit with error code if any tests failed
  if (results.failed > 0) {
    console.log('\n🚨 INTEGRATION TESTS FAILED - System not ready for deployment');
    process.exit(1);
  } else {
    console.log('\n🎉 ALL INTEGRATION TESTS PASSED - System ready for deployment');
    process.exit(0);
  }
}

// Run tests if called directly
if (require.main === module) {
  runIntegrationTests().catch(error => {
    console.error('💥 Test runner crashed:', error);
    process.exit(1);
  });
}

module.exports = { runIntegrationTests };