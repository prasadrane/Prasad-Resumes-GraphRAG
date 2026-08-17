"""
github_ingester.py — GitHub Repository & Open-Source Portfolio Ingestion Pipeline.

Parses local/remote GitHub repositories, analyzing READMEs, file extensions, and architectures
into structured candidate project stories for GraphRAG indexing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
import re
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

_EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    ".py": "Python",
    ".cs": "C#",
    ".ts": "TypeScript",
    ".js": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".cpp": "C++",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
}


@dataclass
class GitHubProjectStory:
    """Parsed repository project story."""
    repo_name: str
    description: str
    languages: List[str] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)


class GitHubIngester:
    """
    Parses code repositories into candidate story bank entries.
    """

    def parse_directory(self, repo_dir: Path) -> GitHubProjectStory:
        """Analyze repository folder, extracting description from README and detected languages."""
        repo_name = repo_dir.name
        readme_path = repo_dir / "README.md"
        description = f"Software project: {repo_name}"
        highlights: List[str] = []

        if readme_path.exists():
            try:
                content = readme_path.read_text(encoding="utf-8")
                lines = [l.strip() for l in content.splitlines() if l.strip()]
                # Extract first paragraph after title
                desc_lines = [l for l in lines if not l.startswith("#") and len(l) > 15]
                if desc_lines:
                    description = desc_lines[0]
            except Exception as exc:
                logger.warning("Failed to read README in %s: %s", repo_dir, exc)

        # Detect primary languages from file extensions
        detected_languages: Set[str] = set()
        for item in repo_dir.rglob("*"):
            if item.is_file() and not item.name.startswith("."):
                ext = item.suffix.lower()
                if ext in _EXTENSION_LANGUAGE_MAP:
                    detected_languages.add(_EXTENSION_LANGUAGE_MAP[ext])

        sorted_langs = sorted(list(detected_languages))

        highlights.append(f"Engineered and maintained {repo_name} using {', '.join(sorted_langs) if sorted_langs else 'modern software engineering standards'}.")
        highlights.append("Built modular automated test suites and structured architecture documentation.")

        return GitHubProjectStory(
            repo_name=repo_name,
            description=description,
            languages=sorted_langs,
            highlights=highlights,
        )

    def format_story_markdown(self, story: GitHubProjectStory) -> str:
        """Format GitHub project story as a GraphRAG knowledge graph section."""
        lines = [
            f"### Project: {story.repo_name}",
            f"**Technologies:** {', '.join(story.languages)}",
            f"**Summary:** {story.description}\n",
        ]
        for h in story.highlights:
            lines.append(f"- {h}")
        return "\n".join(lines)
