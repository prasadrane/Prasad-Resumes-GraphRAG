# Evaluator Agent In-The-Loop Design Specification

**Date:** 2026-08-21  
**Status:** Approved  
**Topic:** Fully Agentic Evaluator In-The-Loop for ATS Resume & Cover Letter Generation  

---

## 1. Overview & Objectives

This specification defines the architecture, data models, logic flow, and integration points for an **Evaluator Agent In-The-Loop** within Prasad-Resumes-GraphRAG. 

The system provides:
1. **Pre-Generation Feasibility Check & Strategy Blueprint**:
   - Ingests target Job Descriptions (raw text or scraped URLs).
   - Computes dynamic match metrics (Hard Skills, Soft Skills, Tools).
   - Cross-references requirements with candidate project stories (input/03-Story-Bank.txt, input/MASTER_RESUME.txt, and GraphRAG knowledge graph).
   - Classifies gaps into **Fillable Gaps** (grounded in candidate experience) vs **Unfillable Gaps** (no candidate backing).
   - Recommends whether to apply or issue a DO_NOT_APPLY verdict if fatal gaps exist.
2. **Grounded Generation Guidance**:
   - Passes a structured TailoringStrategyBlueprint into the generator to weave specific verified STAR stories and relevant keywords into the resume and cover letter.
3. **Post-Generation 4-Dimension Audit**:
   - **ATS Match %**: Detailed keyword hit/miss count and match score.
   - **Story Grounding / Anti-Hallucination**: Verifies 0 hallucinated metrics or fabricated technologies; all claims traceable to story bank or master resume.
   - **Formatting & Page Budget Compliance**: Verifies bullet bolding cap (<20% chars, max 3 phrases), length constraint (2 pages max), contact header completeness.
   - **Cover Letter Impact**: Tone, value proposition, relevance to company mission and JD requirements.
4. **Autonomous Multi-Turn Refinement Loop**:
   - If the scorecard identifies fixable gaps and iteration limit (default max 2 refinement turns) has not been reached, the Evaluator generates precise delta edit instructions back to the generator.
   - Terminates when the scorecard passes or reaches max turns, outputting a comprehensive EvaluationScorecard alongside the generated artifacts.

---

## 2. System Architecture & Workflow

`
                     ┌──────────────────────────────────────┐
                     │           Target Job Description     │
                     └───────────────────┬──────────────────┘
                                         │
                                         ▼
                     ┌──────────────────────────────────────┐
                     │        Phase 1: Pre-Generation      │
                     │         Feasibility & Strategy       │
                     │  - Extract JD skills & requirements  │
                     │  - Hybrid scan: Story Bank + GraphRAG│
                     │  - Compute baseline match %          │
                     │  - Classify Fillable vs True Gaps    │
                     └───────────────────┬──────────────────┘
                                         │
                 ┌───────────────────────┴────────────────────────┐
                 │                                                │
   [Critical Unfillable Gap]                              [Viable Fit]
                 │                                                │
                 ▼                                                ▼
┌──────────────────────────────────────┐         ┌─────────────────────────────────┐
│     'Do Not Apply' Recommendation    │         │ Tailoring Strategy Blueprint    │
│  - Explanation of critical gaps      │         │ - Mapped story bullets per role │
│  - Missing must-have competencies    │         │ - Target keywords to weave in   │
│  - Option to override and proceed    │         │ - Cover letter hook & themes    │
└──────────────────────────────────────┘         └────────────────┬────────────────┘
                                                                  │
                                                                  ▼
                                                 ┌─────────────────────────────────┐
                                                 │       Generator Agent           │
                                                 │  - Synthesizes Tailored Resume  │
                                                 │  - Synthesizes Cover Letter     │
                                                 └────────────────┬────────────────┘
                                                                  │
                                                                  ▼
                                                 ┌─────────────────────────────────┐
                                                 │        Phase 2: Post-Generation │
                                                 │          4-Dimension Audit      │
                                                 │  1. ATS Keyword & Match %       │
                                                 │  2. Story Grounding (0 Halluc.) │
                                                 │  3. Page Budget & Formatting    │
                                                 │  4. Cover Letter Impact         │
                                                 └────────────────┬────────────────┘
                                                                  │
                                     ┌────────────────────────────┴───────────────────────────┐
                                     │                                                        │
                      [Score < Target & Turns < Max]                          [Passes Audit / Max Turns / Approved]
                                     │                                                        │
                                     ▼                                                        ▼
                    ┌─────────────────────────────────┐                     ┌───────────────────────────────────┐
                    │     Evaluator Refinement Prompt │                     │ Final Evaluation Scorecard & Artifacts│
                    │  - Specific bullet replacements │                     │ - ATS Match %, Gaps, Strengths   │
                    │  - Grounded story adjustments   │                     │ - Verified Resume & Cover Letter │
                    └────────────────┬────────────────┘                     │ - PDF / LaTeX / Typst renders    │
                                     │                                      └───────────────────────────────────┘
                                     └───────────► (Loop back to Generator)
`

---

## 3. Module Structure & File Placement

The evaluator logic lives under src/evaluator/, cleanly composed with existing generators:

