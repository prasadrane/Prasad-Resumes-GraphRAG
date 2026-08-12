"""
api_models.py — Shared Pydantic request models for both FastAPI apps.

Consumed by src/web/app.py (local UI server) and api/index.py (Vercel
serverless entrypoint) so the two apps expose one API contract. Handler
behavior stays environment-appropriate: the local app can write files via
txt_url, the serverless app renders from raw text only.
"""

from typing import Optional

from pydantic import BaseModel, Field


from typing import Literal


class QueryRequest(BaseModel):
    query: str = Field(..., description="Question for GraphRAG knowledge graph")
    mode: Literal["local", "global", "drift"] = Field(default="local", description="Query mode: 'local', 'global', or 'drift'")
    session_id: Optional[str] = Field(default=None, description="Session ID for conversation memory (auto-generated if not provided)")


class ResumeGenerationRequest(BaseModel):
    company: str = Field(..., description="Target company name")
    jd_text: str = Field(default="", description="Job description text")


class SaveEditRequest(BaseModel):
    txt_url: Optional[str] = Field(default=None, description="Relative URL or path to text file")
    raw_text: Optional[str] = Field(default=None, description="Updated raw resume text content")
    content: Optional[str] = Field(default=None, description="Updated raw resume text content (alias)")
    company: Optional[str] = Field(default="Tailored", description="Company name")
