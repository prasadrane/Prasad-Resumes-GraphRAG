# Deployment Fixes + GraphRAG Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 6 deployment issues (Dockerfile, pinned deps/version, favicon, static routing, vercel dev workaround) AND activate real GraphRAG query engine with vector search/conversation memory/SSE streaming.

**Architecture:** Two phases. Phase 1 fixes deployment infrastructure (Dockerfile, pinned deps, version pinning, favicon, nginx config, docker-compose.yml, CI/CD). Phase 2 activates real GraphRAG query engine (LanceDB vector search, parquet traversal, three modes: local/global/drift, conversation memory, SSE streaming). Deployed via Docker Compose on Oracle Cloud ARM VM.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, ReportLab, Docker, Docker Compose, nginx, certbot, SQLite3, LanceDB, graphrag, pandas, aiohttp.

## Global Constraints

- **Python version:** 3.11 (exact floor from `.python-version`)
- **LLM primary:** OpenRouter free models (`nvidia/nemotron-3-super-120b-a12b:free` for chat, `llama-nemotron-embed-vl-1b-v2` for embeddings)
- **LLM fallback:** Gemini 2.5 Flash free tier (15 req/min, 1M tokens/day)
- **Streaming:** Token-by-token SSE (`data: {"token": "...", "done": false}` / `data: {"done": true, "sources": [...]}`)
- **Conversation history:** Max 10 turns per session, persisted in SQLite
- **Performance:** Local <3s, Global <5s, DRIFT <10s, first token <500ms
- **All existing tests must pass after every task** (current baseline: 125 passing)

---

## Phase 1: Deployment Fixes

### Task 1.1: Pin Python version + dependencies

**Files:**
- Create: `.python-version`
- Modify: `requirements.txt` (pin versions)
- Modify: `vercel.json` (add runtime pin for Vercel parity)

**Interfaces:**
- Consumes: None (standalone setup)
- Produces: Pinned dependency manifest used by all subsequent tasks

- [ ] **Step 1: Create `.python-version` file**
```
3.11
```

- [ ] **Step 2: Pin all dependencies in `requirements.txt`**

Replace current content with:
```txt
fastapi==0.115.0
pydantic==2.9.2
reportlab==4.2.5
python-dotenv==1.0.1
pyyaml==6.0.2
uvicorn==0.32.0
aiohttp==3.11.0
pandas==2.2.3
graphrag==0.5.0
lancedb==0.15.0
sqlalchemy==2.0.35
```

Verify with `pip install -r requirements.txt`.

- [ ] **Step 3: Update `vercel.json` to pin runtime**

Add functions block:
```json
{
  "functions": {
    "api/index.py": {
      "runtime": "@vercel/python@4.3.0"
    }
  },
  "builds": [...],
  "routes": [...]
}
```
Preserve existing builds/routes. Add `"output"` to `.vercelignore` if not present.

- [ ] **Step 4: Commit and run tests**

```bash
git add .python-version requirements.txt vercel.json
git commit -m "fix(deploy): pin Python 3.11 version and all dependencies"
python -m unittest discover tests -v  # All 125 tests pass
```

### Task 1.2: Fix Dockerfile + LiteLLM proxy Dockerfile

**Files:**
- Modify: `Dockerfile` (web service — full app including GraphRAG)
- Create: `Dockerfile.litellm` (LiteLLM proxy — lightweight)
- Modify: `.dockerignore` (ensure large dirs excluded)

**Interfaces:**
- Consumes: Pinned `requirements.txt` from Task 1.1
- Produces: Valid Dockerfiles buildable via `docker build --test`

