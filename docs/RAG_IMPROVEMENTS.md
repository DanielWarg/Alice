# RAG Memory System - Förbättringar

Alice's RAG (Retrieval-Augmented Generation) memory system har förbättrats avsevärt med avancerade funktioner för bättre kontextförståelse och minneshämtning.

## 🚀 Nya Funktioner

### 1. Avancerad Hybrid Scoring
**Före:** Enkel BM25 + recency scoring
**Nu:** Multi-faktor scoring med:
- **BM25 relevance**: Full-text search relevance
- **Förbättrad recency**: Tiered decay (1h, 24h, 1v, 2m)  
- **Text quality**: Optimal längd (50-500 chars)
- **Query coverage**: Andel query-ord som matchar
- **Context bonus**: Bonuspoäng för relaterade konversationer
- **Explicit scoring**: Användar/system-tilldelade poäng

### 2. Semantisk Text Chunking
**Problem:** Långa texter blev svåra att indexera och hämta effektivt
**Lösning:** Smart chunking som respekterar:
- **Paragraph boundaries** (dubbelradbrytningar först)
- **Sentence boundaries** (punkt, utropstecken, frågetecken)
- **Metadata tracking** (chunk_index, total_chunks, original_length)
- **Max chunk size**: 500 tecken (konfigurerbart)

### 3. Conversation Context Tracking
**Nyhet:** Fullständig session-baserad kontexthantering
- **Session ID**: Genereras baserat på modell + timme
- **Turn tracking**: Alla user/assistant meddelanden sparas
- **Context-enhanced retrieval**: Hämtar memories relaterade till pågående konversation
- **Automatic cleanup**: Gamla konversationer rensas efter 30 dagar

### 4. Förbättrad Retrieval Pipeline
```
User Query → Session Context → Enhanced Query → Multi-factor Scoring → Top Results
```
1. Hämta recent conversation turns
2. Extrahera keywords från context
3. Förbättra query med context keywords
4. Applicera advanced scoring algorithm
5. Returnera top results med context bonus

## 📊 Tekniska Förbättringar

### Database Schema Updates
```sql
-- Ny tabell för conversation tracking
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    ts TEXT NOT NULL,
    role TEXT NOT NULL,      -- 'user' | 'assistant'
    content TEXT NOT NULL,
    memory_id INTEGER
);

-- Index för snabba queries
CREATE INDEX idx_conversations_session ON conversations(session_id, ts);
```

### API Ändringar
- `upsert_text_memory()` returnerar nu `List[int]` för chunked entries
- `upsert_text_memory_single()` backward compatible version
- Nya metoder: `get_conversation_context()`, `get_related_memories_from_context()`
- Auto-chunking kan disabled med `auto_chunk=False`

### Performance Optimizations
- **Ökad candidate pool**: 50→100 resultat före scoring
- **Effektiv context lookup**: Session-baserad indexering
- **Smart query enhancement**: Max 5 context keywords
- **Optimized weights**: Balanserad viktning mellan faktorer

## 🎯 Praktiska Fördelar

### Bättre Kontextförståelse
```
User: "Vad sa vi om Gmail integration?"
→ Alice hämtar memories från aktuell konversation +
  relaterade Gmail-diskussioner från tidigare
```

### Smartare Long-form Content
```
Lång text (>500 chars) → Automatisk semantic chunking
→ Varje chunk indexeras separat
→ Bättre retrieval av specifika delar
```

### Förbättrad Relevance
```
Query: "hur startar jag servern"
Previous: Matching "servern" anywhere
Now: BM25 + recent usage + conversation context + text quality
```

## 🔧 Konfiguration

### Environment Variables
```bash
# Existing settings continue to work
ENABLED_TOOLS=PLAY,PAUSE,SEND_EMAIL,READ_EMAILS,SEARCH_EMAILS
```

### Memory Settings
```python
# Auto-chunking för långa texter
memory.upsert_text_memory(long_text, auto_chunk=True)

# Context-aware retrieval  
contexts = memory.get_related_memories_from_context(session_id, query)

# Cleanup gamla konversationer
cleaned = memory.cleanup_old_conversations(days=30)
```

## 📈 Resultat

**Innan RAG-förbättringar:**
- Basic BM25 ranking
- Ingen chunking av långa texter
- Ingen conversation context
- Simpel recency decay

**Efter RAG-förbättringar:**
- ✅ Multi-factor intelligent scoring
- ✅ Semantic text chunking
- ✅ Session-based context tracking
- ✅ Context-enhanced retrieval
- ✅ Optimized performance
- ✅ Backward compatibility maintained

Alice kan nu:
🧠 **Förstå konversationskontext** bättre  
📚 **Hantera långa dokument** effektivt  
🎯 **Hitta relevanta memories** mer precist  
⚡ **Leverera snabbare svar** med bättre context