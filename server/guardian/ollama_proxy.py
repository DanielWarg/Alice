#!/usr/bin/env python3
"""
Alice Ollama Proxy - Process isolering för macOS
================================================

Ansvar:
- Starta Ollama som isolerad subprocess
- Resource limits (så mycket som möjligt på macOS)
- Safe startup/shutdown
- Process monitoring
- Recovery vid crashes

macOS-specifik implementering eftersom vi inte har cgroups.
"""

import os
import sys
import time
import signal
import psutil
import logging
import subprocess
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio

@dataclass
class OllamaProxyConfig:
    """Konfiguration för Ollama isolering"""
    # macOS process limits
    nice_level: int = 10                    # Lägre prioritet
    max_memory_gb: float = 8.0              # Soft limit (monitoring)
    max_cpu_percent: float = 80.0           # Soft limit (monitoring)
    
    # Paths
    ollama_binary: str = "/Applications/Ollama.app/Contents/Resources/ollama"
    ollama_command: str = "serve"
    working_dir: str = "/tmp/ollama_isolated"
    log_file: str = "/tmp/ollama_proxy.log"
    
    # Monitoring
    check_interval_s: float = 5.0           # Process health check
    restart_delay_s: float = 10.0           # Väntetid före restart
    max_restart_attempts: int = 3           # Max restart attempts
    
    # Network
    host: str = "127.0.0.1"
    port: int = 11434

