"""
jd_extractor.py — Job Description URL extraction, metadata scraping, and HTML normalization.

Extracts company name, job title, and sanitized job description body from public URLs
(e.g., LinkedIn, Greenhouse, Lever, Indeed, or general company career portals).
"""

import logging
import re
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from typing import Dict, Optional

log = logging.getLogger(__name__)


class _HTMLTextExtractor(HTMLParser):
    """HTML parser that strips non-content tags and extracts formatted text."""

    def __init__(self):
        super().__init__()
        self._result: list[str] = []
        self._skip_tags = {"script", "style", "nav", "header", "footer", "aside", "noscript", "svg"}
        self._current_skip_depth = 0

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() in self._skip_tags:
            self._current_skip_depth += 1
        elif tag.lower() in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "br", "section", "article"}:
            self._result.append("\n")

    def handle_endtag(self, tag: str):
        if tag.lower() in self._skip_tags:
            self._current_skip_depth = max(0, self._current_skip_depth - 1)
        elif tag.lower() in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "section", "article"}:
            self._result.append("\n")

    def handle_data(self, data: str):
        if self._current_skip_depth == 0:
            text = data.strip()
            if text:
                self._result.append(text + " ")

    def get_text(self) -> str:
        raw = "".join(self._result)
        # Collapse excessive newlines & whitespace
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n\s*\n\s*\n+", "\n\n", raw)
        return raw.strip()


def clean_html_to_text(html: str) -> str:
    """Strip markup, script tags, navbars, and boilerplate from raw HTML."""
    extractor = _HTMLTextExtractor()
    extractor.feed(html)
    return extractor.get_text()


def _extract_metadata_from_html(html: str, url: str) -> Dict[str, str]:
    """Extract page title, site name, and company from HTML head / meta tags."""
    title = ""
    company = ""

    # Check meta property og:site_name
    site_match = re.search(r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if site_match:
        company = site_match.group(1).strip()

    # Check meta property og:title or <title>
    title_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not title_match:
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)

    if title_match:
        full_title = title_match.group(1).strip()
        parts = re.split(r"\s+at\s+|\s+[-|—–]\s+", full_title)
        if len(parts) >= 2:
            extracted_title = parts[0].strip()
            if not company:
                cand_comp = parts[1].strip()
                cand_comp = re.sub(r"(?i)\s*(Careers|Jobs|Hiring|Work with us|Apply).*$", "", cand_comp).strip()
                if cand_comp:
                    company = cand_comp
            title = extracted_title
        else:
            title = re.sub(r"(?i)\s*[-|—–]\s*(?:.*\s+)?(Careers|Jobs|Hiring|Apply).*$", "", full_title).strip()

    # Prefer <h1> element for the specific job title if present
    h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.IGNORECASE)
    if h1_match:
        h1_text = h1_match.group(1).strip()
        if h1_text and len(h1_text) < 100:
            title = h1_text

    # Fallback to domain name if company still empty
    if not company:
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc.replace("www.", "").split(".")[0]
        if domain and domain.lower() not in {"linkedin", "indeed", "greenhouse", "lever", "workday"}:
            company = domain.capitalize()

    return {"title": title or "Software Engineer", "company": company or "Target Company"}


def extract_jd_from_url(url: str, timeout: int = 15) -> Dict[str, str]:
    """Fetch and extract cleaned Job Description text and metadata from a URL."""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        raise ValueError(f"Invalid URL format: '{url}'. Must start with http:// or https://")

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        try:
            charset = resp.headers.get_content_charset() or "utf-8"
            if not isinstance(charset, str):
                charset = "utf-8"
        except Exception:
            charset = "utf-8"
        html = resp.read().decode(charset, errors="replace")

    metadata = _extract_metadata_from_html(html, url)
    jd_text = clean_html_to_text(html)

    return {
        "company": metadata["company"],
        "title": metadata["title"],
        "jd_text": jd_text,
        "url": url,
    }
