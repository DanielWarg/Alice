#!/usr/bin/env python3
"""
Alice Guardian - Graceful Killswitch Sequence
==============================================

Implementerar kontrollerad eskalering för Ollama shutdown:
1. Stoppa intake (429/"busy") + dränera kö i 5–10s
2. SIGTERM på endast `ollama serve`-PID (inte alla processer med "ollama" i cmdline)  
3. Vänta upp till 5s → om kvar: SIGKILL
4. systemd/Docker restart i stället för "bara starta binären"

Tekniska förbättringar vs `pkill -9 -f ollama`:
- Exakt PID-targeting: spara serve-PID vid start (PID-file)
- Selektiv process-matching: parent cmd `ollama serve`, inte "-f ollama" brett
- Sessioner först: försök `ollama ps` + stop per session innan daemon-kill
- Backoff på restart: 5s → 15s → 60s (exponentiellt)
- Health gate innan reopen: `/api/health/ready` + mini-prompt "2+2?" mot LLM
"""

import os
import sys
import json
import time
import signal
import asyncio
import logging
import subprocess
import psutil
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class KillSequenceConfig:
    """Configuration för graceful killswitch"""
    # Drain timing
    drain_timeout_s: float = 8.0        # Tid för att dränera kö
    sigterm_timeout_s: float = 5.0      # Vänta på graceful shutdown
    
    # PID file management
    pid_file_path: str = "/tmp/alice_ollama.pid"
    
    # Restart backoff (exponential)
    restart_delays: List[float] = None  # [5.0, 15.0, 60.0]
    max_restart_attempts: int = 3
    
    # Health gating
    health_check_url: str = "http://localhost:11434/api/health"
    llm_test_prompt: str = "2+2=?"
    health_timeout_s: float = 10.0
    
    # URLs
    alice_base_url: str = "http://localhost:3000"
    ollama_base_url: str = "http://localhost:11434"
    
    def __post_init__(self):
        if self.restart_delays is None:
            self.restart_delays = [5.0, 15.0, 60.0]

