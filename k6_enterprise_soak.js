#!/usr/bin/env k6 run
/**
 * Alice Enterprise 14-Day Soak Test
 * ==================================
 * 
 * Kontinuerlig belastning över 14 dagar för production readiness validation.
 * Mäter p50/p95/p99/p99.9 latens, error rates, och systemstabilitet.
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics för enterprise validation
const errorRate = new Rate('alice_error_rate');
const responseTime = new Trend('alice_response_time', true);
const cacheHits = new Counter('alice_cache_hits');
const cacheMisses = new Counter('alice_cache_misses');
const guardianModeChanges = new Counter('alice_guardian_mode_changes');

// Enterprise test configuration
export const options = {
    scenarios: {
        // Kontinuerlig baseline load - 14 dagar
        continuous_load: {
            executor: 'constant-vus',
            vus: 5,                    // 5 virtual users
            duration: '14d',           // 14 dagar kontinuerligt
            gracefulRampDown: '30s',   // Graceful shutdown
        },
        
        // Dagliga spike tests för resilience
        daily_spikes: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                // Varje dag: spike till 15 VUs i 10min, sedan tillbaka
                { duration: '23h50m', target: 0 },  // Vila 23h50m
                { duration: '5m', target: 15 },      // Spike upp
                { duration: '5m', target: 15 },      // Håll spike
                { duration: '5m', target: 0 },       // Spike ner
            ],
            gracefulRampDown: '30s',
        },
        
        // Cold start tests - 4x per dag
        cold_start_validation: {
            executor: 'per-vu-iterations',
            vus: 1,
            iterations: 56,          // 4 per dag * 14 dagar
            maxDuration: '14d',
        }
    },
    
    // Enterprise success thresholds
    thresholds: {
        'alice_error_rate': ['rate<0.01'],        // <1% fel över 14 dagar
        'alice_response_time': [
            'p(50)<1500',      // p50 under 1.5s
            'p(95)<2000',      // p95 under 2s  
            'p(99)<3000',      // p99 under 3s (enterprise requirement)
            'p(99.9)<5000',    // p99.9 under 5s
        ],
        'http_req_duration': ['p(95)<2500'],      // Backup metric
        'http_req_failed': ['rate<0.005'],        // <0.5% HTTP failures
    }
};

// Svenska test queries för realism
const swedishQueries = [
    "Vad är klockan nu?",
    "Hur är vädret idag?", 
    "Berätta om Sverige",
    "Vad kan du hjälpa mig med?",
    "Förklara Guardian systemet",
    "Hur fungerar Alice AI?",
    "Vad är dagens datum?",
    "Hjälp mig planera dagen",
    "Sammanfatta senaste nyheterna",
    "Förklara maschinlärning enkelt",
];

let currentGuardianMode = 'unknown';
let testStartTime = new Date();

export default function () {
    const testType = __ITER < 1000 ? 'continuous' : 
                    __ITER < 1100 ? 'spike' : 'cold_start';
    
    // Välj query baserat på test type
    let query;
    if (testType === 'cold_start') {
        // Cold start: använd nya queries för cache misses
        query = `Cold start test ${__ITER}: ${swedishQueries[__ITER % swedishQueries.length]}`;
        cacheMisses.add(1);
    } else {
        // Normal: blanda återanvända och nya queries (realistisk cache pattern)
        const useCache = Math.random() < 0.25; // 25% cache hit rate target
        if (useCache && __ITER > 50) {
            // Återanvänd tidigare query för cache hit
            query = swedishQueries[Math.floor(Math.random() * 3)]; 
            cacheHits.add(1);
        } else {
            query = swedishQueries[__ITER % swedishQueries.length];
            cacheMisses.add(1);
        }
    }
    
    // Preparera request
    const payload = JSON.stringify({
        text: query,
        session_id: `soak_test_${testType}_${__VU}`,
        timestamp: new Date().toISOString()
    });
    
    const params = {
        headers: {
            'Content-Type': 'application/json',
            'X-Test-Type': testType,
            'X-Test-Day': Math.floor((new Date() - testStartTime) / (24 * 60 * 60 * 1000)) + 1,
        },
        timeout: '30s',  // Enterprise timeout
    };
    
    // Execute request med timing
    const startTime = new Date();
    const response = http.post('http://localhost:8000/api/chat', payload, params);
    const endTime = new Date();
    const duration = endTime - startTime;
    
    // Record metrics
    responseTime.add(duration);
    
    // Validate response
    const success = check(response, {
        'status is 200': (r) => r.status === 200,
        'response time OK': (r) => r.timings.duration < 5000,
        'has response text': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.response && body.response.length > 0;
            } catch {
                return false;
            }
        },
        'not error response': (r) => !r.body.includes('error'),
        'guardian mode present': (r) => r.headers['X-Guardian-Mode'] !== undefined,
    });
    
    errorRate.add(!success);
    
    // Track Guardian mode changes
    const guardianMode = response.headers['X-Guardian-Mode'] || 'unknown';
    if (guardianMode !== currentGuardianMode) {
        console.log(`Guardian mode change: ${currentGuardianMode} → ${guardianMode} at ${new Date().toISOString()}`);
        guardianModeChanges.add(1);
        currentGuardianMode = guardianMode;
    }
    
    // Enterprise logging för detailed analysis
    if (!success || duration > 3000 || response.status !== 200) {
        console.log(`[ENTERPRISE-ALERT] ${testType} failure: ${response.status}, ${duration}ms, mode=${guardianMode}, query="${query.substr(0, 30)}..."`);
    }
    
    // Variable sleep för realism (enterprise users aren't robots)
    const sleepTime = testType === 'spike' ? 0.5 : 
                     testType === 'cold_start' ? 300 : // 5min mellan cold starts
                     2 + Math.random() * 3; // 2-5s för continuous
    
    sleep(sleepTime);
}

// Soak test lifecycle hooks
export function setup() {
    console.log('🚀 Starting Alice Enterprise 14-Day Soak Test');
    console.log(`📅 Start time: ${new Date().toISOString()}`);
    console.log('📊 Monitoring: p50/p95/p99/p99.9 latencies, <1% error rate, Guardian stability');
    
    // Verify system health before starting
    const healthCheck = http.get('http://localhost:8000/health');
    if (healthCheck.status !== 200) {
        throw new Error(`System unhealthy before soak test: ${healthCheck.status}`);
    }
    
    const guardianCheck = http.get('http://localhost:8787/health');
    if (guardianCheck.status !== 200) {
        throw new Error(`Guardian unhealthy before soak test: ${guardianCheck.status}`);
    }
    
    console.log('✅ Pre-flight checks passed - enterprise soak test starting');
    return { startTime: new Date().toISOString() };
}

export function teardown(data) {
    const endTime = new Date();
    const startTime = new Date(data.startTime);
    const totalDuration = (endTime - startTime) / (1000 * 60 * 60 * 24); // Days
    
    console.log('🏁 Alice Enterprise 14-Day Soak Test Complete');
    console.log(`📅 End time: ${endTime.toISOString()}`);
    console.log(`⏱️  Total duration: ${totalDuration.toFixed(2)} days`);
    console.log('📊 Check metrics for enterprise production readiness validation');
}

// Export för external monitoring
export { errorRate, responseTime, cacheHits, cacheMisses, guardianModeChanges };