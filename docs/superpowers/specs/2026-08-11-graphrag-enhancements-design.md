# Spec: GraphRAG Query Engine Enhancements

**Date:** 2026-08-11  
**Status:** Approved for implementation  
**Scope:** Activate real GraphRAG query engine, vector search, conversation memory, real SSE streaming

## Problem Statement

The current GraphRAG query path is a keyword-template engine:
- LanceDB embeddings exist (2048-dim, `llama-nemotron-embed-vl-1b-v2`) but are never queried
- Parquet artifacts (entities, relationships, communities, text_units) are unused at query time
- "Local" vs "global" modes are just prompt personas over identical keyword retrieval
- No vector similarity search, no graph traversal, no hybrid search
- Dead code: `_run_graphrag_query_uncached` and `search_static_graph` never invoked
- Context assembly is query-blind (always first 8 resume sections)
- Fake streaming: SSE emits entire response as one token event
- No conversation memory (configured but stateless)

## Solution

Replace keyword-template engine with direct GraphRAG Python API integration. Three query modes (local, global, DRIFT), vector similarity search via LanceDB, graph traversal of parquet artifacts, conversation memory via SQLite, and real token-by-token SSE streaming.

## Architecture

```
User query → /api/query (POST {query, mode, session_id})
  ├─ Load conversation history from SQLite (if session_id provided)
  ├─ GraphRAGEngine.query(query, mode, history)
  │   ├─ Vector search (LanceDB) → top-k relevant text_units/communities
  │   ├─ Graph traversal (parquet entities/relationships) → expand context
  │   ├─ Build system prompt + context window
  │   └─ Stream LLM response token-by-token → yield SSE events
  ├─ Save user message + assistant response to SQLite
  └─ Return StreamingResponse
```

## Components

### 1. GraphRAGEngine (`src/query/graphrag_engine.py` — new file)

