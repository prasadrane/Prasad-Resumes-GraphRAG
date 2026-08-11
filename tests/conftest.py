"""
Shared pytest fixtures for unit tests.

These fixtures are consumed by pytest-style test functions (see
tests/test_pdf_parser.py and tests/test_static_graph_reader.py).
unittest discovery ignores this file.
"""

import pytest


@pytest.fixture
def sample_master_resume_text() -> str:
    """Minimal master-resume document shaped like input/MASTER_RESUME.txt."""
    return (
        "# Prasad Rane\n"
        "Senior Software Engineer\n"
        "\n"
        "## SUMMARY\n"
        "Engineer with cloud, AI, and distributed systems experience.\n"
        "\n"
        "## EXPERIENCE\n"
        "- Built AWS ECS Fargate microservices with Python and Kafka.\n"
        "\n"
        "## SKILLS\n"
        "Python, AWS, Docker, Terraform, SQL\n"
    )