class OllamaProxy:
    """Proxy för isolerad Ollama-process"""
    
    def __init__(self, config: OllamaProxyConfig = None):
        self.config = config or OllamaProxyConfig()
        self.logger = logging.getLogger("ollama_proxy")
        
        # Process state
        self.process: Optional[subprocess.Popen] = None
        self.pid: Optional[int] = None
        self.start_time: Optional[datetime] = None
        self.restart_count = 0
        
        # Monitoring
        self.running = True
        self.last_health_check = None
        
        # Signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Graceful shutdown"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.stop_ollama()
    
    def _prepare_environment(self) -> Dict[str, str]:
        """Förbered miljövariabler för isolerad Ollama"""
        env = os.environ.copy()
        
        # Ollama-specifika environment variables
        env.update({
            "OLLAMA_HOST": f"{self.config.host}:{self.config.port}",
            "OLLAMA_LOGS": "1",  # Enable logging
            "OLLAMA_DEBUG": "0", # Minimize debug output
            "OLLAMA_NOHISTORY": "1",  # No command history
        })
        
        # macOS-specifika optimeringar
        env.update({
            "MALLOC_NANO_ZONE": "0",  # Reduce memory fragmentation
            "MallocNanoZone": "0",
        })
        
        return env
    
    def start_ollama(self) -> bool:
        """Starta Ollama som isolerad process"""
        if self.process and self.process.poll() is None:
            self.logger.info("Ollama already running")
            return True
        
        try:
            # Skapa working directory
            os.makedirs(self.config.working_dir, exist_ok=True)
            
            # Prepare command
            cmd = [self.config.ollama_binary, self.config.ollama_command]
            env = self._prepare_environment()
            
            self.logger.info(f"Starting Ollama: {' '.join(cmd)}")
            
            # Start process med resource restrictions
            with open(self.config.log_file, 'w') as log_file:
                self.process = subprocess.Popen(
                    cmd,
                    cwd=self.config.working_dir,
                    env=env,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    preexec_fn=lambda: os.nice(self.config.nice_level)  # Lägre prioritet
                )
            
            self.pid = self.process.pid
            self.start_time = datetime.now()
            
            self.logger.info(f"Ollama started: PID {self.pid}")
            
            # Vänta kort för att se att processen startar
            time.sleep(2)
            
            if self.process.poll() is None:
                return True
            else:
                self.logger.error(f"Ollama failed to start: return code {self.process.returncode}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start Ollama: {e}")
            return False
    
    def stop_ollama(self, force: bool = False) -> bool:
        """Stoppa Ollama-processen"""
        if not self.process:
            return True
        
        try:
            if force:
                # Hard kill
                self.process.kill()
                self.logger.warning("Ollama killed (SIGKILL)")
            else:
                # Graceful shutdown
                self.process.terminate()
                self.logger.info("Ollama terminating (SIGTERM)")
                
                # Vänta på graceful shutdown
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.logger.warning("Graceful shutdown timeout, killing...")
                    self.process.kill()
            
            self.process = None
            self.pid = None
            self.start_time = None
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop Ollama: {e}")
            return False
    
    def get_process_stats(self) -> Optional[Dict[str, Any]]:
        """Hämta processtatistik för monitoring"""
        if not self.pid:
            return None
        
        try:
            proc = psutil.Process(self.pid)
            
            # Memory info
            memory_info = proc.memory_info()
            memory_gb = memory_info.rss / (1024**3)
            
            # CPU info
            cpu_percent = proc.cpu_percent()
            
            # Process info
            create_time = datetime.fromtimestamp(proc.create_time())
            uptime_s = (datetime.now() - create_time).total_seconds()
            
            return {
                "pid": self.pid,
                "memory_gb": memory_gb,
                "cpu_percent": cpu_percent,
                "uptime_s": uptime_s,
                "status": proc.status(),
                "num_threads": proc.num_threads(),
                "create_time": create_time.isoformat(),
            }
            
        except psutil.NoSuchProcess:
            self.logger.warning(f"Process {self.pid} no longer exists")
            self.pid = None
            self.process = None
            return None
        except Exception as e:
            self.logger.error(f"Failed to get process stats: {e}")
            return None
    
    def check_process_health(self) -> bool:
        """Kontrollera om Ollama-processen är hälsosam"""
        if not self.process or self.process.poll() is not None:
            return False
        
        stats = self.get_process_stats()
        if not stats:
            return False
        
        # Check resource limits
        memory_gb = stats["memory_gb"]
        cpu_percent = stats["cpu_percent"]
        
        if memory_gb > self.config.max_memory_gb:
            self.logger.warning(f"Memory limit exceeded: {memory_gb:.1f}GB > {self.config.max_memory_gb}GB")
            return False
        
        if cpu_percent > self.config.max_cpu_percent:
            self.logger.warning(f"CPU limit exceeded: {cpu_percent:.1f}% > {self.config.max_cpu_percent}%")
            return False
        
        return True
    
    async def health_check_loop(self):
        """Kontinuerlig hälsokontroll med auto-restart"""
        while self.running:
            try:
                healthy = self.check_process_health()
                stats = self.get_process_stats()
                
                if stats:
                    self.logger.debug(f"Ollama stats: {stats['memory_gb']:.1f}GB, {stats['cpu_percent']:.1f}% CPU")
                
                if not healthy and self.running:
                    self.logger.warning("Ollama unhealthy, attempting restart...")
                    
                    # Stop unhealthy process
                    self.stop_ollama(force=True)
                    
                    # Wait before restart
                    await asyncio.sleep(self.config.restart_delay_s)
                    
                    # Restart if we haven't exceeded max attempts
                    if self.restart_count < self.config.max_restart_attempts:
                        self.restart_count += 1
                        if self.start_ollama():
                            self.logger.info(f"Ollama restarted (attempt {self.restart_count})")
                        else:
                            self.logger.error(f"Restart failed (attempt {self.restart_count})")
                    else:
                        self.logger.error(f"Max restart attempts exceeded ({self.config.max_restart_attempts})")
                        self.running = False
                        break
                
                self.last_health_check = datetime.now()
                await asyncio.sleep(self.config.check_interval_s)
                
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                await asyncio.sleep(self.config.check_interval_s)
    
    def get_status(self) -> Dict[str, Any]:
        """Status för monitoring"""
        stats = self.get_process_stats()
        
        return {
            "running": self.running,
            "process_alive": self.process is not None and self.process.poll() is None,
            "pid": self.pid,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "restart_count": self.restart_count,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "stats": stats,
            "config": {
                "max_memory_gb": self.config.max_memory_gb,
                "max_cpu_percent": self.config.max_cpu_percent,
                "nice_level": self.config.nice_level
            }
        }
    
    async def run(self):
        """Huvudloop - starta och övervaka Ollama"""
        self.logger.info("=== Ollama Proxy Starting ===")
        self.logger.info(f"Binary: {self.config.ollama_binary}")
        self.logger.info(f"Limits: {self.config.max_memory_gb}GB RAM, {self.config.max_cpu_percent}% CPU")
        
        # Initial start
        if not self.start_ollama():
            self.logger.error("Failed to start Ollama initially")
            return
        
        # Start monitoring loop
        await self.health_check_loop()
        
        # Cleanup
        self.logger.info("Stopping Ollama...")
        self.stop_ollama()
        self.logger.info("Ollama Proxy stopped")

# Global instance
_proxy = None

def get_proxy() -> OllamaProxy:
    """Singleton access"""
    global _proxy
    if _proxy is None:
        _proxy = OllamaProxy()
    return _proxy

# CLI interface
async def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ollama Proxy - Isolated process management")
    parser.add_argument("--memory-limit", type=float, default=8.0, help="Memory limit in GB")
    parser.add_argument("--cpu-limit", type=float, default=80.0, help="CPU limit in percent")
    parser.add_argument("--nice", type=int, default=10, help="Process nice level")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s [%(name)s:%(levelname)s] %(message)s'
    )
    
    # Create proxy with custom config
    config = OllamaProxyConfig(
        max_memory_gb=args.memory_limit,
        max_cpu_percent=args.cpu_limit,
        nice_level=args.nice
    )
    
    proxy = OllamaProxy(config)
    
    try:
        await proxy.run()
    except KeyboardInterrupt:
        print("\\nProxy stopped by user")
    except Exception as e:
        print(f"Proxy error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())