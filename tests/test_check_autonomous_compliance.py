"""Tests for scripts/check_autonomous_compliance.py — v1.2.1 post-run drift check."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_autonomous_compliance as cac  # type: ignore  # noqa: E402


def _setup_autonomous_run(
    tmp_path: Path,
    decisions_md: str = "",
    run_log: str = "",
    chat_log: str | None = None,
    autonomous_mode_log: str | None = None,
    stages: list[dict] | None = None,
) -> Path:
    """Build a fixture run directory under tmp_path/.agent-runs/test-run/."""
    repo = tmp_path
    pipelines = repo / ".pipelines"
    pipelines.mkdir(parents=True, exist_ok=True)
    if stages is None:
        stages = [
            {"name": "manifest", "role": "human", "autonomous_skip_chat": True},
            {"name": "research", "role": "researcher"},
            {"name": "plan", "role": "planner", "autonomous_skip_chat": True},
            {"name": "manager", "role": "manager", "autonomous_skip_chat": True},
        ]
    (pipelines / "feature.yaml").write_text(
        yaml.safe_dump({"pipeline": "feature", "stages": stages}),
        encoding="utf-8",
    )
    run_dir = repo / ".agent-runs" / "test-run"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.yaml").write_text(
        yaml.safe_dump({"pipeline_run": {"id": "test-run", "type": "feature"}}),
        encoding="utf-8",
    )
    (run_dir / "autonomous-decisions.md").write_text(decisions_md, encoding="utf-8")
    (run_dir / "run.log").write_text(run_log, encoding="utf-8")
    if chat_log is not None:
        (run_dir / "chat-log.md").write_text(chat_log, encoding="utf-8")
    if autonomous_mode_log is None:
        autonomous_mode_log = "2026-05-14T03:00:00Z  status=AUTONOMOUS-ACTIVE  grant=test\n"
    (run_dir / "autonomous-mode.log").write_text(autonomous_mode_log, encoding="utf-8")
    return repo


def test_human_mode_skipped_silently(tmp_path: Path) -> None:
    """If autonomous-mode.log shows HUMAN-MODE, compliance check is a no-op."""
    repo = _setup_autonomous_run(
        tmp_path,
        autonomous_mode_log="2026-05-14T03:00:00Z  status=HUMAN-MODE\n",
    )
    findings = cac.evaluate("test-run", repo)
    assert findings == []


def test_no_autonomous_mode_log_skipped(tmp_path: Path) -> None:
    """Run with no autonomous-mode.log (legacy/human run) is skipped."""
    repo = tmp_path
    run_dir = repo / ".agent-runs" / "test-run"
    run_dir.mkdir(parents=True)
    findings = cac.evaluate("test-run", repo)
    assert findings == []


def test_all_stages_logged_passes(tmp_path: Path) -> None:
    decisions = (
        "# Autonomous decisions for test-run\n\n"
        "## 2026-05-14T03:01:00Z — manifest\n"
        "Verdict: AUTONOMOUS-APPROVE\n\n"
        "## 2026-05-14T03:05:00Z — plan\n"
        "Verdict: AUTONOMOUS-APPROVE\n\n"
        "## 2026-05-14T03:30:00Z — manager\n"
        "Verdict: AUTONOMOUS-PROMOTE\n"
    )
    repo = _setup_autonomous_run(tmp_path, decisions_md=decisions)
    findings = cac.evaluate("test-run", repo)
    assert findings == [], findings


def test_missing_stage_decision_is_flagged(tmp_path: Path) -> None:
    decisions = (
        "# Autonomous decisions for test-run\n\n"
        "## 2026-05-14T03:01:00Z — manifest\n"
        "Verdict: AUTONOMOUS-APPROVE\n"
        # plan + manager missing
    )
    repo = _setup_autonomous_run(tmp_path, decisions_md=decisions)
    findings = cac.evaluate("test-run", repo)
    flagged = " ".join(f.detail for f in findings)
    assert "plan" in flagged
    assert "manager" in flagged


def test_forbidden_action_in_run_log_flagged(tmp_path: Path) -> None:
    decisions = (
        "## 2026-05-14T03:01:00Z — manifest\nVerdict: AUTONOMOUS-APPROVE\n"
        "## 2026-05-14T03:05:00Z — plan\nVerdict: AUTONOMOUS-APPROVE\n"
        "## 2026-05-14T03:30:00Z — manager\nVerdict: AUTONOMOUS-PROMOTE\n"
    )
    run_log = "gh pr merge 42 -R foo/bar --admin --squash --delete-branch\n"
    repo = _setup_autonomous_run(tmp_path, decisions_md=decisions, run_log=run_log)
    findings = cac.evaluate("test-run", repo)
    flagged = " ".join(f.detail for f in findings)
    assert "admin-merge" in flagged


def test_chat_wait_pattern_flagged(tmp_path: Path) -> None:
    decisions = (
        "## 2026-05-14T03:01:00Z — manifest\nVerdict: AUTONOMOUS-APPROVE\n"
        "## 2026-05-14T03:05:00Z — plan\nVerdict: AUTONOMOUS-APPROVE\n"
        "## 2026-05-14T03:30:00Z — manager\nVerdict: AUTONOMOUS-PROMOTE\n"
    )
    chat = "Manifest ready. Reply APPROVE to proceed.\n"
    repo = _setup_autonomous_run(tmp_path, decisions_md=decisions, chat_log=chat)
    findings = cac.evaluate("test-run", repo)
    flagged = " ".join(f.detail for f in findings)
    assert "Reply APPROVE" in flagged or "chickening-out" in flagged
