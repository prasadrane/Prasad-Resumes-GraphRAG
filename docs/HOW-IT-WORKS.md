# How It Works: Embeddings, GraphRAG & LLM in This Project

This document explains how **Vector Embeddings**, **GraphRAG**, and **LLMs** work together in the GraphRAG Resume Generator project. It's designed for understanding the architecture and code flow.

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Chat Q&A Flow](#chat-qa-flow)
3. [Resume Tailoring Flow](#resume-tailoring-flow)
4. [Comparison of Both Flows](#comparison-of-both-flows)
5. [Key Files & Code Locations](#key-files--code-locations)

---

## Core Concepts

### 1. Vector Embeddings — "The Computer's Way of Understanding Words"

**What it is:** Turning text into a list of numbers (a vector) that captures meaning.

**How it works:**
- Every word/sentence gets converted into numbers like `[0.82, 0.15, 0.91, ...]`
- Similar meanings end up close together in this "number space"
- Example: "king" and "queen" vectors are close; "king" and "banana" are far apart

**In this project:**
- Questions are converted to embeddings
- Resume chunks are pre-indexed as embeddings in LanceDB
- Vector search finds the most relevant chunks for a query

### 2. GraphRAG — "A Mind Map for AI"

**What it is:** A knowledge graph that connects entities (people, technologies, projects) with relationships.

**How it works:**
```
Prasad ──led──→ AWS Migration Project
    │                │
    │                └──used──→ Lambda, S3, EC2
    │
    └──managed──→ Team of 5 Engineers
```

**In this project:**
- Microsoft GraphRAG indexes the entire resume + story bank
- Extracts entities, relationships, and communities
- Stores in Parquet files + LanceDB for vector search
- Queries traverse the graph to find connected information

### 3. LLM (Large Language Model) — "The AI Brain"

**What it is:** A neural network (like GPT-4, Claude, Gemini) that generates human-like text.

**How it works:**
- You give it a prompt (system instructions + context + question)
- It predicts, word by word, the best response
- It only knows what's in the prompt — it doesn't have access to your resume directly

**In this project:**
- Uses Alibaba (qwen3.7-plus) → OpenRouter → Gemini fallback chain
- Generates answers for chat queries
- Rewrites resume content to match job descriptions

---

## Chat Q&A Flow

When a user asks a question like "What AWS experience does Prasad have?", the system follows these steps:

### Step 1: User Asks a Question (API Route)

**File:** `src/shared/api_routes.py` (lines 42-59)

```python
@shared_router.post("/api/chat-stream")
def chat_stream_endpoint(req: QueryRequest):
    """Chat stream endpoint yielding tokens incrementally via SSE."""
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    return StreamingResponse(
        _stream_query_response(req),
        media_type="text/event-stream",
    )
```

**What happens:** The user's question is received via HTTP POST and streaming response is initiated.

### Step 2: Convert Question to Embedding

**File:** `src/query/graphrag_engine.py` (lines 93-96)

```python
async def get_embedding(self, text: str) -> List[float]:
    """Delegate embedding generation to serverless_gateway (OpenRouter → Gemini)."""
    from src.gateway import get_embedding as _get_emb
    return await _get_emb(text)
```

**File:** `src/gateway/facade.py` (lines 196-219)

```python
async def get_embedding(text: str) -> List[float]:
    """Get a text embedding via openrouter → litellm proxy → gemini direct."""
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GRAPHRAG_API_KEY")

    if openrouter_key:
        try:
            return await _client("openrouter").embed(text)  # ← Try OpenRouter first
        except Exception as err:
            log.warning("[WARN] OpenRouter embed failed (%s). Trying fallback…", err)

    if gemini_key:
        try:
            return await _litellm_embed(text, gemini_key)  # ← Fallback to LiteLLM
        except Exception as err:
            log.warning("[WARN] LiteLLM proxy embed failed (%s). Trying Gemini direct…", err)

    if gemini_key:
        try:
            return await _client("gemini").embed(text)  # ← Final fallback: Gemini
        except Exception as err:
            raise RuntimeError(f"Gemini embedding failed: {err}") from err
```

**What happens:** Your question gets converted to a vector embedding by calling OpenRouter or Gemini embedding API.

### Step 3: GraphRAG Retrieves Relevant Context (Vector Search + Graph Traversal)

**File:** `src/query/graphrag_engine.py` (lines 140-171)

```python
async def _local_retrieval(self, query: str, top_k: int = 26) -> Dict[str, Any]:
    # Try vector search first, fall back to keyword search if embeddings fail
    try:
        # 1. Open the LanceDB table containing text chunks
        table = self._db.open_table("default-text_unit-text")
        
        # 2. Convert query to embedding (we just did this in Step 2)
        emb = await self.get_embedding(query)
        
        # 3. 🔍 VECTOR SEARCH: Find text chunks closest to your query embedding
        results = table.search(emb).limit(top_k).to_pandas()
        
    except Exception as e:
        # Fallback to keyword search on text_units parquet
        results = self._keyword_search(self._text_units, "text", query, top_k)

    # 4. Get the IDs of matching text chunks
    text_unit_ids: List[Any] = results["id"].tolist()

    # 5. 🕸️ GRAPH TRAVERSAL: Find entities that wrote these text chunks
    mask = self._entities["text_unit_ids"].apply(
        lambda arr: any(_tid_match(tid, arr) for tid in text_unit_ids)
    )
    relevant_ents = self._entities[mask]
    ent_ids = relevant_ents["id"].tolist()

    # 6. 🔗 Find relationships involving those entities
    rel_mask = (
        self._relationships["source"].isin(ent_ids)
        | self._relationships["target"].isin(ent_ids)
    )
    relevant_rels = self._relationships[rel_mask]

    return {
        "text_units": results,           # ← Relevant text chunks
        "entities": relevant_ents,        # ← Connected entities (Prasad, AWS, etc.)
        "relationships": relevant_rels,   # ← Relationships (Prasad → led → AWS)
    }
```

**What happens:**
1. LanceDB searches for text chunks whose embeddings are closest to your query
2. It finds the entities (Prasad, AWS Lambda, etc.) that are mentioned in those chunks
3. It finds the relationships between those entities (Prasad **led** AWS Migration)
4. Returns all this as **context**

### Step 4: Context Gets Formatted into a Prompt

**File:** `src/query/graphrag_engine.py` (lines 233-276)

```python
@staticmethod
def format_context(context: Dict[str, Any]) -> str:
    """Render a retrieved *context* dict into a human-readable string for LLM ingestion."""
    parts: List[str] = []

    # Format text chunks
    tUs = context.get("text_units")
    if tUs is not None and not tUs.empty:
        parts.append("## Relevant Text Segments")
        for _, tu in tUs.iterrows():
            txt = str(tu.get("text", "")).strip()
            if txt:
                parts.append(f"- {txt}")

    # Format entities
    ents = context.get("entities")
    if ents is not None and not ents.empty:
        parts.append("\n## Key Entities")
        for _, e in ents.head(10).iterrows():
            name = e.get("title", "") or e.get("name", "")
            desc = str(e.get("description", ""))[:150]
            parts.append(f"- **{name}** ({e.get('type', '')}): {desc}")

    # Format relationships
    rels = context.get("relationships")
    if rels is not None and not rels.empty:
        parts.append("\n## Relationships")
        for _, r in rels.head(8).iterrows():
            src = str(r.get("source", ""))[:40]
            tgt = str(r.get("target", ""))[:40]
            desc = str(r.get("description", ""))[:100]
            parts.append(f"- {src} → {tgt}: {desc}")

    return "\n".join(parts)
```

**File:** `src/query/graphrag_engine.py` (lines 362-394)

```python
def _build_system_prompt(
    self,
    mode: str,
    context: Dict[str, Any],
    history: Optional[List[Dict[str, str]]],
) -> str:
    # System instruction based on query mode
    personas = {
        "local": (
            "You are a knowledgeable assistant answering questions about Prasad Rane's "
            "professional experience. Use ALL the provided context comprehensively..."
        ),
        "global": (
            "You are a career analyst providing executive-level summaries..."
        ),
        "drift": (
            "You are a career researcher performing multi-hop analysis..."
        ),
    }
    sys_msg = personas.get(mode, personas["local"])

    # Add conversation history if exists
    hist = ""
    if history:
        pairs = history[-6:]  # last 3 exchanges
        hist_lines = [f"{m['role']}: {m['content']}" for m in pairs]
        hist = "\n\nPrevious conversation:\n" + "\n".join(hist_lines)

    # 🔥 FINAL PROMPT = System Instruction + Retrieved Context + History
    return f"{sys_msg}\n\nContext:\n{self.format_context(context)}{hist}"
```

**What happens:** The retrieved context (text chunks, entities, relationships) gets formatted into a readable string and combined with system instructions and conversation history.

### Step 5: Prompt + Question Sent to LLM

**File:** `src/query/graphrag_engine.py` (lines 301-333)

```python
async def chat_stream(
    self,
    query: str,
    mode: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> AsyncGenerator[str, None]:
    """Stream a GraphRAG answer token-by-token via SSE frames."""
    
    # 1. Retrieve context (we did this in Step 3)
    context = await self.retrieve(query, mode=mode)

    # 2. Build system prompt with context (we did this in Step 4)
    sys_prompt = self._build_system_prompt(mode, context, conversation_history)

    full_resp_parts: List[str] = []

    # 3. 🤖 SEND TO LLM: system_prompt + user query → LLM generates answer
    try:
        from src.gateway import call_serverless_llm_stream

        async for token in call_serverless_llm_stream(
            system_prompt=sys_prompt,    # ← System instructions + context
            user_message=query,          # ← Your question: "What AWS experience..."
            temperature=0.3,
        ):
            full_resp_parts.append(token)
            yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
```

**File:** `src/gateway/facade.py` (lines 160-193)

```python
async def call_serverless_llm_stream(
    system_prompt: Optional[str],
    user_message: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
    timeout: int = 60,
) -> AsyncGenerator[str, None]:
    """Streaming chat — yields tokens from the first provider that returns any."""
    resolved = model or get_model_for("chat")[1]
    
    # Try providers in order: alibaba → openrouter → gemini
    for name in _CHAT_CHAIN_ORDER:
        if not _has_key(name):
            continue
        any_attempted = True
        provider = _client(name)
        gen = provider.chat_stream(system_prompt, user_message, resolved, temperature, timeout)
        consumed = False
        try:
            while True:
                tok = await gen.__anext__()
                yield tok  # ← Stream tokens back to user
                consumed = True
        except StopAsyncIteration:
            if consumed:
                return  # successfully yielded at least one token
            continue  # nothing yielded → try next provider
        break
```

**What happens:**
1. The system prompt (with all the GraphRAG context) + your question get sent to the LLM
2. The LLM reads the context and generates an answer token-by-token
3. Tokens stream back to the user in real-time

### Chat Q&A Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: User asks "What AWS experience does Prasad have?"          │
│ → api_routes.py:chat_stream_endpoint() receives the query          │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: Convert question to embedding                               │
│ → graphrag_engine.py:get_embedding()                                │
│ → facade.py:get_embedding() → OpenRouter/Gemini API                │
│ → Returns: [0.82, 0.15, 0.91, ...] (vector of numbers)            │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: Retrieve relevant context from knowledge graph              │
│ → graphrag_engine.py:_local_retrieval()                             │
│   • Vector search in LanceDB (find text chunks close to query)     │
│   • Graph traversal (find entities & relationships)                │
│ → Returns: text_units + entities + relationships                   │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 4: Build the prompt                                            │
│ → graphrag_engine.py:format_context() + _build_system_prompt()     │
│ → Combines: System instruction + Retrieved context + History       │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 5: Send prompt + question to LLM                               │
│ → graphrag_engine.py:chat_stream()                                  │
│ → facade.py:call_serverless_llm_stream()                            │
│ → Alibaba/OpenRouter/Gemini API streams response token-by-token    │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ANSWER: "Prasad has extensive AWS experience including ECS Fargate,│
│ Lambda, Bedrock AI chatbots, Kafka/MSK governance, achieving 40%   │
│ cost reduction and 99.95% uptime..."                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Resume Tailoring Flow

When generating a tailored resume for a job description, the system follows these steps:

### Step 1: Extract ATS Keywords from Job Description

**File:** `src/generators/ats_matcher.py` (lines 51-85)

```python
def extract_ats_keywords(jd_text: str) -> list[str]:
    """Extract ATS keywords, technologies, and competencies dynamically from job description text."""
    if not jd_text or not jd_text.strip():
        return []

    found = set()
    upper_keywords = {kw.upper() for kw in COMMON_ATS_KEYWORDS}
    
    # 1. Match static dictionary terms
    cleaned = re.sub(r"[^A-Za-z0-9+#/\s-]", " ", jd_text)
    tokens = [t.strip().upper() for t in cleaned.split() if len(t.strip()) >= 2]

    for token in tokens:
        if token in upper_keywords:
            matched_kw = next((kw for kw in COMMON_ATS_KEYWORDS if kw.upper() == token), token)
            found.add(matched_kw)

    # 2. Match known technical & domain patterns (regex)
    for pat in KNOWN_TECH_PATTERNS:
        matches = re.findall(pat, jd_text, re.IGNORECASE)
        for m in matches:
            found.add(m.strip())

    # 3. Match camelCase / TitleCase technical terms from JD
    words = re.findall(r"\b[A-Z][a-zA-Z0-9#+.-]{2,}\b", jd_text)
    # ... more matching logic
    
    return sorted(list(found), key=lambda x: (len(x), x), reverse=True)
```

**What happens:** The JD text is scanned for keywords like "AWS", "Lambda", "Python", "Microservices", etc. These become the search terms.

### Step 2: Query GraphRAG Knowledge Graph for Relevant Stories

**File:** `src/generators/ats_matcher.py` (lines 87-108)

```python
def match_graphrag_stories(keywords: list[str], root_dir: Optional[Path] = None) -> list[str]:
    """Query GraphRAG knowledge graph using keywords to retrieve candidate achievements."""
    if not keywords:
        return []

    # Build a query string from keywords
    query_str = f"Find relevant experience and metrics for: {', '.join(keywords)}"
    
    try:
        if root_dir is None:
            root_dir = ROOT_DIR
        # 🔍 THIS IS WHERE GRAPHRAG HAPPENS!
        response = execute_graphrag_query(query_str, mode="local", root_dir=root_dir)
        
        if not response:
            return []
        return [line.strip() for line in response.split("\n") if line.strip()]
    except Exception as e:
        print(f"[WARN] GraphRAG matcher fallback to serverless gateway: {e}")
        # Fallback to direct LLM call
        try:
            from src.llm.service import call_llm
            res = call_llm(query_str, system_prompt="You are an ATS resume matcher...")
            return [line.strip() for line in res.split("\n") if line.strip()]
        except Exception as s_err:
            print(f"[WARN] Serverless gateway fallback error: {s_err}")
            return []
```

**What happens:**
1. Keywords from JD → Construct a query string
2. Query GraphRAG → Get relevant achievements/stories
3. The GraphRAG query internally uses embeddings + vector search
4. Returns relevant context about Prasad's achievements

### Step 3: Build the LLM Prompt with All Context

**File:** `src/generators/resume_generator.py` (lines 418-487)

```python
def tailor_resume_with_llm_single_call(parsed: "ResumeData", company_name: str, jd_text: str,
                                        graphrag_context: str, gap_framing: str, top_metrics: str) -> "ResumeData":
    """
    Combined LLM call: rewrites both summary AND bullets in a single API call.
    """
    jobs_with_bullets = [job for job in parsed.jobs if job.bullets]

    # Build combined prompt with ALL the context
    prompt_parts = [
        f"## Target Role\nCompany: {company_name}\n",
        f"## Full Job Description\n{jd_text}\n",
        f"## Original Summary\n{parsed.summary}\n",
    ]

    # Add top metrics (quantified achievements)
    if top_metrics:
        prompt_parts.append(
            f"## Candidate's Strongest Impact Metrics\n{top_metrics}\n"
        )

    # 🔥 ADD GRAPHRAG CONTEXT (from Step 2)
    if graphrag_context:
        prompt_parts.append(
            f"## Relevant Candidate Achievements (from Knowledge Graph)\n{graphrag_context}\n"
        )

    # Add gap-framing (how to address skill gaps)
    if gap_framing:
        prompt_parts.append(
            f"## Skill Bridging Notes\n{gap_framing}\n"
        )

    # Add all jobs' bullets to rewrite
    prompt_parts.append("## Experience Bullets to Rewrite\n")
    for idx, job in enumerate(jobs_with_bullets):
        prompt_parts.append(f"### Job {idx + 1}: {job.title} at {job.company} ({job.dates})")
        prompt_parts.append(f"Original bullets ({len(job.bullets)} total):")
        for i, b in enumerate(job.bullets):
            story = job.bullet_stories[i] if i < len(job.bullet_stories) else ""
            if story:
                prompt_parts.append(f"  [Context: {story}]")
            prompt_parts.append(f"  - {b}")
        prompt_parts.append("")

    # Instructions for the LLM
    prompt_parts.append(
        "## Your Task\n"
        "1. REWRITE THE SUMMARY: Create a compelling executive summary positioned for this specific role...\n\n"
        "2. REWRITE THE BULLETS: Rewrite and reorder bullets for each job to maximize JD relevance...\n\n"
        # ... formatting instructions
    )

    prompt = "\n".join(prompt_parts)

    # 🤖 SEND TO LLM
    from src.gateway import ALIBABA_RESUME_MODEL
    llm_response = _call_llm_safe(prompt, SUMMARY_SYSTEM_PROMPT, timeout=300, model=ALIBABA_RESUME_MODEL).strip()
```

**What happens:** The prompt combines:
- Target company + JD
- Original summary
- **GraphRAG context** (relevant achievements)
- Gap-framing notes
- Top metrics
- All experience bullets to rewrite

This goes to the LLM which rewrites everything to match the JD.

### Step 4: Parse LLM Response & Apply Changes

**File:** `src/generators/resume_generator.py` (lines 492-548)

```python
    # Parse the response
    lines = llm_response.split("\n")
    in_summary = False
    current_job_idx = -1
    summary_lines = []
    current_bullets = []

    for line in lines:
        line = line.strip()

        if line.startswith("### SUMMARY:"):
            in_summary = True
            current_job_idx = -1
            # ... collect summary lines
            continue

        if line.startswith("### JOB"):
            in_summary = False
            # Apply previous bullets
            if current_job_idx >= 0 and current_bullets:
                apply_job_bullets(current_job_idx, current_bullets)
            # Parse job number
            current_job_idx = int(line.split("JOB")[1].split(":")[0].strip()) - 1
            current_bullets = []
            continue

        if in_summary:
            if line:
                summary_lines.append(line)
        elif current_job_idx >= 0 and line:
            cleaned = re.sub(r"^[\s\-\*\•\·\d\.]+", "", line).strip()
            if cleaned:
                current_bullets.append(cleaned)

    # Apply last job's bullets
    if current_job_idx >= 0 and current_bullets:
        apply_job_bullets(current_job_idx, current_bullets)

    # Apply summary
    if summary_lines:
        new_summary = " ".join(summary_lines).strip()
        parsed.summary = new_summary

    return parsed
```

### Resume Tailoring Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: Extract ATS Keywords from Job Description                  │
│ → ats_matcher.py:extract_ats_keywords()                            │
│ → Returns: ["AWS", "Lambda", "Python", "Microservices", ...]       │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: Query GraphRAG for Relevant Achievements                   │
│ → ats_matcher.py:match_graphrag_stories()                          │
│ → search_engine.py:execute_graphrag_query()                        │
│   • Constructs query: "Find relevant experience for: AWS, Lambda…" │
│   • Vector search + graph traversal internally                     │
│   • Returns relevant stories & metrics                             │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: Build the Prompt                                            │
│ → resume_generator.py:tailor_resume_with_llm_single_call()         │
│ → Combines:                                                         │
│   • Target company + JD                                            │
│   • Original summary                                               │
│   • GraphRAG context (relevant achievements) ← FROM STEP 2         │
│   • Gap-framing notes                                              │
│   • Top metrics                                                    │
│   • All experience bullets to rewrite                              │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 4: Send to LLM (Alibaba qwen3.7-plus)                         │
│ → facade.py:call_serverless_llm()                                  │
│ → LLM rewrites summary + bullets to match JD                       │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ OUTPUT: Tailored Resume (Markdown + PDF)                           │
│ → Executive summary rewritten for the role                         │
│ → Bullets reordered & reframed to emphasize JD-relevant skills    │
│ → ATS keywords bolded (<20% cap)                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Comparison of Both Flows

| Aspect | Chat Q&A | Resume Tailoring |
|--------|----------|------------------|
| **Input** | Natural language question | Job Description keywords |
| **Embeddings** | Question → embedding | Keywords → query string (no explicit embedding at this step) |
| **GraphRAG** | Vector search + graph traversal | Same (internally via `execute_graphrag_query`) |
| **Context** | Retrieved text chunks + entities | Retrieved stories + gap-framing + metrics |
| **LLM Task** | Answer the question | Rewrite summary + bullets to match JD |
| **Output** | Text answer | Tailored resume (Markdown → PDF) |

### Key Similarities

1. **Both use GraphRAG** to retrieve relevant context from the knowledge graph
2. **Both use embeddings** (chat directly, resume indirectly through GraphRAG)
3. **Both send context to LLM** so it can generate accurate, relevant output
4. **Both use the same LLM gateway** (`src/gateway/facade.py`) with fallback chain

### Key Differences

1. **Input format:** Chat uses natural language; Resume uses JD keywords
2. **LLM task:** Chat answers questions; Resume rewrites content
3. **Output format:** Chat returns text; Resume generates structured Markdown + PDF

---

## Key Files & Code Locations

### Core Pipeline Files

| File | Purpose |
|------|---------|
| `src/query/graphrag_engine.py` | Main GraphRAG engine — loads parquet artifacts, vector search, context retrieval |
| `src/query/search_engine.py` | Search execution and LRU caching for GraphRAG queries |
| `src/query/static_graph_reader.py` | Fast static Parquet/JSON reader for serverless environments |
| `src/gateway/facade.py` | LLM gateway — provider cache, failover orchestration, public API |
| `src/gateway/alibaba.py` | AlibabaProvider — Anthropic-compatible protocol |
| `src/gateway/openrouter.py` | OpenRouterProvider — OpenAI-compatible protocol |
| `src/gateway/gemini.py` | GeminiProvider — Google REST protocol |
| `src/llm/service.py` | Thin wrappers for LLM calls used by resume generators |

### Resume Generation Files

| File | Purpose |
|------|---------|
| `src/generators/resume_generator.py` | Tailored resume content generator with LLM-driven tailoring |
| `src/generators/ats_matcher.py` | ATS keyword extraction and GraphRAG story matching |
| `src/generators/pdf_renderer.py` | Renders 2-page max PDF with tight margins |
| `src/generators/models.py` | Pydantic models for structured resume data |

### API & Web Files

| File | Purpose |
|------|---------|
| `src/shared/api_routes.py` | Shared FastAPI router for `/api/query`, `/api/chat-stream` |
| `src/web/app.py` | Canonical FastAPI application with Material Design 3 UI |
| `api/index.py` | Thin Vercel serverless wrapper |

### Configuration Files

| File | Purpose |
|------|---------|
| `src/config/providers.py` | Provider registry — maps use cases to providers/models |
| `settings.yaml` | GraphRAG configuration (models, chunking, entity extraction) |
| `config/litellm-config.yaml` | LiteLLM proxy model routing and fallback configuration |

---

## Summary

The magic of this system is **RAG (Retrieval-Augmented Generation)**:

1. **Retrieve** relevant information from the knowledge graph (using embeddings + GraphRAG)
2. **Augment** the prompt with that information
3. **Generate** accurate, contextual output (using LLM)

Without GraphRAG, the LLM would hallucinate or say "I don't know." With GraphRAG, it has the exact context it needs to answer accurately or tailor resumes precisely.

---

*Last updated: 2026-08-12*
