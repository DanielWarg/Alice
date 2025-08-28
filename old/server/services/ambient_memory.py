from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import logging
from pathlib import Path
import asyncio
import time

# Import our enhanced logging
from logger_config import get_logger

router = APIRouter(prefix="/api/memory/ambient", tags=["ambient"])
logger = get_logger("ambient_memory")

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "ambient.db"
DB_PATH.parent.mkdir(exist_ok=True)

class AmbientChunk(BaseModel):
    text: str
    ts: str  # ISO timestamp
    conf: float = Field(ge=0, le=1)
    speaker: Optional[str] = "user"
    source: str = "realtime"
    importance: Optional[Dict[str, Any]] = None

class IngestRawRequest(BaseModel):
    chunks: List[AmbientChunk]

class SummaryRequest(BaseModel):
    windowSec: int
    highlights: List[Dict[str, Any]]
    rawRef: str
    windowStart: str
    windowEnd: str
    chunkCount: int

class CleanRequest(BaseModel):
    olderThanMinutes: Optional[int] = None

# Initialize database
def init_ambient_db():
    """Skapa tabeller för ambient memory systemet"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ambient_raw (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts DATETIME NOT NULL,
                text TEXT NOT NULL,
                conf REAL NOT NULL,
                speaker TEXT,
                source TEXT NOT NULL DEFAULT 'realtime',
                importance_json TEXT,
                expires_at DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                meta_json TEXT,
                embedding_vector BLOB,
                fts_text TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_ambient_raw_ts ON ambient_raw(ts);
            CREATE INDEX IF NOT EXISTS idx_ambient_raw_expires ON ambient_raw(expires_at);
            CREATE INDEX IF NOT EXISTS idx_memory_kind ON memory(kind);
            CREATE INDEX IF NOT EXISTS idx_memory_created ON memory(created_at);
            
            -- FTS5 tabell för fulltext search
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                id UNINDEXED,
                text,
                content='memory',
                content_rowid='id'
            );
            
            -- Triggers för att synka FTS
            CREATE TRIGGER IF NOT EXISTS memory_fts_insert AFTER INSERT ON memory BEGIN
                INSERT INTO memory_fts(id, text) VALUES (new.id, new.fts_text);
            END;
            
            CREATE TRIGGER IF NOT EXISTS memory_fts_delete AFTER DELETE ON memory BEGIN
                DELETE FROM memory_fts WHERE id = old.id;
            END;
        """)
        logger.info("Ambient database initialized")

# Initialize on import
init_ambient_db()

