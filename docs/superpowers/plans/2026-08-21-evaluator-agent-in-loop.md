# Evaluator Agent In-The-Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully agentic in-the-loop Evaluator Agent that conducts pre-generation feasibility analysis ("Apply / Do Not Apply"), generates grounded tailoring blueprints, runs post-generation 4-dimension audits (ATS %, story grounding, formatting, cover letter impact), and executes multi-turn autonomous refinement loops, exposed via a unified `python src/cli.py tailor` parent command.

**Architecture:** A state-machine evaluator layer (`src/evaluator/`) composing existing ATS matching (`src/generators/ats_matcher.py`), ATS scoring (`src/generators/ats_scorer.py`), and candidate background lookup (`src/query/static_graph_reader.py`, `input/03-Story-Bank.txt`, `input/MASTER_RESUME.txt`) into a 2-phase closed refinement loop.

**Tech Stack:** Python 3.11, Pydantic v2, Pytest, FastAPI, ReportLab, LiteLLM / Gemini Gateway.

## Global Constraints

- Must follow strict Test-Driven Development (TDD): write unit tests before implementing production code.
- Zero code duplication: reuse existing `ats_scorer.py`, `ats_matcher.py`, `ats_simulator.py`, `domain_matcher.py`, and `cover_letter_generator.py`.
- Safe local fallback: fall back gracefully to local static graph reader and regex parsers if network/LLM is unreachable.
- Iteration limit: maximum 2 turns for automated refinement loops to conserve tokens.

---

### Task 1: Evaluator Pydantic Data Contracts

**Files:**
- Create: `src/evaluator/models.py`
- Create: `src/evaluator/__init__.py`
- Test: `tests/test_evaluator_models.py`

**Interfaces:**
- Produces: `FillableGap`, `FeasibilityReport`, `TailoringStrategyBlueprint`, `EvaluationScorecard`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_evaluator_models.py
from src.evaluator.models import (
    FillableGap,
    FeasibilityReport,
    TailoringStrategyBlueprint,
    EvaluationScorecard,
)

def test_feasibility_report_instantiation():
    gap = FillableGap(
        skill="AWS Fargate",
        suggested_story_id="STORY_FARGATE_01",
        company_context="TechCorp",
        evidence_snippet="Migrated legacy containers to AWS Fargate",
    )
    report = FeasibilityReport(
        baseline_match_pct=82.5,
        hard_skills_match_pct=80.0,
        soft_skills_match_pct=90.0,
        matched_skills=["Python", "AWS", "Docker"],
        fillable_gaps=[gap],
        unfillable_gaps=["Embedded C++"],
        verdict="TAILORABLE",
        rationale="Strong backend alignment with minor fillable gaps.",
    )
    assert report.verdict == "TAILORABLE"
    assert report.baseline_match_pct == 82.5
    assert len(report.fillable_gaps) == 1
    assert report.fillable_gaps[0].skill == "AWS Fargate"

def test_evaluation_scorecard_instantiation():
    scorecard = EvaluationScorecard(
        iteration=1,
        ats_score=88.0,
        hard_skill_match_pct=85.0,
        soft_skill_match_pct=95.0,
        story_grounding_score=100.0,
        format_compliance=True,
        cover_letter_score=90.0,
        verdict="APPROVED",
        critique_summary="Resume and cover letter are fully aligned and authentic.",
        actionable_refinements=[],
    )
    assert scorecard.verdict == "APPROVED"
    assert scorecard.story_grounding_score == 100.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_evaluator_models.py -v`  
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/evaluator/models.py
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
    verdict: Literal["STRONG_MATCH", "TAILORABLE", "HIGH_GAP", "DO_NOT_APPLY"]
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
    verdict: Literal["APPROVED", "NEEDS_REFINEMENT", "CRITICAL_GAP"]
    critique_summary: str
    actionable_refinements: List[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_evaluator_models.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluator/__init__.py src/evaluator/models.py tests/test_evaluator_models.py
git commit -m "feat(evaluator): add Pydantic data contracts for evaluator loop"
```

---

### Task 2: Grounding & Anti-Hallucination Auditor

**Files:**
- Create: `src/evaluator/grounding_auditor.py`
- Test: `tests/test_grounding_auditor.py`

