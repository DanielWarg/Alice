from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum
import sqlite3
import json
import logging
import re
import hashlib
from pathlib import Path

from logger_config import get_logger

logger = get_logger("pattern_recognizer")

# Database paths
AMBIENT_DB_PATH = Path(__file__).parent.parent / "data" / "ambient.db"
PATTERNS_DB_PATH = Path(__file__).parent.parent / "data" / "patterns.db"

class PatternType(Enum):
    TIME_BASED = "time_based"
    ACTIVITY_BASED = "activity_based"
    LOCATION_BASED = "location_based"
    CONTEXT_BASED = "context_based"

@dataclass
class Pattern:
    id: Optional[str]
    pattern_type: PatternType
    description: str
    confidence: float
    occurrences: int
    last_seen: datetime
    first_seen: datetime
    pattern_data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class PatternRecognizer:
    def __init__(self):
        self.init_patterns_db()
        
    def init_patterns_db(self):
        """Initialize patterns database with schema"""
        PATTERNS_DB_PATH.parent.mkdir(exist_ok=True)
        
        with sqlite3.connect(PATTERNS_DB_PATH) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    occurrences INTEGER NOT NULL DEFAULT 1,
                    first_seen DATETIME NOT NULL,
                    last_seen DATETIME NOT NULL,
                    pattern_data_json TEXT NOT NULL,
                    metadata_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS pattern_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id TEXT NOT NULL,
                    action TEXT NOT NULL,  -- accept, decline, snooze
                    feedback_data_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pattern_id) REFERENCES patterns(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type);
                CREATE INDEX IF NOT EXISTS idx_patterns_confidence ON patterns(confidence);
                CREATE INDEX IF NOT EXISTS idx_patterns_last_seen ON patterns(last_seen);
                CREATE INDEX IF NOT EXISTS idx_feedback_pattern ON pattern_feedback(pattern_id);
            """)
            logger.info("Pattern recognition database initialized")
    
    async def analyze_ambient_summaries(self, lookback_days: int = 7) -> List[Pattern]:
        """Analyze recent ambient summaries to identify patterns"""
        try:
            patterns = []
            
            # Get recent summaries from ambient memory
            summaries = self._fetch_recent_summaries(lookback_days)
            logger.info(f"Analyzing {len(summaries)} summaries for patterns")
            
            if not summaries:
                return patterns
            
            # Pattern detection algorithms
            patterns.extend(await self._detect_time_patterns(summaries))
            patterns.extend(await self._detect_activity_patterns(summaries))
            patterns.extend(await self._detect_context_patterns(summaries))
            
            # Store or update patterns in database
            for pattern in patterns:
                await self._store_or_update_pattern(pattern)
            
            logger.info(f"Identified {len(patterns)} patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to analyze patterns: {e}")
            return []
    
    def _fetch_recent_summaries(self, days: int) -> List[Dict[str, Any]]:
        """Fetch recent ambient summaries from the database"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            with sqlite3.connect(AMBIENT_DB_PATH) as conn:
                cursor = conn.execute("""
                    SELECT id, text, created_at, meta_json
                    FROM memory 
                    WHERE kind = 'ambient_summary' 
                    AND created_at >= ?
                    ORDER BY created_at DESC
                """, (cutoff_time,))
                
                summaries = []
                for row in cursor.fetchall():
                    summary = {
                        'id': row[0],
                        'text': row[1],
                        'created_at': datetime.fromisoformat(row[2]),
                        'metadata': json.loads(row[3]) if row[3] else {}
                    }
                    summaries.append(summary)
                
                return summaries
                
        except Exception as e:
            logger.error(f"Failed to fetch summaries: {e}")
            return []
    
    async def _detect_time_patterns(self, summaries: List[Dict[str, Any]]) -> List[Pattern]:
        """Detect time-based patterns from summaries"""
        patterns = []
        
        try:
            # Group summaries by hour and day of week
            time_activities = {}
            
            for summary in summaries:
                created_at = summary['created_at']
                hour = created_at.hour
                day_of_week = created_at.weekday()  # 0=Monday
                text = summary['text'].lower()
                
                # Extract activities from summary text
                activities = self._extract_activities(text)
                
                for activity in activities:
                    key = f"{day_of_week}_{hour}_{activity}"
                    if key not in time_activities:
                        time_activities[key] = {
                            'activity': activity,
                            'day_of_week': day_of_week,
                            'hour': hour,
                            'occurrences': 0,
                            'timestamps': []
                        }
                    time_activities[key]['occurrences'] += 1
                    time_activities[key]['timestamps'].append(created_at)
            
            # Find patterns with multiple occurrences
            for key, data in time_activities.items():
                if data['occurrences'] >= 3:  # Minimum 3 occurrences for time pattern
                    pattern_id = self._generate_pattern_id(PatternType.TIME_BASED, key)
                    
                    # Calculate confidence based on frequency and consistency
                    total_weeks = len(set(ts.isocalendar()[1] for ts in data['timestamps']))
                    consistency = data['occurrences'] / max(total_weeks, 1)
                    confidence = min(0.3 + (consistency * 0.4), 0.9)
                    
                    day_names = ['måndag', 'tisdag', 'onsdag', 'torsdag', 'fredag', 'lördag', 'söndag']
                    description = f"Varje {day_names[data['day_of_week']]} kl {data['hour']:02d}:00 → {data['activity']}"
                    
                    pattern = Pattern(
                        id=pattern_id,
                        pattern_type=PatternType.TIME_BASED,
                        description=description,
                        confidence=confidence,
                        occurrences=data['occurrences'],
                        last_seen=max(data['timestamps']),
                        first_seen=min(data['timestamps']),
                        pattern_data={
                            'day_of_week': data['day_of_week'],
                            'hour': data['hour'],
                            'activity': data['activity'],
                            'timestamps': [ts.isoformat() for ts in data['timestamps']]
                        }
                    )
                    patterns.append(pattern)
            
            logger.info(f"Detected {len(patterns)} time-based patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to detect time patterns: {e}")
            return []
    
    async def _detect_activity_patterns(self, summaries: List[Dict[str, Any]]) -> List[Pattern]:
        """Detect activity sequence patterns"""
        patterns = []
        
        try:
            # Look for recurring activity sequences
            activity_sequences = {}
            
            for i in range(len(summaries) - 1):
                current_activities = self._extract_activities(summaries[i]['text'].lower())
                next_activities = self._extract_activities(summaries[i + 1]['text'].lower())
                
                for current in current_activities:
                    for next_activity in next_activities:
                        sequence_key = f"{current}→{next_activity}"
                        if sequence_key not in activity_sequences:
                            activity_sequences[sequence_key] = {
                                'current': current,
                                'next': next_activity,
                                'occurrences': 0,
                                'timestamps': []
                            }
                        activity_sequences[sequence_key]['occurrences'] += 1
                        activity_sequences[sequence_key]['timestamps'].append(summaries[i]['created_at'])
            
            # Find significant activity patterns
            for key, data in activity_sequences.items():
                if data['occurrences'] >= 3:  # Minimum 3 occurrences
                    pattern_id = self._generate_pattern_id(PatternType.ACTIVITY_BASED, key)
                    
                    confidence = min(0.3 + (data['occurrences'] * 0.15), 0.85)
                    description = f"Efter '{data['current']}' → vanligen '{data['next']}'"
                    
                    pattern = Pattern(
                        id=pattern_id,
                        pattern_type=PatternType.ACTIVITY_BASED,
                        description=description,
                        confidence=confidence,
                        occurrences=data['occurrences'],
                        last_seen=max(data['timestamps']),
                        first_seen=min(data['timestamps']),
                        pattern_data={
                            'current_activity': data['current'],
                            'next_activity': data['next'],
                            'sequence': key,
                            'timestamps': [ts.isoformat() for ts in data['timestamps']]
                        }
                    )
                    patterns.append(pattern)
            
            logger.info(f"Detected {len(patterns)} activity-based patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to detect activity patterns: {e}")
            return []
    
    async def _detect_context_patterns(self, summaries: List[Dict[str, Any]]) -> List[Pattern]:
        """Detect contextual patterns like preferences and habits"""
        patterns = []
        
        try:
            # Look for recurring preferences and habits
            context_patterns = {}
            
            for summary in summaries:
                text = summary['text'].lower()
                
                # Extract preferences (likes, dislikes, habits)
                preferences = self._extract_preferences(text)
                habits = self._extract_habits(text)
                
                for item_type, items in [('preference', preferences), ('habit', habits)]:
                    for item in items:
                        key = f"{item_type}_{item}"
                        if key not in context_patterns:
                            context_patterns[key] = {
                                'type': item_type,
                                'item': item,
                                'occurrences': 0,
                                'timestamps': []
                            }
                        context_patterns[key]['occurrences'] += 1
                        context_patterns[key]['timestamps'].append(summary['created_at'])
            
            # Create patterns for recurring contexts
            for key, data in context_patterns.items():
                if data['occurrences'] >= 2:  # Lower threshold for preferences/habits
                    pattern_id = self._generate_pattern_id(PatternType.CONTEXT_BASED, key)
                    
                    confidence = min(0.4 + (data['occurrences'] * 0.2), 0.8)
                    description = f"{data['type'].capitalize()}: {data['item']}"
                    
                    pattern = Pattern(
                        id=pattern_id,
                        pattern_type=PatternType.CONTEXT_BASED,
                        description=description,
                        confidence=confidence,
                        occurrences=data['occurrences'],
                        last_seen=max(data['timestamps']),
                        first_seen=min(data['timestamps']),
                        pattern_data={
                            'context_type': data['type'],
                            'context_item': data['item'],
                            'timestamps': [ts.isoformat() for ts in data['timestamps']]
                        }
                    )
                    patterns.append(pattern)
            
            logger.info(f"Detected {len(patterns)} context-based patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to detect context patterns: {e}")
            return []
    
    def _extract_activities(self, text: str) -> List[str]:
        """Extract activities from summary text"""
        # Common Swedish activity patterns
        activity_patterns = [
            r'läser? email',
            r'kollar? kalender',
            r'meeting',
            r'möte',
            r'kaffe',
            r'lunch',
            r'jobbar? med',
            r'skriver?',
            r'planerar?',
            r'ringer?',
            r'pratar? om',
            r'arbetar? på',
            r'går? igenom',
            r'uppdaterar?'
        ]
        
        activities = []
        for pattern in activity_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            activities.extend(matches)
        
        # Clean and normalize
        activities = [act.strip().lower() for act in activities if len(act.strip()) > 2]
        return list(set(activities))  # Remove duplicates
    
    def _extract_preferences(self, text: str) -> List[str]:
        """Extract preferences from text"""
        preference_patterns = [
            r'gillar? (.+?)(?:\.|$)',
            r'föredrar? (.+?)(?:\.|$)',
            r'tycker? om (.+?)(?:\.|$)',
            r'alltid (.+?)(?:\.|$)'
        ]
        
        preferences = []
        for pattern in preference_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            preferences.extend([match.strip() for match in matches if len(match.strip()) > 3])
        
        return preferences
    
    def _extract_habits(self, text: str) -> List[str]:
        """Extract habits from text"""
        habit_patterns = [
            r'brukar? (.+?)(?:\.|$)',
            r'vanligtvis (.+?)(?:\.|$)',
            r'alltid (.+?) på',
            r'varje dag (.+?)(?:\.|$)'
        ]
        
        habits = []
        for pattern in habit_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            habits.extend([match.strip() for match in matches if len(match.strip()) > 3])
        
        return habits
    
    def _generate_pattern_id(self, pattern_type: PatternType, key: str) -> str:
        """Generate unique pattern ID"""
        combined = f"{pattern_type.value}_{key}"
        return hashlib.md5(combined.encode()).hexdigest()[:16]
    
    async def _store_or_update_pattern(self, pattern: Pattern):
        """Store new pattern or update existing one"""
        try:
            with sqlite3.connect(PATTERNS_DB_PATH) as conn:
                # Check if pattern already exists
                existing = conn.execute(
                    "SELECT confidence, occurrences FROM patterns WHERE id = ?", 
                    (pattern.id,)
                ).fetchone()
                
                if existing:
                    # Update existing pattern
                    new_confidence = min(existing[0] + 0.1, 0.95)  # Increase confidence
                    new_occurrences = existing[1] + pattern.occurrences
                    
                    conn.execute("""
                        UPDATE patterns 
                        SET confidence = ?, occurrences = ?, last_seen = ?, 
                            pattern_data_json = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (
                        new_confidence, new_occurrences, pattern.last_seen,
                        json.dumps(pattern.pattern_data), pattern.id
                    ))
                    
                    logger.debug(f"Updated pattern {pattern.id} (confidence: {new_confidence:.2f})")
                else:
                    # Insert new pattern
                    conn.execute("""
                        INSERT INTO patterns 
                        (id, pattern_type, description, confidence, occurrences,
                         first_seen, last_seen, pattern_data_json, metadata_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        pattern.id, pattern.pattern_type.value, pattern.description,
                        pattern.confidence, pattern.occurrences, pattern.first_seen,
                        pattern.last_seen, json.dumps(pattern.pattern_data),
                        json.dumps(pattern.metadata) if pattern.metadata else None
                    ))
                    
                    logger.debug(f"Stored new pattern {pattern.id} (confidence: {pattern.confidence:.2f})")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store pattern {pattern.id}: {e}")
    
    async def get_patterns_for_triggering(self, min_confidence: float = 0.5) -> List[Pattern]:
        """Get patterns that meet confidence threshold for triggering"""
        try:
            with sqlite3.connect(PATTERNS_DB_PATH) as conn:
                cursor = conn.execute("""
                    SELECT id, pattern_type, description, confidence, occurrences,
                           first_seen, last_seen, pattern_data_json, metadata_json
                    FROM patterns 
                    WHERE confidence >= ?
                    ORDER BY confidence DESC, last_seen DESC
                """, (min_confidence,))
                
                patterns = []
                for row in cursor.fetchall():
                    pattern = Pattern(
                        id=row[0],
                        pattern_type=PatternType(row[1]),
                        description=row[2],
                        confidence=row[3],
                        occurrences=row[4],
                        first_seen=datetime.fromisoformat(row[5]),
                        last_seen=datetime.fromisoformat(row[6]),
                        pattern_data=json.loads(row[7]),
                        metadata=json.loads(row[8]) if row[8] else None
                    )
                    patterns.append(pattern)
                
                logger.info(f"Retrieved {len(patterns)} patterns for triggering")
                return patterns
                
        except Exception as e:
            logger.error(f"Failed to get patterns for triggering: {e}")
            return []
    
    async def record_feedback(self, pattern_id: str, action: str, feedback_data: Optional[Dict] = None):
        """Record user feedback on pattern suggestions"""
        try:
            with sqlite3.connect(PATTERNS_DB_PATH) as conn:
                # Store feedback
                conn.execute("""
                    INSERT INTO pattern_feedback (pattern_id, action, feedback_data_json)
                    VALUES (?, ?, ?)
                """, (
                    pattern_id, action, 
                    json.dumps(feedback_data) if feedback_data else None
                ))
                
                # Adjust pattern confidence based on feedback
                if action == "accept":
                    conn.execute("""
                        UPDATE patterns 
                        SET confidence = MIN(confidence + 0.2, 0.95),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (pattern_id,))
                elif action == "decline":
                    conn.execute("""
                        UPDATE patterns 
                        SET confidence = MAX(confidence - 0.1, 0.1),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (pattern_id,))
                
                conn.commit()
                logger.info(f"Recorded {action} feedback for pattern {pattern_id}")
                
        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")

# Create global instance
pattern_recognizer = PatternRecognizer()