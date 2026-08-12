"""
ats_matcher.py — ATS keyword extraction from Job Descriptions and GraphRAG story matching.
"""

import logging
import re
from typing import Optional
from pathlib import Path
from src.config import ROOT_DIR
from src.query.search_engine import execute_graphrag_query
from .constants import COMMON_ATS_KEYWORDS

log = logging.getLogger(__name__)

KNOWN_TECH_PATTERNS = [
    r"\b\.NET\s*(?:Core|[6789])?\b",
    r"\bC#\b",
    r"\bPython\b",
    r"\bFastAPI\b",
    r"\bAngular\b",
    r"\bTypeScript\b",
    r"\bAWS\b",
    r"\bECS\b",
    r"\bFargate\b",
    r"\bLambda\b",
    r"\bDynamoDB\b",
    r"\bBedrock\b",
    r"\bClaude\b",
    r"\bKafka\b",
    r"\bMSK\b",
    r"\bSQS\b",
    r"\bSNS\b",
    r"\bTerraform\b",
    r"\bDocker\b",
    r"\bKubernetes\b",
    r"\bSQL\s*Server\b",
    r"\bOAuth2?\b",
    r"\bJWT\b",
    r"\bDynatrace\b",
    r"\bSplunk\b",
    r"\bOpenTelemetry\b",
    r"\bMicroservices\b",
    r"\bCI/CD\b",
    r"\bCrowdStrike\b",
    r"\bFalcon\b",
    r"\bThreat\s*Hunting\b",
    r"\bObservability\b",
    r"\bREST\s*APIs?\b",
    r"\bCQRS\b",
    r"\bSingle-Table\b",
    r"\bDevEx\b",
]

def extract_ats_keywords(jd_text: str) -> list[str]:
    """Extract ATS keywords, technologies, and competencies dynamically from job description text."""
    if not jd_text or not jd_text.strip():
        return []

    found = set()
    upper_keywords = {kw.upper() for kw in COMMON_ATS_KEYWORDS}
    
    # 1. Match static dictionary terms
    cleaned = re.sub(r"[^A-Za-z0-9+#/\s-]", " ", jd_text)
    tokens = [t.strip().upper() for t in cleaned.split() if len(t.strip()) >= 2]

    for token in tokens:
        if token in upper_keywords:
            matched_kw = next((kw for kw in COMMON_ATS_KEYWORDS if kw.upper() == token), token)
            found.add(matched_kw)

    # 2. Match known technical & domain patterns (regex)
    for pat in KNOWN_TECH_PATTERNS:
        matches = re.findall(pat, jd_text, re.IGNORECASE)
        for m in matches:
            found.add(m.strip())

    # 3. Match camelCase / TitleCase technical terms from JD
    words = re.findall(r"\b[A-Z][a-zA-Z0-9#+.-]{2,}\b", jd_text)
    ignore_words = {"The", "And", "With", "For", "This", "That", "Your", "Have", "From", "Will", "Role", "Team", "Work"}
    for w in words:
        if w not in ignore_words and len(w) >= 3:
            if w.upper() in upper_keywords:
                matched_kw = next((kw for kw in COMMON_ATS_KEYWORDS if kw.upper() == w.upper()), w)
                found.add(matched_kw)
            elif any(c.isupper() for c in w[1:]): # e.g. FastAPI, DynamoDB, OpenTelemetry
                found.add(w)

    return sorted(list(found), key=lambda x: (len(x), x), reverse=True)

def match_graphrag_stories(keywords: list[str], root_dir: Optional[Path] = None) -> list[str]:
    """Query GraphRAG knowledge graph using keywords to retrieve candidate achievements."""
    if not keywords:
        return []

    query_str = f"Find relevant experience and metrics for: {', '.join(keywords)}"
    try:
        if root_dir is None:
            root_dir = ROOT_DIR
        response = execute_graphrag_query(query_str, mode="local", root_dir=root_dir)
        if not response:
            return []
        return [line.strip() for line in response.split("\n") if line.strip()]
    except Exception as e:
        log.warning("GraphRAG matcher fallback to serverless gateway: %s", e)
        try:
            from src.llm.service import call_llm
            res = call_llm(query_str, system_prompt="You are an ATS resume matcher. Extract matching resume bullets for the given keywords.")
            return [line.strip() for line in res.split("\n") if line.strip()]
        except Exception as s_err:
            log.warning("Serverless gateway fallback error: %s", s_err)
            return []
