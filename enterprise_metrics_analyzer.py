#!/usr/bin/env python3
"""
Alice Enterprise Metrics Analyzer
==================================

Analyserar NDJSON logs från 14-dagars soak test för production readiness validation.
Genererar enterprise-grade rapporter med p50/p95/p99/p99.9 metrics.
"""

import json
import sys
import statistics
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import argparse

@dataclass
class MetricSample:
    """En metric sample från logs"""
    timestamp: datetime
    value: float
    guardian_mode: str = 'unknown'
    test_type: str = 'continuous'
    cache_hit: bool = False

@dataclass 
class EnterpriseMetrics:
    """Enterprise-grade metrics för production readiness"""
    p50: float
    p95: float  
    p99: float
    p99_9: float
    mean: float
    std_dev: float
    min_val: float
    max_val: float
    sample_count: int
    
    def __post_init__(self):
        """Validate enterprise thresholds"""
        self.p95_sla_met = self.p95 <= 2000  # Enterprise: p95 ≤ 2s
        self.p99_sla_met = self.p99 <= 3000  # Enterprise: p99 ≤ 3s
        self.availability = 100 - (self.error_rate * 100) if hasattr(self, 'error_rate') else None

class EnterpriseAnalyzer:
    """Analyserar Alice logs för enterprise production readiness"""
    
    def __init__(self, log_file: str, start_date: Optional[datetime] = None):
        self.log_file = log_file
        self.start_date = start_date or datetime.now()
        
        # Enterprise data structures
        self.response_times: List[MetricSample] = []
        self.error_samples: List[MetricSample] = []
        self.guardian_modes: List[MetricSample] = []
        self.cache_performance: List[MetricSample] = []
        self.cpu_samples: List[MetricSample] = []
        self.ram_samples: List[MetricSample] = []
        
        # Daily aggregations för enterprise reporting
        self.daily_metrics: Dict[str, Dict] = defaultdict(dict)
        
    def parse_ndjson_logs(self) -> None:
        """Parse NDJSON logs från Alice system"""
        print(f"📊 Parsing enterprise logs: {self.log_file}")
        
        with open(self.log_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    log_entry = json.loads(line.strip())
                    self._process_log_entry(log_entry)
                except json.JSONDecodeError as e:
                    print(f"⚠️  JSON parse error line {line_num}: {e}")
                except Exception as e:
                    print(f"❌ Processing error line {line_num}: {e}")
                    
        print(f"✅ Parsed {len(self.response_times)} response samples")
        print(f"✅ Parsed {len(self.guardian_modes)} guardian state samples")
        
    def _process_log_entry(self, entry: Dict[str, Any]) -> None:
        """Process en log entry och extrahera metrics"""
        timestamp = self._parse_timestamp(entry.get('timestamp'))
        if not timestamp:
            return
            
        # Response time metrics
        if 'tftt_ms' in entry:
            sample = MetricSample(
                timestamp=timestamp,
                value=float(entry['tftt_ms']),
                guardian_mode=entry.get('guardian_mode', 'unknown'),
                test_type=entry.get('test_type', 'continuous'),
                cache_hit=entry.get('cache_hit', False)
            )
            self.response_times.append(sample)
            
        # Error tracking
        if entry.get('level') == 'ERROR' or 'error' in entry.get('message', '').lower():
            sample = MetricSample(
                timestamp=timestamp,
                value=1.0,  # Error occurred
                guardian_mode=entry.get('guardian_mode', 'unknown')
            )
            self.error_samples.append(sample)
            
        # Guardian mode changes
        if 'guardian_mode' in entry:
            sample = MetricSample(
                timestamp=timestamp,
                value=0.0,  # Dummy value
                guardian_mode=entry['guardian_mode']
            )
            self.guardian_modes.append(sample)
            
        # System resource metrics
        if 'ram_pct' in entry:
            sample = MetricSample(
                timestamp=timestamp,
                value=float(entry['ram_pct']) * 100,  # Convert to percentage
                guardian_mode=entry.get('guardian_mode', 'unknown')
            )
            self.ram_samples.append(sample)
            
        if 'cpu_pct' in entry:
            sample = MetricSample(
                timestamp=timestamp,
                value=float(entry['cpu_pct']) * 100,
                guardian_mode=entry.get('guardian_mode', 'unknown')
            )
            self.cpu_samples.append(sample)
    
    def _parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        """Parse timestamp från olika format"""
        if not ts_str:
            return None
            
        try:
            # ISO format
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except:
            try:
                # Unix timestamp
                return datetime.fromtimestamp(float(ts_str))
            except:
                return None
    
    def calculate_enterprise_metrics(self, samples: List[MetricSample]) -> EnterpriseMetrics:
        """Beräkna enterprise-grade metrics"""
        if not samples:
            return EnterpriseMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)
            
        values = [s.value for s in samples]
        values.sort()
        
        n = len(values)
        metrics = EnterpriseMetrics(
            p50=np.percentile(values, 50),
            p95=np.percentile(values, 95), 
            p99=np.percentile(values, 99),
            p99_9=np.percentile(values, 99.9),
            mean=statistics.mean(values),
            std_dev=statistics.stdev(values) if n > 1 else 0,
            min_val=min(values),
            max_val=max(values),
            sample_count=n
        )
        
        return metrics
    
    def analyze_guardian_stability(self) -> Dict[str, Any]:
        """Analysera Guardian stability över tid"""
        mode_changes = []
        current_mode = None
        mode_durations = defaultdict(list)
        
        for sample in sorted(self.guardian_modes, key=lambda x: x.timestamp):
            if current_mode and sample.guardian_mode != current_mode:
                mode_changes.append({
                    'timestamp': sample.timestamp.isoformat(),
                    'from': current_mode,
                    'to': sample.guardian_mode
                })
            current_mode = sample.guardian_mode
            
        # Räkna mode distribution
        mode_counter = Counter(s.guardian_mode for s in self.guardian_modes)
        
        return {
            'total_mode_changes': len(mode_changes),
            'mode_changes': mode_changes,
            'mode_distribution': dict(mode_counter),
            'stability_score': 100 - min(100, len(mode_changes) / max(1, len(self.guardian_modes) / 1000) * 100)
        }
    
    def analyze_cache_performance(self) -> Dict[str, Any]:
        """Analysera cache hit rates och impact"""
        if not self.response_times:
            return {'error': 'No response time data available'}
            
        cache_hits = [s for s in self.response_times if s.cache_hit]
        cache_misses = [s for s in self.response_times if not s.cache_hit]
        
        hit_rate = len(cache_hits) / len(self.response_times) * 100
        
        cache_hit_metrics = self.calculate_enterprise_metrics(cache_hits)
        cache_miss_metrics = self.calculate_enterprise_metrics(cache_misses)
        
        return {
            'hit_rate_percent': hit_rate,
            'hit_p95_ms': cache_hit_metrics.p95,
            'miss_p95_ms': cache_miss_metrics.p95,
            'performance_improvement': cache_miss_metrics.p95 - cache_hit_metrics.p95 if cache_hits else 0,
            'enterprise_threshold_met': hit_rate >= 15.0  # Minimum 15% för enterprise
        }
    
    def validate_cpu_ram_accuracy(self) -> Dict[str, Any]:
        """Validera CPU/RAM telemetri accuracy under belastning"""
        
        # Identifiera periods med hög belastning (>5 RPS)
        high_load_periods = []
        current_period = []
        
        # Gruppera response times per minut för RPS calculation
        minute_buckets = defaultdict(list)
        for sample in self.response_times:
            minute_key = sample.timestamp.replace(second=0, microsecond=0)
            minute_buckets[minute_key].append(sample)
            
        high_load_minutes = [
            minute for minute, samples in minute_buckets.items() 
            if len(samples) > 5  # >5 requests per minute ≈ high load
        ]
        
        # Find CPU/RAM data under high load
        high_load_cpu = []
        high_load_ram = []
        
        for sample in self.cpu_samples:
            minute_key = sample.timestamp.replace(second=0, microsecond=0)
            if minute_key in high_load_minutes:
                high_load_cpu.append(sample.value)
                
        for sample in self.ram_samples:
            minute_key = sample.timestamp.replace(second=0, microsecond=0)
            if minute_key in high_load_minutes:
                high_load_ram.append(sample.value)
        
        # Validate realism
        cpu_suspicious = len([c for c in high_load_cpu if c < 1.0])  # <1% CPU under load = suspicious
        zero_cpu_periods = len([c for c in high_load_cpu if c == 0.0])
        
        return {
            'high_load_periods': len(high_load_minutes),
            'avg_cpu_under_load': statistics.mean(high_load_cpu) if high_load_cpu else 0,
            'avg_ram_under_load': statistics.mean(high_load_ram) if high_load_ram else 0,
            'suspicious_cpu_readings': cpu_suspicious,
            'zero_cpu_periods': zero_cpu_periods,
            'telemetry_accuracy_score': 100 - (cpu_suspicious / max(1, len(high_load_cpu)) * 100),
            'realistic_telemetry': zero_cpu_periods == 0 and cpu_suspicious < len(high_load_cpu) * 0.1
        }
    
    def generate_enterprise_report(self) -> Dict[str, Any]:
        """Generera enterprise production readiness rapport"""
        
        # Calculate core metrics
        response_metrics = self.calculate_enterprise_metrics(self.response_times)
        
        # Calculate error rate
        total_requests = len(self.response_times)
        total_errors = len(self.error_samples)
        error_rate = total_errors / max(1, total_requests)
        response_metrics.error_rate = error_rate
        
        # Calculate availability (enterprise standard)
        availability = (1 - error_rate) * 100
        
        # Guardian analysis
        guardian_analysis = self.analyze_guardian_stability()
        
        # Cache analysis
        cache_analysis = self.analyze_cache_performance()
        
        # Telemetry validation
        telemetry_analysis = self.validate_cpu_ram_accuracy()
        
        # Production readiness assessment
        production_ready = all([
            response_metrics.p95_sla_met,  # p95 ≤ 2s
            response_metrics.p99_sla_met,  # p99 ≤ 3s
            availability >= 99.0,          # >99% availability
            guardian_analysis['stability_score'] >= 90,
            cache_analysis.get('enterprise_threshold_met', False),
            telemetry_analysis['realistic_telemetry']
        ])
        
        return {
            'enterprise_summary': {
                'production_ready': production_ready,
                'test_duration_hours': (max(s.timestamp for s in self.response_times) - 
                                      min(s.timestamp for s in self.response_times)).total_seconds() / 3600 if self.response_times else 0,
                'total_requests': total_requests,
                'availability_percent': availability,
                'sla_compliance': {
                    'p95_under_2s': response_metrics.p95_sla_met,
                    'p99_under_3s': response_metrics.p99_sla_met,
                    'error_rate_under_1pct': error_rate < 0.01
                }
            },
            'response_time_metrics': {
                'p50_ms': response_metrics.p50,
                'p95_ms': response_metrics.p95,
                'p99_ms': response_metrics.p99,
                'p99_9_ms': response_metrics.p99_9,
                'mean_ms': response_metrics.mean,
                'std_dev_ms': response_metrics.std_dev
            },
            'reliability_metrics': {
                'error_rate_percent': error_rate * 100,
                'availability_percent': availability,
                'total_errors': total_errors
            },
            'guardian_stability': guardian_analysis,
            'cache_performance': cache_analysis,
            'telemetry_validation': telemetry_analysis,
            'enterprise_recommendations': self._generate_recommendations(
                production_ready, response_metrics, error_rate, guardian_analysis, 
                cache_analysis, telemetry_analysis
            )
        }
    
    def _generate_recommendations(self, production_ready: bool, response_metrics: EnterpriseMetrics,
                                error_rate: float, guardian_analysis: Dict, 
                                cache_analysis: Dict, telemetry_analysis: Dict) -> List[str]:
        """Generera enterprise rekommendationer baserat på analys"""
        recommendations = []
        
        if not production_ready:
            recommendations.append("❌ SYSTEM NOT PRODUCTION READY - Address critical issues below")
            
        if not response_metrics.p95_sla_met:
            recommendations.append(f"🚨 p95 latency {response_metrics.p95:.1f}ms exceeds 2s SLA - optimize critical path")
            
        if not response_metrics.p99_sla_met:
            recommendations.append(f"🚨 p99 latency {response_metrics.p99:.1f}ms exceeds 3s SLA - investigate tail latency")
            
        if error_rate >= 0.01:
            recommendations.append(f"🚨 Error rate {error_rate*100:.2f}% exceeds 1% enterprise threshold")
            
        if guardian_analysis['stability_score'] < 90:
            recommendations.append(f"⚠️ Guardian stability {guardian_analysis['stability_score']:.1f}% below 90% - tune hysteresis")
            
        if cache_analysis.get('hit_rate_percent', 0) < 15:
            recommendations.append(f"⚠️ Cache hit rate {cache_analysis.get('hit_rate_percent', 0):.1f}% below 15% enterprise minimum")
            
        if not telemetry_analysis['realistic_telemetry']:
            recommendations.append(f"🚨 Telemetry accuracy issues detected - verify monitoring infrastructure")
            
        if production_ready:
            recommendations.append("✅ ENTERPRISE PRODUCTION READY - All SLAs met")
            
        return recommendations

