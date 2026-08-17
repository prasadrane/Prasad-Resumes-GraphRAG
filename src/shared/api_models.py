"""
api_models.py — Shared Pydantic request models for both FastAPI apps.

Consumed by src/web/app.py (local UI server) and api/index.py (Vercel
serverless entrypoint) so the two apps expose one API contract. Handler
behavior stays environment-appropriate: the local app can write files via
txt_url, the serverless app renders from raw text only.
"""

import re
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from typing import Literal


# Regex: common script and delimiter injection patterns (HTML/JS/eval)
_INJECTION_RE = re.compile(
    r"""
        ;.*--|
        javascript:|
        on\w+\s*=|
        <script|</script>|
        eval\s*\(|exec\s*\(
    """,
    re.IGNORECASE | re.X,
)

_MODE_PATTERN = re.compile(r"^(local|global|drift)$")


class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Question for GraphRAG knowledge graph",
    )
    mode: Literal["local", "global", "drift"] = Field(
        default="local",
        description="Query mode: 'local', 'global', or 'drift'",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for conversation memory (auto-generated if not provided)",
    )

    @model_validator(mode="before")
    @classmethod
    def _validate(cls, values):
        """Sanitise and constrain fields before validation."""
        if isinstance(values, dict):
            q = values.get("query")
            if q is not None:
                q = str(q).strip()
                # Reject injection patterns early with a descriptive error
                if _INJECTION_RE.search(q):
                    raise ValueError(
                        "Query contains suspicious characters that look like injection attempts"
                    )
                values["query"] = q

            m = values.get("mode")
            if m is not None:
                m_clean = str(m).lower().strip()
                if _MODE_PATTERN.match(m_clean):
                    values["mode"] = m_clean
                else:
                    raise ValueError(
                        f"mode must be one of: local, global, drift — got {m!r}"
                    )
        return values


class ResumeGenerationRequest(BaseModel):
    company: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Target company name",
    )
    jd_text: str = Field(
        default="",
        description="Job description text",
    )

    @model_validator(mode="after")
    def _validate(self):
        """Validate company + jd_text constraints after initial parsing."""
        if not self.company or len(self.company.strip()) < 2:
            raise ValueError("Company name must be at least 2 characters")
        self.company = self.company.strip()

        if self.jd_text:
            jd = self.jd_text.strip()
            if len(jd) < 50:
                raise ValueError(
                    "JD text must be at least 50 characters when provided"
                )
            if len(jd) > 10_000:
                raise ValueError(
                    "JD text must not exceed 10000 characters"
                )
            words = [w for w in jd.split() if len(w) > 1]
            if len(words) < 10:
                raise ValueError(
                    "JD text must contain at least 50 characters and ~10 meaningful words"
                )
            self.jd_text = jd
        else:
            self.jd_text = ""

        return self


class SaveEditRequest(BaseModel):
    txt_url: Optional[str] = Field(default=None, description="Relative URL or path to text file")
    raw_text: Optional[str] = Field(default=None, description="Updated raw resume text content")
    content: Optional[str] = Field(default=None, description="Updated raw resume text content (alias)")
    company: Optional[str] = Field(default="Tailored", description="Company name")


class BehavioralQuestionRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000, description="Behavioral interview question")
    context: Optional[str] = Field(default=None, description="Optional custom background context")


class DiffResumeRequest(BaseModel):
    tailored_text: str = Field(..., min_length=10, description="Tailored resume text to compare against master")
    candidate_id: Optional[str] = Field(default="default", description="Candidate profile ID")


class ATSSimulationRequest(BaseModel):
    resume_text: str = Field(..., min_length=10, description="Resume text to evaluate")
    jd_text: str = Field(..., min_length=10, description="Target job description text")


class CoverLetterRequest(BaseModel):
    company: str = Field(..., min_length=2, max_length=100, description="Target company name")
    jd_text: str = Field(default="", description="Job description text")
    candidate_name: Optional[str] = Field(default="Prasad Rane", description="Candidate name")
    role_title: Optional[str] = Field(default="Senior Software Engineer", description="Target role title")


class InterviewPrepRequest(BaseModel):
    jd_text: str = Field(..., min_length=10, description="Target job description text")


class LinkedInProfileRequest(BaseModel):
    target_role: Optional[str] = Field(default="Senior Software Engineer / Tech Lead", description="Target role or headline focus")
    candidate_name: Optional[str] = Field(default="Prasad Rane", description="Candidate name")


class ExtractJDURLRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=2000, description="Job posting URL to extract")

