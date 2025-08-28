#!/usr/bin/env python3
"""
GPT-OSS:20B Evaluation Script with Killswitch
=====================================

Testar gpt-oss:20b prestanda över en minut med detaljerad monitoring och automatisk killswitch.

SÄKERHETSFUNKTIONER:
- RAM-övervakning med automatisk killswitch vid >90% användning
- TTFT-trösklar som automatiskt avbryter vid långsamma svar
- System load monitoring
- Emergeny exit vid Ctrl+C eller kritiska problem

Användning:
    python gpt_oss_evaluation.py [--duration 60] [--interval 10] [--ram-limit 90]
"""

import os
import sys
import time
import json
import signal
import argparse
import asyncio
import psutil
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import httpx

@dataclass 
class TestResult:
    timestamp: str
    request_text: str
    response_text: str
    ttft_ms: float
    total_time_ms: float
    ram_usage_gb: float
    ram_percent: float
    cpu_percent: float
    success: bool
    error: Optional[str] = None

class SafetyKillSwitch:
    """Säkerhetsystem som övervakar systemhälsa och kan avbryta testet"""
    
    def __init__(self, ram_limit_percent=90, ttft_limit_ms=30000, cpu_limit_percent=95):
        self.ram_limit_percent = ram_limit_percent
        self.ttft_limit_ms = ttft_limit_ms  
        self.cpu_limit_percent = cpu_limit_percent
        self.killed = False
        self.kill_reason = None
        
    def check_system_safety(self, ram_percent: float, cpu_percent: float, ttft_ms: float = None) -> tuple[bool, str]:
        """
        Kontrollerar systemsäkerhet. Returnerar (safe, reason)
        """
        if self.killed:
            return False, self.kill_reason
            
        # RAM Check
        if ram_percent >= self.ram_limit_percent:
            self.killed = True
            self.kill_reason = f"KRITISK: RAM användning {ram_percent:.1f}% >= {self.ram_limit_percent}%"
            return False, self.kill_reason
            
        # CPU Check  
        if cpu_percent >= self.cpu_limit_percent:
            self.killed = True
            self.kill_reason = f"KRITISK: CPU användning {cpu_percent:.1f}% >= {self.cpu_limit_percent}%"
            return False, self.kill_reason
            
        # TTFT Check
        if ttft_ms and ttft_ms >= self.ttft_limit_ms:
            self.killed = True
            self.kill_reason = f"KRITISK: TTFT {ttft_ms:.0f}ms >= {self.ttft_limit_ms}ms (modellen hänger)"
            return False, self.kill_reason
            
        return True, "OK"
    
    def emergency_kill(self, reason: str):
        """Nödstopp av testet"""
        self.killed = True
        self.kill_reason = f"NÖDSTOPP: {reason}"
        print(f"\\n🚨 {self.kill_reason}")

