#!/usr/bin/env python3
"""
🧹 Alice Autonomous Cleanup Script
Maintains codebase cleanliness and removes unnecessary artifacts.

Usage:
    python cleanup_alice.py --dry-run    # Preview changes
    python cleanup_alice.py --execute    # Actually perform cleanup
"""

import os
import shutil
import glob
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Set
import json

class AliceCleanup:
    """Autonomous cleanup system for Alice project"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.dry_run = True
        self.actions_taken: List[str] = []
        self.files_removed = 0
        self.space_saved = 0
        
    def set_mode(self, dry_run: bool):
        """Set execution mode"""
        self.dry_run = dry_run
        
    def log_action(self, action: str, details: str = ""):
        """Log cleanup action"""
        full_action = f"{'[DRY RUN] ' if self.dry_run else ''}{action}"
        if details:
            full_action += f" - {details}"
        self.actions_taken.append(full_action)
        print(f"✓ {full_action}")
        
    def get_file_size(self, path: Path) -> int:
        """Get file or directory size in bytes"""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        return 0
        
    def safe_remove(self, path: Path, reason: str):
        """Safely remove file or directory with logging"""
        if not path.exists():
            return
            
        size = self.get_file_size(path)
        self.space_saved += size
        
        if not self.dry_run:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            self.files_removed += 1
            
        size_mb = size / (1024 * 1024)
        self.log_action(f"Remove {path.relative_to(self.project_root)}", 
                       f"{reason} (saved {size_mb:.1f}MB)")
        
    def cleanup_pycache(self):
        """Remove dependency __pycache__ directories"""
        print("\\n🐍 Cleaning Python cache directories...")
        
        # Keep Alice-relevant __pycache__ directories
        alice_paths = {
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
            'server/services/voice_gateway/tests/__pycache__',
            'tests/__pycache__',
            '__pycache__'
        }
        
        for pycache in self.project_root.rglob('__pycache__'):
            rel_path = str(pycache.relative_to(self.project_root))
            
            # Skip Alice-relevant caches
            if any(alice_path in rel_path for alice_path in alice_paths):
                continue
                
            # Remove dependency caches  
            if ('site-packages' in rel_path or 'node_modules' in rel_path or 
                '.venv' in rel_path or 'venv' in rel_path):
                self.safe_remove(pycache, "dependency cache")
                
    def cleanup_temporary_files(self):
        """Remove temporary and build artifacts"""
        print("\\n🗑️ Cleaning temporary files...")
        
        temp_patterns = [
            '**/.DS_Store',
            '**/.pytest_cache',
            '**/node_modules/.cache',
            '**/*.pyc',
            '**/*.pyo', 
            '**/.coverage',
            '**/coverage.xml',
            '**/*.log',
            '**/npm-debug.log*',
            '**/yarn-debug.log*',
            '**/yarn-error.log*',
            '**/.next/cache',
            '**/dist/__pycache__'
        ]
        
        for pattern in temp_patterns:
            for path in self.project_root.glob(pattern):
                # Skip important log files
                if 'alice_monitor' in str(path) or 'server.log' in str(path):
                    continue
                self.safe_remove(Path(path), "temporary file")
                
    def cleanup_old_test_files(self):
        """Remove or flag deprecated test files"""
        print("\\n🧪 Reviewing test files...")
        
        deprecated_tests = [
            'test_voice_always_on.py',  # Contains OpenAI Realtime references
            'test_websocket.py'         # May reference deprecated endpoints
        ]
        
        for test_file in deprecated_tests:
            test_path = self.project_root / test_file
            if test_path.exists():
                # Don't auto-remove, just flag for manual review
                self.log_action(f"FLAG for manual review: {test_file}", 
                               "contains deprecated OpenAI Realtime code")
                
    def cleanup_documentation_duplicates(self):
        """Remove outdated/duplicate documentation"""
        print("\\n📚 Cleaning documentation...")
        
        # Files that were already cleaned in manual review
        outdated_docs = [
            'visionupdated.md',
            'VOICE_PIPELINE_ARCHIVE.md',
            'VOICE_PIPELINE_STATUS.md', 
            'LIVEKIT_VOICE_IMPLEMENTATION.md',
            'LIVEKIT_VOICE_PLAN.md',
            'ALICE_VOICE_GATEWAY_COMPLETE_DESIGN.md',
            'CRITICAL_STATUS_GAPS.md'
        ]
        
        for doc_file in outdated_docs:
            doc_path = self.project_root / doc_file
            if doc_path.exists():
                self.safe_remove(doc_path, "outdated documentation")
                
    def validate_core_files(self):
        """Ensure core files exist and are current"""
        print("\\n✅ Validating core files...")
        
        required_files = {
            'README.md': 'Main project documentation',
            'VISION.md': 'Project vision and goals', 
            'ALICE_ROADMAP.md': 'Development roadmap',
            'STARTUP.md': 'Startup instructions',
            'MODULES.md': 'Component documentation',
            'DEVELOPMENT.md': 'Development guide',
            'TROUBLESHOOTING.md': 'Common issues and fixes'
        }
        
        for file_name, description in required_files.items():
            file_path = self.project_root / file_name
            if not file_path.exists():
                self.log_action(f"MISSING: {file_name}", description)
            else:
                # Check if file is recent (modified in last 30 days)
                import time
                mod_time = file_path.stat().st_mtime
                days_old = (time.time() - mod_time) / (24 * 3600)
                if days_old > 30:
                    self.log_action(f"OLD: {file_name}", f"{days_old:.0f} days since update")
                    
    def optimize_database_files(self):
        """Optimize SQLite database files"""
        print("\\n🗄️ Optimizing databases...")
        
        for db_file in self.project_root.rglob('*.db'):
            # Skip temporary database files
            if db_file.name.endswith(('.db-shm', '.db-wal')):
                continue
                
            if not self.dry_run:
                try:
                    # Run SQLite VACUUM to optimize database
                    subprocess.run(['sqlite3', str(db_file), 'VACUUM;'], 
                                 check=True, capture_output=True)
                    self.log_action(f"Optimized {db_file.name}", "SQLite VACUUM")
                except subprocess.CalledProcessError:
                    self.log_action(f"SKIP {db_file.name}", "SQLite optimization failed")
            else:
                self.log_action(f"Would optimize {db_file.name}", "SQLite VACUUM")
                
    def generate_cleanup_report(self) -> Dict:
        """Generate summary report of cleanup actions"""
        return {
            'actions_taken': len(self.actions_taken),
            'files_removed': self.files_removed,
            'space_saved_mb': self.space_saved / (1024 * 1024),
            'dry_run': self.dry_run,
            'details': self.actions_taken
        }
        
    def run_full_cleanup(self):
        """Execute complete cleanup process"""
        print("🧹 Alice Autonomous Cleanup Starting...")
        print(f"📁 Project root: {self.project_root}")
        print(f"🎭 Mode: {'DRY RUN (preview only)' if self.dry_run else 'EXECUTE (making changes)'}")
        
        # Run all cleanup tasks
        self.cleanup_pycache()
        self.cleanup_temporary_files()  
        self.cleanup_old_test_files()
        self.cleanup_documentation_duplicates()
        self.validate_core_files()
        self.optimize_database_files()
        
        # Generate report
        report = self.generate_cleanup_report()
        
        print("\\n📊 Cleanup Complete!")
        print(f"   Actions taken: {report['actions_taken']}")
        print(f"   Files removed: {report['files_removed']}")
        print(f"   Space saved: {report['space_saved_mb']:.1f}MB")
        
        if self.dry_run:
            print("\\n💡 Run with --execute to actually perform cleanup")
            
        return report

def main():
    parser = argparse.ArgumentParser(description='Alice Autonomous Cleanup Script')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Preview changes without executing (default)')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually perform cleanup operations')
    parser.add_argument('--project-root', type=str, default=None,
                       help='Project root directory (default: current directory)')
    
    args = parser.parse_args()
    
    # Determine mode
    dry_run = not args.execute  # Default to dry run unless --execute is specified
    
    # Initialize cleanup system
    cleaner = AliceCleanup(args.project_root)
    cleaner.set_mode(dry_run)
    
    # Run cleanup
    try:
        report = cleaner.run_full_cleanup()
        
        # Save report
        report_file = Path('cleanup_report.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\\n📄 Detailed report saved to: {report_file}")
        
    except KeyboardInterrupt:
        print("\\n⚠️ Cleanup interrupted by user")
    except Exception as e:
        print(f"\\n❌ Cleanup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()