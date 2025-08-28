#!/usr/bin/env python3
"""
Stresstest för Alice RAG/Context system
Testar prestanda under belastning och verifierar funktionalitet
"""

import asyncio
import time
import json
import random
import statistics
from concurrent.futures import ThreadPoolExecutor
from memory import MemoryStore
import os

# Testdata
SAMPLE_TEXTS = [
    "Alice är en avancerad AI-assistent som kan hantera komplexa uppgifter som e-post, musikuppspelning och planering.",
    "Gmail-integrationen gör det möjligt att skicka, läsa och söka e-post direkt genom naturligt språk.",
    "RAG-systemet använder hybrid retrieval med BM25, recency scoring och kontextuell bonus för optimal relevance.",
    "Conversation context tracking sparar alla turns och förbättrar minneshämtning baserat på pågående diskussion.",
    "Semantic chunking delar upp långa texter i meningsfulla segment som respekterar paragraph och sentence boundaries.",
    "Local LLM integration med gpt-oss:20B via Ollama möjliggör privat och snabb AI-inferens utan externa API-anrop.",
    "Tool system architecture följer single source of truth princip med centraliserade tool specs och executors.",
    "Pydantic models validerar alla tool arguments och säkerställer type safety genom hela systemet.",
    "Svenska språkstöd är inbyggt i alla komponenter från NLU till response generation och memory storage.",
    "Session-baserad context tracking grupperar konversationer per timme och modell för optimal minneshantering."
] * 10  # 100 texter

QUERIES = [
    "gmail e-post",
    "musik spela",
    "RAG retrieval",
    "context tracking", 
    "semantic chunking",
    "local LLM",
    "tool system",
    "svenska språk",
    "AI assistent",
    "memory storage"
] * 5  # 50 queries

LONG_TEXTS = [
    """Detta är en mycket lång text som testar semantic chunking funktionaliteten i Alice memory system. 

    Första avsnittet handlar om hur RAG (Retrieval-Augmented Generation) fungerar med hybrid retrieval som kombinerar BM25 full-text search med recency scoring och kontextuell bonus. Detta ger mycket mer relevanta resultat än traditionella sökmetoder.

    Andra avsnittet fokuserar på conversation context tracking som sparar alla user och assistant turns i sessioner baserade på modell och tid. Detta möjliggör att Alice kan förstå vad som diskuterats tidigare i konversationen.

    Tredje avsnittet beskriver semantic chunking som intelligent delar upp långa texter i mindre segment som respekterar paragraph och sentence boundaries istället för att bara dela på teckenantal.

    Fjärde och sista avsnittet täcker tekniska implementationsdetaljer som SQLite databas med WAL mode, FTS5 full-text indexering och optimerade SQL queries för snabb retrieval av relevanta memories.""",
    
    """Alice AI-assistenten har utvecklats med flera avancerade komponenter för att leverera en robust och intelligent användarupplevelse.

    Gmail Integration bygger på Google API och tillåter användare att skicka e-post via naturligt språk som "skicka mail till chef om projektuppdatering". Systemet hanterar OAuth autentisering säkert och sparar credentials lokalt.

    Tool Architecture följer en centraliserad approach där tool_specs.py är single source of truth för alla verktyg. Pydantic models validerar arguments och tool_registry.py hanterar execution med lambda functions.

    Memory System använder SQLite med flera tabeller: memories för textdata, conversations för context tracking, embeddings för semantic search och events för audit trail. FTS5 möjliggör snabb full-text search.

    Local LLM Support via Ollama kör gpt-oss:20B modellen lokalt för privat inferens utan externa API-anrop. Detta säkerställer både prestanda och integritet för känslig data."""
] * 5  # 10 långa texter

