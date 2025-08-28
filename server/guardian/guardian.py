#!/usr/bin/env python3
"""
Alice System Guardian - Regelbaserad säkerhetsdaemon
==================================================

Deterministisk övervakare som skyddar systemet från gpt-oss:20b överbelastning.
Ingen AI i säkerhetsloopen - bara hårda trösklar och verifierbara regler.

Ansvar:
- RAM/CPU/Disk monitoring (1s intervall)
- Tröskelbaserade åtgärder (soft degradation → hard kill)
- Emergency stop vid kritiska problem
- HTTP API för åtgärder

Kommunikation:
- HTTP endpoints för degrade/stop-intake
- JSON metrics loggning
- Health check på :8787
"""

import os
import sys
import json
import time
import signal
import asyncio
import logging
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
import psutil
import httpx
from aiohttp import web, web_runner

@dataclass
class GuardianConfig:
    """Deterministisk konfiguration - inga AI-parametrar"""
    # Polling
    poll_interval_s: float = 1.0
    
    # Trösklar (andel av total)
    ram_soft_pct: float = 0.85      # Mjuk degradation
    ram_hard_pct: float = 0.92      # Hard kill
    cpu_soft_pct: float = 0.85      # Mjuk degradation  
    cpu_hard_pct: float = 0.92      # Hard kill
    disk_hard_pct: float = 0.95     # Hard kill
    temp_hard_c: float = 90.0       # Hard kill (om tillgänglig)
    
    # Åtgärder
    enable_unload_model: bool = True
    enable_stop_intake: bool = True  
    enable_kill_ollama: bool = True
    
    # Endpoints
    alice_base_url: str = "http://localhost:3000"
    ollama_base_url: str = "http://localhost:11434"
    guardian_port: int = 8787

