"""
delta_indexer.py — Incremental Delta GraphRAG Indexer.

Tracks chunk-level SHA-256 hashes of source files (e.g. MASTER_RESUME.txt, story banks)
and detects modified chunks to avoid expensive full-graph re-indexing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.config import CACHE_DIR_PATH, ROOT_DIR

logger = logging.getLogger(__name__)


@dataclass
class DeltaDiffReport:
    """Report of changed chunks between runs."""
    has_changes: bool
    added_or_modified_chunks: List[Tuple[str, str]] = field(default_factory=list)  # (chunk_id, content)
    deleted_chunk_ids: List[str] = field(default_factory=list)
    current_hashes: Dict[str, str] = field(default_factory=dict)


class DeltaGraphIndexer:
    """
    Computes incremental delta changes on source text files to avoid redundant graph indexing.
    """

    def __init__(self, manifest_path: Optional[Path] = None) -> None:
        self.manifest_path = manifest_path or (CACHE_DIR_PATH / "delta_manifest.json")

    @staticmethod
    def _chunk_text(text: str) -> Dict[str, str]:
        """Split text into semantic section chunks keyed by header title."""
        sections = text.split("\n## ")
        chunks: Dict[str, str] = {}
        for i, sec in enumerate(sections):
            lines = sec.strip().split("\n")
            header = lines[0].replace("#", "").strip() if lines else f"section_{i}"
            chunks[header] = sec.strip()
        return chunks

    def compute_diff(self, source_file: Path) -> DeltaDiffReport:
        """Compare current source file chunk hashes against stored manifest."""
        if not source_file.exists():
            return DeltaDiffReport(has_changes=False)

        with open(source_file, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = self._chunk_text(text)
        current_hashes: Dict[str, str] = {}
        for chunk_id, content in chunks.items():
            current_hashes[chunk_id] = hashlib.sha256(content.encode("utf-8")).hexdigest()

        previous_hashes: Dict[str, str] = {}
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    previous_hashes = json.load(f)
            except Exception as exc:
                logger.warning("Failed to load manifest %s: %s", self.manifest_path, exc)

        added_or_modified: List[Tuple[str, str]] = []
        for chunk_id, h in current_hashes.items():
            if chunk_id not in previous_hashes or previous_hashes[chunk_id] != h:
                added_or_modified.append((chunk_id, chunks[chunk_id]))

        deleted: List[str] = [cid for cid in previous_hashes if cid not in current_hashes]

        has_changes = len(added_or_modified) > 0 or len(deleted) > 0

        return DeltaDiffReport(
            has_changes=has_changes,
            added_or_modified_chunks=added_or_modified,
            deleted_chunk_ids=deleted,
            current_hashes=current_hashes,
        )

    def save_manifest(self, source_file: Path, report: DeltaDiffReport) -> None:
        """Persist current hashes to manifest file."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(report.current_hashes, f, indent=2)
