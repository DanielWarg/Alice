#!/usr/bin/env python3
"""
🧹 Alice Smart Cleanup Script - Uppdaterad Version
Baserat på vår omfattande städning av Alice-projektet

Kör automatiskt före start för optimal prestanda.
"""

import os
import shutil
import glob
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Set
import json
import time

class AliceSmartCleanup:
    """Smart cleanup baserat på lärdomar från manuell städning"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.dry_run = False
        self.actions_taken: List[str] = []
        self.files_removed = 0
        self.space_saved = 0
        
    def log_action(self, action: str, details: str = ""):
        """Log cleanup action"""
        full_action = f"{'[DRY RUN] ' if self.dry_run else ''}{action}"
        if details:
            full_action += f" - {details}"
        self.actions_taken.append(full_action)
        print(f"✓ {full_action}")
        
    def get_file_size(self, path: Path) -> int:
        """Get file or directory size in bytes"""
        try:
            if path.is_file():
                return path.stat().st_size
            elif path.is_dir():
                return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        except (OSError, PermissionError):
            return 0
        return 0
        
    def safe_remove(self, path: Path, reason: str):
        """Safely remove file or directory with logging"""
        if not path.exists():
            return
            
        size = self.get_file_size(path)
        self.space_saved += size
        
        if not self.dry_run:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                self.files_removed += 1
            except (OSError, PermissionError) as e:
                self.log_action(f"ERROR removing {path}", f"Permission denied: {e}")
                return
            
        size_mb = size / (1024 * 1024)
        self.log_action(f"Remove {path.relative_to(self.project_root)}", 
                       f"{reason} (saved {size_mb:.1f}MB)")
        
    def cleanup_cache_files(self):
        """Remove all cache files based on our experience"""
        print("\\n🐍 Cleaning cache files...")
        
        cache_patterns = [
            # Python cache (keep Alice core, remove dependencies)
            '**/.venv/lib/python*/site-packages/**/__pycache__',
            '**/venv/lib/python*/site-packages/**/__pycache__',
            '**/node_modules/**/__pycache__',
            
            # Pytest cache
            '**/.pytest_cache',
            
            # Next.js cache
            'web/.next/cache',
            
            # Python compiled files (not in core Alice dirs)
            'server/*.pyc',
            '__pycache__/*.pyc'
        ]
        
        # Keep Alice core __pycache__ directories
        alice_core_paths = {
            'server/__pycache__',
            'server/llm/__pycache__', 
            'server/core/__pycache__',
            'server/agents/__pycache__',
            'server/agent/__pycache__',
            'server/agent/tools/__pycache__',
            'server/tests/__pycache__',
            'server/evals/__pycache__',
            'server/prompts/__pycache__',
            'server/services/__pycache__',
            'server/services/voice_gateway/__pycache__',
            'tests/__pycache__'
        }
        
        for pattern in cache_patterns:
            for path in self.project_root.glob(pattern):
                rel_path = str(path.relative_to(self.project_root))
                
                # Skip Alice core caches
                if any(core_path in rel_path for core_path in alice_core_paths):
                    continue
                    
                self.safe_remove(Path(path), "dependency cache")
                
    def cleanup_test_artifacts(self):
        """Remove test databases and artifacts from server root"""
        print("\\n🧪 Cleaning test artifacts...")
        
        # Test databases in server root (not in data/)
        test_db_patterns = [
            'server/test_*.db*',
            'server/stress_test*.db*', 
            'server/*_test.db*',
            'server/*.db-wal',
            'server/*.db-shm'
        ]
        
        for pattern in test_db_patterns:
            for db_file in self.project_root.glob(pattern):
                # Skip data/ directory databases
                if 'data/' in str(db_file):
                    continue
                # Skip proactive.db (hardcoded location)
                if db_file.name == 'proactive.db':
                    continue
                self.safe_remove(db_file, "test database artifact")
        
        # Test audio files
        test_audio_patterns = [
            'server/test*.wav',
            'server/tts_test.wav',
            'server/*_test.wav'
        ]
        
        for pattern in test_audio_patterns:
            for audio_file in self.project_root.glob(pattern):
                self.safe_remove(audio_file, "test audio artifact")
        
        # Test JSON files
        test_json_patterns = [
            'server/test_*.json',
            'server/integration_test_results_*.json'
        ]
        
        for pattern in test_json_patterns:
            for json_file in self.project_root.glob(pattern):
                self.safe_remove(json_file, "test data artifact")
                
    def cleanup_logs_and_temp(self):
        """Remove old logs and temporary files"""
        print("\\n📋 Cleaning logs and temporary files...")
        
        temp_patterns = [
            '**/.DS_Store',
            '**/Thumbs.db',
            '**/*.tmp',
            '**/*.temp',
            '**/npm-debug.log*',
            '**/yarn-debug.log*',
            '**/yarn-error.log*',
            '**/.coverage',
            '**/coverage.xml'
        ]
        
        for pattern in temp_patterns:
            for temp_file in self.project_root.glob(pattern):
                self.safe_remove(temp_file, "temporary file")
        
        # Old log files (but keep server.log if recent)
        for log_file in self.project_root.rglob('*.log'):
            # Skip logs in proper log directories
            if 'logs/' in str(log_file) or '/log/' in str(log_file):
                continue
                
            # Check if file is old (>7 days)
            try:
                file_age = time.time() - log_file.stat().st_mtime
                if file_age > 7 * 24 * 3600:  # 7 days in seconds
                    self.safe_remove(log_file, "old log file")
            except OSError:
                continue
                
    def organize_misplaced_files(self):
        """Move files that should not be in root"""
        print("\\n📂 Organizing misplaced files...")
        
        # Move test scripts from web root to tests
        web_test_files = [
            'web/console-voice-test.js',
            'web/quick-ws-test.js', 
            'web/voice-end-to-end-test.js',
            'web/voice-flow-test.js',
            'web/test_*.html'
        ]
        
        web_tests_dir = self.project_root / 'web' / 'tests'
        web_tests_dir.mkdir(exist_ok=True)
        
        for pattern in web_test_files:
            for test_file in self.project_root.glob(pattern):
                if not self.dry_run:
                    dest = web_tests_dir / test_file.name
                    try:
                        shutil.move(str(test_file), str(dest))
                        self.log_action(f"Moved {test_file.name} to web/tests/", "organization")
                    except OSError:
                        pass
                        
    def optimize_databases(self):
        """Optimize SQLite databases"""
        print("\\n🗄️ Optimizing databases...")
        
        for db_file in self.project_root.rglob('*.db'):
            # Skip temporary database files
            if db_file.name.endswith(('.db-shm', '.db-wal')):
                continue
                
            if not self.dry_run:
                try:
                    # Run SQLite VACUUM to optimize database
                    result = subprocess.run(
                        ['sqlite3', str(db_file), 'VACUUM;'], 
                        check=True, 
                        capture_output=True,
                        timeout=30
                    )
                    self.log_action(f"Optimized {db_file.name}", "SQLite VACUUM")
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                    pass  # Skip if sqlite3 not available or timeout
            else:
                self.log_action(f"Would optimize {db_file.name}", "SQLite VACUUM")
                
    def validate_project_health(self):
        """Check that critical files exist"""
        print("\\n✅ Validating project health...")
        
        critical_files = [
            'server/app.py',
            'web/package.json',
            'README.md',
            'VISION.md',
            'start_alice.sh'
        ]
        
        missing_files = []
        for critical_file in critical_files:
            if not (self.project_root / critical_file).exists():
                missing_files.append(critical_file)
                
        if missing_files:
            self.log_action(f"WARNING: Missing critical files", ', '.join(missing_files))
        else:
            self.log_action("Project health check", "All critical files present")
            
    def generate_cleanup_report(self) -> Dict:
        """Generate summary report of cleanup actions"""
        return {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'actions_taken': len(self.actions_taken),
            'files_removed': self.files_removed,
            'space_saved_mb': round(self.space_saved / (1024 * 1024), 2),
            'dry_run': self.dry_run,
            'details': self.actions_taken[-20:] if len(self.actions_taken) > 20 else self.actions_taken  # Last 20 actions
        }
        
    def run_smart_cleanup(self, quick: bool = False):
        """Execute smart cleanup process"""
        print("🧹 Alice Smart Cleanup Starting...")
        print(f"📁 Project root: {self.project_root}")
        print(f"🎭 Mode: {'DRY RUN (preview only)' if self.dry_run else 'EXECUTE (making changes)'}")
        print(f"⚡ Type: {'Quick cleanup' if quick else 'Full cleanup'}")
        
        # Always run these (fast)
        self.cleanup_cache_files()
        self.cleanup_test_artifacts()
        self.cleanup_logs_and_temp()
        
        if not quick:
            # Full cleanup includes these (slower)
            self.organize_misplaced_files()
            self.optimize_databases()
            
        self.validate_project_health()
        
        # Generate report
        report = self.generate_cleanup_report()
        
        print("\\n📊 Cleanup Complete!")
        print(f"   Actions taken: {report['actions_taken']}")
        print(f"   Files removed: {report['files_removed']}")
        print(f"   Space saved: {report['space_saved_mb']}MB")
        
        if self.dry_run:
            print("\\n💡 Run with --execute to actually perform cleanup")
        else:
            # Save report for reference
            report_file = self.project_root / 'last_cleanup.json'
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"📄 Cleanup report saved to: {report_file}")
            
        return report

def main():
    parser = argparse.ArgumentParser(description='Alice Smart Cleanup Script')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without executing')
    parser.add_argument('--execute', action='store_true',
                       help='Actually perform cleanup operations')
    parser.add_argument('--quick', action='store_true',
                       help='Quick cleanup (cache and test artifacts only)')
    parser.add_argument('--project-root', type=str, default=None,
                       help='Project root directory (default: current directory)')
    
    args = parser.parse_args()
    
    # Determine mode (default to dry run for safety)
    dry_run = not args.execute
    
    # Initialize cleanup system
    cleaner = AliceSmartCleanup(args.project_root)
    cleaner.dry_run = dry_run
    
    # Run cleanup
    try:
        report = cleaner.run_smart_cleanup(quick=args.quick)
        
        if not dry_run and report['files_removed'] > 0:
            print(f"\\n🎉 Cleanup successful! Alice should run faster now.")
            
    except KeyboardInterrupt:
        print("\\n⚠️ Cleanup interrupted by user")
    except Exception as e:
        print(f"\\n❌ Cleanup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()