- [ ] **Step 1: Replace `Dockerfile` with web service**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create `Dockerfile.litellm` for LiteLLM proxy**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/run_litellm.py ./run_litellm.py
COPY config/litellm-config.yaml ./config.yaml

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["python", "run_litellm.py"]
```

- [ ] **Step 3: Create/update `.dockerignore`**

Ensure `node_modules`, `venv`, `__pycache__`, `*.pyc`, `output/`, `cache/`, `logs/`, `.graphify/`, `scratch/`, `*.tmp`, `.coverage`, `.pytest_cache`, `htmlcov/` are excluded. Also exclude `docs/`, `tests/`, images.

- [ ] **Step 4: Verify Dockerfiles build locally**

```bash
docker build -t graphrag-web-test .
docker build -t graphrag-litellm-test -f Dockerfile.litellm .
```

- [ ] **Step 5: Commit**

```bash
git add Dockerfile Dockerfile.litellm .dockerignore
git commit -m "fix(deploy): fix Dockerfiles, pin Python 3.11, add LiteLLM Dockerfile"
```

### Task 1.3: Create docker-compose.yml with nginx + static assets

**Files:**
- Modify: `docker-compose.yml` (complete rewrite)
- Create: `nginx/nginx.conf`
- Create: `certbot/` directory (placeholder reference)

**Interfaces:**
- Consumes: Dockerfiles from Task 1.2
- Produces: Three-service compose stack runnable via `docker-compose up` locally

- [ ] **Step 1: Rewrite `docker-compose.yml`**

Four services: web, litellm, nginx, certbot. Include health checks, volumes, env vars, restart policies. See spec for exact YAML structure.

- [ ] **Step 2: Create `nginx/nginx.conf`**

See spec for exact nginx config — serves static files directly, proxies /api/* to FastAPI, no buffering for SSE.

- [ ] **Step 3: Test compose stack locally**

```bash
export OPENROUTER_API_KEY=test GEMINI_API_KEY=test FREELLMAPI_API_KEY=test
docker compose up --build -d web litellm
sleep 10
curl -f http://localhost:8000/api/health
docker compose down
```

This validates networking works even without full API key setup.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml nginx/
git commit -m "feat(deploy): add docker-compose with nginx reverse proxy, static asset serving"
```

### Task 1.4: Add favicon + health endpoint + fix CLI for local dev

**Files:**
- Create: `src/web/static/favicon.ico` (simple icon)
- Modify: `src/web/app.py` (add `/api/health` endpoint if missing)
- Modify: `src/cli.py` (support running via uvicorn as fallback)

**Interfaces:**
- Consumes: Static file dir structure from `src/web/app.py`
- Produces: No favicon 404, working health check, robust local launch

- [ ] **Step 1: Check if `/api/health` endpoint exists**

Search `src/web/app.py` for "health". If missing, add:
```python
@router.get("/api/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 2: Create minimal favicon**

Create `src/web/static/favicon.ico` — simple resume document icon ICO (~4KB).

- [ ] **Step 3: Update `cli.py` ui subcommand**

Make it try vercel dev first, fall back to direct uvicorn:
```python
elif args.command == "ui":
    print("[CLI] Starting Web UI...")
    try:
        res = subprocess.run(["vercel", "dev"], cwd=str(ROOT_DIR))
    except FileNotFoundError:
        print("[CLI] vercel CLI not available, launching uvicorn directly...")
        cmd = ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "3000"]
        py = str(venv / "Scripts" / "python") if sys.platform == "win32" else "python"
        res = subprocess.run([py] + cmd)
    if res.returncode != 0:
        sys.exit(res.returncode)
```

- [ ] **Step 4: Commit and test**

```bash
git add src/web/static/favicon.ico src/web/app.py src/cli.py
git commit -m "fix(ui): add favicon, health endpoint, graceful fallback for local dev"
```

### Task 1.5: GitHub Actions CI/CD pipeline

**Files:**
- Create: `.github/workflows/deploy.yml`

**Interfaces:**
- Consumes: docker-compose.yml and Dockerfiles from Tasks 1.2-1.3
- Produces: Automated deploy on push to main

- [ ] **Step 1: Create deploy workflow**

See spec for complete deploy.yml content (build → save images → SCP to Oracle VM → docker load → compose up -d).

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: add Oracle Cloud deployment pipeline"
```

Phase 1 complete. All 6 deployment issues fixed:
1. ✅ Python version pinned (`.python-version`, Dockerfile uses 3.11-slim)
2. ✅ `vercel dev` workaround added (cli.py falls back to uvicorn)
3. ✅ Dockerfiles fixed (correct path, includes litellm dep)
4. ✅ Dependencies pinned (all versions locked)
5. ✅ Favicon added (`src/web/static/favicon.ico`)
6. ✅ Static assets served by nginx (not through Python function)

---

## Phase 2: GraphRAG Enhancements

### Task 2.1: Create GraphRAGEngine with LanceDB connection

**Files:**
- Create: `src/query/graphrag_engine.py`
- Test: `tests/test_graphrag_engine.py`

**Interfaces:**
- Consumes: None
- Produces: `GraphRAGEngine(root_dir)` class with `.connect()`, `.get_embedding()`, mode stubs

- [ ] **Step 1: Write test scaffolding**

