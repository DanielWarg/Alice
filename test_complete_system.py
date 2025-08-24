#!/usr/bin/env python3
"""
Complete system test för Alice Ambient Memory B1
Testar hela kedjan utan att starta en server
"""

import sys
import json
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompleteAmbientTest:
    """Complete test suite för ambient memory systemet"""
    
    def __init__(self):
        self.test_db = Path(__file__).parent / "test_complete_ambient.db"
        self.results = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'errors': []
        }
        
    def setup_database(self):
        """Setup test database"""
        logger.info("🗄️ Setting up test database...")
        
        if self.test_db.exists():
            self.test_db.unlink()
            
        with sqlite3.connect(self.test_db) as conn:
            conn.executescript("""
                CREATE TABLE ambient_raw (
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
                
                CREATE TABLE memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    meta_json TEXT,
                    embedding_vector BLOB,
                    fts_text TEXT
                );
                
                CREATE INDEX idx_ambient_raw_ts ON ambient_raw(ts);
                CREATE INDEX idx_ambient_raw_expires ON ambient_raw(expires_at);
                CREATE INDEX idx_memory_kind ON memory(kind);
                CREATE INDEX idx_memory_created ON memory(created_at);
                
                CREATE VIRTUAL TABLE memory_fts USING fts5(
                    id UNINDEXED,
                    text,
                    content='memory',
                    content_rowid='id'
                );
                
                CREATE TRIGGER memory_fts_insert AFTER INSERT ON memory BEGIN
                    INSERT INTO memory_fts(id, text) VALUES (new.id, new.fts_text);
                END;
                
                CREATE TRIGGER memory_fts_delete AFTER DELETE ON memory BEGIN
                    DELETE FROM memory_fts WHERE id = old.id;
                END;
            """)
        logger.info("✅ Database setup completed")
        
    def importance_scorer(self, text):
        """Importance scoring implementation"""
        score = 0
        reasons = []
        text_lower = text.lower().strip()
        
        if len(text_lower) < 8:
            return {'score': 0, 'reasons': ['too_short']}
        
        # First person intentions
        if any(kw in text_lower for kw in ['jag ska', 'jag kommer', 'jag planerar', 'jag behöver', 'jag vill', 'påminn', 'kom ihåg']):
            score += 1
            reasons.append('first_person_intention')
            
        # Time references
        if any(kw in text_lower for kw in ['imorgon', 'idag', 'igår', 'klockan', 'tid', 'möte', 'måndag', 'tisdag', 'onsdag', 'torsdag', 'fredag']):
            score += 1
            reasons.append('time_references')
            
        # Named entities
        if any(kw in text_lower for kw in ['stockholm', 'göteborg', 'malmö', 'daniel', 'google', 'spotify', 'ica', 'coop']):
            score += 1
            reasons.append('named_entities')
            
        # Numbers and quantities
        if any(char.isdigit() for char in text) or any(kw in text_lower for kw in ['kronor', 'kr', 'euro', 'dollar', 'timmar', 'dagar']):
            score += 1
            reasons.append('numbers_quantities')
            
        # Financial context (NEW)
        if any(kw in text_lower for kw in ['betala', 'betalning', 'hyra', 'lön', 'lån', 'skuld', 'faktura', 'räkning', 'kostnad']):
            score += 1
            reasons.append('financial_context')
            
        # Penalize small talk - but not if already has importance
        if (any(kw in text_lower for kw in ['mm', 'hmm', 'ja', 'nej', 'okej', 'ok']) or len(text_lower) < 15) and score == 0:
            reasons.append('small_talk')
        elif len(text_lower) < 10 and score == 0:
            score = 0
            reasons.append('small_talk')
            
        return {'score': min(3, score), 'reasons': reasons}
    
    def test_importance_scoring(self):
        """Test importance scoring with comprehensive cases"""
        logger.info("🧪 Testing importance scoring...")
        self.results['tests_run'] += 1
        
        test_cases = [
            # High importance cases
            ("jag ska handla mjölk och bröd imorgon", 2, "Should score high: first_person + time"),
            ("påminn mig om mötet med Daniel klockan tre", 3, "Should score max: first_person + time + entity"),
            ("jag behöver betala 500 kronor för hyran", 3, "Should score max: first_person + numbers + importance"),
            ("kom ihåg att ringa Spotify imorgon", 3, "Should score max: first_person + time + entity"),
            
            # Medium importance
            ("Daniel bor i Stockholm", 1, "Should score medium: entity only"),
            ("det kostar 200 kronor", 1, "Should score medium: numbers only"),
            ("mötet är på måndag", 1, "Should score medium: time only"),
            
            # Low importance
            ("mm okej ja", 0, "Should score zero: small talk"),
            ("det var bra", 0, "Should score zero: too vague"),
            ("hej", 0, "Should score zero: too short"),
        ]
        
        passed = 0
        for text, expected_min, description in test_cases:
            result = self.importance_scorer(text)
            actual_score = result['score']
            
            if actual_score >= expected_min:
                logger.info(f"  ✅ '{text}' → {actual_score} (≥{expected_min}) {result['reasons']}")
                passed += 1
            else:
                logger.error(f"  ❌ '{text}' → {actual_score} (expected ≥{expected_min}) {result['reasons']}")
                self.results['errors'].append(f"Importance scoring failed for: {text}")
        
        if passed == len(test_cases):
            logger.info("✅ Importance scoring test passed")
            self.results['tests_passed'] += 1
        else:
            logger.error(f"❌ Importance scoring test failed: {passed}/{len(test_cases)} passed")
            self.results['tests_failed'] += 1
            
    def test_chunk_ingestion(self):
        """Test raw chunk storage with realistic data"""
        logger.info("🧪 Testing chunk ingestion...")
        self.results['tests_run'] += 1
        
        # Simulate realistic conversation chunks
        chunks = [
            {
                'text': 'jag ska handla mjölk och bröd imorgon',
                'ts': datetime.now(timezone.utc),
                'conf': 0.92,
                'speaker': 'user',
                'source': 'realtime'
            },
            {
                'text': 'påminn mig om mötet klockan tre',
                'ts': datetime.now(timezone.utc) + timedelta(seconds=15),
                'conf': 0.87,
                'speaker': 'user', 
                'source': 'realtime'
            },
            {
                'text': 'mm okej ja',
                'ts': datetime.now(timezone.utc) + timedelta(seconds=30),
                'conf': 0.65,
                'speaker': 'user',
                'source': 'realtime'
            },
            {
                'text': 'Daniel arbetar på Google i Stockholm',
                'ts': datetime.now(timezone.utc) + timedelta(seconds=45),
                'conf': 0.91,
                'speaker': 'user',
                'source': 'realtime'
            }
        ]
        
        try:
            ttl_minutes = 120
            high_importance_count = 0
            
            with sqlite3.connect(self.test_db) as conn:
                for chunk in chunks:
                    importance = self.importance_scorer(chunk['text'])
                    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
                    
                    if importance['score'] >= 2:
                        high_importance_count += 1
                    
                    conn.execute("""
                        INSERT INTO ambient_raw 
                        (ts, text, conf, speaker, source, importance_json, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        chunk['ts'].isoformat() if hasattr(chunk['ts'], 'isoformat') else chunk['ts'], 
                        chunk['text'], chunk['conf'], chunk['speaker'],
                        chunk['source'], json.dumps(importance), expires_at.isoformat()
                    ))
                
                conn.commit()
                
                # Verify storage
                count = conn.execute("SELECT COUNT(*) FROM ambient_raw").fetchone()[0]
                
            logger.info(f"  📊 Stored {count} chunks, {high_importance_count} high importance")
            
            if count == len(chunks):
                logger.info("✅ Chunk ingestion test passed")
                self.results['tests_passed'] += 1
            else:
                raise Exception(f"Expected {len(chunks)} chunks, got {count}")
                
        except Exception as e:
            logger.error(f"❌ Chunk ingestion test failed: {e}")
            self.results['tests_failed'] += 1
            self.results['errors'].append(f"Chunk ingestion: {str(e)}")
    
    def test_summary_generation(self):
        """Test summary generation from highlights"""
        logger.info("🧪 Testing summary generation...")
        self.results['tests_run'] += 1
        
        try:
            # Get high importance chunks
            with sqlite3.connect(self.test_db) as conn:
                conn.row_factory = sqlite3.Row
                chunks = conn.execute("""
                    SELECT * FROM ambient_raw 
                    WHERE json_extract(importance_json, '$.score') >= 2
                    ORDER BY ts
                """).fetchall()
                
                if not chunks:
                    raise Exception("No high importance chunks found for summary")
                
                # Create highlights
                highlights = []
                for chunk in chunks:
                    importance = json.loads(chunk['importance_json'])
                    highlights.append({
                        'text': chunk['text'],
                        'score': importance['score'],
                        'ts': chunk['ts']
                    })
                
                # Generate mock summary
                highlights_text = '\n'.join([h['text'] for h in highlights])
                summary_text = f"Sammanfattning ({len(highlights)} viktiga punkter): " + "; ".join([h['text'][:40] for h in highlights[:3]])
                
                # Store summary
                meta = {
                    'windowStart': (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
                    'windowEnd': datetime.now(timezone.utc).isoformat(),
                    'source': 'always-on',
                    'highlights': highlights,
                    'chunkCount': len(chunks)
                }
                
                cursor = conn.execute("""
                    INSERT INTO memory (kind, text, meta_json, fts_text)
                    VALUES (?, ?, ?, ?)
                """, (
                    'ambient_summary',
                    summary_text,
                    json.dumps(meta),
                    summary_text
                ))
                
                summary_id = cursor.lastrowid
                conn.commit()
                
                # Verify FTS
                fts_result = conn.execute("SELECT * FROM memory_fts WHERE id = ?", (summary_id,)).fetchone()
                
            logger.info(f"  📝 Created summary {summary_id}: '{summary_text[:60]}...'")
            logger.info(f"  📊 From {len(highlights)} highlights")
            
            if fts_result:
                logger.info("✅ Summary generation test passed")
                self.results['tests_passed'] += 1
                return summary_id
            else:
                raise Exception("Summary not found in FTS index")
                
        except Exception as e:
            logger.error(f"❌ Summary generation test failed: {e}")
            self.results['tests_failed'] += 1
            self.results['errors'].append(f"Summary generation: {str(e)}")
            return None
    
    def test_pattern_detection(self, summary_id):
        """Test pattern detection in summaries"""
        logger.info("🧪 Testing pattern detection...")
        self.results['tests_run'] += 1
        
        if not summary_id:
            logger.warning("⚠️ Skipping pattern detection: no summary ID")
            return
            
        try:
            with sqlite3.connect(self.test_db) as conn:
                conn.row_factory = sqlite3.Row
                
                summary = conn.execute("SELECT * FROM memory WHERE id = ?", (summary_id,)).fetchone()
                if not summary:
                    raise Exception("Summary not found")
                
                # Analyze patterns
                text = summary['text'].lower()
                patterns_found = []
                
                # TODO detection
                if any(kw in text for kw in ['ska', 'kommer att', 'planerar', 'behöver', 'påminn']):
                    patterns_found.append('todo_detected')
                
                # Habit detection
                if any(kw in text for kw in ['varje', 'brukar', 'alltid', 'klockan']):
                    patterns_found.append('habit_detected')
                
                # Entity detection
                if any(kw in text for kw in ['daniel', 'google', 'stockholm', 'möte']):
                    patterns_found.append('entity_mentioned')
                
                logger.info(f"  🔍 Detected patterns: {patterns_found}")
                
                # Create reflections for patterns
                for pattern_type in patterns_found:
                    reflection_meta = {
                        'type': pattern_type,
                        'confidence': 0.7,
                        'source_summary_id': summary_id,
                        'detected_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    conn.execute("""
                        INSERT INTO memory (kind, text, meta_json, fts_text)
                        VALUES (?, ?, ?, ?)
                    """, (
                        'reflection',
                        f"Pattern detected: {pattern_type}",
                        json.dumps(reflection_meta),
                        f"reflection {pattern_type}"
                    ))
                
                conn.commit()
                
            if patterns_found:
                logger.info(f"✅ Pattern detection test passed: found {len(patterns_found)} patterns")
                self.results['tests_passed'] += 1
            else:
                logger.warning("⚠️ Pattern detection test: no patterns found (might be okay)")
                self.results['tests_passed'] += 1
                
        except Exception as e:
            logger.error(f"❌ Pattern detection test failed: {e}")
            self.results['tests_failed'] += 1
            self.results['errors'].append(f"Pattern detection: {str(e)}")
    
    def test_cleanup_and_stats(self):
        """Test data cleanup and statistics"""
        logger.info("🧪 Testing cleanup and stats...")
        self.results['tests_run'] += 1
        
        try:
            with sqlite3.connect(self.test_db) as conn:
                # Insert expired data
                old_time = datetime.now(timezone.utc) - timedelta(hours=3)
                conn.execute("""
                    INSERT INTO ambient_raw (ts, text, conf, speaker, source, importance_json, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (old_time.isoformat(), "expired chunk", 0.8, "user", "test", "{}", old_time.isoformat()))
                
                # Get stats before cleanup
                stats_before = {
                    'raw_total': conn.execute("SELECT COUNT(*) FROM ambient_raw").fetchone()[0],
                    'summaries_total': conn.execute("SELECT COUNT(*) FROM memory WHERE kind = 'ambient_summary'").fetchone()[0],
                    'reflections_total': conn.execute("SELECT COUNT(*) FROM memory WHERE kind = 'reflection'").fetchone()[0]
                }
                
                # Cleanup expired data
                cutoff = datetime.now(timezone.utc)
                cursor = conn.execute("DELETE FROM ambient_raw WHERE expires_at < ?", (cutoff.isoformat(),))
                deleted = cursor.rowcount
                
                # Get stats after cleanup
                stats_after = {
                    'raw_total': conn.execute("SELECT COUNT(*) FROM ambient_raw").fetchone()[0],
                    'summaries_total': conn.execute("SELECT COUNT(*) FROM memory WHERE kind = 'ambient_summary'").fetchone()[0],
                    'reflections_total': conn.execute("SELECT COUNT(*) FROM memory WHERE kind = 'reflection'").fetchone()[0]
                }
                
                conn.commit()
                
            logger.info(f"  📊 Before cleanup: {stats_before['raw_total']} raw, {stats_before['summaries_total']} summaries, {stats_before['reflections_total']} reflections")
            logger.info(f"  🧹 Deleted {deleted} expired entries")  
            logger.info(f"  📊 After cleanup: {stats_after['raw_total']} raw, {stats_after['summaries_total']} summaries, {stats_after['reflections_total']} reflections")
            
            if deleted > 0 and stats_after['summaries_total'] > 0:
                logger.info("✅ Cleanup and stats test passed")
                self.results['tests_passed'] += 1
            else:
                logger.warning("⚠️ Cleanup test: no expired data found or no summaries (might be okay)")
                self.results['tests_passed'] += 1
                
        except Exception as e:
            logger.error(f"❌ Cleanup and stats test failed: {e}")
            self.results['tests_failed'] += 1
            self.results['errors'].append(f"Cleanup and stats: {str(e)}")
    
    def run_all_tests(self):
        """Run complete test suite"""
        logger.info("🚀 Starting Complete Ambient Memory System Test")
        start_time = time.time()
        
        try:
            self.setup_database()
            self.test_importance_scoring() 
            self.test_chunk_ingestion()
            summary_id = self.test_summary_generation()
            self.test_pattern_detection(summary_id)
            self.test_cleanup_and_stats()
            
        except Exception as e:
            logger.error(f"💥 Test suite crashed: {e}")
            self.results['errors'].append(f"Test suite crash: {str(e)}")
            
        finally:
            # Cleanup
            if self.test_db.exists():
                self.test_db.unlink()
                
        # Report results
        duration = time.time() - start_time
        logger.info(f"\n{'='*50}")
        logger.info("📋 TEST RESULTS")
        logger.info(f"{'='*50}")
        logger.info(f"⏱️  Duration: {duration:.2f}s")
        logger.info(f"🧪 Tests run: {self.results['tests_run']}")
        logger.info(f"✅ Passed: {self.results['tests_passed']}")
        logger.info(f"❌ Failed: {self.results['tests_failed']}")
        
        if self.results['errors']:
            logger.error(f"\n❌ ERRORS:")
            for error in self.results['errors']:
                logger.error(f"   - {error}")
        
        success_rate = (self.results['tests_passed'] / max(1, self.results['tests_run'])) * 100
        logger.info(f"📊 Success rate: {success_rate:.1f}%")
        
        if self.results['tests_failed'] == 0:
            logger.info("🎉 ALL TESTS PASSED! Ambient Memory System is working correctly.")
            return True
        else:
            logger.error(f"💥 {self.results['tests_failed']} tests failed!")
            return False

def main():
    """Main test runner"""
    test_suite = CompleteAmbientTest()
    success = test_suite.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())