"""
scoring.py — Action-Verb Impact Scoring & Recency Decay Engine.

Provides rule-based impact scoring based on action-verb hierarchies, quantified metric
detection, and exponential recency decay modeling.
"""

from datetime import datetime
import math
import re
from typing import List, Optional, Union
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Gazetteers for Action-Verb Classification
# ---------------------------------------------------------------------------

TIER_1_VERBS = {
    "architected",
    "spearheaded",
    "engineered",
    "orchestrated",
    "pioneered",
    "designed",
    "founded",
    "transformed",
}

TIER_1_VARIANTS = {
    "architect",
    "architecting",
    "spearhead",
    "spearheading",
    "engineer",
    "engineering",
    "orchestrate",
    "orchestrating",
    "pioneer",
    "pioneering",
    "design",
    "designing",
    "found",
    "founding",
    "transform",
    "transforming",
}

TIER_2_VERBS = {
    "implemented",
    "developed",
    "built",
    "optimized",
    "migrated",
    "scaled",
    "delivered",
    "automated",
    "integrated",
}

TIER_2_VARIANTS = {
    "implement",
    "implementing",
    "develop",
    "developing",
    "build",
    "building",
    "optimize",
    "optimizing",
    "migrate",
    "migrating",
    "scale",
    "scaling",
    "deliver",
    "delivering",
    "automate",
    "automating",
    "integrate",
    "integrating",
    "led",
    "lead",
    "leading",
    "executed",
    "execute",
    "executing",
}

TIER_3_VERBS = {
    "maintained",
    "supported",
    "assisted",
    "monitored",
    "updated",
    "documented",
    "troubleshot",
}

TIER_3_VARIANTS = {
    "maintain",
    "maintaining",
    "support",
    "supporting",
    "assist",
    "assisting",
    "monitor",
    "monitoring",
    "update",
    "updating",
    "document",
    "documenting",
    "troubleshoot",
    "troubleshooting",
    "troubleshooted",
}

TIER_SCORES = {
    1: 1.0,
    2: 0.7,
    3: 0.4,
    0: 0.5,  # Fallback for other verbs
}


# ---------------------------------------------------------------------------
# Metric Detection Regex Patterns
# ---------------------------------------------------------------------------

METRIC_PATTERNS = [
    # Percentages: e.g. 70%, 40%, 99.9%
    re.compile(r"\b\d+(?:\.\d+)?\s?%", re.IGNORECASE),
    # Currencies: e.g. $1.2M, $500K, $25,000, €100M
    re.compile(
        r"[\$€£¥]\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?\s?[kKmMbBtT]?\+?\b|\b\d+(?:\.\d+)?\s?[kKmMbBtT]?\s?(?:USD|EUR|GBP)\b",
        re.IGNORECASE,
    ),
    # Multipliers / speedup: e.g. 2.5x, 10x, 3X
    re.compile(r"\b\d+(?:\.\d+)?\s?[xX]\b"),
    # Latency / time units: e.g. 50ms, 200μs, 1.5s, 500 ms
    re.compile(
        r"\b\d+(?:\.\d+)?\s?(?:ms|millisecond(?:s)?|microsecond(?:s)?|μs|us|s|sec(?:ond)?(?:s)?|min(?:ute)?(?:s)?|hr(?:s)?|hour(?:s)?)\b",
        re.IGNORECASE,
    ),
    # Scale indicators with units: e.g. 10k users, 5M requests, 100+ microservices, 1M+ queries
    re.compile(
        r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s?[kKmMbB]?\+?\s+(?:users|customers|clients|requests|rps|qps|queries|events|records|rows|messages|transactions|connections|endpoints|services|microservices|pipelines|repos|repositories|nodes|instances|servers|engineers|developers|members|dau|mau)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b\d+\+\s+(?:users|customers|clients|requests|rps|qps|queries|events|records|rows|messages|transactions|connections|endpoints|services|microservices|pipelines|repos|repositories|nodes|instances|servers|engineers|developers|members|dau|mau)\b",
        re.IGNORECASE,
    ),
    # Throughput rates: e.g. 10k requests/sec, 500 req/s, 1000 ops/sec
    re.compile(
        r"\b\d+(?:\.\d+)?\s?[kKmMbBtT]?\+?\s+(?:requests/sec|req/s|ops/sec|tps)\b",
        re.IGNORECASE,
    ),
]


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class ScoreBreakdown(BaseModel):
    """Structured breakdown of bullet impact, recency, and overall composite score."""
    verb_score: float
    metric_bonus: float
    impact_score: float
    recency_score: float
    duration_score: float = 1.0
    final_score: float
    detected_metrics: List[str] = Field(default_factory=list)
    verb_tier: int = 0


# ---------------------------------------------------------------------------
# Impact Scorer Engine
# ---------------------------------------------------------------------------

