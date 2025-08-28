#!/usr/bin/env node
/**
 * Performance Analysis for Alice Voice System
 * Tests multiple scenarios and identifies bottlenecks
 */

const agentUrl = 'http://localhost:3000/api/agent';
const healthUrl = 'http://localhost:3000/api/health';

// Test scenarios for performance
const testScenarios = [
  {
    name: 'Simple Chat',
    payload: {
      session_id: 'perf_simple',
      messages: [{ role: 'user', content: 'Hej' }]
    }
  },
  {
    name: 'Timer Tool Call',
    payload: {
      session_id: 'perf_timer',
      messages: [{ role: 'user', content: 'sätt en timer på 5 minuter' }]
    }
  },
  {
    name: 'Weather Tool Call',
    payload: {
      session_id: 'perf_weather',  
      messages: [{ role: 'user', content: 'vad är vädret i Stockholm?' }]
    }
  },
  {
    name: 'Long Conversation',
    payload: {
      session_id: 'perf_long',
      messages: [
        { role: 'user', content: 'Hej Alice' },
        { role: 'assistant', content: 'Hej! Hur kan jag hjälpa dig?' },
        { role: 'user', content: 'Berätta om vädret' },
        { role: 'assistant', content: 'Jag kan hjälpa dig med väder. Vilken stad?' },
        { role: 'user', content: 'Stockholm tack' }
      ]
    }
  }
];

async function measureLatency(url, payload, iterations = 10) {
  const latencies = [];
  const errors = [];
  
  console.log(`\n🎯 Testing ${iterations} iterations...`);
  
  for (let i = 0; i < iterations; i++) {
    const start = Date.now();
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, session_id: `${payload.session_id}_${i}` })
      });
      
      const latency = Date.now() - start;
      latencies.push(latency);
      
      if (response.ok) {
        const data = await response.json();
        console.log(`  ${i+1}. ✅ ${latency}ms${data.next_action === 'tool_call' ? ' [tool]' : ''}`);
      } else {
        console.log(`  ${i+1}. ❌ ${response.status} (${latency}ms)`);
        errors.push({ status: response.status, latency });
      }
      
    } catch (error) {
      const latency = Date.now() - start;
      console.log(`  ${i+1}. 💥 Error (${latency}ms): ${error.message}`);
      errors.push({ error: error.message, latency });
    }
    
    // Small delay between requests
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  return { latencies, errors };
}

function calculateStats(latencies) {
  if (latencies.length === 0) return null;
  
  const sorted = [...latencies].sort((a, b) => a - b);
  const sum = sorted.reduce((a, b) => a + b, 0);
  
  return {
    count: sorted.length,
    min: sorted[0],
    max: sorted[sorted.length - 1],
    mean: Math.round(sum / sorted.length),
    p50: sorted[Math.floor(sorted.length * 0.5)],
    p95: sorted[Math.floor(sorted.length * 0.95)],
    p99: sorted[Math.floor(sorted.length * 0.99)]
  };
}

async function testHealth() {
  console.log('\n🏥 Health Check Performance');
  console.log('============================');
  
  const { latencies, errors } = await measureLatency(healthUrl, {}, 20);
  const stats = calculateStats(latencies);
  
  if (stats) {
    console.log(`\n📊 Health Endpoint Stats:`);
    console.log(`   Requests: ${stats.count}`);
    console.log(`   Mean: ${stats.mean}ms`);
    console.log(`   P50: ${stats.p50}ms`);
    console.log(`   P95: ${stats.p95}ms`);
    console.log(`   Range: ${stats.min}-${stats.max}ms`);
  }
  
  if (errors.length > 0) {
    console.log(`\n❌ Errors: ${errors.length}`);
  }
  
  return stats;
}

async function main() {
  console.log('🚀 Alice Performance Analysis');
  console.log('==============================');
  
  const results = {};
  
  // Test health endpoint first
  results.health = await testHealth();
  
  // Test each scenario
  for (const scenario of testScenarios) {
    console.log(`\n🧪 Testing: ${scenario.name}`);
    console.log('─'.repeat(40));
    
    const { latencies, errors } = await measureLatency(agentUrl, scenario.payload, 15);
    const stats = calculateStats(latencies);
    
    if (stats) {
      console.log(`\n📊 ${scenario.name} Stats:`);
      console.log(`   Requests: ${stats.count}`);
      console.log(`   Mean: ${stats.mean}ms`);
      console.log(`   P50: ${stats.p50}ms`);
      console.log(`   P95: ${stats.p95}ms`);
      console.log(`   Range: ${stats.min}-${stats.max}ms`);
      
      // Performance targets
      const p95Target = 1200;
      const p95Status = stats.p95 <= p95Target ? '✅' : '❌';
      console.log(`   P95 Target (≤${p95Target}ms): ${p95Status} ${stats.p95}ms`);
    }
    
    if (errors.length > 0) {
      console.log(`\n❌ Errors: ${errors.length}`);
      errors.slice(0, 3).forEach(e => {
        console.log(`   - ${e.status || 'Network'}: ${e.latency}ms`);
      });
    }
    
    results[scenario.name] = { stats, errors: errors.length };
  }
  
  // Overall analysis
  console.log(`\n\n📈 Performance Summary`);
  console.log('======================');
  
  const allScenarios = Object.entries(results).filter(([name]) => name !== 'health');
  let worstP95 = 0;
  let bestScenario = '';
  let worstScenario = '';
  
  allScenarios.forEach(([name, data]) => {
    if (data.stats && data.stats.p95 > worstP95) {
      worstP95 = data.stats.p95;
      worstScenario = name;
    }
    if (!bestScenario || (data.stats && data.stats.p95 < results[bestScenario]?.stats?.p95)) {
      bestScenario = name;
    }
  });
  
  console.log(`🏆 Best performance: ${bestScenario} (${results[bestScenario]?.stats?.p95}ms p95)`);
  console.log(`⚠️  Worst performance: ${worstScenario} (${worstP95}ms p95)`);
  
  const targetMet = worstP95 <= 1200;
  console.log(`🎯 P95 Target (≤1200ms): ${targetMet ? '✅' : '❌'} ${worstP95}ms`);
  
  // Recommendations
  console.log(`\n💡 Performance Recommendations:`);
  if (worstP95 > 1200) {
    console.log(`   - Optimize ${worstScenario} scenario (${worstP95}ms p95)`);
    if (worstScenario.includes('Tool')) {
      console.log(`   - Consider tool call caching/batching`);
    }
  }
  if (results.health?.stats?.p95 > 100) {
    console.log(`   - Health endpoint slow (${results.health.stats.p95}ms p95)`);
  }
  console.log(`   - Consider OpenAI response caching for repeated queries`);
  console.log(`   - Implement request connection pooling`);
  console.log(`   - Add response compression`);
}

main().catch(console.error);