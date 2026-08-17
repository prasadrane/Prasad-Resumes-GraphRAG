"""
judge_evaluator.py — Automated LLM-as-a-Judge Evaluation & Hallucination Auditor.

Audits generated resume bullets against ground truth master resume facts, grading for
factual faithfulness, metric preservation, and hallucination suppression.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import List, Set

from src.generators.scoring import ImpactScorer
from src.generators.sme_ontology import SMEOntology

logger = logging.getLogger(__name__)

_STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "by", "from",
    "of", "is", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "into", "across", "using", "through", "over", "under", "prasad",
}


@dataclass
class JudgeScore:
    """Evaluation output from the Judge auditor."""
    faithfulness: float  # 0.0 to 1.0
    hallucination_detected: bool
    unsupported_claims: List[str] = field(default_factory=list)
    critique: str = "Faithfully grounded in context."


class LLMJudgeEvaluator:
    """
    Evaluates factual alignment between generated content and master facts.
    """

    def __init__(
        self,
        faithfulness_threshold: float = 0.70,
        scorer: Optional[ImpactScorer] = None,
        ontology: Optional[SMEOntology] = None,
    ) -> None:
        self.threshold = faithfulness_threshold
        self.scorer = scorer or ImpactScorer()
        self.ontology = ontology or SMEOntology()

    def evaluate(self, generated_bullet: str, ground_truth_context: str) -> JudgeScore:
        """Score generated bullet against ground truth context for hallucinations."""
        if not generated_bullet or not generated_bullet.strip():
            return JudgeScore(faithfulness=1.0, hallucination_detected=False)
        if not ground_truth_context or not ground_truth_context.strip():
            return JudgeScore(
                faithfulness=0.0,
                hallucination_detected=True,
                unsupported_claims=[generated_bullet],
                critique="No ground truth context provided to verify claim.",
            )

        context_lower = ground_truth_context.lower()
        bullet_tokens = [
            t.lower()
            for t in re.findall(r"\b[a-zA-Z0-9#+.-]{3,}\b", generated_bullet)
            if t.lower() not in _STOPWORDS
        ]

        if not bullet_tokens:
            return JudgeScore(faithfulness=1.0, hallucination_detected=False)

        # Check token and entity support in ground truth context
        supported_tokens: List[str] = []
        unsupported_tokens: List[str] = []

        for token in bullet_tokens:
            if token in context_lower:
                supported_tokens.append(token)
            else:
                norm = self.ontology.normalize_term(token)
                if norm and norm.lower() in context_lower:
                    supported_tokens.append(token)
                else:
                    unsupported_tokens.append(token)

        # Metric verification
        gen_metrics = self.scorer.detect_metrics(generated_bullet)
        context_metrics = self.scorer.detect_metrics(ground_truth_context)
        unsupported_metrics = [m for m in gen_metrics if m.lower() not in [cm.lower() for cm in context_metrics]]

        faithfulness = len(supported_tokens) / len(bullet_tokens) if bullet_tokens else 1.0

        if unsupported_metrics:
            faithfulness = max(0.0, faithfulness - 0.25 * len(unsupported_metrics))

        hallucination_detected = (faithfulness < self.threshold) or (len(unsupported_metrics) > 0)
        unsupported_claims = [f"Unsupported entity/metric: {t}" for t in unsupported_tokens[:3] + unsupported_metrics] if hallucination_detected else []

        critique = "Claim is well-grounded in candidate experience." if not hallucination_detected else "Contains unverified technical terms or fabricated metrics."

        return JudgeScore(
            faithfulness=round(faithfulness, 2),
            hallucination_detected=hallucination_detected,
            unsupported_claims=unsupported_claims,
            critique=critique,
        )
