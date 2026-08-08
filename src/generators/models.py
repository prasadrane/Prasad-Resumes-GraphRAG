"""
models.py — Pydantic models for consistent resume data structures across generators.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from .constants import (
    CREDLY_AWS_CERT_URL,
    DEFAULT_CANDIDATE_NAME,
    DEFAULT_CANDIDATE_TITLE,
    DEFAULT_EDUCATION,
    DEFAULT_EMAIL,
    DEFAULT_LINKEDIN_URL,
    DEFAULT_LOCATION,
    DEFAULT_PHONE,
    DEFAULT_PORTFOLIO_URL,
)

class JobEntry(BaseModel):
    """Pydantic model representing a single job role entry."""
    heading: str
    title: str = "Software Engineer"
    company: str = "Rocket Mortgage"
    location: str = DEFAULT_LOCATION
    dates: str = "Jan 2023 - Jul 2025"
    bullets: List[str] = Field(default_factory=list)

class ResumeData(BaseModel):
    """Pydantic model representing the complete structured resume data."""
    name: str = DEFAULT_CANDIDATE_NAME
    title: str = DEFAULT_CANDIDATE_TITLE
    contact_location: str = DEFAULT_LOCATION
    contact_phone: str = DEFAULT_PHONE
    contact_email: str = DEFAULT_EMAIL
    contact_linkedin: str = DEFAULT_LINKEDIN_URL
    contact_portfolio: str = DEFAULT_PORTFOLIO_URL
    summary: str = ""
    jobs: List[JobEntry] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
