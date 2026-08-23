---
name: generating-tailored-resume
description: Use when user wants to generate a tailored resume or cover letter for a specific job posting — triggered by phrases like "apply to", "tailor resume for", "generate resume", "cover letter for", or when a JD (job description) is provided
---

# Generating Tailored Resume & Cover Letter

CLI-driven workflow to produce ATS-optimized resumes and cover letters from a job description, using the GraphRAG knowledge graph and NLP keyword matching.

## Prerequisites

- `.env` with API keys configured (`OPENROUTER_API_KEY`, `GEMINI_API_KEY`)
- GraphRAG index built (`./venv/Scripts/python.exe src/cli.py index`) — improves context retrieval quality
- **LiteLLM proxy** — required for resume generation only; cover letter works without it

## Critical: Always Use Venv Python

All CLI commands MUST run through the project virtual environment. System Python will not find `litellm` or other dependencies.

```bash
# ✅ CORRECT — use venv Python
./venv/Scripts/python.exe src/cli.py <command>

# ❌ WRONG — system Python will fail
python src/cli.py <command>
```

## Starting the LiteLLM Proxy (Resume Generation Only)

The proxy must be running on port 8002 before generating resumes. Cover letter generation does NOT need the proxy.

```bash
# Start proxy (must use venv Python)
./venv/Scripts/python.exe src/cli.py proxy &

# Or directly:
./venv/Scripts/litellm.exe --config config/litellm-config.yaml --port 8002 &
```

**Verify proxy is ready** (takes ~10s to start):
```bash
curl -s http://localhost:8002/health/readiness
# Should return: {"status":"healthy",...}
```

**If port 8002 is already in use**: another proxy instance is already running — proceed without restarting.

## Workflow

### Step 1: Collect Job Description

Three input modes:

| Mode | Flag | Example |
|------|------|---------|
| **File** | `--jd-file <path>` | `jd.txt` |
| **URL** | `--url <url>` or `--jd-url <url>` | Auto-scrapes JD from URL |
| **Paste** | (stdin) | User pastes JD text directly |

Also collect:
- **Company name** — auto-inferred from `--url`; must be provided explicitly for file/paste modes
- **Role title** — defaults to "Senior Software Engineer"; override with `--role`

### Step 2: Generate Cover Letter (No Proxy Needed)

Generate cover letter FIRST — it doesn't require the proxy, so you can start immediately while proxy spins up in the background.

```bash
./venv/Scripts/python.exe src/cli.py cover-letter \
  --company "<Company>" \
  --role "<Role>" \
  --jd-file <path>
```

Output (date-stamped directory, same as resume):
- `output/MM-DD-YYYY/<Company>/cover_letter.txt` — text source
- `output/MM-DD-YYYY/<Company>/cover_letter.pdf` — rendered PDF

### Step 3: Start Proxy & Generate Resume

Start the proxy in background, wait for health check, then generate resume:

```bash
# Start proxy (skip if already running)
./venv/Scripts/python.exe src/cli.py proxy &

# Wait for it (~10s)
sleep 10
curl -s http://localhost:8002/health/readiness

# Generate resume
./venv/Scripts/python.exe src/cli.py generate --company "<Company>" --jd-file <path>
```

**Agentic mode** (evaluator-optimizer loop for higher ATS scores):
```bash
./venv/Scripts/python.exe src/cli.py generate --company "<Company>" --jd-file <path> \
  --agentic --min-score 90 --max-iterations 2
```

### Step 4: Report Results

Output goes to a date-stamped directory: `output/MM-DD-YYYY/<Company>/`

Print a summary:
- Resume PDF path (`Prasad_Rane_Resume.pdf`)
- Resume text source (`raw_resume.txt`)
- Cover letter PDF (`cover_letter.pdf`, if generated)
- Cover letter text (`cover_letter.txt`, if generated)
- ATS match score (printed to stdout by generate command)

## Quick Reference

| Command | Purpose |
|---------|---------|
| `./venv/Scripts/python.exe src/cli.py generate --company X --jd-file Y` | Tailored resume (text + PDF) |
| `./venv/Scripts/python.exe src/cli.py generate ... --agentic` | Multi-iteration ATS optimization |
| `./venv/Scripts/python.exe src/cli.py cover-letter --company X --jd-file Y` | Tailored cover letter |
| `./venv/Scripts/python.exe src/cli.py proxy` | Start LiteLLM proxy (port 8002) |
| `./venv/Scripts/python.exe src/cli.py index` | Build/update GraphRAG knowledge graph |

## Common Mistakes

- **Using system Python instead of venv** — `python src/cli.py proxy` will fail with "LiteLLM CLI not found". Always use `./venv/Scripts/python.exe`.
- **Not waiting for proxy health** — proxy takes ~10s to start. Resume generation will fail if proxy isn't ready. Check `/health/readiness` before proceeding.
- **Forgetting `--company`** with file/paste input — company is only auto-inferred from `--url`
- **Missing JD** — `--jd-file` must be plain text; PDF/Word files must be converted first (`./venv/Scripts/python.exe src/cli.py convert --source <dir>`)
- **Starting proxy for cover letter** — unnecessary; cover letter uses static graph reader, no LLM calls needed

## Cover Letter Style Rules

The cover letter generator enforces these style rules:

- **No em dashes or hyphens** — all compound words are expanded (e.g., "offline-first" becomes "offline capable", "cross-functional" becomes "collaborative")
- **Humanized tone** — conversational and natural, avoiding corporate jargon and buzzwords
- The `_sanitize()` method in `CoverLetterGenerator` handles these transformations automatically
