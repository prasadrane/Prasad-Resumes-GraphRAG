# Implementation Plan: Tailored Resume & Rule-Based PDF Generation Engine

## Phase 1: Environment & Dependencies Setup
- [x] Task: Add PDF & ReportLab generation libraries to requirements.txt
    - [x] Add `reportlab` dependency to `requirements.txt`
    - [x] Verify environment installation and import readiness
- [x] Task: Conductor - User Manual Verification 'Phase 1: Environment & Dependencies Setup' (Protocol in workflow.md)

## Phase 2: ATS Keyword Analyzer & Generator Subsystem (Feature 1)
- [x] Task: Implement ATS keyword extraction & GraphRAG query matcher (`src/generators/ats_matcher.py`)
    - [x] Write unit tests in `tests/test_ats_matcher.py` for keyword extraction and matching
    - [x] Implement `extract_ats_keywords(jd_text)` and `match_graphrag_stories(keywords)`
- [x] Task: Implement raw resume builder & keyword bolding (`src/generators/resume_generator.py`)
    - [x] Write unit tests in `tests/test_resume_generator.py` for raw resume formatting and `**bold**` keyword injection
    - [x] Implement `generate_raw_resume(company_name, jd_text)` and date-based output path resolver `get_output_dir(company_name)`
    - [x] Ensure output creates `output/<MM-DD-YYYY>/<company_name>/raw_resume.txt`
- [x] Task: Conductor - User Manual Verification 'Phase 2: ATS Keyword Analyzer & Generator Subsystem (Feature 1)' (Protocol in workflow.md)

## Phase 3: Rule-Based PDF Generator Subsystem (Feature 2)
- [x] Task: Implement PDF renderer using ReportLab (`src/generators/pdf_renderer.py`)
    - [x] Write unit tests in `tests/test_pdf_renderer.py` for raw text parsing and PDF canvas layout creation
    - [x] Implement `render_pdf_resume(raw_resume_path, output_pdf_path)` with ATS-compliant typography, section lines, and bold rendering
    - [x] Output `output/<MM-DD-YYYY>/<company_name>/Prasad_Rane_Resume.pdf`
- [x] Task: Conductor - User Manual Verification 'Phase 3: Rule-Based PDF Generator Subsystem (Feature 2)' (Protocol in workflow.md)

## Phase 4: CLI Integration, End-to-End Testing & Verification
- [x] Task: Integrate `generate` command into unified CLI (`src/cli.py`)
    - [x] Write unit tests in `tests/test_cli.py` for `generate` subcommand and interactive JD prompt
    - [x] Add `generate` subcommand to `src/cli.py` with `--company` and optional `--jd-file` arguments
- [x] Task: Perform end-to-end test execution and verification
    - [x] Execute `python -m unittest discover -s tests` to verify 100% test pass rate
    - [x] Test sample resume generation for a test job description
- [x] Task: Conductor - User Manual Verification 'Phase 4: CLI Integration, End-to-End Testing & Verification' (Protocol in workflow.md)