class RAGStressTest:
    def __init__(self):
        self.db_path = "./stress_test_alice.db"
        self.memory = MemoryStore(self.db_path)
        self.results = {
            'insert_times': [],
            'retrieval_times': [],
            'context_times': [],
            'chunking_times': [],
            'errors': []
        }
    
    def cleanup(self):
        """Rensa testdatabasen"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def setup_test_data(self):
        """Förbereda testdata"""
        print("🔄 Skapar testdata...")
        
        # Lägg till normala texter
        start_time = time.time()
        for i, text in enumerate(SAMPLE_TEXTS):
            try:
                t0 = time.time()
                tags = json.dumps({"test": True, "batch": i // 10}, ensure_ascii=False)
                self.memory.upsert_text_memory_single(text, score=random.uniform(0, 5), tags_json=tags)
                self.results['insert_times'].append(time.time() - t0)
            except Exception as e:
                self.results['errors'].append(f"Insert error: {e}")
        
        # Lägg till långa texter (chunked)
        for i, long_text in enumerate(LONG_TEXTS):
            try:
                t0 = time.time()
                tags = json.dumps({"test": True, "long_text": True, "index": i}, ensure_ascii=False)
                memory_ids = self.memory.upsert_text_memory(long_text, score=3.0, tags_json=tags)
                chunk_time = time.time() - t0
                self.results['chunking_times'].append(chunk_time)
                print(f"📝 Lång text {i+1}: {len(memory_ids)} chunks på {chunk_time:.3f}s")
            except Exception as e:
                self.results['errors'].append(f"Chunking error: {e}")
        
        setup_time = time.time() - start_time
        print(f"✅ {len(SAMPLE_TEXTS)} texter + {len(LONG_TEXTS)} långa texter skapade på {setup_time:.2f}s")
    
    def test_retrieval_performance(self):
        """Test retrieval under belastning"""
        print("\n🔍 Testar retrieval prestanda...")
        
        for query in QUERIES:
            try:
                # Test standard retrieval
                t0 = time.time()
                results = self.memory.retrieve_text_bm25_recency(query, limit=10)
                retrieval_time = time.time() - t0
                self.results['retrieval_times'].append(retrieval_time)
                
                if retrieval_time > 0.1:  # Warn if over 100ms
                    print(f"⚠️  Slow query '{query}': {retrieval_time:.3f}s")
                    
            except Exception as e:
                self.results['errors'].append(f"Retrieval error for '{query}': {e}")
    
    def test_conversation_context(self):
        """Test conversation context under belastning"""
        print("\n💬 Testar conversation context...")
        
        # Skapa flera sessions
        sessions = [f"test_session_{i}" for i in range(10)]
        
        for session_id in sessions:
            try:
                # Lägg till conversation turns
                t0 = time.time()
                for i in range(20):  # 20 turns per session
                    user_msg = f"User message {i} in {session_id}"
                    self.memory.add_conversation_turn(session_id, "user", user_msg)
                    
                    assistant_msg = f"Assistant response {i} in {session_id}"  
                    self.memory.add_conversation_turn(session_id, "assistant", assistant_msg)
                
                # Test context retrieval
                context = self.memory.get_conversation_context(session_id, limit=10)
                
                # Test context-aware memory retrieval
                for query in QUERIES[:3]:  # Test med några queries
                    memories = self.memory.get_related_memories_from_context(session_id, query, limit=5)
                
                context_time = time.time() - t0
                self.results['context_times'].append(context_time)
                
                print(f"📊 Session {session_id}: {len(context)} turns, {context_time:.3f}s")
                
            except Exception as e:
                self.results['errors'].append(f"Context error for {session_id}: {e}")
    
    def concurrent_stress_test(self):
        """Concurrent access test"""
        print("\n⚡ Testar concurrent access...")
        
        def worker_task(worker_id):
            results = {'times': [], 'errors': []}
            try:
                for i in range(10):
                    t0 = time.time()
                    
                    # Random operation
                    operation = random.choice(['insert', 'retrieve', 'context'])
                    
                    if operation == 'insert':
                        text = f"Concurrent worker {worker_id} message {i}"
                        self.memory.upsert_text_memory_single(text, score=random.uniform(0,3))
                        
                    elif operation == 'retrieve':
                        query = random.choice(QUERIES)
                        memories = self.memory.retrieve_text_bm25_recency(query, limit=5)
                        
                    elif operation == 'context':
                        session = f"concurrent_session_{worker_id}"
                        self.memory.add_conversation_turn(session, "user", f"Message {i}")
                        context = self.memory.get_conversation_context(session, limit=5)
                    
                    results['times'].append(time.time() - t0)
                    
            except Exception as e:
                results['errors'].append(f"Worker {worker_id}: {e}")
            
            return results
        
        # Kör concurrent workers
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_task, i) for i in range(5)]
            worker_results = [f.result() for f in futures]
        
        total_time = time.time() - start_time
        
        # Samla resultat
        all_times = []
        all_errors = []
        for result in worker_results:
            all_times.extend(result['times'])
            all_errors.extend(result['errors'])
        
        self.results['errors'].extend(all_errors)
        
        print(f"🔄 5 workers, {len(all_times)} operations på {total_time:.2f}s")
        if all_times:
            print(f"📊 Genomsnitt: {statistics.mean(all_times):.3f}s, Max: {max(all_times):.3f}s")
    
    def performance_analysis(self):
        """Analysera prestanda resultat"""
        print("\n📊 PRESTANDA ANALYS")
        print("=" * 50)
        
        # Insert performance
        if self.results['insert_times']:
            insert_avg = statistics.mean(self.results['insert_times'])
            insert_max = max(self.results['insert_times'])
            print(f"🔸 Insert: Genomsnitt {insert_avg*1000:.1f}ms, Max {insert_max*1000:.1f}ms")
        
        # Retrieval performance  
        if self.results['retrieval_times']:
            retrieval_avg = statistics.mean(self.results['retrieval_times'])
            retrieval_max = max(self.results['retrieval_times'])
            print(f"🔍 Retrieval: Genomsnitt {retrieval_avg*1000:.1f}ms, Max {retrieval_max*1000:.1f}ms")
        
        # Context performance
        if self.results['context_times']:
            context_avg = statistics.mean(self.results['context_times'])
            context_max = max(self.results['context_times'])  
            print(f"💬 Context: Genomsnitt {context_avg*1000:.1f}ms, Max {context_max*1000:.1f}ms")
        
        # Chunking performance
        if self.results['chunking_times']:
            chunk_avg = statistics.mean(self.results['chunking_times'])
            chunk_max = max(self.results['chunking_times'])
            print(f"📝 Chunking: Genomsnitt {chunk_avg*1000:.1f}ms, Max {chunk_max*1000:.1f}ms")
        
        # Errors
        if self.results['errors']:
            print(f"\n❌ FEL: {len(self.results['errors'])} fel upptäckta:")
            for error in self.results['errors'][:5]:  # Visa första 5
                print(f"   - {error}")
            if len(self.results['errors']) > 5:
                print(f"   ... och {len(self.results['errors'])-5} till")
        else:
            print("\n✅ Inga fel upptäckta!")
        
        # Database stats
        try:
            with self.memory._conn() as c:
                memories_count = c.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                conversations_count = c.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
                print(f"\n📊 Databas: {memories_count} memories, {conversations_count} conversation turns")
        except Exception as e:
            print(f"\n❌ Kunde inte hämta databas stats: {e}")
    
    def run_all_tests(self):
        """Kör alla stresstests"""
        print("🚀 ALICE RAG/CONTEXT STRESSTEST STARTAR")
        print("=" * 50)
        
        start_time = time.time()
        
        try:
            self.setup_test_data()
            self.test_retrieval_performance()
            self.test_conversation_context()
            self.concurrent_stress_test()
            
            total_time = time.time() - start_time
            print(f"\n⏱️  Total testtid: {total_time:.2f}s")
            
            self.performance_analysis()
            
        finally:
            self.cleanup()
            print(f"\n🧹 Testdatabas rensad")

if __name__ == "__main__":
    test = RAGStressTest()
    test.run_all_tests()