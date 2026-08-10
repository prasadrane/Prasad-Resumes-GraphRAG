"""
run_e2e_baseline.py — One-command runner for the Phase 0 E2E safety net.

Runs the deterministic Playwright baseline against the local UI server.
Exits non-zero if any baseline test fails, making it usable as a gate.

Usage:
    python scripts/run_e2e_baseline.py           # deterministic baseline
    python scripts/run_e2e_baseline.py --live     # also run live LLM tests
"""

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def main() -> int:
    live = "--live" in sys.argv
    marker = "live or not live" if live else "not live"
    cmd = [
        sys.executable, "-m", "pytest", "tests/e2e/",
        "-v", "-m", marker,
    ]
    print(f"[E2E] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
