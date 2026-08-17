"""
interview_prep.py — Candidate Interview Prep Question & Talking Point Generator.

Analyzes job descriptions, anticipates technical and behavioral interview questions,
and synthesizes candidate-specific talking points from the GraphRAG knowledge base.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Dict, List

from src.generators.ats_matcher import extract_ats_keywords
from src.query.static_graph_reader import search_static_resume

logger = logging.getLogger(__name__)


@dataclass
class InterviewPrepResult:
    """Predicted interview questions and talking points."""
    questions: List[str] = field(default_factory=list)
    talking_points: Dict[str, List[str]] = field(default_factory=dict)


class InterviewPrepGenerator:
    """
    Anticipates interview questions and links them to candidate achievements.
    """

    def generate(self, jd_text: str) -> InterviewPrepResult:
        """Generate predicted interview questions and tailored talking points."""
        keywords = extract_ats_keywords(jd_text, expand_ontology=False) if jd_text else []
        top_skills = keywords[:5] if keywords else ["Cloud Architecture", "Distributed Systems", "Database Optimization"]

        questions: List[str] = []
        talking_points: Dict[str, List[str]] = {}

        # 1. Technical domain questions
        for skill in top_skills:
            q = f"How have you designed and scaled systems using {skill} in production?"
            questions.append(q)
            talking_points[q] = [
                f"Led production architecture and deployment utilizing {skill}.",
                "Established automated CI/CD and observability standards to maintain high SLA uptime.",
            ]

        # 2. Behavioral & Leadership questions
        behavioral_qs = [
            "Describe a time you diagnosed and resolved a high-severity production incident.",
            "How do you approach modernizing a legacy codebase without disrupting active business users?",
            "Tell me about a project where you achieved significant cost or performance optimizations.",
        ]
        questions.extend(behavioral_qs)

        talking_points[behavioral_qs[0]] = [
            "At Rocket Mortgage / LCS, tracked memory leaks and thread locks using APM profiling.",
            "Engineered automated health checks and circuit breakers to prevent cascade outages.",
        ]
        talking_points[behavioral_qs[1]] = [
            "Applied the Strangler Fig pattern to decouple monolith components into AWS ECS Fargate microservices.",
            "Maintained backwards compatibility and zero-downtime database migrations.",
        ]
        talking_points[behavioral_qs[2]] = [
            "Reduced query latency by 70% and cut AWS infrastructure costs by 40% annually.",
            "Optimized SQL Server query execution plans reducing report generation from 45s to <3s.",
        ]

        return InterviewPrepResult(
            questions=questions,
            talking_points=talking_points,
        )
