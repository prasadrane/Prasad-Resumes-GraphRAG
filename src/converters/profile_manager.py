"""
profile_manager.py — Multi-Profile & Multi-Track Story Bank Manager.

Enables loading and managing multiple candidate personas or specialized career tracks
(e.g., Staff Backend, AI/ML Engineer, Solutions Architect) with fallback to default master resume.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from src.config import ROOT_DIR

logger = logging.getLogger(__name__)


@dataclass
class CandidateProfile:
    """Candidate profile model representing a candidate persona or specialization track."""
    candidate_id: str
    name: str = "Prasad Rane"
    title: str = "Senior Software Engineer / Tech Lead"
    email: str = "prasad.rane@example.com"
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    location: str = "United States"
    master_resume_text: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)


class ProfileManager:
    """
    Manages loading, caching, and querying multiple candidate profiles and story banks.
    """

    def __init__(self, profiles_dir: Optional[Path] = None) -> None:
        self.profiles_dir = profiles_dir or (ROOT_DIR / "candidates")
        self._profiles_cache: Dict[str, CandidateProfile] = {}

    def get_profile(self, candidate_id: str = "default") -> CandidateProfile:
        """
        Retrieve candidate profile by ID. If 'default' or not found on disk,
        loads the repository's base MASTER_RESUME.txt.
        """
        if candidate_id in self._profiles_cache:
            return self._profiles_cache[candidate_id]

        profile_path = self.profiles_dir / candidate_id / "profile.yaml"
        resume_path = self.profiles_dir / candidate_id / "resume.txt"

        if profile_path.exists():
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}

                resume_text = ""
                if resume_path.exists():
                    with open(resume_path, "r", encoding="utf-8") as f:
                        resume_text = f.read()

                profile = CandidateProfile(
                    candidate_id=candidate_id,
                    name=data.get("name", "Candidate"),
                    title=data.get("title", ""),
                    email=data.get("email", ""),
                    phone=data.get("phone", ""),
                    linkedin=data.get("linkedin", ""),
                    github=data.get("github", ""),
                    location=data.get("location", ""),
                    master_resume_text=resume_text,
                    metadata=data.get("metadata", {}),
                )
                self._profiles_cache[candidate_id] = profile
                return profile
            except Exception as exc:
                logger.warning("Failed to load profile %s: %s; falling back to default.", candidate_id, exc)

        # Default fallback: Load ROOT_DIR / input / MASTER_RESUME.txt
        default_resume = ROOT_DIR / "input" / "MASTER_RESUME.txt"
        default_text = ""
        if default_resume.exists():
            with open(default_resume, "r", encoding="utf-8") as f:
                default_text = f.read()

        default_profile = CandidateProfile(
            candidate_id="default",
            name="Prasad Rane",
            title="Senior Software Engineer / Tech Lead",
            master_resume_text=default_text,
        )
        self._profiles_cache["default"] = default_profile
        return default_profile

    def list_profiles(self) -> List[Dict[str, str]]:
        """List all discovered profiles on disk along with default profile."""
        profiles = [{"id": "default", "name": "Prasad Rane", "title": "Senior Software Engineer"}]
        if self.profiles_dir.exists():
            for child in self.profiles_dir.iterdir():
                if child.is_dir() and (child / "profile.yaml").exists():
                    p = self.get_profile(child.name)
                    if p.candidate_id != "default":
                        profiles.append({"id": p.candidate_id, "name": p.name, "title": p.title})
        return profiles
