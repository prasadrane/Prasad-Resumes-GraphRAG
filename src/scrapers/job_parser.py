"""
src/scrapers/job_parser.py — Structured job posting parser with zero-cost JSON-LD and LLM fallback.
"""

import json
import logging
import re
from typing import Optional

from src.gateway.facade import call_serverless_llm
from .job_scraper import JobScraper, ScrapeResult
from .models import JobPosting

log = logging.getLogger(__name__)

JOB_PARSER_SYSTEM_PROMPT = """You are an expert Job Description Parser.
Extract key structured metadata from the provided raw job description text.
Return ONLY a valid JSON object with the following schema:
{
  "company": "<company name or Target Company>",
  "role_title": "<job title or Senior Software Engineer>",
  "location": "<location or Remote/Hybrid if mentioned, or null>",
  "required_skills": ["<skill1>", "<skill2>"],
  "preferred_skills": ["<skill1>", "<skill2>"],
  "responsibilities": ["<resp1>", "<resp2>"],
  "raw_description": "<concise summary of key duties and requirements>"
}
Do not include any conversational preamble or explanation, only raw JSON.
"""


class JobParser:
    """Parses raw job URLs or text into structured JobPosting models."""

    def __init__(self, scraper: Optional[JobScraper] = None):
        self.scraper = scraper or JobScraper()

    def parse_url(self, url: str) -> JobPosting:
        """Fetch URL and parse into JobPosting (via JSON-LD fast path or LLM fallback)."""
        scrape_result = self.scraper.fetch_url(url)
        return self.parse_scrape_result(scrape_result)

    def parse_scrape_result(self, scrape_result: ScrapeResult) -> JobPosting:
        """Parse a ScrapeResult. Returns zero-cost JSON-LD if available, else runs LLM structuring."""
        if scrape_result.has_json_ld and scrape_result.json_ld_posting:
            log.info("Zero-Cost Job Ingestion: Extracted Schema.org JSON-LD directly (0 LLM tokens).")
            return scrape_result.json_ld_posting

        return self.parse_text(
            raw_text=scrape_result.sanitized_text,
            source_url=scrape_result.source_url,
        )

    def parse_text(self, raw_text: str, source_url: Optional[str] = None) -> JobPosting:
        """Parse raw or sanitized job description text using structured LLM extraction."""
        if not raw_text or not raw_text.strip():
            return JobPosting(
                company="Target Company",
                role_title="Software Professional",
                raw_description="",
                source_url=source_url,
            )

        # Truncate text if excessively long to save input tokens
        truncated_text = raw_text[:6000]

        prompt = f"Please parse the following job description:\n\n{truncated_text}"

        try:
            raw_response = call_serverless_llm(
                prompt=prompt,
                system_prompt=JOB_PARSER_SYSTEM_PROMPT,
                temperature=0.1,
            )
            data = self._clean_and_parse_json(raw_response)

            return JobPosting(
                company=data.get("company") or "Target Company",
                role_title=data.get("role_title") or "Software Professional",
                location=data.get("location"),
                required_skills=data.get("required_skills", []),
                preferred_skills=data.get("preferred_skills", []),
                responsibilities=data.get("responsibilities", []),
                raw_description=data.get("raw_description") or raw_text[:1000],
                source_url=source_url,
            )
        except Exception as exc:
            log.warning("LLM job parsing failed or returned invalid JSON: %s. Using heuristic fallback.", exc)
            return self._heuristic_fallback(raw_text, source_url)

    @staticmethod
    def _clean_and_parse_json(text: str) -> dict:
        """Strip markdown json code fences and parse JSON."""
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned.strip())

    @staticmethod
    def _heuristic_fallback(raw_text: str, source_url: Optional[str] = None) -> JobPosting:
        """Fallback heuristic parser if LLM fails or is offline."""
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        title = lines[0] if lines else "Software Professional"
        return JobPosting(
            company="Target Company",
            role_title=title[:80],
            raw_description=raw_text,
            source_url=source_url,
        )