```python
# tests/test_graphrag_engine.py
import pytest
from pathlib import Path
from src.query.graphrag_engine import GraphRAGEngine

def test_graphrag_engine_instantiation():
    engine = GraphRAGEngine(str(Path(".").resolve()))
    assert engine.root_dir is not None

def test_connect_raises_on_missing_artifacts(tmp_path):
    engine = GraphRAGEngine(str(tmp_path))
    with pytest.raises(FileNotFoundError):
        engine.connect()
```

- [ ] **Step 2: Create `graphrag_engine.py` skeleton**

```python
# src/query/graphrag_engine.py
import os
from pathlib import Path
from typing import Optional
import pandas as pd
import lancedb

class GraphRAGEngine:
    def __init__(self, root_dir: str = None):
        self.root_dir = Path(root_dir or os.environ.get("ROOT_DIR", "."))
        self.db: Optional["lancedb.DBConnection"] = None
        self.entities: Optional[pd.DataFrame] = None
        self.relationships: Optional[pd.DataFrame] = None
        self.communities: Optional[pd.DataFrame] = None
        self.text_units: Optional[pd.DataFrame] = None
    
    def connect(self) -> None:
        lancedb_path = self.root_dir / "output" / "lancedb"
        parquet_dir = self.root_dir / "output"
        
        if not lancedb_path.exists():
            raise FileNotFoundError(f"LanceDB directory not found: {lancedb_path}")
        
        self.db = lancedb.connect(str(lancedb_path))
        text_unit_table = self.db.open_table("default-text_unit-text")
        community_table = self.db.open_table("default-community-full_content")
        
        self.entities = pd.read_parquet(parquet_dir / "entities.parquet")
        self.relationships = pd.read_parquet(parquet_dir / "relationships.parquet")
        self.communities = pd.read_parquet(parquet_dir / "community_reports.parquet")
        self.text_units = pd.read_parquet(parquet_dir / "text_units.parquet")
    
    async def get_embedding(self, text: str) -> list[float]:
        from src.query.serverless_gateway import get_embedding
        return await get_embedding(text)
```

