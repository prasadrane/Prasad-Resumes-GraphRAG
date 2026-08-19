# Design Specification: Agentic Job Posting Ingestion & Evaluator-Optimizer Engine

> **Full Specification Document**: [`docs/superpowers/specs/2026-08-19-agentic-job-ingestion-and-resume-optimizer-design.md`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/docs/superpowers/specs/2026-08-19-agentic-job-ingestion-and-resume-optimizer-design.md)

---

## Summary of Planned Architecture

```mermaid
sequenceDiagram
    autonumber
    actor User as Candidate / User
    participant UI as Web UI / CLI
    participant Scraper as HTTP Scraper (src/scrapers)
    participant Gateway as LLM Gateway (src/gateway)
    participant Critic as Agentic Critic (src/agents/evaluator)
    participant Optimizer as Bullet Optimizer (src/agents/optimizer)
    participant PDF as PDF Renderer (src/generators)

    User->>UI: Submit Job URL (e.g. greenhouse.io/...)
    UI->>Scraper: Fetch & Sanitize HTML
    Scraper->>Gateway: Extract Structured JobPosting Model
    Gateway-->>Scraper: JobPosting(company, title, requirements, skills)
    
    UI->>Optimizer: Generate Base Draft 1 Resume
    loop Agentic Evaluator-Optimizer Loop (Max 3 iterations)
        Optimizer->>Critic: Evaluate Resume vs JobPosting
        Critic-->>UI: Stream Event: Score Breakdown & Keyword Gaps
        alt ATS Score >= 90% & Page Budget Compliant
            Critic-->>Optimizer: Converged (Exit Loop)
        else ATS Score < 90%
            Critic-->>Optimizer: Identified Gaps & Target Bullet Recommendations
            Optimizer->>Gateway: Fact-Grounded Bullet Rewriting (Zero Hallucination)
            Gateway-->>Optimizer: Refined Job Bullets
            Optimizer-->>UI: Stream Event: Iteration Diff & Reason Log
        end
    end

    Optimizer->>PDF: Render Tailored PDF & Raw Text
    PDF-->>UI: Downloadable Prasad_Rane_Resume.pdf + Optimization Audit Report
```

## Key Capabilities

1. **Job Ingestion Engine (`src/scrapers/`)**: Scrapes job postings directly from URLs (Greenhouse, Lever, Ashby, Workable, etc.) and uses LLM gateway structured extraction into a typed `JobPosting` model.
2. **Autonomous Evaluator-Optimizer Agent (`src/agents/`)**: Multi-step Critic-Refiner loop that scores keyword alignment, impact metrics, bolding density (<20%), and 2-page budget, iteratively rewriting bullets until ATS score >= 90%.
3. **Live Streaming UI/UX (`api/index.py` & Web UI)**: Real-time Server-Sent Events (SSE) stream displaying live thinking logs, pulsing status badges, animated metric radial gauges, and before/after iteration diffs.
4. **CLI Integration (`src/cli.py`)**: `python src/cli.py generate --url <JOB_URL> --agentic` with animated Rich terminal interface.
5. **Anti-Hallucination Guardrails**: Strictly grounds all rewrites in candidate facts from `input/MASTER_RESUME.txt` and the GraphRAG graph.
