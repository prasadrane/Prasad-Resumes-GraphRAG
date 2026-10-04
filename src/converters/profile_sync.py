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


def normalize_master(text: str, employers: dict, profile: dict) -> str:
    """Adapt ledger export headings/contact fields to the existing resume parser."""
    contact = [profile["location"], profile["phone"], profile["email"]]
    contact.extend(link["url"] for link in profile.get("links", []))
    lines = [f'# {profile["name"]}', f'**Title:** {profile["headline"]}',
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
                    lines.append("### Independent Projects and Professional Development")
            continue
        if section is None:
            continue
        if section == "Professional Experience":
            if line.startswith("Generated from"):
                continue
            if line.startswith("### "):
                company, role = line[4:].rsplit(" | ", 1)
                identity = next((v for k, v in employers.items()
                                 if company in (k, v.get("display_name"))), None)
                if identity is None:
                    raise ValueError(f"No employer identity for {company}")
                lines.append(f'### {role} | {company} | {identity["location"]} | {identity["dates"]}')
                continue
            if line and not line.startswith(("- ", "**")):
                continue  # location/date line already included in job heading
            if line.startswith("**") and line.endswith("**"):
                lines.append("#### " + line.strip("*"))
                continue
        if section in ("Certification", "Education") and line.strip() and not line.startswith("- "):
            line = "- " + line
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def sync_profile(source_root: Path = None, target_root: Path = ROOT, profile_name: str = "prasad-rane") -> dict:
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
    master = normalize_master((profile_dir / "resume/Staff_Master_Resume.md").read_text(encoding="utf-8"),
                              employers, profile)
    payloads = {"MASTER_RESUME.txt": master}
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
    snapshot = target_root / "input" / "MASTER_RESUME.txt"
    if not snapshot.exists() or snapshot.read_text(encoding="utf-8") != master:
        snapshot.write_text(master, encoding="utf-8")
    return {"source": str(profile_dir), "documents": len(payloads), "changed": changed, "removed": removed}
