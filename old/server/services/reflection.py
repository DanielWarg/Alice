from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sqlite3
import json
import logging
from pathlib import Path

router = APIRouter(prefix="/api/reflect", tags=["reflection"])
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "ambient.db"

class ObserveRequest(BaseModel):
    summary_id: Optional[int] = None
    trigger: str = "manual"

class ReflectionResponse(BaseModel):
    id: int
    type: str
    text: str
    confidence: float
    created_at: str
    source_summary_id: Optional[int]

@router.post("/observe")
async def trigger_observation(request: ObserveRequest):
    """Manuell trigger för reflektion/observation av patterns"""
    try:
        reflections_created = []
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            
            # Hämta senaste summaries för analys
            if request.summary_id:
                summaries = conn.execute("""
                    SELECT * FROM memory 
                    WHERE kind = 'ambient_summary' AND id = ?
                """, (request.summary_id,)).fetchall()
            else:
                # Senaste 10 summaries
                summaries = conn.execute("""
                    SELECT * FROM memory 
                    WHERE kind = 'ambient_summary' 
                    ORDER BY created_at DESC 
                    LIMIT 10
                """).fetchall()
            
            for summary in summaries:
                reflection = await analyze_summary_for_patterns(summary)
                if reflection:
                    cursor = conn.execute("""
                        INSERT INTO memory (kind, text, meta_json, fts_text)
                        VALUES (?, ?, ?, ?)
                    """, (
                        "reflection",
                        reflection['text'],
                        json.dumps(reflection),
                        reflection['text']
                    ))
                    
                    reflections_created.append({
                        'id': cursor.lastrowid,
                        'type': reflection['type'],
                        'confidence': reflection['confidence'],
                        'summary_id': summary['id']
                    })
            
            conn.commit()
            
        logger.info(f"Created {len(reflections_created)} reflections")
        
        return {
            "status": "ok",
            "reflections_created": len(reflections_created),
            "details": reflections_created
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger observation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/questions")
async def get_pending_questions():
    """Hämta väntande frågor som Alice kan ställa"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            
            # Hämta reflektioner som kan bli frågor
            reflections = conn.execute("""
                SELECT * FROM memory 
                WHERE kind = 'reflection'
                AND json_extract(meta_json, '$.confidence') >= 0.5
                ORDER BY created_at DESC 
                LIMIT 5
            """).fetchall()
            
            questions = []
            for reflection in reflections:
                meta = json.loads(reflection['meta_json'])
                question = generate_question_from_reflection(reflection['text'], meta)
                if question:
                    questions.append({
                        'id': reflection['id'],
                        'question': question,
                        'confidence': meta.get('confidence', 0),
                        'type': meta.get('type', 'unknown'),
                        'created_at': reflection['created_at']
                    })
            
        return {
            "status": "ok",
            "questions": questions
        }
        
    except Exception as e:
        logger.error(f"Failed to get questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patterns")
async def get_behavior_patterns():
    """Analysera patterns från ambient data"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            
            # Hitta återkommande teman
            patterns = []
            
            # Tid-baserade patterns
            time_patterns = conn.execute("""
                SELECT 
                    strftime('%H', ts) as hour,
                    COUNT(*) as frequency,
                    GROUP_CONCAT(text, ' | ') as examples
                FROM ambient_raw 
                WHERE ts > datetime('now', '-7 days')
                GROUP BY strftime('%H', ts)
                HAVING frequency > 2
                ORDER BY frequency DESC
                LIMIT 10
            """).fetchall()
            
            for tp in time_patterns:
                patterns.append({
                    'type': 'time_pattern',
                    'pattern': f"Aktivitet runt {tp['hour']}:00",
                    'frequency': tp['frequency'],
                    'confidence': min(0.9, tp['frequency'] / 10),
                    'examples': tp['examples'][:200] + "..."
                })
            
            # Ord-frekvens patterns
            word_patterns = conn.execute("""
                SELECT 
                    text,
                    COUNT(*) as frequency
                FROM ambient_raw 
                WHERE ts > datetime('now', '-3 days')
                AND length(text) > 20
                GROUP BY lower(text)
                HAVING frequency > 1
                ORDER BY frequency DESC
                LIMIT 5
            """).fetchall()
            
            for wp in word_patterns:
                if wp['frequency'] > 2:
                    patterns.append({
                        'type': 'recurring_topic',
                        'pattern': wp['text'][:100] + "...",
                        'frequency': wp['frequency'],
                        'confidence': min(0.8, wp['frequency'] / 5)
                    })
            
        return {
            "status": "ok",
            "patterns": patterns
        }
        
    except Exception as e:
        logger.error(f"Failed to get patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def analyze_summary_for_patterns(summary) -> Optional[Dict[str, Any]]:
    """Analysera en summary för intressanta patterns"""
    text = summary['text'].lower()
    meta = json.loads(summary.get('meta_json', '{}'))
    
    # TODO detection
    todo_keywords = ['ska', 'kommer att', 'planerar', 'behöver', 'måste', 'vill', 'påminn']
    if any(keyword in text for keyword in todo_keywords):
        return {
            'type': 'todo_detected',
            'text': f"Upptäckt möjlig TODO: {text[:100]}",
            'confidence': 0.7,
            'source_summary_id': summary['id'],
            'keywords_found': [kw for kw in todo_keywords if kw in text]
        }
    
    # Vanor/rutiner
    habit_keywords = ['varje dag', 'brukar', 'alltid', 'vanligtvis', 'klockan', 'på morgonen', 'på kvällen']
    if any(keyword in text for keyword in habit_keywords):
        return {
            'type': 'habit_detected',
            'text': f"Möjlig vana/rutin: {text[:100]}",
            'confidence': 0.6,
            'source_summary_id': summary['id'],
            'keywords_found': [kw for kw in habit_keywords if kw in text]
        }
    
    # Problem/frustration
    problem_keywords = ['problem', 'fungerar inte', 'fel', 'trasig', 'irriterad', 'frustrerad']
    if any(keyword in text for keyword in problem_keywords):
        return {
            'type': 'problem_detected',
            'text': f"Upptäckt problem: {text[:100]}",
            'confidence': 0.8,
            'source_summary_id': summary['id'],
            'keywords_found': [kw for kw in problem_keywords if kw in text]
        }
    
    return None

def generate_question_from_reflection(reflection_text: str, meta: Dict) -> Optional[str]:
    """Generera en fråga som Alice kan ställa baserat på reflektion"""
    ref_type = meta.get('type', '')
    
    if ref_type == 'todo_detected':
        return "Vill du att jag skapar en påminnelse för det du nämnde?"
        
    elif ref_type == 'habit_detected':
        return "Märker att du ofta gör detta - ska jag hjälpa dig optimera rutinen?"
        
    elif ref_type == 'problem_detected':
        return "Du verkade frustrerad över något - kan jag hjälpa till på något sätt?"
        
    else:
        # Generell fråga
        return "Har du någon reflektion om det vi pratade om tidigare?"
    
    return None

# Export
__all__ = ['router']