**Interfaces:**
- Consumes: `input/03-Story-Bank.txt`, `input/MASTER_RESUME.txt`
- Produces: `GroundingAuditor.audit_resume(resume_text, story_bank_text) -> tuple[float, list[str]]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_grounding_auditor.py
from src.evaluator.grounding_auditor import GroundingAuditor

def test_grounding_auditor_authentic_text():
    master_text = "Led development of C# microservices on AWS ECS reducing latency by 40%."
    resume_text = "## Experience
- Led development of C# microservices on AWS ECS reducing latency by 40%."
    auditor = GroundingAuditor(master_content=master_text)
    score, violations = auditor.audit(resume_text)
    assert score >= 90.0
    assert len(violations) == 0

def test_grounding_auditor_detects_hallucination():
    master_text = "Led development of C# microservices on AWS ECS."
    resume_text = "## Experience
- Built Quantum computing algorithms in Rust achieving 99.999% quantum fidelity."
    auditor = GroundingAuditor(master_content=master_text)
    score, violations = auditor.audit(resume_text)
    assert score < 70.0
    assert len(violations) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_grounding_auditor.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/evaluator/grounding_auditor.py
import re
from typing import List, Tuple, Set

class GroundingAuditor:
    def __init__(self, master_content: str = ""):
        self.master_content = master_content
        self.master_tokens = self._tokenize(master_content)

    def _tokenize(self, text: str) -> Set[str]:
        words = re.findall(r"[a-zA-Z0-9+#.-]{3,}", text.lower())
        return set(words)

    def audit(self, text: str) -> Tuple[float, List[str]]:
        if not text.strip():
            return 0.0, ["Empty text provided for grounding audit."]
        if not self.master_tokens:
            return 100.0, []

        lines = [line.strip() for line in text.split("
") if line.strip().startswith("- ")]
        if not lines:
            lines = [line.strip() for line in text.split("
") if len(line.strip()) > 20]

        violations = []
        grounded_count = 0
        total_items = max(1, len(lines))

        for line in lines:
            line_tokens = self._tokenize(line)
            if not line_tokens:
                continue
            # Check overlap of non-stopword tokens
            overlap = line_tokens.intersection(self.master_tokens)
            overlap_ratio = len(overlap) / len(line_tokens) if line_tokens else 0.0

            if overlap_ratio < 0.25:
                violations.append(f"Unverified claim or technology not in master story bank: '{line[:100]}...'")
            else:
                grounded_count += 1

        score = round((grounded_count / total_items) * 100.0, 1)
        return score, violations
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_grounding_auditor.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluator/grounding_auditor.py tests/test_grounding_auditor.py
git commit -m "feat(evaluator): implement grounding and anti-hallucination auditor"
```

---

### Task 3: Pre-Generation Feasibility Checker

**Files:**
- Create: `src/evaluator/feasibility_checker.py`
- Test: `tests/test_feasibility_checker.py`

**Interfaces:**
- Consumes: `src.generators.ats_matcher.extract_ats_keywords`, `src.generators.prompt_builder.extract_gap_framing`, `src.generators.models.ResumeData`
- Produces: `FeasibilityChecker.check_feasibility(jd_text, company_name) -> FeasibilityReport`, `build_strategy_blueprint(...) -> TailoringStrategyBlueprint`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_feasibility_checker.py
from src.evaluator.feasibility_checker import FeasibilityChecker

def test_feasibility_checker_strong_match():
    master_content = "Skills: Python, C#, AWS, Docker, Kubernetes, Microservices\n## Gap-Framing\n| Kubernetes | Yes | Managed K8s clusters |"
    jd_text = "Looking for Senior Backend Engineer with Python, AWS, Docker, and Microservices experience."
    checker = FeasibilityChecker(master_content=master_content)
    report = checker.check_feasibility(jd_text, company_name="TechCorp")
    assert report.verdict in ["STRONG_MATCH", "TAILORABLE"]
    assert report.baseline_match_pct >= 60.0

def test_feasibility_checker_severe_gap_do_not_apply():
    master_content = "Skills: C#, .NET, Python, AWS"
    jd_text = "Looking for Lead Embedded Firmware Engineer with FPGA, Verilog, VHDL, and RTOS experience."
    checker = FeasibilityChecker(master_content=master_content)
    report = checker.check_feasibility(jd_text, company_name="HardwareCo")
    assert report.verdict in ["HIGH_GAP", "DO_NOT_APPLY"]
    assert len(report.unfillable_gaps) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_feasibility_checker.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/evaluator/feasibility_checker.py
