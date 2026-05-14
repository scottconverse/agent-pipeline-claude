# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/run_all.py policy-report.md write behavior (v1.3.1).

Pins the false-stop fix that has run_all.py write the canonical
artifact directly when `--run` is given, instead of relying on the
orchestrator to capture stdout. This was the root cause of the v1.2.1
PROMOTED report's Finding #1: auto_promote read policy-report.md
looking for the marker line, didn't find it (orchestrator's stdout
capture lost it), and stopped on a false policy failure even though
the policy gate actually passed.

Tests use in-process monkeypatch on RUN_DIR_BASE — the real check
scripts still run as subprocesses against the live repo and may PASS
or FAIL depending on the working tree, which is fine. The
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


def test_run_all_skips_artifact_write_without_run(tmp_path, monkeypatch) -> None:
    """Without --run, run_all is a developer convenience; it must not
    attempt to write any .agent-runs path."""
    fake_runs = tmp_path / ".agent-runs"

    monkeypatch.setattr("scripts.run_all.RUN_DIR_BASE", fake_runs)
    monkeypatch.setattr("sys.argv", ["run_all.py"])

    exit_code = run_all_main()
    assert exit_code in (0, 1)
    assert not fake_runs.exists()
