#!/usr/bin/env python3
"""
Guardian NDJSON Logger - Strukturerad loggning för Guardian-systemet
===================================================================

Implementerar NDJSON (Newline Delimited JSON) loggning för Guardian metrics,
händelser och korrelationsanalys. Designad för hög prestanda och enkel parsing.

Features:
- NDJSON-format för streaming-parser
- Säkerhetskorrelation mellan systemload och AI-prestanda
- Automatisk logrotation och buffering
- Thread-safe operations för concurrent logging
- Korrelationsanalys för auto-tuning
"""

import json
import os
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import logging


@dataclass
class GuardianLogEntry:
    """Strukturerad Guardian log entry"""
    timestamp: float
    event_type: str  # 'metrics', 'action', 'correlation', 'alert'
    guardian_id: str
    data: Dict[str, Any]
    level: str = 'INFO'  # DEBUG, INFO, WARN, ERROR, CRITICAL
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None


class GuardianLogger:
    """
    NDJSON Logger för Guardian System
    
    Loggar alla Guardian-händelser i strukturerat NDJSON-format för
    enkel parsing och korrelationsanalys.
    """
    
    def __init__(self, 
                 log_dir: str = "logs/guardian",
                 max_file_size: int = 50 * 1024 * 1024,  # 50MB
                 max_files: int = 10,
                 buffer_size: int = 1000):
        self.log_dir = Path(log_dir)
        self.max_file_size = max_file_size
        self.max_files = max_files
        self.buffer_size = buffer_size
        
        # Thread safety
        self._lock = threading.RLock()
        self._buffer: List[GuardianLogEntry] = []
        self._current_file = None
        self._current_size = 0
        
        # Guardian instance tracking
        self.guardian_id = f"guardian_{int(time.time())}"
        self.session_id = f"session_{int(time.time())}"
        
        # Setup
        self._setup_log_directory()
        self._open_current_log_file()
        
        # Background flush thread
        self._flush_thread = threading.Thread(target=self._background_flush, daemon=True)
        self._flush_thread.start()
        
        self.logger = logging.getLogger(__name__)
    
    def _setup_log_directory(self):
        """Skapa log-katalog om den inte finns"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _open_current_log_file(self):
        """Öppna aktuell log-fil"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"guardian_{timestamp}.ndjson"
        
        self._current_file = open(log_file, 'a', encoding='utf-8')
        self._current_size = log_file.stat().st_size if log_file.exists() else 0
        
        # Log startup
        self.log_event('startup', {
            'guardian_id': self.guardian_id,
            'session_id': self.session_id,
            'log_file': str(log_file),
            'pid': os.getpid()
        })
    
    def _rotate_log_file(self):
        """Rotera log-fil när den blir för stor"""
        if self._current_file:
            self._current_file.close()
        
        # Cleanup gamla filer
        self._cleanup_old_logs()
        
        # Öppna ny fil
        self._open_current_log_file()
    
    def _cleanup_old_logs(self):
        """Ta bort gamla log-filer över max_files"""
        log_files = list(self.log_dir.glob("guardian_*.ndjson"))
        log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Behåll bara max_files filer
        for old_file in log_files[self.max_files:]:
            try:
                old_file.unlink()
            except OSError:
                pass
    
    def _write_entry(self, entry: GuardianLogEntry):
        """Skriv entry direkt till fil"""
        if not self._current_file:
            return
        
        try:
            json_line = json.dumps(asdict(entry), ensure_ascii=False) + '\n'
            self._current_file.write(json_line)
            self._current_file.flush()  # Força flush för viktiga händelser
            
            self._current_size += len(json_line.encode('utf-8'))
            
            # Rotera om filen blir för stor
            if self._current_size >= self.max_file_size:
                self._rotate_log_file()
                
        except Exception as e:
            self.logger.error(f"Failed to write log entry: {e}")
    
    def _background_flush(self):
        """Background thread som flushar buffer regelbundet"""
        while True:
            try:
                time.sleep(5)  # Flush varje 5 sekunder
                self.flush_buffer()
            except Exception as e:
                self.logger.error(f"Background flush failed: {e}")
    
    def log_entry(self, entry: GuardianLogEntry):
        """Logga en Guardian entry"""
        with self._lock:
            self._buffer.append(entry)
            
            # Flush om buffer är full eller kritisk händelse
            if len(self._buffer) >= self.buffer_size or entry.level in ('ERROR', 'CRITICAL'):
                self.flush_buffer()
    
    def flush_buffer(self):
        """Flush buffer till disk"""
        with self._lock:
            if not self._buffer:
                return
            
            for entry in self._buffer:
                self._write_entry(entry)
            
            self._buffer.clear()
    
    def log_metrics(self, metrics: Dict[str, Any], correlation_id: str = None):
        """Logga Guardian system metrics"""
        entry = GuardianLogEntry(
            timestamp=time.time(),
            event_type='metrics',
            guardian_id=self.guardian_id,
            data={
                'metrics': metrics,
                'collection_time': datetime.now(timezone.utc).isoformat()
            },
            correlation_id=correlation_id,
            session_id=self.session_id
        )
        self.log_entry(entry)
    
    def log_action(self, action: str, details: Dict[str, Any], level: str = 'INFO'):
        """Logga Guardian-åtgärder"""
        entry = GuardianLogEntry(
            timestamp=time.time(),
            event_type='action',
            guardian_id=self.guardian_id,
            data={
                'action': action,
                'details': details,
                'execution_time': datetime.now(timezone.utc).isoformat()
            },
            level=level,
            session_id=self.session_id
        )
        self.log_entry(entry)
    
    def log_correlation(self, analysis: Dict[str, Any], correlation_id: str = None):
        """Logga korrelationsanalys resultat"""
        entry = GuardianLogEntry(
            timestamp=time.time(),
            event_type='correlation',
            guardian_id=self.guardian_id,
            data={
                'analysis': analysis,
                'analysis_time': datetime.now(timezone.utc).isoformat()
            },
            correlation_id=correlation_id,
            session_id=self.session_id
        )
        self.log_entry(entry)
    
    def log_alert(self, alert_type: str, message: str, details: Dict[str, Any], level: str = 'WARN'):
        """Logga Guardian-varningar och alerts"""
        entry = GuardianLogEntry(
            timestamp=time.time(),
            event_type='alert',
            guardian_id=self.guardian_id,
            data={
                'alert_type': alert_type,
                'message': message,
                'details': details,
                'alert_time': datetime.now(timezone.utc).isoformat()
            },
            level=level,
            session_id=self.session_id
        )
        self.log_entry(entry)
    
    def log_event(self, event_type: str, data: Dict[str, Any], level: str = 'INFO'):
        """Generisk event logging"""
        entry = GuardianLogEntry(
            timestamp=time.time(),
            event_type=event_type,
            guardian_id=self.guardian_id,
            data=data,
            level=level,
            session_id=self.session_id
        )
        self.log_entry(entry)
    
    def close(self):
        """Stäng logger och flush alla buffers"""
        with self._lock:
            self.flush_buffer()
            if self._current_file:
                self._current_file.close()
                self._current_file = None


