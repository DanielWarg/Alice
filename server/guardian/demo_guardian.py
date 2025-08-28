#!/usr/bin/env python3
"""
Guardian Hysteresis & Brownout Demo
===================================

Demonstrerar Guardian's hysteresis, cooldown och brownout-funktioner.
Simulerar olika belastningsscenarier för att visa:

1. Hysteresis: 5-point measurements för triggers
2. Cooldown: Kill rate limiting
3. Brownout: Intelligent degradation före kill
4. Lockdown: Automatisk lockdown vid överträdelser
5. Auto-tuning: Concurrency adjustment
6. NDJSON logging: Strukturerad spårning

Användning:
    python demo_guardian.py [scenario]
    
Scenarios:
    - normal: Normal operation
    - soft_trigger: Simulera mjuk överbelastning (brownout)
    - hard_trigger: Simulera hård överbelastning (kill)
    - flapping: Simulera oscillerande system
    - cooldown_test: Testa kill cooldown logik
    - lockdown_test: Triggra lockdown scenario
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from guardian.guardian import SystemGuardian, GuardianConfig, GuardianState
from guardian.brownout_manager import BrownoutManager, BrownoutLevel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s:%(levelname)s] %(message)s'
)

class MetricsSimulator:
    """Simulera systemmetriker för demo"""
    
    def __init__(self):
        self.base_ram = 0.70  # 70% normal baseline
        self.base_cpu = 0.65  # 65% normal baseline
        self.noise_factor = 0.05
        self.scenario = "normal"
        self.time_offset = 0
    
    def set_scenario(self, scenario: str, time_offset: float = 0):
        """Sätt simuleringsscenario"""
        self.scenario = scenario
        self.time_offset = time_offset
        logging.info(f"📊 Scenario: {scenario} (time offset: {time_offset:.1f}s)")
    
    def get_metrics(self) -> dict:
        """Generera simulerade metriker"""
        import random
        
        # Base noise
        ram_noise = random.uniform(-self.noise_factor, self.noise_factor)
        cpu_noise = random.uniform(-self.noise_factor, self.noise_factor)
        
        # Scenario-based adjustments
        if self.scenario == "normal":
            ram_pct = self.base_ram + ram_noise
            cpu_pct = self.base_cpu + cpu_noise
            
        elif self.scenario == "soft_trigger":
            # Gradual increase to trigger brownout
            ramp = min(self.time_offset / 10.0, 0.20)  # 20% increase over 10s
            ram_pct = self.base_ram + ramp + ram_noise
            cpu_pct = self.base_cpu + ramp + cpu_noise
            
        elif self.scenario == "hard_trigger":
            # Immediate spike to trigger kill
            ram_pct = 0.95 + ram_noise  # 95% RAM
            cpu_pct = 0.93 + cpu_noise  # 93% CPU
            
        elif self.scenario == "flapping":
            # Oscillate between normal and high
            cycle = (self.time_offset % 6.0) / 6.0  # 6s cycle
            if cycle < 0.5:
                ram_pct = 0.88 + ram_noise  # High
                cpu_pct = 0.87 + cpu_noise
            else:
                ram_pct = self.base_ram + ram_noise  # Normal
                cpu_pct = self.base_cpu + cpu_noise
                
        elif self.scenario == "recovery":
            # Gradual decrease for recovery simulation
            decay = max(0, 0.25 - (self.time_offset / 20.0))  # Decay over 20s
            ram_pct = self.base_ram + decay + ram_noise
            cpu_pct = self.base_cpu + decay + cpu_noise
            
        else:  # Default to normal
            ram_pct = self.base_ram + ram_noise
            cpu_pct = self.base_cpu + cpu_noise
        
        # Clamp values
        ram_pct = max(0.0, min(1.0, ram_pct))
        cpu_pct = max(0.0, min(1.0, cpu_pct))
        
        return {
            'timestamp': datetime.now().isoformat(),
            'ram_pct': ram_pct,
            'cpu_pct': cpu_pct,
            'disk_pct': 0.45,  # Static
            'temp_c': 0.0,     # Not simulated
            'ram_gb': ram_pct * 32.0,  # Assume 32GB system
            'ollama_pids': [12345] if self.scenario != "killed" else [],
            'degraded': False,
            'intake_blocked': False,
            'emergency_mode': False
        }

class GuardianDemo:
    """Demo harness för Guardian testing"""
    
    def __init__(self):
        # Demo-anpassad konfiguration
        self.config = GuardianConfig(
            # Snabbare polling för demo
            poll_interval_s=0.5,
            
            # Lägre trösklar för demo
            ram_soft_pct=0.85,
            ram_hard_pct=0.92,
            ram_recovery_pct=0.75,
            cpu_soft_pct=0.85,
            cpu_hard_pct=0.92,
            cpu_recovery_pct=0.75,
            
            # Kortare hysteresis för demo
            measurement_window=3,  # 3 measurements instead of 5
            recovery_window_s=6.0, # 6s instead of 60s
            
            # Kortare cooldowns för demo
            kill_cooldown_short_s=10.0,  # 10s instead of 5min
            kill_cooldown_long_s=30.0,   # 30s instead of 30min
            max_kills_per_window=2,      # 2 kills instead of 3
            lockdown_duration_s=20.0,    # 20s instead of 1h
            
            # Brownout settings
            enable_brownout=True,
            enable_lockdown=True,
            
            # Mock URLs för demo (won't actually call)
            alice_base_url="http://demo-alice:8000",
            ollama_base_url="http://demo-ollama:11434",
            guardian_port=8788  # Different port
        )
        
        self.metrics_simulator = MetricsSimulator()
        self.guardian = None
        self.demo_running = False
        
    async def run_scenario(self, scenario: str, duration_s: float = 30.0):
        """Kör ett specifikt scenario"""
        print(f"\n🎬 STARTING SCENARIO: {scenario.upper()}")
        print(f"Duration: {duration_s}s")
        print("=" * 60)
        
        # Initialize Guardian with mock
        self.guardian = MockGuardian(self.config)
        
        # Set scenario
        self.metrics_simulator.set_scenario(scenario)
        
        # Run simulation
        start_time = time.time()
        self.demo_running = True
        
        try:
            while self.demo_running and (time.time() - start_time) < duration_s:
                # Update time offset
                self.metrics_simulator.time_offset = time.time() - start_time
                
                # Generate metrics
                metrics = self.metrics_simulator.get_metrics()
                
                # Feed to Guardian
                await self.guardian.process_metrics(metrics)
                
                # Print status
                self._print_status(metrics)
                
                await asyncio.sleep(self.config.poll_interval_s)
                
        except KeyboardInterrupt:
            print("\n🛑 Demo interrupted by user")
        
        print(f"\n🏁 SCENARIO COMPLETE: {scenario.upper()}")
        self._print_summary()
        
    def _print_status(self, metrics: dict):
        """Skriv ut aktuell status"""
        ram_pct = metrics['ram_pct'] * 100
        cpu_pct = metrics['cpu_pct'] * 100
        state = self.guardian.state.value if self.guardian else "unknown"
        
        # Color coding
        ram_color = "🔴" if ram_pct > 92 else "🟡" if ram_pct > 85 else "🟢"
        cpu_color = "🔴" if cpu_pct > 92 else "🟡" if cpu_pct > 85 else "🟢"
        
        status_line = (f"⏱️  {datetime.now().strftime('%H:%M:%S')} | "
                      f"State: {state.upper():10} | "
                      f"RAM: {ram_color}{ram_pct:5.1f}% | "
                      f"CPU: {cpu_color}{cpu_pct:5.1f}% | "
                      f"Measurements: {len(self.guardian.ram_measurements)}")\n        
        print(status_line)
        
    def _print_summary(self):
        """Skriv ut sammanfattning"""
        if not self.guardian:
            return
            
        print("\\n📊 DEMO SUMMARY:")
        print(f"Final State: {self.guardian.state.value}")
        print(f"State Transitions: {len(self.guardian.state_history)}")
        print(f"Kill History: {len(self.guardian.kill_history)}")
        
        if self.config.enable_brownout:
            brownout_stats = self.guardian.brownout_manager.degradation_stats
            print(f"Brownout Activations: {brownout_stats['activations']}")
            print(f"Model Switches: {brownout_stats['model_switches']}")
        
        print(f"Lockdown Until: {self.guardian.lockdown_until}")

class MockGuardian(SystemGuardian):
    """Mock Guardian för demo utan verkliga API calls"""
    
    def __init__(self, config):
        # Initialize without actual signal handlers
        self.config = config
        self.state = GuardianState.NORMAL
        self.previous_state = GuardianState.NORMAL
        self.state_change_time = datetime.now()
        
        # Hysteresis
        self.ram_measurements = []
        self.cpu_measurements = []
        
        # Kill tracking
        self.kill_history = []
        self.lockdown_until = None
        
        # State tracking
        self.state_history = []
        
        # Mock brownout manager
        self.brownout_manager = MockBrownoutManager(config)
        
        self.logger = logging.getLogger("demo.guardian")
        
    async def process_metrics(self, metrics: dict):
        """Process simulated metrics"""
        await self.evaluate_and_act(metrics)
        
        # Mock any additional processing
        await asyncio.sleep(0.01)  # Simulate processing time

class MockBrownoutManager:
    """Mock Brownout Manager för demo"""
    
    def __init__(self, config):
        self.brownout_active = False
        self.current_level = BrownoutLevel.NONE
        self.degradation_stats = {
            'activations': 0,
            'model_switches': 0,
            'context_reductions': 0,
            'toolchain_disables': 0,
            'total_brownout_time_s': 0.0
        }
        self.logger = logging.getLogger("demo.brownout")
        
    async def activate_brownout_mode(self, level=BrownoutLevel.MODERATE):
        """Mock brownout activation"""
        self.brownout_active = True
        self.current_level = level
        self.degradation_stats['activations'] += 1
        self.logger.info(f"🟡 MOCK: Brownout activated (level: {level.name})")
        return True
        
    async def restore_normal_operation(self):
        """Mock brownout restoration"""
        self.brownout_active = False
        self.current_level = BrownoutLevel.NONE
        self.logger.info("🟢 MOCK: Normal operation restored")
        return True
        
    async def get_status(self):
        """Mock status"""
        return {
            'active': self.brownout_active,
            'level': self.current_level.name,
            'stats': self.degradation_stats.copy()
        }

async def main():
    """Huvudfunktion för demo"""
    demo = GuardianDemo()
    
    scenarios = {
        'normal': ("Normal operation", 15.0),
        'soft_trigger': ("Soft trigger → Brownout", 20.0),
        'hard_trigger': ("Hard trigger → Emergency kill", 15.0),
        'flapping': ("Flapping/oscillation detection", 25.0),
        'cooldown_test': ("Kill cooldown testing", 20.0),
        'lockdown_test': ("Lockdown activation", 30.0)
    }
    
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
        if scenario in scenarios:
            desc, duration = scenarios[scenario]
            print(f"🎯 Running scenario: {desc}")
            await demo.run_scenario(scenario, duration)
        else:
            print(f"❌ Unknown scenario: {scenario}")
            print("Available scenarios:", ", ".join(scenarios.keys()))
            sys.exit(1)
    else:
        print("🎮 Guardian Hysteresis & Brownout Demo")
        print("=" * 40)
        print("Available scenarios:")
        for name, (desc, duration) in scenarios.items():
            print(f"  {name:15} - {desc} ({duration}s)")
        print("\\nUsage: python demo_guardian.py <scenario>")

if __name__ == "__main__":
    asyncio.run(main())