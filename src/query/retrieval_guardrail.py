"""
retrieval_guardrail.py — Self-Healing Retrieval Guardrail Agent.

Evaluates GraphRAG retrieval context quality (token density, entity coverage, relevance)
and autonomously heals low-quality or empty context by escalating retrieval modes
(local -> drift -> global) and expanding query entities via SMEOntology.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Callable, List, NamedTuple, Optional, Set, Tuple, Union

try:
    from src.generators.sme_ontology import SMEOntology
    _HAS_ONTOLOGY = True
except ImportError:
    SMEOntology = None  # type: ignore
    _HAS_ONTOLOGY = False

logger = logging.getLogger(__name__)

# Common English stopwords to ignore when extracting candidate entities from queries
_STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "can", "could", "did", "do", "does", "doing",
    "down", "during", "each", "few", "for", "from", "further", "had", "has", "have",
    "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how",
    "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most",
    "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "our", "ours", "ourselves", "out", "over", "own", "prasad", "prasad's",
    "rane", "same", "she", "should", "so", "some", "such", "than", "that", "the",
    "their", "theirs", "them", "themselves", "then", "there", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "with", "work", "worked", "working", "experience", "background", "role", "tell",
    "give", "describe", "detail", "details", "list", "show", "summary",
}


@dataclass
class ContextQualityReport:
    """Evaluation report on retrieved context quality."""
    is_sufficient: bool
    token_count: int
    entity_coverage: float
    relevance_score: float
    detected_issues: List[str] = field(default_factory=list)
    suggested_action: str = "proceed"


@dataclass
class HealingTraceStep:
    """Step in self-healing execution trace."""
    attempt: int
    mode: str
    query: str
    quality_report: ContextQualityReport
    action_taken: str = ""
    context_preview: str = ""


class HealedRetrievalResult(NamedTuple):
    """Result of self-healing retrieval supporting 2-tuple unpacking (context, trace)."""
    context: str
    trace: List[HealingTraceStep]

    @property
    def final_report(self) -> Optional[ContextQualityReport]:
        return self.trace[-1].quality_report if self.trace else None


def _call_retrieval(fn: Callable, query: str, mode: str) -> str:
    """Safely invoke retrieval function with keyword/positional mode support."""
    try:
        res = fn(query, mode=mode)
    except TypeError:
        try:
            res = fn(query, mode)
        except TypeError:
            res = fn(query)
    return str(res) if res is not None else ""


class RetrievalGuardrail:
    """
    Self-Healing Guardrail for knowledge graph retrieval.

    Evaluates retrieved context completeness, entity coverage, and token density,
    triggering automated fallback chains and query expansions if retrieval is insufficient.
    """

    def __init__(
        self,
        min_tokens: int = 30,
        min_entity_coverage: float = 0.3,
        ontology: Optional[SMEOntology] = None,
        fallback_chain: Optional[List[str]] = None,
    ) -> None:
        self.min_tokens = min_tokens
        self.min_entity_coverage = min_entity_coverage
        self.ontology = ontology or (SMEOntology() if _HAS_ONTOLOGY and SMEOntology else None)
        self.fallback_chain = fallback_chain or ["local", "drift", "global"]

    def _extract_entities_from_query(self, query: str) -> List[str]:
        """Extract high-signal candidate entity terms and technical keywords from query."""
        if not query or not query.strip():
            return []

        clean_query = query.strip()
        entities: List[str] = []
        seen: Set[str] = set()

        def add_entity(e: str):
            c = e.strip().lower()
            if c and c not in seen and c not in _STOPWORDS and len(c) > 1:
                seen.add(c)
                entities.append(e.strip())

        # Check ontology taxonomy directly for multi-word or single-word matches with word boundaries
        if self.ontology:
            for syn in sorted(self.ontology.SYNONYM_MAP.keys(), key=len, reverse=True):
                pattern = r"(?:\b|_)" + re.escape(syn) + r"(?:\b|_)"
                if re.search(pattern, clean_query, re.IGNORECASE):
                    add_entity(syn)
            for skill in sorted(self.ontology.SKILL_TAXONOMY.keys(), key=len, reverse=True):
                pattern = r"(?:\b|_)" + re.escape(skill) + r"(?:\b|_)"
                if re.search(pattern, clean_query, re.IGNORECASE):
                    add_entity(skill)

        # Regex tokenization preserving special tech symbols (.net, c#, node.js, ci/cd)
        words = re.findall(r"[\w\+\#\.\/\-]+", clean_query)
        for word in words:
            w_clean = re.sub(r"^[\.\,\/\-]+|[\.\,\/\-]+$", "", word)
            if w_clean:
                add_entity(w_clean)

        return entities

    def _entity_in_context(self, entity: str, context: str) -> bool:
        """Check if an entity or its ontology synonyms/canonical form appear in context."""
        if not entity or not context:
            return False

        context_lower = context.lower()
        entity_lower = entity.lower().strip()

        # Direct containment check
        if entity_lower in context_lower:
            return True

        # Special symbols or aliases
        pattern = r"(?:\b|_)" + re.escape(entity_lower) + r"(?:\b|_)"
        if re.search(pattern, context_lower):
            return True

        # Ontology synonym & canonical checks
        if self.ontology:
            norm = self.ontology.normalize_term(entity_lower)
            if norm and norm != entity_lower:
                if norm in context_lower:
                    return True
                norm_pattern = r"(?:\b|_)" + re.escape(norm) + r"(?:\b|_)"
                if re.search(norm_pattern, context_lower):
                    return True

        return False

    def evaluate_context(
        self,
        query: str,
        context: Optional[str],
        extracted_entities: Optional[List[str]] = None,
    ) -> ContextQualityReport:
        """
        Evaluate retrieved context quality against token density and entity coverage thresholds.
        """
        raw_text = (context or "").strip()
        tokens = raw_text.split() if raw_text else []
        token_count = len(tokens)

        # Empty context check
        if token_count == 0:
            return ContextQualityReport(
                is_sufficient=False,
                token_count=0,
                entity_coverage=0.0,
                relevance_score=0.0,
                detected_issues=["empty_context"],
                suggested_action="fallback_drift",
            )

        detected_issues: List[str] = []

        # Token density check
        if token_count < self.min_tokens:
            detected_issues.append("low_token_density")

        # Entity coverage check
        targets = (
            extracted_entities
            if extracted_entities is not None
            else self._extract_entities_from_query(query)
        )

        if targets:
            matched = [e for e in targets if self._entity_in_context(e, raw_text)]
            entity_coverage = round(len(matched) / len(targets), 2)
            if len(matched) == 0:
                detected_issues.append("zero_entity_overlap")
            elif entity_coverage < self.min_entity_coverage:
                detected_issues.append("low_entity_coverage")
        else:
            entity_coverage = 1.0

        # Calculate relevance score (0.0 - 1.0)
        token_density_ratio = min(1.0, token_count / max(self.min_tokens * 2, 60))
        if "zero_entity_overlap" in detected_issues:
            relevance_score = round(min(0.2, 0.1 * token_density_ratio), 2)
        elif "low_token_density" in detected_issues:
            relevance_score = round(
                min(0.5, 0.5 * entity_coverage + 0.2 * (token_count / self.min_tokens)), 2
            )
        else:
            relevance_score = round(
                min(1.0, 0.6 * entity_coverage + 0.4 * token_density_ratio), 2
            )

        is_sufficient = len(detected_issues) == 0

        # Suggest next action
        if is_sufficient:
            suggested_action = "proceed"
        else:
            if "zero_entity_overlap" in detected_issues:
                suggested_action = "expand_ontology_entities"
            elif "low_token_density" in detected_issues:
                suggested_action = "fallback_drift"
            else:
                suggested_action = "fallback_drift"

        return ContextQualityReport(
            is_sufficient=is_sufficient,
            token_count=token_count,
            entity_coverage=entity_coverage,
            relevance_score=relevance_score,
            detected_issues=detected_issues,
            suggested_action=suggested_action,
        )

    def _get_next_mode(self, current_mode: str) -> str:
        """Find the next mode in the fallback ladder."""
        curr_clean = current_mode.lower().strip()
        if curr_clean in self.fallback_chain:
            idx = self.fallback_chain.index(curr_clean)
            if idx + 1 < len(self.fallback_chain):
                return self.fallback_chain[idx + 1]
        return "global"

    def _has_ontology_alias(self, query: str) -> bool:
        """Check if query contains terms mapped to canonical forms in SYNONYM_MAP."""
        if not self.ontology or not query.strip():
            return False
        for syn in self.ontology.SYNONYM_MAP:
            pattern = r"(?:\b|_)" + re.escape(syn) + r"(?:\b|_)"
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _expand_query_with_ontology(self, query: str) -> Optional[str]:
        """Expand query with canonical technology terms, parent categories, and child skills."""
        if not self.ontology or not query.strip():
            return None

        terms = self._extract_entities_from_query(query)
        if not terms:
            return None

        new_terms: List[str] = []
        for t in terms:
            norm = self.ontology.normalize_term(t)
            if norm and norm.lower() != t.lower() and norm.lower() not in query.lower():
                new_terms.append(norm)

            parents = self.ontology.get_parent_categories(t)
            for p in parents:
                if p.lower() not in query.lower() and p.lower() not in [x.lower() for x in new_terms]:
                    new_terms.append(p.lower())

            children = self.ontology.get_child_skills(t)
            for c in children:
                if c.lower() not in query.lower() and c.lower() not in [x.lower() for x in new_terms]:
                    new_terms.append(c.lower())

        if not new_terms:
            return None

        expanded_str = " ".join(new_terms[:4])
        return f"{query} {expanded_str}".strip()

    def heal_retrieval(
        self,
        query: str,
        current_mode: str = "local",
        retrieval_fn: Optional[Callable[..., str]] = None,
        max_retries: int = 2,
    ) -> HealedRetrievalResult:
        """
        Execute self-healing retrieval.

        1. Queries retrieval_fn with current mode.
        2. Evaluates context quality.
        3. If insufficient, retries with alternative modes or ontology-expanded queries.
        4. Returns the best healed context and complete execution trace.
        """
        if retrieval_fn is None:
            from src.query.search_engine import execute_graphrag_query
            retrieval_fn = execute_graphrag_query

        trace: List[HealingTraceStep] = []
        best_context: str = ""
        best_score: float = -1.0

        active_mode = current_mode
        active_query = query
        ontology_expanded_tried = False

        attempt = 1
        max_attempts = 1 + max_retries

        while attempt <= max_attempts:
            try:
                raw_context = _call_retrieval(retrieval_fn, active_query, active_mode)
            except Exception as exc:
                logger.warning(
                    "Retrieval failed for mode=%s query='%s': %s",
                    active_mode,
                    active_query,
                    exc,
                )
                raw_context = ""

            report = self.evaluate_context(query, raw_context)

            # Score this attempt
            score = report.relevance_score
            if report.is_sufficient:
                score += 1.0

            if score > best_score or (score == best_score and len(raw_context) > len(best_context)):
                best_score = score
                best_context = raw_context

            if report.is_sufficient:
                trace.append(
                    HealingTraceStep(
                        attempt=attempt,
                        mode=active_mode,
                        query=active_query,
                        quality_report=report,
                        action_taken="proceed",
                        context_preview=raw_context[:100],
                    )
                )
                return HealedRetrievalResult(context=raw_context, trace=trace)

            # Context was insufficient, plan next self-healing action
            is_last_attempt = (attempt == max_attempts)

            has_alias = self._has_ontology_alias(active_query)

            if has_alias and not ontology_expanded_tried:
                expanded = self._expand_query_with_ontology(active_query)
                if expanded and expanded != active_query:
                    action_taken = "expand_ontology_and_retry"
                    next_query = expanded
                    next_mode = active_mode
                    ontology_expanded_tried = True
                else:
                    next_mode = self._get_next_mode(active_mode)
                    action_taken = f"fallback_to_{next_mode}"
                    next_query = query
            else:
                next_mode = self._get_next_mode(active_mode)
                action_taken = f"fallback_to_{next_mode}"
                next_query = query

            trace.append(
                HealingTraceStep(
                    attempt=attempt,
                    mode=active_mode,
                    query=active_query,
                    quality_report=report,
                    action_taken=action_taken if not is_last_attempt else "exhausted_retries",
                    context_preview=raw_context[:100],
                )
            )

            if is_last_attempt:
                break

            active_mode = next_mode
            active_query = next_query
            attempt += 1

        return HealedRetrievalResult(context=best_context, trace=trace)
