"""
test_job_parser.py — Unit tests for JobParser structuring into JobPosting model.
"""

import json
from unittest.mock import patch, MagicMock
import pytest

from src.scrapers.models import JobPosting, ScrapeResult
from src.scrapers.job_parser import JobParser


def test_job_parser_with_json_ld_zero_llm():
    posting_in = JobPosting(
        company="Stripe",
        role_title="Staff Infrastructure Engineer",
        location="Remote",
        required_skills=["AWS", "Terraform", "Go"],
        preferred_skills=["Distributed Systems"],
        responsibilities=["Lead platform scaling"],
        raw_description="Full job description",
    )
    scrape_res = ScrapeResult(
        raw_html="<html>...</html>",
        sanitized_text="Full job description",
        status_code=200,
        has_json_ld=True,
        json_ld_posting=posting_in,
    )
    
    with patch("src.scrapers.job_parser.call_serverless_llm") as mock_llm:
        parser = JobParser()
        result = parser.parse_scrape_result(scrape_res)
        
        # Verify zero LLM calls
        mock_llm.assert_not_called()
        assert result.company == "Stripe"
        assert result.role_title == "Staff Infrastructure Engineer"
        assert "AWS" in result.required_skills


def test_job_parser_with_raw_text_llm_fallback():
    mock_llm_payload = {
        "company": "Amazon AWS",
        "role_title": "Senior Solutions Architect",
        "location": "Seattle, WA",
        "required_skills": ["AWS", "Microservices", "Python", "Docker"],
        "preferred_skills": ["Serverless", "DynamoDB"],
        "responsibilities": ["Design distributed architectures"],
        "raw_description": "We are seeking a Senior Solutions Architect..."
    }
    
    with patch("src.scrapers.job_parser.call_serverless_llm") as mock_llm:
        mock_llm.return_value = json.dumps(mock_llm_payload)
        
        parser = JobParser()
        result = parser.parse_text("We are seeking a Senior Solutions Architect at Amazon AWS in Seattle...")
        
        assert mock_llm.called
        assert result.company == "Amazon AWS"
        assert result.role_title == "Senior Solutions Architect"
        assert "Microservices" in result.required_skills


def test_job_parser_cleans_markdown_json_fences():
    mock_llm_payload = {
        "company": "Netflix",
        "role_title": "Senior Backend Engineer",
        "location": "Los Gatos, CA",
        "required_skills": ["Java", "Kafka", "AWS"],
        "preferred_skills": ["gRPC"],
        "responsibilities": ["Scale streaming APIs"],
        "raw_description": "Join Netflix..."
    }
    
    with patch("src.scrapers.job_parser.call_serverless_llm") as mock_llm:
        mock_llm.return_value = f"```json\n{json.dumps(mock_llm_payload)}\n```"
        
        parser = JobParser()
        result = parser.parse_text("Join Netflix as Senior Backend Engineer...")
        
        assert result.company == "Netflix"
        assert "Java" in result.required_skills


@patch.object(JobParser, "parse_scrape_result")
@patch("src.scrapers.job_scraper.JobScraper.fetch_url")
def test_job_parser_parse_url_orchestration(mock_fetch, mock_parse_result):
    mock_fetch.return_value = ScrapeResult(
        raw_html="...", sanitized_text="...", status_code=200, has_json_ld=False
    )
    expected_posting = JobPosting(
        company="Apple", role_title="Cloud Engineer", raw_description="..."
    )
    mock_parse_result.return_value = expected_posting
    
    parser = JobParser()
    res = parser.parse_url("https://jobs.apple.com/en-us/details/12345")
    
    mock_fetch.assert_called_once_with("https://jobs.apple.com/en-us/details/12345")
    assert res.company == "Apple"