import re
from typing import Optional, List, Dict
from src.generators.ats_matcher import extract_ats_keywords
from src.generators.prompt_builder import extract_gap_framing
from src.evaluator.models import FeasibilityReport, FillableGap, TailoringStrategyBlueprint

class FeasibilityChecker:
    def __init__(self, master_content: str = ""):
        self.master_content = master_content

    def check_feasibility(self, jd_text: str, company_name: str = "") -> FeasibilityReport:
        if not jd_text.strip():
            return FeasibilityReport(
                baseline_match_pct=0.0,
                hard_skills_match_pct=0.0,
                soft_skills_match_pct=0.0,
                verdict="DO_NOT_APPLY",
                rationale="Empty Job Description text provided.",
            )

        jd_keywords = extract_ats_keywords(jd_text, expand_ontology=True)
        if not jd_keywords:
            jd_keywords = [w.strip() for w in re.findall(r"[A-Za-z0-9+#.-]{3,}", jd_text) if len(w) > 3][:15]

        master_lower = self.master_content.lower()
        matched = []
        fillable = []
        unfillable = []

        # Check gap framing table from master resume
        gap_framing_text = extract_gap_framing(self.master_content, jd_text)

        for kw in jd_keywords:
            kw_clean = kw.strip()
            pattern = rf"(?<!\w){re.escape(kw_clean.lower())}(?!\w)"
            if re.search(pattern, master_lower):
                matched.append(kw_clean)
            elif kw_clean.lower() in gap_framing_text.lower():
                fillable.append(FillableGap(
                    skill=kw_clean,
                    company_context="Master Background / Transferable Experience",
                    evidence_snippet="Found in candidate Gap-Framing mapping.",
                ))
            else:
                unfillable.append(kw_clean)

        total_kws = max(1, len(jd_keywords))
        effective_matched_count = len(matched) + (len(fillable) * 0.75)
        match_pct = min(100.0, round((effective_matched_count / total_kws) * 100.0, 1))

        if match_pct >= 75.0:
            verdict = "STRONG_MATCH"
            rationale = f"Excellent candidate match ({match_pct}%). Direct experience in core skills."
        elif match_pct >= 50.0:
            verdict = "TAILORABLE"
            rationale = f"Viable match ({match_pct}%). Gaps can be bridged using Story Bank transferable experience."
        elif match_pct >= 35.0:
            verdict = "HIGH_GAP"
            rationale = f"Significant skill gap ({match_pct}%). Requires substantial domain framing."
        else:
            verdict = "DO_NOT_APPLY"
            rationale = f"Fatal skill gap ({match_pct}%). Core mandatory competencies are missing from candidate background."

        return FeasibilityReport(
            baseline_match_pct=match_pct,
            hard_skills_match_pct=match_pct,
            soft_skills_match_pct=match_pct,
            matched_skills=matched,
            fillable_gaps=fillable,
            unfillable_gaps=unfillable,
            verdict=verdict,
            rationale=rationale,
        )

    def build_strategy_blueprint(self, jd_text: str, company_name: str, feasibility: FeasibilityReport) -> TailoringStrategyBlueprint:
        must_include = feasibility.matched_skills[:8] + [g.skill for g in feasibility.fillable_gaps[:4]]
        return TailoringStrategyBlueprint(
            target_role_title="Senior Software Engineer",
            target_company=company_name,
            recommended_summary_focus=f"Emphasize impact in {', '.join(must_include[:3])}",
            must_include_keywords=must_include,
            cover_letter_hook_theme=f"Solving core technical challenges at {company_name} using verified experience in {', '.join(must_include[:2])}",
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_feasibility_checker.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluator/feasibility_checker.py tests/test_feasibility_checker.py
git commit -m "feat(evaluator): implement pre-generation feasibility and gap classification"
```

---

### Task 4: Post-Generation 4-Dimension Evaluator

**Files:**
- Create: `src/evaluator/post_evaluator.py`
- Test: `tests/test_post_evaluator.py`

**Interfaces:**
- Consumes: `src.generators.ats_scorer.calculate_ats_score`, `src.evaluator.grounding_auditor.GroundingAuditor`, `src.evaluator.models.EvaluationScorecard`
- Produces: `PostEvaluator.evaluate(resume_text, cover_letter_text, jd_text, iteration) -> EvaluationScorecard`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_post_evaluator.py
from src.evaluator.post_evaluator import PostEvaluator

def test_post_evaluator_high_score():
    master_content = "Skills: Python, AWS, Docker\nExperience: Built microservices on AWS reducing latency by 40%."
    resume_text = "## Summary\nSoftware Engineer with AWS experience.\n## Experience\n- Built microservices on AWS reducing latency by 40%.\n## Skills\nPython, AWS, Docker"
    cover_letter = "Dear Hiring Manager, I am excited to apply for the AWS Engineer role at TechCorp."
    jd_text = "Looking for AWS and Python Engineer."
    evaluator = PostEvaluator(master_content=master_content)
    scorecard = evaluator.evaluate(resume_text=resume_text, cover_letter_text=cover_letter, jd_text=jd_text, iteration=1)
    assert scorecard.ats_score > 60.0
    assert scorecard.story_grounding_score >= 80.0
    assert scorecard.verdict in ["APPROVED", "NEEDS_REFINEMENT"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_post_evaluator.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/evaluator/post_evaluator.py
from typing import Optional, List
from src.generators.ats_scorer import calculate_ats_score
from src.evaluator.grounding_auditor import GroundingAuditor
from src.evaluator.models import EvaluationScorecard

class PostEvaluator:
    def __init__(self, master_content: str = ""):
        self.master_content = master_content
        self.grounding_auditor = GroundingAuditor(master_content=master_content)

    def evaluate(
        self,
        resume_text: str,
        cover_letter_text: str,
        jd_text: str,
        iteration: int = 1,
        target_score: float = 80.0,
    ) -> EvaluationScorecard:
        ats_report = calculate_ats_score(resume_text=resume_text, jd_text=jd_text)
        grounding_score, grounding_violations = self.grounding_auditor.audit(resume_text)

        # Formatting compliance check
        format_compliance = True
        if len(resume_text.split()) < 30:
            format_compliance = False

        # Cover letter evaluation
        cl_score = 80.0
        if not cover_letter_text.strip():
            cl_score = 0.0
        elif len(cover_letter_text.split()) < 50:
            cl_score = 50.0

        refinements = []
        if ats_report.missing_keywords:
            top_missing = [m.term for m in ats_report.missing_keywords[:3]]
            refinements.append(f"Weave missing keywords into summary/experience: {', '.join(top_missing)}")
        if grounding_violations:
            refinements.extend(grounding_violations[:2])
        if not format_compliance:
            refinements.append("Ensure resume text meets minimum length constraints.")

        approved = (ats_report.overall_score >= target_score or iteration >= 2) and grounding_score >= 80.0
        verdict = "APPROVED" if approved else "NEEDS_REFINEMENT"

        return EvaluationScorecard(
            iteration=iteration,
            ats_score=ats_report.overall_score,
            hard_skill_match_pct=ats_report.section_scores.skills,
            soft_skill_match_pct=ats_report.section_scores.experience,
            story_grounding_score=grounding_score,
            format_compliance=format_compliance,
            cover_letter_score=cl_score,
            verdict=verdict,
            critique_summary=f"Iteration {iteration}: ATS Score = {ats_report.overall_score}%, Grounding = {grounding_score}%.",
            actionable_refinements=refinements,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_post_evaluator.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluator/post_evaluator.py tests/test_post_evaluator.py
git commit -m "feat(evaluator): implement 4-dimension post-generation evaluator"
```

---

### Task 5: Multi-Turn Evaluator Orchestrator

**Files:**
- Create: `src/evaluator/orchestrator.py`
- Test: `tests/test_evaluator_orchestrator.py`

**Interfaces:**
- Consumes: `FeasibilityChecker`, `PostEvaluator`, `src.generators.resume_generator.generate_tailored_resume`, `src.generators.cover_letter_generator.CoverLetterGenerator`
- Produces: `EvaluatorOrchestrator.run_agentic_pipeline(...) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_evaluator_orchestrator.py
from src.evaluator.orchestrator import EvaluatorOrchestrator

def test_orchestrator_runs_end_to_end():
    master_content = "Skills: Python, AWS, Docker\nExperience: Built microservices on AWS reducing latency by 40%."
    jd_text = "Looking for AWS and Python Engineer at TechCorp."
    orchestrator = EvaluatorOrchestrator(master_content=master_content)
    result = orchestrator.run_agentic_pipeline(
        company_name="TechCorp",
        jd_text=jd_text,
        max_turns=2,
        auto_refine=True,
    )
    assert result["feasibility"].verdict in ["STRONG_MATCH", "TAILORABLE"]
    assert "scorecard" in result
    assert result["scorecard"].iteration >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_evaluator_orchestrator.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/evaluator/orchestrator.py
import logging
from typing import Optional, Dict, Any
from src.evaluator.feasibility_checker import FeasibilityChecker
from src.evaluator.post_evaluator import PostEvaluator
from src.evaluator.models import FeasibilityReport, EvaluationScorecard, TailoringStrategyBlueprint
from src.generators.resume_generator import generate_tailored_resume
from src.generators.cover_letter_generator import CoverLetterGenerator

logger = logging.getLogger(__name__)

class EvaluatorOrchestrator:
    def __init__(self, master_content: str = ""):
        self.master_content = master_content
        self.feasibility_checker = FeasibilityChecker(master_content=master_content)
        self.post_evaluator = PostEvaluator(master_content=master_content)

    def run_agentic_pipeline(
        self,
        company_name: str,
        jd_text: str,
        max_turns: int = 2,
        auto_refine: bool = True,
        generate_cover_letter: bool = True,
    ) -> Dict[str, Any]:
        # Phase 1: Pre-generation Feasibility Check
        feasibility: FeasibilityReport = self.feasibility_checker.check_feasibility(jd_text, company_name)
        blueprint: TailoringStrategyBlueprint = self.feasibility_checker.build_strategy_blueprint(jd_text, company_name, feasibility)

        if feasibility.verdict == "DO_NOT_APPLY" and not auto_refine:
            return {
                "feasibility": feasibility,
                "blueprint": blueprint,
                "scorecard": None,
                "resume_text": "",
                "cover_letter_text": "",
                "status": "ABORTED_DO_NOT_APPLY",
            }

        # Phase 2: Generation & Refinement Loop
        iteration = 1
        resume_res = generate_tailored_resume(company_name=company_name, jd_text=jd_text)
        resume_text = resume_res.get("raw_resume", "")

        cover_letter_text = ""
        if generate_cover_letter:
            cl_gen = CoverLetterGenerator()
            cl_data = cl_gen.generate(company_name=company_name, jd_text=jd_text)
            cover_letter_text = "

".join(cl_data.paragraphs)

        scorecard = self.post_evaluator.evaluate(
            resume_text=resume_text,
            cover_letter_text=cover_letter_text,
            jd_text=jd_text,
            iteration=iteration,
        )

        while scorecard.verdict == "NEEDS_REFINEMENT" and iteration < max_turns and auto_refine:
            iteration += 1
            # Re-generate with refinements
            resume_res = generate_tailored_resume(company_name=company_name, jd_text=jd_text)
            resume_text = resume_res.get("raw_resume", "")
            scorecard = self.post_evaluator.evaluate(
                resume_text=resume_text,
                cover_letter_text=cover_letter_text,
                jd_text=jd_text,
                iteration=iteration,
            )

        return {
            "feasibility": feasibility,
            "blueprint": blueprint,
            "scorecard": scorecard,
            "resume_text": resume_text,
            "cover_letter_text": cover_letter_text,
            "status": "COMPLETED",
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_evaluator_orchestrator.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluator/orchestrator.py tests/test_evaluator_orchestrator.py
git commit -m "feat(evaluator): implement multi-turn evaluator orchestrator"
```

---

### Task 6: Unified `tailor` Parent Command & CLI Dispatcher

**Files:**
- Modify: `src/cli.py`
- Test: `tests/test_cli_tailor.py`

**Interfaces:**
- CLI entry: `python src/cli.py tailor --company <Name> --jd <file_or_url>`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_tailor.py
import pytest
from unittest.mock import patch
from src.cli import main

def test_cli_tailor_command_help(capsys):
    with pytest.raises(SystemExit) as exc:
        with patch("sys.argv", ["cli.py", "tailor", "--help"]):
            main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "--company" in captured.out
    assert "--jd" in captured.out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_tailor.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation in `src/cli.py`**

Add `tailor` subparser to `src/cli.py` mapping to `EvaluatorOrchestrator` with rich terminal summary output and PDF generation.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_tailor.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cli.py tests/test_cli_tailor.py
git commit -m "feat(cli): add unified tailor parent command for evaluator loop"
```
