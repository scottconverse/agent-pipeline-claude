"""Pytest wrapper for scripts/check_skill_packaging.py.

Runs the standalone validator as a subprocess and asserts a clean exit. This
makes the packaging check part of the normal test gate so every commit-worthy
diff is checked for self-contained skills.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = REPO_ROOT / "scripts" / "check_skill_packaging.py"


def test_skill_packaging_passes() -> None:
    """Every skill must be self-contained per check_skill_packaging.py rules."""
    assert CHECK_SCRIPT.exists(), f"missing check script at {CHECK_SCRIPT}"

    result = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        msg = (
            f"check_skill_packaging.py failed (exit {result.returncode}):\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
        raise AssertionError(msg)

    assert "SKILL-PACKAGING: PASSED" in result.stdout, (
        f"expected PASSED line in stdout, got:\n{result.stdout}"
    )
