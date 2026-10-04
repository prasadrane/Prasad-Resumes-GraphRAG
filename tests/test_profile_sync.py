import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.converters.profile_sync import normalize_master, sync_profile
from src.generators.resume_parser import parse_master_resume


def test_normalized_export_preserves_identity_and_sections():
    profile = {"name": "Example", "headline": "Engineer", "location": "Remote",
               "phone": "123-456-7890", "email": "test@example.com"}
    employers = {"Acme": {"location": "Remote", "dates": "2020 - 2025"}}
    text = """# Example
## Professional Summary
Builds services.
## Professional Experience
### Acme | Developer
Remote | 2020 - 2025
**A story**
- Delivered a service. `[confirmed]` `S01-B1`
## Independent Engineering
- Built a tool.
## Education
A degree
## Technology index
- Python: S01-B1
"""
    resume = parse_master_resume(normalize_master(text, employers, profile))
    assert resume.contact_email == "test@example.com"
    assert resume.jobs[0].company == "Acme"
    assert resume.jobs[0].dates == "2020 - 2025"
    assert resume.jobs[0].bullet_stories == ["A story"]
    assert resume.education == ["A degree"]
    assert resume.projects[0].bullets == ["Built a tool."]


def make_source(root):
    profile = root / "profiles/prasad-rane"
    (root / "engine").mkdir(parents=True)
    (root / "engine/kb_cli.py").write_text("", encoding="utf-8")
    (profile / "resume").mkdir(parents=True)
    (profile / "cards").mkdir()
    (profile / "resume/profile.json").write_text(json.dumps({"name": "Example", "headline": "Engineer",
        "location": "Remote", "phone": "1234567890", "email": "e@example.com"}), encoding="utf-8")
    (profile / "resume/employers.json").write_text("{}", encoding="utf-8")
    (profile / "resume/Staff_Master_Resume.md").write_text("## Professional Summary\nExample", encoding="utf-8")
    (profile / "cards/story-01.md").write_text("# Story\n```yaml\nold: data\n```\nA narrative", encoding="utf-8")
    (profile / "cards/story-01.metadata.json").write_text('{"status": "confirmed"}', encoding="utf-8")
    return profile


@patch("src.converters.profile_sync.subprocess.run")
def test_sync_updates_prunes_and_preserves_unrelated_files(run, tmp_path):
    run.return_value.returncode = 0
    source, target = tmp_path / "source", tmp_path / "target"
    profile = make_source(source)
    assert sync_profile(source, target)["changed"] == 2
    assert sync_profile(source, target)["changed"] == 0
    destination = target / "input/centralized"
    content = (destination / "story-01.txt").read_text(encoding="utf-8")
    assert "old: data" not in content and '"status": "confirmed"' in content
    (destination / "story-99.txt").write_text("stale", encoding="utf-8")
    (destination / "notes.txt").write_text("keep", encoding="utf-8")
    (profile / "cards/story-01.md").write_text("Changed narrative", encoding="utf-8")
    result = sync_profile(source, target)
    assert result["changed"] == 1 and result["removed"] == 1
    assert (destination / "notes.txt").exists()


@patch("src.converters.profile_sync.subprocess.run")
def test_failed_validation_does_not_change_inputs(run, tmp_path):
    run.return_value.returncode = 1
    run.return_value.stdout = "stale export"
    run.return_value.stderr = ""
    source, target = tmp_path / "source", tmp_path / "target"
    make_source(source)
    with pytest.raises(ValueError, match="stale export"):
        sync_profile(source, target)
    assert not (target / "input").exists()
