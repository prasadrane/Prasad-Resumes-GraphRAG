"""
IntentClassifier — Classify query intent to optimize retrieval strategy.

Routes queries to the most appropriate GraphRAG mode, top-k, and filters.
Integrates SMEOntology for entity extraction and semantic domain recognition.
This module is additive — existing query modes (local/global/drift) remain unchanged.

Usage:
    classifier = IntentClassifier()
    intent = classifier.classify("What AWS services has Prasad used?")
    strategy = classifier.get_retrieval_strategy(intent)
    # strategy -> {"mode": "local", "top_k": 15, "entity_boost": True, "enable_guardrail": True, ...}
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Dict, List, Optional, Set

from src.generators.sme_ontology import SMEOntology

log = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Categories of user queries against the knowledge graph."""
    SKILL_LOOKUP = "skill_lookup"
    COMPANY_LOOKUP = "company_lookup"
    EXPERIENCE_LOOKUP = "experience_lookup"
    METRICS_LOOKUP = "metrics_lookup"
    COMPARATIVE_QUERY = "comparative_query"
    GENERAL_QUERY = "general_query"


# ── Intent signatures — lists of high-signal trigger patterns ──

_COMPARATIVE_TRIGGERS: List[str] = [
    r"\b(compare|comparing|comparison|contrasting?)\b",
    r"\bvs\.?\b|\bversus\b",
    r"\bdifference\s+(between|in)\b",
    r"\bhow\s+does\s+.*compare\b",
    r"\bcompare\s+.*across\b",
    r"\b(across\s+companies|across\s+roles|across\s+projects)\b",
]

_METRICS_TRIGGERS: List[str] = [
    r"\b(cost\s*savings?|dollar\s*savings?|savings?)\b",
    r"\b(percentage|percent|%)\s*(reduction|increase|improvement|growth|cut)?\b",
    r"\b(performance\s*metrics?|metrics?|scale\s*numbers?|scale)\b",
    r"\b(latency\s*reduction|latency|throughput|response\s*time|sla|uptime)\b",
    r"\b(quantitative\s*impact|roi|kpis?|benchmark\s*statistics?|statistics?)\b",
    r"\b(reduction\s*was\s*achieved|performance\s*numbers?)\b",
    r"\b(dollar\s*amount|million|\$|stats?)\b",
]

_COMPANY_TRIGGERS: List[str] = [
    r"\bworked?\s*at\b",
    r"\bworks?\s+for\b",
    r"\bemployed\b",
    r"\bemployer\b",
    r"\bwhere.*\b(?:did|does|has)\s+(he|prasad|she)?\s*(work|worked|been)\b",
    r"\bcareer\s+history\b",
    r"\bprevious\s+(job|employer|employers|companies|company)\b",
    r"(?<!w)where\b.*\b(at|did|does)",
    r"\b(companies|company)\b.*\b(worked|at|for|employed)\b",
    r"\bwhat\s+companies\b",
    r"\bwhere\s+has\s+he\s+been\s+employed\b",
    r"\bjobs?\s*\?",
]

_SKILL_TRIGGERS: List[str] = [
    r"\b(skill|skills|technology|technologies|tools?|tech\s*stack|infrastructure|stack|frameworks?|languages?|libraries|databases?)\b",
    r"\b(know|knows|proficient\s+in|familiar\s+with|experience\s+with)\b",
    r"\b(does\s+(he|prasad)\s+(know|have\s+experience\s+with))\b",
]

_EXPERIENCE_TRIGGERS: List[str] = [
    r"\b(experience\s+building|background\s+leading|leading\s+.*team|leading\s+engineering)\b",
    r"\b(projects?\s+has|projects?\s+built|projects?\s+managed|projects?\s+led)\b",
    r"\b(architecture\s+(he|prasad)?\s*designed|designed\s+the\s+architecture)\b",
    r"\b(describe|tell\s+me\s+about)\s+(his|prasad'?s?)?\s*(background|experience|achievement|achievements|career|projects?|contributions?)\b",
    r"\b(achievement|achievements|led|managed|built|designed|implemented|contributions?)\b",
    r"\b(responsibility|responsibilities)\b",
]

_GENERAL_TRIGGERS: List[str] = [
    r"^(hi|hello|hey|greetings|howdy|good\s+(morning|afternoon|evening))\b",
    r"\b(education|degree|gpa|university|college|bachelor|master|phd|school|graduat(ed?|ion))\b",
    r"\b(certificat(ion|ions|e|es)|certified|credential|credentials)\b",
    r"\b(summary|overview|bio|biography|who\s+is\s+prasad|about\s+prasad)\b",
]

