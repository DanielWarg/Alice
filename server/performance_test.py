#!/usr/bin/env python3
"""
Alice Performance Test Script
Tests response times over time to analyze model warming behavior
"""
import asyncio
import httpx
import time
import json
import statistics
from datetime import datetime
from typing import List, Dict

class PerformanceTester:
    def __init__(self, 
                 base_url: str = "http://127.0.0.1:8000",
                 interval_seconds: int = 10,
                 total_tests: int = 20):
        self.base_url = base_url
        self.interval_seconds = interval_seconds
        self.total_tests = total_tests
        self.results: List[Dict] = []
        
        # Test questions (short ones to avoid token count affecting performance)
        self.questions = [
            "Hej Alice!",
            "Vad heter du?",
            "Vilken dag är det idag?",
            "Vad är 2+2?",
            "Säg något kort",
            "Hur mår du?",
            "Vad är klockan?",
            "Berätta en kort fact",
        ]
    
    async def send_request(self, question: str) -> Dict:
        """Send a single request and measure performance"""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {"message": question}
                
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                end_time = time.time()
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "timestamp": datetime.now().isoformat(),
                        "question": question,
                        "status": "success",
                        "response_time_ms": (end_time - start_time) * 1000,
                        "backend_ttft_ms": data.get("tftt_ms"),
                        "model": data.get("model"),
                        "response_length": len(data.get("response", "")),
                        "response_preview": data.get("response", "")[:50] + "..." if len(data.get("response", "")) > 50 else data.get("response", "")
                    }
                else:
                    return {
                        "timestamp": datetime.now().isoformat(),
                        "question": question,
                        "status": "error",
                        "response_time_ms": (end_time - start_time) * 1000,
                        "error": f"HTTP {response.status_code}",
                        "model": "unknown"
                    }
                    
        except Exception as e:
            end_time = time.time()
            return {
                "timestamp": datetime.now().isoformat(),
                "question": question,
                "status": "exception",
                "response_time_ms": (end_time - start_time) * 1000,
                "error": str(e),
                "model": "unknown"
            }
    
    async def check_ollama_status(self) -> Dict:
        """Check Ollama model status"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:11434/api/ps")
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    
                    gpt_model = next((m for m in models if "gpt-oss" in m.get("name", "")), None)
                    
                    if gpt_model:
                        return {
                            "loaded": True,
                            "name": gpt_model.get("name"),
                            "size_vram_gb": round(gpt_model.get("size_vram", 0) / 1024**3, 2),
                            "expires_at": gpt_model.get("expires_at"),
                            "context_length": gpt_model.get("context_length")
                        }
                    else:
                        return {"loaded": False}
                else:
                    return {"error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            return {"error": str(e)}
    
    async def run_test(self):
        """Run the performance test"""
        print(f"🚀 Starting Alice Performance Test")
        print(f"📊 {self.total_tests} tests, {self.interval_seconds}s intervals")
        print("=" * 80)
        
        # Check initial Ollama status
        ollama_status = await self.check_ollama_status()
        print(f"🔍 Initial Ollama Status: {ollama_status}")
        print("=" * 80)
        
        for i in range(self.total_tests):
            question = self.questions[i % len(self.questions)]
            
            print(f"📝 Test {i+1}/{self.total_tests}: {question}")
            
            result = await self.send_request(question)
            self.results.append(result)
            
            # Print result
            if result["status"] == "success":
                print(f"✅ {result['response_time_ms']:.0f}ms | {result['model']} | {result['response_preview']}")
                if result.get('backend_ttft_ms'):
                    print(f"   Backend TTFT: {result['backend_ttft_ms']:.0f}ms")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")
            
            # Check Ollama status periodically
            if (i + 1) % 5 == 0:
                ollama_status = await self.check_ollama_status()
                if ollama_status.get("loaded"):
                    expires_in = "N/A"
                    if ollama_status.get("expires_at"):
                        try:
                            from dateutil.parser import parse
                            expire_time = parse(ollama_status["expires_at"])
                            expires_in = f"{int((expire_time - datetime.now()).total_seconds() / 60)}min"
                        except:
                            pass
                    print(f"🔥 Ollama: {ollama_status['size_vram_gb']}GB VRAM, expires in {expires_in}")
                else:
                    print("❄️ Ollama: Model not loaded")
            
            print("-" * 50)
            
            # Wait before next test
            if i < self.total_tests - 1:
                await asyncio.sleep(self.interval_seconds)
        
        # Generate summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary with statistics"""
        print("\n" + "=" * 80)
        print("📊 PERFORMANCE SUMMARY")
        print("=" * 80)
        
        successful_tests = [r for r in self.results if r["status"] == "success"]
        
        if not successful_tests:
            print("❌ No successful tests!")
            return
        
        response_times = [r["response_time_ms"] for r in successful_tests]
        backend_times = [r["backend_ttft_ms"] for r in successful_tests if r.get("backend_ttft_ms")]
        
        # Model usage
        models_used = {}
        for result in successful_tests:
            model = result.get("model", "unknown")
            models_used[model] = models_used.get(model, 0) + 1
        
        print(f"✅ Successful tests: {len(successful_tests)}/{len(self.results)}")
        print(f"❌ Failed tests: {len(self.results) - len(successful_tests)}")
        print()
        
        print("🏃 Response Time Statistics:")
        print(f"   Min:    {min(response_times):.0f}ms")
        print(f"   Max:    {max(response_times):.0f}ms")
        print(f"   Mean:   {statistics.mean(response_times):.0f}ms")
        print(f"   Median: {statistics.median(response_times):.0f}ms")
        if len(response_times) > 1:
            print(f"   StdDev: {statistics.stdev(response_times):.0f}ms")
        print()
        
        if backend_times:
            print("🧠 Backend TTFT Statistics:")
            print(f"   Min:    {min(backend_times):.0f}ms")
            print(f"   Max:    {max(backend_times):.0f}ms")
            print(f"   Mean:   {statistics.mean(backend_times):.0f}ms")
            print(f"   Median: {statistics.median(backend_times):.0f}ms")
            print()
        
        print("🤖 Model Usage:")
        for model, count in models_used.items():
            percentage = (count / len(successful_tests)) * 100
            print(f"   {model}: {count} times ({percentage:.1f}%)")
        print()
        
        # Performance trend analysis
        first_half = response_times[:len(response_times)//2]
        second_half = response_times[len(response_times)//2:]
        
        if len(first_half) > 0 and len(second_half) > 0:
            first_avg = statistics.mean(first_half)
            second_avg = statistics.mean(second_half)
            improvement = ((first_avg - second_avg) / first_avg) * 100
            
            print("📈 Performance Trend:")
            print(f"   First half avg:  {first_avg:.0f}ms")
            print(f"   Second half avg: {second_avg:.0f}ms")
            if improvement > 0:
                print(f"   Improvement:     {improvement:.1f}% faster ⚡")
            else:
                print(f"   Degradation:     {abs(improvement):.1f}% slower 🐌")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_test_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                "test_config": {
                    "base_url": self.base_url,
                    "interval_seconds": self.interval_seconds,
                    "total_tests": self.total_tests
                },
                "results": self.results,
                "summary": {
                    "successful_tests": len(successful_tests),
                    "failed_tests": len(self.results) - len(successful_tests),
                    "response_time_stats": {
                        "min_ms": min(response_times),
                        "max_ms": max(response_times),
                        "mean_ms": statistics.mean(response_times),
                        "median_ms": statistics.median(response_times)
                    } if response_times else None,
                    "models_used": models_used
                }
            }, indent=2)
        
        print(f"💾 Detailed results saved to: {filename}")


async def main():
    """Main function"""
    import sys
    
    # Parse command line arguments
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    total_tests = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    
    tester = PerformanceTester(
        interval_seconds=interval,
        total_tests=total_tests
    )
    
    try:
        await tester.run_test()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        if tester.results:
            tester.print_summary()


if __name__ == "__main__":
    # Install required packages if missing
    try:
        import httpx
        import dateutil.parser
    except ImportError:
        print("Installing required packages...")
        import subprocess
        import sys
        subprocess.run([sys.executable, "-m", "pip", "install", "httpx", "python-dateutil"])
        import httpx
        import dateutil.parser
    
    asyncio.run(main())