class GPTOSSEvaluator:
    """Huvudklass för utvärdering av GPT-OSS:20B prestanda"""
    
    def __init__(self, base_url="http://localhost:11434", model="gpt-oss:20b"):
        self.base_url = base_url
        self.model = model
        self.results: List[TestResult] = []
        self.safety = SafetyKillSwitch()
        self.start_time = None
        self.test_prompts = [
            "Hej, vad heter du?",
            "Förklara kort vad artificiell intelligens är.",
            "Räkna från 1 till 5 på svenska.",
            "Vad är huvudstaden i Sverige?",
            "Skriv en kort dikt om våren.",
            "Hur räknar man ut arean av en cirkel?",
            "Vad är skillnaden mellan AI och ML?",
            "Nämn tre svenska författare.",
            "Förklara kort hur en dator fungerar.",
            "Vad händer när man kokar vatten?"
        ]
        self.current_prompt_index = 0
        
        # Setup signal handlers för Ctrl+C
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Hanterar Ctrl+C och andra avbrott"""
        self.safety.emergency_kill("Användare avbröt testet (Ctrl+C)")
        
    def get_system_stats(self) -> tuple[float, float, float]:
        """Hämtar aktuell RAM och CPU användning"""
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        ram_gb = memory.used / (1024**3)
        ram_percent = memory.percent
        
        return ram_gb, ram_percent, cpu_percent
    
    async def test_single_request(self, prompt: str) -> TestResult:
        """Testar en enskild request med full monitoring"""
        timestamp = datetime.now().isoformat()
        ram_gb, ram_percent, cpu_percent = self.get_system_stats()
        
        # Säkerhetskontroll innan request
        safe, reason = self.safety.check_system_safety(ram_percent, cpu_percent)
        if not safe:
            return TestResult(
                timestamp=timestamp,
                request_text=prompt,
                response_text="",
                ttft_ms=0,
                total_time_ms=0,
                ram_usage_gb=ram_gb,
                ram_percent=ram_percent,
                cpu_percent=cpu_percent,
                success=False,
                error=reason
            )
        
        print(f"📤 Test: '{prompt[:50]}...' (RAM: {ram_percent:.1f}%, CPU: {cpu_percent:.1f}%)")
        
        start_time = time.time()
        ttft_recorded = False
        ttft_ms = 0
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "15m",  # Längre keep-alive för test
                "options": {
                    "temperature": 0.7,
                    "num_predict": 100  # Begränsa för testning
                }
            }
            
            timeout = httpx.Timeout(45.0)  # 45 sekunder timeout
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                ttft_ms = (time.time() - start_time) * 1000
                ttft_recorded = True
                
                # Säkerhetskontroll efter TTFT
                ram_gb, ram_percent, cpu_percent = self.get_system_stats()
                safe, reason = self.safety.check_system_safety(ram_percent, cpu_percent, ttft_ms)
                if not safe:
                    return TestResult(
                        timestamp=timestamp,
                        request_text=prompt,
                        response_text="",
                        ttft_ms=ttft_ms,
                        total_time_ms=(time.time() - start_time) * 1000,
                        ram_usage_gb=ram_gb,
                        ram_percent=ram_percent,
                        cpu_percent=cpu_percent,
                        success=False,
                        error=reason
                    )
                
                response.raise_for_status()
                result_data = response.json()
                response_text = result_data.get("response", "")
                
                total_time_ms = (time.time() - start_time) * 1000
                
                # Final säkerhetskontroll
                ram_gb, ram_percent, cpu_percent = self.get_system_stats()
                safe, reason = self.safety.check_system_safety(ram_percent, cpu_percent)
                if not safe:
                    return TestResult(
                        timestamp=timestamp,
                        request_text=prompt,
                        response_text=response_text,
                        ttft_ms=ttft_ms,
                        total_time_ms=total_time_ms,
                        ram_usage_gb=ram_gb,
                        ram_percent=ram_percent,
                        cpu_percent=cpu_percent,
                        success=False,
                        error=reason
                    )
                
                print(f"✅ Svar: {len(response_text)} chars, TTFT: {ttft_ms:.0f}ms, Total: {total_time_ms:.0f}ms")
                
                return TestResult(
                    timestamp=timestamp,
                    request_text=prompt,
                    response_text=response_text,
                    ttft_ms=ttft_ms,
                    total_time_ms=total_time_ms,
                    ram_usage_gb=ram_gb,
                    ram_percent=ram_percent,
                    cpu_percent=cpu_percent,
                    success=True
                )
                
        except Exception as e:
            total_time_ms = (time.time() - start_time) * 1000
            if not ttft_recorded:
                ttft_ms = total_time_ms
                
            ram_gb, ram_percent, cpu_percent = self.get_system_stats()
            
            print(f"❌ Fel: {e}")
            
            return TestResult(
                timestamp=timestamp,
                request_text=prompt,
                response_text="",
                ttft_ms=ttft_ms,
                total_time_ms=total_time_ms,
                ram_usage_gb=ram_gb,
                ram_percent=ram_percent,
                cpu_percent=cpu_percent,
                success=False,
                error=str(e)
            )
    
    def get_next_prompt(self) -> str:
        """Hämtar nästa testprompt i rotation"""
        prompt = self.test_prompts[self.current_prompt_index % len(self.test_prompts)]
        self.current_prompt_index += 1
        return prompt
    
    def print_live_stats(self):
        """Skriver ut live-statistik"""
        if not self.results:
            return
            
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        if successful:
            avg_ttft = sum(r.ttft_ms for r in successful) / len(successful)
            avg_total = sum(r.total_time_ms for r in successful) / len(successful)
            latest = self.results[-1]
            
            print(f"📊 Status: {len(successful)} lyckade, {len(failed)} misslyckade")
            print(f"   TTFT: {avg_ttft:.0f}ms avg, Total: {avg_total:.0f}ms avg")
            print(f"   RAM: {latest.ram_percent:.1f}%, CPU: {latest.cpu_percent:.1f}%\\n")
    
    async def run_evaluation(self, duration_seconds=60, interval_seconds=10) -> Dict[str, Any]:
        """Kör huvudutvärderingen"""
        print(f"🚀 Startar GPT-OSS:20B utvärdering")
        print(f"⏱️  Varaktighet: {duration_seconds}s, Intervall: {interval_seconds}s")
        print(f"🛡️  Säkerhetsgränser: RAM {self.safety.ram_limit_percent}%, CPU {self.safety.cpu_limit_percent}%, TTFT {self.safety.ttft_limit_ms/1000:.1f}s")
        print(f"🎯 Modell: {self.model}\\n")
        
        self.start_time = datetime.now()
        end_time = self.start_time + timedelta(seconds=duration_seconds)
        
        # Test av initial connectivity
        print("🔌 Testar anslutning till Ollama...")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    raise Exception(f"Ollama inte tillgänglig: {response.status_code}")
                print("✅ Ollama anslutning OK\\n")
        except Exception as e:
            print(f"❌ Kunde inte ansluta till Ollama: {e}")
            return {"error": f"Anslutningsfel: {e}"}
        
        # Huvudloop
        test_count = 0
        while datetime.now() < end_time and not self.safety.killed:
            test_count += 1
            prompt = self.get_next_prompt()
            
            # Kör test
            result = await self.test_single_request(prompt)
            self.results.append(result)
            
            # Kontrollera om test misslyckades pga säkerhet
            if not result.success and self.safety.killed:
                print(f"\\n🚨 AVBRYTER TESTNING: {result.error}")
                break
                
            # Visa live stats
            self.print_live_stats()
            
            # Vänta till nästa test (om tid finns kvar)
            if datetime.now() < end_time and not self.safety.killed:
                remaining = (end_time - datetime.now()).total_seconds()
                wait_time = min(interval_seconds, remaining)
                if wait_time > 0:
                    print(f"⏳ Väntar {wait_time:.1f}s till nästa test...")
                    await asyncio.sleep(wait_time)
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """Genererar slutrapport"""
        if not self.results:
            return {"error": "Inga testresultat att rapportera"}
            
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        # Beräkna statistik
        stats = {
            "test_count": len(self.results),
            "successful_count": len(successful),
            "failed_count": len(failed),
            "success_rate": len(successful) / len(self.results) * 100,
            "killed_by_safety": self.safety.killed,
            "kill_reason": self.safety.kill_reason
        }
        
        if successful:
            ttfts = [r.ttft_ms for r in successful]
            totals = [r.total_time_ms for r in successful]
            rams = [r.ram_percent for r in successful]
            cpus = [r.cpu_percent for r in successful]
            
            stats.update({
                "ttft_avg_ms": sum(ttfts) / len(ttfts),
                "ttft_min_ms": min(ttfts),
                "ttft_max_ms": max(ttfts),
                "total_avg_ms": sum(totals) / len(totals),
                "total_min_ms": min(totals),
                "total_max_ms": max(totals),
                "ram_avg_percent": sum(rams) / len(rams),
                "ram_max_percent": max(rams),
                "cpu_avg_percent": sum(cpus) / len(cpus),
                "cpu_max_percent": max(cpus)
            })
        
        # Bygg rapport
        report = {
            "timestamp": datetime.now().isoformat(),
            "model": self.model,
            "duration_actual": (datetime.now() - self.start_time).total_seconds(),
            "statistics": stats,
            "results": [
                {
                    "timestamp": r.timestamp,
                    "prompt": r.request_text[:100] + "..." if len(r.request_text) > 100 else r.request_text,
                    "response_length": len(r.response_text),
                    "ttft_ms": r.ttft_ms,
                    "total_ms": r.total_time_ms,
                    "ram_percent": r.ram_percent,
                    "cpu_percent": r.cpu_percent,
                    "success": r.success,
                    "error": r.error
                } for r in self.results
            ]
        }
        
        return report

def main():
    parser = argparse.ArgumentParser(description="GPT-OSS:20B Evaluation med säkerhetsfunktioner")
    parser.add_argument("--duration", type=int, default=60, help="Test duration i sekunder (default: 60)")
    parser.add_argument("--interval", type=int, default=10, help="Sekunder mellan tester (default: 10)")  
    parser.add_argument("--ram-limit", type=int, default=90, help="RAM gräns i procent (default: 90)")
    parser.add_argument("--ttft-limit", type=int, default=30, help="TTFT gräns i sekunder (default: 30)")
    parser.add_argument("--output", type=str, default="gpt_oss_evaluation_report.json", help="Output fil")
    
    args = parser.parse_args()
    
    # Skapa evaluator med anpassade gränser
    evaluator = GPTOSSEvaluator()
    evaluator.safety.ram_limit_percent = args.ram_limit
    evaluator.safety.ttft_limit_ms = args.ttft_limit * 1000
    
    try:
        # Kör asynkron evaluering
        report = asyncio.run(evaluator.run_evaluation(args.duration, args.interval))
        
        # Spara rapport
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Skriv slutrapport
        print(f"\\n📋 SLUTRAPPORT SPARAD: {args.output}")
        if "error" not in report:
            stats = report["statistics"]
            print(f"✅ Lyckade tester: {stats['successful_count']}/{stats['test_count']} ({stats['success_rate']:.1f}%)")
            if stats["successful_count"] > 0:
                print(f"⚡ TTFT genomsnitt: {stats['ttft_avg_ms']:.0f}ms (min: {stats['ttft_min_ms']:.0f}, max: {stats['ttft_max_ms']:.0f})")
                print(f"💾 RAM max: {stats['ram_max_percent']:.1f}%")
                print(f"🔥 CPU max: {stats['cpu_max_percent']:.1f}%")
            
            if stats["killed_by_safety"]:
                print(f"🚨 Test avbrutet: {stats['kill_reason']}")
        else:
            print(f"❌ Error: {report['error']}")
            
    except KeyboardInterrupt:
        print("\\n🛑 Test avbrutet av användare")
        sys.exit(1)
    except Exception as e:
        print(f"\\n💥 Kritiskt fel: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()