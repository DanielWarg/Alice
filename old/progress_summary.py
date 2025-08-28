#!/usr/bin/env python3
"""
📊 Alice Progress Summary Generator
Generates comprehensive summaries of development progress and activities.
"""

import json
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import subprocess

class ProgressSummaryGenerator:
    """Generates progress summaries from tracking data"""
    
    def __init__(self, db_path: str = "progress_tracking.db", log_dir: str = "logs/progress"):
        self.db_path = Path(db_path)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def get_database_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get statistics from the database"""
        if not self.db_path.exists():
            return {}
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Date range
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        stats = {}
        
        # Progress entries summary
        cursor.execute('''
            SELECT entry_type, category, COUNT(*), impact_level
            FROM progress_entries 
            WHERE timestamp > ? 
            GROUP BY entry_type, category, impact_level
            ORDER BY COUNT(*) DESC
        ''', (start_date,))
        
        activity_breakdown = defaultdict(lambda: defaultdict(int))
        impact_summary = Counter()
        
        for entry_type, category, count, impact_level in cursor.fetchall():
            activity_breakdown[entry_type][category] += count
            impact_summary[impact_level] += count
        
        stats['activity_breakdown'] = dict(activity_breakdown)
        stats['impact_summary'] = dict(impact_summary)
        
        # Git commit stats
        cursor.execute('''
            SELECT COUNT(*), SUM(files_changed), SUM(insertions), SUM(deletions), 
                   COUNT(DISTINCT author) as unique_authors
            FROM git_commits 
            WHERE timestamp > ?
        ''', (start_date,))
        
        commit_data = cursor.fetchone()
        if commit_data and commit_data[0]:
            stats['git_activity'] = {
                'total_commits': commit_data[0],
                'files_changed': commit_data[1] or 0,
                'insertions': commit_data[2] or 0,
                'deletions': commit_data[3] or 0,
                'unique_authors': commit_data[4] or 0
            }
        
        # System health trends
        cursor.execute('''
            SELECT AVG(cpu_percent), AVG(memory_percent), AVG(response_time_ms),
                   MAX(cpu_percent), MAX(memory_percent), MAX(response_time_ms)
            FROM system_metrics 
            WHERE timestamp > ?
        ''', (start_date,))
        
        health_data = cursor.fetchone()
        if health_data and health_data[0] is not None:
            stats['system_health'] = {
                'avg_cpu_percent': round(health_data[0], 2),
                'avg_memory_percent': round(health_data[1], 2),
                'avg_response_time_ms': round(health_data[2] or 0, 2),
                'peak_cpu_percent': round(health_data[3], 2),
                'peak_memory_percent': round(health_data[4], 2),
                'peak_response_time_ms': round(health_data[5] or 0, 2)
            }
        
        # Test results summary
        cursor.execute('''
            SELECT COUNT(*), SUM(tests_run), SUM(tests_passed), SUM(tests_failed)
            FROM test_results 
            WHERE timestamp > ?
        ''', (start_date,))
        
        test_data = cursor.fetchone()
        if test_data and test_data[0]:
            stats['test_activity'] = {
                'test_runs': test_data[0],
                'total_tests_run': test_data[1] or 0,
                'total_tests_passed': test_data[2] or 0,
                'total_tests_failed': test_data[3] or 0,
                'success_rate': round((test_data[2] or 0) / max(test_data[1] or 1, 1) * 100, 2)
            }
        
        conn.close()
        return stats
    
    def get_daily_summaries(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily summaries from log files"""
        summaries = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_log = self.log_dir / f"progress_{date}.json"
            summary_file = self.log_dir / f"daily_summary_{date}.json"
            
            daily_data = {'date': date, 'activities': [], 'summary': {}}
            
            # Load daily activities
            if daily_log.exists():
                try:
                    with open(daily_log, 'r') as f:
                        daily_data['activities'] = json.load(f)
                except Exception as e:
                    print(f"⚠️ Error reading daily log {daily_log}: {e}")
            
            # Load daily summary if available
            if summary_file.exists():
                try:
                    with open(summary_file, 'r') as f:
                        daily_data['summary'] = json.load(f)
                except Exception as e:
                    print(f"⚠️ Error reading summary {summary_file}: {e}")
            
            if daily_data['activities'] or daily_data['summary']:
                summaries.append(daily_data)
        
        return summaries
    
    def analyze_progress_trends(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trends and patterns in progress data"""
        trends = {
            'productivity_indicators': {},
            'quality_indicators': {},
            'health_indicators': {},
            'milestone_progress': {}
        }
        
        # Productivity analysis
        if 'git_activity' in stats:
            git_stats = stats['git_activity']
            commits_per_day = git_stats['total_commits'] / 7
            trends['productivity_indicators'] = {
                'commits_per_day': round(commits_per_day, 1),
                'avg_files_per_commit': round(git_stats['files_changed'] / max(git_stats['total_commits'], 1), 1),
                'code_velocity': f"+{git_stats['insertions']} -{git_stats['deletions']} lines",
                'collaboration_level': git_stats['unique_authors']
            }
        
        # Quality indicators
        if 'test_activity' in stats:
            test_stats = stats['test_activity']
            trends['quality_indicators'] = {
                'test_coverage': 'improving' if test_stats['success_rate'] > 90 else 'needs_attention',
                'test_frequency': test_stats['test_runs'],
                'success_rate': f"{test_stats['success_rate']}%"
            }
        
        # System health
        if 'system_health' in stats:
            health_stats = stats['system_health']
            trends['health_indicators'] = {
                'performance_status': 'good' if health_stats['avg_response_time_ms'] < 1000 else 'slow',
                'resource_usage': 'optimal' if health_stats['avg_cpu_percent'] < 70 else 'high',
                'stability': 'stable' if health_stats['peak_cpu_percent'] < 90 else 'variable'
            }
        
        # Activity patterns
        if 'activity_breakdown' in stats:
            activity_stats = stats['activity_breakdown']
            total_activities = sum(sum(categories.values()) for categories in activity_stats.values())
            
            trends['milestone_progress'] = {
                'total_activities': total_activities,
                'most_active_area': max(activity_stats.keys(), key=lambda k: sum(activity_stats[k].values())) if activity_stats else 'none',
                'activity_diversity': len(activity_stats),
                'development_focus': self._classify_development_focus(activity_stats)
            }
        
        return trends
    
    def _classify_development_focus(self, activity_stats: Dict[str, Dict[str, int]]) -> str:
        """Classify the main development focus based on activity patterns"""
        focus_weights = {
            'commit': {'code_change': 1.0},
            'test': {'quality_assurance': 1.5, 'testing': 1.5},
            'deployment': {'deployment': 2.0},
            'metric': {'system_health': 0.5, 'performance': 1.0},
            'issue': {'bug_fix': 1.5},
            'milestone': {'development': 2.0, 'feature': 1.5}
        }
        
        focus_scores = defaultdict(float)
        
        for activity_type, categories in activity_stats.items():
            for category, count in categories.items():
                weight = focus_weights.get(activity_type, {}).get(category, 0.5)
                
                if 'test' in category or 'quality' in category:
                    focus_scores['Quality Assurance'] += count * weight
                elif 'deploy' in category or 'release' in category:
                    focus_scores['Deployment'] += count * weight
                elif 'performance' in category or 'optimization' in category:
                    focus_scores['Performance'] += count * weight
                elif 'feature' in category or 'development' in category:
                    focus_scores['Feature Development'] += count * weight
                elif 'bug' in category or 'fix' in category:
                    focus_scores['Bug Fixing'] += count * weight
                else:
                    focus_scores['General Development'] += count * weight
        
        if not focus_scores:
            return 'No specific focus detected'
        
        return max(focus_scores.keys(), key=lambda k: focus_scores[k])
    
    def generate_summary_report(self, days: int = 7, output_format: str = 'markdown') -> str:
        """Generate a comprehensive summary report"""
        stats = self.get_database_stats(days)
        trends = self.analyze_progress_trends(stats)
        daily_summaries = self.get_daily_summaries(days)
        
        if output_format == 'markdown':
            return self._generate_markdown_report(days, stats, trends, daily_summaries)
        elif output_format == 'json':
            return json.dumps({
                'period': f'Last {days} days',
                'generated_at': datetime.now().isoformat(),
                'statistics': stats,
                'trends': trends,
                'daily_summaries': daily_summaries
            }, indent=2)
        else:
            return self._generate_text_report(days, stats, trends, daily_summaries)
    
    def _generate_markdown_report(self, days: int, stats: Dict, trends: Dict, daily_summaries: List) -> str:
        """Generate a markdown formatted report"""
        report = f"""# Alice Development Progress Report

**Period:** Last {days} days  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🎯 Executive Summary

"""
        
        # High-level summary
        if 'milestone_progress' in trends:
            milestone = trends['milestone_progress']
            report += f"""
- **Total Activities:** {milestone.get('total_activities', 0)}
- **Development Focus:** {milestone.get('development_focus', 'General Development')}
- **Most Active Area:** {milestone.get('most_active_area', 'N/A')}
- **Activity Diversity:** {milestone.get('activity_diversity', 0)} different types

"""
        
        # Git Activity
        if 'git_activity' in stats:
            git = stats['git_activity']
            report += f"""## 🔧 Code Development

- **Commits:** {git['total_commits']} 
- **Files Changed:** {git['files_changed']}
- **Code Changes:** +{git['insertions']} / -{git['deletions']} lines
- **Contributors:** {git['unique_authors']} unique author(s)

"""
        
        # System Health
        if 'system_health' in stats:
            health = stats['system_health']
            report += f"""## 🏥 System Health

- **Average CPU:** {health['avg_cpu_percent']}% (Peak: {health['peak_cpu_percent']}%)
- **Average Memory:** {health['avg_memory_percent']}% (Peak: {health['peak_memory_percent']}%)
- **API Response Time:** {health['avg_response_time_ms']}ms (Peak: {health['peak_response_time_ms']}ms)

"""
        
        # Test Results
        if 'test_activity' in stats:
            test = stats['test_activity']
            report += f"""## 🧪 Quality Assurance

- **Test Runs:** {test['test_runs']}
- **Tests Executed:** {test['total_tests_run']}
- **Success Rate:** {test['success_rate']}%
- **Passed:** {test['total_tests_passed']} | **Failed:** {test['total_tests_failed']}

"""
        
        # Trends Analysis
        report += "## 📈 Trends & Insights\n\n"
        
        if 'productivity_indicators' in trends:
            prod = trends['productivity_indicators']
            report += f"""### Productivity
- **Daily Commit Rate:** {prod.get('commits_per_day', 0)} commits/day
- **Code Velocity:** {prod.get('code_velocity', 'N/A')}
- **Files per Commit:** {prod.get('avg_files_per_commit', 0)} files/commit

"""
        
        if 'quality_indicators' in trends:
            quality = trends['quality_indicators']
            report += f"""### Quality
- **Test Coverage:** {quality.get('test_coverage', 'unknown')}
- **Success Rate:** {quality.get('success_rate', '0%')}

"""
        
        if 'health_indicators' in trends:
            health_ind = trends['health_indicators']
            report += f"""### System Health
- **Performance:** {health_ind.get('performance_status', 'unknown')}
- **Resource Usage:** {health_ind.get('resource_usage', 'unknown')}
- **Stability:** {health_ind.get('stability', 'unknown')}

"""
        
        # Activity Breakdown
        if 'activity_breakdown' in stats:
            report += "## 📊 Activity Breakdown\n\n"
            for activity_type, categories in stats['activity_breakdown'].items():
                report += f"### {activity_type.title()}\n"
                for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                    report += f"- **{category}:** {count}\n"
                report += "\n"
        
        # Recent Daily Activity
        if daily_summaries:
            report += "## 📅 Daily Activity Overview\n\n"
            for daily in daily_summaries[:3]:  # Last 3 days
                report += f"### {daily['date']}\n"
                if daily['activities']:
                    activity_count = len(daily['activities'])
                    activity_types = Counter(act.get('entry_type', 'unknown') for act in daily['activities'])
                    report += f"- **Total Activities:** {activity_count}\n"
                    for act_type, count in activity_types.most_common():
                        report += f"- **{act_type.title()}:** {count}\n"
                else:
                    report += "- No recorded activities\n"
                report += "\n"
        
        # Footer
        report += f"""
---
*Report generated by Alice Progress Tracker*  
*Database: {self.db_path}*
"""
        
        return report
    
    def _generate_text_report(self, days: int, stats: Dict, trends: Dict, daily_summaries: List) -> str:
        """Generate a plain text report"""
        lines = [
            f"Alice Development Progress Report - Last {days} days",
            "=" * 60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        # Summary stats
        if 'git_activity' in stats:
            git = stats['git_activity']
            lines.extend([
                "GIT ACTIVITY:",
                f"  Commits: {git['total_commits']}",
                f"  Files Changed: {git['files_changed']}",
                f"  Code Changes: +{git['insertions']} / -{git['deletions']} lines",
                ""
            ])
        
        if 'test_activity' in stats:
            test = stats['test_activity']
            lines.extend([
                "TESTING:",
                f"  Test Runs: {test['test_runs']}",
                f"  Success Rate: {test['success_rate']}%",
                ""
            ])
        
        if 'system_health' in stats:
            health = stats['system_health']
            lines.extend([
                "SYSTEM HEALTH:",
                f"  Avg CPU: {health['avg_cpu_percent']}%",
                f"  Avg Memory: {health['avg_memory_percent']}%",
                f"  Avg Response: {health['avg_response_time_ms']}ms",
                ""
            ])
        
        return "\n".join(lines)
    
    def save_report(self, report: str, filename: str = None, format_type: str = 'markdown'):
        """Save report to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = 'md' if format_type == 'markdown' else 'txt' if format_type == 'text' else 'json'
            filename = f"progress_report_{timestamp}.{ext}"
        
        output_file = self.log_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📄 Report saved to: {output_file}")
        return output_file

def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description='Generate Alice Progress Summary')
    parser.add_argument('--days', type=int, default=7, help='Number of days to analyze')
    parser.add_argument('--format', choices=['markdown', 'text', 'json'], default='markdown', help='Output format')
    parser.add_argument('--output', help='Output filename')
    parser.add_argument('--save', action='store_true', help='Save report to file')
    parser.add_argument('--db', help='Database path', default='progress_tracking.db')
    parser.add_argument('--logs', help='Logs directory', default='logs/progress')
    
    args = parser.parse_args()
    
    generator = ProgressSummaryGenerator(db_path=args.db, log_dir=args.logs)
    report = generator.generate_summary_report(days=args.days, output_format=args.format)
    
    if args.save or args.output:
        generator.save_report(report, args.output, args.format)
    else:
        print(report)

if __name__ == "__main__":
    main()