"""
ats_matcher.py — ATS keyword extraction from Job Descriptions, SME Ontology expansion,
and GraphRAG story matching with action-verb impact ranking.
"""

import logging
import re
from dataclasses import replace
from pathlib import Path
from typing import Optional, List, Tuple

import yaml

from src.config import ROOT_DIR
from src.query.search_engine import execute_graphrag_query
from .constants import COMMON_ATS_KEYWORDS
from .sme_ontology import SMEOntology
from .scoring import ImpactScorer, ScoreBreakdown

log = logging.getLogger(__name__)

# ── Tech Patterns (loaded from YAML config; falls back to hardcoded if missing) ──

_DEFAULT_TECH_PATTERNS: list[str] = [
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


def _load_tech_patterns(config_dir: Optional[Path] = None) -> list[str]:
    """Load tech regex patterns from *config/tech_patterns.yaml*, falling back to defaults."""
    if config_dir is None:
        config_dir = ROOT_DIR / "config"
    yaml_path = config_dir / "tech_patterns.yaml"
    try:
        if yaml_path.exists():
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            patterns: list[str] = data.get("patterns", [])
            if patterns:
                return patterns
    except Exception as exc:  # pragma: no cover
        log.warning("Failed to load tech_patterns.yaml: %s — using built-in defaults", exc)
    return list(_DEFAULT_TECH_PATTERNS)


KNOWN_TECH_PATTERNS = _load_tech_patterns()
_ontology = SMEOntology()
_scorer = ImpactScorer()


def extract_ats_keywords(jd_text: str, expand_ontology: bool = True) -> list[str]:
    """Extract ATS keywords, technologies, and competencies dynamically from job description text.
    
    If expand_ontology is True, queries the SME Technology Ontology to enrich with
    domain child skills, parent categories, and normalized synonyms.
    """
    if not jd_text or not jd_text.strip():
        return []

    found = set()
    upper_keywords = {kw.upper() for kw in COMMON_ATS_KEYWORDS}
    jd_lower = jd_text.lower()
    
    # 1. Match static dictionary terms (single words & tokens)
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

    # 3. Match ontology domain categories, skills, and synonyms directly in JD text
    for syn in _ontology.SYNONYM_MAP.keys():
        if len(syn) >= 3 and re.search(r"\b" + re.escape(syn) + r"\b", jd_lower):
            found.add(syn)
    for cat in _ontology.CATEGORY_CHILDREN_MAP.keys():
        if len(cat) >= 3 and re.search(r"\b" + re.escape(cat) + r"\b", jd_lower):
            found.add(cat)
    for skill in _ontology.SKILL_TAXONOMY.keys():
        if len(skill) >= 3 and re.search(r"\b" + re.escape(skill) + r"\b", jd_lower):
            found.add(skill)

    # 4. Match camelCase / TitleCase technical terms from JD
    words = re.findall(r"\b[A-Z][a-zA-Z0-9#+.-]{2,}\b", jd_text)
    ignore_words = {"The", "And", "With", "For", "This", "That", "Your", "Have", "From", "Will", "Role", "Team", "Work"}
    for w in words:
        if w not in ignore_words and len(w) >= 3:
            if w.upper() in upper_keywords:
                matched_kw = next((kw for kw in COMMON_ATS_KEYWORDS if kw.upper() == w.upper()), w)
                found.add(matched_kw)
            elif any(c.isupper() for c in w[1:]):  # e.g. FastAPI, DynamoDB, OpenTelemetry
                found.add(w)

    # 5. SME Ontology Expansion (Domain Categories, Synonyms, and Child Skills)
    if expand_ontology:
        expanded_terms = _ontology.expand_query_terms(list(found))
        found.update(expanded_terms)

    return sorted(list(found), key=lambda x: (len(x), x), reverse=True)


def rank_experience_bullets(
    bullets: list[str],
    keywords: Optional[list[str]] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    duration_years: Optional[float] = None,
    reference_year: Optional[int] = None,
) -> list[Tuple[str, ScoreBreakdown]]:
    """Rank candidate experience bullets using Action-Verb Impact Scoring, Metric Detection, and Recency Decay."""
    if not bullets:
        return []

    scored_bullets: list[Tuple[str, ScoreBreakdown]] = []
    kw_set = {k.lower() for k in keywords} if keywords else set()

    for bullet in bullets:
        score_breakdown = _scorer.score_bullet(
            bullet=bullet,
            start_year=start_year,
            end_year=end_year,
            duration_years=duration_years,
            reference_year=reference_year,
        )

        # Keyword density bonus if bullet contains target keywords
        if kw_set:
            bullet_lower = bullet.lower()
            kw_matches = sum(1 for kw in kw_set if kw in bullet_lower)
            if kw_matches > 0:
                bonus = min(0.15 * kw_matches, 0.3)
                adjusted_final = min(1.0, score_breakdown.final_score + bonus)
                score_breakdown = score_breakdown.model_copy(update={"final_score": round(adjusted_final, 4)})

        scored_bullets.append((bullet, score_breakdown))

    # Sort descending by final score
    scored_bullets.sort(key=lambda item: item[1].final_score, reverse=True)
    return scored_bullets


def compute_bm25_relevance(
    query_terms: list[str],
    doc_text: str,
    k1: float = 1.5,
    b: float = 0.75,
    avg_doc_len: float = 25.0,
) -> float:
    """Compute BM25 term frequency relevance score between query terms and a document/bullet."""
    if not query_terms or not doc_text:
        return 0.0

    doc_tokens = re.findall(r"\w+", doc_text.lower())
    doc_len = len(doc_tokens)
    if doc_len == 0:
        return 0.0

    score = 0.0
    for term in query_terms:
        term_clean = term.strip().lower()
        if not term_clean:
            continue
        tf = doc_tokens.count(term_clean)
        if tf > 0:
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_len / avg_doc_len))
            score += numerator / denominator

    return round(score, 4)


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
