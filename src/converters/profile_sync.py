"""Read-only import of a validated central story profile into GraphRAG inputs."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def default_profile_root() -> Path:
    return Path(os.environ.get("PROFILE_SOURCE_ROOT", ROOT.parent / "Prasad-Rane-Profile"))


def normalize_master(text: str, employers: dict, profile: dict, presentation: dict = None) -> str:
    """Export current facts in resume syntax; ledger annotations stay in evidence inputs."""
    presentation = presentation or {}
    selected_ids = presentation.get("bullet_ids")
    if selected_ids is not None:
        available_ids = set(re.findall(r"`(S\d+-B\d+)`", text))
        missing = set(selected_ids) - available_ids
        if missing or len(set(selected_ids)) != len(selected_ids):
            raise ValueError(f"Invalid presentation bullet IDs: {sorted(missing)}")
    skill_lines = None
    project_lines = None
    if "projects" in presentation:
        source_projects = {p["name"]: p["text"] for p in profile.get("independent_projects", [])}
        project_lines = []
        for project in presentation["projects"]:
            if not project["text"] or project["text"] not in source_projects.get(project["name"], ""):
                raise ValueError(f"Presentation project excerpt absent from current profile: {project['name']}")
            project_lines.append(f'- **{project["name"]}:** {project["text"]}')

    def compact_dates(value):
        return re.sub(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\b",
                      lambda match: match[0][:3], value)
    if "skills" in presentation:
        # Exact source-token matching prevents the old layout from reintroducing
        # superseded framework versions or unsupported tools.
        source_items = {item.strip().rstrip(".") for group in profile.get("skills", [])
                        for item in group["items"].split(",")}
        skill_lines = []
        for group in presentation["skills"]:
            missing = set(group["items"]) - source_items
            if missing:
                raise ValueError(f"Presentation skill absent from current profile: {sorted(missing)}")
            skill_lines.append(f'- **{group["group"]}**: ' + ", ".join(group["items"]))
    contact = [profile["location"], profile["phone"], profile["email"]]
    contact.extend(link["url"] for link in profile.get("links", []))
    lines = [f'# {profile["name"].upper()}', f'**Title:** {profile["headline"]}',
             "**Contact:** " + " | ".join(contact), ""]
    section = None
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            if section in ("Editorial References", "Technology index", "Competency index"):
                break
            headings = {"Professional Summary": "SUMMARY", "Professional Experience": "EXPERIENCE",
                        "Independent Engineering": "PROJECTS", "Technical Skills": "SKILLS",
                        "Certification": "CERTIFICATIONS", "Education": "EDUCATION"}
            if section == "Role-specific Summary Options":
                lines.extend(["### Domain-Specific Summary Variants", ""])
            else:
                lines.append("## " + headings.get(section, section))
                if section == "Independent Engineering":
                    lines.append("### Independent Projects and Professional Development | "
                                 + compact_dates(profile.get("independent_period", "")))
                    if project_lines is not None:
                        lines.extend(project_lines)
                if section == "Technical Skills" and skill_lines is not None:
                    lines.extend(skill_lines)
            continue
        if section is None:
            continue
        if section == "Independent Engineering" and project_lines is not None:
            continue
        if section == "Technical Skills" and skill_lines is not None:
            continue
        if section == "Technical Skills":
            line = re.sub(r"^(- \*\*[^*]+?):\*\*", r"\1**:", line)
        if section == "Professional Experience":
            if line.startswith("Generated from"):
                continue
            if line.startswith("### "):
                company, role = line[4:].rsplit(" | ", 1)
                identity = next((v for k, v in employers.items()
                                 if company in (k, v.get("display_name"))), None)
                if identity is None:
                    raise ValueError(f"No employer identity for {company}")
                lines.append(f'### {role} | {company} | {identity["location"]} | {compact_dates(identity["dates"])}')
                continue
            if line and not line.startswith(("- ", "**")):
                continue  # location/date line already included in job heading
            if line.startswith("**") and line.endswith("**"):
                lines.append("#### " + line.strip("*"))
                continue
            if line.startswith("- "):
                bullet_id = re.search(r"`(S\d+-B\d+)`\s*$", line)
                if selected_ids is not None and (not bullet_id or bullet_id[1] not in selected_ids):
                    continue
                line = re.sub(r"\s+`\[[a-z_]+\]`\s+`S\d+-B\d+`\s*$", "", line)
        if section in ("Certification", "Education") and line.strip() and not line.startswith("- "):
            line = "- " + line
        if section == "Certification":
            line = compact_dates(line)
        if section == "Education" and line.startswith("- "):
            fields = line[2:].split(" | ")
            if len(fields) == 3:
                line = f'- **{fields[0]}**, {fields[1]} ({fields[2]})'
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def sync_profile(source_root: Path = None, target_root: Path = ROOT, profile_name: str = "prasad-rane",
                 dry_run: bool = False) -> dict:
    source_root = (source_root or default_profile_root()).resolve()
    profile_dir = source_root / "profiles" / profile_name
    validator = source_root / "engine" / "kb_cli.py"
    if not validator.is_file() or not profile_dir.is_dir():
        raise FileNotFoundError(f"Central profile unavailable: {profile_dir}")
    validation = subprocess.run([sys.executable, str(validator), "--profile", str(profile_dir),
                                 "validate", "--strict"], capture_output=True, text=True, encoding="utf-8")
    if validation.returncode:
        raise ValueError("Central profile validation failed; build/repair it before syncing:\n"
                         + validation.stdout + validation.stderr)
    profile = json.loads((profile_dir / "resume/profile.json").read_text(encoding="utf-8"))
    employers = json.loads((profile_dir / "resume/employers.json").read_text(encoding="utf-8"))
    source_master = (profile_dir / "resume/Staff_Master_Resume.md").read_text(encoding="utf-8")
    presentation_path = target_root / "config" / "resume_presentation.json"
    presentation = json.loads(presentation_path.read_text(encoding="utf-8")) if presentation_path.exists() else None
    master = normalize_master(source_master, employers, profile, presentation=presentation)
    # Retrieval retains complete evidence; public presentation is a separate projection.
    payloads = {"MASTER_RESUME.txt": source_master}
    for card in sorted((profile_dir / "cards").glob("story-*.md")):
        metadata = json.loads(card.with_suffix(".metadata.json").read_text(encoding="utf-8"))
        narrative = re.sub(r"```yaml\s*\n.*?```", "", card.read_text(encoding="utf-8"), flags=re.S)
        payloads[card.stem + ".txt"] = (f"Source: {profile_name}/cards/{card.name}\n"
            "Evidence statuses and proposed work below must retain their original scope.\n\n"
            + narrative.strip() + "\n\nAuthoritative ledger:\n" + json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    if len(payloads) == 1:
        raise ValueError("Central profile contains no story cards; nothing imported")
    # Finish validation and reads before changing any local inputs. Never write to the source.
    destination = target_root / "input" / "centralized"
    changed_files = ["centralized/" + name for name, content in payloads.items()
                     if not (destination / name).exists()
                     or (destination / name).read_text(encoding="utf-8") != content]
    snapshot = target_root / "input" / "MASTER_RESUME.txt"
    master_changed = not snapshot.exists() or snapshot.read_text(encoding="utf-8") != master
    if master_changed:
        changed_files.append("MASTER_RESUME.txt")
    stale_paths = [path for path in destination.glob("story-*.txt")
                   if re.fullmatch(r"story-\d+\.txt", path.name) and path.name not in payloads]
    if dry_run:
        return {"source": str(profile_dir), "documents": len(payloads), "dry_run": True,
                "changed_files": changed_files, "removed_files": [p.name for p in stale_paths]}
    destination.mkdir(parents=True, exist_ok=True)
    changed = 0
    for name, content in payloads.items():
        path = destination / name
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")
            changed += 1
    # Prune only this importer's fixed filenames; preserve unrelated inputs.
    removed = 0
    for path in destination.glob("story-*.txt"):
        if re.fullmatch(r"story-\d+\.txt", path.name) and path.name not in payloads:
            path.unlink()
            removed += 1
    if master_changed:
        snapshot.write_text(master, encoding="utf-8")
    return {"source": str(profile_dir), "documents": len(payloads), "changed": changed, "removed": removed,
            "master_changed": master_changed, "changed_files": changed_files, "dry_run": False}