def main():
    parser = argparse.ArgumentParser(description='Alice Enterprise Metrics Analyzer')
    parser.add_argument('log_file', help='Path to NDJSON log file')
    parser.add_argument('--output', '-o', help='Output JSON report file')
    parser.add_argument('--start-date', help='Analysis start date (ISO format)')
    
    args = parser.parse_args()
    
    start_date = None
    if args.start_date:
        start_date = datetime.fromisoformat(args.start_date)
    
    # Run enterprise analysis
    analyzer = EnterpriseAnalyzer(args.log_file, start_date)
    analyzer.parse_ndjson_logs()
    
    report = analyzer.generate_enterprise_report()
    
    # Output report
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"📊 Enterprise report saved: {args.output}")
    else:
        print(json.dumps(report, indent=2, default=str))
    
    # Print executive summary
    summary = report['enterprise_summary']
    print(f"\n🎯 ENTERPRISE PRODUCTION READINESS SUMMARY")
    print(f"{'='*50}")
    print(f"Production Ready: {'✅ YES' if summary['production_ready'] else '❌ NO'}")
    print(f"Test Duration: {summary['test_duration_hours']:.1f} hours")
    print(f"Total Requests: {summary['total_requests']:,}")
    print(f"Availability: {summary['availability_percent']:.3f}%")
    print(f"SLA Compliance: p95 {'✅' if summary['sla_compliance']['p95_under_2s'] else '❌'} | p99 {'✅' if summary['sla_compliance']['p99_under_3s'] else '❌'} | Errors {'✅' if summary['sla_compliance']['error_rate_under_1pct'] else '❌'}")
    
    print(f"\n📋 RECOMMENDATIONS:")
    for rec in report['enterprise_recommendations']:
        print(f"  {rec}")

if __name__ == '__main__':
    main()