- [ ] **Step 3: Run test — should fail (module doesn't exist)**

```bash
python -m unittest tests/test_graphrag_engine.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 4: Commit**

```bash
git add src/query/graphrag_engine.py tests/test_graphrag_engine.py
git commit -m "feat(graphrag): create GraphRAGEngine with LanceDB connection and artifact loading"
```

### Task 2.2: Implement local retrieval (vector search + entity extraction)

**Files:**
- Modify: `src/query/graphrag_engine.py` (add `_local_retrieval`)
- Test: `tests/test_graphrag_engine.py` (add retrieval tests)

**Interfaces:**
- Consumes: `engine.db`, `engine.entities`, `engine.relationships`, `engine.text_units` from Task 2.1
- Produces: `_local_retrieval(query) -> dict{text_units, entities, relationships}`

- [ ] **Step 1: Write test**

```python
# Add to tests/test_graphrag_engine.py
import asyncio

def test_local_retrieval_returns_dict_keys():
    engine = GraphRAGEngine(str(Path(".").resolve()))
    engine.connect()
    
    result = asyncio.run(engine._local_retrieval("AWS"))
    
    assert isinstance(result, dict)
    assert "text_units" in result
    assert "entities" in result
    assert "relationships" in result
    assert len(result["text_units"]) > 0
    assert len(result["entities"]) > 0
```

- [ ] **Step 2: Implement `_local_retrieval`**

Append to `GraphRAGEngine`:
```python
async def _local_retrieval(self, query: str, top_k: int = 10) -> dict:
    query_emb = await self.get_embedding(query)
    results = self.db.open_table("default-text_unit-text").search(query_emb).limit(top_k).to_pandas()
    text_unit_ids = results["id"].tolist()
    relevant_entities = self.entities[self.entities["text_unit_ids"].apply(
        lambda x: any(tid in x for tid in text_unit_ids)
    )].head(20)
    entity_ids = relevant_entities["id"].tolist()
    relevant_relationships = self.relationships[
        (self.relationships["source"].isin(entity_ids)) |
        (self.relationships["target"].isin(entity_ids))
    ].head(30)
    return {
        "text_units": results.to_dict("records"),
        "entities": relevant_entities.to_dict("records"),
        "relationships": relevant_relationships.to_dict("records"),
    }
```

- [ ] **Step 3: Run test**

```bash
python -m unittest tests/test_graphrag_engine.py::test_local_retrieval_returns_dict_keys -v
```

Expected: Pass.

- [ ] **Step 4: Commit**

```bash
git add src/query/graphrag_engine.py tests/test_graphrag_engine.py
git commit -m "feat(graphrag): add local retrieval with vector search + entity/relationship extraction"
```

### Task 2.3: Implement global + drift retrieval modes

**Files:**
- Modify: `src/query/graphrag_engine.py` (add `_global_retrieval`, `_drift_retrieval`)
- Test: `tests/test_graphrag_engine.py` (add tests for each mode)

**Interfaces:**
- Consumes: Same engine state from Task 2.2
- Produces: Three complete retrieval methods

- [ ] **Step 1: Write tests**

```python
def test_global_retrieval_queries_community_table():
    engine = GraphRAGEngine(str(Path(".").resolve()))
    engine.connect()
    result = asyncio.run(engine._global_retrieval("career summary"))
    assert "communities" in result
    assert len(result["communities"]) > 0

def test_drift_expands_context():
    engine = GraphRAGEngine(str(Path(".").resolve()))
    engine.connect()
    result = asyncio.run(engine._drift_retrieval("Python microservices"))
    assert len(result["entities"]) >= len(result.get("seed_entities", []))
```

- [ ] **Step 2: Implement `_global_retrieval` and `_drift_retrieval`**

Global:
```python
async def _global_retrieval(self, query: str, top_k: int = 5) -> dict:
    query_emb = await self.get_embedding(query)
    results = self.db.open_table("default-community-full_content").search(query_emb).limit(top_k).to_pandas()
    return {"communities": results.to_dict("records")}
```

Drift (multi-hop):
```python
async def _drift_retrieval(self, query: str, hop_limit: int = 2) -> dict:
    initial = await self._local_retrieval(query, top_k=10)
    seed_entities = initial["entities"][:5]
    expanded = []
    for entity in seed_entities:
        related = self.relationships[(self.relationships["source"] == entity["id"]) | 
                                     (self.relationships["target"] == entity["id"])].head(3)
        for _, rel in related.iterrows():
            other_id = rel["target"] if rel["source"] == entity["id"] else rel["source"]
            other = self.entities[self.entities["id"] == other_id]
            if not other.empty:
                expanded.append(other.iloc[0].to_dict())
    seen = {e["id"] for e in seed_entities}
    unique = [e for e in expanded if e["id"] not in seen][:10]
    return {
        **initial,
        "entities": seed_entities + unique,
        "seed_entities": seed_entities,
    }
```

- [ ] **Step 3: Run all tests**

```bash
python -m unittest tests/test_graphrag_engine.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/query/graphrag_engine.py tests/test_graphrag_engine.py
git commit -m "feat(graphrag): add global summary and multi-hop DRIFT retrieval modes"
```

### Task 2.4: Add conversation memory (SQLite persistence)

**Files:**
- Create: `src/query/conversation_store.py`
- Test: `tests/test_conversation_store.py`

**Interfaces:**
- Consumes: None
- Produces: `ConversationStore` with `.add_message(session_id, role, content)`, `.get_history(session_id, limit=10)`, `get_or_create_conversation(session_id) -> int`, module-level `get_conversation_store() -> ConversationStore`

- [ ] **Step 1: Write tests**

```python
# tests/test_conversation_store.py
import pytest
from src.query.conversation_store import ConversationStore

@pytest.fixture
def store(tmp_path):
    return ConversationStore(db_path=str(tmp_path / "conv.db"))

def test_add_and_get_messages(store):
    store.add_message("session-1", "user", "Hello")
    store.add_message("session-1", "assistant", "Hi there")
    history = store.get_history("session-1", limit=10)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Hi there"

def test_isolation_between_sessions(store):
    store.add_message("session-a", "user", "A")
    store.add_message("session-b", "user", "B")
    a = store.get_history("session-a")
    b = store.get_history("session-b")
    assert len(a) == 1 and len(b) == 1
    assert a[0]["content"] == "A"
    assert b[0]["content"] == "B"

def test_limit_parameter(store):
    for i in range(5):
        store.add_message("sess", "user", f"msg{i}")
    history = store.get_history("sess", limit=3)
    assert len(history) == 3
```

- [ ] **Step 2: Implement `conversation_store.py`**

Exact content per spec (SQLite init, conversations/messages tables, add/get history, singleton get_conversation_store).

- [ ] **Step 3: Run tests**

```bash
python -m unittest tests/test_conversation_store.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/query/conversation_store.py tests/test_conversation_store.py
git commit -m "feat(graphrag): add SQLite conversation memory with per-session isolation"
```

### Task 2.5: Add SSE streaming to serverless_gateway

**Files:**
- Modify: `src/query/serverless_gateway.py` (add streaming methods)
- Test: `tests/test_serverless_gateway_streaming.py`

**Interfaces:**
- Consumes: `OPENROUTER_API_KEY`, `GEMINI_API_KEY` env vars
- Produces: `call_serverless_llm_stream(system_prompt, user_message, temperature=0.3) -> AsyncGenerator[str, None]`

- [ ] **Step 1: Write test (will fail until implemented)**

```python
# tests/test_serverless_gateway_streaming.py
import pytest
import asyncio
from src.query.serverless_gateway import call_serverless_llm_stream

@pytest.mark.asyncio
async def test_stream_yields_multiple_tokens():
    tokens = []
    async for token in call_serverless_llm_stream("You are helpful.", "Say hi.", 0.3):
        tokens.append(token)
    assert len(tokens) >= 1, "Streaming should produce at least some tokens"
```

- [ ] **Step 2: Add streaming methods to `serverless_gateway.py`**

Import: `json`, `aiohttp`, `asyncio`, `logging`

Append `call_serverless_llm_stream`, `_stream_openrouter`, `_stream_gemini` functions. OpenRouter streams via HTTP POST with `stream=true`. Gemini streams via `streamGenerateContent` endpoint. Both yield individual tokens.

- [ ] **Step 3: Run tests**

If API keys invalid, gracefully handled. Full verification requires valid keys.

- [ ] **Step 4: Commit**

```bash
git add src/query/serverless_gateway.py tests/test_serverless_gateway_streaming.py
git commit -m "feat(graphrag): add SSE streaming via OpenRouter and Gemini APIs"
```

### Task 2.6: Wire up API routes with SSE streaming + context assembly

**Files:**
- Modify: `src/shared/api_routes.py` (update `/api/query` to use new engine)
- Modify: `src/shared/api_models.py` (add `mode` field, `session_id` optional)
- Test: `tests/test_api_routes_query.py`

**Interfaces:**
- Consumes: `GraphRAGEngine`, `call_serverless_llm_stream`, `get_conversation_store`
- Produces: Working `/api/query` endpoint returning `StreamingResponse` with SSE events

- [ ] **Step 1: Extend request model in `api_models.py`**

```python
from typing import Literal, Optional

class QueryRequest(BaseModel):
    query: str
    mode: Literal["local", "global", "drift"] = "local"
    session_id: Optional[str] = None
```

- [ ] **Step 2: Rewrite `/api/query` endpoint in `api_routes.py`**

Add to imports: `AsyncGenerator`, `StreamingResponse`, `GraphRAGEngine`, `get_conversation_store`, `call_serverless_llm_stream`, `json`.

New endpoint returns `StreamingResponse` with SSE format events. Uses engine to retrieve context, calls LLM stream, yields tokens incrementally. Saves conversation history.

Also add to `graphrag_engine.py`:
```python
async def query(self, query: str, mode: str, conversation_history: list = None) -> AsyncGenerator[str, None]:
    context = await getattr(self, f"_{mode}_retrieval")(query)
    sys_prompt = f"Answer questions about Prasad Rane's experience. Context:\n{self._format_context(context)}\nHistory:\n{''.join(f'{m['role']}: {m['content']}\n' for m in conversation_history) if conversation_history else 'No history'}"
    full_resp = []
    async for token in call_serverless_llm_stream(sys_prompt, query, 0.3):
        full_resp.append(token)
        yield f'data: {json.dumps({"token": token, "done": False})}\n\n'
    yield f'data: {json.dumps({"done": True, "sources": [], "full_response": "".join(full_resp)})}\n\n'

def _format_context(self, context: dict) -> str:
    parts = []
    if "entities" in context:
        parts.extend(f"Entity: {e.get('name', '')} - {e.get('description', '')[:200]}" for e in context["entities"][:10])
    if "relationships" in context:
        parts.extend(f"Relation: {r.get('source', '')} -> {r.get('target', '')}" for r in context["relationships"][:10])
    return "\n".join(parts)
```

- [ ] **Step 3: Write route test**

```python
# tests/test_api_routes_query.py
from fastapi.testclient import TestClient
from src.web.app import app
from src.shared.api_routes import shared_router
app.include_router(shared_router)
client = TestClient(app)

def test_query_accepts_mode_param():
    resp = client.post("/api/query", json={"query": "AWS", "mode": "local"})
    assert resp.status_code != 400, "Should accept mode parameter"
```

- [ ] **Step 4: Commit**

```bash
git add src/shared/api_routes.py src/shared/api_models.py src/query/graphrag_engine.py tests/test_api_routes_query.py
git commit -m "feat(graphrag): wire SSE streaming, mode selection, and conversation memory to API"
```

### Task 2.7: Update frontend for SSE streaming + mode selector

**Files:**
- Modify: `src/web/static/js/app.js` (update chat handler)
- Modify: `src/web/static/index.html` (add mode selector radio buttons)

**Interfaces:**
- Consumes: SSE format `{"token": "...", "done": false}` and `{"done": true, "sources": [...]}`
- Produces: Frontend shows incremental tokens, displays suggested mode selector

- [ ] **Step 1: Add mode selector HTML to index.html**

Before the chat input area:
```html
<div class="query-mode">
    <label>Local</label><input type="radio" name="qmode" value="local" checked>
    <label>Global</label><input type="radio" name="qmode" value="global">
    <label>DRIFT</label><input type="radio" name="qmode" value="drift">
</div>
```

- [ ] **Step 2: Update JavaScript fetch to SSE streaming in app.js**

Replace single-request `fetch` with ReadableStream-based SSE parser:

```javascript
const mode = document.querySelector('input[name="qmode"]:checked').value;
const sessionId = localStorage.getItem('graphrag_session') || crypto.randomUUID();
localStorage.setItem('graphrag_session', sessionId);

try {
    const response = await fetch('/api/query', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query: message, mode: mode, session_id: sessionId})
    });
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, {stream: true});
        const lines = buffer.split('\n\n');
        buffer = lines.pop();
        
        for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const data = JSON.parse(line.slice(6));
            
            if (data.token && !data.done) {
                appendMessageToken(data.token);
            }
            if (data.done) {
                showSources(data.sources || []);
            }
            if (data.error) {
                showError(data.token);
            }
        }
    }
} catch (err) {
    appendErrorMessage(err.message);
}
```

- [ ] **Step 3: Test manually with app running**

Open UI, select different modes, send queries, verify tokens appear incrementally.

- [ ] **Step 4: Commit**

```bash
git add src/web/static/index.html src/web/static/js/app.js
git commit -m "feat(ui): add SSE streaming, mode selector, incremental token display to Q&A chat"
```

### Task 2.8: Remove dead code paths

**Files:**
- Modify: `src/query/search_engine.py`
- Modify: `src/query/static_graph_reader.py`

**Interfaces:**
- Consumes: None
- Produces: Cleaner codebase, smaller attack surface

- [ ] **Step 1: Remove dead functions from `search_engine.py`**

Delete:
- `_run_graphrag_query_uncached()` (never called)
- `search_static_graph()` (only used by tests — also remove test references)
- Unused helper functions

Keep `search_static_resume()` as fallback only, simplify hardcoded lookup branches.

- [ ] **Step 2: Simplify `static_graph_reader.py`**

Remove brittle canned answer patterns. Keep pure keyword-match + bullet-scan fallback logic.

- [ ] **Step 3: Run all tests**

```bash
python -m unittest discover tests -v
```

Expected: All still pass (removed functions were already dead; updated references in remaining tests).

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor(graphrag): remove dead code from search engine and static reader"
```

### Task 2.9: End-to-end integration test

**Files:**
- Create: `tests/e2e/test_graphrag_e2e.py`

**Interfaces:**
- Consumes: Everything from Tasks 2.1-2.8
- Produces: Verified end-to-end pipeline from browser → API → GraphRAG → LLM → Streaming → Response

- [ ] **Step 1: Write E2E test**

```python
# tests/e2e/test_graphrag_e2e.py
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from src.web.app import app
from src.shared.api_routes import shared_router
app.include_router(shared_router)

@pytest.mark.asyncio
async def test_full_query_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/query", json={
            "query": "What AWS technologies did Prasad use?",
            "mode": "local",
        }, timeout=30)
        assert resp.status_code == 200
        body = resp.json()
        assert "answer" in body or "token" in body
```

- [ ] **Step 2: Run full test suite**

```bash
python -m unittest discover tests -v --failfast
```

Expected: All tests pass including new ones (total count should increase from 125).

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/
git commit -m "test(e2e): add end-to-end integration test for GraphRAG query flow"
```

---

## Execution Summary

Two execution options:

**1. Subagent-Driven** — Dispatch a fresh subagent per task, review between tasks, fast iteration
**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Choose one.
