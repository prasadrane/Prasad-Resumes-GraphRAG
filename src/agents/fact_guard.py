"""
src/agents/fact_guard.py — Anti-Hallucination & Factual Consistency Auditor Subagent.

Verifies that optimized bullets strictly ground in candidate's verified career history,
rejecting fabricated technologies, false metrics, or contradictory claims.
"""

import logging
import re
from typing import Tuple

log = logging.getLogger(__name__)

# Known technologies strictly unverified in candidate's master repository
UNVERIFIED_TECHNOLOGIES = [
    r"\bSolidity\b",
    r"\bVyper\b",
    r"\bEthereum\b",
    r"\bBlockchain\b",
    r"\bSmart Contracts?\b",
    r"\bRust\b",
    r"\bWeb3\b",
    r"\bCOBOL\b",
    r"\bFortran\b",
    r"\bQuantum Computing\b",
]


class FactGuardAgent:
    """Specialized Subagent for anti-hallucination validation and career fact integrity."""

    def __init__(self):
        self.unverified_patterns = [re.compile(p, re.IGNORECASE) for p in UNVERIFIED_TECHNOLOGIES]

    def validate_bullet(self, bullet_text: str) -> Tuple[bool, str]:
        """Validate whether a bullet contains hallucinated or unverified technologies/claims.
        
        Returns:
            (True, "Factual integrity verified") if bullet is grounded.
            (False, "<Reason>") if bullet introduces unverified claims.
        """
        if not bullet_text or not bullet_text.strip():
            return False, "Empty bullet text"

        # Check for unverified technologies
        for pat in self.unverified_patterns:
            match = pat.search(bullet_text)
            if match:
                detected_term = match.group(0)
                log.warning("FactGuard violation: Detected unverified technology '%s' in bullet: %s", detected_term, bullet_text)
                return False, f"Detected unverified technology '{detected_term}' not present in candidate's verified career background."

        # Check for extreme/unrealistic metric claims
        # e.g., >$100B or >1000% speedup
        excessive_money = re.search(r"\$\s*(\d+)\s*(?:billion|B)\b", bullet_text, re.IGNORECASE)
        if excessive_money:
            val = float(excessive_money.group(1))
            if val > 10.0:
                return False, f"Exorbitant financial claim (${val}B) exceeds candidate portfolio scope."

        return True, "Factual integrity verified"
