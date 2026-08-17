# Spec: Master Resume Review & Numbers Interrogation Prompt

**Date**: 2026-08-16  
**Status**: Approved  
**Target Location**: `prompts/master_resume_review_prompt.md`

---

## 1. Overview & Objective

The objective is to create a battle-tested, high-rigor Master Resume Review Prompt modeled after the evaluation standards of Top-Tech (FAANG/Tier-1) Principal Technical Recruiters and Senior Engineering Hiring Managers.

The prompt will:
1. Conduct an unsparing **6-Second Recruiter Red Flag Scan** to catch immediate skip triggers, eye-rolling clichés, and weak phrasing.
2. Run an exhaustive **Numbers Interrogation** across every bullet point, creating a structured metric discovery table that guides the candidate using the Google XYZ formula (`Accomplished [X] as measured by [Y], by doing [Z]`).
3. Perform an **ATS & Technical Architecture Alignment Audit** (supporting both standalone Master Resume auditing and optional Target Job Description priority mirroring).
4. Deliver an **Executive Scorecard & Top 5 High-Leverage Fixes** prioritizing the highest ROI updates.

---

## 2. Personas & Evaluation Criteria

### Persona 1: Top-Tech Principal Technical Recruiter
* **Screening Time**: 6 seconds per resume.
* **Focus Areas**: Visual scanning density, title progression, immediate clarity of impact, action verb strength, elimination of fluff/clichés (*"responsible for"*, *"worked on"*, *"assisted with"*), and ATS keyword parsability.

### Persona 2: Top-Tech Senior / Director of Engineering Hiring Manager
* **Focus Areas**: Deep architectural scope, ownership vs. maintenance, engineering trade-offs, system scalability, and unassailable quantified business/technical metrics.
* **Core Rule**: Strictly enforces Google's XYZ formula. No unquantified claims allowed.

---

## 3. Four-Stage Modular Output Architecture

### Stage 1: The 6-Second Recruiter Red Flag Scan
* **First Impression**: Instant gut reaction and clarity assessment.
* **Skip & Downlevel Triggers**: Specific factors that would cause a recruiter to skip the resume or downlevel the candidate from Senior/Staff to Mid-level.
* **Cliché & Passive Verb Extinction List**: Identification and redlining of weak, passive, or non-impactful words.

### Stage 2: The Numbers Interrogation (Metric Extraction Table)
* Scans 100% of resume bullet points.
* Generates a markdown table with columns:
  1. `Job / Section`
  2. `Bullet # & Original Text`
  3. `Metric Deficiency Category` (Scale, Latency, Cost, Reliability, Adoption, Revenue, Efficiency)
  4. `Surgical Discovery Questions` (targeted questions to unearth real metrics)
  5. `Google XYZ Template / Suggestion`
* Interactive hand-off: Allows the candidate to reply with raw metrics to generate instant bullet rewrites.

### Stage 3: ATS & Technical Alignment Audit
* **Hard Skills & Tech Stack Taxonomy**: Categorization and density analysis of core frameworks, cloud primitives, AI/ML tools, and distributed systems technologies.
* **JD Priority Mirroring (if target JD provided)**: Checks whether the top 3 core requirements of the job description are reflected in the top 3 focal bullets of the resume.

### Stage 4: Executive Scorecard & Action Plan
* **Scorecard (0–10 scale)**:
  - 6-Second Recruiter Clarity
  - Metric & Impact Rigor
  - Architectural Depth & Scope
  - ATS Keyword & Priority Alignment
* **Top 5 High-ROI Fixes**: Specific, ordered actions to move the resume to the top 1% candidate pool.

---

## 4. File Deliverables

1. `prompts/master_resume_review_prompt.md`: The complete, standalone reusable markdown prompt template with clear placeholder tags `[PASTE MASTER RESUME HERE]` and `[OPTIONAL: PASTE TARGET JOB DESCRIPTION HERE]`.
2. Direct presentation of the full prompt in chat for instant copy-pasting.
