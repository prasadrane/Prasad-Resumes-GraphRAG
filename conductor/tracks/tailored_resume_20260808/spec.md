# Specification: Tailored Resume & Rule-Based PDF Generation Engine

## Overview
This track introduces an automated tailored resume generator and consistent PDF renderer into the Prasad-Resumes-GraphRAG platform. Given a Job Description (JD) and Company Name, the system performs ATS keyword extraction, queries the GraphRAG knowledge graph to select and highlight matching technical achievements/stories, generates a structured `raw_resume.txt` with ATS-matched keywords marked in `**bold**`, and compiles a clean, ATS-compliant PDF resume (`Prasad_Rane_Resume.pdf`).

## Functional Requirements

### Feature 1: Tailored Resume Generation & ATS Keyword Analysis
1. **Input Interface:**
   - Command: `python src/cli.py generate --company <Company> [--jd-file <Path>]`
   - If `--jd-file` is not provided, prompt the user interactively in the CLI to paste the Job Description text.
2. **ATS Keyword Extraction & GraphRAG Matching:**
   - Extract key ATS skills, tools, domain competencies, and required experience from the Job Description.
   - Query GraphRAG (local/global) to retrieve Prasad's most relevant projects, metrics, and behavioral stories matching the JD keywords.
3. **Raw Resume Generation:**
   - Format tailored resume text according to standard Markdown section structures (`# Name`, `## SUMMARY`, `## SKILLS`, `## EXPERIENCE`, `## EDUCATION`).
   - Highlight matched ATS keywords in `**bold**` within bullet points and skills sections.
4. **Directory Storage Output:**
   - Output Path: `output/<MM-DD-YYYY>/<company_name>/raw_resume.txt` (e.g. `output/08-08-2026/Google/raw_resume.txt`)
   - Create directories automatically if they do not exist.

### Feature 2: Rule-Based Consistent PDF Resume Generation
1. **PDF Renderer Subsystem:**
   - Parse `raw_resume.txt` into structured section data.
   - Render a rule-based PDF using `ReportLab` (or Python PDF engine).
   - Apply clean, consistent typography (Helvetica/Arial), standard 0.5-0.75 in margins, section horizontal dividers, clean bullet alignment, and bold text rendering.
2. **Directory Storage Output:**
   - Output Path: `output/<MM-DD-YYYY>/<company_name>/Prasad_Rane_Resume.pdf`

## Non-Functional Requirements
- **ATS Compliance:** Single-column layout, standard headings, parseable fonts, no multi-column text tables or hidden graphic overlays.
- **Portability:** Works across Windows/Linux without external system binary requirements.
- **Test-Driven Development (TDD):** Full unit test suite under `tests/` covering ATS keyword extraction, directory path resolution, raw text formatting, and PDF rendering.

## Out of Scope
- Direct integration with job application job-board APIs.
- Manual visual drag-and-drop PDF design editors.