# Additional high-signal tech tokens
_ADDITIONAL_TECH_TOKENS: List[str] = [
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "python", "java", "c#", ".net", "angular", "react", "node.js",
    "kafka", "redis", "postgres", "dynamodb", "lambda", "ecs",
    "fargate", "splunk", "dynatrace", "graphql", "rest api",
    "microservice", "ci/cd", "jenkins", "oauth", "jwt", "lancedb",
    "neo4j", "pytorch", "tensorflow", "keras", "fastapi", "spring boot",
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
    """Classifies natural-language queries into structured intents using ontology-informed matching."""

    def __init__(self, min_confidence: float = 0.0, ontology: Optional[SMEOntology] = None) -> None:
        """
        Args:
            min_confidence: Reserved for future confidence-weighted classification.
            ontology: Optional SMEOntology instance. If None, a new instance is created.
        """
        self.ontology = ontology or SMEOntology()
        self._triggers: Dict[QueryIntent, List[str]] = {
            QueryIntent.COMPARATIVE_QUERY: _COMPARATIVE_TRIGGERS,
            QueryIntent.METRICS_LOOKUP: _METRICS_TRIGGERS,
            QueryIntent.COMPANY_LOOKUP: _COMPANY_TRIGGERS,
            QueryIntent.SKILL_LOOKUP: _SKILL_TRIGGERS,
            QueryIntent.EXPERIENCE_LOOKUP: _EXPERIENCE_TRIGGERS,
            QueryIntent.GENERAL_QUERY: _GENERAL_TRIGGERS,
        }
        self._init_entity_vocabulary()

    def _init_entity_vocabulary(self) -> None:
        """Collect all canonical terms, synonyms, and categories from ontology for matching."""
        vocab: Set[str] = set()
        for term in self.ontology.SKILL_TAXONOMY:
            vocab.add(term.lower())
        for alias in self.ontology.SYNONYM_MAP:
            vocab.add(alias.lower())
        for cat in self.ontology.CATEGORY_CHILDREN_MAP:
            vocab.add(cat.lower())
        for token in _ADDITIONAL_TECH_TOKENS:
            vocab.add(token.lower())
        # Sort terms by descending length so multi-word matches take precedence
        self._entity_candidates: List[str] = sorted(vocab, key=lambda x: len(x), reverse=True)

    def extract_entities(self, query: str) -> List[str]:
        """Extract recognized technology terms and domain categories from query using SMEOntology."""
        normalized = _norm(query)
        if not normalized:
            return []

        matched_terms: List[str] = []
        seen_canonical: Set[str] = set()

        for term in self._entity_candidates:
            if not term.strip():
                continue
            escaped_term = re.escape(term)
            pattern = rf"(?<![a-zA-Z0-9]){escaped_term}(?![a-zA-Z0-9])"
            if re.search(pattern, normalized):
                canonical = self.ontology.normalize_term(term)
                target = canonical if canonical else term
                if target not in seen_canonical:
                    seen_canonical.add(target)
                    matched_terms.append(target)

        return matched_terms

    def classify(self, query: str) -> QueryIntent:
        """Determine the intent behind *query*.

        Classification priority:
        1. Comparative query — multi-entity / multi-company comparison
        2. Metrics lookup — quantitative metrics, cost savings, scale numbers, ROI
        3. General query — greetings, certifications, education, summaries, empty/short query
        4. Company lookup — queries asking where the candidate worked / employment history
        5. Experience lookup (strong) — queries specifically asking about building/leading/projects
        6. Skill lookup — queries asking about technologies/tools/skills or containing recognized tech entities
        7. Experience lookup — open-ended experience queries
        8. General query fallback — everything else
        """
        normalized = _norm(query)
        if not normalized or len(normalized) < 3:
            return QueryIntent.GENERAL_QUERY

        # 1. Comparative queries take precedence
        if _check_any(normalized, self._triggers[QueryIntent.COMPARATIVE_QUERY]):
            return QueryIntent.COMPARATIVE_QUERY

        # 2. Metrics lookup takes precedence next
        if _check_any(normalized, self._triggers[QueryIntent.METRICS_LOOKUP]):
            return QueryIntent.METRICS_LOOKUP

        # 3. Explicit general topics (education, certifications, greetings, summary)
        if _check_any(normalized, self._triggers[QueryIntent.GENERAL_QUERY]):
            if not _check_any(normalized, self._triggers[QueryIntent.SKILL_LOOKUP]):
                entities = self.extract_entities(normalized)
                if not entities:
                    return QueryIntent.GENERAL_QUERY

        # 4. Company lookup
        if _check_any(normalized, self._triggers[QueryIntent.COMPANY_LOOKUP]):
            return QueryIntent.COMPANY_LOOKUP

        # 5. Strong experience patterns (building, leading teams, architecture designed, projects built)
        strong_exp_patterns = [
            r"\b(experience\s+building|background\s+leading|leading\s+.*team|leading\s+engineering)\b",
            r"\b(projects?\s+has|projects?\s+built|projects?\s+managed|projects?\s+led)\b",
            r"\b(architecture\s+(he|prasad)?\s*designed|designed\s+the\s+architecture)\b",
            r"\b(describe|tell\s+me\s+about)\s+(his|prasad'?s?)?\s*(background|experience|achievement|achievements|career|projects?|contributions?)\b",
        ]
        if _check_any(normalized, strong_exp_patterns):
            return QueryIntent.EXPERIENCE_LOOKUP

        # 6. Skill lookup — explicit skill triggers or recognized tech entities
        if _check_any(normalized, self._triggers[QueryIntent.SKILL_LOOKUP]):
            return QueryIntent.SKILL_LOOKUP

        entities = self.extract_entities(normalized)
        if entities:
            return QueryIntent.SKILL_LOOKUP

        # 7. Open-ended experience lookup
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
                "enable_guardrail": True,
                "fallback_mode": "global",
                "description": "Focused entity search for technology/skill queries",
            },
            QueryIntent.COMPANY_LOOKUP: {
                "mode": "global",
                "top_k": 20,
                "entity_boost": False,
                "enable_guardrail": True,
                "fallback_mode": "local",
                "description": "Broad community aggregation for employment history",
            },
            QueryIntent.EXPERIENCE_LOOKUP: {
                "mode": "drift",
                "top_k": 12,
                "entity_boost": True,
                "enable_guardrail": True,
                "fallback_mode": "local",
                "description": "Drift mode for open-ended experience/project queries",
            },
            QueryIntent.METRICS_LOOKUP: {
                "mode": "local",
                "top_k": 15,
                "entity_boost": True,
                "enable_guardrail": True,
                "fallback_mode": "global",
                "description": "Targeted metric and quantitative impact extraction",
            },
            QueryIntent.COMPARATIVE_QUERY: {
                "mode": "global",
                "top_k": 20,
                "entity_boost": True,
                "enable_guardrail": True,
                "fallback_mode": "drift",
                "description": "Comparative multi-entity synthesis across communities and roles",
            },
            QueryIntent.GENERAL_QUERY: {
                "mode": "local",
                "top_k": 10,
                "entity_boost": False,
                "enable_guardrail": True,
                "fallback_mode": "global",
                "description": "Default fallback — balanced local search",
            },
        }
        return strategies.get(intent, strategies[QueryIntent.GENERAL_QUERY])

    def classify_with_details(self, query: str) -> Dict[str, object]:
        """Classify query with confidence score, extracted entities, intent, and suggested strategy."""
        normalized = _norm(query)
        if not normalized or len(normalized) < 3:
            intent = QueryIntent.GENERAL_QUERY
            strategy = self.get_retrieval_strategy(intent)
            return {
                "intent": intent.value,
                "primary_intent": intent.value,
                "confidence": 0.0,
                "extracted_entities": [],
                "suggested_strategy": strategy,
                "strategy": strategy,
                "match_details": {},
            }

        intent = self.classify(query)
        extracted_entities = self.extract_entities(query)
        strategy = self.get_retrieval_strategy(intent)

        # Collect match details for debugging
        matches = {}
        for q_intent, triggers in self._triggers.items():
            matched_triggers = []
            for t in triggers:
                if re.search(t, normalized):
                    matched_triggers.append(t)
            matches[q_intent.value] = {"matched_triggers": matched_triggers}

        # Calculate confidence score
        confidence = 0.50
        if intent == QueryIntent.COMPARATIVE_QUERY:
            matched_count = len(matches.get(QueryIntent.COMPARATIVE_QUERY.value, {}).get("matched_triggers", []))
            confidence = 0.95 if matched_count >= 2 else 0.90
        elif intent == QueryIntent.METRICS_LOOKUP:
            matched_count = len(matches.get(QueryIntent.METRICS_LOOKUP.value, {}).get("matched_triggers", []))
            confidence = 0.95 if matched_count >= 2 else 0.90
        elif intent == QueryIntent.COMPANY_LOOKUP:
            confidence = 0.88
        elif intent == QueryIntent.SKILL_LOOKUP:
            confidence = 0.92 if extracted_entities else 0.85
        elif intent == QueryIntent.EXPERIENCE_LOOKUP:
            confidence = 0.88
        elif intent == QueryIntent.GENERAL_QUERY:
            confidence = 0.80 if matches.get(QueryIntent.GENERAL_QUERY.value, {}).get("matched_triggers", []) else 0.50

        return {
            "intent": intent.value,
            "primary_intent": intent.value,
            "confidence": round(confidence, 2),
            "extracted_entities": extracted_entities,
            "suggested_strategy": strategy,
            "strategy": strategy,
            "match_details": matches,
        }