class ImpactScorer:
    """
    Engine for action-verb impact classification, quantified metric bonus detection,
    exponential recency decay calculation, and composite bullet scoring.
    """

    @classmethod
    def _extract_lead_word(cls, bullet: str) -> str:
        """Extracts and normalizes the leading verb/word from a bullet point."""
        if not bullet or not isinstance(bullet, str):
            return ""

        # Remove leading bullet symbols, list markers, and markdown prefixes
        cleaned = bullet.strip()
        cleaned = re.sub(r"^[\s\-\*\•\>]+", "", cleaned)
        cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned)
        # Remove bold/italic markdown at start
        cleaned = re.sub(r"^[\*\_`]+", "", cleaned)

        # Match first word token
        match = re.match(r"^([a-zA-Z]+(?:-[a-zA-Z]+)?)", cleaned.strip())
        if not match:
            return ""

        lead = match.group(1).lower().strip(".,:;!?-")

        # Skip leading adverbs if followed by a verb (e.g. "Successfully architected")
        adverbs = {"successfully", "effectively", "collaboratively", "consistently", "proactively"}
        if lead in adverbs:
            tokens = re.findall(r"[a-zA-Z]+(?:-[a-zA-Z]+)?", cleaned)
            if len(tokens) > 1:
                return tokens[1].lower().strip(".,:;!?-")

        return lead

    @classmethod
    def get_verb_tier(cls, bullet: str) -> int:
        """
        Determines the tier of the action verb in the bullet.
        Returns:
            1: Tier 1 (architected, spearheaded, engineered, orchestrated, pioneered, designed, founded, transformed)
            2: Tier 2 (implemented, developed, built, optimized, migrated, scaled, delivered, automated, integrated)
            3: Tier 3 (maintained, supported, assisted, monitored, updated, documented, troubleshot)
            0: Fallback / other verbs
        """
        lead_word = cls._extract_lead_word(bullet)
        if not lead_word:
            return 0

        if lead_word in TIER_1_VERBS or lead_word in TIER_1_VARIANTS:
            return 1
        if lead_word in TIER_2_VERBS or lead_word in TIER_2_VARIANTS:
            return 2
        if lead_word in TIER_3_VERBS or lead_word in TIER_3_VARIANTS:
            return 3
        return 0

    @classmethod
    def get_verb_score(cls, bullet: str) -> float:
        """
        Returns the base verb score corresponding to the bullet's action verb tier:
        - Tier 1: 1.0
        - Tier 2: 0.7
        - Tier 3: 0.4
        - Fallback: 0.5
        """
        tier = cls.get_verb_tier(bullet)
        return TIER_SCORES.get(tier, 0.5)

    @classmethod
    def detect_metrics(cls, bullet: str) -> List[str]:
        """
        Detects quantified metrics (percentages, currency, latency, scale) within the bullet.
        """
        if not bullet or not isinstance(bullet, str):
            return []

        results = []
        seen = set()
        for pattern in METRIC_PATTERNS:
            for match in pattern.finditer(bullet):
                matched_text = match.group(0).strip()
                norm = matched_text.lower()
                if norm not in seen:
                    seen.add(norm)
                    results.append(matched_text)
        return results

    @classmethod
    def get_metric_bonus(cls, bullet: str, bonus_value: float = 0.2) -> float:
        """
        Computes metric bonus (+0.2 if quantified metrics are present, capped at 1.0).
        """
        metrics = cls.detect_metrics(bullet)
        if metrics:
            return min(1.0, float(bonus_value))
        return 0.0

    @classmethod
    def calculate_recency_decay(
        cls,
        start_year: Optional[Union[int, str]] = None,
        end_year: Optional[Union[int, str]] = None,
        reference_year: Optional[int] = None,
        lambda_decay: float = 0.15,
    ) -> float:
        """
        Calculates exponential recency decay: e^(-lambda * delta_t),
        where delta_t = max(0, reference_year - end_year).
        """
        ref_year = reference_year if reference_year is not None else datetime.now().year
        if end_year is None:
            effective_end = ref_year
        elif isinstance(end_year, str):
            end_str = end_year.strip().lower()
            if end_str in {"present", "current", "now", ""}:
                effective_end = ref_year
            else:
                match = re.search(r"\b(20\d{2}|19\d{2})\b", end_year)
                effective_end = int(match.group(1)) if match else ref_year
        else:
            effective_end = int(end_year)

        delta_t = max(0.0, float(ref_year - effective_end))
        decay = math.exp(-lambda_decay * delta_t)
        return max(0.0, min(1.0, decay))

    @classmethod
    def score_bullet(
        cls,
        bullet: str,
        start_year: Optional[Union[int, str]] = None,
        end_year: Optional[Union[int, str]] = None,
        duration_years: Optional[float] = None,
        alpha: float = 0.25,
        beta: float = 0.35,
        gamma: float = 0.40,
        reference_year: Optional[int] = None,
        lambda_decay: float = 0.15,
    ) -> ScoreBreakdown:
        """
        Calculates parameterized composite weight:
        W = alpha * Duration + beta * Recency + gamma * ImpactScore
        (default alpha=0.25, beta=0.35, gamma=0.40).

        Returns:
            ScoreBreakdown with verb_score, metric_bonus, impact_score,
            recency_score, duration_score, and final_score.
        """
        ref_year = reference_year if reference_year is not None else datetime.now().year
        verb_tier = cls.get_verb_tier(bullet)
        verb_score = cls.get_verb_score(bullet)
        detected_metrics = cls.detect_metrics(bullet)
        metric_bonus = cls.get_metric_bonus(bullet)
        impact_score = min(1.0, verb_score + metric_bonus)

        recency_score = cls.calculate_recency_decay(
            start_year=start_year,
            end_year=end_year,
            reference_year=ref_year,
            lambda_decay=lambda_decay,
        )

        if duration_years is not None:
            if duration_years <= 1.0:
                duration_score = max(0.0, float(duration_years))
            else:
                duration_score = min(1.0, max(0.0, float(duration_years) / 5.0))
        else:
            duration_score = 1.0

        final_score = (alpha * duration_score) + (beta * recency_score) + (gamma * impact_score)

        return ScoreBreakdown(
            verb_score=verb_score,
            metric_bonus=metric_bonus,
            impact_score=impact_score,
            recency_score=recency_score,
            duration_score=duration_score,
            final_score=final_score,
            detected_metrics=detected_metrics,
            verb_tier=verb_tier,
        )
