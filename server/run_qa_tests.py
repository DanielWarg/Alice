#!/usr/bin/env python3
"""
Quick QA Test Runner for Alice Systems
Runs all individual test suites and provides summary
"""

import subprocess
import sys
import time
from pathlib import Path

def run_test(test_file, description):
    """Run a single test file and return results"""
    print(f"\n🧪 Running {description}...")
    print("=" * 60)
    
    start_time = time.time()
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout per test
        )
        
        execution_time = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {description} PASSED ({execution_time:.1f}s)")
            return True, execution_time, result.stdout
        else:
            print(f"❌ {description} FAILED ({execution_time:.1f}s)")
            print("STDERR:", result.stderr[-500:] if result.stderr else "No error output")
            return False, execution_time, result.stdout
            
    except subprocess.TimeoutExpired:
        print(f"⏱️  {description} TIMEOUT (>120s)")
        return False, 120, "Test timed out"
    except Exception as e:
        print(f"💥 {description} ERROR: {e}")
        return False, 0, str(e)

def main():
    """Run all QA tests"""
    print("🚀 ALICE QA TEST RUNNER")
    print("=" * 80)
    print("Running comprehensive QA tests for all Alice systems...")
    
    # Define tests to run
    tests = [
        ("test_voice_system.py", "Voice System Integration"),
        ("test_gmail_integration.py", "Gmail Integration"), 
        ("test_command_vs_chat.py", "Command vs Chat Discrimination"),
        ("stress_test_nlu.py", "NLU System Performance"),
        ("stress_test_rag.py", "Memory System Performance"),
    ]
    
    results = []
    total_time = 0
    
    for test_file, description in tests:
        test_path = Path(__file__).parent / test_file
        
        if not test_path.exists():
            print(f"⚠️  Skipping {description} - test file not found: {test_file}")
            continue
            
        success, exec_time, output = run_test(str(test_path), description)
        results.append((description, success, exec_time, output))
        total_time += exec_time
    
    # Summary
    print("\n" + "=" * 80)
    print("🎯 QA TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, success, _, _ in results if success)
    total = len(results)
    success_rate = passed / total if total > 0 else 0
    
    print(f"📊 Overall Results: {passed}/{total} tests passed ({success_rate:.1%})")
    print(f"⏱️  Total Time: {total_time:.1f} seconds")
    print()
    
    for description, success, exec_time, _ in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {description} ({exec_time:.1f}s)")
    
    print("\n" + "=" * 80)
    
    if success_rate >= 0.9:
        print("🎉 EXCELLENT! All systems performing well.")
        verdict = "PRODUCTION READY"
    elif success_rate >= 0.8:
        print("✅ GOOD! Most systems working, minor issues to address.")
        verdict = "MOSTLY READY"
    else:
        print("⚠️  ISSUES DETECTED! Several systems need attention.")
        verdict = "NEEDS WORK"
    
    print(f"🏆 VERDICT: {verdict}")
    print("=" * 80)
    
    # Return appropriate exit code
    sys.exit(0 if success_rate >= 0.8 else 1)

if __name__ == "__main__":
    main()