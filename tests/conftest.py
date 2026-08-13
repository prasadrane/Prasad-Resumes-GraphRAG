"""
Shared pytest fixtures for unit tests.

These fixtures are consumed by pytest-style test functions (see
tests/test_pdf_parser.py and tests/test_static_graph_reader.py).
unittest discovery ignores this file.
"""

import pytest

# Minimum valid JD text that passes the ResumeGenerationRequest validator:
# ≥50 characters AND ≥10 meaningful words (>1 char each).
VALID_JD_TEXT = (
    "Senior software engineer with experience in Python, AWS, Docker, "
    "Kubernetes, and microservices architecture. Must have strong background "
    "in distributed systems and cloud-native development."
)


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset module-level singletons before each test to prevent pollution."""
    try:
        from src.query.graphrag_engine import reset_engine
        from src.query.conversation_store import reset_conversation_store
        reset_engine()
        reset_conversation_store()
    except ImportError:
        pass
    yield


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
