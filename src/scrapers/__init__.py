"""
src/scrapers/__init__.py — Job ingestion and scraping subsystem.
"""

from .models import JobPosting, ScrapeResult
from .job_scraper import JobScraper, ScrapeError
from .job_parser import JobParser

__all__ = [
    "JobPosting",
    "ScrapeResult",
    "JobScraper",
    "ScrapeError",
    "JobParser",
]
