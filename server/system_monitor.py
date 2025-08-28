#!/usr/bin/env python3
"""
System Resource Monitor
Monitors CPU, Memory, GPU usage while Alice is running
"""
import time
import psutil
import json
import subprocess
from datetime import datetime
from typing import Dict, List

class SystemMonitor:
    def __init__(self, interval_seconds: int = 5):
        self.interval_seconds = interval_seconds
        self.measurements: List[Dict] = []
        
    def get_ollama_process_info(self) -> Dict:
        """Get information about Ollama process"""
        try:
            # Find Ollama process
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                if 'ollama' in proc.info['name'].lower():
                    proc_info = psutil.Process(proc.info['pid'])
                    
                    # Get detailed memory info
                    memory_info = proc_info.memory_info()
                    
                    return {
                        "found": True,
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "memory_rss_mb": memory_info.rss / 1024**2,  # Resident Set Size
                        "memory_vms_mb": memory_info.vms / 1024**2,  # Virtual Memory Size
                        "cpu_percent": proc_info.cpu_percent(),
                        "num_threads": proc_info.num_threads(),
                        "status": proc_info.status()
                    }
            
            return {"found": False}
            
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    def get_gpu_info(self) -> Dict:
        """Get GPU usage info (if available)"""
        try:
            # Try nvidia-smi for NVIDIA GPUs
            result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                gpus = []
                
                for i, line in enumerate(lines):
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 4:
                        gpus.append({
                            "gpu_id": i,
                            "utilization_percent": int(parts[0]),
                            "memory_used_mb": int(parts[1]),
                            "memory_total_mb": int(parts[2]),
                            "temperature_c": int(parts[3]),
                            "memory_usage_percent": round((int(parts[1]) / int(parts[2])) * 100, 1)
                        })
                
                return {"available": True, "type": "nvidia", "gpus": gpus}
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Try Metal Performance Shaders (macOS)
        try:
            result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and 'Metal' in result.stdout:
                return {"available": True, "type": "metal", "info": "macOS Metal GPU detected"}
            
        except:
            pass
        
        return {"available": False, "type": "none"}
    
    def get_system_snapshot(self) -> Dict:
        """Get current system resource snapshot"""
        timestamp = datetime.now().isoformat()
        
        # System-wide stats
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Load averages (Unix-like systems)
        load_avg = None
        try:
            load_avg = psutil.getloadavg()
        except AttributeError:
            pass  # Not available on Windows
        
        # Network I/O
        net_io = psutil.net_io_counters()
        
        # Ollama process info
        ollama_info = self.get_ollama_process_info()
        
        # GPU info
        gpu_info = self.get_gpu_info()
        
        return {
            "timestamp": timestamp,
            "system": {
                "cpu_percent": cpu_percent,
                "cpu_count": psutil.cpu_count(),
                "load_avg_1min": load_avg[0] if load_avg else None,
                "memory_total_gb": memory.total / 1024**3,
                "memory_available_gb": memory.available / 1024**3,
                "memory_used_gb": memory.used / 1024**3,
                "memory_percent": memory.percent,
                "disk_total_gb": disk.total / 1024**3,
                "disk_used_gb": disk.used / 1024**3,
                "disk_percent": (disk.used / disk.total) * 100,
                "network_bytes_sent": net_io.bytes_sent,
                "network_bytes_recv": net_io.bytes_recv
            },
            "ollama": ollama_info,
            "gpu": gpu_info
        }
    
    def monitor(self, duration_minutes: int = 10):
        """Monitor system for specified duration"""
        total_measurements = (duration_minutes * 60) // self.interval_seconds
        
        print(f"🖥️  Starting System Monitor")
        print(f"⏱️  Duration: {duration_minutes} minutes ({total_measurements} measurements)")
        print(f"📊 Interval: {self.interval_seconds} seconds")
        print("=" * 80)
        
        try:
            for i in range(total_measurements):
                snapshot = self.get_system_snapshot()
                self.measurements.append(snapshot)
                
                # Print current status
                system = snapshot["system"]
                ollama = snapshot["ollama"]
                gpu = snapshot["gpu"]
                
                print(f"[{i+1:3d}/{total_measurements}] ", end="")
                print(f"CPU: {system['cpu_percent']:5.1f}% | ", end="")
                print(f"RAM: {system['memory_percent']:5.1f}% ({system['memory_used_gb']:.1f}GB) | ", end="")
                
                if ollama.get("found"):
                    print(f"Ollama: {ollama['memory_rss_mb']:.0f}MB", end="")
                else:
                    print("Ollama: Not found", end="")
                
                if gpu.get("available") and gpu.get("gpus"):
                    gpu_data = gpu["gpus"][0]  # First GPU
                    print(f" | GPU: {gpu_data['utilization_percent']}% ({gpu_data['memory_used_mb']}MB)")
                else:
                    print()
                
                if i < total_measurements - 1:
                    time.sleep(self.interval_seconds)
        
        except KeyboardInterrupt:
            print("\n🛑 Monitoring interrupted by user")
        
        # Generate summary
        self.print_summary()
    
    def print_summary(self):
        """Print monitoring summary"""
        if not self.measurements:
            print("❌ No measurements collected!")
            return
        
        print("\n" + "=" * 80)
        print("📊 SYSTEM RESOURCE SUMMARY")
        print("=" * 80)
        
        # Calculate averages and peaks
        cpu_values = [m["system"]["cpu_percent"] for m in self.measurements]
        memory_values = [m["system"]["memory_percent"] for m in self.measurements]
        memory_gb_values = [m["system"]["memory_used_gb"] for m in self.measurements]
        
        print(f"⏱️  Monitoring Duration: {len(self.measurements) * self.interval_seconds} seconds")
        print(f"📏 Measurements: {len(self.measurements)}")
        print()
        
        print("🖥️  CPU Usage:")
        print(f"   Average: {sum(cpu_values)/len(cpu_values):.1f}%")
        print(f"   Peak:    {max(cpu_values):.1f}%")
        print(f"   Min:     {min(cpu_values):.1f}%")
        print()
        
        print("💾 Memory Usage:")
        print(f"   Average: {sum(memory_values)/len(memory_values):.1f}% ({sum(memory_gb_values)/len(memory_gb_values):.1f}GB)")
        print(f"   Peak:    {max(memory_values):.1f}% ({max(memory_gb_values):.1f}GB)")
        print(f"   Min:     {min(memory_values):.1f}% ({min(memory_gb_values):.1f}GB)")
        print()
        
        # Ollama-specific stats
        ollama_measurements = [m["ollama"] for m in self.measurements if m["ollama"].get("found")]
        
        if ollama_measurements:
            ollama_memory = [m["memory_rss_mb"] for m in ollama_measurements]
            
            print("🦙 Ollama Process:")
            print(f"   Detected in {len(ollama_measurements)}/{len(self.measurements)} measurements")
            print(f"   Average Memory: {sum(ollama_memory)/len(ollama_memory):.0f}MB")
            print(f"   Peak Memory:    {max(ollama_memory):.0f}MB")
            print(f"   Memory Growth:  {max(ollama_memory) - min(ollama_memory):.0f}MB")
            
            # Get latest process info
            latest_ollama = ollama_measurements[-1]
            print(f"   Current PID:    {latest_ollama.get('pid')}")
            print(f"   Threads:        {latest_ollama.get('num_threads')}")
            print(f"   Status:         {latest_ollama.get('status')}")
        else:
            print("🦙 Ollama Process: Not detected during monitoring")
        print()
        
        # GPU stats if available
        gpu_measurements = [m["gpu"] for m in self.measurements if m["gpu"].get("available")]
        
        if gpu_measurements and any(m.get("gpus") for m in gpu_measurements):
            gpu_util = [m["gpus"][0]["utilization_percent"] for m in gpu_measurements if m.get("gpus")]
            gpu_memory = [m["gpus"][0]["memory_used_mb"] for m in gpu_measurements if m.get("gpus")]
            
            print("🎮 GPU Usage:")
            print(f"   Average Utilization: {sum(gpu_util)/len(gpu_util):.1f}%")
            print(f"   Peak Utilization:    {max(gpu_util):.1f}%")
            print(f"   Average VRAM:        {sum(gpu_memory)/len(gpu_memory):.0f}MB")
            print(f"   Peak VRAM:           {max(gpu_memory):.0f}MB")
        else:
            print("🎮 GPU: Not available or not detected")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"system_monitor_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                "config": {
                    "interval_seconds": self.interval_seconds,
                    "total_measurements": len(self.measurements)
                },
                "measurements": self.measurements
            }, indent=2)
        
        print(f"\n💾 Detailed data saved to: {filename}")


def main():
    """Main function"""
    import sys
    
    # Parse command line arguments
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 10  # minutes
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5   # seconds
    
    monitor = SystemMonitor(interval_seconds=interval)
    
    print(f"Starting system monitor for {duration} minutes...")
    print("Press Ctrl+C to stop early\n")
    
    monitor.monitor(duration_minutes=duration)


if __name__ == "__main__":
    main()