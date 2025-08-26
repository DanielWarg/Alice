#!/usr/bin/env python3
"""
🧪 WebRTC Gateway Test Runner
Comprehensive test suite runner with different test levels
"""
import subprocess
import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, List

class TestRunner:
    """Orchestrate WebRTC Gateway test execution"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.results = {}
        
    def check_services_running(self) -> bool:
        """Check if required services are running"""
        import requests
        
        try:
            # Check Voice Gateway
            response = requests.get("http://localhost:8001/health", timeout=3)
            if response.status_code != 200:
                return False
                
            # Check Redis (via gateway status)
            response = requests.get("http://localhost:8001/api/webrtc/status", timeout=3)
            if response.status_code != 200:
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Service check failed: {e}")
            return False
    
    def run_unit_tests(self) -> Dict:
        """Run fast unit tests"""
        print("\\n🔬 Running Unit Tests...")
        
        cmd = [
            "python", "-m", "pytest",
            "tests/test_audio_processor.py",
            "-v", "--tb=short",
            "-m", "not integration and not performance"
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.base_path, capture_output=True, text=True)
        duration = time.time() - start_time
        
        return {
            "name": "Unit Tests",
            "duration": duration,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "passed": result.returncode == 0
        }
    
    def run_integration_tests(self) -> Dict:
        """Run integration tests (requires running services)"""
        print("\\n🔗 Running Integration Tests...")
        
        if not self.check_services_running():
            return {
                "name": "Integration Tests",
                "duration": 0,
                "returncode": -1,
                "stdout": "",
                "stderr": "Services not running - skipping integration tests",
                "passed": False,
                "skipped": True
            }
        
        cmd = [
            "python", "-m", "pytest", 
            "tests/test_webrtc_manager.py",
            "-v", "--tb=short",
            "-m", "integration"
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.base_path, capture_output=True, text=True)
        duration = time.time() - start_time
        
        return {
            "name": "Integration Tests",
            "duration": duration,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "passed": result.returncode == 0
        }
    
    def run_performance_tests(self) -> Dict:
        """Run performance/SLO validation tests"""
        print("\\n⚡ Running Performance Tests...")
        
        if not self.check_services_running():
            return {
                "name": "Performance Tests", 
                "duration": 0,
                "returncode": -1,
                "stdout": "",
                "stderr": "Services not running - skipping performance tests",
                "passed": False,
                "skipped": True
            }
        
        cmd = [
            "python", "-m", "pytest",
            "tests/test_performance_slo.py", 
            "-v", "--tb=short", "-s",
            "-m", "performance"
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.base_path, capture_output=True, text=True)
        duration = time.time() - start_time
        
        return {
            "name": "Performance Tests",
            "duration": duration, 
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "passed": result.returncode == 0
        }
    
    def run_e2e_tests(self) -> Dict:
        """Run Playwright E2E browser tests"""
        print("\\n🎭 Running E2E Browser Tests...")
        
        # Check if playwright is available
        try:
            subprocess.run(["playwright", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {
                "name": "E2E Tests",
                "duration": 0,
                "returncode": -1, 
                "stdout": "",
                "stderr": "Playwright not installed - install with: pip install playwright && playwright install",
                "passed": False,
                "skipped": True
            }
        
        if not self.check_services_running():
            return {
                "name": "E2E Tests",
                "duration": 0,
                "returncode": -1,
                "stdout": "",
                "stderr": "Services not running - skipping E2E tests", 
                "passed": False,
                "skipped": True
            }
        
        cmd = [
            "python", "-m", "pytest",
            "tests/test_webrtc_e2e.py",
            "-v", "--tb=short", "-s",
            "-m", "integration"
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.base_path, capture_output=True, text=True)
        duration = time.time() - start_time
        
        return {
            "name": "E2E Tests",
            "duration": duration,
            "returncode": result.returncode, 
            "stdout": result.stdout,
            "stderr": result.stderr,
            "passed": result.returncode == 0
        }
    
    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        total_duration = sum(r["duration"] for r in self.results.values())
        passed_tests = sum(1 for r in self.results.values() if r["passed"])
        total_tests = len([r for r in self.results.values() if not r.get("skipped", False)])
        skipped_tests = sum(1 for r in self.results.values() if r.get("skipped", False))
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                🧪 WEBRTC GATEWAY TEST REPORT                ║  
╠══════════════════════════════════════════════════════════════╣
║ Total Duration: {total_duration:.1f}s                                    ║
║ Tests Passed:   {passed_tests}/{total_tests} ({(passed_tests/max(total_tests,1)*100):.1f}%)                              ║
║ Tests Skipped:  {skipped_tests}                                           ║
╚══════════════════════════════════════════════════════════════╝

📋 Test Suite Results:
"""
        
        for result in self.results.values():
            status = "✅" if result["passed"] else ("⏭️ " if result.get("skipped") else "❌")
            duration = f"{result['duration']:.1f}s" if result["duration"] > 0 else "0.0s"
            report += f"{status} {result['name']}: {duration}\\n"
        
        # Add failure details
        failed_tests = [r for r in self.results.values() if not r["passed"] and not r.get("skipped", False)]
        if failed_tests:
            report += "\\n❌ Failed Test Details:\\n"
            for result in failed_tests:
                report += f"\\n{result['name']}:\\n"
                if result["stderr"]:
                    report += f"  Error: {result['stderr'][:200]}...\\n"
                if result["stdout"]:
                    # Extract key info from pytest output
                    lines = result["stdout"].split("\\n")
                    failure_lines = [line for line in lines if "FAILED" in line or "ERROR" in line]
                    for line in failure_lines[:3]:
                        report += f"  {line}\\n"
        
        return report
    
    def save_detailed_results(self):
        """Save detailed results to JSON"""
        results_file = self.base_path / "test_results.json"
        with open(results_file, "w") as f:
            json.dump({
                "timestamp": time.time(),
                "results": self.results,
                "summary": {
                    "total_duration": sum(r["duration"] for r in self.results.values()),
                    "passed": sum(1 for r in self.results.values() if r["passed"]),
                    "failed": sum(1 for r in self.results.values() if not r["passed"] and not r.get("skipped")),
                    "skipped": sum(1 for r in self.results.values() if r.get("skipped", False))
                }
            }, f, indent=2)
        
        print(f"\\n💾 Detailed results saved to: {results_file}")
    
    def run_all_tests(self, test_level: str = "all"):
        """Run test suite based on level"""
        
        print("🚀 Starting WebRTC Gateway Test Suite")
        print("=" * 50)
        
        if test_level in ["all", "unit"]:
            self.results["unit"] = self.run_unit_tests()
        
        if test_level in ["all", "integration"]:
            self.results["integration"] = self.run_integration_tests()
        
        if test_level in ["all", "performance"]:
            self.results["performance"] = self.run_performance_tests()
        
        if test_level in ["all", "e2e"]:
            self.results["e2e"] = self.run_e2e_tests()
        
        # Generate and display report
        report = self.generate_report()
        print(report)
        
        # Save detailed results
        self.save_detailed_results()
        
        # Return overall success
        return all(r["passed"] or r.get("skipped", False) for r in self.results.values())

def main():
    """Main test runner entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="WebRTC Gateway Test Runner")
    parser.add_argument(
        "--level", 
        choices=["all", "unit", "integration", "performance", "e2e"],
        default="all",
        help="Test level to run"
    )
    parser.add_argument(
        "--check-services",
        action="store_true", 
        help="Only check if services are running"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.check_services:
        if runner.check_services_running():
            print("✅ All required services are running")
            sys.exit(0)
        else:
            print("❌ Required services are not running")
            print("Start services with: python3 main.py")
            sys.exit(1)
    
    success = runner.run_all_tests(args.level)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()