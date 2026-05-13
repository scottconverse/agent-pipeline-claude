"""Tests for scripts/check_stage_done.py — v1.2.0 STAGE_DONE marker enforcement."""

from __future__ import annotations

from pathlib import Path

import sys
import yaml
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_stage_done as csd  # type: ignore  # noqa: E402


def _setup_run(
    tmp_path: Path,
    pipeline_type: str = "feature",
    stages: list[dict] | None = None,
    log_content: str = "",
) -> Path:
    repo = tmp_path
    pipelines = repo / ".pipelines"
    pipelines.mkdir(parents=True)
    if stages is None:
        stages = [
            {"name": "manifest", "role": "human"},
            {"name": "research", "role": "researcher"},
            {"name": "plan", "role": "planner"},
            {"name": "execute", "role": "executor"},
            {"name": "policy", "role": "pipeline"},
        ]
    (pipelines / f"{pipeline_type}.yaml").write_text(
        yaml.safe_dump({"pipeline": pipeline_type, "stages": stages}),
        encoding="utf-8",
    )
    run_dir = repo / ".agent-runs" / "test-run"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.yaml").write_text(
        yaml.safe_dump({"pipeline_run": {"id": "test-run", "type": pipeline_type}}),
        encoding="utf-8",
    )
    (run_dir / "run.log").write_text(log_content, encoding="utf-8")
    return repo


def test_all_markers_present_passes(tmp_path: Path) -> None:
    repo = _setup_run(
        tmp_path,
        log_content=(
            "STAGE_DONE: manifest\n"
            "STAGE_DONE: research\n"
            "STAGE_DONE: plan\n"
            "STAGE_DONE: execute\n"
        ),
    )
    missing, found, _ = csd.evaluate("test-run", repo)
    assert missing == []
    assert "execute" in found


def test_missing_marker_is_flagged(tmp_path: Path) -> None:
    repo = _setup_run(
        tmp_path,
        log_content=(
            "STAGE_DONE: manifest\n"
            "STAGE_DONE: research\n"
            # plan and execute missing
        ),
    )
    missing, found, _ = csd.evaluate("test-run", repo)
    assert "plan" in missing
    assert "execute" in missing


def test_through_truncates_expected(tmp_path: Path) -> None:
    """--through limits the check to stages up to and including the named stage."""
    repo = _setup_run(
        tmp_path,
        log_content="STAGE_DONE: manifest\nSTAGE_DONE: research\n",
    )
    missing, found, _ = csd.evaluate("test-run", repo, through="research")
    assert missing == []  # only required up to research; later stages not required yet


def test_pipeline_owned_stages_skipped(tmp_path: Path) -> None:
    """policy / auto-promote stages are owned by orchestrator, no STAGE_DONE required."""
    repo = _setup_run(
        tmp_path,
        stages=[
            {"name": "manifest", "role": "human"},
            {"name": "execute", "role": "executor"},
            {"name": "policy", "role": "pipeline"},  # pipeline-owned, no marker
        ],
        log_content="STAGE_DONE: manifest\nSTAGE_DONE: execute\n",
    )
    missing, found, _ = csd.evaluate("test-run", repo)
    assert missing == []
    assert "policy" not in missing  # was never expected
