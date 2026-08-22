"""
grounding_auditor.py ? Anti-hallucination and truthfulness verification auditor.

Validates that technical claims, metrics, and tools mentioned in generated resumes
are grounded in the candidate's master story bank and experience repository.
"""

import re
from typing import List, Tuple, Set


class GroundingAuditor:
    """Audits text against master candidate background to detect fabricated claims or tools."""

    def __init__(self, master_content: str = ""):
        self.master_content = master_content
        self.master_tokens = self._tokenize(master_content)

    def _tokenize(self, text: str) -> Set[str]:
        words = re.findall(r"\b[a-zA-Z0-9+#.-]{3,}\b", text.lower())
        stopwords = {
            "and", "the", "with", "for", "from", "using", "into", "that", "this",
            "over", "under", "per", "across", "within", "built", "designed",
            "implemented", "engineered", "reduced", "led", "achieved", "developed",
            "company", "experience", "summary", "skills", "technologies"
        }
        return {w for w in words if w not in stopwords}

    def audit(self, text: str) -> Tuple[float, List[str]]:
        """
        Audit bullet points / narrative against master background tokens.
        Returns (grounding_score_0_to_100, list_of_violations).
        """
        if not text.strip():
            return 0.0, ["Empty text provided for grounding audit."]
        if not self.master_tokens:
            return 100.0, []

        lines = [line.strip() for line in text.split("\n") if line.strip().startswith("- ")]
        if not lines:
            lines = [line.strip() for line in text.split("\n") if len(line.strip()) > 25 and not line.strip().startswith("#")]

        if not lines:
            return 100.0, []

        violations: List[str] = []
        grounded_count = 0
        total_items = len(lines)

        for line in lines:
            line_tokens = self._tokenize(line)
            if not line_tokens:
                grounded_count += 1
                continue

            overlap = line_tokens.intersection(self.master_tokens)
            overlap_ratio = len(overlap) / len(line_tokens) if line_tokens else 1.0

            # If fewer than 25% of distinctive terms match master background, flag as ungrounded
            if overlap_ratio < 0.25:
                violations.append(f"Unverified claim or technology not in master story bank: '{line[:100]}...'")
            else:
                grounded_count += 1

        score = round((grounded_count / total_items) * 100.0, 1)
        return score, violations