class CorrelationAnalyzer:
    """
    Korrelationsanalysator för Guardian-data
    
    Analyserar NDJSON-loggar för att hitta kopplingar mellan systemload
    och AI-prestanda, för automatisk tuning av Guardian-parametrar.
    """
    
    def __init__(self, log_dir: str = "logs/guardian"):
        self.log_dir = Path(log_dir)
        self.logger = logging.getLogger(__name__)
    
    def load_recent_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Ladda metrics från senaste timmarna"""
        cutoff_time = time.time() - (hours * 3600)
        metrics = []
        
        # Läs alla relevanta log-filer
        log_files = sorted(self.log_dir.glob("guardian_*.ndjson"))
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            
                            # Filtrera på tid och event_type
                            if (entry.get('timestamp', 0) >= cutoff_time and 
                                entry.get('event_type') == 'metrics'):
                                metrics.append(entry)
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                self.logger.error(f"Error reading log file {log_file}: {e}")
        
        return sorted(metrics, key=lambda x: x.get('timestamp', 0))
    
    def analyze_ram_performance_correlation(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analysera korrelation mellan RAM-användning och AI-prestanda"""
        if len(metrics) < 10:
            return {'error': 'Insufficient data for correlation analysis'}
        
        ram_values = []
        response_times = []
        degradation_events = []
        
        for entry in metrics:
            data = entry.get('data', {}).get('metrics', {})
            ram_pct = data.get('ram_pct', 0)
            
            if ram_pct > 0:
                ram_values.append(ram_pct)
                
                # Extrahera response time om tillgängligt
                response_time = data.get('llm_response_time', 0)
                if response_time > 0:
                    response_times.append(response_time)
                
                # Spåra degradation events
                if data.get('degraded', False):
                    degradation_events.append({
                        'timestamp': entry.get('timestamp'),
                        'ram_pct': ram_pct,
                        'response_time': response_time
                    })
        
        # Beräkna korrelation (enkel implementation)
        correlation_analysis = {
            'total_samples': len(metrics),
            'ram_stats': {
                'min': min(ram_values) if ram_values else 0,
                'max': max(ram_values) if ram_values else 0,
                'avg': sum(ram_values) / len(ram_values) if ram_values else 0
            },
            'response_time_stats': {
                'min': min(response_times) if response_times else 0,
                'max': max(response_times) if response_times else 0,
                'avg': sum(response_times) / len(response_times) if response_times else 0
            },
            'degradation_events': len(degradation_events),
            'recommendations': self._generate_recommendations(ram_values, response_times, degradation_events)
        }
        
        return correlation_analysis
    
    def _generate_recommendations(self, ram_values: List[float], 
                                response_times: List[float], 
                                degradation_events: List[Dict]) -> List[str]:
        """Generera rekommendationer baserat på korrelationsanalys"""
        recommendations = []
        
        if ram_values:
            avg_ram = sum(ram_values) / len(ram_values)
            max_ram = max(ram_values)
            
            if max_ram > 0.90:
                recommendations.append("Consider lowering RAM thresholds - system reaching 90%+ usage")
            
            if avg_ram > 0.75:
                recommendations.append("Average RAM usage high - consider more aggressive early intervention")
            
            if len(degradation_events) > len(ram_values) * 0.1:
                recommendations.append("Frequent degradation events - consider lowering soft thresholds")
        
        if response_times:
            avg_response = sum(response_times) / len(response_times)
            if avg_response > 30:  # 30 sekunder
                recommendations.append("High average response times - consider more aggressive model unloading")
        
        if not recommendations:
            recommendations.append("System performing within normal parameters")
        
        return recommendations


