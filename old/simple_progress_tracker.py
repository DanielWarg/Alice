#!/usr/bin/env python3
"""
Simple Progress Tracker for Alice Development
Tracks activities without external dependencies
"""

import os
import sys
import json
import time
import datetime
import subprocess
import threading
from pathlib import Path

class SimpleProgressTracker:
    def __init__(self):
        self.start_time = time.time()
        self.log_dir = Path("logs/progress")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.daily_log = self.log_dir / f"progress-{datetime.datetime.now().strftime('%Y-%m-%d')}.json"
        self.activities = []
        
        # Initialize log file
        self.log_activity("system", "Progress tracker started", {"tracker": "simple", "version": "1.0"})
    
    def log_activity(self, category, description, details=None):
        """Log an activity with timestamp"""
        activity = {
            "timestamp": datetime.datetime.now().isoformat(),
            "category": category,
            "description": description,
            "details": details or {},
            "session_duration": time.time() - self.start_time
        }
        
        self.activities.append(activity)
        
        # Write to daily log
        try:
            with open(self.daily_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(activity) + '\n')
        except Exception as e:
            print(f"Failed to write to log: {e}")
        
        # Console output
        print(f"📊 [{activity['timestamp'][:19]}] {category.upper()}: {description}")
        if details:
            print(f"   Details: {details}")
    
    def check_git_status(self):
        """Check git status and log changes"""
        try:
            # Get current branch
            branch_result = subprocess.run(
                ['git', 'branch', '--show-current'], 
                capture_output=True, text=True, timeout=5
            )
            
            # Get status
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'], 
                capture_output=True, text=True, timeout=5
            )
            
            if branch_result.returncode == 0 and status_result.returncode == 0:
                branch = branch_result.stdout.strip()
                changes = status_result.stdout.strip()
                
                if changes:
                    modified = len([line for line in changes.split('\n') if line.startswith(' M')])
                    added = len([line for line in changes.split('\n') if line.startswith('A ')])
                    untracked = len([line for line in changes.split('\n') if line.startswith('??')])
                    
                    self.log_activity("git", "Working tree changes detected", {
                        "branch": branch,
                        "modified": modified,
                        "added": added,
                        "untracked": untracked
                    })
                
        except Exception as e:
            self.log_activity("error", f"Git status check failed: {e}")
    
    def track_test_activity(self, test_type, status, details=None):
        """Track test execution"""
        self.log_activity("testing", f"{test_type} test {status}", details)
    
    def track_code_activity(self, activity_type, description, details=None):
        """Track code development activity"""
        self.log_activity("development", f"{activity_type}: {description}", details)
    
    def track_milestone(self, milestone, details=None):
        """Track development milestones"""
        self.log_activity("milestone", milestone, details)
    
    def generate_summary(self):
        """Generate activity summary"""
        if not self.activities:
            return "No activities tracked yet."
        
        total_duration = time.time() - self.start_time
        categories = {}
        
        for activity in self.activities:
            cat = activity['category']
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
        
        summary = {
            "session_duration_minutes": round(total_duration / 60, 1),
            "total_activities": len(self.activities),
            "categories": categories,
            "latest_activity": self.activities[-1] if self.activities else None
        }
        
        return json.dumps(summary, indent=2)
    
    def save_session_summary(self):
        """Save session summary"""
        summary_file = self.log_dir / f"session-summary-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_summary())
        
        print(f"📈 Session summary saved to: {summary_file}")

# Global tracker instance
_tracker = None

def get_tracker():
    """Get or create tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = SimpleProgressTracker()
    return _tracker

def log_activity(category, description, details=None):
    """Convenience function to log activity"""
    get_tracker().log_activity(category, description, details)

def track_test(test_type, status, details=None):
    """Convenience function to track tests"""
    get_tracker().track_test_activity(test_type, status, details)

def track_code(activity_type, description, details=None):
    """Convenience function to track code activities"""
    get_tracker().track_code_activity(activity_type, description, details)

def track_milestone(milestone, details=None):
    """Convenience function to track milestones"""
    get_tracker().track_milestone(milestone, details)

if __name__ == "__main__":
    tracker = SimpleProgressTracker()
    
    # Log startup
    tracker.check_git_status()
    tracker.log_activity("system", "Simple progress tracker running")
    
    try:
        # Keep running and check periodically
        while True:
            time.sleep(30)  # Check every 30 seconds
            tracker.check_git_status()
    except KeyboardInterrupt:
        print("\n🛑 Progress tracker stopping...")
        tracker.log_activity("system", "Progress tracker stopped")
        tracker.save_session_summary()
        print("📊 Final summary:")
        print(tracker.generate_summary())