`
src/
├── evaluator/
│   ├── __init__.py
│   ├── models.py                  # Pydantic data schemas
│   ├── feasibility_checker.py     # Pre-generation match & gap classification
│   ├── grounding_auditor.py       # Anti-hallucination & story verification
│   ├── post_evaluator.py          # 4-dimension scoring & delta generator
│   └── orchestrator.py            # Multi-turn state machine orchestrator
`

### Module Responsibilities & Reused Components:

1. **src/evaluator/models.py**:
   - Defines FillableGap, FeasibilityReport, TailoringStrategyBlueprint, and EvaluationScorecard.
2. **src/evaluator/feasibility_checker.py**:
   - Reuses src.generators.ats_matcher.extract_ats_keywords and src.generators.sme_ontology.SMEOntology.
   - Reuses src.query.static_graph_reader.search_static_resume and src.generators.prompt_builder.extract_gap_framing.
   - Analyzes candidate background to separate fillable skills from unfillable hard requirements.
3. **src/evaluator/grounding_auditor.py**:
   - Inspects generated bullets against master resume and story bank tokens.
   - Flags any invented metrics, fake company experiences, or unbacked tool claims.
4. **src/evaluator/post_evaluator.py**:
   - Reuses src.generators.ats_scorer.calculate_ats_score and src.generators.ats_simulator.ATSSimulator.
   - Produces 4-dimension scorecard and generates actionable refinement instructions.
5. **src/evaluator/orchestrator.py**:
   - Coordinates end-to-end multi-turn loop with safety turn caps (max_turns=2).

---

## 4. Data Contracts & Pydantic Schemas

`python
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field

class FillableGap(BaseModel):
    skill: str
    suggested_story_id: Optional[str] = None
    company_context: str
    evidence_snippet: str

class FeasibilityReport(BaseModel):
    baseline_match_pct: float
    hard_skills_match_pct: float
    soft_skills_match_pct: float
    matched_skills: List[str] = Field(default_factory=list)
    fillable_gaps: List[FillableGap] = Field(default_factory=list)
    unfillable_gaps: List[str] = Field(default_factory=list)
    verdict: Literal['STRONG_MATCH', 'TAILORABLE', 'HIGH_GAP', 'DO_NOT_APPLY']
    rationale: str

class TailoringStrategyBlueprint(BaseModel):
    target_role_title: str
    target_company: str
    recommended_summary_focus: str
    role_story_mappings: Dict[str, List[str]] = Field(default_factory=dict)
    must_include_keywords: List[str] = Field(default_factory=list)
    cover_letter_hook_theme: str

class EvaluationScorecard(BaseModel):
    iteration: int
    ats_score: float
    hard_skill_match_pct: float
    soft_skill_match_pct: float
    story_grounding_score: float  # 0.0 - 100.0%
    format_compliance: bool
    cover_letter_score: float     # 0.0 - 100.0%
    verdict: Literal['APPROVED', 'NEEDS_REFINEMENT', 'CRITICAL_GAP']
    critique_summary: str
    actionable_refinements: List[str] = Field(default_factory=list)
`

---

## 5. CLI & Web API Integration

### Unified Parent CLI Command:
The entire pipeline is wrapped in a single, intuitive parent command that abstracts all inner details:
```powershell
# All-In-One Unified Agent Command (handles URL or local file, pre-eval, tailoring, audit loop, cover letter & PDF builds):
python src/cli.py tailor --company "Stripe" --jd input/target_jd.txt
# Or with a live job URL:
python src/cli.py tailor --company "Stripe" --jd "https://jobs.stripe.com/senior-backend-engineer"

# Optional fine-tuning flags (default is full auto):
# --check-only      : Run only pre-generation feasibility & gap report without generating files
# --interactive     : Pause at evaluation checkpoints for terminal review
# --max-turns <N>   : Set maximum refinement turns (default: 2)
# --no-cover-letter : Generate resume only
```

### Web API Endpoints:
- POST /api/evaluator/feasibility: Evaluates JD and returns FeasibilityReport.
- POST /api/evaluator/agentic-generate-stream: Server-Sent Events (SSE) stream reporting step-by-step agent thoughts, feasibility check, initial draft, post-audit scorecard, and refinement iterations.

---

## 6. Error Handling & Guardrails

- **Zero-Crash Local Fallback**: When LLM gateway or GraphRAG is unavailable, static graph reader and local regex parsers ensure uninterrupted evaluation.
- **Iteration Limits**: Hard cap of max_turns = 2 prevents infinite loops and token runaway.
- **Circuit Breaker Resiliency**: Gateway router handles LLM provider 429s automatically with Alibaba -> Gemini -> OpenRouter failover.

---

## 7. Test-Driven Development (TDD) Plan

1. **	ests/test_feasibility_checker.py**:
   - Verifies baseline match percentage on matched vs mismatched JDs.
   - Verifies separation of fillable gaps (in story bank) vs unfillable gaps.
   - Verifies DO_NOT_APPLY verdict on severe mismatch scenarios.
2. **	ests/test_grounding_auditor.py**:
   - Verifies audit passes on authentic bullets from MASTER_RESUME.txt.
   - Verifies audit detects and flags fabricated numbers or unmentioned technologies.
3. **	ests/test_post_evaluator.py**:
   - Verifies composite 4-dimension scoring calculation.
   - Verifies generation of concrete refinement instructions when scores are below threshold.
4. **	ests/test_evaluator_orchestrator.py**:
   - Tests end-to-end multi-turn loop and termination conditions.