@router.post("/ingest-raw")
async def ingest_raw_chunks(request: IngestRawRequest):
    """Lagra råa transkriberings-chunks med TTL"""
    start_time = time.time()
    
    logger.log_user_interaction("ingest_raw_chunks", chunks_count=len(request.chunks))
    
    try:
        # TTL från env eller default 2 timmar
        import os
        ttl_minutes = int(os.getenv('AMBIENT_RAW_TTL_MIN', '120'))
        
        logger.debug(f"Using TTL: {ttl_minutes} minutes for {len(request.chunks)} chunks")
        
        high_importance_count = 0
        total_chars = 0
        
        with sqlite3.connect(DB_PATH) as conn:
            for i, chunk in enumerate(request.chunks):
                ts = datetime.fromisoformat(chunk.ts.replace('Z', '+00:00'))
                expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
                
                importance_json = json.dumps(chunk.importance) if chunk.importance else None
                importance_score = chunk.importance.get('score', 0) if chunk.importance else 0
                
                if importance_score >= 2:
                    high_importance_count += 1
                    logger.debug(f"High importance chunk: '{chunk.text[:50]}...' (score: {importance_score})")
                
                total_chars += len(chunk.text)
                
                conn.execute("""
                    INSERT INTO ambient_raw 
                    (ts, text, conf, speaker, source, importance_json, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    ts, chunk.text, chunk.conf, chunk.speaker, 
                    chunk.source, importance_json, expires_at
                ))
            
            conn.commit()
            
        duration_ms = (time.time() - start_time) * 1000
        
        logger.log_performance("ingest_raw_chunks", duration_ms, 
                              chunks=len(request.chunks), 
                              high_importance=high_importance_count,
                              total_chars=total_chars)
        
        logger.log_data_flow("chunks_ingested", len(request.chunks), 
                            ttl_minutes=ttl_minutes,
                            high_importance_ratio=high_importance_count/len(request.chunks))
            
        return {
            "status": "ok", 
            "ingested": len(request.chunks),
            "ttl_minutes": ttl_minutes,
            "high_importance_count": high_importance_count,
            "processing_time_ms": duration_ms
        }
        
    except Exception as e:
        logger.log_error_with_context(e, "ingest_raw_chunks", 
                                     chunks_count=len(request.chunks))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/summary")
async def create_ambient_summary(request: SummaryRequest, background_tasks: BackgroundTasks):
    """Skapa komprimerad sammanfattning från highlights"""
    try:
        if not request.highlights:
            raise HTTPException(status_code=400, detail="No highlights provided")
        
        # Förbered text för LLM
        highlights_text = "\n".join([
            f"[{h.get('ts', 'N/A')}] {h.get('text', '')}" 
            for h in request.highlights
        ])
        
        # Kalla LLM för sammanfattning
        summary_text = await generate_ambient_summary(highlights_text, request.windowSec)
        
        # Spara i memory tabell
        with sqlite3.connect(DB_PATH) as conn:
            meta = {
                "windowStart": request.windowStart,
                "windowEnd": request.windowEnd,
                "source": "always-on",
                "highlights": request.highlights,
                "chunkCount": request.chunkCount,
                "rawRef": request.rawRef
            }
            
            cursor = conn.execute("""
                INSERT INTO memory (kind, text, meta_json, fts_text)
                VALUES (?, ?, ?, ?)
            """, (
                "ambient_summary",
                summary_text,
                json.dumps(meta),
                summary_text  # FTS text samma som summary
            ))
            
            summary_id = cursor.lastrowid
            conn.commit()
            
        logger.info(f"Created ambient summary {summary_id} from {len(request.highlights)} highlights")
        
        # Schemalägg reflektion i bakgrunden
        background_tasks.add_task(trigger_reflection, summary_id, summary_text, meta)
        
        return {
            "status": "ok",
            "summary_id": summary_id,
            "highlights_processed": len(request.highlights),
            "summary_length": len(summary_text)
        }
        
    except Exception as e:
        logger.error(f"Failed to create summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clean")
async def clean_expired_data(request: Optional[CleanRequest] = None):
    """Rensa gamla ambient_raw entries"""
    try:
        cutoff_time = datetime.now(timezone.utc)
        if request and request.olderThanMinutes:
            cutoff_time -= timedelta(minutes=request.olderThanMinutes)
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                DELETE FROM ambient_raw 
                WHERE expires_at < ?
            """, (cutoff_time,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
        logger.info(f"Cleaned {deleted_count} expired ambient raw entries")
        
        return {
            "status": "ok",
            "deleted_count": deleted_count,
            "cutoff_time": cutoff_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to clean expired data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_ambient_stats():
    """Debug endpoint för att se status"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Räkna raw chunks
            raw_total = conn.execute("SELECT COUNT(*) FROM ambient_raw").fetchone()[0]
            raw_expired = conn.execute(
                "SELECT COUNT(*) FROM ambient_raw WHERE expires_at < ?", 
                (datetime.now(timezone.utc),)
            ).fetchone()[0]
            
            # Räkna summaries
            summaries_total = conn.execute(
                "SELECT COUNT(*) FROM memory WHERE kind = 'ambient_summary'"
            ).fetchone()[0]
            
            # Senaste summary
            latest_summary = conn.execute("""
                SELECT created_at, text 
                FROM memory 
                WHERE kind = 'ambient_summary' 
                ORDER BY created_at DESC 
                LIMIT 1
            """).fetchone()
            
        return {
            "ambient_raw": {
                "total": raw_total,
                "expired": raw_expired,
                "active": raw_total - raw_expired
            },
            "summaries": {
                "total": summaries_total,
                "latest": {
                    "created_at": latest_summary[0] if latest_summary else None,
                    "preview": latest_summary[1][:100] + "..." if latest_summary and latest_summary[1] else None
                } if latest_summary else None
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_ambient_summary(highlights_text: str, window_sec: int) -> str:
    """Generera sammanfattning med LLM"""
    try:
        from openai import AsyncOpenAI
        import os
        
        client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        window_min = window_sec // 60
        
        prompt = f"""Du är en assistent som destillerar vardagligt tal.
        
Här är transkript-bitar från de senaste {window_min} minuterna. 

Uppgift:
1) Sammanfatta neutralt i 3–6 bullets på svenska.
2) Lista "TODO/Vanor/Preferenser" om tydliga.  
3) Spara bara det som kan vara nyttigt senare. Undvik småprat.

TRANSKRIPT:
{highlights_text}

Sammanfatta:"""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content.strip()
        logger.info(f"Generated summary: {len(summary)} chars")
        return summary
        
    except Exception as e:
        logger.error(f"Failed to generate LLM summary: {e}")
        # Fallback: enkel text-sammanslagning
        lines = highlights_text.split('\n')[:5]
        return f"Sammanfattning ({window_sec//60}min): " + "; ".join([
            line.split('] ', 1)[-1] if '] ' in line else line 
            for line in lines
        ])

async def trigger_reflection(summary_id: int, summary_text: str, meta: dict):
    """Trigger reflection logic för spontan dialog"""
    try:
        # Enkel heuristik: sök efter TODO patterns
        todo_patterns = ['ska', 'kommer att', 'planerar', 'behöver', 'måste', 'vill']
        has_todo = any(pattern in summary_text.lower() for pattern in todo_patterns)
        
        # Återkommande tema check (mockat för nu)
        recurring_theme = 'kaffe' in summary_text.lower()
        
        if has_todo or recurring_theme:
            with sqlite3.connect(DB_PATH) as conn:
                reflection = {
                    "type": "hypothesis" if recurring_theme else "todo_detected",
                    "text": summary_text[:200],
                    "confidence": 0.6 if recurring_theme else 0.8,
                    "source_summary_id": summary_id
                }
                
                conn.execute("""
                    INSERT INTO memory (kind, text, meta_json, fts_text)
                    VALUES (?, ?, ?, ?)
                """, (
                    "reflection",
                    f"Reflektion: {reflection['text']}",
                    json.dumps(reflection),
                    reflection['text']
                ))
                conn.commit()
                
            logger.info(f"Created reflection for summary {summary_id}")
            
    except Exception as e:
        logger.error(f"Failed to trigger reflection: {e}")

# Export router för huvudappen
__all__ = ['router', 'init_ambient_db']