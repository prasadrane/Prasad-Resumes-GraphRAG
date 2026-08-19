"""
src/scrapers/models.py — Data models for scraped job postings and scrape results.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    """Structured representation of an ingested job posting."""
    company: str = Field(..., description="Name of the hiring company")
    role_title: str = Field(..., description="Job role or job title")
    location: Optional[str] = Field(None, description="Job location or Remote indicator")
    required_skills: List[str] = Field(default_factory=list, description="Explicitly required skills and technologies")
    preferred_skills: List[str] = Field(default_factory=list, description="Nice-to-have or preferred qualifications")
    responsibilities: List[str] = Field(default_factory=list, description="Key duties and core responsibilities")
    raw_description: str = Field(..., description="Full sanitized job description text")
    source_url: Optional[str] = Field(None, description="Original source URL if ingested via web link")


class ScrapeResult(BaseModel):
    """Raw and processed result from a web scrape operation."""
    raw_html: str
    sanitized_text: str
    status_code: int = 200
    has_json_ld: bool = False
    json_ld_posting: Optional[JobPosting] = None
    source_url: Optional[str] = None
