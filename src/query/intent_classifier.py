"""
IntentClassifier — Classify query intent to optimize retrieval strategy.

Routes queries to the most appropriate GraphRAG mode, top-k, and filters.
This module is additive — existing query modes (local/global/drift) remain unchanged.

Usage:
    classifier = IntentClassifier()
    intent = classifier.classify("What AWS services has Prasad used?")
    strategy = classifier.get_retrieval_strategy(intent)
    # strategy -> {"mode": "local", "top_k": 15, "filters": {"entities": ["AWS"]}}
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Categories of user queries against the knowledge graph."""
    SKILL_LOOKUP = "skill_lookup"
    COMPANY_LOOKUP = "company_lookup"
    EXPERIENCE_LOOKUP = "experience_lookup"
    GENERAL_QUERY = "general_query"


# ── Intent signatures — short lists of high-signal trigger words/phrases ──

_SKILL_TRIGGERS: List[str] = [
    "skill", "skills", "technology", "technologies",
    "tools", "tech stack", "infrastructure",
]

# High-signal tech terms whose mere presence suggests a skill_lookup intent
_SKILL_TECH_TERMS: List[str] = [
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "python", "java", "c#", ".net", "angular", "react", "node.js",
    "kafka", "redis", "postgres", "dynamodb", "lambda", "ecs",
    "fargate", "splunk", "dynatrace", "graphql", "rest api",
    "microservice", "ci/cd", "jenkins", "oauth", "jwt",
]

_COMPANY_TRIGGERS: List[str] = [
    r"\bworked?\s*at\b", r"\bworks?\s+for\b", r"\bemployed\b",
    r"\bemployer\b", r"\bwhere.*\b(?:did|does|has)\s",
    r"\bcareer\s+history\b", r"\bprevious\s+job",
    r"(?<!w)where\b.*\b(at|did|does)", r"\bjobs?\s*\?",
]

_EXPERIENCE_TRIGGERS: List[str] = [
    "experience", "project(s|s)", "what.*do(?:ne|id)",
    "tell me about", "describe (?:your |the )?(?:experience|background|achievement)",
    "achievement", "led", "managed", "built", "designed",
    "implemented", "resulted in", "metric", "metrics", "impact",
    "responsibility", "responsibilities",
]


def _norm(text: str) -> str:
    """Lowercase + collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _check_any(query_norm: str, triggers: List[str]) -> bool:
    """Check if ANY regex trigger matches the normalized query."""
    for pattern in triggers:
        if re.search(pattern, query_norm):
            return True
    return False


class IntentClassifier:
    """Classifies natural-language queries into structured intents using rule-based matching."""

    def __init__(self, min_confidence: float = 0.0) -> None:
        """
        Args:
            min_confidence: Reserved for future confidence-weighted classification.
        """
        self._triggers: Dict[QueryIntent, List[str]] = {
            QueryIntent.SKILL_LOOKUP: _SKILL_TRIGGERS,
            QueryIntent.COMPANY_LOOKUP: _COMPANY_TRIGGERS,
            QueryIntent.EXPERIENCE_LOOKUP: _EXPERIENCE_TRIGGERS,
        }

    def classify(self, query: str) -> QueryIntent:
        """Determine the intent behind *query*.

        Classification priority:
        1. Skill lookup — queries asking about technologies/tools/skills
        2. Company lookup — queries asking where the candidate worked
        3. Experience lookup — queries about projects/achievements/experience
        4. General query — everything else (education, certifications, summaries)
        """
        normalized = _norm(query)
        if not normalized or len(normalized) < 3:
            return QueryIntent.GENERAL_QUERY

        # Check skill triggers + known tech term presence
        if _check_any(normalized, self._triggers[QueryIntent.SKILL_LOOKUP]):
            return QueryIntent.SKILL_LOOKUP
        # Direct tech mention without explicit trigger words
        if any(term in normalized for term in _SKILL_TECH_TERMS):
            return QueryIntent.SKILL_LOOKUP
        if _check_any(normalized, self._triggers[QueryIntent.COMPANY_LOOKUP]):
            return QueryIntent.COMPANY_LOOKUP
        if _check_any(normalized, self._triggers[QueryIntent.EXPERIENCE_LOOKUP]):
            return QueryIntent.EXPERIENCE_LOOKUP

        return QueryIntent.GENERAL_QUERY

    def get_retrieval_strategy(self, intent: QueryIntent) -> Dict[str, object]:
        """Return the recommended retrieval configuration for an intent."""
        strategies: Dict[QueryIntent, Dict[str, object]] = {
            QueryIntent.SKILL_LOOKUP: {
                "mode": "local",
                "top_k": 15,
                "entity_boost": True,
                "description": "Focused entity search for technology/skill queries",
            },
            QueryIntent.COMPANY_LOOKUP: {
                "mode": "global",
                "top_k": 20,
                "entity_boost": False,
                "description": "Broad community aggregation for employment history",
            },
            QueryIntent.EXPERIENCE_LOOKUP: {
                "mode": "drift",
                "top_k": 12,
                "entity_boost": True,
                "description": "Drift mode for open-ended experience/project queries",
            },
            QueryIntent.GENERAL_QUERY: {
                "mode": "local",
                "top_k": 10,
                "entity_boost": False,
                "description": "Default fallback — balanced local search",
            },
        }
        return strategies.get(intent, strategies[QueryIntent.GENERAL_QUERY])

    def classify_with_details(self, query: str) -> Dict[str, object]:
        """Classify and return match details (useful for debugging)."""
        normalized = _norm(query)
        matches = {}
        for intent, triggers in self._triggers.items():
            matched_triggers = []
            for t in triggers:
                if re.search(t, normalized):
                    matched_triggers.append(t)
            matches[intent.value] = {"matched_triggers": matched_triggers}
        return {
            "intent": self.classify(query).value,
            "match_details": matches,
        }