# Global Guardian Logger instance
_guardian_logger: Optional[GuardianLogger] = None

def get_guardian_logger() -> GuardianLogger:
    """Hämta global Guardian Logger instance"""
    global _guardian_logger
    if _guardian_logger is None:
        _guardian_logger = GuardianLogger()
    return _guardian_logger

def log_guardian_metrics(metrics: Dict[str, Any], correlation_id: str = None):
    """Convenience function för att logga metrics"""
    get_guardian_logger().log_metrics(metrics, correlation_id)

def log_guardian_action(action: str, details: Dict[str, Any], level: str = 'INFO'):
    """Convenience function för att logga åtgärder"""
    get_guardian_logger().log_action(action, details, level)

def log_guardian_alert(alert_type: str, message: str, details: Dict[str, Any], level: str = 'WARN'):
    """Convenience function för att logga alerts"""
    get_guardian_logger().log_alert(alert_type, message, details, level)

def analyze_guardian_correlations(hours: int = 24) -> Dict[str, Any]:
    """Convenience function för korrelationsanalys"""
    analyzer = CorrelationAnalyzer()
    metrics = analyzer.load_recent_metrics(hours)
    return analyzer.analyze_ram_performance_correlation(metrics)

if __name__ == "__main__":
    # Test NDJSON logging
    print("🧪 Testing Guardian NDJSON Logger")
    
    logger = GuardianLogger(log_dir="test_logs")
    
    # Test olika typer av loggar
    logger.log_metrics({
        'ram_pct': 0.65,
        'cpu_pct': 0.45,
        'ollama_pids': [12345],
        'response_time': 2.5
    })
    
    logger.log_action('degrade', {
        'old_concurrency': 2,
        'new_concurrency': 1,
        'reason': 'RAM threshold exceeded'
    })
    
    logger.log_alert('high_ram_usage', 'RAM usage approaching limits', {
        'current_ram': 0.87,
        'threshold': 0.85
    }, level='WARN')
    
    # Test korrelationsanalys  
    time.sleep(1)  # Låt loggarna skrivas
    analyzer = CorrelationAnalyzer(log_dir="test_logs")
    analysis = analyzer.analyze_ram_performance_correlation(analyzer.load_recent_metrics(1))
    
    print("📊 Correlation Analysis Results:")
    print(json.dumps(analysis, indent=2))
    
    logger.close()
    print("✅ NDJSON Logger test completed")