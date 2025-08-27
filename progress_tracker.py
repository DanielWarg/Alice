#!/usr/bin/env python3
"""
📊 Alice Progress Tracking System - Development Activity Logger
Tracks and logs development activities like a diary/logbook for the Alice project.
"""

import asyncio
import json
import time
import os
import sys
import subprocess
import psutil
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import aiofiles
import requests

@dataclass
class ProgressEntry:
    """Structure for a single progress log entry"""
    timestamp: str
    entry_type: str  # commit, test, deployment, metric, issue, milestone
    category: str    # code_change, system_status, performance, bug_fix, feature
    title: str
    description: str
    metadata: Dict[str, Any]
    tags: List[str]
    impact_level: str  # low, medium, high, critical
    
class ProgressTracker:
    """Main progress tracking system for Alice project"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "progress_tracker_config.json"
        self.config = self.load_config()
        self.db_path = self.config.get("db_path", "progress_tracking.db")
        self.log_dir = Path(self.config.get("log_dir", "logs/progress"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Daily log file
        today = datetime.now().strftime("%Y-%m-%d")
        self.daily_log_file = self.log_dir / f"progress_{today}.json"
        
        # Initialize database
        self.init_database()
        
        # Tracking state
        self.running = True
        self.last_git_commit = None
        self.last_system_check = None
        self.performance_baseline = {}
        
        print(f"📊 Alice Progress Tracker initialized")
        print(f"📁 Daily log: {self.daily_log_file}")
        print(f"💾 Database: {self.db_path}")
    
    def load_config(self) -> Dict[str, Any]:
        """Load or create default configuration"""
        default_config = {
            "tracking_enabled": True,
            "log_dir": "logs/progress",
            "db_path": "progress_tracking.db",
            "tracking_intervals": {
                "git_monitor": 30,      # seconds
                "system_health": 60,    # seconds  
                "performance": 300,     # seconds (5 minutes)
                "test_results": 120     # seconds
            },
            "track_categories": [
                "commits", "tests", "deployments", 
                "performance", "issues", "milestones",
                "system_health", "api_usage"
            ],
            "alert_thresholds": {
                "cpu_usage": 80,
                "memory_usage": 85,
                "response_time_ms": 2000
            },
            "summary_generation": {
                "daily_summary": True,
                "weekly_summary": True,
                "milestone_detection": True
            }
        }
        
        if Path(self.config_path).exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                print(f"⚠️ Error loading config, using defaults: {e}")
                return default_config
        else:
            # Create default config file
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def init_database(self):
        """Initialize SQLite database for progress tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main progress entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS progress_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                metadata TEXT,
                tags TEXT,
                impact_level TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Git commits tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS git_commits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                commit_hash TEXT UNIQUE NOT NULL,
                author TEXT,
                message TEXT,
                timestamp TEXT,
                files_changed INTEGER,
                insertions INTEGER,
                deletions INTEGER,
                tracked_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # System metrics tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_percent REAL,
                memory_percent REAL,
                disk_usage_percent REAL,
                active_processes INTEGER,
                response_time_ms REAL,
                tracked_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Test results tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                test_suite TEXT,
                tests_run INTEGER,
                tests_passed INTEGER,
                tests_failed INTEGER,
                test_duration REAL,
                test_details TEXT,
                tracked_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def log_progress_entry(self, entry: ProgressEntry):
        """Log a progress entry to both database and daily file"""
        # Add to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO progress_entries 
            (timestamp, entry_type, category, title, description, metadata, tags, impact_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.timestamp, entry.entry_type, entry.category, entry.title,
            entry.description, json.dumps(entry.metadata), json.dumps(entry.tags), entry.impact_level
        ))
        
        conn.commit()
        conn.close()
        
        # Add to daily log file
        try:
            # Read existing entries
            if self.daily_log_file.exists():
                async with aiofiles.open(self.daily_log_file, 'r') as f:
                    content = await f.read()
                    daily_entries = json.loads(content) if content.strip() else []
            else:
                daily_entries = []
            
            # Add new entry
            daily_entries.append(asdict(entry))
            
            # Write back
            async with aiofiles.open(self.daily_log_file, 'w') as f:
                await f.write(json.dumps(daily_entries, indent=2, ensure_ascii=False))
                
        except Exception as e:
            print(f"❌ Error writing to daily log: {e}")
        
        # Console output with color coding
        color_map = {
            'commit': '🔧',
            'test': '🧪', 
            'deployment': '🚀',
            'metric': '📊',
            'issue': '🐛',
            'milestone': '🎯'
        }
        
        icon = color_map.get(entry.entry_type, '📝')
        timestamp_short = entry.timestamp.split('T')[1][:8]  # HH:MM:SS
        print(f"{icon} [{timestamp_short}] {entry.category}: {entry.title}")
        
        if entry.impact_level in ['high', 'critical']:
            print(f"   ⚠️ {entry.impact_level.upper()} IMPACT: {entry.description}")
    
    async def monitor_git_activity(self):
        """Monitor git commits and changes"""
        while self.running:
            try:
                # Get latest commit info
                result = subprocess.run([
                    'git', 'log', '-1', '--format=%H|%an|%s|%ad', '--date=iso'
                ], capture_output=True, text=True, cwd='.')
                
                if result.returncode == 0:
                    commit_info = result.stdout.strip()
                    if commit_info and commit_info != self.last_git_commit:
                        parts = commit_info.split('|')
                        if len(parts) >= 4:
                            commit_hash, author, message, timestamp = parts
                            
                            # Get commit statistics
                            stats_result = subprocess.run([
                                'git', 'show', '--stat', '--format=', commit_hash
                            ], capture_output=True, text=True, cwd='.')
                            
                            files_changed = 0
                            insertions = 0
                            deletions = 0
                            
                            if stats_result.returncode == 0:
                                stats_lines = stats_result.stdout.strip().split('\n')
                                for line in stats_lines:
                                    if 'files changed' in line:
                                        # Parse: "X files changed, Y insertions(+), Z deletions(-)"
                                        parts = line.split(',')
                                        for part in parts:
                                            if 'files changed' in part:
                                                files_changed = int(part.split()[0])
                                            elif 'insertion' in part:
                                                insertions = int(part.split()[0])
                                            elif 'deletion' in part:
                                                deletions = int(part.split()[0])
                            
                            # Store in database
                            conn = sqlite3.connect(self.db_path)
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT OR REPLACE INTO git_commits 
                                (commit_hash, author, message, timestamp, files_changed, insertions, deletions)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (commit_hash, author, message, timestamp, files_changed, insertions, deletions))
                            conn.commit()
                            conn.close()
                            
                            # Log as progress entry
                            entry = ProgressEntry(
                                timestamp=datetime.now().isoformat(),
                                entry_type='commit',
                                category='code_change',
                                title=f"New commit by {author}",
                                description=message,
                                metadata={
                                    'commit_hash': commit_hash,
                                    'author': author,
                                    'files_changed': files_changed,
                                    'insertions': insertions,
                                    'deletions': deletions
                                },
                                tags=['git', 'commit'],
                                impact_level='medium' if files_changed > 5 else 'low'
                            )
                            
                            await self.log_progress_entry(entry)
                            self.last_git_commit = commit_info
                
            except Exception as e:
                print(f"❌ Git monitoring error: {e}")
            
            await asyncio.sleep(self.config['tracking_intervals']['git_monitor'])
    
    async def monitor_system_health(self):
        """Monitor system performance and health"""
        while self.running:
            try:
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Count Alice processes
                alice_processes = 0
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                        if any(keyword in cmdline.lower() for keyword in ['alice', 'uvicorn', 'next']):
                            alice_processes += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                # Test API response time
                response_time_ms = None
                try:
                    start_time = time.time()
                    response = requests.get('http://localhost:8000/api/tools/spec', timeout=5)
                    response_time_ms = (time.time() - start_time) * 1000
                except:
                    response_time_ms = None
                
                # Store metrics
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO system_metrics 
                    (timestamp, cpu_percent, memory_percent, disk_usage_percent, active_processes, response_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    cpu_percent,
                    memory.percent,
                    disk.percent,
                    alice_processes,
                    response_time_ms
                ))
                conn.commit()
                conn.close()
                
                # Check for alerts
                alert_needed = False
                alert_reasons = []
                
                if cpu_percent > self.config['alert_thresholds']['cpu_usage']:
                    alert_needed = True
                    alert_reasons.append(f"High CPU usage: {cpu_percent}%")
                
                if memory.percent > self.config['alert_thresholds']['memory_usage']:
                    alert_needed = True
                    alert_reasons.append(f"High memory usage: {memory.percent}%")
                
                if response_time_ms and response_time_ms > self.config['alert_thresholds']['response_time_ms']:
                    alert_needed = True
                    alert_reasons.append(f"Slow API response: {response_time_ms:.1f}ms")
                
                if alert_needed:
                    entry = ProgressEntry(
                        timestamp=datetime.now().isoformat(),
                        entry_type='metric',
                        category='system_health',
                        title="System performance alert",
                        description="; ".join(alert_reasons),
                        metadata={
                            'cpu_percent': cpu_percent,
                            'memory_percent': memory.percent,
                            'disk_percent': disk.percent,
                            'processes': alice_processes,
                            'response_time_ms': response_time_ms
                        },
                        tags=['system', 'alert', 'performance'],
                        impact_level='high'
                    )
                    await self.log_progress_entry(entry)
                
            except Exception as e:
                print(f"❌ System health monitoring error: {e}")
            
            await asyncio.sleep(self.config['tracking_intervals']['system_health'])
    
    async def monitor_test_results(self):
        """Monitor for test execution and results"""
        while self.running:
            try:
                # Look for recent test files or results
                test_patterns = [
                    'test_results_*.json',
                    'pytest_report_*.xml',
                    '*.test.log'
                ]
                
                # Check for recent test artifacts
                recent_tests = []
                for pattern in test_patterns:
                    for file_path in Path('.').rglob(pattern):
                        if file_path.stat().st_mtime > time.time() - 300:  # Last 5 minutes
                            recent_tests.append(file_path)
                
                if recent_tests:
                    for test_file in recent_tests:
                        try:
                            # Try to parse test results
                            if test_file.suffix == '.json':
                                with open(test_file, 'r') as f:
                                    test_data = json.load(f)
                                
                                entry = ProgressEntry(
                                    timestamp=datetime.now().isoformat(),
                                    entry_type='test',
                                    category='quality_assurance',
                                    title=f"Test results: {test_file.name}",
                                    description=f"Test execution completed",
                                    metadata=test_data,
                                    tags=['testing', 'qa'],
                                    impact_level='medium'
                                )
                                await self.log_progress_entry(entry)
                        except Exception as e:
                            print(f"⚠️ Error parsing test file {test_file}: {e}")
                
            except Exception as e:
                print(f"❌ Test monitoring error: {e}")
            
            await asyncio.sleep(self.config['tracking_intervals']['test_results'])
    
    async def detect_milestones(self):
        """Detect and log development milestones"""
        while self.running:
            try:
                # Check for milestone indicators
                milestones_detected = []
                
                # Check git tags (version releases)
                result = subprocess.run([
                    'git', 'tag', '--sort=-creatordate'
                ], capture_output=True, text=True, cwd='.')
                
                if result.returncode == 0:
                    tags = result.stdout.strip().split('\n')
                    if tags and tags[0]:  # Latest tag
                        latest_tag = tags[0]
                        # Check if this tag is recent (last 24 hours)
                        tag_info = subprocess.run([
                            'git', 'log', '-1', '--format=%ad', '--date=iso', latest_tag
                        ], capture_output=True, text=True, cwd='.')
                        
                        if tag_info.returncode == 0:
                            tag_date = datetime.fromisoformat(tag_info.stdout.strip().replace(' ', 'T'))
                            if datetime.now() - tag_date < timedelta(hours=24):
                                milestones_detected.append({
                                    'type': 'version_release',
                                    'version': latest_tag,
                                    'date': tag_date.isoformat()
                                })
                
                # Check for significant commit counts
                commits_today = subprocess.run([
                    'git', 'rev-list', '--count', '--since="24 hours ago"', 'HEAD'
                ], capture_output=True, text=True, cwd='.')
                
                if commits_today.returncode == 0:
                    count = int(commits_today.stdout.strip() or 0)
                    if count >= 10:  # 10+ commits in a day
                        milestones_detected.append({
                            'type': 'high_activity',
                            'commits_count': count,
                            'timeframe': '24_hours'
                        })
                
                # Log milestones
                for milestone in milestones_detected:
                    entry = ProgressEntry(
                        timestamp=datetime.now().isoformat(),
                        entry_type='milestone',
                        category='development',
                        title=f"Milestone: {milestone['type'].replace('_', ' ').title()}",
                        description=f"Detected milestone: {milestone}",
                        metadata=milestone,
                        tags=['milestone', milestone['type']],
                        impact_level='high'
                    )
                    await self.log_progress_entry(entry)
                
            except Exception as e:
                print(f"❌ Milestone detection error: {e}")
            
            # Check less frequently
            await asyncio.sleep(3600)  # 1 hour
    
    async def generate_daily_summary(self):
        """Generate daily progress summary"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Query today's activities
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get today's progress entries
            cursor.execute('''
                SELECT entry_type, category, COUNT(*) as count 
                FROM progress_entries 
                WHERE DATE(timestamp) = DATE('now') 
                GROUP BY entry_type, category
            ''')
            activity_summary = cursor.fetchall()
            
            # Get today's commits
            cursor.execute('''
                SELECT COUNT(*), SUM(files_changed), SUM(insertions), SUM(deletions)
                FROM git_commits 
                WHERE DATE(timestamp) = DATE('now')
            ''')
            commit_stats = cursor.fetchone()
            
            # Get system health summary
            cursor.execute('''
                SELECT AVG(cpu_percent), AVG(memory_percent), AVG(response_time_ms)
                FROM system_metrics 
                WHERE DATE(timestamp) = DATE('now')
            ''')
            health_stats = cursor.fetchone()
            
            conn.close()
            
            # Generate summary
            summary = {
                'date': today,
                'generated_at': datetime.now().isoformat(),
                'activity_summary': {
                    f"{activity[0]}_{activity[1]}": activity[2] 
                    for activity in activity_summary
                },
                'git_activity': {
                    'commits': commit_stats[0] or 0,
                    'files_changed': commit_stats[1] or 0,
                    'insertions': commit_stats[2] or 0,
                    'deletions': commit_stats[3] or 0
                } if commit_stats[0] else {},
                'system_health': {
                    'avg_cpu_percent': round(health_stats[0] or 0, 2),
                    'avg_memory_percent': round(health_stats[1] or 0, 2),
                    'avg_response_time_ms': round(health_stats[2] or 0, 2)
                } if health_stats[0] else {}
            }
            
            # Save summary
            summary_file = self.log_dir / f"daily_summary_{today}.json"
            async with aiofiles.open(summary_file, 'w') as f:
                await f.write(json.dumps(summary, indent=2))
            
            print(f"📋 Daily summary generated: {summary_file}")
            
            # Log the summary generation
            entry = ProgressEntry(
                timestamp=datetime.now().isoformat(),
                entry_type='milestone',
                category='reporting',
                title="Daily summary generated",
                description=f"Summary for {today} - {sum(summary['activity_summary'].values())} total activities",
                metadata=summary,
                tags=['summary', 'daily', 'reporting'],
                impact_level='low'
            )
            await self.log_progress_entry(entry)
            
        except Exception as e:
            print(f"❌ Error generating daily summary: {e}")
    
    async def run(self):
        """Main tracking loop"""
        print("🚀 Starting Alice Progress Tracker...")
        
        # Start all monitoring tasks
        tasks = [
            self.monitor_git_activity(),
            self.monitor_system_health(),
            self.monitor_test_results(), 
            self.detect_milestones()
        ]
        
        # Schedule daily summary generation
        async def daily_summary_scheduler():
            while self.running:
                # Generate summary at end of day (23:55)
                now = datetime.now()
                if now.hour == 23 and now.minute == 55:
                    await self.generate_daily_summary()
                    await asyncio.sleep(3600)  # Wait an hour to avoid duplicate
                await asyncio.sleep(60)  # Check every minute
        
        tasks.append(daily_summary_scheduler())
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n🛑 Progress tracker stopped by user")
        except Exception as e:
            print(f"❌ Progress tracker error: {e}")
        finally:
            self.running = False
    
    def get_recent_progress(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent progress entries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM progress_entries 
            WHERE datetime(timestamp) > datetime('now', '-{} hours')
            ORDER BY timestamp DESC
        '''.format(hours))
        
        columns = ['id', 'timestamp', 'entry_type', 'category', 'title', 'description', 
                  'metadata', 'tags', 'impact_level', 'created_at']
        
        results = []
        for row in cursor.fetchall():
            entry = dict(zip(columns, row))
            entry['metadata'] = json.loads(entry['metadata']) if entry['metadata'] else {}
            entry['tags'] = json.loads(entry['tags']) if entry['tags'] else []
            results.append(entry)
        
        conn.close()
        return results

def main():
    """Command line interface for progress tracker"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Alice Progress Tracker')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--summary', action='store_true', help='Generate daily summary')
    parser.add_argument('--recent', type=int, default=24, help='Show recent progress (hours)')
    
    args = parser.parse_args()
    
    tracker = ProgressTracker(config_path=args.config)
    
    if args.summary:
        asyncio.run(tracker.generate_daily_summary())
    elif args.recent:
        entries = tracker.get_recent_progress(hours=args.recent)
        print(f"\n📊 Recent Progress ({args.recent} hours):")
        print("=" * 60)
        for entry in entries:
            timestamp_short = entry['timestamp'].split('T')[1][:8]
            print(f"[{timestamp_short}] {entry['category']}: {entry['title']}")
    else:
        # Run the main tracker
        try:
            asyncio.run(tracker.run())
        except KeyboardInterrupt:
            print("\n👋 Progress tracker stopped")

if __name__ == "__main__":
    main()