#!/usr/bin/env python3
"""
Voice v2 System - 2 Minute Evaluation Test
==========================================

Tests Voice v2 ack-flow system for 2 minutes, logging:
- TTS latency and caching
- Brain API performance  
- Error rates
- User experience simulation

Results logged to NDJSON for analysis.
"""

import asyncio
import json
import time
import random
from datetime import datetime, timezone
from pathlib import Path
import aiohttp
import sys

# Test configuration
TEST_DURATION_SECONDS = 120  # 2 minutes
BASE_URL = "http://localhost:8000"
LOG_FILE = "voice_v2_test_results.ndjson"

# Test scenarios to rotate through
SCENARIOS = [
    {
        "name": "email_check",
        "intent": "mail.check_unread", 
        "ack_phrase": "Let me check your inbox for a second...",
        "brain_endpoint": "/api/brain/mail-count",
        "expected_result_pattern": "emails"
    },
    {
        "name": "calendar_today",
        "intent": "calendar.today",
        "ack_phrase": "Let me pull up your schedule for today...",
        "brain_endpoint": None,  # No real API yet
        "expected_result_pattern": "calendar"
    },
    {
        "name": "weather_check", 
        "intent": "weather.current",
        "ack_phrase": "Let me check the weather in Stockholm...",
        "brain_endpoint": None,  # No real API yet
        "expected_result_pattern": "weather"
    },
    {
        "name": "general_ack",
        "intent": "default",
        "ack_phrase": "One moment...",
        "brain_endpoint": None,
        "expected_result_pattern": "mock"
    }
]

