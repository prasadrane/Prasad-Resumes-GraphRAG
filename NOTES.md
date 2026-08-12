# NOTES.md - Session Continuity

## 🎯 Current State

**LLM Provider:** Alibaba Cloud Token Plan (Anthropic-compatible endpoint)
- **Chatbot:** `qwen3.6-flash` (fast, ~10-20s streaming)
- **Resume Generation:** `qwen3.7-plus` (quality, ~3m 45s)
- **Endpoint:** `https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic/v1/messages`
- **API Key:** In `.env` as `ALIBABA_API_KEY`

**Performance Achieved:**
- Chatbot: ~10-20s (streaming) ✅
- Resume generation: ~3m 45s (within 3-5 min acceptable range) ✅

---

## ✅ Completed This Session

1. **Switched from OpenRouter/Gemini to Alibaba Cloud Token Plan**
   - Anthropic-compatible endpoint is faster than OpenAI-compatible
   - Response format has `thinking` blocks + `text` blocks (extract text only)

2. **Combined 2 LLM calls into 1 for resume tailoring**
   - `tailor_resume_with_llm_single_call()` in `resume_generator.py`
   - Prompt asks for both summary + bullets in one response
   - Parses response by `### SUMMARY:` and `### JOB N:` headers

3. **Increased timeouts to 5 minutes (300s)**
   - `resume_generator.py`: timeout=300 for LLM calls
   - `serverless_gateway.py`: aiohttp session timeout=300

4. **Fixed streaming for Anthropic-compatible endpoint**
   - Handles `event:` and `data:` lines
   - Extracts `text_delta` from `content_block_delta` events

---

## 📋 BACKLOG - Next Session

### 1. Fix "[object Object]" in Chat Response Description
- **Symptom:** Chat response shows "description [object Object]" repeatedly
- **Location:** Likely `src/shared/api_routes.py` or frontend `app.js`
- **Action:** Find where description is stringified incorrectly, ensure proper JSON serialization

### 2. Verify Vercel Compatibility
- **Question:** Will Alibaba Token Plan API work on Vercel serverless?
- **Answer:** YES - Vercel functions can call external APIs
- **Note:** No migration to Oracle needed unless user wants self-hosted
- **Action:** Document in README that Vercel deployment works with current setup

### 3. Flexible LLM/Embedding Architecture
- **Goal:** Easy plug-in/plug-out of different LLM models, embeddings, providers
- **Plan:**
  - Create `src/config/providers.py` with provider registry
  - Make `serverless_gateway.py` configurable via env vars
  - Support model selection per use-case (chat vs resume)
  - Document how to add new providers

### 4. Documentation Updates
- **README.md:** Update with Alibaba setup, non-technical explanations
- **Architecture.md:** Create detailed architecture doc explaining:
  - What is LLM, embeddings, GraphRAG (simple terms)
  - Data flow diagrams
  - How resume generation works
  - How chatbot works

### 5. Remove "(Planned near-term:...)" from Certifications
- **Location:** `MASTER_RESUME.md` CERTIFICATION section
- **Action:** Remove "(Planned near-term: AWS Certified Solutions Architect. Associate)" text

---

## 🔧 Key Technical Details

### Alibaba API Response Format
```json
{
  "content": [
    {"type": "thinking", "thinking": "..."},  // Skip this
    {"type": "text", "text": "actual response"}  // Use this
  ]
}
```

### Streaming Format (Anthropic SSE)
```
event:content_block_delta
data:{"type":"content_block_delta","delta":{"type":"text_delta","text":"token"}}
```
- Skip `thinking_delta` blocks, only yield `text_delta`

### File Locations
- `src/query/serverless_gateway.py` - LLM gateway (Alibaba/OpenRouter/Gemini)
- `src/generators/resume_generator.py` - Resume tailoring
- `src/llm/service.py` - LLM service wrapper
- `.env` - API keys (ALIBABA_API_KEY, etc.)

### Environment Variables
```bash
ALIBABA_API_KEY=sk-sp-...  # Token Plan key
ALIBABA_BASE_URL=https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic
```

---

## 🚀 How to Run

```bash
# Activate venv
.\venv\Scripts\Activate.ps1

# Start server
python src/cli.py ui

# Test
# Chatbot: POST http://localhost:3000/api/chat-stream
# Resume: POST http://localhost:3000/api/generate
```

---

## 📝 Session Log

**2026-08-12:**
- Switched to Alibaba Cloud Token Plan
- Fixed slow resume generation (was 675s → now 225s)
- Combined 2 LLM calls into 1
- Fixed Anthropic-compatible endpoint parsing
- User confirmed 3-5 min wait is acceptable for resume generation
