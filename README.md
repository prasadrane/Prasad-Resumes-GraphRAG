# Prasad Resumes - GraphRAG Knowledge Graph & Tailored Resume Generator

GraphRAG knowledge graph engine and automated ATS resume generator built over Prasad Rane's master resume and story bank content. Powered primarily by **OpenRouter API** (with direct Google Gemini AI Studio API fallback).

---

## Architecture & System Data Flow

![Architecture & System Data Flow](docs/architecture_diagram.png)

<details>
<summary><b>Click to expand detailed system pipeline workflow specification</b></summary>

1. **Input Preprocessing (`src/converters/`):** Parses raw input documents into canonical [`input/MASTER_RESUME.txt`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/input/MASTER_RESUME.txt) & [`03-Story-Bank.txt`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/input/03-Story-Bank.txt).
2. **GraphRAG Indexing Engine (`graphrag index`):** Extracts entities, relationships, communities, and stores embeddings in LanceDB (`output/lancedb`) & Parquet tables.
3. **Primary LLM Gateway (`src/query/serverless_gateway.py`):** Routes requests primarily to **OpenRouter API**, with automatic failover to **Google Gemini AI Studio API** (`GEMINI_API_KEY` / `GRAPHRAG_API_KEY`).
4. **ATS Resume & PDF Generator (`src/generators/`):** Extracts ATS keywords from target job descriptions, assembles tailored Markdown, and renders standard ATS-compliant PDFs via ReportLab (`Prasad_Rane_Resume.pdf`).
5. **FastAPI Web UI & Chatbot (`src/web/` & `api/index.py`):** Single-page Material Design 3 interface featuring ATS Resume Tailoring, raw content editor, and interactive GraphRAG Q&A Chatbot.

</details>

---

## Features

### 1. ATS Resume Tailoring & Rule-Based PDF Generator
- Input target company name and paste job description to synthesize keyword-optimized resumes.
- Automatically extracts ATS keywords, formats bold phrasing caps (<20%), and outputs raw text.
- Renders standard ATS-compliant PDF (`Prasad_Rane_Resume.pdf`) meeting tight margins (`0.55"` left/right, `0.45"` top/bottom), left alignment, clickable links, and a strict 2-page maximum constraint.
- Inline PDF Preview Drawer with interactive raw text Markdown editor and manual PDF download.

### 2. GraphRAG AI Chatbot (Ask Me Questions)
- Interactive Q&A interface powered by Prasad's GraphRAG knowledge graph.
- Dual Query Modes:
  - **Local Context:** Detailed experience, specific metric breakdowns, and technical stack details.
  - **Global Summary:** High-level executive summaries and thematic overviews.
- Interactive action chips for one-click sample questions.
- Formatted Markdown responses with bullet lists, bold highlights, code blocks, clear chat reset, and one-click copy to clipboard.

---

## Configuration & Environment Variables

Create a `.env` file in the project root directory:

```env
# Primary LLM Provider (OpenRouter API)
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_api_key_here

# Fallback LLM Provider (Google Gemini AI Studio API)
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## Quick Start Setup

### 1. Activate Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Launch Web UI (FastAPI Server)
```powershell
python src/cli.py ui
# Or directly: python scripts/run_ui.py
```
Open **http://127.0.0.1:8000** in your browser.

### 3. Generate Tailored Resume via CLI
```powershell
python src/cli.py generate --company <Company_Name> --jd-file <Path_To_JD.txt>
```

### 4. Query Knowledge Graph via CLI
```powershell
python src/cli.py query --mode local "What AWS technologies did Prasad use?"
```

### 5. Build or Re-Index Knowledge Graph
```powershell
python -m graphrag index --root .
```

### 6. Run Unit Test Suite
```powershell
python -m unittest discover -s tests
```

---

## Vercel Serverless Deployment

Deploy to **Vercel Free Tier** using FastAPI (`api/index.py`):

```powershell
vercel --prod
```

Ensure `OPENROUTER_API_KEY` and `GEMINI_API_KEY` are configured in Vercel project environment variables.
