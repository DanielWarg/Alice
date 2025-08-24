#!/usr/bin/env python3
"""
E2E test för Ambient Memory systemet
Testar hela flödet från partials -> ingest -> summary -> reflection
"""

import asyncio
import aiohttp
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "data" / "ambient.db"
BASE_URL = "http://127.0.0.1:8000"

class AmbientE2ETest:
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_ingest_raw_chunks(self):
        """Test 1: Ingest raw chunks"""
        logger.info("🧪 Testing raw chunk ingestion...")
        
        chunks = [
            {
                "text": "jag ska handla mjölk och bröd imorgon",
                "ts": datetime.now(timezone.utc).isoformat() + "Z",
                "conf": 0.9,
                "speaker": "user",
                "source": "realtime",
                "importance": {"score": 2, "reasons": ["first_person_intention", "time_references"]}
            },
            {
                "text": "påminn mig om mötet klockan tre",
                "ts": (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat() + "Z",
                "conf": 0.85,
                "speaker": "user", 
                "source": "realtime",
                "importance": {"score": 3, "reasons": ["first_person_intention", "time_references", "named_entities"]}
            },
            {
                "text": "mm okej ja",
                "ts": (datetime.utcnow() + timedelta(seconds=60)).isoformat() + "Z",
                "conf": 0.7,
                "speaker": "user",
                "source": "realtime", 
                "importance": {"score": 0, "reasons": ["small_talk", "too_short"]}
            }
        ]
        
        async with self.session.post(
            f"{BASE_URL}/api/memory/ambient/ingest-raw",
            json={"chunks": chunks}
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()
            assert data["status"] == "ok"
            assert data["ingested"] == 3
            logger.info(f"✅ Ingested {data['ingested']} chunks with TTL {data['ttl_minutes']}min")
            
        return chunks
    
    async def test_create_summary(self, chunks):
        """Test 2: Create ambient summary från highlights"""
        logger.info("🧪 Testing ambient summary creation...")
        
        # Bara chunks med hög importance score
        highlights = [
            {
                "text": chunk["text"],
                "score": chunk["importance"]["score"],
                "ts": chunk["ts"]
            }
            for chunk in chunks
            if chunk["importance"]["score"] >= 2
        ]
        
        window_start = (datetime.utcnow() - timedelta(minutes=2)).isoformat() + "Z"
        window_end = datetime.utcnow().isoformat() + "Z"
        
        async with self.session.post(
            f"{BASE_URL}/api/memory/ambient/summary",
            json={
                "windowSec": 120,
                "highlights": highlights,
                "rawRef": f"ambient:{window_start}",
                "windowStart": window_start,
                "windowEnd": window_end,
                "chunkCount": len(chunks)
            }
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()
            assert data["status"] == "ok"
            assert "summary_id" in data
            logger.info(f"✅ Created summary {data['summary_id']} from {data['highlights_processed']} highlights")
            
        return data["summary_id"]
    
    async def test_database_content(self, summary_id):
        """Test 3: Verifiera databasinnehåll"""
        logger.info("🧪 Testing database content...")
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            
            # Kontrollera raw chunks
            raw_count = conn.execute("SELECT COUNT(*) FROM ambient_raw").fetchone()[0]
            assert raw_count >= 3, f"Expected at least 3 raw chunks, got {raw_count}"
            
            # Kontrollera summary
            summary = conn.execute(
                "SELECT * FROM memory WHERE kind = 'ambient_summary' AND id = ?",
                (summary_id,)
            ).fetchone()
            assert summary is not None, "Summary not found in database"
            assert len(summary['text']) > 0, "Summary text is empty"
            
            # Kontrollera FTS
            fts_result = conn.execute(
                "SELECT * FROM memory_fts WHERE id = ?",
                (summary_id,)
            ).fetchone()
            assert fts_result is not None, "Summary not found in FTS index"
            
            logger.info(f"✅ Database verification passed")
            logger.info(f"   Raw chunks: {raw_count}")
            logger.info(f"   Summary text: {summary['text'][:100]}...")
    
    async def test_reflection_trigger(self, summary_id):
        """Test 4: Trigger reflection analysis"""
        logger.info("🧪 Testing reflection trigger...")
        
        async with self.session.post(
            f"{BASE_URL}/api/reflect/observe",
            json={"summary_id": summary_id, "trigger": "test"}
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()
            assert data["status"] == "ok"
            logger.info(f"✅ Triggered reflection, created {data['reflections_created']} reflections")
    
    async def test_get_stats(self):
        """Test 5: Hämta system stats"""
        logger.info("🧪 Testing stats endpoint...")
        
        async with self.session.get(f"{BASE_URL}/api/memory/ambient/stats") as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()
            assert "ambient_raw" in data
            assert "summaries" in data
            logger.info(f"✅ Stats retrieved")
            logger.info(f"   Raw chunks: {data['ambient_raw']['total']} total, {data['ambient_raw']['active']} active")
            logger.info(f"   Summaries: {data['summaries']['total']} total")
    
    async def test_clean_expired(self):
        """Test 6: Cleanup av expired data"""
        logger.info("🧪 Testing cleanup...")
        
        async with self.session.post(
            f"{BASE_URL}/api/memory/ambient/clean",
            json={"olderThanMinutes": 0}  # Rensa allt äldre än 0 minuter (allt)
        ) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = await resp.json()
            assert data["status"] == "ok"
            logger.info(f"✅ Cleaned {data['deleted_count']} expired entries")

async def main():
    """Kör hela E2E test suite"""
    logger.info("🚀 Starting Ambient Memory E2E Tests")
    
    try:
        async with AmbientE2ETest() as test:
            # Test hela flödet
            chunks = await test.test_ingest_raw_chunks()
            summary_id = await test.test_create_summary(chunks)
            await test.test_database_content(summary_id)
            await test.test_reflection_trigger(summary_id)
            await test.test_get_stats()
            await test.test_clean_expired()
            
        logger.info("🎉 All E2E tests passed!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ E2E test failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))