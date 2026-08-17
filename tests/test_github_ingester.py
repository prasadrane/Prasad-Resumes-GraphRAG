"""
Unit tests for GitHub Ingestion Pipeline.
"""

import tempfile
from pathlib import Path
import unittest

from src.converters.github_ingester import GitHubIngester, GitHubProjectStory


class TestGitHubIngester(unittest.TestCase):
    """Test suite for repository analysis and story bank conversion."""

    def setUp(self):
        self.ingester = GitHubIngester()

    def test_parse_repo_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_path = Path(tmp_dir) / "prasad-graphrag"
            repo_path.mkdir(parents=True)

            readme = repo_path / "README.md"
            readme.write_text(
                "# Prasad Resumes GraphRAG\n\n"
                "A high-performance GraphRAG knowledge graph that generates ATS-tailored resumes on AWS and Vercel.\n"
                "Built using Python, FastAPI, and ReportLab.\n",
                encoding="utf-8",
            )

            # Add sample code files
            (repo_path / "main.py").write_text("print('hello')", encoding="utf-8")
            (repo_path / "service.py").write_text("class Service: pass", encoding="utf-8")

            story = self.ingester.parse_directory(repo_path)
            self.assertIsInstance(story, GitHubProjectStory)
            self.assertEqual(story.repo_name, "prasad-graphrag")
            self.assertIn("Python", story.languages)
            self.assertIn("GraphRAG", story.description)

            md = self.ingester.format_story_markdown(story)
            self.assertIn("### Project: prasad-graphrag", md)
            self.assertIn("Python", md)


if __name__ == "__main__":
    unittest.main()
