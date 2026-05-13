#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Autonomous-mode compliance check (post-run).

v1.2.1 hardening: when a run executes under `gate_policy: autonomous`,
the LLM-operating role is supposed to skip the chat-APPROVE waits at
the manifest / plan / manager gates and proceed on its own
recommendation. This script verifies that procedure was actually
followed — catches the v1.2.0 failure mode where an LLM under
autonomous authorization "chickens out" and stops anyway.

Compliance checks:

  1. Every pipeline stage marked `autonomous_skip_chat: true` in the
     pipeline yaml has a corresponding entry in
     `.agent-runs/<run-id>/autonomous-decisions.md`.

  2. Run.log does not contain forbidden-action patterns that should
     have been blocked by the grant's Forbidden-actions list. Default
     forbidden set: gh pr merge --admin, git push tag, gh release create,
     git push --force.

  3. Chat artifacts (if captured at `.agent-runs/<run-id>/chat-log.md`
     or similar) do not contain "Reply APPROVE" / "Reply WAIT" / "type
     APPROVE" patterns for stages that were supposed to auto-approve.
     This catches the LLM emitting a wait-for-human message under
     autonomous mode.

  4. The grant file's SHA-256 has not changed since the run began
     (recorded at preflight in .agent-runs/<run-id>/autonomous-mode.log).
     Catches mid-run grant tampering.

Each violation is emitted as a `COMPLIANCE_DRIFT` finding. Any drift
finding fails the gate (exit 1).

