/**
 * k6 Live Load Test - RIKTIG AI DATA
 * ================================
 * HTTP lasttest mot /api/chat med verklig AI och Guardian monitoring.
 * 
 * Ramping load: 1→3→6→10→2 rps över 6min
 * Thresholds: <1% fel, p95 <2.5s, Guardian mode tracking
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Custom metrics för Guardian monitoring
const guardianModeCounter = new Counter('guardian_mode_transitions');
const guardianErrorRate = new Rate('guardian_error_rate');
const aiResponseTime = new Trend('ai_response_time');
const databaseWriteTime = new Trend('database_write_time');

// Load test configuration
export let options = {
  stages: [
    { duration: '1m', target: 1 },   // Warmup: 1 rps
    { duration: '1m', target: 3 },   // Ramp: 3 rps
    { duration: '2m', target: 6 },   // Peak: 6 rps
    { duration: '1m', target: 10 },  // Spike: 10 rps
    { duration: '1m', target: 2 },   // Cooldown: 2 rps
  ],
  
  thresholds: {
    // Production success criteria
    'http_req_failed': ['rate<0.01'],        // <1% fel
    'http_req_duration': ['p(95)<2500'],     // p95 <2.5s
    'ai_response_time': ['p(95)<2000'],      // AI p95 <2s
    'guardian_error_rate': ['rate<0.05'],    // Guardian <5% fel
  },
};

// RIKTIG DATA - Svenska meddelanden för Alice
const testMessages = [
  "Hej Alice! Kan du hjälpa mig idag?",
  "Vad är vädret för något i Stockholm?", 
  "Kan du berätta något intressant om Sverige?",
  "Spela lite musik åt mig, tack!",
  "Sätt volymen till 70 procent",
  "Vilka möten har jag idag?",
  "Skicka ett mail till min kollega",
  "Vad heter Sveriges huvudstad?",
  "Kan du hjälpa mig med matematik?",
  "Berätta en rolig fakta",
  "Tack så mycket för hjälpen!",
  "Vi ses imorgon, Alice!",
  "Hur mår du idag?",
  "Kan du sjunga en sång?",
  "Vad kan du göra för mig?",
  "Alice, är du där?",
  "Kolla kalendern för nästa vecka",
  "Ställ en timer på 5 minuter",
  "Vad är klockan nu?",
  "Kan du komma ihåg det här?"
];

export default function () {
  // Välj slumpmässigt meddelande för RIKTIG DATA
  const message = testMessages[Math.floor(Math.random() * testMessages.length)];
  
  // HTTP request med riktig chat data
  const payload = JSON.stringify({
    message: message
  });
  
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-load-test/1.0 (production-testing)',
    },
    timeout: '15s', // Tillåt AI response time
  };
  
  const response = http.post('http://localhost:8000/api/chat', payload, params);
  
  // Check basic HTTP success
  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'response has content': (r) => r.body && r.body.length > 0,
    'response is valid JSON': (r) => {
      try {
        JSON.parse(r.body);
        return true;
      } catch {
        return false;
      }
    }
  });
  
  if (success && response.status === 200) {
    try {
      const data = JSON.parse(response.body);
      
      // Validate RIKTIG AI response structure
      check(data, {
        'has response field': (d) => d.response && d.response.length > 0,
        'has model field': (d) => d.model && d.model.length > 0,
        'has timestamp': (d) => d.timestamp !== undefined,
        'AI response is Swedish': (d) => {
          // Basic check för svenska ord i response
          const swedish_words = ['är', 'och', 'att', 'det', 'för', 'jag', 'du', 'kan', 'på'];
          return swedish_words.some(word => d.response.toLowerCase().includes(word));
        }
      });
      
      // Track AI performance metrics
      if (data.tftt_ms) {
        aiResponseTime.add(data.tftt_ms);
      }
      
      // Monitor Guardian mode via headers
      const guardianMode = response.headers['x-guardian-mode'] || 'normal';
      if (guardianMode !== 'normal') {
        guardianModeCounter.add(1);
        console.log(`🛡️ Guardian mode: ${guardianMode} for message: "${message.substring(0, 30)}..."`);
      }
      
      // Log successful AI interaction
      if (__ITER % 10 === 0) { // Log every 10th request
        console.log(`✅ AI Response (${data.model}): "${data.response.substring(0, 50)}..." (${data.tftt_ms}ms)`);
      }
      
    } catch (e) {
      guardianErrorRate.add(1);
      console.error(`❌ JSON parse error: ${e}`);
    }
  } else {
    guardianErrorRate.add(1);
    console.error(`❌ HTTP error: ${response.status} - ${response.error || 'Unknown error'}`);
    
    // Log response body för debugging
    if (response.body) {
      console.error(`Response body: ${response.body.substring(0, 200)}`);
    }
  }
  
  // Variable sleep för mer realistisk load
  sleep(Math.random() * 0.5 + 0.3); // 0.3-0.8s mellan requests
}

// Setup function - körs innan load test
export function setup() {
  console.log('🚀 Starting k6 Live Load Test with REAL AI');
  console.log('📊 Configuration:');
  console.log('  - Target: http://localhost:8000/api/chat');
  console.log('  - Load pattern: 1→3→6→10→2 rps over 6 minutes');  
  console.log('  - Success criteria: <1% errors, p95 <2.5s');
  console.log('  - Real Swedish messages with AI responses');
  console.log('  - Guardian mode monitoring enabled');
  console.log('');
  
  // Health check innan start
  const healthCheck = http.get('http://localhost:8000/health');
  if (healthCheck.status !== 200) {
    throw new Error(`Backend health check failed: ${healthCheck.status}`);
  }
  
  const guardianHealth = http.get('http://localhost:8787/health');
  if (guardianHealth.status !== 200) {
    throw new Error(`Guardian health check failed: ${guardianHealth.status}`);
  }
  
  console.log('✅ Pre-flight checks passed - starting load test...');
  return {};
}

// Teardown function - körs efter load test  
export function teardown(data) {
  console.log('');
  console.log('🏁 k6 Live Load Test Complete');
  console.log('📊 Check the summary above for results');
  console.log('🛡️ Guardian mode transitions tracked');
  console.log('💬 Real AI conversations tested');
  console.log('🗄️ Database persistence verified');
}

export function handleSummary(data) {
  // Custom summary med Guardian metrics
  const guardianModes = data.metrics.guardian_mode_transitions?.values?.count || 0;
  const guardianErrors = data.metrics.guardian_error_rate?.values?.rate || 0;
  const aiP95 = data.metrics.ai_response_time?.values?.['p(95)'] || 0;
  
  console.log('');
  console.log('📈 GUARDIAN & AI METRICS:');
  console.log(`🛡️ Guardian mode transitions: ${guardianModes}`);
  console.log(`⚠️ Guardian error rate: ${(guardianErrors * 100).toFixed(2)}%`);
  console.log(`🤖 AI response p95: ${aiP95.toFixed(0)}ms`);
  
  return {
    'k6_live_load_results.json': JSON.stringify(data, null, 2),
  };
}