"""
domain_matcher.py — Domain classification and summary variant selection.

Uses SME ontology taxonomies and domain keyword sets to select the best matching
executive summary variant from MASTER_RESUME.txt for a given Job Description.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from src.config import ROOT_DIR
from .resume_parser import extract_summary_variants

log = logging.getLogger(__name__)

# Default domain keywords (overridable via config/domain_keywords.yaml)
_DEFAULT_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "AI / LLM-Forward": [
        "AI", "ML", "LLM", "Bedrock", "chatbot", "NLP", "prompt", "Claude", "GPT",
        "machine learning", "deep learning", "generative", "RAG", "language model",
        "natural language", "neural", "transformer", "inference",
    ],
    "Cloud & Reliability-Forward": [
        "cloud", "AWS", "Azure", "GCP", "infrastructure", "reliability",
        "uptime", "SRE", "migration", "ECS", "Fargate", "Lambda", "containeriz",
        "scalab", "distributed system", "high availability",
    ],
    "Platform & DevEx-Forward": [
        "platform", "developer experience", "tooling", "onboarding", "DevEx",
        "DX", "developer productivity", "internal tools", "DevOps", "platform engineering",
    ],
    "Security & Auth-Forward": [
        "security", "authentication", "authorization", "OAuth", "JWT", "SSO",
        "IAM", "compliance", "zero trust", "RBAC", "identity", "penetration",
        "vulnerability", "SOC", "audit",
    ],
}


def _load_domain_keywords(config_dir: Optional[Path] = None) -> Dict[str, List[str]]:
    """Load domain keywords from *config/domain_keywords.yaml*, falling back to defaults."""
    if config_dir is None:
        config_dir = ROOT_DIR / "config"
    yaml_path = config_dir / "domain_keywords.yaml"
    try:
        if yaml_path.exists():
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            domains: dict = data.get("domains", {})
            if domains:
                return {k: list(v) for k, v in domains.items()}
    except Exception as exc:
        log.warning("Failed to load domain_keywords.yaml: %s — using built-in defaults", exc)
    return dict(_DEFAULT_DOMAIN_KEYWORDS)


DOMAIN_KEYWORDS: Dict[str, List[str]] = _load_domain_keywords()


def select_tailored_summary(content: str, keywords: List[str], company_name: str = "", jd_text: str = "") -> str:
    """Select best-matching summary variant using domain-category analysis.

    Evaluates full JD text and extracted keywords against domain taxonomies.
    """
    variants = extract_summary_variants(content)
    if not variants:
        return ""

    match_text = (jd_text or " ".join(keywords)).upper()

    domain_scores = {}
    for domain_name, domain_kws in DOMAIN_KEYWORDS.items():
        score = sum(1 for dkw in domain_kws if dkw.upper() in match_text)
        domain_scores[domain_name] = score

    best_domain = max(domain_scores, key=domain_scores.get)
    best_score = domain_scores[best_domain]

    if best_score >= 2 and best_domain in variants:
        return variants[best_domain]

    # Fallback to canonical if no clear domain match
    return variants.get("Canonical", "")
