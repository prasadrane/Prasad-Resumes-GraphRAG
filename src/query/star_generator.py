"""
star_generator.py — STAR Method Behavioral Interview Response Engine.

Synthesizes structured Situation, Task, Action, Result interview responses
from GraphRAG context and master resume story bank with quantified metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Dict, List, Optional

from src.generators.scoring import ImpactScorer
from src.generators.sme_ontology import SMEOntology
from src.query.static_graph_reader import search_static_resume

logger = logging.getLogger(__name__)


@dataclass
class STARResponse:
    """Structured STAR interview response."""
    situation: str
    task: str
    action: str
    result: str
    metrics: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    dimension: str = "general"

    def to_markdown(self) -> str:
        """Format STAR response as readable markdown."""
        lines = [
            f"### **Situation**\n{self.situation}\n",
            f"### **Task**\n{self.task}\n",
            f"### **Action**\n{self.action}\n",
            f"### **Result**\n{self.result}\n",
        ]
        if self.metrics:
            lines.append(f"**Quantified Metrics:** {', '.join(self.metrics)}\n")
        if self.technologies:
            lines.append(f"**Key Technologies:** {', '.join(self.technologies)}")
        return "\n".join(lines)


class STARGenerator:
    """
    Generates behavioral interview answers structured in the STAR methodology.
    """

    DIMENSIONS = {
        "cost_optimization": [r"\b(costs?|savings?|reduce expenses?|budget|roi|financial)\b"],
        "incident_response": [r"\b(incident|outage|production issue|bug|crash|failure|down)\b"],
        "leadership_conflict": [r"\b(conflict|disagreement|lead|leadership|stakeholder|mentor|influence)\b"],
        "architecture_scaling": [r"\b(scale|scaling|architecture|architect|migration|moderniz|microservices?)\b"],
    }

    def __init__(
        self,
        scorer: Optional[ImpactScorer] = None,
        ontology: Optional[SMEOntology] = None,
    ) -> None:
        self.scorer = scorer or ImpactScorer()
        self.ontology = ontology or SMEOntology()

    def classify_dimension(self, question: str) -> str:
        """Classify question into a core behavioral dimension."""
        q_lower = question.lower()
        for dim, patterns in self.DIMENSIONS.items():
            for pat in patterns:
                if re.search(pat, q_lower):
                    return dim
        return "architecture_scaling"

    def generate_star_response(
        self,
        question: str,
        context: Optional[str] = None,
    ) -> STARResponse:
        """
        Generate structured STAR response from question and candidate knowledge context.
        """
        dimension = self.classify_dimension(question)
        source_text = context if (context and context.strip()) else search_static_resume(question, mode="local")

        # Detect metrics and technologies from source text
        metrics = self.scorer.detect_metrics(source_text)
        techs: List[str] = []
        for syn in self.ontology.SYNONYM_MAP.keys():
            if len(syn) >= 3 and re.search(r"\b" + re.escape(syn) + r"\b", source_text, re.IGNORECASE):
                techs.append(syn.title())
        techs = sorted(list(set(techs)))[:6]

        # Extract sentences from context for STAR mapping
        sentences = [s.strip() for s in re.split(r"[.\n•-]", source_text) if len(s.strip()) > 15]

        # Synthesize STAR sections
        situation = (
            f"At Rocket Mortgage / enterprise environment, legacy monolith workflows and high transaction volumes "
            f"created performance bottlenecks and operational scaling challenges."
        )
        task = (
            f"Tasked with modernizing mission-critical services, establishing robust governance, "
            f"and delivering automated high-throughput cloud infrastructure."
        )
        action = (
            f"Engineered cloud-native services using {', '.join(techs[:3]) if techs else 'AWS and .NET Core'}, "
            f"integrated automated CI/CD pipelines, and resolved architectural bottlenecks through structured monitoring."
        )
        result = (
            f"Successfully improved reliability, achieved {metrics[0] if metrics else 'significant latency and throughput improvements'}, "
            f"and enabled zero-downtime deployments across engineering teams."
        )

        if sentences:
            action_candidates = [s for s in sentences if any(v in s.lower() for v in ["architected", "engineered", "built", "modernized", "implemented"])]
            if action_candidates:
                action = action_candidates[0]

            result_candidates = [s for s in sentences if any(m in s for m in metrics)] if metrics else []
            if result_candidates:
                result = result_candidates[0]

        return STARResponse(
            situation=situation,
            task=task,
            action=action,
            result=result,
            metrics=metrics[:4],
            technologies=techs,
            dimension=dimension,
        )
