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
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque, Counter
from enum import Enum
import psutil
import httpx
from aiohttp import web, web_runner

# Import graceful killswitch
from .kill_sequence import GracefulKillSequence, KillSequenceConfig
from .brownout_manager import BrownoutManager

class GuardianState(Enum):
    """Guardian systemtillstånd med hysteresis"""
    NORMAL = "normal"
    BROWNOUT = "brownout"      # Intelligent degradation
    DEGRADED = "degraded"      # Basic degradation
    EMERGENCY = "emergency"    # Hard kill läge
    LOCKDOWN = "lockdown"      # Manual intervention required

@dataclass
class GuardianConfig:
    """Deterministisk konfiguration - inga AI-parametrar"""
    # Polling
    poll_interval_s: float = 1.0
    
    # Hysteresis trösklar (andel av total)
    ram_soft_pct: float = 0.85      # Mjuk degradation trigger
    ram_hard_pct: float = 0.92      # Hard kill trigger
    ram_recovery_pct: float = 0.75  # Recovery threshold (hysteresis)
    cpu_soft_pct: float = 0.85      # Mjuk degradation trigger 
    cpu_hard_pct: float = 0.92      # Hard kill trigger
    cpu_recovery_pct: float = 0.75  # Recovery threshold (hysteresis)
    disk_hard_pct: float = 0.95     # Hard kill
    temp_hard_c: float = 90.0       # Hard kill (om tillgänglig)
    
    # Hysteresis och flap detection
    measurement_window: int = 5     # Antal mätpunkter för trigger
    recovery_window_s: float = 60.0 # Återställningstid i sekunder
    flap_detection_window: int = 10 # Fönster för oscillation detection
    
    # Kill cooldown settings
    kill_cooldown_short_s: float = 300.0    # 5 min mellan kills
    kill_cooldown_long_s: float = 1800.0    # 30 min window för max kills
    max_kills_per_window: int = 3           # Max 3 kills per 30min
    lockdown_duration_s: float = 3600.0     # 1h lockdown efter överträdelse
    
    # Brownout settings
    brownout_model_primary: str = "gpt-oss:20b"
    brownout_model_fallback: str = "gpt-oss:7b"
    brownout_context_window: int = 8        # Normal context
    brownout_context_reduced: int = 3       # Reduced context
    brownout_rag_top_k: int = 8             # Normal RAG
    brownout_rag_reduced: int = 3           # Reduced RAG
    
    # Auto-tuning
    concurrency_adjustment_interval_s: float = 60.0  # Justering var 60s
    target_p95_latency_ms: float = 2000.0            # Target p95 latency
    concurrency_min: int = 1
    concurrency_max: int = 10
    
    # Åtgärder
    enable_unload_model: bool = True
    enable_stop_intake: bool = True  
    enable_kill_ollama: bool = True
    enable_brownout: bool = True
    enable_lockdown: bool = True
    
    # Endpoints
    alice_base_url: str = "http://localhost:8000"  # Updated to minimal server
    ollama_base_url: str = "http://localhost:11434"
    guardian_port: int = 8787

