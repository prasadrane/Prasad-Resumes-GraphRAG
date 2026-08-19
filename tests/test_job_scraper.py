"""
test_job_scraper.py — Unit tests for JobScraper and Schema.org JSON-LD extraction.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.scrapers.models import JobPosting, ScrapeResult
from src.scrapers.job_scraper import JobScraper, ScrapeError


SAMPLE_JSON_LD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Senior Cloud Architect at Databricks</title>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": "Senior Cloud Architect",
        "hiringOrganization": {
            "@type": "Organization",
            "name": "Databricks"
        },
        "jobLocation": {
            "@type": "Place",
            "address": {
                "addressLocality": "San Francisco",
                "addressRegion": "CA"
            }
        },
        "description": "<p>We are seeking a <strong>Senior Cloud Architect</strong> proficient in AWS, Kubernetes, Terraform, and Python. Responsibilities include building scalable microservices and streaming pipelines.</p>",
        "skills": ["AWS", "Kubernetes", "Terraform", "Python", "Kafka"]
    }
    </script>
</head>
<body>
    <nav>Navigation links</nav>
    <main>
        <h1>Job Opening</h1>
        <p>Visible job page description text...</p>
    </main>
    <footer>Footer & Cookie policy</footer>
</body>
</html>
"""

SAMPLE_GRAPH_JSON_LD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "name": "Careers at Snowflake"
            },
            {
                "@type": "JobPosting",
                "title": "Principal Distributed Systems Engineer",
                "hiringOrganization": {
                    "name": "Snowflake"
                },
                "jobLocation": {
                    "address": "Bellevue, WA"
                },
                "description": "Architect distributed database engines using C#, C++, and AWS S3."
            }
        ]
    }
    </script>
</head>
<body><p>Snowflake careers</p></body>
</html>
"""

SAMPLE_RAW_HTML_NO_JSON_LD = """
<!DOCTYPE html>
<html>
<head>
    <style>body { font-family: sans-serif; }</style>
    <script>console.log("analytics");</script>
</head>
<body>
    <header><nav>Logo and Header Links</nav></header>
    <div class="cookie-banner">Accept all cookies</div>
    <div id="job-content">
        <h2>Software Engineer - Backend</h2>
        <h3>Company: Stripe</h3>
        <p>Location: Remote - US</p>
        <h4>Requirements:</h4>
        <ul>
            <li>5+ years of experience with Python or Go</li>
            <li>Experience with distributed systems and PostgreSQL</li>
        </ul>
    </div>
    <footer>Privacy Policy and copyright 2026</footer>
</body>
</html>
"""


def test_job_scraper_extract_json_ld_direct():
    scraper = JobScraper()
    posting = scraper.extract_json_ld(SAMPLE_JSON_LD_HTML, source_url="https://boards.greenhouse.io/databricks/jobs/123")
    
    assert posting is not None
    assert posting.company == "Databricks"
    assert posting.role_title == "Senior Cloud Architect"
    assert "San Francisco" in posting.location
    assert "AWS" in posting.required_skills or "AWS" in posting.raw_description
    assert posting.source_url == "https://boards.greenhouse.io/databricks/jobs/123"


def test_job_scraper_extract_json_ld_graph_format():
    scraper = JobScraper()
    posting = scraper.extract_json_ld(SAMPLE_GRAPH_JSON_LD_HTML)
    
    assert posting is not None
    assert posting.company == "Snowflake"
    assert posting.role_title == "Principal Distributed Systems Engineer"
    assert "Bellevue, WA" in posting.location
    assert "distributed database engines" in posting.raw_description


def test_job_scraper_extract_json_ld_returns_none_when_absent():
    scraper = JobScraper()
    posting = scraper.extract_json_ld(SAMPLE_RAW_HTML_NO_JSON_LD)
    assert posting is None


def test_job_scraper_sanitize_html():
    scraper = JobScraper()
    cleaned = scraper.sanitize_html(SAMPLE_RAW_HTML_NO_JSON_LD)
    
    assert "Logo and Header Links" not in cleaned
    assert "Accept all cookies" not in cleaned
    assert "Privacy Policy and copyright" not in cleaned
    assert "analytics" not in cleaned
    assert "Software Engineer - Backend" in cleaned
    assert "Python or Go" in cleaned
    assert "PostgreSQL" in cleaned


@patch("requests.get")
def test_job_scraper_fetch_url_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_JSON_LD_HTML
    mock_get.return_value = mock_resp
    
    scraper = JobScraper()
    result = scraper.fetch_url("https://example.com/job/123")
    
    assert isinstance(result, ScrapeResult)
    assert result.status_code == 200
    assert result.has_json_ld is True
    assert result.json_ld_posting is not None
    assert result.json_ld_posting.company == "Databricks"


@patch("requests.get")
def test_job_scraper_fetch_url_error_handling(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.raise_for_status.side_effect = Exception("404 Not Found")
    mock_get.return_value = mock_resp
    
    scraper = JobScraper()
    with pytest.raises(ScrapeError):
        scraper.fetch_url("https://example.com/nonexistent")


@patch("requests.post")
def test_job_scraper_ashby_fastpath(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "jobPosting": {
                "title": "Senior Infrastructure Engineer",
                "locationName": "San Francisco, CA",
                "descriptionHtml": "<p>Build Kubernetes and Terraform infrastructure for OpenAI scale.</p>"
            }
        }
    }
    mock_post.return_value = mock_resp

    scraper = JobScraper()
    posting = scraper.fetch_ats_api_fastpath("https://jobs.ashbyhq.com/openai/12345-6789")
    assert posting is not None
    assert posting.company == "Openai"
    assert posting.role_title == "Senior Infrastructure Engineer"
    assert "Kubernetes" in posting.raw_description


@patch("requests.get")
def test_job_scraper_smartrecruiters_fastpath(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "name": "Staff Backend Engineer",
        "company": {"name": "Visa"},
        "location": {"city": "Foster City", "region": "CA"},
        "jobAd": {
            "sections": {
                "jobDescription": {"text": "<p>Design payment orchestration microservices with AWS and Java.</p>"}
            }
        }
    }
    mock_get.return_value = mock_resp

    scraper = JobScraper()
    posting = scraper.fetch_ats_api_fastpath("https://jobs.smartrecruiters.com/Visa/1234567")
    assert posting is not None
    assert posting.company == "Visa"
    assert posting.role_title == "Staff Backend Engineer"
    assert "payment orchestration" in posting.raw_description