```python
from graphrag.query.context_builder import build_context
from graphrag.query.structured_search.local_search import LocalSearch
from graphrag.query.structured_search.global_search import GlobalSearch
from graphrag.query.structured_search.drift_search import DRIFTSearch
import lancedb

class GraphRAGEngine:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.db = lancedb.connect(self.root_dir / "output" / "lancedb")
        
        # Load parquet artifacts
        self.entities = pd.read_parquet(self.root_dir / "output" / "entities.parquet")
        self.relationships = pd.read_parquet(self.root_dir / "output" / "relationships.parquet")
        self.communities = pd.read_parquet(self.root_dir / "output" / "community_reports.parquet")
        self.text_units = pd.read_parquet(self.root_dir / "output" / "text_units.parquet")
        
        # Load LLM client (from serverless_gateway)
        self.llm = get_serverless_llm_client()
    
    async def query(
        self, 
        query: str, 
        mode: str, 
        conversation_history: list = None
    ) -> AsyncGenerator[str, None]:
        """
        Execute GraphRAG query and stream response.
        
        Args:
            query: User question
            mode: "local" | "global" | "drift"
            conversation_history: Previous messages for context
        
        Yields:
            SSE-formatted tokens: {"token": "...", "done": false}
        """
        # 1. Retrieve relevant context based on mode
        context = await self._retrieve_context(query, mode)
        
        # 2. Build system prompt with context
        system_prompt = self._build_system_prompt(mode, context, conversation_history)
        
        # 3. Stream LLM response
        async for token in self._stream_llm_response(system_prompt, query):
            yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
        
        # 4. Final event with sources
        sources = self._extract_sources(context)
        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"
    
    async def _retrieve_context(self, query: str, mode: str) -> dict:
        """Retrieve relevant context based on query mode."""
        if mode == "local":
            return await self._local_retrieval(query)
        elif mode == "global":
            return await self._global_retrieval(query)
        elif mode == "drift":
            return await self._drift_retrieval(query)
        else:
            raise ValueError(f"Unknown mode: {mode}")
    
    async def _local_retrieval(self, query: str) -> dict:
        """
        Local mode: entity-focused retrieval.
        1. Vector search on text_unit-text table (top-k=10)
        2. Fetch associated entities/relationships from parquet
        3. Build context window
        """
        # Vector similarity search
        text_unit_table = self.db.open_table("default-text_unit-text")
        query_embedding = await self._get_embedding(query)
        results = text_unit_table.search(query_embedding).limit(10).to_list()
        
        # Extract text_unit IDs
        text_unit_ids = [r["id"] for r in results]
        
        # Fetch entities mentioned in these text_units
        relevant_entities = self.entities[
            self.entities["text_unit_ids"].apply(
                lambda x: any(tid in x for tid in text_unit_ids)
            )
        ].head(20)
        
        # Fetch relationships between these entities
        entity_ids = relevant_entities["id"].tolist()
        relevant_relationships = self.relationships[
            (self.relationships["source"].isin(entity_ids)) |
            (self.relationships["target"].isin(entity_ids))
        ].head(30)
        
        return {
            "text_units": results,
            "entities": relevant_entities.to_dict("records"),
            "relationships": relevant_relationships.to_dict("records"),
        }
    
    async def _global_retrieval(self, query: str) -> dict:
        """
        Global mode: community summary retrieval.
        1. Vector search on community-full_content table (top-k=5)
        2. Aggregate community reports
        3. Build executive summary context
        """
        community_table = self.db.open_table("default-community-full_content")
        query_embedding = await self._get_embedding(query)
        results = community_table.search(query_embedding).limit(5).to_list()
        
        return {
            "communities": results,
        }
    
    async def _drift_retrieval(self, query: str) -> dict:
        """
        DRIFT mode: multi-hop reasoning.
        1. Start with vector search (like local)
        2. Traverse relationship graph to find connected entities
        3. Iteratively expand context
        """
        # Initial retrieval (same as local)
        initial_context = await self._local_retrieval(query)
        
        # Extract seed entities
        seed_entities = initial_context["entities"][:5]
        
        # Traverse relationships to find connected entities
        expanded_entities = []
        for entity in seed_entities:
            connected = self.relationships[
                (self.relationships["source"] == entity["id"]) |
                (self.relationships["target"] == entity["id"])
            ]
            # Get entities on the other end of relationships
            for _, rel in connected.head(3).iterrows():
                other_id = rel["target"] if rel["source"] == entity["id"] else rel["source"]
                other_entity = self.entities[self.entities["id"] == other_id]
                if not other_entity.empty:
                    expanded_entities.append(other_entity.iloc[0].to_dict())
        
        # Deduplicate
        seen_ids = {e["id"] for e in seed_entities}
        unique_expanded = [e for e in expanded_entities if e["id"] not in seen_ids]
        
        return {
            "text_units": initial_context["text_units"],
            "entities": seed_entities + unique_expanded[:10],
            "relationships": initial_context["relationships"],
        }
    
    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding vector for text."""
        # Use serverless_gateway or LiteLLM proxy
        from src.query.serverless_gateway import get_embedding
        return await get_embedding(text)
    
    def _build_system_prompt(
        self, 
        mode: str, 
        context: dict, 
        conversation_history: list = None
    ) -> str:
        """Build system prompt with retrieved context."""
        base_prompt = {
            "local": "You are a helpful assistant answering questions about Prasad Rane's professional experience. Use the provided entity and relationship data to give specific, detailed answers.",
            "global": "You are a helpful assistant providing executive-level summaries of Prasad Rane's career. Use the provided community reports to give high-level insights.",
            "drift": "You are a helpful assistant performing multi-hop reasoning about Prasad Rane's experience. Connect information across entities and relationships to provide comprehensive answers.",
        }[mode]
        
        # Format context
        context_str = self._format_context(context)
        
        # Add conversation history
        history_str = ""
        if conversation_history:
            history_str = "\n\nPrevious conversation:\n" + "\n".join(
                f"{msg['role']}: {msg['content']}" for msg in conversation_history[-6:]
            )
        
        return f"{base_prompt}\n\nContext:\n{context_str}{history_str}"
    
    def _format_context(self, context: dict) -> str:
        """Format retrieved context into readable string."""
        parts = []
        
        if "text_units" in context:
            parts.append("## Relevant Text Segments")
            for tu in context["text_units"][:5]:
                parts.append(f"- {tu.get('text', '')[:500]}")
        
        if "entities" in context:
            parts.append("\n## Key Entities")
            for ent in context["entities"][:10]:
                parts.append(f"- {ent.get('name', '')}: {ent.get('description', '')[:200]}")
        
        if "relationships" in context:
            parts.append("\n## Relationships")
            for rel in context["relationships"][:10]:
                parts.append(f"- {rel.get('source', '')} → {rel.get('target', '')}: {rel.get('description', '')[:150]}")
        
        if "communities" in context:
            parts.append("\n## Community Reports")
            for comm in context["communities"][:5]:
                parts.append(f"- {comm.get('full_content', '')[:500]}")
        
        return "\n".join(parts)
    
    async def _stream_llm_response(
        self, 
        system_prompt: str, 
        user_query: str
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response token-by-token."""
        from src.query.serverless_gateway import call_serverless_llm_stream
        
        async for token in call_serverless_llm_stream(
            system_prompt=system_prompt,
            user_message=user_query,
            temperature=0.3,
        ):
            yield token
    
    def _extract_sources(self, context: dict) -> list[dict]:
        """Extract source references from context."""
        sources = []
        
        if "entities" in context:
            for ent in context["entities"][:5]:
                sources.append({
                    "type": "entity",
                    "name": ent.get("name", ""),
                    "description": ent.get("description", "")[:100],
                })
        
        if "communities" in context:
            for comm in context["communities"][:3]:
                sources.append({
                    "type": "community",
                    "title": comm.get("title", ""),
                    "summary": comm.get("full_content", "")[:150],
                })
        
        return sources
```

