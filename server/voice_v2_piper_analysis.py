#!/usr/bin/env python3
"""
Voice v2 Piper-Sim Analysis - Clean Production-Ready Report
===========================================================

Analyzes ONLY the latest Piper-simulation test run.
Separates cached vs uncached TTS performance.
Provides per-intent SLO analysis.
"""

import json
from pathlib import Path
from datetime import datetime
import statistics

def analyze_piper_test(log_file: str = "voice_v2_test_results.ndjson"):
    """Analyze latest Piper test run with production metrics"""
    
    log_path = Path(log_file)
    if not log_path.exists():
        print(f"❌ Log file not found: {log_file}")
        return
    
    # Parse all events
    events = []
    with open(log_path, 'r') as f:
        for line in f:
            try:
                events.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    
    if not events:
        print("❌ No events found in log file")
        return
    
    # Find the LATEST test ID (Piper-sim run)
    test_ids = set(e["test_id"] for e in events)
    latest_test_id = max(test_ids)  # Assumes chronological order
    
    # Filter to latest test only
    piper_events = [e for e in events if e["test_id"] == latest_test_id]
    
    print("🎙️ Voice v2 PIPER-SIM Analysis Report")
    print("=" * 50)
    print(f"📅 Test ID: {latest_test_id}")
    
    # Find test session info
    test_start = next((e for e in piper_events if e["event"] == "test_start"), None)
    test_complete = next((e for e in piper_events if e["event"] == "test_complete"), None)
    
    if test_start:
        print(f"⏱️ Started: {test_start['timestamp']}")
        print(f"🎯 Scenarios: {', '.join(test_start['scenarios'])}")
    
    if test_complete:
        print(f"✅ Duration: {test_complete['test_duration_s']}s")
        print(f"📊 Commands: {test_complete['successful_commands']}/{test_complete['commands_run']}")
        print(f"🎯 Success Rate: {test_complete['success_rate_pct']}%")
    
    print(f"\n🚀 PIPER TTS Performance (Production Analysis)")
    print("-" * 45)
    
    # Analyze TTS performance - separate cached vs uncached
    tts_events = [e for e in piper_events if e["event"] == "tts_test"]
    if tts_events:
        # Separate cached vs uncached
        cached_tts = [e for e in tts_events if e.get("cached", False)]
        uncached_tts = [e for e in tts_events if not e.get("cached", False)]
        
        print(f"📈 TTS Request Summary:")
        print(f"   - Total requests: {len(tts_events)}")
        print(f"   - Cached hits: {len(cached_tts)} ({len(cached_tts)/len(tts_events):.1%})")
        print(f"   - Uncached (Piper): {len(uncached_tts)} ({len(uncached_tts)/len(tts_events):.1%})")
        
        if cached_tts:
            cached_latencies = [e["latency_ms"] for e in cached_tts]
            print(f"\n⚡ CACHED Performance (Disk Cache):")
            print(f"   - Count: {len(cached_latencies)}")
            print(f"   - P50: {statistics.median(cached_latencies):.1f}ms")
            print(f"   - P95: {sorted(cached_latencies)[int(len(cached_latencies) * 0.95)]:.1f}ms")
            print(f"   - Max: {max(cached_latencies):.1f}ms")
            
            # SLO check for cached (target: p95 ≤ 120ms)
            cached_p95 = sorted(cached_latencies)[int(len(cached_latencies) * 0.95)]
            cached_slo = "✅ PASS" if cached_p95 <= 120 else "❌ FAIL"
            print(f"   - SLO Check (p95 ≤ 120ms): {cached_slo}")
        
        if uncached_tts:
            uncached_latencies = [e["latency_ms"] for e in uncached_tts]
            print(f"\n🔥 UNCACHED Performance (Piper TTS):")
            print(f"   - Count: {len(uncached_latencies)}")
            print(f"   - P50: {statistics.median(uncached_latencies):.1f}ms")
            print(f"   - P95: {sorted(uncached_latencies)[int(len(uncached_latencies) * 0.95)]:.1f}ms")
            print(f"   - Max: {max(uncached_latencies):.1f}ms")
            print(f"   - Min: {min(uncached_latencies):.1f}ms")
            
            # SLO check for uncached short phrases (≤40 chars, target: p95 ≤ 800ms)
            short_phrases = [e for e in uncached_tts if len(e.get("text", "")) <= 40]
            if short_phrases:
                short_latencies = [e["latency_ms"] for e in short_phrases]
                short_p95 = sorted(short_latencies)[int(len(short_latencies) * 0.95)]
                short_slo = "✅ PASS" if short_p95 <= 800 else "❌ FAIL"
                print(f"   - Short Phrases (≤40 chars): {len(short_phrases)}")
                print(f"   - Short P95: {short_p95:.1f}ms")
                print(f"   - SLO Check (p95 ≤ 800ms): {short_slo}")
    
    # Per-intent analysis
    print(f"\n📊 Per-Intent Performance Analysis")
    print("-" * 35)
    
    command_events = [e for e in piper_events if e["event"] == "command_complete"]
    if command_events:
        # Group by scenario
        by_intent = {}
        for cmd in command_events:
            intent = cmd["scenario"]
            if intent not in by_intent:
                by_intent[intent] = []
            by_intent[intent].append(cmd)
        
        for intent, commands in by_intent.items():
            total_times = [c["total_time_ms"] for c in commands]
            ack_times = [c["ack_latency_ms"] for c in commands if c["ack_latency_ms"]]
            brain_times = [c["brain_latency_ms"] for c in commands if c["brain_latency_ms"]]
            
            print(f"\n🎯 {intent.upper()}:")
            print(f"   - Commands: {len(commands)}")
            print(f"   - Total Time P50: {statistics.median(total_times):.1f}ms")
            print(f"   - Total Time P95: {sorted(total_times)[int(len(total_times) * 0.95)]:.1f}ms")
            
            if ack_times:
                ack_p95 = sorted(ack_times)[int(len(ack_times) * 0.95)]
                print(f"   - Ack P95: {ack_p95:.1f}ms")
            
            if brain_times:
                brain_p95 = sorted(brain_times)[int(len(brain_times) * 0.95)]
                brain_slo = "✅ PASS" if brain_p95 <= 300 else "❌ FAIL" 
                print(f"   - Brain P95: {brain_p95:.1f}ms (SLO ≤300ms: {brain_slo})")
    
    # Error analysis
    error_events = [e for e in piper_events if e["event"] == "error"]
    print(f"\n❌ Error Analysis:")
    if error_events:
        print(f"   - Total errors: {len(error_events)}")
        for error in error_events:
            print(f"   - {error.get('error_type', 'unknown')}: {error.get('message', 'N/A')}")
    else:
        print(f"   ✅ Zero errors - excellent stability")
    
    # Production readiness assessment
    print(f"\n🎯 PRODUCTION READINESS GATE")
    print("-" * 30)
    
    if test_complete:
        success_rate = test_complete.get("success_rate_pct", 0)
        
        # Calculate key metrics
        if cached_tts:
            cached_latencies = [e["latency_ms"] for e in cached_tts]
            cached_p95 = sorted(cached_latencies)[int(len(cached_latencies) * 0.95)]
            ack_gate = "✅ PASS" if cached_p95 <= 120 else "❌ FAIL"
        else:
            ack_gate = "⚠️ NO DATA"
        
        if uncached_tts:
            short_uncached = [e for e in uncached_tts if len(e.get("text", "")) <= 40]
            if short_uncached:
                short_latencies = [e["latency_ms"] for e in short_uncached]
                short_p95 = sorted(short_latencies)[int(len(short_latencies) * 0.95)]
                tts_gate = "✅ PASS" if short_p95 <= 800 else "❌ FAIL"
            else:
                tts_gate = "⚠️ NO SHORT PHRASES"
        else:
            tts_gate = "❌ NO UNCACHED DATA"
        
        stability_gate = "✅ PASS" if success_rate == 100 and len(error_events) == 0 else "❌ FAIL"
        
        print(f"Ack TTFA (cached p95 ≤ 120ms): {ack_gate}")
        print(f"TTS Short Phrases (p95 ≤ 800ms): {tts_gate}")
        print(f"Stability (100% success, 0 errors): {stability_gate}")
        
        # Overall verdict
        if all("✅" in gate for gate in [ack_gate, tts_gate, stability_gate]):
            overall = "🟢 PRODUCTION READY"
        elif "❌" in tts_gate or "❌" in stability_gate:
            overall = "🔴 NEEDS WORK"
        else:
            overall = "🟡 NEEDS TUNING"
        
        print(f"\n🏁 OVERALL VERDICT: {overall}")
    
    # Next steps
    print(f"\n💡 Recommended Next Steps")
    print("-" * 25)
    print("1. Add TTFB measurement for GET /audio/* (client-side)")
    print("2. Add provider:'piper-sim' tag to TTS events")  
    print("3. Implement crossfade gap measurement")
    print("4. Replace calendar/weather mocks with real adapters")
    print("5. Test burst load: 5 parallel flows for 30s")
    print("6. Add ack phrase rotation (3-5 variants per intent)")
    
    return piper_events

if __name__ == "__main__":
    analyze_piper_test()