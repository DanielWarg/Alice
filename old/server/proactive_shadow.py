#!/usr/bin/env python3
"""
B4.1 Shadow Mode & KPI Tracking
Monitors proactive suggestions without showing them to user, tracks KPIs
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import os
from pathlib import Path

@dataclass
class ShadowLog:
    """Log entry for shadow mode tracking"""
    timestamp: str
    pattern_id: str
    confidence: float
    message: str
    why: str  # Reason for suggestion
    throttling_reason: Optional[str]
    policy_reason: Optional[str]
    latency_ms: float
    action: Optional[str]  # accepted/declined/never/snooze
    metadata: Dict[str, Any]

class ProactiveShadow:
    def __init__(self, db_path: str = "proactive.db"):
        self.db_path = db_path
        self.shadow_logs = []
        self.init_shadow_db()
        
    def init_shadow_db(self):
        """Initialize shadow mode database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Shadow logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shadow_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                pattern_id TEXT,
                confidence REAL,
                message TEXT,
                why TEXT,
                throttling_reason TEXT,
                policy_reason TEXT,
                latency_ms REAL,
                action TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # KPI tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shadow_kpis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total_suggestions INTEGER DEFAULT 0,
                accepted INTEGER DEFAULT 0,
                declined INTEGER DEFAULT 0,
                snoozed INTEGER DEFAULT 0,
                never_interacted INTEGER DEFAULT 0,
                avg_latency_ms REAL DEFAULT 0,
                p95_latency_ms REAL DEFAULT 0,
                quiet_hour_violations INTEGER DEFAULT 0,
                top_patterns TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        
    def log_shadow_suggestion(self, 
                            pattern_id: str,
                            confidence: float,
                            message: str,
                            why: str,
                            latency_ms: float,
                            throttling_reason: Optional[str] = None,
                            policy_reason: Optional[str] = None,
                            metadata: Dict[str, Any] = None) -> str:
        """Log a suggestion that would be shown in shadow mode"""
        
        log_entry = ShadowLog(
            timestamp=datetime.now().isoformat(),
            pattern_id=pattern_id,
            confidence=confidence,
            message=message,
            why=why,
            throttling_reason=throttling_reason,
            policy_reason=policy_reason,
            latency_ms=latency_ms,
            action=None,  # Will be updated if user interacts
            metadata=metadata or {}
        )
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO shadow_logs 
            (timestamp, pattern_id, confidence, message, why, throttling_reason, 
             policy_reason, latency_ms, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_entry.timestamp,
            log_entry.pattern_id,
            log_entry.confidence,
            log_entry.message,
            log_entry.why,
            log_entry.throttling_reason,
            log_entry.policy_reason,
            log_entry.latency_ms,
            json.dumps(log_entry.metadata)
        ))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[SHADOW] {log_entry.timestamp}: {message} (conf: {confidence:.2f}, {latency_ms:.1f}ms)")
        
        return str(log_id)
        
    def log_user_action(self, log_id: str, action: str):
        """Log user action for a shadow suggestion"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE shadow_logs 
            SET action = ? 
            WHERE id = ?
        """, (action, log_id))
        
        conn.commit()
        conn.close()
        
        print(f"[SHADOW] User {action} suggestion {log_id}")
        
    def calculate_daily_kpis(self, date: str = None) -> Dict[str, Any]:
        """Calculate KPIs for a specific date"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all logs for the date
        cursor.execute("""
            SELECT pattern_id, confidence, latency_ms, action, throttling_reason, policy_reason
            FROM shadow_logs 
            WHERE DATE(timestamp) = ?
        """, (date,))
        
        logs = cursor.fetchall()
        conn.close()
        
        if not logs:
            return {
                "date": date,
                "total_suggestions": 0,
                "accepted": 0,
                "declined": 0,
                "snoozed": 0,
                "never_interacted": 0,
                "accept_rate": 0.0,
                "avg_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "quiet_hour_violations": 0,
                "top_patterns": []
            }
        
        # Calculate metrics
        total = len(logs)
        accepted = sum(1 for log in logs if log[3] == "accepted")
        declined = sum(1 for log in logs if log[3] == "declined")
        snoozed = sum(1 for log in logs if log[3] == "snoozed")
        never = sum(1 for log in logs if log[3] is None)
        
        latencies = [log[2] for log in logs if log[2] is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
        
        # Quiet hour violations (suggestions with policy_reason containing "quiet")
        quiet_violations = sum(1 for log in logs if log[5] and "quiet" in log[5].lower())
        
        # Top patterns
        pattern_counts = {}
        for log in logs:
            pattern_id = log[0]
            if pattern_id:
                pattern_counts[pattern_id] = pattern_counts.get(pattern_id, 0) + 1
        
        top_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "date": date,
            "total_suggestions": total,
            "accepted": accepted,
            "declined": declined,
            "snoozed": snoozed,
            "never_interacted": never,
            "accept_rate": (accepted / total * 100) if total > 0 else 0.0,
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "quiet_hour_violations": quiet_violations,
            "top_patterns": top_patterns
        }
        
    def store_daily_kpis(self, kpis: Dict[str, Any]):
        """Store calculated KPIs in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO shadow_kpis 
            (date, total_suggestions, accepted, declined, snoozed, never_interacted,
             avg_latency_ms, p95_latency_ms, quiet_hour_violations, top_patterns)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            kpis["date"],
            kpis["total_suggestions"],
            kpis["accepted"],
            kpis["declined"],
            kpis["snoozed"],
            kpis["never_interacted"],
            kpis["avg_latency_ms"],
            kpis["p95_latency_ms"],
            kpis["quiet_hour_violations"],
            json.dumps(kpis["top_patterns"])
        ))
        
        conn.commit()
        conn.close()
        
    def export_shadow_report(self, days: int = 7) -> str:
        """Export comprehensive shadow mode report"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        report_lines = [
            "# B4 Proactive AI - Shadow Mode Report",
            f"**Generated:** {end_date.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Period:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({days} days)",
            "",
            "## Executive Summary",
            ""
        ]
        
        # Calculate overall metrics
        total_kpis = {"total_suggestions": 0, "accepted": 0, "declined": 0, "p95_latency_ms": []}
        daily_reports = []
        
        for i in range(days):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            kpis = self.calculate_daily_kpis(date)
            daily_reports.append(kpis)
            
            total_kpis["total_suggestions"] += kpis["total_suggestions"]
            total_kpis["accepted"] += kpis["accepted"]
            total_kpis["declined"] += kpis["declined"]
            if kpis["p95_latency_ms"] > 0:
                total_kpis["p95_latency_ms"].append(kpis["p95_latency_ms"])
        
        overall_accept_rate = (total_kpis["accepted"] / total_kpis["total_suggestions"] * 100) if total_kpis["total_suggestions"] > 0 else 0
        overall_p95 = max(total_kpis["p95_latency_ms"]) if total_kpis["p95_latency_ms"] else 0
        
        # Executive summary
        report_lines.extend([
            f"- **Total Suggestions:** {total_kpis['total_suggestions']}",
            f"- **Accept Rate:** {overall_accept_rate:.1f}% (Target: ≥60%)",
            f"- **P95 Latency:** {overall_p95:.1f}ms (Target: ≤200ms)",
            f"- **Performance:** {'✅ PASS' if overall_p95 <= 200 else '❌ FAIL'}",
            f"- **User Satisfaction:** {'✅ PASS' if overall_accept_rate >= 60 else '⚠️ REVIEW'}",
            "",
            "## Daily Breakdown",
            "",
            "| Date | Suggestions | Accept Rate | P95 Latency | Status |",
            "|------|------------|-------------|-------------|---------|"
        ])
        
        for kpis in daily_reports:
            status = "✅" if kpis["p95_latency_ms"] <= 200 and kpis["accept_rate"] >= 60 else "⚠️"
            report_lines.append(
                f"| {kpis['date']} | {kpis['total_suggestions']} | {kpis['accept_rate']:.1f}% | {kpis['p95_latency_ms']:.1f}ms | {status} |"
            )
        
        # Recommendations
        report_lines.extend([
            "",
            "## Recommendations",
            ""
        ])
        
        if overall_accept_rate < 60:
            report_lines.append("- 🔧 **Increase confidence threshold** to 0.75 (currently likely 0.70)")
        elif overall_accept_rate > 80:
            report_lines.append("- 📈 **Consider lowering confidence threshold** to 0.65 for more suggestions")
        else:
            report_lines.append("- ✅ **Keep current confidence threshold** (0.70) - good balance")
        
        if overall_p95 > 200:
            report_lines.append("- ⚡ **Optimize pattern recognition** - latency too high")
        else:
            report_lines.append("- ✅ **Performance acceptable** - latency within targets")
        
        # Export to file
        export_dir = Path("export")
        export_dir.mkdir(exist_ok=True)
        
        filename = f"proactive_report_{end_date.strftime('%Y%m%d')}.md"
        filepath = export_dir / filename
        
        with open(filepath, "w") as f:
            f.write("\n".join(report_lines))
        
        print(f"📊 Shadow report exported to: {filepath}")
        return str(filepath)

# Global shadow instance
shadow = ProactiveShadow()