### 2. Conversation Memory (`src/query/conversation_store.py` — new file)

```python
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
from functools import lru_cache

class ConversationStore:
    def __init__(self, db_path: str = "output/conversations.db"):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_or_create_conversation(self, session_id: str) -> int:
        """Get conversation ID for session, create if not exists."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM conversations WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        
        if row:
            conversation_id = row[0]
        else:
            cursor.execute(
                "INSERT INTO conversations (session_id) VALUES (?)",
                (session_id,)
            )
            conversation_id = cursor.lastrowid
            conn.commit()
        
        conn.close()
        return conversation_id
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add message to conversation."""
        conversation_id = self.get_or_create_conversation(session_id)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content)
        )
        
        conn.commit()
        conn.close()
    
    def get_history(self, session_id: str, limit: int = 10) -> list[dict]:
        """Get conversation history for session."""
        conversation_id = self.get_or_create_conversation(session_id)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT role, content, timestamp 
            FROM messages 
            WHERE conversation_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (conversation_id, limit)
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        # Reverse to chronological order
        return [
            {"role": row[0], "content": row[1], "timestamp": row[2]}
            for row in reversed(rows)
        ]

# Global instance
_store: Optional[ConversationStore] = None

def get_conversation_store() -> ConversationStore:
    """Get global conversation store instance."""
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store
```

### 3. Streaming LLM (`src/query/serverless_gateway.py` — extend existing)

Add streaming support:

```python
async def call_serverless_llm_stream(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.3,
    timeout: int = 30,
) -> AsyncGenerator[str, None]:
    """
    Stream LLM response token-by-token.
    
    Yields:
        str: Individual tokens
    """
    # Try OpenRouter first
    try:
        async for token in _stream_openrouter(
            system_prompt, user_message, temperature, timeout
        ):
            yield token
        return
    except Exception as e:
        logger.warning(f"OpenRouter streaming failed: {e}. Falling back to Gemini...")
    
    # Fallback to Gemini
    try:
        async for token in _stream_gemini(
            system_prompt, user_message, temperature, timeout
        ):
            yield token
        return
    except Exception as e:
        logger.error(f"Gemini streaming failed: {e}")
        raise

async def _stream_openrouter(
    system_prompt: str,
    user_message: str,
    temperature: float,
    timeout: int,
) -> AsyncGenerator[str, None]:
    """Stream from OpenRouter API."""
    import aiohttp
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": "nvidia/nemotron-3-super-120b-a12b:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "stream": True,
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, headers=headers, json=payload, timeout=timeout
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"OpenRouter returned {response.status}")
            
            async for line in response.content:
                if line.startswith(b"data: "):
                    data = line[6:].decode("utf-8").strip()
                    if data == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

async def _stream_gemini(
    system_prompt: str,
    user_message: str,
    temperature: float,
    timeout: int,
) -> AsyncGenerator[str, None]:
    """Stream from Gemini API."""
    import aiohttp
    
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GRAPHRAG_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\n{user_message}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
        },
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, json=payload, timeout=timeout
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Gemini returned {response.status}")
            
            async for line in response.content:
                if line.startswith(b"data: "):
                    data = line[6:].decode("utf-8").strip()
                    
                    try:
                        chunk = json.loads(data)
                        candidates = chunk.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                if "text" in part:
                                    yield part["text"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
```

### 4. Updated API Route (`src/shared/api_routes.py` — modify existing)

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json

from src.query.graphrag_engine import GraphRAGEngine
from src.query.conversation_store import get_conversation_store

shared_router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    mode: str = "local"  # "local" | "global" | "drift"
    session_id: Optional[str] = None