class OllamaSessionManager:
    """Hanterar Ollama sessions för graceful shutdown"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.logger = logging.getLogger("guardian.sessions")
    
    async def list_active_sessions(self) -> List[str]:
        """Lista aktiva modell-sessioner"""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/api/ps")
                if response.status_code == 200:
                    data = response.json()
                    models = [model.get('name', '') for model in data.get('models', [])]
                    self.logger.info(f"Active sessions: {models}")
                    return models
                else:
                    self.logger.warning(f"Failed to list sessions: {response.status_code}")
                    return []
        except Exception as e:
            self.logger.error(f"Session list failed: {e}")
            return []
    
    async def stop_session(self, model_name: str) -> bool:
        """Stoppa en specifik modell-session"""
        try:
            payload = {"model": model_name, "keep_alive": 0}
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                success = response.status_code == 200
                self.logger.info(f"Stop session {model_name}: {'OK' if success else 'FAILED'}")
                return success
        except Exception as e:
            self.logger.error(f"Stop session {model_name} failed: {e}")
            return False
    
    async def stop_all_sessions(self) -> bool:
        """Stoppa alla aktiva sessioner gracefully"""
        sessions = await self.list_active_sessions()
        if not sessions:
            self.logger.info("No active sessions to stop")
            return True
        
        success_count = 0
        for session in sessions:
            if await self.stop_session(session):
                success_count += 1
        
        all_stopped = success_count == len(sessions)
        self.logger.info(f"Stopped {success_count}/{len(sessions)} sessions")
        return all_stopped

class PIDTracker:
    """PID-tracking för exakt targeting av ollama serve"""
    
    def __init__(self, pid_file_path: str):
        self.pid_file_path = Path(pid_file_path)
        self.logger = logging.getLogger("guardian.pid_tracker")
    
    def save_serve_pid(self, pid: int) -> None:
        """Spara ollama serve PID till fil"""
        try:
            self.pid_file_path.write_text(str(pid))
            self.logger.info(f"Saved serve PID {pid} to {self.pid_file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save PID: {e}")
    
    def get_serve_pid(self) -> Optional[int]:
        """Hämta sparat ollama serve PID"""
        try:
            if self.pid_file_path.exists():
                pid = int(self.pid_file_path.read_text().strip())
                # Verifiera att processen fortfarande finns
                if self._is_valid_ollama_serve_pid(pid):
                    return pid
                else:
                    self.logger.warning(f"Stale PID {pid}, removing file")
                    self.pid_file_path.unlink()
            return None
        except Exception as e:
            self.logger.error(f"Failed to read PID: {e}")
            return None
    
    def _is_valid_ollama_serve_pid(self, pid: int) -> bool:
        """Verifiera att PID är en giltig ollama serve process"""
        try:
            proc = psutil.Process(pid)
            cmdline = proc.cmdline()
            # Kolla att det är "ollama serve" och inte något annat
            return (
                len(cmdline) >= 2 and 
                'ollama' in cmdline[0].lower() and 
                'serve' in cmdline[1].lower()
            )
        except (psutil.NoSuchProcess, IndexError):
            return False
    
    def find_serve_process(self) -> Optional[int]:
        """Hitta ollama serve process genom scanning"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline'] or []
                    if len(cmdline) >= 2:
                        if ('ollama' in cmdline[0].lower() and 
                            'serve' in cmdline[1].lower()):
                            pid = proc.info['pid']
                            self.logger.info(f"Found ollama serve at PID {pid}")
                            self.save_serve_pid(pid)
                            return pid
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    continue
            return None
        except Exception as e:
            self.logger.error(f"Process scanning failed: {e}")
            return None
    
    def clear_pid_file(self) -> None:
        """Rensa PID-fil efter shutdown"""
        try:
            if self.pid_file_path.exists():
                self.pid_file_path.unlink()
                self.logger.info("Cleared PID file")
        except Exception as e:
            self.logger.error(f"Failed to clear PID file: {e}")

