"""
linkedin_optimizer.py — LinkedIn Profile & Headline Optimizer.

Synthesizes recruiter-optimized LinkedIn profiles including 220-character headlines,
narrative "About" sections, and keyword-rich experience bullet points.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import List

from src.query.static_graph_reader import search_static_resume

logger = logging.getLogger(__name__)


@dataclass
class LinkedInProfileData:
    """Optimized LinkedIn profile components."""
    headline: str
    about_section: str
    experience_bullets: List[str] = field(default_factory=list)
    core_skills: List[str] = field(default_factory=list)


class LinkedInOptimizer:
    """
    Synthesizes search-optimized LinkedIn assets.
    """

    def optimize(
        self,
        target_role: str = "Senior Software Engineer / Tech Lead",
        candidate_name: str = "Prasad Rane",
    ) -> LinkedInProfileData:
        """Generate optimized headline, about section, and skill tags."""
        # 220-character LinkedIn headline limit
        headline = (
            f"{target_role} | AWS ECS Fargate, Kafka, .NET Core, Python | "
            f"Enterprise Cloud Modernization & GenAI Microservices"
        )
        if len(headline) > 220:
            headline = headline[:217] + "..."

        about = (
            f"Over a decade of experience architecting and delivering high-throughput cloud platforms, "
            f"distributed microservices, and enterprise streaming architectures.\n\n"
            f"🌟 Core Impact Highlights:\n"
            f"• Modernized enterprise monoliths to AWS ECS Fargate, cutting query latency by 70% and infrastructure costs by 40%.\n"
            f"• Built Amazon Bedrock (Claude Sonnet) GenAI chatbot integrations accelerating automated loan workflows.\n"
            f"• Established enterprise Kafka/MSK governance, schema registries, and high-concurrency event pipelines.\n\n"
            f"Technologies: AWS, Docker, Kubernetes, Kafka, Python, C# / .NET Core, SQL Server, Redis, FastAPI, REST APIs."
        )

        core_skills = [
            "Cloud Architecture",
            "AWS ECS Fargate",
            "Apache Kafka",
            "Python",
            "C# / .NET Core",
            "Microservices",
            "Distributed Systems",
            "Amazon Bedrock",
            "SQL Server",
            "FastAPI",
        ]

        bullets = [
            "Architected AWS ECS Fargate microservices and Bedrock AI chatbots reducing loan turnaround times by 70%.",
            "Established cross-team Kafka event streaming standards and schema validation rules.",
            "Optimized relational query plans reducing batch analytics latency from 45s to <3s.",
        ]

        return LinkedInProfileData(
            headline=headline,
            about_section=about,
            experience_bullets=bullets,
            core_skills=core_skills,
        )
