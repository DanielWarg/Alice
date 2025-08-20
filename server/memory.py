from __future__ import annotations

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any


class MemoryStore:
    def __init__(self, db_path: str) -> None:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    payload TEXT
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_events_topic_ts ON events(topic, ts)")
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    kind TEXT NOT NULL,         -- 'text' | 'image' (future)
                    text TEXT,                  -- for kind='text'
                    score REAL DEFAULT 0.0,
                    tags TEXT                   -- JSON string of tags/metadata
                )
                """
            )
            c.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memories_text ON memories(text)
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    text TEXT NOT NULL,
                    score REAL DEFAULT 0.0,
                    tags TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS tool_stats (
                    tool TEXT PRIMARY KEY,
                    success INTEGER DEFAULT 0,
                    fail INTEGER DEFAULT 0
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS cv_frames (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    source TEXT,
                    meta TEXT                -- JSON (objects, notes)
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS sensor_timeseries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    sensor TEXT NOT NULL,
                    value REAL,
                    meta TEXT                -- JSON
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_sensor_ts ON sensor_timeseries(sensor, ts)")
            # Conversation context tracking
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    ts TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    memory_id INTEGER,
                    FOREIGN KEY (memory_id) REFERENCES memories(id)
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id, ts)")
            # Embeddings för semantisk sökning
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    mem_id INTEGER PRIMARY KEY,
                    ts TEXT NOT NULL,
                    model TEXT,
                    dim INTEGER,
                    vector TEXT
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model)")
            # FTS5 for BM25 retrieval (external content table referencing memories)
            try:
                c.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
                    USING fts5(text, content='memories', content_rowid='id');
                    """
                )
                # Keep FTS in sync with base table
                c.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                        INSERT INTO memories_fts(rowid, text) VALUES (new.id, new.text);
                    END;
                    """
                )
                c.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                        INSERT INTO memories_fts(memories_fts, rowid, text) VALUES('delete', old.id, old.text);
                    END;
                    """
                )
                c.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                        INSERT INTO memories_fts(memories_fts, rowid, text) VALUES('delete', old.id, old.text);
                        INSERT INTO memories_fts(rowid, text) VALUES (new.id, new.text);
                    END;
                    """
                )
            except Exception:
                # FTS5 may be unavailable; skip without failing init
                pass

    def ping(self) -> bool:
        try:
            with self._conn() as c:
                c.execute("SELECT 1")
            return True
        except Exception:
            return False

    def append_event(self, topic: str, payload: Optional[str]) -> None:
        ts = datetime.utcnow().isoformat() + "Z"
        with self._conn() as c:
            c.execute(
                "INSERT INTO events (ts, topic, payload) VALUES (?, ?, ?)",
                (ts, topic, payload),
            )

    # --- Memories (text) ---
    def _chunk_text_semantically(self, text: str, max_chunk_size: int = 500) -> List[str]:
        """Smart text chunking that preserves semantic boundaries"""
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        # First split by double newlines (paragraphs)
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        for paragraph in paragraphs:
            # If paragraph alone is too long, split by sentences
            if len(paragraph) > max_chunk_size:
                # Split by sentence endings
                sentences = []
                for delimiter in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
                    if delimiter in paragraph:
                        parts = paragraph.split(delimiter)
                        for i, part in enumerate(parts[:-1]):
                            sentences.append(part + delimiter.strip())
                        if parts[-1].strip():
                            sentences.append(parts[-1])
                        break
                else:
                    # No sentence delimiters found, split by length
                    sentences = [paragraph[i:i+max_chunk_size] 
                               for i in range(0, len(paragraph), max_chunk_size)]
                
                # Process sentences
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > max_chunk_size:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence
                    else:
                        current_chunk += (' ' if current_chunk else '') + sentence
            else:
                # Normal paragraph processing
                if len(current_chunk) + len(paragraph) > max_chunk_size:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    current_chunk += ('\n\n' if current_chunk else '') + paragraph
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]

    def upsert_text_memory(self, text: str, score: float = 0.0, tags_json: Optional[str] = None, auto_chunk: bool = True) -> List[int]:
        """Insert text memory with optional semantic chunking for long texts"""
        if not auto_chunk or len(text) <= 500:
            # Single memory entry
            ts = datetime.utcnow().isoformat() + "Z"
            with self._conn() as c:
                cur = c.execute(
                    "INSERT INTO memories (ts, kind, text, score, tags) VALUES (?, 'text', ?, ?, ?)",
                    (ts, text, score, tags_json),
                )
                return [int(cur.lastrowid)]
        
        # Chunked memory entries
        chunks = self._chunk_text_semantically(text)
        memory_ids = []
        ts = datetime.utcnow().isoformat() + "Z"
        
        # Add chunk metadata to tags
        import json
        base_tags = json.loads(tags_json) if tags_json else {}
        base_tags.update({
            "chunked": True,
            "total_chunks": len(chunks),
            "original_length": len(text)
        })
        
        with self._conn() as c:
            for i, chunk in enumerate(chunks):
                chunk_tags = base_tags.copy()
                chunk_tags["chunk_index"] = i
                chunk_tags_json = json.dumps(chunk_tags, ensure_ascii=False)
                
                cur = c.execute(
                    "INSERT INTO memories (ts, kind, text, score, tags) VALUES (?, 'text', ?, ?, ?)",
                    (ts, chunk, score, chunk_tags_json),
                )
                memory_ids.append(int(cur.lastrowid))
        
        return memory_ids
    
    def upsert_text_memory_single(self, text: str, score: float = 0.0, tags_json: Optional[str] = None) -> int:
        """Backward compatible version that returns single memory ID"""
        memory_ids = self.upsert_text_memory(text, score, tags_json, auto_chunk=False)
        return memory_ids[0]

    def retrieve_text_memories(self, query: str, limit: int = 5):
        # Simple LIKE-based retrieval as a baseline; embeddings can replace this later
        like = f"%{query}%"
        with self._conn() as c:
            cur = c.execute(
                """
                SELECT id, ts, kind, text, score, tags
                FROM memories
                WHERE kind='text' AND (text LIKE ?)
                ORDER BY score DESC, ts DESC
                LIMIT ?
                """,
                (like, limit),
            )
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]

    def retrieve_text_bm25_recency(self, query: str, limit: int = 5, context_bonus: float = 0.0) -> List[Dict[str, Any]]:
        """Advanced hybrid retrieval: FTS5 BM25 + recency + relevance + context.
        Returns top items with optimized combined score.
        """
        try:
            with self._conn() as c:
                cur = c.execute(
                    """
                    SELECT m.id, m.ts, m.kind, m.text, m.score, m.tags,
                           bm25(memories_fts) AS rank
                    FROM memories_fts
                    JOIN memories m ON m.id = memories_fts.rowid
                    WHERE memories_fts MATCH ? AND m.kind='text'
                    ORDER BY rank ASC
                    LIMIT 100
                    """,
                    (query,)
                )
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]
                items = [dict(zip(cols, r)) for r in rows]
        except Exception:
            # FTS not available; fallback to LIKE
            return self.retrieve_text_memories(query, limit)

        if not items:
            return []

        # Advanced multi-factor scoring
        now = datetime.utcnow()
        def to_dt(ts: str) -> Optional[datetime]:
            if not ts:
                return None
            t = ts.rstrip("Z")
            try:
                return datetime.fromisoformat(t)
            except Exception:
                return None

        rescored = []
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        for it in items:
            # 1. BM25 relevance (lower rank = higher relevance)
            bm25_score = max(0.0, 10.0 - float(it.get("rank") or 100.0))
            
            # 2. Recency with improved decay
            ts = to_dt(str(it.get("ts") or ""))
            if ts:
                age_hours = (now - ts).total_seconds() / 3600.0
                # Multi-tier recency: bonus for very recent, gradual decay
                if age_hours < 1:
                    recency = 5.0  # Very recent
                elif age_hours < 24:
                    recency = 3.0  # Same day
                elif age_hours < 168:  # 1 week
                    recency = 2.0
                else:
                    age_days = age_hours / 24.0
                    recency = max(0.0, 1.0 - (age_days / 60.0))  # Decay over 2 months
            else:
                recency = 0.0
            
            # 3. Explicit score (user/system assigned importance)
            explicit = float(it.get("score") or 0.0)
            
            # 4. Text quality indicators
            text = str(it.get("text") or "")
            text_lower = text.lower()
            
            # Length bonus (neither too short nor too long)
            length = len(text)
            if 50 <= length <= 500:
                length_bonus = 1.0
            elif length > 500:
                length_bonus = 0.5  # Long texts get reduced priority
            else:
                length_bonus = 0.3  # Very short texts get reduced priority
            
            # Query word coverage
            text_words = set(text_lower.split())
            coverage = len(query_words.intersection(text_words)) / max(1, len(query_words))
            coverage_bonus = coverage * 2.0
            
            # 5. Context bonus (for related conversations)
            context_score = context_bonus if any(word in text_lower for word in query_words) else 0.0
            
            # 6. Combined scoring with optimized weights
            combined = (
                bm25_score * 1.0 +          # BM25 relevance
                recency * 0.8 +             # Recency importance
                explicit * 0.5 +            # Explicit user score
                length_bonus * 0.3 +        # Text quality
                coverage_bonus * 0.7 +      # Query coverage
                context_score * 0.4         # Context bonus
            )
            
            rescored.append((combined, it, {
                'bm25': bm25_score, 'recency': recency, 'explicit': explicit,
                'length_bonus': length_bonus, 'coverage': coverage_bonus,
                'context': context_score, 'final': combined
            }))
        
        # Sort by combined score and return top results
        rescored.sort(key=lambda x: x[0], reverse=True)
        top = [it for _, it, _ in rescored[: max(1, limit)]]
        return top

    def get_recent_text_memories(self, limit: int = 10):
        with self._conn() as c:
            cur = c.execute(
                """
                SELECT id, ts, kind, text, score, tags
                FROM memories
                WHERE kind='text'
                ORDER BY ts DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]

    def get_all_tool_stats(self):
        with self._conn() as c:
            cur = c.execute("SELECT tool, success, fail FROM tool_stats ORDER BY (success+fail) DESC, tool ASC")
            rows = cur.fetchall()
            return [
                {"tool": r[0], "success": int(r[1] or 0), "fail": int(r[2] or 0)}
                for r in rows
            ]

    # --- Embeddings ---
    def upsert_embedding(self, mem_id: int, model: str, dim: int, vector_json: str) -> None:
        ts = datetime.utcnow().isoformat() + "Z"
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO embeddings (mem_id, ts, model, dim, vector) VALUES (?, ?, ?, ?, ?)",
                (mem_id, ts, model, dim, vector_json),
            )

    def get_all_embeddings(self, model: str):
        with self._conn() as c:
            cur = c.execute("SELECT mem_id, dim, vector FROM embeddings WHERE model = ?", (model,))
            return cur.fetchall()

    def get_texts_for_mem_ids(self, ids):
        if not ids:
            return {}
        qmarks = ",".join(["?"] * len(ids))
        with self._conn() as c:
            cur = c.execute(
                f"SELECT id, text FROM memories WHERE id IN ({qmarks})",
                tuple(ids),
            )
            return {int(r[0]): (r[1] or "") for r in cur.fetchall()}

    def update_memory_score(self, mem_id: int, delta: float) -> None:
        with self._conn() as c:
            c.execute("UPDATE memories SET score = COALESCE(score,0) + ? WHERE id = ?", (delta, mem_id))

    def update_tool_stats(self, tool: str, success: bool) -> None:
        with self._conn() as c:
            # Upsert-like behavior for SQLite
            c.execute("INSERT OR IGNORE INTO tool_stats(tool, success, fail) VALUES (?, 0, 0)", (tool,))
            if success:
                c.execute("UPDATE tool_stats SET success = success + 1 WHERE tool = ?", (tool,))
            else:
                c.execute("UPDATE tool_stats SET fail = fail + 1 WHERE tool = ?", (tool,))

    def get_tool_stats(self, tool: str):
        with self._conn() as c:
            cur = c.execute("SELECT success, fail FROM tool_stats WHERE tool = ?", (tool,))
            row = cur.fetchone()
            if not row:
                return 0, 0
            return int(row[0] or 0), int(row[1] or 0)

    # --- Perception/Sensors ---
    def add_cv_frame(self, source: str, meta_json: str) -> int:
        ts = datetime.utcnow().isoformat() + "Z"
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO cv_frames (ts, source, meta) VALUES (?, ?, ?)",
                (ts, source, meta_json),
            )
            return int(cur.lastrowid)

    def add_sensor_telemetry(self, sensor: str, value: float, meta_json: str = None) -> int:
        ts = datetime.utcnow().isoformat() + "Z"
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO sensor_timeseries (ts, sensor, value, meta) VALUES (?, ?, ?, ?)",
                (ts, sensor, value, meta_json),
            )
            return int(cur.lastrowid)
    
    # --- Conversation Context Tracking ---
    def add_conversation_turn(self, session_id: str, role: str, content: str, memory_id: int = None) -> int:
        """Add a conversation turn for context tracking"""
        ts = datetime.utcnow().isoformat() + "Z"
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO conversations (session_id, ts, role, content, memory_id) VALUES (?, ?, ?, ?, ?)",
                (session_id, ts, role, content, memory_id),
            )
            return int(cur.lastrowid)
    
    def get_conversation_context(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation context for a session"""
        with self._conn() as c:
            cur = c.execute(
                """
                SELECT id, ts, role, content, memory_id
                FROM conversations
                WHERE session_id = ?
                ORDER BY ts DESC
                LIMIT ?
                """,
                (session_id, limit),
            )
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in reversed(rows)]  # Reverse to chronological order
    
    def get_related_memories_from_context(self, session_id: str, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Retrieve memories related to current conversation context"""
        # Get recent conversation turns
        context = self.get_conversation_context(session_id, limit=5)
        
        if not context:
            return self.retrieve_text_bm25_recency(query, limit)
        
        # Extract keywords from recent conversation
        context_words = set()
        for turn in context[-3:]:  # Last 3 turns
            content = turn.get('content', '').lower()
            words = content.split()
            context_words.update(word.strip('.,!?;:') for word in words if len(word) > 3)
        
        # Enhanced query with context
        if context_words:
            context_query = query + ' ' + ' '.join(list(context_words)[:5])
            return self.retrieve_text_bm25_recency(context_query, limit, context_bonus=1.0)
        
        return self.retrieve_text_bm25_recency(query, limit)
    
    def cleanup_old_conversations(self, days: int = 30) -> int:
        """Clean up old conversation history"""
        cutoff = datetime.utcnow().timestamp() - (days * 24 * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat() + "Z"
        
        with self._conn() as c:
            cur = c.execute(
                "DELETE FROM conversations WHERE ts < ?",
                (cutoff_iso,)
            )
            return cur.rowcount