class HealthGate:
    """Health gating innan återöppning av systemet"""
    
    def __init__(self, config: KillSequenceConfig):
        self.config = config
        self.logger = logging.getLogger("guardian.health_gate")
    
    async def check_ollama_health(self) -> bool:
        """Kontrollera Ollama API health"""
        try:
            async with httpx.AsyncClient(timeout=self.config.health_timeout_s) as client:
                response = await client.get(self.config.health_check_url)
                healthy = response.status_code == 200
                self.logger.info(f"Ollama health check: {'PASS' if healthy else 'FAIL'}")
                return healthy
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    async def test_llm_response(self) -> bool:
        """Mini-prompt test: '2+2=?' för att verifiera LLM funktion"""
        try:
            payload = {
                "model": "gpt-oss:20b",
                "prompt": self.config.llm_test_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 10
                }
            }
            
            async with httpx.AsyncClient(timeout=self.config.health_timeout_s) as client:
                response = await client.post(
                    f"{self.config.ollama_base_url}/api/generate",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get('response', '').strip()
                    # Enkel validering: borde innehålla "4" för 2+2
                    valid = '4' in response_text
                    self.logger.info(f"LLM test: {response_text} -> {'PASS' if valid else 'FAIL'}")
                    return valid
                else:
                    self.logger.error(f"LLM test failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"LLM test error: {e}")
            return False
    
    async def wait_for_ready(self, max_wait_s: float = 60.0) -> bool:
        """Vänta tills både health och LLM test passerar"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_s:
            # Steg 1: Grundläggande health
            if not await self.check_ollama_health():
                self.logger.info("Waiting for Ollama health...")
                await asyncio.sleep(2.0)
                continue
            
            # Steg 2: LLM funktionalitet
            if not await self.test_llm_response():
                self.logger.info("Waiting for LLM readiness...")
                await asyncio.sleep(3.0)
                continue
            
            # Båda testen passerade
            self.logger.info("Health gate: READY")
            return True
        
        self.logger.error(f"Health gate timeout after {max_wait_s}s")
        return False

class GracefulKillSequence:
    """
    Huvudklass för graceful killswitch-sekvens
    Ersätter den brutala `pkill -9 -f ollama` metoden
    """
    
    def __init__(self, config: KillSequenceConfig = None):
        self.config = config or KillSequenceConfig()
        self.logger = logging.getLogger("guardian.kill_sequence")
        
        # Komponenter
        self.session_manager = OllamaSessionManager(self.config.ollama_base_url)
        self.pid_tracker = PIDTracker(self.config.pid_file_path)
        self.health_gate = HealthGate(self.config)
        
        # Restart tracking
        self.restart_attempt = 0
        self.last_kill_time: Optional[datetime] = None
    
    async def stop_intake_and_drain(self) -> bool:
        """Steg 1: Stoppa intake och dränera kö"""
        self.logger.info("=== STEP 1: Stop intake and drain queue ===")
        
        try:
            # Stoppa nya requests (429/busy)
            url = f"{self.config.alice_base_url}/api/guard/stop-intake"
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(url)
                intake_stopped = response.status_code == 200
                self.logger.info(f"Intake stop: {'SUCCESS' if intake_stopped else 'FAILED'}")
            
            # Dränera befintlig kö
            self.logger.info(f"Draining queue for {self.config.drain_timeout_s}s...")
            await asyncio.sleep(self.config.drain_timeout_s)
            
            return intake_stopped
            
        except Exception as e:
            self.logger.error(f"Intake stop failed: {e}")
            return False
    
    async def graceful_session_shutdown(self) -> bool:
        """Steg 2a: Stoppa Ollama sessioner gracefully"""
        self.logger.info("=== STEP 2a: Graceful session shutdown ===")
        return await self.session_manager.stop_all_sessions()
    
    def targeted_process_kill(self) -> bool:
        """Steg 2b: Targeted SIGTERM/SIGKILL på ollama serve"""
        self.logger.info("=== STEP 2b: Targeted process termination ===")
        
        # Försök hitta PID (sparat eller genom scanning)
        serve_pid = self.pid_tracker.get_serve_pid()
        if serve_pid is None:
            serve_pid = self.pid_tracker.find_serve_process()
        
        if serve_pid is None:
            self.logger.warning("No ollama serve process found")
            return True  # Redan död
        
        try:
            proc = psutil.Process(serve_pid)
            
            # Försök SIGTERM först
            self.logger.info(f"Sending SIGTERM to PID {serve_pid}")
            proc.terminate()
            
            # Vänta på graceful shutdown
            try:
                proc.wait(timeout=self.config.sigterm_timeout_s)
                self.logger.info("Graceful termination successful")
                self.pid_tracker.clear_pid_file()
                return True
            except psutil.TimeoutExpired:
                # Timeout - använd SIGKILL
                self.logger.warning("SIGTERM timeout, using SIGKILL")
                proc.kill()
                proc.wait(timeout=2.0)
                self.logger.info("Force kill successful")
                self.pid_tracker.clear_pid_file()
                return True
                
        except psutil.NoSuchProcess:
            self.logger.info("Process already terminated")
            self.pid_tracker.clear_pid_file()
            return True
        except Exception as e:
            self.logger.error(f"Process termination failed: {e}")
            return False
    
    def smart_restart(self) -> bool:
        """Steg 3: Smart restart med backoff"""
        self.logger.info(f"=== STEP 3: Smart restart (attempt {self.restart_attempt + 1}) ===")
        
        if self.restart_attempt >= self.config.max_restart_attempts:
            self.logger.error("Max restart attempts reached")
            return False
        
        # Exponential backoff
        if self.restart_attempt < len(self.config.restart_delays):
            delay = self.config.restart_delays[self.restart_attempt]
        else:
            delay = self.config.restart_delays[-1]
        
        self.logger.info(f"Waiting {delay}s before restart...")
        time.sleep(delay)
        
        try:
            # Försök använda systemd/launchctl först (macOS)
            if sys.platform == "darwin":
                # På macOS, försök med launchctl om Ollama installerats som service
                try:
                    subprocess.run(
                        ["launchctl", "start", "com.ollama.ollama"],
                        check=True, capture_output=True, timeout=10
                    )
                    self.logger.info("Started via launchctl")
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Fallback till direkt start
                    pass
            
            # Direkt start som fallback
            ollama_path = "/Applications/Ollama.app/Contents/Resources/ollama"
            if not os.path.exists(ollama_path):
                # Försök med PATH
                ollama_path = "ollama"
            
            proc = subprocess.Popen(
                [ollama_path, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # Förhindra signal propagation
            )
            
            # Spara ny PID
            self.pid_tracker.save_serve_pid(proc.pid)
            self.logger.info(f"Started ollama serve with PID {proc.pid}")
            
            self.restart_attempt += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Restart failed: {e}")
            self.restart_attempt += 1
            return False
    
    async def execute_full_sequence(self) -> bool:
        """
        Utför hela graceful killswitch-sekvensen
        Returns: True om framgångsrik, False om något steg misslyckades
        """
        self.logger.info("=== EXECUTING GRACEFUL KILLSWITCH SEQUENCE ===")
        self.last_kill_time = datetime.now()
        
        # Steg 1: Stoppa intake och dränera
        if not await self.stop_intake_and_drain():
            self.logger.warning("Intake stop failed, continuing anyway")
        
        # Steg 2a: Graceful session shutdown
        sessions_stopped = await self.graceful_session_shutdown()
        if not sessions_stopped:
            self.logger.warning("Session shutdown incomplete, proceeding with process kill")
        
        # Kort paus för att låta sessioner stänga
        await asyncio.sleep(1.0)
        
        # Steg 2b: Process termination
        if not self.targeted_process_kill():
            self.logger.error("Process termination failed")
            return False
        
        # Steg 3: Smart restart
        if not self.smart_restart():
            self.logger.error("Restart failed")
            return False
        
        # Steg 4: Health gating
        self.logger.info("=== STEP 4: Health gating ===")
        if not await self.health_gate.wait_for_ready():
            self.logger.error("Health gate failed - system may not be fully ready")
            return False
        
        self.logger.info("=== GRACEFUL KILLSWITCH SEQUENCE COMPLETE ===")
        return True
    
    def reset_restart_counter(self) -> None:
        """Återställ restart counter efter framgångsrik körning"""
        if self.restart_attempt > 0:
            self.logger.info(f"Resetting restart counter (was {self.restart_attempt})")
            self.restart_attempt = 0
    
    def get_sequence_status(self) -> Dict[str, Any]:
        """Hämta status för killswitch-sekvensen"""
        return {
            "last_kill_time": self.last_kill_time.isoformat() if self.last_kill_time else None,
            "restart_attempts": self.restart_attempt,
            "max_attempts": self.config.max_restart_attempts,
            "serve_pid": self.pid_tracker.get_serve_pid(),
            "pid_file_exists": Path(self.config.pid_file_path).exists()
        }

# Convenience function för enkel användning
async def execute_graceful_killswitch(config: KillSequenceConfig = None) -> bool:
    """
    Convenience function för att utföra graceful killswitch
    Usage:
        success = await execute_graceful_killswitch()
    """
    sequence = GracefulKillSequence(config)
    return await sequence.execute_full_sequence()

if __name__ == "__main__":
    # Test/demo
    import logging
    logging.basicConfig(level=logging.INFO)
    
    async def test_sequence():
        config = KillSequenceConfig()
        success = await execute_graceful_killswitch(config)
        print(f"Graceful killswitch: {'SUCCESS' if success else 'FAILED'}")
    
    asyncio.run(test_sequence())