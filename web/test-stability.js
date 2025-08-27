/**
 * Agent Stability Test - 100 sequential calls
 * Done criteria: 0 × 5xx på /api/agent under 100 sekventiella körningar
 */

const API_BASE = 'http://localhost:3001';

async function runSingleAgentCall(id) {
  try {
    const response = await fetch(`${API_BASE}/api/agent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: `stability_test_${id}`,
        messages: [{ role: 'user', content: 'Hej Alice, hur mår du?' }],
        allow_tool_calls: true
      })
    });

    return {
      id,
      status: response.status,
      ok: response.ok,
      latency: Date.now()
    };
    
  } catch (error) {
    return {
      id,
      status: 0,
      ok: false,
      error: error.message
    };
  }
}

async function runStabilityTest() {
  console.log('🏃 Starting Agent Stability Test - 100 sequential calls');
  console.log('====================================================');
  
  const results = [];
  const latencies = [];
  let errors5xx = 0;
  let errors4xx = 0;
  let success = 0;
  
  const startTime = Date.now();
  
  for (let i = 1; i <= 100; i++) {
    const callStart = Date.now();
    const result = await runSingleAgentCall(i);
    const callLatency = Date.now() - callStart;
    
    results.push(result);
    latencies.push(callLatency);
    
    if (result.status >= 500) {
      errors5xx++;
      console.log(`❌ Call ${i}: ${result.status} (${callLatency}ms)`);
    } else if (result.status >= 400) {
      errors4xx++;
      if (i <= 5 || i % 10 === 0) console.log(`⚠️  Call ${i}: ${result.status} (${callLatency}ms)`);
    } else if (result.ok) {
      success++;
      if (i <= 5 || i % 10 === 0) console.log(`✅ Call ${i}: ${result.status} (${callLatency}ms)`);
    } else {
      console.log(`💥 Call ${i}: Network error - ${result.error}`);
    }
  }
  
  const totalTime = Date.now() - startTime;
  const avgLatency = latencies.reduce((a, b) => a + b, 0) / latencies.length;
  const p95Latency = latencies.sort((a, b) => a - b)[Math.floor(latencies.length * 0.95)];
  
  console.log('\n📊 Stability Test Results');
  console.log('==========================');
  console.log(`✅ Success: ${success}/100 (${(success/100*100).toFixed(1)}%)`);
  console.log(`⚠️  4xx errors: ${errors4xx}/100 (${(errors4xx/100*100).toFixed(1)}%)`);  
  console.log(`❌ 5xx errors: ${errors5xx}/100 (${(errors5xx/100*100).toFixed(1)}%)`);
  console.log(`⏱️  Average latency: ${avgLatency.toFixed(0)}ms`);
  console.log(`⏱️  P95 latency: ${p95Latency}ms`);
  console.log(`🕐 Total time: ${(totalTime/1000).toFixed(1)}s`);
  
  console.log('\n🎯 Done Criteria Check:');
  console.log('========================');
  
  if (errors5xx === 0) {
    console.log(`✅ 0 × 5xx på /api/agent ✓`);
  } else {
    console.log(`❌ ${errors5xx} × 5xx på /api/agent ✗`);
  }
  
  if (p95Latency <= 1200) {
    console.log(`✅ Dashboard p95 ≤ 1200ms: ${p95Latency}ms ✓`);
  } else {
    console.log(`❌ Dashboard p95 > 1200ms: ${p95Latency}ms ✗`);
  }
  
  const allPassed = errors5xx === 0 && p95Latency <= 1200;
  
  if (allPassed) {
    console.log(`\n🎉 STABILITY TEST PASSED - Agent ready for production!`);
    process.exit(0);
  } else {
    console.log(`\n💥 STABILITY TEST FAILED - Agent needs more work`);
    process.exit(1);
  }
}

runStabilityTest().catch(error => {
  console.error('Stability test crashed:', error);
  process.exit(1);
});