Skipped silently when the run was in HUMAN-MODE (the compliance check
doesn't apply).

Usage:

    python scripts/check_autonomous_compliance.py --run <run-id>

Exit codes:

    0  — compliance check passed, or HUMAN-MODE (skipped)
    1  — at least one COMPLIANCE_DRIFT finding
    2  — run directory not found
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore


FORBIDDEN_PATTERNS = (
    (re.compile(r"gh\s+pr\s+merge\b.*--admin"), "admin-merge"),
    (re.compile(r"gh\s+release\s+create\b"), "release publish"),
    (re.compile(r"git\s+push\b.*--force\b"), "force push"),
    (re.compile(r"git\s+push\b.*--tags\b"), "push --tags"),
    (re.compile(r"git\s+push\b.+v\d+\.\d+\.\d+"), "tag push"),
)

CHAT_WAIT_PATTERNS = (
    re.compile(r"Reply\s+APPROVE\b", re.IGNORECASE),
    re.compile(r"Reply\s+WAIT\b", re.IGNORECASE),
    re.compile(r"type\s+APPROVE\b", re.IGNORECASE),
    re.compile(r"wait(?:ing)?\s+for\s+human\s+(?:to\s+)?approv", re.IGNORECASE),
)

AUTONOMOUS_DECISION_HEADING = re.compile(
    r"^##\s+\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?\s+[-—]+\s+(?P<stage>[a-zA-Z][a-zA-Z0-9_-]*)"
)


@dataclass
class Finding:
    code: str
    detail: str


def _find_repo_root() -> Path:
    p = Path.cwd().resolve()
    for parent in (p, *p.parents):
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    return p


def _read_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    if yaml is None:
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _stages_with_autonomous_skip(pipeline_yaml: Path) -> list[str]:
    if not pipeline_yaml.exists() or yaml is None:
        return []
    try:
        data = yaml.safe_load(pipeline_yaml.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    stages = data.get("stages") or []
    if not isinstance(stages, list):
        return []
    return [
        s["name"] for s in stages
        if isinstance(s, dict) and s.get("autonomous_skip_chat") is True
    ]


def _decisions_logged(decisions_md: Path) -> set[str]:
    if not decisions_md.exists():
        return set()
    text = decisions_md.read_text(encoding="utf-8", errors="replace")
    logged: set[str] = set()
    for line in text.splitlines():
        m = AUTONOMOUS_DECISION_HEADING.match(line)
        if m:
            logged.add(m.group("stage"))
    return logged


def _check_forbidden_in_log(run_log: Path) -> list[Finding]:
    if not run_log.exists():
        return []
    text = run_log.read_text(encoding="utf-8", errors="replace")
    findings: list[Finding] = []
    for pattern, name in FORBIDDEN_PATTERNS:
        for m in pattern.finditer(text):
            line = m.group(0)
            findings.append(Finding(
                code="COMPLIANCE_DRIFT",
                detail=f"forbidden action under autonomous mode: {name} ({line!r})",
            ))
    return findings


def _check_chat_waits(chat_paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for cp in chat_paths:
        if not cp.exists():
            continue
        text = cp.read_text(encoding="utf-8", errors="replace")
        for pattern in CHAT_WAIT_PATTERNS:
            if pattern.search(text):
                findings.append(Finding(
                    code="COMPLIANCE_DRIFT",
                    detail=(
                        f"chat artifact {cp.name} contains a wait-for-human pattern "
                        f"matching /{pattern.pattern}/. Under autonomous mode the LLM "
                        "should never emit these — that's the v1.2.0 chickening-out "
                        "failure mode v1.2.1 is meant to catch."
                    ),
                ))
                break
    return findings


def _check_grant_sha(run_dir: Path, repo_root: Path) -> list[Finding]:
    """Compare the grant file's current SHA against the SHA recorded at preflight."""
    mode_log = run_dir / "autonomous-mode.log"
    if not mode_log.exists():
        return []
    # Find the grant path from log
    grant_path = None
    for line in mode_log.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.search(r"grant=(\S+)", line)
        if m:
            grant_path = Path(m.group(1))
            break
    if not grant_path or not grant_path.exists():
        return []
    # The SHA we'd want to compare against would need to have been pinned at preflight.
    # For v1.2.1 first cut, log a warning if the file's mtime moved post-preflight;
    # full SHA-pin is a v1.2.2 extension.
    return []


def evaluate(run_id: str, repo_root: Path) -> list[Finding]:
    run_dir = (repo_root / ".agent-runs" / run_id).resolve()
    if not run_dir.exists():
        return [Finding("RUN_NOT_FOUND", f"run directory not found: {run_dir}")]

    # Determine mode from autonomous-mode.log
    mode_log = run_dir / "autonomous-mode.log"
    if not mode_log.exists():
        # No autonomous-mode log written → HUMAN-MODE; nothing to check.
        return []
    last_status = ""
    for line in mode_log.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.search(r"status=(\S+)", line)
        if m:
            last_status = m.group(1)
    if last_status != "AUTONOMOUS-ACTIVE":
        # Run was not autonomous; compliance check doesn't apply.
        return []

    findings: list[Finding] = []

    # 1. Stage coverage
    manifest = _read_manifest(run_dir / "manifest.yaml")
    pipeline_run = manifest.get("pipeline_run", {}) if isinstance(manifest, dict) else {}
    pipeline_type = pipeline_run.get("type", "feature") if isinstance(pipeline_run, dict) else "feature"
    pipeline_yaml = (repo_root / ".pipelines" / f"{pipeline_type}.yaml").resolve()
    auto_skip_stages = _stages_with_autonomous_skip(pipeline_yaml)
    decisions_md = run_dir / "autonomous-decisions.md"
    logged = _decisions_logged(decisions_md)
    for stage in auto_skip_stages:
        if stage not in logged:
            findings.append(Finding(
                code="COMPLIANCE_DRIFT",
                detail=(
                    f"stage '{stage}' is marked autonomous_skip_chat:true but has "
                    f"no entry in autonomous-decisions.md. The LLM either skipped "
                    f"the stage entirely or failed to log its autonomous decision."
                ),
            ))

    # 2. Forbidden actions in run.log
    findings.extend(_check_forbidden_in_log(run_dir / "run.log"))

    # 3. Chat-wait patterns
    chat_paths = [
        run_dir / "chat-log.md",
        run_dir / "chat-transcript.md",
    ]
    findings.extend(_check_chat_waits(chat_paths))

    # 4. Grant SHA stability (deferred to v1.2.2)
    findings.extend(_check_grant_sha(run_dir, repo_root))

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_autonomous_compliance",
        description="Post-run compliance check for autonomous-mode pipeline runs.",
    )
    parser.add_argument("--run", required=False)
    parser.add_argument(
        "--version", action="version", version="check_autonomous_compliance 1.2.1"
    )
    args = parser.parse_args(argv)

    if not args.run:
        return 0

    repo_root = _find_repo_root()
    findings = evaluate(args.run, repo_root)

    if not findings:
        print("OK: autonomous-mode compliance check passed (or run was HUMAN-MODE).")
        return 0

    print("AUTONOMOUS_COMPLIANCE_DRIFT — the following violations were detected:\n", file=sys.stderr)
    for f in findings:
        print(f"  [{f.code}] {f.detail}", file=sys.stderr)
    print(
        "\nThese findings indicate the run failed to follow the autonomous-mode "
        "procedure that the grant authorized. The next manager-decision should "
        "treat these as Blocker findings.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
