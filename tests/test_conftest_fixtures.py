"""
Sanity checks that shared conftest fixtures are wired and well-formed.
Pytest-style (fixture parameters); not collected by unittest discovery.
"""


def test_sample_master_resume_text_has_sections(sample_master_resume_text):
    assert sample_master_resume_text.startswith("# Prasad Rane")
    for section in ("## SUMMARY", "## EXPERIENCE", "## SKILLS"):
        assert section in sample_master_resume_text


def test_sample_master_resume_text_has_expected_content(sample_master_resume_text):
    assert "AWS ECS Fargate" in sample_master_resume_text
    assert "Python, AWS, Docker, Terraform, SQL" in sample_master_resume_text
