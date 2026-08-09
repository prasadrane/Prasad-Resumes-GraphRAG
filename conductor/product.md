# Initial Concept
Build and query a GraphRAG knowledge graph over Prasad Rane's master resume and behavioral story bank.

# Product Vision
An evolving, extensible AI-powered knowledge retrieval platform designed for Prasad Rane to conduct high-speed interview preparation, behavioral story retrieval, and custom resume tailoring by querying a structured GraphRAG knowledge graph built from 47+ resume variations and story bank content. The project is designed for continuous iterative feature expansion as usage grows over time.

# Target Audience
- **Primary User:** Prasad Rane (Self) for interview prep, story retrieval, STAR response synthesis, and job-specific resume tailoring.
- **Secondary Users:** Technical Recruiters, Hiring Managers, and AI Screening Agents seeking deep insights into technical experience and achievements.

# Core Capabilities & Roadmap
1. **Local & Global Graph Queries:** Fast, accurate retrieval of specific technical experience (local) and high-level thematic profiles (global).
2. **Structured Resume & Story Bank Extraction:** Automatic extraction and alignment of STAR behavioral stories and custom resume sections.
3. **Interactive Q&A & Conversational Search:** Sub-second query execution backed by LRU caching and LanceDB vector search, featuring simulated typewriter streaming, typing indicators, and source entity chips.
4. **Stepwise progress updates:** Real-time generation feedback via an SSE-driven progress stepper UI, eliminating blocking interface freezes.
5. **Evolving Extensibility:** Modular architecture built to continuously incorporate new features, analysis pipelines, and custom automation workflows as project usage expands.

# Key Success Metrics
- **Zero Quota / Rate-Limit Stalls:** 100% index and query availability using LiteLLM proxy multi-model fallback cascades.
- **High Graph Density & Accuracy:** Precise entity and relationship extraction across 10 custom domain types.
- **Sub-Second Query Performance:** Instant lookup for repeated and cached queries.
- **Iterative Growth:** Modular code structure allowing rapid addition of new commands, integrations, and tools.
