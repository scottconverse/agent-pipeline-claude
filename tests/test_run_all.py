# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/run_all.py.

v1.2.2: run_all.py now writes the canonical `policy-report.md` artifact
directly when `--run` is given, instead of relying on the orchestrator
to capture stdout. This pins that behavior so the marker line that
auto_promote depends on cannot be lost mid-pipeline.

These tests use in-process monkeypatch on RUN_DIR_BASE — the real
check scripts still run as subprocesses against the live repo and may
PASS or FAIL depending on the working tree, which is fine. The
artifact-write contract holds regardless of check outcomes.
"""

from __future__ import annotations

from scripts.run_all import main as run_all_main


def test_run_all_writes_policy_report_md_to_run_dir(tmp_path, monkeypatch) -> None:
    """When --run is given and the run dir exists, run_all writes
    `<RUN_DIR_BASE>/<run-id>/policy-report.md` containing the POLICY
    marker line — independent of which checks pass or fail."""
    fake_runs = tmp_path / ".agent-runs"
    run_id = "policy-write-test"
    run_dir = fake_runs / run_id
    run_dir.mkdir(parents=True)

    monkeypatch.setattr("scripts.run_all.RUN_DIR_BASE", fake_runs)
    monkeypatch.setattr("sys.argv", ["run_all.py", "--run", run_id])

    # Real check subprocesses may fail (no manifest, etc.) — the
    # artifact-write contract is unconditional once --run is set and
    # the run dir exists.
    exit_code = run_all_main()
    assert exit_code in (0, 1)

    report = run_dir / "policy-report.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "POLICY:" in text
    assert "Policy checks" in text


def test_run_all_skips_artifact_write_when_run_dir_missing(
    tmp_path, monkeypatch
) -> None:
    """If `--run` is given but the run dir does not exist, the script
    must not silently create it — that would mask a real run-id typo."""
    fake_runs = tmp_path / ".agent-runs"
    fake_runs.mkdir()

    monkeypatch.setattr("scripts.run_all.RUN_DIR_BASE", fake_runs)
    monkeypatch.setattr("sys.argv", ["run_all.py", "--run", "no-such-run"])

    exit_code = run_all_main()
    assert exit_code in (0, 1)
    assert not (fake_runs / "no-such-run").exists()


def test_run_all_reports_missing_check_script_distinctly(tmp_path, monkeypatch) -> None:
    """v1.2.2: a deleted/renamed check script must be flagged as a
    missing-script error, not a generic non-zero exit. Operators need
    to distinguish a real policy violation from a configuration drift
    in the CHECKS list."""
    fake_runs = tmp_path / ".agent-runs"
    run_id = "missing-script-test"
    run_dir = fake_runs / run_id
    run_dir.mkdir(parents=True)

    # Patch the CHECKS list to include a script that doesn't exist.
    import scripts.run_all as run_all_mod

    original_checks = run_all_mod.CHECKS
    monkeypatch.setattr(
        run_all_mod, "CHECKS", original_checks + [("does_not_exist", ["does_not_exist.py"])]
    )
    monkeypatch.setattr("scripts.run_all.RUN_DIR_BASE", fake_runs)
    monkeypatch.setattr("sys.argv", ["run_all.py", "--run", run_id])

    exit_code = run_all_main()
    assert exit_code == 1  # presence of any FAIL means non-zero
    text = (run_dir / "policy-report.md").read_text(encoding="utf-8")
    assert "check script not found" in text
    assert "does_not_exist.py" in text


def test_run_all_skips_artifact_write_without_run(tmp_path, monkeypatch) -> None:
    """Without --run, run_all is a developer convenience; it must not
    attempt to write any .agent-runs path."""
    fake_runs = tmp_path / ".agent-runs"

    monkeypatch.setattr("scripts.run_all.RUN_DIR_BASE", fake_runs)
    monkeypatch.setattr("sys.argv", ["run_all.py"])

    exit_code = run_all_main()
    assert exit_code in (0, 1)
    assert not fake_runs.exists()