class GuardianActions:
    """Deterministiska åtgärder utan AI-logik"""
    
    def __init__(self, config: GuardianConfig):
        self.config = config
        self.logger = logging.getLogger("guardian.actions")
    
    async def degrade(self) -> bool:
        """Mjuk nedväxling: minska samtidighet"""
        try:
            url = f"{self.config.alice_base_url}/api/guard/degrade"
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.post(url)
                self.logger.info(f"Degrade: {response.status_code}")
                return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Degrade failed: {e}")
            return False
    
    async def stop_intake(self) -> bool:
        """Hård: stoppa nya requests"""
        try:
            url = f"{self.config.alice_base_url}/api/guard/stop-intake"
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.post(url)
                self.logger.info(f"Stop intake: {response.status_code}")
                return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Stop intake failed: {e}")
            return False
    
    async def unload_model(self) -> bool:
        """Snäll: försök ladda ur modell från Ollama"""
        try:
            url = f"{self.config.ollama_base_url}/api/generate"
            payload = {"model": "gpt-oss:20b", "keep_alive": 0}
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload)
                self.logger.info(f"Unload model: {response.status_code}")
                return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Unload model failed: {e}")
            return False
    
    def kill_ollama(self) -> bool:
        """Hard kill: döda Ollama-processer"""
        try:
            result = subprocess.run(
                ["pkill", "-9", "-f", "ollama"],
                capture_output=True, text=True, timeout=5
            )
            self.logger.warning(f"Kill Ollama: return code {result.returncode}")
            return True
        except Exception as e:
            self.logger.error(f"Kill Ollama failed: {e}")
            return False
    
    def restart_ollama(self) -> bool:
        """Restart Ollama efter kill"""
        try:
            # macOS: starta Ollama app eller serve
            subprocess.Popen(
                ["/Applications/Ollama.app/Contents/Resources/ollama", "serve"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            self.logger.info("Restarting Ollama")
            return True
        except Exception as e:
            self.logger.error(f"Restart Ollama failed: {e}")
            return False

class SystemGuardian:
    """Huvudklassen - deterministisk övervakare"""
    
    def __init__(self, config: GuardianConfig = None):
        self.config = config or GuardianConfig()
        self.actions = GuardianActions(self.config)
        self.logger = logging.getLogger("guardian")
        
        # Tillstånd (deterministiskt)
        self.degraded = False
        self.intake_blocked = False
        self.emergency_mode = False
        self.startup_time = datetime.now()
        
        # Metrics history (för trend - ej AI)
        self.metrics_history = []
        self.max_history = 60  # 1 minut vid 1s polling
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
    
    def _signal_handler(self, signum, frame):
        """Graceful shutdown"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Samla systemmetriker - deterministiskt"""
        try:
            # Memory
            memory = psutil.virtual_memory()
            ram_pct = memory.percent / 100.0
            
            # CPU (kort sampling för realtid)
            cpu_pct = psutil.cpu_percent(interval=0.1) / 100.0
            
            # Disk usage (root filesystem)
            disk = psutil.disk_usage('/')
            disk_pct = (disk.used / disk.total) if disk.total > 0 else 0.0
            
            # Temperature (macOS - försök bara)
            temp_c = 0.0
            try:
                # På macOS kan vi försöka läsa sensors, men oftast inte tillgängligt
                sensors = psutil.sensors_temperatures()
                if sensors:
                    for name, entries in sensors.items():
                        for entry in entries:
                            if entry.current:
                                temp_c = max(temp_c, entry.current)
            except:
                pass
            
            # Process counts
            ollama_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if any('ollama' in str(item).lower() for item in proc.info['cmdline'] or []):
                        ollama_processes.append(proc.info['pid'])
                except:
                    pass
            
            return {
                'timestamp': datetime.now().isoformat(),
                'ram_pct': ram_pct,
                'cpu_pct': cpu_pct, 
                'disk_pct': disk_pct,
                'temp_c': temp_c,
                'ram_gb': memory.used / (1024**3),
                'ollama_pids': ollama_processes,
                'degraded': self.degraded,
                'intake_blocked': self.intake_blocked,
                'emergency_mode': self.emergency_mode
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'degraded': self.degraded,
                'intake_blocked': self.intake_blocked,
                'emergency_mode': self.emergency_mode
            }
    
    async def evaluate_and_act(self, metrics: Dict[str, Any]) -> None:
        """
        Deterministisk regelmotor - INGEN AI här
        Bara enkla if/else baserat på trösklar
        """
        if 'error' in metrics:
            return
        
        ram_pct = metrics.get('ram_pct', 0)
        cpu_pct = metrics.get('cpu_pct', 0) 
        disk_pct = metrics.get('disk_pct', 0)
        temp_c = metrics.get('temp_c', 0)
        
        # === SOFT ACTIONS (degradation) ===
        soft_trigger = (
            ram_pct >= self.config.ram_soft_pct or
            cpu_pct >= self.config.cpu_soft_pct
        )
        
        if soft_trigger and not self.degraded:
            self.logger.warning(f"SOFT trigger: RAM={ram_pct:.1%} CPU={cpu_pct:.1%}")
            if self.config.enable_unload_model:
                await self.actions.degrade()
                # Försök unload model mjukt
                await self.actions.unload_model()
                self.degraded = True
        
        # === HARD ACTIONS (emergency) ===
        hard_trigger = (
            ram_pct >= self.config.ram_hard_pct or
            cpu_pct >= self.config.cpu_hard_pct or
            disk_pct >= self.config.disk_hard_pct or
            (temp_c > 0 and temp_c >= self.config.temp_hard_c)
        )
        
        if hard_trigger:
            self.logger.error(f"HARD trigger: RAM={ram_pct:.1%} CPU={cpu_pct:.1%} DISK={disk_pct:.1%} TEMP={temp_c}°C")
            
            if not self.intake_blocked and self.config.enable_stop_intake:
                await self.actions.stop_intake()
                self.intake_blocked = True
            
            if self.config.enable_kill_ollama:
                # Försök unload först
                await self.actions.unload_model()
                time.sleep(1)
                
                # Sen hard kill
                if self.actions.kill_ollama():
                    self.emergency_mode = True
                    # Vänta lite, sen restart
                    await asyncio.sleep(3)
                    self.actions.restart_ollama()
        
        # === RECOVERY CHECK ===
        # Om systemet är stabilt igen, återställ gradvis
        recovery_safe = (
            ram_pct < self.config.ram_soft_pct * 0.9 and  # 10% marginal
            cpu_pct < self.config.cpu_soft_pct * 0.9
        )
        
        if recovery_safe and (self.degraded or self.intake_blocked):
            self.logger.info("System recovered, resetting state")
            self.degraded = False
            self.intake_blocked = False
            self.emergency_mode = False
    
    async def health_handler(self, request):
        """HTTP health check endpoint"""
        metrics = self.get_system_metrics()
        status = {
            'status': 'emergency' if self.emergency_mode else 'degraded' if self.degraded else 'ok',
            'uptime_s': (datetime.now() - self.startup_time).total_seconds(),
            'metrics': metrics
        }
        return web.json_response(status)
    
    async def run_monitoring_loop(self):
        """Huvudloop - kontinuerlig övervakning"""
        self.logger.info("Starting Guardian monitoring loop")
        
        while self.running:
            try:
                # Samla metrics
                metrics = self.get_system_metrics()
                
                # Spara för trend (ej AI, bara historia)
                self.metrics_history.append(metrics)
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history.pop(0)
                
                # Logga (NDJSON för parsing)
                print(json.dumps(metrics, separators=(',', ':')))
                
                # Deterministisk evaluering
                await self.evaluate_and_act(metrics)
                
                # Vänta till nästa cykel
                await asyncio.sleep(self.config.poll_interval_s)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(self.config.poll_interval_s)
        
        self.logger.info("Guardian monitoring stopped")
    
    async def start_http_server(self):
        """Starta HTTP server för health checks"""
        app = web.Application()
        app.router.add_get('/health', self.health_handler)
        app.router.add_get('/metrics', self.health_handler)  # Alias
        
        runner = web_runner.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, '127.0.0.1', self.config.guardian_port)
        await site.start()
        
        self.logger.info(f"Guardian HTTP server on :{self.config.guardian_port}")
    
    async def run(self):
        """Starta Guardian daemon"""
        self.logger.info("=== Alice System Guardian Starting ===")
        self.logger.info(f"Config: RAM soft={self.config.ram_soft_pct:.1%} hard={self.config.ram_hard_pct:.1%}")
        self.logger.info(f"        CPU soft={self.config.cpu_soft_pct:.1%} hard={self.config.cpu_hard_pct:.1%}")
        
        # Starta HTTP server
        await self.start_http_server()
        
        # Starta monitoring loop
        await self.run_monitoring_loop()

def main():
    """Entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s:%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/tmp/guardian.log')
        ]
    )
    
    # Skapa och starta Guardian
    guardian = SystemGuardian()
    
    try:
        asyncio.run(guardian.run())
    except KeyboardInterrupt:
        print("\\nGuardian stopped by user")
    except Exception as e:
        print(f"Guardian fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()