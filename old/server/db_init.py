#!/usr/bin/env python3
"""
Database initialization för Alice Ambient Memory system
Kör detta skript för att säkerställa att alla tabeller finns
"""

import sys
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_ambient_db():
    """Skapa tabeller för ambient memory systemet"""
    db_path = Path(__file__).parent / "data" / "ambient.db"
    db_path.parent.mkdir(exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
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

def main():
    """Initialisera alla databaser"""
    try:
        logger.info("Initializing ambient memory database...")
        init_ambient_db()
        logger.info("✅ Database initialization completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())