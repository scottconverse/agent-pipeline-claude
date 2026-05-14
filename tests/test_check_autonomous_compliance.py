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


def test_human_mode_returns_human_mode_no_findings(tmp_path: Path) -> None:
    """v1.2.2: HUMAN-MODE log returns mode=human, findings empty."""
    repo = _setup_autonomous_run(
        tmp_path,
        autonomous_mode_log="2026-05-14T03:00:00Z  status=HUMAN-MODE\n",
    )
    mode, findings = cac.evaluate("test-run", repo)
    assert mode == cac.MODE_HUMAN
    assert findings == []


def test_no_autonomous_mode_log_returns_human_mode(tmp_path: Path) -> None:
    """v1.2.2: legacy run with no autonomous-mode.log returns mode=human."""
    repo = tmp_path
    run_dir = repo / ".agent-runs" / "test-run"
    run_dir.mkdir(parents=True)
    mode, findings = cac.evaluate("test-run", repo)
    assert mode == cac.MODE_HUMAN
    assert findings == []


def test_run_dir_missing_returns_not_found(tmp_path: Path) -> None:
    """v1.2.2: missing run dir returns mode=not-found with diagnostic finding."""
    mode, findings = cac.evaluate("nonexistent", tmp_path)
    assert mode == cac.MODE_NOT_FOUND
    assert len(findings) == 1
    assert findings[0].code == "RUN_NOT_FOUND"


def test_all_stages_logged_returns_autonomous_clean(tmp_path: Path) -> None:
    """v1.2.2: clean autonomous run returns mode=autonomous, findings empty."""
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
    mode, findings = cac.evaluate("test-run", repo)
    assert mode == cac.MODE_AUTONOMOUS
    assert findings == [], findings


def test_missing_stage_decision_is_flagged(tmp_path: Path) -> None:
    decisions = (
        "# Autonomous decisions for test-run\n\n"
        "## 2026-05-14T03:01:00Z — manifest\n"
        "Verdict: AUTONOMOUS-APPROVE\n"
        # plan + manager missing
    )
    repo = _setup_autonomous_run(tmp_path, decisions_md=decisions)
    mode, findings = cac.evaluate("test-run", repo)
    assert mode == cac.MODE_AUTONOMOUS
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
    mode, findings = cac.evaluate("test-run", repo)
    assert mode == cac.MODE_AUTONOMOUS
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
    mode, findings = cac.evaluate("test-run", repo)
    assert mode == cac.MODE_AUTONOMOUS
    flagged = " ".join(f.detail for f in findings)
    assert "Reply APPROVE" in flagged or "chickening-out" in flagged


# v1.2.2 — _check_grant_sha tests


def _decisions_full() -> str:
    return (
        "## 2026-05-14T03:01:00Z — manifest\nVerdict: AUTONOMOUS-APPROVE\n"
        "## 2026-05-14T03:05:00Z — plan\nVerdict: AUTONOMOUS-APPROVE\n"
        "## 2026-05-14T03:30:00Z — manager\nVerdict: AUTONOMOUS-PROMOTE\n"
    )


def test_grant_sha_matches_no_finding(tmp_path: Path) -> None:
    """When the grant file's current SHA matches the recorded SHA, no drift."""
    import hashlib

    grant = tmp_path / "grant.md"
    grant_content = "Granted-by: Scott\nGranted-at: 2026-05-14T00:00:00Z\n"
    grant.write_bytes(grant_content.encode("utf-8"))
    sha = hashlib.sha256(grant.read_bytes()).hexdigest()
    log = (
        f"2026-05-14T03:00:00Z  status=AUTONOMOUS-ACTIVE  grant={grant}  grant_sha={sha}\n"
    )
    repo = _setup_autonomous_run(
        tmp_path, decisions_md=_decisions_full(), autonomous_mode_log=log
    )
    mode, findings = cac.evaluate("test-run", repo)
    assert mode == cac.MODE_AUTONOMOUS
    sha_findings = [f for f in findings if "SHA-256" in f.detail]
    assert sha_findings == []


def test_grant_sha_mismatch_flagged(tmp_path: Path) -> None:
    """When the grant file is modified mid-run, the SHA check flags drift."""
    grant = tmp_path / "grant.md"
    grant.write_text("original content\n", encoding="utf-8")
    pinned_but_now_wrong_sha = "0" * 64
    log = (
        f"2026-05-14T03:00:00Z  status=AUTONOMOUS-ACTIVE  "
        f"grant={grant}  grant_sha={pinned_but_now_wrong_sha}\n"
    )
    repo = _setup_autonomous_run(
        tmp_path, decisions_md=_decisions_full(), autonomous_mode_log=log
    )
    mode, findings = cac.evaluate("test-run", repo)
    assert mode == cac.MODE_AUTONOMOUS
    sha_findings = [f for f in findings if "SHA-256" in f.detail]
    assert len(sha_findings) == 1
    assert sha_findings[0].code == "COMPLIANCE_DRIFT"


def test_grant_sha_missing_in_log_back_compat(tmp_path: Path) -> None:
    """Logs without grant_sha (older runs) skip the SHA check silently."""
    grant = tmp_path / "grant.md"
    grant.write_text("any content\n", encoding="utf-8")
    log = f"2026-05-14T03:00:00Z  status=AUTONOMOUS-ACTIVE  grant={grant}\n"
    repo = _setup_autonomous_run(
        tmp_path, decisions_md=_decisions_full(), autonomous_mode_log=log
    )
    mode, findings = cac.evaluate("test-run", repo)
    assert mode == cac.MODE_AUTONOMOUS
    # Other checks should still fire if anything's wrong; SHA check should not.
    sha_findings = [f for f in findings if "SHA-256" in f.detail]
    assert sha_findings == []