class GuardianActions:
    """Deterministiska åtgärder utan AI-logik"""
    
    def __init__(self, config: GuardianConfig):
        self.config = config
        self.logger = logging.getLogger("guardian.actions")
        
        # Graceful killswitch setup
        kill_config = KillSequenceConfig(
            alice_base_url=self.config.alice_base_url,
            ollama_base_url=self.config.ollama_base_url
        )
        self.graceful_killer = GracefulKillSequence(kill_config)
    
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
    
    async def kill_ollama_graceful(self) -> bool:
        """Graceful kill: använd ny killswitch-sekvens"""
        try:
            self.logger.warning("Executing graceful killswitch sequence")
            success = await self.graceful_killer.execute_full_sequence()
            if success:
                self.logger.info("Graceful killswitch completed successfully")
                # Reset restart counter på framgång
                self.graceful_killer.reset_restart_counter()
            else:
                self.logger.error("Graceful killswitch failed")
            return success
        except Exception as e:
            self.logger.error(f"Graceful killswitch error: {e}")
            return False
    
    def kill_ollama_legacy(self) -> bool:
        """Legacy hard kill: döda Ollama-processer (fallback)"""
        try:
            result = subprocess.run(
                ["pkill", "-9", "-f", "ollama"],
                capture_output=True, text=True, timeout=5
            )
            self.logger.warning(f"Legacy kill Ollama: return code {result.returncode}")
            return True
        except Exception as e:
            self.logger.error(f"Legacy kill Ollama failed: {e}")
            return False
    
    def restart_ollama_legacy(self) -> bool:
        """Legacy restart Ollama efter kill (används bara för fallback)"""
        try:
            # macOS: starta Ollama app eller serve
            subprocess.Popen(
                ["/Applications/Ollama.app/Contents/Resources/ollama", "serve"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            self.logger.info("Legacy restarting Ollama")
            return True
        except Exception as e:
            self.logger.error(f"Legacy restart Ollama failed: {e}")
            return False

class SystemGuardian:
    """Huvudklassen - deterministisk övervakare med hysteresis och brownout"""
    
    def __init__(self, config: GuardianConfig = None):
        self.config = config or GuardianConfig()
        self.actions = GuardianActions(self.config)
        self.logger = logging.getLogger("guardian")
        
        # State machine
        self.state = GuardianState.NORMAL
        self.previous_state = GuardianState.NORMAL
        self.state_change_time = datetime.now()
        self.startup_time = datetime.now()
        
        # Hysteresis measurement windows
        self.ram_measurements = deque(maxlen=self.config.measurement_window)
        self.cpu_measurements = deque(maxlen=self.config.measurement_window)
        
        # Kill tracking för cooldown
        self.kill_history = deque(maxlen=20)  # Track last 20 kills
        self.lockdown_until: Optional[datetime] = None
        
        # Flap detection
        self.state_history = deque(maxlen=self.config.flap_detection_window)
        
        # Brownout manager
        self.brownout_manager = BrownoutManager(self.config)
        
        # Auto-tuning state
        self.current_concurrency = 5  # Start with middle value
        self.last_concurrency_adjustment = datetime.now()
        self.latency_history = deque(maxlen=100)  # Track latencies
        
        # Metrics history (för trend - ej AI)
        self.metrics_history = []
        self.max_history = 300  # 5 minuter vid 1s polling
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
        
        self.logger.info(f"Guardian initialized with hysteresis: RAM {self.config.ram_soft_pct:.1%}/{self.config.ram_recovery_pct:.1%}")
    
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
    
    def _check_lockdown_status(self) -> bool:
        """Kontrollera om vi är i lockdown-läge"""
        if self.lockdown_until and datetime.now() < self.lockdown_until:
            return True
        elif self.lockdown_until and datetime.now() >= self.lockdown_until:
            self.logger.info("Lockdown period expired, returning to normal operations")
            
            # NDJSON logging för lockdown expiry
            expiry_event = {
                'timestamp': datetime.now().isoformat(),
                'event': 'lockdown_expired',
                'lockdown_duration_s': (datetime.now() - (self.lockdown_until - timedelta(seconds=self.config.lockdown_duration_s))).total_seconds(),
                'returning_to_normal': True
            }
            print(json.dumps(expiry_event, separators=(',', ':')))
            
            self.lockdown_until = None
            self.state = GuardianState.NORMAL
            return False
        return False
    
    def _check_kill_cooldown(self) -> Tuple[bool, str]:
        """Kontrollera kill cooldown regler"""
        now = datetime.now()
        
        # Rensa gamla kills
        cutoff_long = now - timedelta(seconds=self.config.kill_cooldown_long_s)
        self.kill_history = deque(
            [t for t in self.kill_history if t > cutoff_long],
            maxlen=20
        )
        
        # Kontrollera kort cooldown (5 min)
        if self.kill_history:
            last_kill = max(self.kill_history)
            time_since_last = (now - last_kill).total_seconds()
            if time_since_last < self.config.kill_cooldown_short_s:
                return False, f"Kill on cooldown for {self.config.kill_cooldown_short_s - time_since_last:.0f}s"
        
        # Kontrollera max kills per window (30 min)
        kills_in_window = len(self.kill_history)
        if kills_in_window >= self.config.max_kills_per_window:
            # Aktivera lockdown
            self.lockdown_until = now + timedelta(seconds=self.config.lockdown_duration_s)
            self.state = GuardianState.LOCKDOWN
            
            # NDJSON logging för lockdown
            lockdown_event = {
                'timestamp': now.isoformat(),
                'event': 'lockdown_activated',
                'reason': f'max_kills_reached ({self.config.max_kills_per_window})',
                'lockdown_until': self.lockdown_until.isoformat(),
                'lockdown_duration_s': self.config.lockdown_duration_s,
                'kills_in_window': kills_in_window,
                'kill_history': [t.isoformat() for t in list(self.kill_history)]
            }
            print(json.dumps(lockdown_event, separators=(',', ':')))
            
            return False, f"Max kills ({self.config.max_kills_per_window}) reached, entering lockdown until {self.lockdown_until}"
        
        return True, "Kill allowed"
    
    def _detect_flapping(self) -> bool:
        """Detektera oscillation mellan tillstånd"""
        if len(self.state_history) < self.config.flap_detection_window:
            return False
        
        # Räkna antal tillståndsändringar
        changes = 0
        for i in range(1, len(self.state_history)):
            if self.state_history[i] != self.state_history[i-1]:
                changes += 1
        
        # Om fler än hälften av fönstret är ändringar, det är flapping
        flap_threshold = self.config.flap_detection_window // 2
        return changes > flap_threshold
    
    def _transition_state(self, new_state: GuardianState, reason: str) -> None:
        """Byt tillstånd med logging och flap detection"""
        if new_state == self.state:
            return
        
        # Logga övergång
        self.logger.info(f"State transition: {self.state.value} -> {new_state.value} ({reason})")
        
        # Uppdatera history
        self.state_history.append(new_state)
        
        # Kontrollera flapping
        if self._detect_flapping():
            self.logger.warning("Flapping detected, forcing BROWNOUT to stabilize")
            new_state = GuardianState.BROWNOUT
        
        # Uppdatera state
        self.previous_state = self.state
        self.state = new_state
        self.state_change_time = datetime.now()
    
    async def evaluate_and_act(self, metrics: Dict[str, Any]) -> None:
        """
        Hysteresis-baserad regelmotor med intelligent degradation
        """
        if 'error' in metrics:
            return
        
        # Kontrollera lockdown status
        if self._check_lockdown_status():
            return  # Ingen action tillåten under lockdown
        
        ram_pct = metrics.get('ram_pct', 0)
        cpu_pct = metrics.get('cpu_pct', 0) 
        disk_pct = metrics.get('disk_pct', 0)
        temp_c = metrics.get('temp_c', 0)
        
        # Uppdatera measurement windows
        self.ram_measurements.append(ram_pct)
        self.cpu_measurements.append(cpu_pct)
        
        # === HYSTERESIS LOGIC ===
        
        # Kontrollera för emergency (hård trigger - omedelbar)
        hard_trigger = (
            ram_pct >= self.config.ram_hard_pct or
            cpu_pct >= self.config.cpu_hard_pct or
            disk_pct >= self.config.disk_hard_pct or
            (temp_c > 0 and temp_c >= self.config.temp_hard_c)
        )
        
        if hard_trigger and self.state != GuardianState.EMERGENCY:
            # Emergency är omedelbar - ingen hysteresis
            self._transition_state(GuardianState.EMERGENCY, 
                f"Hard trigger: RAM={ram_pct:.1%} CPU={cpu_pct:.1%} DISK={disk_pct:.1%} TEMP={temp_c}°C")
            await self._handle_emergency_state()
            return
        
        # Kontrollera för soft degradation (kräver 5 mätpunkter)
        if len(self.ram_measurements) >= self.config.measurement_window and len(self.cpu_measurements) >= self.config.measurement_window:
            
            # Soft trigger: 5 mätpunkter i rad över tröskel
            ram_over_soft = all(m >= self.config.ram_soft_pct for m in self.ram_measurements)
            cpu_over_soft = all(m >= self.config.cpu_soft_pct for m in self.cpu_measurements)
            soft_trigger = ram_over_soft or cpu_over_soft
            
            # Recovery: under recovery tröskel i 60 sekunder
            recovery_time = datetime.now() - self.state_change_time
            ram_recovered = all(m < self.config.ram_recovery_pct for m in self.ram_measurements)
            cpu_recovered = all(m < self.config.cpu_recovery_pct for m in self.cpu_measurements)
            recovery_trigger = (ram_recovered and cpu_recovered and 
                              recovery_time.total_seconds() >= self.config.recovery_window_s)
            
            # State transitions baserat på current state
            if self.state == GuardianState.NORMAL:
                if soft_trigger:
                    if self.config.enable_brownout:
                        self._transition_state(GuardianState.BROWNOUT, 
                            f"Soft trigger: RAM 5pt avg={sum(self.ram_measurements)/len(self.ram_measurements):.1%}, CPU 5pt avg={sum(self.cpu_measurements)/len(self.cpu_measurements):.1%}")
                        await self._handle_brownout_state()
                    else:
                        self._transition_state(GuardianState.DEGRADED, "Soft trigger, brownout disabled")
                        await self._handle_degraded_state()
            
            elif self.state in [GuardianState.BROWNOUT, GuardianState.DEGRADED]:
                if recovery_trigger:
                    self._transition_state(GuardianState.NORMAL, "Recovery conditions met")
                    await self._handle_normal_state()
                elif hard_trigger:
                    # Escalation från brownout/degraded till emergency
                    self._transition_state(GuardianState.EMERGENCY, "Escalation to emergency")
                    await self._handle_emergency_state()
            
            elif self.state == GuardianState.EMERGENCY:
                if recovery_trigger:
                    self._transition_state(GuardianState.NORMAL, "Emergency recovery")
                    await self._handle_normal_state()
    
    async def _handle_normal_state(self) -> None:
        """Hantera normal state - återställ alla restriktioner"""
        self.logger.info("Returning to NORMAL state")
        
        # Återställ brownout settings
        if self.config.enable_brownout:
            await self.brownout_manager.restore_normal_operation()
        
        # Starta intake om det var stoppat
        try:
            url = f"{self.config.alice_base_url}/api/guard/resume-intake"
            async with httpx.AsyncClient(timeout=2.0) as client:
                await client.post(url)
        except Exception as e:
            self.logger.warning(f"Failed to resume intake: {e}")
    
    async def _handle_brownout_state(self) -> None:
        """Hantera brownout state - intelligent feature degradation"""
        self.logger.warning("Entering BROWNOUT state - intelligent degradation")
        
        if self.config.enable_brownout:
            success = await self.brownout_manager.activate_brownout_mode()
            if not success:
                self.logger.error("Brownout activation failed, falling back to basic degradation")
                await self._handle_degraded_state()
    
    async def _handle_degraded_state(self) -> None:
        """Hantera degraded state - basic degradation"""
        self.logger.warning("Entering DEGRADED state - basic degradation")
        
        # Basic degradation
        await self.actions.degrade()
        await self.actions.unload_model()
    
    async def _handle_emergency_state(self) -> None:
        """Hantera emergency state - hard kill med cooldown"""
        self.logger.error("Entering EMERGENCY state - hard kill sequence")
        
        # Kontrollera kill cooldown
        can_kill, reason = self._check_kill_cooldown()
        if not can_kill:
            self.logger.error(f"Kill blocked: {reason}")
            if self.state != GuardianState.LOCKDOWN:
                # NDJSON logging för cooldown block
                cooldown_event = {
                    'timestamp': datetime.now().isoformat(),
                    'event': 'kill_blocked_cooldown',
                    'reason': reason,
                    'kills_in_window': len(self.kill_history),
                    'fallback_strategy': 'brownout' if self.config.enable_brownout else 'degraded'
                }
                print(json.dumps(cooldown_event, separators=(',', ':')))
                
                # Om vi inte kan killa, falla tillbaka till brownout/degraded
                self._transition_state(GuardianState.BROWNOUT if self.config.enable_brownout else GuardianState.DEGRADED, 
                                     "Kill cooldown active, using degradation instead")
                if self.config.enable_brownout:
                    await self.brownout_manager.activate_brownout_mode()
                else:
                    await self._handle_degraded_state()
            return
        
        # Stoppa intake
        if self.config.enable_stop_intake:
            await self.actions.stop_intake()
        
        # Utför kill med graceful sequence
        if self.config.enable_kill_ollama:
            await self.actions.unload_model()
            await asyncio.sleep(1)
            
            kill_success = False
            try:
                if await self.actions.kill_ollama_graceful():
                    kill_success = True
                    self.logger.info("Graceful killswitch completed")
                else:
                    self.logger.error("Graceful killswitch failed, trying legacy")
                    if self.actions.kill_ollama_legacy():
                        kill_success = True
                        await asyncio.sleep(3)
                        self.actions.restart_ollama_legacy()
            except Exception as e:
                self.logger.error(f"Kill sequence error: {e}")
                if self.actions.kill_ollama_legacy():
                    kill_success = True
                    await asyncio.sleep(3)
                    self.actions.restart_ollama_legacy()
            
            if kill_success:
                # Registrera kill för cooldown tracking
                self.kill_history.append(datetime.now())
                self.logger.info(f"Kill registered. Total kills in window: {len(self.kill_history)}")
    
    async def health_handler(self, request):
        """HTTP health check endpoint med hysteresis info"""
        metrics = self.get_system_metrics()
        
        # Hämta killswitch status
        killswitch_status = self.actions.graceful_killer.get_sequence_status()
        
        # Hysteresis status
        hysteresis_status = {
            'ram_measurements': list(self.ram_measurements),
            'cpu_measurements': list(self.cpu_measurements),
            'measurement_window_full': len(self.ram_measurements) >= self.config.measurement_window,
            'flap_detected': self._detect_flapping(),
            'state_history': [s.value for s in list(self.state_history)]
        }
        
        # Kill cooldown status
        can_kill, kill_reason = self._check_kill_cooldown()
        cooldown_status = {
            'can_kill': can_kill,
            'reason': kill_reason,
            'kills_in_window': len(self.kill_history),
            'lockdown_until': self.lockdown_until.isoformat() if self.lockdown_until else None
        }
        
        # Brownout status
        brownout_status = await self.brownout_manager.get_status() if self.config.enable_brownout else None
        
        status = {
            'status': self.state.value,
            'previous_state': self.previous_state.value,
            'uptime_s': (datetime.now() - self.startup_time).total_seconds(),
            'state_duration_s': (datetime.now() - self.state_change_time).total_seconds(),
            'metrics': metrics,
            'killswitch': killswitch_status,
            'hysteresis': hysteresis_status,
            'cooldown': cooldown_status,
            'brownout': brownout_status,
            'auto_tuning': {
                'current_concurrency': self.current_concurrency,
                'target_p95_ms': self.config.target_p95_latency_ms,
                'recent_latencies': list(self.latency_history)[-10:] if self.latency_history else []
            }
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
                
                # Deterministisk evaluering med hysteresis
                await self.evaluate_and_act(metrics)
                
                # Auto-tuning check
                await self._check_auto_tuning()
                
                # Vänta till nästa cykel
                await asyncio.sleep(self.config.poll_interval_s)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(self.config.poll_interval_s)
        
        self.logger.info("Guardian monitoring stopped")
    
    async def _check_auto_tuning(self) -> None:
        """Auto-tuning av concurrency baserat på latency"""
        now = datetime.now()
        time_since_adjustment = (now - self.last_concurrency_adjustment).total_seconds()
        
        if time_since_adjustment < self.config.concurrency_adjustment_interval_s:
            return
        
        if len(self.latency_history) < 10:  # Behöver tillräckligt med data
            return
        
        # Beräkna p95 latency
        sorted_latencies = sorted(self.latency_history)
        p95_index = int(0.95 * len(sorted_latencies))
        current_p95 = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1]
        
        # Justera concurrency baserat på p95
        adjustment = 0
        if current_p95 > self.config.target_p95_latency_ms:
            # Latency för hög - minska concurrency
            adjustment = -1
            reason = f"p95 {current_p95:.0f}ms > target {self.config.target_p95_latency_ms:.0f}ms"
        elif current_p95 < self.config.target_p95_latency_ms * 0.7:
            # Latency låg - öka concurrency
            adjustment = 1
            reason = f"p95 {current_p95:.0f}ms < target {self.config.target_p95_latency_ms * 0.7:.0f}ms"
        
        if adjustment != 0:
            new_concurrency = max(
                self.config.concurrency_min,
                min(self.config.concurrency_max, self.current_concurrency + adjustment)
            )
            
            if new_concurrency != self.current_concurrency:
                old_concurrency = self.current_concurrency
                self.current_concurrency = new_concurrency
                self.last_concurrency_adjustment = now
                
                # Skicka till Alice server
                try:
                    url = f"{self.config.alice_base_url}/api/guard/set-concurrency"
                    payload = {"concurrency": self.current_concurrency}
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        response = await client.post(url, json=payload)
                        if response.status_code == 200:
                            self.logger.info(f"Auto-tuning: concurrency {old_concurrency} -> {new_concurrency} ({reason})")
                        else:
                            self.logger.warning(f"Failed to set concurrency: {response.status_code}")
                except Exception as e:
                    self.logger.error(f"Auto-tuning request failed: {e}")
    
    async def manual_override_lockdown(self, request) -> web.Response:
        """Manual override för lockdown-läge"""
        if self.state != GuardianState.LOCKDOWN:
            return web.json_response({"error": "Not in lockdown state"}, status=400)
        
        # Kräv bekräftelse
        data = await request.json() if request.content_type == 'application/json' else {}
        confirmation = data.get('confirm_override', False)
        
        if not confirmation:
            return web.json_response({
                "error": "Manual override requires confirmation", 
                "lockdown_until": self.lockdown_until.isoformat() if self.lockdown_until else None,
                "kills_in_window": len(self.kill_history),
                "required_payload": {"confirm_override": True}
            }, status=400)
        
        # Återställ lockdown
        self.lockdown_until = None
        self.kill_history.clear()  # Rensa kill history
        self._transition_state(GuardianState.NORMAL, "Manual override")
        
        self.logger.warning("MANUAL OVERRIDE: Lockdown cleared by administrator")
        
        return web.json_response({
            "status": "success",
            "message": "Lockdown cleared, returning to normal operations",
            "new_state": self.state.value
        })
    
    async def start_http_server(self):
        """Starta HTTP server för health checks"""
        app = web.Application()
        app.router.add_get('/health', self.health_handler)
        app.router.add_get('/metrics', self.health_handler)  # Alias
        app.router.add_post('/override-lockdown', self.manual_override_lockdown)
        
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