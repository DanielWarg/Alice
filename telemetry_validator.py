#!/usr/bin/env python3
"""
Alice Telemetry Validator
========================

Verifierar CPU/RAM telemetri accuracy under realistisk belastning.
Identifierar orealistiska readings som "cpu_pct: 0.0" under 10+ RPS.
"""

import asyncio
import aiohttp
import psutil
import time
import json
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telemetry_validator")

@dataclass
class TelemetryReading:
    """En telemetri reading med timestamp"""
    timestamp: datetime
    cpu_percent: float
    ram_percent: float
    requests_per_second: float
    source: str  # 'guardian', 'system', 'validator'

@dataclass
class ValidationResult:
    """Resultat från telemetri validering"""
    accuracy_score: float
    suspicious_readings: int
    zero_cpu_under_load: int
    realistic_telemetry: bool
    recommendations: List[str]

class TelemetryValidator:
    """Validerar Alice systemets telemetri mot faktiska system readings"""
    
    def __init__(self, guardian_url: str = "http://localhost:8787", 
                 alice_url: str = "http://localhost:8000"):
        self.guardian_url = guardian_url
        self.alice_url = alice_url
        self.readings: List[TelemetryReading] = []
        self.load_generator_active = False
        
    async def collect_system_telemetry(self, duration_minutes: int = 30) -> List[TelemetryReading]:
        """Samla systemtelemetri över specificerad tid"""
        logger.info(f"🔍 Starting {duration_minutes}min telemetry collection...")
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        readings = []
        
        while datetime.now() < end_time:
            # Samla faktisk system telemetri
            cpu_percent = psutil.cpu_percent(interval=1)
            ram_percent = psutil.virtual_memory().percent
            
            # Estimera RPS från senaste minuten (enkel implementation)
            rps = await self._estimate_current_rps()
            
            reading = TelemetryReading(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                ram_percent=ram_percent,
                requests_per_second=rps,
                source='system'
            )
            readings.append(reading)
            
            # Samla Guardian telemetri samtidigt
            guardian_reading = await self._get_guardian_telemetry()
            if guardian_reading:
                readings.append(guardian_reading)
            
            logger.debug(f"📊 System: CPU={cpu_percent:.1f}%, RAM={ram_percent:.1f}%, RPS={rps:.1f}")
            
            await asyncio.sleep(5)  # Sample var 5:e sekund
        
        logger.info(f"✅ Collected {len(readings)} telemetry readings")
        return readings
    
    async def _estimate_current_rps(self) -> float:
        """Enkel RPS estimation baserat på Alice health endpoint"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                start_time = time.time()
                
                # Gör flera snabba requests för att testa current load
                tasks = []
                for _ in range(5):
                    tasks.append(session.get(f"{self.alice_url}/health"))
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                successful_responses = [r for r in responses if not isinstance(r, Exception)]
                
                if successful_responses:
                    # Enkel estimation: om responses tar lång tid = system under load
                    avg_response_time = sum(r.headers.get('x-response-time', 0) for r in successful_responses) / len(successful_responses)
                    # Rough estimation: längre response times indikerar högre load
                    estimated_rps = max(0, (avg_response_time - 50) / 100)  # Very rough heuristic
                    return estimated_rps
                    
        except Exception as e:
            logger.debug(f"RPS estimation failed: {e}")
        
        return 0.0
    
    async def _get_guardian_telemetry(self) -> Optional[TelemetryReading]:
        """Hämta Guardian telemetri för jämförelse"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                async with session.get(f"{self.guardian_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        cpu_pct = data.get('cpu_pct', 0) * 100 if 'cpu_pct' in data else 0
                        ram_pct = data.get('ram_pct', 0) * 100 if 'ram_pct' in data else 0
                        
                        return TelemetryReading(
                            timestamp=datetime.now(),
                            cpu_percent=cpu_pct,
                            ram_percent=ram_pct,
                            requests_per_second=0,  # Guardian doesn't track RPS directly
                            source='guardian'
                        )
        except Exception as e:
            logger.debug(f"Guardian telemetry failed: {e}")
        
        return None
    
    async def generate_load_and_validate(self, load_duration_minutes: int = 10) -> ValidationResult:
        """Generera belastning och validera telemetri under load"""
        logger.info(f"🚀 Starting load generation and telemetry validation...")
        
        # Start load generation i background
        load_task = asyncio.create_task(self._generate_realistic_load(load_duration_minutes))
        
        # Samla telemetri under load
        readings = await self.collect_system_telemetry(load_duration_minutes)
        
        # Vänta på att load generation ska avslutas
        await load_task
        
        # Validera readings
        return self._validate_telemetry_accuracy(readings)
    
    async def _generate_realistic_load(self, duration_minutes: int):
        """Generera realistisk belastning för att testa telemetri"""
        logger.info(f"⚡ Generating realistic load for {duration_minutes} minutes...")
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        concurrent_requests = 8  # Simulera 8+ concurrent users
        
        async def make_request(session: aiohttp.ClientSession, query: str):
            try:
                payload = {
                    "text": f"Telemetry validation test: {query}",
                    "session_id": f"telemetry_test_{int(time.time())}"
                }
                
                async with session.post(f"{self.alice_url}/api/chat", 
                                      json=payload,
                                      timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        await response.json()  # Consume response
                        return True
            except Exception as e:
                logger.debug(f"Load request failed: {e}")
            return False
        
        # Svenska queries för realistic load
        queries = [
            "Vad är klockan?",
            "Berätta om Sverige", 
            "Hur fungerar AI?",
            "Förklara quantum computing",
            "Vad är weather idag?",
            "Hjälp mig med matematik",
            "Sammanfatta latest news",
            "Förklara Guardian system",
        ]
        
        async with aiohttp.ClientSession() as session:
            while datetime.now() < end_time:
                # Generera batch av concurrent requests
                tasks = []
                for i in range(concurrent_requests):
                    query = queries[i % len(queries)]
                    tasks.append(make_request(session, f"{query} batch_{int(time.time())}"))
                
                # Execute concurrent requests
                results = await asyncio.gather(*tasks, return_exceptions=True)
                successful = sum(1 for r in results if r is True)
                
                logger.debug(f"📈 Load batch: {successful}/{concurrent_requests} successful")
                
                # Realistisk pacing mellan batches
                await asyncio.sleep(2)
        
        logger.info("✅ Load generation completed")
    
    def _validate_telemetry_accuracy(self, readings: List[TelemetryReading]) -> ValidationResult:
        """Validera telemetri accuracy mot enterprise standards"""
        logger.info(f"📊 Validating {len(readings)} telemetry readings...")
        
        # Separera readings per source
        system_readings = [r for r in readings if r.source == 'system']
        guardian_readings = [r for r in readings if r.source == 'guardian']
        
        suspicious_readings = 0
        zero_cpu_under_load = 0
        recommendations = []
        
        # Validate Guardian readings mot system readings
        if guardian_readings and system_readings:
            # Find corresponding readings (inom 10s av varandra)
            paired_readings = []
            
            for guardian_reading in guardian_readings:
                closest_system = min(
                    system_readings,
                    key=lambda sr: abs((sr.timestamp - guardian_reading.timestamp).total_seconds()),
                    default=None
                )
                
                if closest_system and abs((closest_system.timestamp - guardian_reading.timestamp).total_seconds()) <= 10:
                    paired_readings.append((guardian_reading, closest_system))
            
            logger.info(f"📍 Found {len(paired_readings)} paired readings for comparison")
            
            # Validate paired readings
            for guardian, system in paired_readings:
                cpu_diff = abs(guardian.cpu_percent - system.cpu_percent)
                ram_diff = abs(guardian.ram_percent - system.ram_percent)
                
                # Check för suspicious patterns
                if system.cpu_percent > 5 and guardian.cpu_percent == 0:
                    zero_cpu_under_load += 1
                    logger.warning(f"⚠️ Zero CPU reading under load: Guardian={guardian.cpu_percent}%, System={system.cpu_percent}%")
                
                if cpu_diff > 20:  # >20% skillnad = suspicious
                    suspicious_readings += 1
                    logger.warning(f"⚠️ Large CPU discrepancy: Guardian={guardian.cpu_percent}%, System={system.cpu_percent}%")
                
                if ram_diff > 15:  # >15% RAM skillnad = suspicious
                    suspicious_readings += 1
                    logger.warning(f"⚠️ Large RAM discrepancy: Guardian={guardian.ram_percent}%, System={system.ram_percent}%")
        
        # Calculate accuracy score
        total_comparisons = len(paired_readings) if 'paired_readings' in locals() else 1
        accuracy_score = max(0, 100 - (suspicious_readings / total_comparisons * 100))
        
        # Realistic telemetry assessment
        realistic_telemetry = (
            zero_cpu_under_load == 0 and 
            suspicious_readings < total_comparisons * 0.1  # <10% suspicious readings
        )
        
        # Generate recommendations
        if zero_cpu_under_load > 0:
            recommendations.append(f"🚨 Fix zero CPU readings under load ({zero_cpu_under_load} detected)")
        
        if suspicious_readings > total_comparisons * 0.1:
            recommendations.append(f"⚠️ High telemetry discrepancy rate ({suspicious_readings}/{total_comparisons})")
            recommendations.append("💡 Verify Guardian telemetry collection interval and accuracy")
        
        if accuracy_score < 80:
            recommendations.append("🔧 Consider implementing cross-validation with system telemetry")
        
        if realistic_telemetry:
            recommendations.append("✅ Telemetry accuracy meets enterprise standards")
        
        return ValidationResult(
            accuracy_score=accuracy_score,
            suspicious_readings=suspicious_readings,
            zero_cpu_under_load=zero_cpu_under_load,
            realistic_telemetry=realistic_telemetry,
            recommendations=recommendations
        )
    
    async def run_validation_suite(self) -> Dict[str, Any]:
        """Kör komplett telemetri validation suite"""
        logger.info("🎯 Starting comprehensive telemetry validation...")
        
        start_time = datetime.now()
        
        # Run validation under load
        validation_result = await self.generate_load_and_validate(load_duration_minutes=15)
        
        end_time = datetime.now()
        test_duration = (end_time - start_time).total_seconds() / 60
        
        report = {
            'validation_summary': {
                'test_duration_minutes': test_duration,
                'accuracy_score': validation_result.accuracy_score,
                'realistic_telemetry': validation_result.realistic_telemetry,
                'enterprise_ready': validation_result.realistic_telemetry and validation_result.accuracy_score >= 80
            },
            'telemetry_issues': {
                'suspicious_readings': validation_result.suspicious_readings,
                'zero_cpu_under_load': validation_result.zero_cpu_under_load,
            },
            'recommendations': validation_result.recommendations,
            'validation_timestamp': datetime.now().isoformat()
        }
        
        # Print executive summary
        print("\n🎯 TELEMETRY VALIDATION SUMMARY")
        print("=" * 40)
        print(f"Accuracy Score: {validation_result.accuracy_score:.1f}/100")
        print(f"Enterprise Ready: {'✅ YES' if report['validation_summary']['enterprise_ready'] else '❌ NO'}")
        print(f"Suspicious Readings: {validation_result.suspicious_readings}")
        print(f"Zero CPU Under Load: {validation_result.zero_cpu_under_load}")
        
        print(f"\n📋 RECOMMENDATIONS:")
        for rec in validation_result.recommendations:
            print(f"  {rec}")
        
        return report

async def main():
    """Main validation runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Alice Telemetry Validator')
    parser.add_argument('--duration', '-d', type=int, default=15, help='Load test duration in minutes')
    parser.add_argument('--guardian-url', default='http://localhost:8787', help='Guardian URL')
    parser.add_argument('--alice-url', default='http://localhost:8000', help='Alice URL')
    parser.add_argument('--output', '-o', help='Output JSON report file')
    
    args = parser.parse_args()
    
    validator = TelemetryValidator(args.guardian_url, args.alice_url)
    
    try:
        report = await validator.run_validation_suite()
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\n📊 Telemetry validation report saved: {args.output}")
        
        # Exit code based on results
        exit_code = 0 if report['validation_summary']['enterprise_ready'] else 1
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("🛑 Telemetry validation interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Telemetry validation failed: {e}")
        return 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    exit(exit_code)