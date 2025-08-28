import asyncio
import json
import os
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path

from fastapi import WebSocket
from logger_config import get_logger
from .pattern_recognizer import pattern_recognizer, Pattern, PatternType
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from proactive_shadow import shadow

logger = get_logger("proactive_trigger")

# Database path
PATTERNS_DB_PATH = Path(__file__).parent.parent / "data" / "patterns.db"
TRIGGER_DB_PATH = Path(__file__).parent.parent / "data" / "triggers.db"

class TriggerType(Enum):
    PATTERN_MATCH = "pattern_match"
    TIME_BASED = "time_based"
    CONTEXT_CHANGE = "context_change"

@dataclass
class ProactiveSuggestion:
    id: str
    pattern_id: str
    trigger_type: TriggerType
    message: str
    confidence: float
    metadata: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime] = None

class ProactiveTrigger:
    def __init__(self):
        self.active_websockets: List[WebSocket] = []
        self.running = False
        self.settings = self._load_default_settings()
        self.init_trigger_db()
    
    def init_trigger_db(self):
        """Initialize trigger database"""
        TRIGGER_DB_PATH.parent.mkdir(exist_ok=True)
        
        with sqlite3.connect(TRIGGER_DB_PATH) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS triggers (
                    id TEXT PRIMARY KEY,
                    pattern_id TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    metadata_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sent_at DATETIME,
                    response TEXT,  -- accept, decline, snooze
                    response_at DATETIME
                );
                
                CREATE TABLE IF NOT EXISTS trigger_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_triggers_created ON triggers(created_at);
                CREATE INDEX IF NOT EXISTS idx_triggers_pattern ON triggers(pattern_id);
                CREATE INDEX IF NOT EXISTS idx_triggers_response ON triggers(response);
            """)
        
        logger.info("Proactive trigger database initialized")
    
    def _load_default_settings(self) -> Dict[str, Any]:
        """Load default proactive settings"""
        return {
            "level": os.getenv("PROACTIVE_LEVEL", "standard"),  # off, minimal, standard, eager
            "quiet_hours_start": int(os.getenv("QUIET_HOURS_START", "22")),
            "quiet_hours_end": int(os.getenv("QUIET_HOURS_END", "7")),
            "max_prompts_per_day": int(os.getenv("MAX_PROMPTS_PER_DAY", "5")),
            "min_confidence_threshold": float(os.getenv("MIN_CONFIDENCE", "0.5")),
            "pattern_cooldown_hours": int(os.getenv("PATTERN_COOLDOWN_HOURS", "24")),
            "shadow_mode": os.getenv("SHADOW_MODE", "false").lower() == "true",
            "show_banners_only": os.getenv("SHOW_BANNERS_ONLY", "false").lower() == "true"
        }
    
    async def start_monitoring(self):
        """Start the proactive monitoring system"""
        if self.running:
            logger.warning("Proactive trigger already running")
            return
        
        self.running = True
        logger.info("Starting proactive trigger monitoring")
        
        try:
            while self.running:
                await self._check_for_triggers()
                await asyncio.sleep(300)  # Check every 5 minutes
                
        except Exception as e:
            logger.error(f"Error in proactive monitoring: {e}")
            self.running = False
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.running = False
        logger.info("Stopped proactive trigger monitoring")
    
    async def _check_for_triggers(self):
        """Check if any patterns should trigger proactive suggestions"""
        try:
            # Skip if proactive is disabled
            if self.settings["level"] == "off":
                return
            
            # Skip during quiet hours
            if self._is_quiet_hours():
                logger.debug("Skipping triggers during quiet hours")
                return
            
            # Check daily limit
            if await self._reached_daily_limit():
                logger.debug("Daily prompt limit reached")
                return
            
            # Get patterns ready for triggering
            min_confidence = self._get_confidence_threshold()
            patterns = await pattern_recognizer.get_patterns_for_triggering(min_confidence)
            
            for pattern in patterns:
                # Check if pattern was triggered recently (cooldown)
                if await self._pattern_in_cooldown(pattern.id):
                    continue
                
                # Check if pattern matches current context
                if await self._should_trigger_pattern(pattern):
                    suggestion = await self._create_suggestion_from_pattern(pattern)
                    if suggestion:
                        # Log suggestion performance timing
                        start_time = time.time()
                        
                        # Determine action based on shadow mode
                        if self.settings["shadow_mode"]:
                            # Shadow mode: log but don't send
                            await self._log_shadow_suggestion(suggestion, start_time)
                        elif self.settings["show_banners_only"]:
                            # Banner only mode: send but mark as banner
                            await self._send_banner_suggestion(suggestion)
                            await self._log_shadow_suggestion(suggestion, start_time, sent=True)
                        else:
                            # Normal mode: full suggestions
                            await self._send_suggestion(suggestion)
                            await self._log_shadow_suggestion(suggestion, start_time, sent=True)
                        
                        await self._record_trigger(suggestion)
                        break  # Only send one suggestion at a time
                        
        except Exception as e:
            logger.error(f"Error checking for triggers: {e}")
    
    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours"""
        now = datetime.now()
        current_hour = now.hour
        start_hour = self.settings["quiet_hours_start"]
        end_hour = self.settings["quiet_hours_end"]
        
        if start_hour > end_hour:  # Spans midnight
            return current_hour >= start_hour or current_hour < end_hour
        else:
            return start_hour <= current_hour < end_hour
    
    async def _reached_daily_limit(self) -> bool:
        """Check if daily prompt limit has been reached"""
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            with sqlite3.connect(TRIGGER_DB_PATH) as conn:
                count = conn.execute("""
                    SELECT COUNT(*) FROM triggers 
                    WHERE sent_at >= ? AND sent_at IS NOT NULL
                """, (today_start,)).fetchone()[0]
                
                return count >= self.settings["max_prompts_per_day"]
                
        except Exception as e:
            logger.error(f"Error checking daily limit: {e}")
            return False
    
    def _get_confidence_threshold(self) -> float:
        """Get confidence threshold based on proactive level"""
        level_thresholds = {
            "minimal": 0.8,
            "standard": 0.5,
            "eager": 0.3
        }
        
        level = self.settings["level"]
        return level_thresholds.get(level, 0.5)
    
    async def _pattern_in_cooldown(self, pattern_id: str) -> bool:
        """Check if pattern is in cooldown period"""
        try:
            cooldown_hours = self.settings["pattern_cooldown_hours"]
            cooldown_start = datetime.now() - timedelta(hours=cooldown_hours)
            
            with sqlite3.connect(TRIGGER_DB_PATH) as conn:
                last_trigger = conn.execute("""
                    SELECT sent_at FROM triggers 
                    WHERE pattern_id = ? AND sent_at >= ?
                    ORDER BY sent_at DESC LIMIT 1
                """, (pattern_id, cooldown_start)).fetchone()
                
                return last_trigger is not None
                
        except Exception as e:
            logger.error(f"Error checking pattern cooldown: {e}")
            return False
    
    async def _should_trigger_pattern(self, pattern: Pattern) -> bool:
        """Determine if pattern should trigger based on current context"""
        try:
            if pattern.pattern_type == PatternType.TIME_BASED:
                # Check if current time matches pattern
                now = datetime.now()
                pattern_data = pattern.pattern_data
                
                if (now.weekday() == pattern_data.get('day_of_week') and
                    now.hour == pattern_data.get('hour')):
                    # Add some tolerance (within 30 minutes)
                    return now.minute < 30
                    
            elif pattern.pattern_type == PatternType.ACTIVITY_BASED:
                # Check if current activity context matches trigger conditions
                # This would need integration with current activity detection
                # For now, use simple heuristic
                return True  # TODO: Implement activity context detection
                
            elif pattern.pattern_type == PatternType.CONTEXT_BASED:
                # Contextual patterns can trigger more flexibly
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating trigger condition for pattern {pattern.id}: {e}")
            return False
    
    async def _create_suggestion_from_pattern(self, pattern: Pattern) -> Optional[ProactiveSuggestion]:
        """Create a proactive suggestion from a pattern"""
        try:
            suggestion_id = f"suggestion_{pattern.id}_{int(datetime.now().timestamp())}"
            
            # Generate suggestion message based on pattern type
            message = await self._generate_suggestion_message(pattern)
            
            suggestion = ProactiveSuggestion(
                id=suggestion_id,
                pattern_id=pattern.id,
                trigger_type=TriggerType.PATTERN_MATCH,
                message=message,
                confidence=pattern.confidence,
                metadata={
                    "pattern_type": pattern.pattern_type.value,
                    "pattern_description": pattern.description,
                    "pattern_data": pattern.pattern_data
                },
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=10)  # Suggestions expire
            )
            
            return suggestion
            
        except Exception as e:
            logger.error(f"Error creating suggestion from pattern {pattern.id}: {e}")
            return None
    
    async def _generate_suggestion_message(self, pattern: Pattern) -> str:
        """Generate human-readable suggestion message"""
        try:
            if pattern.pattern_type == PatternType.TIME_BASED:
                data = pattern.pattern_data
                activity = data.get('activity', 'aktivitet')
                return f"Dags för {activity}? Du brukar göra detta nu."
                
            elif pattern.pattern_type == PatternType.ACTIVITY_BASED:
                data = pattern.pattern_data
                next_activity = data.get('next_activity', 'nästa steg')
                return f"Vill du {next_activity}? Du brukar göra det härnäst."
                
            elif pattern.pattern_type == PatternType.CONTEXT_BASED:
                data = pattern.pattern_data
                context_item = data.get('context_item', 'detta')
                return f"Påminnelse om {context_item} baserat på dina vanor."
                
            return f"Förslag baserat på mönster: {pattern.description}"
            
        except Exception as e:
            logger.error(f"Error generating message for pattern {pattern.id}: {e}")
            return "Alice har ett förslag baserat på dina vanor."
    
    async def _send_suggestion(self, suggestion: ProactiveSuggestion):
        """Send suggestion to connected WebSocket clients"""
        if not self.active_websockets:
            logger.debug("No active websockets for proactive suggestions")
            return
        
        payload = {
            "type": "suggestion",
            "id": suggestion.id,
            "pattern_id": suggestion.pattern_id,
            "message": suggestion.message,
            "confidence": suggestion.confidence,
            "metadata": suggestion.metadata,
            "actions": [
                {"action": "accept", "label": "Acceptera"},
                {"action": "decline", "label": "Nej tack"},
                {"action": "snooze", "label": "Påminn senare"}
            ]
        }
        
        message = json.dumps(payload)
        disconnected_sockets = []
        
        for websocket in self.active_websockets:
            try:
                await websocket.send_text(message)
                logger.info(f"Sent proactive suggestion {suggestion.id}")
            except Exception as e:
                logger.error(f"Failed to send suggestion to websocket: {e}")
                disconnected_sockets.append(websocket)
        
        # Remove disconnected sockets
        for socket in disconnected_sockets:
            self.active_websockets.remove(socket)
    
    async def _record_trigger(self, suggestion: ProactiveSuggestion):
        """Record trigger event in database"""
        try:
            with sqlite3.connect(TRIGGER_DB_PATH) as conn:
                conn.execute("""
                    INSERT INTO triggers 
                    (id, pattern_id, trigger_type, message, confidence, metadata_json, sent_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    suggestion.id,
                    suggestion.pattern_id,
                    suggestion.trigger_type.value,
                    suggestion.message,
                    suggestion.confidence,
                    json.dumps(suggestion.metadata),
                    datetime.now()
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error recording trigger: {e}")
    
    async def record_suggestion_response(self, suggestion_id: str, action: str, metadata: Optional[Dict] = None):
        """Record user response to suggestion"""
        try:
            with sqlite3.connect(TRIGGER_DB_PATH) as conn:
                # Update trigger record
                conn.execute("""
                    UPDATE triggers 
                    SET response = ?, response_at = ?
                    WHERE id = ?
                """, (action, datetime.now(), suggestion_id))
                
                # Get pattern_id for feedback
                pattern_id = conn.execute(
                    "SELECT pattern_id FROM triggers WHERE id = ?", 
                    (suggestion_id,)
                ).fetchone()
                
                conn.commit()
                
                # Record feedback to pattern recognizer
                if pattern_id:
                    await pattern_recognizer.record_feedback(
                        pattern_id[0], action, metadata
                    )
                
                # Update shadow log if exists
                shadow_log_id = metadata.get("shadow_log_id") if metadata else None
                if shadow_log_id:
                    shadow.log_user_action(shadow_log_id, action)
                    
            logger.info(f"Recorded {action} response for suggestion {suggestion_id}")
            
        except Exception as e:
            logger.error(f"Error recording suggestion response: {e}")
    
    async def add_websocket(self, websocket: WebSocket):
        """Add WebSocket connection for proactive suggestions"""
        self.active_websockets.append(websocket)
        logger.info(f"Added proactive WebSocket connection ({len(self.active_websockets)} total)")
    
    async def remove_websocket(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_websockets:
            self.active_websockets.remove(websocket)
            logger.info(f"Removed proactive WebSocket connection ({len(self.active_websockets)} total)")
    
    async def get_suggestion_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent suggestion history"""
        try:
            with sqlite3.connect(TRIGGER_DB_PATH) as conn:
                cursor = conn.execute("""
                    SELECT id, pattern_id, trigger_type, message, confidence,
                           created_at, sent_at, response, response_at, metadata_json
                    FROM triggers 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,))
                
                history = []
                for row in cursor.fetchall():
                    item = {
                        "id": row[0],
                        "pattern_id": row[1],
                        "trigger_type": row[2],
                        "message": row[3],
                        "confidence": row[4],
                        "created_at": row[5],
                        "sent_at": row[6],
                        "response": row[7],
                        "response_at": row[8],
                        "metadata": json.loads(row[9]) if row[9] else {}
                    }
                    history.append(item)
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting suggestion history: {e}")
            return []
    
    async def get_proactive_status(self) -> Dict[str, Any]:
        """Get current proactive system status"""
        try:
            # Get recent activity stats
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            with sqlite3.connect(TRIGGER_DB_PATH) as conn:
                today_count = conn.execute("""
                    SELECT COUNT(*) FROM triggers 
                    WHERE sent_at >= ? AND sent_at IS NOT NULL
                """, (today_start,)).fetchone()[0]
                
                recent_responses = conn.execute("""
                    SELECT response, COUNT(*) FROM triggers 
                    WHERE response IS NOT NULL AND created_at >= ?
                    GROUP BY response
                """, (datetime.now() - timedelta(days=7),)).fetchall()
                
            response_stats = {row[0]: row[1] for row in recent_responses}
            
            return {
                "running": self.running,
                "settings": self.settings,
                "active_connections": len(self.active_websockets),
                "today_suggestions": today_count,
                "daily_limit": self.settings["max_prompts_per_day"],
                "quiet_hours_active": self._is_quiet_hours(),
                "response_stats_7d": response_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting proactive status: {e}")
            return {"error": str(e)}
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """Update proactive settings"""
        try:
            self.settings.update(new_settings)
            
            # Store settings in database
            with sqlite3.connect(TRIGGER_DB_PATH) as conn:
                for key, value in new_settings.items():
                    conn.execute("""
                        INSERT OR REPLACE INTO trigger_settings (key, value, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    """, (key, json.dumps(value)))
                conn.commit()
                
            logger.info(f"Updated proactive settings: {new_settings}")
            
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
    
    async def _log_shadow_suggestion(self, suggestion: ProactiveSuggestion, start_time: float, sent: bool = False):
        """Log suggestion for shadow mode analysis"""
        try:
            latency_ms = (time.time() - start_time) * 1000
            
            # Determine throttling/policy reasons
            throttling_reason = None
            policy_reason = None
            
            if await self._reached_daily_limit():
                throttling_reason = "daily_limit_reached"
            
            if self._is_quiet_hours():
                policy_reason = "quiet_hours_active"
            
            why = f"Pattern {suggestion.pattern_id} triggered with confidence {suggestion.confidence:.2f}"
            
            # Log to shadow system
            log_id = shadow.log_shadow_suggestion(
                pattern_id=suggestion.pattern_id,
                confidence=suggestion.confidence,
                message=suggestion.message,
                why=why,
                latency_ms=latency_ms,
                throttling_reason=throttling_reason,
                policy_reason=policy_reason,
                metadata={
                    "sent": sent,
                    "shadow_mode": self.settings["shadow_mode"],
                    "show_banners_only": self.settings["show_banners_only"],
                    **suggestion.metadata
                }
            )
            
            # Store log_id for potential user feedback tracking
            suggestion.metadata["shadow_log_id"] = log_id
            
        except Exception as e:
            logger.error(f"Error logging shadow suggestion: {e}")
    
    async def _send_banner_suggestion(self, suggestion: ProactiveSuggestion):
        """Send suggestion as banner-only (non-intrusive)"""
        if not self.active_websockets:
            return
        
        payload = {
            "type": "banner_suggestion",
            "id": suggestion.id,
            "pattern_id": suggestion.pattern_id,
            "message": suggestion.message,
            "confidence": suggestion.confidence,
            "metadata": {**suggestion.metadata, "banner_only": True},
            "actions": [
                {"action": "acknowledge", "label": "OK"}
            ]
        }
        
        message = json.dumps(payload)
        disconnected_sockets = []
        
        for websocket in self.active_websockets:
            try:
                await websocket.send_text(message)
                logger.info(f"Sent banner suggestion {suggestion.id}")
            except Exception as e:
                logger.error(f"Failed to send banner suggestion: {e}")
                disconnected_sockets.append(websocket)
        
        # Remove disconnected sockets
        for socket in disconnected_sockets:
            self.active_websockets.remove(socket)

# Create global instance
proactive_trigger = ProactiveTrigger()