@shared_router.post("/api/query")
async def query_knowledge_graph(request: QueryRequest):
    """
    Query the GraphRAG knowledge graph with streaming response.
    
    Returns SSE stream:
    - {"token": "...", "done": false} for each token
    - {"done": true, "sources": [...]} for final event
    """
    # Validate mode
    if request.mode not in ("local", "global", "drift"):
        raise HTTPException(status_code=400, detail=f"Invalid mode: {request.mode}")
    
    # Get conversation history
    history = []
    if request.session_id:
        store = get_conversation_store()
        history = store.get_history(request.session_id, limit=10)
        
        # Save user message
        store.add_message(request.session_id, "user", request.query)
    
    # Initialize GraphRAG engine
    engine = GraphRAGEngine(root_dir=str(ROOT_DIR))
    
    async def generate():
        full_response = []
        
        try:
            async for event in engine.query(
                query=request.query,
                mode=request.mode,
                conversation_history=history,
            ):
                # Parse event to extract token
                event_data = json.loads(event.split("data: ")[1])
                
                if "token" in event_data:
                    full_response.append(event_data["token"])
                
                yield event
                
                if event_data.get("done"):
                    # Save assistant response
                    if request.session_id:
                        store.add_message(
                            request.session_id,
                            "assistant",
                            "".join(full_response)
                        )
        except Exception as e:
            logger.error(f"Query failed: {e}")
            # Fallback to static response
            fallback = f"I encountered an error processing your query. Error: {str(e)}"
            yield f"data: {json.dumps({'token': fallback, 'done': True, 'sources': []})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
```

### 5. Cleanup Dead Code

Remove from `src/query/search_engine.py`:
- `_run_graphrag_query_uncached` function (never called)
- `search_static_graph` function (only tests use it)
- Hardcoded keyword branches in `search_static_resume`

Keep `search_static_resume` as fallback only.

## Error Handling

- If LanceDB/parquet files missing → fall back to static reader (existing logic)
- If GraphRAG query times out (>30s) → return partial results + error message
- If LLM call fails → return static context without LLM polish
- Conversation memory: if SQLite write fails, continue without persistence (log error)
- Streaming: if connection drops mid-stream, client can reconnect with session_id to resume

## Testing

### Unit Tests

- Mock LanceDB/parquet, verify retrieval logic per mode
- Test conversation store: add/get messages, session isolation
- Test streaming: verify SSE event format

### Integration Tests

- Use existing `output/` artifacts, verify end-to-end query
- Test all three modes: local, global, drift
- Verify conversation history persistence

### Performance Tests

- Local query: <3s (vector search + LLM)
- Global query: <5s (community aggregation + LLM)
- DRIFT query: <10s (multi-hop traversal + LLM)
- Streaming: first token <500ms

## Performance Targets

| Metric | Target |
|--------|--------|
| Local query latency | <3s |
| Global query latency | <5s |
| DRIFT query latency | <10s |
| First token latency (streaming) | <500ms |
| Conversation history load | <100ms |

## Migration Path

1. Create `src/query/graphrag_engine.py` with GraphRAGEngine class
2. Create `src/query/conversation_store.py` with SQLite persistence
3. Extend `src/query/serverless_gateway.py` with streaming support
4. Update `src/shared/api_routes.py` to use new engine
5. Update frontend to handle SSE streaming properly
6. Remove dead code from `src/query/search_engine.py`
7. Add tests for all new components
8. Deploy to Oracle Cloud (requires deployment spec first)

## Success Criteria

- Real GraphRAG queries work (local/global/DRIFT modes)
- Vector similarity search retrieves relevant context
- Conversation memory persists across requests
- Real SSE streaming delivers tokens incrementally
- All existing tests pass
- New tests cover retrieval, streaming, conversation
- Performance targets met

## Out of Scope

- Citation links in UI (future enhancement)
- Visual graph explorer
- Multi-modal queries (images, PDFs)
- Custom entity/relationship types
- GraphRAG indexing improvements (separate concern)

## Dependencies

- `graphrag` package (already in requirements-dev.txt)
- `lancedb` package (already in requirements-dev.txt)
- `pandas` for parquet manipulation (already installed via graphrag, but add to requirements.txt explicitly)
- `aiohttp` for async HTTP streaming (add to requirements.txt)
- SQLite3 (built into Python)

## Risks

- **Bundle size:** GraphRAG + LanceDB are large (~100MB+). Mitigation: Oracle Cloud VM has no bundle limits.
- **Cold starts:** First query may be slow (loading parquet files). Mitigation: lazy initialization, keep engine warm.
- **LLM rate limits:** OpenRouter free tier has limits. Mitigation: Gemini fallback, caching.
- **Memory usage:** Loading all parquet files into memory. Mitigation: Oracle VM has 24GB RAM, sufficient for this dataset size.
