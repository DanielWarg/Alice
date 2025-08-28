#!/usr/bin/env python3
"""
Controlled Memory Test for gpt-oss:20b
Tests if 24GB RAM can handle the model safely with monitoring
"""
import psutil
import httpx
import asyncio
import time
import json
from datetime import datetime

class MemoryMonitor:
    def __init__(self):
        self.measurements = []
        self.running = False
        
    def get_memory_info(self):
        """Get detailed memory information"""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Find Ollama process
        ollama_memory = 0
        ollama_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                if 'ollama' in proc.info['name'].lower():
                    ollama_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'], 
                        'memory_mb': proc.info['memory_info'].rss / 1024**2
                    })
                    ollama_memory += proc.info['memory_info'].rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return {
            'timestamp': datetime.now().isoformat(),
            'system_memory': {
                'total_gb': round(memory.total / 1024**3, 2),
                'available_gb': round(memory.available / 1024**3, 2),
                'used_gb': round(memory.used / 1024**3, 2),
                'used_percent': memory.percent,
                'free_gb': round(memory.free / 1024**3, 2)
            },
            'swap_memory': {
                'total_gb': round(swap.total / 1024**3, 2),
                'used_gb': round(swap.used / 1024**3, 2),
                'used_percent': swap.percent
            },
            'ollama': {
                'total_memory_gb': round(ollama_memory / 1024**3, 2),
                'processes': ollama_processes
            }
        }
    
    async def monitor_during_load(self, duration_seconds=300):
        """Monitor memory during model loading"""
        print(f"🔍 Starting memory monitoring for {duration_seconds} seconds")
        print("=" * 60)
        
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds and self.running:
            info = self.get_memory_info()
            self.measurements.append(info)
            
            # Print current status
            sys_mem = info['system_memory']
            ollama_mem = info['ollama']
            
            print(f"[{len(self.measurements):3d}] ", end="")
            print(f"RAM: {sys_mem['used_gb']:.1f}GB/{sys_mem['total_gb']:.1f}GB ({sys_mem['used_percent']:.1f}%) | ", end="")
            print(f"Available: {sys_mem['available_gb']:.1f}GB | ", end="")
            print(f"Ollama: {ollama_mem['total_memory_gb']:.1f}GB")
            
            # Check for danger zone
            if sys_mem['used_percent'] > 90:
                print("⚠️  WARNING: Memory usage > 90%!")
            
            if sys_mem['available_gb'] < 2:
                print("🚨 CRITICAL: Less than 2GB available!")
                
            await asyncio.sleep(2)
        
        print("\n" + "=" * 60)
        print("📊 MEMORY TEST SUMMARY")
        print("=" * 60)
        
        if self.measurements:
            used_gb_values = [m['system_memory']['used_gb'] for m in self.measurements]
            used_percent_values = [m['system_memory']['used_percent'] for m in self.measurements]
            ollama_gb_values = [m['ollama']['total_memory_gb'] for m in self.measurements]
            
            print(f"System Memory Usage:")
            print(f"  Min:     {min(used_gb_values):.1f}GB ({min(used_percent_values):.1f}%)")
            print(f"  Max:     {max(used_gb_values):.1f}GB ({max(used_percent_values):.1f}%)")
            print(f"  Average: {sum(used_gb_values)/len(used_gb_values):.1f}GB ({sum(used_percent_values)/len(used_percent_values):.1f}%)")
            
            print(f"\nOllama Memory Usage:")
            print(f"  Min:     {min(ollama_gb_values):.1f}GB")
            print(f"  Max:     {max(ollama_gb_values):.1f}GB")
            print(f"  Average: {sum(ollama_gb_values)/len(ollama_gb_values):.1f}GB")
            
            print(f"\nSafety Analysis:")
            max_used_percent = max(used_percent_values)
            min_available = min([m['system_memory']['available_gb'] for m in self.measurements])
            
            if max_used_percent < 80:
                print(f"✅ SAFE: Peak memory usage {max_used_percent:.1f}% (< 80%)")
            elif max_used_percent < 90:
                print(f"⚠️  CAUTION: Peak memory usage {max_used_percent:.1f}% (80-90%)")
            else:
                print(f"🚨 DANGER: Peak memory usage {max_used_percent:.1f}% (> 90%)")
            
            print(f"   Minimum available memory: {min_available:.1f}GB")
            
            # Save detailed log
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"memory_test_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(self.measurements, indent=2, fp=f)
            
            print(f"\n💾 Detailed log saved to: {filename}")

async def test_gpt_oss_loading():
    """Test loading gpt-oss:20b with memory monitoring"""
    
    monitor = MemoryMonitor()
    
    # Get baseline
    print("📊 Baseline memory before test:")
    baseline = monitor.get_memory_info()
    sys_mem = baseline['system_memory']
    print(f"   RAM: {sys_mem['used_gb']:.1f}GB/{sys_mem['total_gb']:.1f}GB ({sys_mem['used_percent']:.1f}%)")
    print(f"   Available: {sys_mem['available_gb']:.1f}GB")
    print()
    
    # Check if we have enough theoretical space
    if sys_mem['available_gb'] < 16:
        print(f"⚠️  WARNING: Only {sys_mem['available_gb']:.1f}GB available")
        print("   gpt-oss:20b needs ~14GB. Proceed? (y/n)")
        response = input().lower()
        if response != 'y':
            print("Test cancelled.")
            return
    
    # Start monitoring
    monitor.running = True
    monitor_task = asyncio.create_task(monitor.monitor_during_load(300))  # 5 minutes
    
    try:
        print("🚀 Loading gpt-oss:20b model...")
        
        # Send a request to load the model
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": "gpt-oss:20b",
                "prompt": "Hej, testa minnet",
                "keep_alive": "5m",  # Short keep-alive for test
                "stream": False,
                "options": {"num_predict": 10}
            }
            
            start_time = time.time()
            response = await client.post("http://localhost:11434/api/generate", json=payload)
            load_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Model loaded successfully in {load_time:.1f} seconds")
                print(f"   Response: {result.get('response', '')[:100]}...")
                
                # Keep monitoring for a bit longer to see steady state
                print("⏱️  Monitoring steady state for 2 minutes...")
                await asyncio.sleep(120)
                
            else:
                print(f"❌ Failed to load model: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
    
    except Exception as e:
        print(f"❌ Error during test: {e}")
    
    finally:
        print("\n🛑 Stopping monitoring...")
        monitor.running = False
        await monitor_task

async def main():
    """Main test function"""
    print("🧪 gpt-oss:20b Memory Test")
    print("Testing if 24GB RAM can safely handle the model")
    print("=" * 60)
    
    # Check if Ollama is running
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code != 200:
                print("❌ Ollama not running. Start it first: ollama serve")
                return
    except Exception as e:
        print(f"❌ Cannot reach Ollama: {e}")
        print("   Make sure Ollama is running: ollama serve")
        return
    
    print("✅ Ollama is running")
    print("⚠️  This test will load gpt-oss:20b and monitor memory usage")
    print("   Press Ctrl+C anytime to stop safely")
    print()
    
    input("Press Enter to start the test...")
    
    try:
        await test_gpt_oss_loading()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        
    print("\n✨ Test completed!")

if __name__ == "__main__":
    asyncio.run(main())