class VoiceV2Tester:
    def __init__(self):
        self.session = None
        self.test_id = f"voice_v2_eval_{int(time.time())}"
        self.start_time = time.time()
        self.commands_run = 0
        self.successful_commands = 0
        self.errors = []
        
        # Performance metrics
        self.tts_latencies = []
        self.brain_latencies = []
        self.total_command_times = []
        
        self.log_file = Path(LOG_FILE)
        
        print(f"🚀 Starting Voice v2 2-minute evaluation test")
        print(f"📝 Logging to: {self.log_file}")
        print(f"⏱️ Test duration: {TEST_DURATION_SECONDS}s")
        
    def log_event(self, event_type: str, data: dict):
        """Log structured event to NDJSON file"""
        
        log_entry = {
            "test_id": self.test_id,
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_s": round(time.time() - self.start_time, 3),
            **data
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
            
        # Also print key events
        if event_type in ['test_start', 'test_complete', 'command_complete', 'error']:
            print(f"📊 {event_type}: {json.dumps(data, indent=2)}")
    
    async def test_tts_endpoint(self, text: str, voice: str = "nova", rate: float = 1.0):
        """Test TTS endpoint and measure performance"""
        
        start = time.time()
        
        try:
            payload = {"text": text, "voice": voice, "rate": rate}
            
            async with self.session.post(f"{BASE_URL}/api/tts/", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    latency = (time.time() - start) * 1000
                    
                    self.log_event("tts_test", {
                        "text": text[:50] + "..." if len(text) > 50 else text,
                        "voice": voice,
                        "rate": rate,
                        "latency_ms": latency,
                        "cached": result.get("cached", False),
                        "url": result.get("url", ""),
                        "status": "success"
                    })
                    
                    self.tts_latencies.append(latency)
                    return result, latency
                    
                else:
                    error_msg = f"TTS failed: {resp.status}"
                    self.log_event("error", {
                        "error_type": "tts_failure",
                        "status_code": resp.status,
                        "message": error_msg
                    })
                    self.errors.append(f"TTS: {error_msg}")
                    return None, None
                    
        except Exception as e:
            self.log_event("error", {
                "error_type": "tts_exception",
                "message": str(e),
                "text": text
            })
            self.errors.append(f"TTS Exception: {e}")
            return None, None
    
    async def test_brain_endpoint(self, endpoint: str):
        """Test brain API endpoint and measure performance"""
        
        start = time.time()
        
        try:
            async with self.session.get(f"{BASE_URL}{endpoint}") as resp:
                result = await resp.json()
                latency = (time.time() - start) * 1000
                
                self.log_event("brain_test", {
                    "endpoint": endpoint,
                    "latency_ms": latency,
                    "status_code": resp.status,
                    "response": result,
                    "status": "success"
                })
                
                self.brain_latencies.append(latency)
                return result, latency
                
        except Exception as e:
            self.log_event("error", {
                "error_type": "brain_exception",
                "endpoint": endpoint,
                "message": str(e)
            })
            self.errors.append(f"Brain API ({endpoint}): {e}")
            return None, None
    
    async def simulate_voice_command(self, scenario: dict):
        """Simulate complete voice command flow"""
        
        command_start = time.time()
        self.commands_run += 1
        
        self.log_event("command_start", {
            "command_num": self.commands_run,
            "scenario": scenario["name"],
            "intent": scenario["intent"]
        })
        
        success = True
        
        # Step 1: Test acknowledgment phrase via TTS
        ack_result, ack_latency = await self.test_tts_endpoint(scenario["ack_phrase"])
        if not ack_result:
            success = False
        
        # Step 2: Test brain endpoint if available
        brain_result, brain_latency = None, None
        if scenario["brain_endpoint"]:
            brain_result, brain_latency = await self.test_brain_endpoint(scenario["brain_endpoint"])
            if not brain_result:
                success = False
        
        # Step 3: Generate result phrase and test TTS
        if brain_result and "count" in brain_result:
            count = brain_result["count"] 
            result_text = f"You have {count} new emails." if count > 0 else "You have no new emails."
        else:
            result_text = f"Mock result for {scenario['name']} command completed successfully."
        
        result_tts, result_latency = await self.test_tts_endpoint(result_text)
        if not result_tts:
            success = False
            
        # Calculate total command time
        total_time = (time.time() - command_start) * 1000
        self.total_command_times.append(total_time)
        
        if success:
            self.successful_commands += 1
            
        self.log_event("command_complete", {
            "command_num": self.commands_run,
            "scenario": scenario["name"],
            "success": success,
            "total_time_ms": total_time,
            "ack_latency_ms": ack_latency,
            "brain_latency_ms": brain_latency,
            "result_latency_ms": result_latency,
            "result_text": result_text
        })
        
        return success
    
    async def run_test(self):
        """Run 2-minute evaluation test"""
        
        self.log_event("test_start", {
            "test_duration_s": TEST_DURATION_SECONDS,
            "scenarios": [s["name"] for s in SCENARIOS],
            "base_url": BASE_URL
        })
        
        # Create HTTP session
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            scenario_index = 0
            
            while (time.time() - self.start_time) < TEST_DURATION_SECONDS:
                # Pick scenario (round-robin)
                scenario = SCENARIOS[scenario_index % len(SCENARIOS)]
                scenario_index += 1
                
                # Run command simulation
                await self.simulate_voice_command(scenario)
                
                # Wait between commands (simulate realistic usage)
                pause = random.uniform(3, 8)  # 3-8 seconds between commands
                remaining_time = TEST_DURATION_SECONDS - (time.time() - self.start_time)
                
                if remaining_time <= pause:
                    break
                    
                await asyncio.sleep(pause)
        
        # Test complete - calculate metrics
        self.log_final_results()
    
    def log_final_results(self):
        """Log final test results and analysis"""
        
        elapsed = time.time() - self.start_time
        success_rate = (self.successful_commands / self.commands_run * 100) if self.commands_run > 0 else 0
        
        # Calculate performance statistics
        avg_tts_latency = sum(self.tts_latencies) / len(self.tts_latencies) if self.tts_latencies else 0
        max_tts_latency = max(self.tts_latencies) if self.tts_latencies else 0
        
        avg_brain_latency = sum(self.brain_latencies) / len(self.brain_latencies) if self.brain_latencies else 0
        
        avg_total_time = sum(self.total_command_times) / len(self.total_command_times) if self.total_command_times else 0
        
        final_results = {
            "test_duration_s": round(elapsed, 2),
            "commands_run": self.commands_run,
            "successful_commands": self.successful_commands,
            "success_rate_pct": round(success_rate, 1),
            "errors": self.errors,
            "performance": {
                "avg_tts_latency_ms": round(avg_tts_latency, 2),
                "max_tts_latency_ms": round(max_tts_latency, 2),
                "avg_brain_latency_ms": round(avg_brain_latency, 2),
                "avg_total_command_ms": round(avg_total_time, 2),
                "commands_per_minute": round((self.commands_run / elapsed) * 60, 1)
            },
            "verdict": "PASS" if success_rate >= 90 and len(self.errors) == 0 else "NEEDS_IMPROVEMENT"
        }
        
        self.log_event("test_complete", final_results)
        
        # Print summary
        print(f"\n🏁 Voice v2 2-Minute Test Complete!")
        print(f"⏱️ Duration: {elapsed:.1f}s")
        print(f"📊 Commands: {self.successful_commands}/{self.commands_run} ({success_rate:.1f}% success)")
        print(f"🚀 Performance:")
        print(f"   - Avg TTS latency: {avg_tts_latency:.1f}ms")
        print(f"   - Avg brain latency: {avg_brain_latency:.1f}ms") 
        print(f"   - Avg total command time: {avg_total_time:.1f}ms")
        print(f"🎯 Verdict: {final_results['verdict']}")
        
        if self.errors:
            print(f"❌ Errors found: {len(self.errors)}")
            for error in self.errors[:3]:  # Show first 3
                print(f"   - {error}")

async def main():
    """Run Voice v2 evaluation test"""
    
    tester = VoiceV2Tester()
    
    try:
        await tester.run_test()
    except KeyboardInterrupt:
        print(f"\n⏹️ Test interrupted by user")
        tester.log_event("test_interrupted", {"reason": "keyboard_interrupt"})
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        tester.log_event("test_failed", {"exception": str(e)})

if __name__ == "__main__":
    print("🎙️ Voice v2 System - 2 Minute Evaluation Test")
    print("=" * 50)
    
    # Check if server is running
    try:
        import requests
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        if resp.status_code != 200:
            print(f"❌ Backend server not responding correctly")
            sys.exit(1)
    except:
        print(f"❌ Cannot connect to backend at {BASE_URL}")
        print("   Make sure the backend is running on port 8000")
        sys.exit(1)
    
    print("✅ Backend connection verified")
    print(f"⏳ Starting 2-minute test in 3 seconds...")
    time.sleep(3)
    
    asyncio.run(main())