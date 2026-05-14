"""Unit tests for scripts/run_status.py."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from scripts.run_status import format_runs, list_runs


def _make_run(runs_dir: Path, run_id: str, last_line: str, scope_mode: str = "task") -> Path:
    """Create a minimal .agent-runs/<run-id>/ with a run.log + scope.md."""
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True)
    log = run_dir / "run.log"
    log.write_text(
        f"2026-05-14T17:00:00Z RUN_STARTED\n"
        f"2026-05-14T17:01:00Z SCOPE_APPROVED\n"
        f"{last_line}\n",
        encoding="utf-8",
    )
    scope = run_dir / "scope.md"
    scope.write_text(
        f"# Scope contract — {run_id}\n\n**Mode**: {scope_mode}\n",
        encoding="utf-8",
    )
    return run_dir


def test_list_runs_empty(tmp_path: Path):
    assert list_runs(tmp_path / ".agent-runs") == []


def test_list_runs_detects_shipped(tmp_path: Path):
    runs_dir = tmp_path / ".agent-runs"
    _make_run(runs_dir, "2026-05-14-shipped", "2026-05-14T17:05:00Z RUN_DONE")
    results = list_runs(runs_dir)
    assert len(results) == 1
    assert results[0]["run_id"] == "2026-05-14-shipped"
    assert results[0]["status"] == "SHIPPED"


def test_list_runs_detects_halted(tmp_path: Path):
    runs_dir = tmp_path / ".agent-runs"
    _make_run(runs_dir, "2026-05-14-halt", "2026-05-14T17:05:00Z TASK_RETRY_EXHAUSTED: task-3")
    results = list_runs(runs_dir)
    assert results[0]["status"] == "HALTED"


def test_list_runs_detects_running(tmp_path: Path):
    runs_dir = tmp_path / ".agent-runs"
    _make_run(runs_dir, "2026-05-14-running", "2026-05-14T17:05:00Z TASK_STARTED: task-2")
    results = list_runs(runs_dir)
    assert results[0]["status"] == "RUNNING"


def test_list_runs_detects_mode(tmp_path: Path):
    runs_dir = tmp_path / ".agent-runs"
    _make_run(runs_dir, "2026-05-14-sprint-x", "2026-05-14T17:05:00Z RUN_DONE", scope_mode="sprint")
    results = list_runs(runs_dir)
    assert results[0]["mode"] == "sprint"


def test_list_runs_sorts_newest_first(tmp_path: Path):
    runs_dir = tmp_path / ".agent-runs"
    older = _make_run(runs_dir, "2026-05-13-older", "2026-05-13T17:05:00Z RUN_DONE")
    # Force the older one to actually be older
    old_ts = time.time() - 3600
    import os
    os.utime(older / "run.log", (old_ts, old_ts))

    _make_run(runs_dir, "2026-05-14-newer", "2026-05-14T17:05:00Z RUN_DONE")

    results = list_runs(runs_dir)
    assert results[0]["run_id"] == "2026-05-14-newer"
    assert results[1]["run_id"] == "2026-05-13-older"


def test_list_runs_respects_limit(tmp_path: Path):
    runs_dir = tmp_path / ".agent-runs"
    for i in range(15):
        _make_run(runs_dir, f"2026-05-14-r{i:02d}", "2026-05-14T17:05:00Z RUN_DONE")
    results = list_runs(runs_dir, limit=5)
    assert len(results) == 5


def test_format_runs_empty_message(tmp_path: Path):
    assert format_runs([]) == "(no runs in .agent-runs/)"


def test_format_runs_includes_status(tmp_path: Path):
    runs_dir = tmp_path / ".agent-runs"
    _make_run(runs_dir, "2026-05-14-x", "2026-05-14T17:05:00Z RUN_DONE")
    results = list_runs(runs_dir)
    formatted = format_runs(results)
    assert "SHIPPED" in formatted
    assert "2026-05-14-x" in formatted
    assert "mode=task" in formatted
