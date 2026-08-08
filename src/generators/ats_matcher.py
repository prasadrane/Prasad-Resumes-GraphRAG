"""
ats_matcher.py — ATS keyword extraction from Job Descriptions and GraphRAG story matching.
"""

import re
from typing import List
from pathlib import Path
from src.query.search_engine import execute_graphrag_query
from .constants import COMMON_ATS_KEYWORDS

def extract_ats_keywords(jd_text: str) -> List[str]:
    """Extract ATS keywords, technologies, and competencies from job description text."""
    if not jd_text or not jd_text.strip():
        return []

    found = set()
    upper_keywords = {kw.upper() for kw in COMMON_ATS_KEYWORDS}
    cleaned = re.sub(r"[^A-Za-z0-9+#/\s-]", " ", jd_text)
    tokens = [t.strip().upper() for t in cleaned.split() if len(t.strip()) >= 2]

    for token in tokens:
        if token in upper_keywords:
            # Map back to standard casing
            matched_kw = next((kw for kw in COMMON_ATS_KEYWORDS if kw.upper() == token), token)
            found.add(matched_kw)

    # Check multi-word patterns
    upper_jd = jd_text.upper()
    if ".NET CORE" in upper_jd or ".NET" in upper_jd:
        found.add(".NET Core")
    if "GRAPH RAG" in upper_jd or "GRAPHRAG" in upper_jd:
        found.add("GraphRAG")
    if "MICROSERVICES" in upper_jd:
        found.add("Microservices")
    if "CI/CD" in upper_jd or "CICD" in upper_jd:
        found.add("CI/CD")

    # Match title cased tech words
    words = re.findall(r"\b[A-Z][a-zA-Z0-9#+.-]{2,}\b", jd_text)
    for w in words:
        if w.upper() in upper_keywords:
            matched_kw = next((kw for kw in COMMON_ATS_KEYWORDS if kw.upper() == w.upper()), w)
            found.add(matched_kw)

    return sorted(list(found))

def match_graphrag_stories(keywords: List[str], root_dir: Path = None) -> List[str]:
    """Query GraphRAG knowledge graph using keywords to retrieve candidate achievements."""
    if not keywords:
        return []

    query_str = f"Find relevant experience and metrics for: {', '.join(keywords)}"
    try:
        if root_dir is None:
            root_dir = Path(__file__).resolve().parent.parent.parent
        response = execute_graphrag_query(query_str, mode="local", root_dir=root_dir)
        if not response:
            return []
        return [line.strip() for line in response.split("\n") if line.strip()]
    except Exception as e:
        print(f"[WARN] GraphRAG matcher fallback: {e}")
        return []
