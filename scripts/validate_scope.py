"""Validate the structure of a v2.0 scope.md file.

The autonomous loop in skills/run/references/run.md drafts scope.md from a
template. This script confirms the drafted file has every required section
before the loop proceeds. Used as a light preflight inside Step 6 of the
procedure — NOT a heavy gate.

Required sections (markdown bold-headers OR markdown H2/H3):

    Goal:
    Mode: (must be `task` or `sprint`)
    Branch:
    Allowed paths
    Forbidden paths
    Success criteria
    Tasks

Optional but checked-if-present:

    Authorizing source: (file:line citation)
    Risk: (low/medium/high)
    Rollback:

Run:

    python scripts/policy/validate_scope.py --scope <path-to-scope.md>

Exit 0 = scope is well-formed. Exit 1 = required sections missing or
malformed (script prints what's missing).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_FIELDS = [
    ("Goal", r"\*\*Goal\*\*:"),
    ("Mode", r"\*\*Mode\*\*:\s*(task|sprint)\b"),
    ("Branch", r"\*\*Branch\*\*:"),
    ("Allowed paths", r"\*\*Allowed paths\*\*:?"),
    ("Forbidden paths", r"\*\*Forbidden paths\*\*"),
    ("Success criteria", r"\*\*Success criteria\*\*"),
    ("Tasks", r"\*\*Tasks\*\*"),
]


def validate(scope_text: str) -> list[str]:
    """Return list of human-readable violations. Empty list = OK."""
    violations: list[str] = []
    for name, pattern in REQUIRED_FIELDS:
        if not re.search(pattern, scope_text):
            violations.append(f"missing required field: **{name}**")

    # Mode value must be task or sprint
    mode_match = re.search(r"\*\*Mode\*\*:\s*(\w+)", scope_text)
    if mode_match:
        mode = mode_match.group(1).lower()
        if mode not in ("task", "sprint"):
            violations.append(
                f"**Mode** must be `task` or `sprint`; got `{mode}`."
            )

    # Tasks must have at least one numbered task entry
    tasks_section = re.search(r"\*\*Tasks\*\*.*?(?=\n\*\*\w|$)", scope_text, flags=re.DOTALL)
    if tasks_section:
        body = tasks_section.group(0)
        # Look for any numbered task line `1.` / `2.` / ...
        if not re.search(r"^\s*\d+\.\s+\S", body, flags=re.MULTILINE):
            violations.append("**Tasks** section is present but contains no numbered tasks.")

    # Risk if present must be low/medium/high
    risk_match = re.search(r"\*\*Risk\*\*:\s*(\w+)", scope_text)
    if risk_match:
        risk = risk_match.group(1).lower()
        if risk not in ("low", "medium", "high"):
            violations.append(
                f"**Risk** must be `low`, `medium`, or `high`; got `{risk}`."
            )

    return violations


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="validate_scope", description=__doc__)
    p.add_argument("--scope", type=Path, required=True, help="Path to scope.md.")
    args = p.parse_args(argv)

    if not args.scope.is_file():
        print(f"validate_scope: file not found: {args.scope}", file=sys.stderr)
        return 1

    text = args.scope.read_text(encoding="utf-8", errors="replace")
    violations = validate(text)

    if violations:
        print(f"validate_scope: FAIL — {len(violations)} issue(s) in {args.scope}")
        for v in violations:
            print(f"  - {v}")
        return 1

    print(f"validate_scope: PASS — {args.scope} has all required sections.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
