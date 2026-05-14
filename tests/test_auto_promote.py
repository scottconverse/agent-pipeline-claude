# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/auto_promote.py.

Ported from agent-pipeline-codex in v1.2.2 — the Claude version of
auto_promote.py had zero direct test coverage prior to this. These
tests pin the count-line regex flexibility (case + whitespace), the
malformed-input failure paths, the test-output failure detection, and
the full-green main() happy path.
"""

from pathlib import Path

from scripts.auto_promote import (
    _check_critic,
    _check_drift,
    _check_tests,
    _check_verifier,
    main,
)


def write_green_run(run_dir: Path) -> None:
    run_dir.mkdir(parents=True)
    (run_dir / "verifier-report.md").write_text(
        "**Criteria: 2 total, 2 MET, 0 PARTIAL, 0 NOT MET, 0 NOT APPLICABLE**",
        encoding="utf-8",
    )
    (run_dir / "critic-report.md").write_text(
        "**Findings: 1 total, 0 blocker, 0 critical, 1 major, 0 minor**",
        encoding="utf-8",
    )
    (run_dir / "drift-report.md").write_text(
        "**Drift: 0 total, 0 blocker**",
        encoding="utf-8",
    )
    (run_dir / "policy-report.md").write_text(
        "POLICY: ALL CHECKS PASSED",
        encoding="utf-8",
    )
    (run_dir / "implementation-report.md").write_text(
        "pytest output: 12 passed, 0 failed",
        encoding="utf-8",
    )


def test_check_tests_rejects_mixed_pass_fail_output(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "implementation-report.md").write_text(
        "pytest output: 5 passed, 2 failed",
        encoding="utf-8",
    )

    result = _check_tests(run_dir)

    assert not result.passed
    assert "non-zero failure count" in result.evidence


def test_check_tests_rejects_nonzero_failure_even_when_zero_failure_appears_elsewhere(
    tmp_path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "implementation-report.md").write_text(
        "legacy suite: 5 passed, 2 failed\nnew suite: 12 passed, 0 failed",
        encoding="utf-8",
    )

    result = _check_tests(run_dir)

    assert not result.passed
    assert "non-zero failure count" in result.evidence


def test_auto_promote_writes_decision_for_full_green_artifact_set(
    tmp_path, monkeypatch
) -> None:
    run_id = "green-run"
    run_base = tmp_path / ".agent-runs"
    write_green_run(run_base / run_id)
    monkeypatch.setattr("scripts.auto_promote.RUN_DIR_BASE", run_base)
    monkeypatch.setattr("sys.argv", ["auto_promote.py", "--run", run_id])

    assert main() == 0
    decision = (run_base / run_id / "manager-decision.md").read_text(encoding="utf-8")
    assert "**Decision: PROMOTE**" in decision


def test_count_line_parsers_accept_case_and_comma_spacing_variants(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "verifier-report.md").write_text(
        "**criteria: 3 total , 2 met , 0 partial , 0 not   met , 1 not applicable**",
        encoding="utf-8",
    )
    (run_dir / "critic-report.md").write_text(
        "**findings: 2 total , 0 blocker , 0 critical , 1 major , 1 minor**",
        encoding="utf-8",
    )
    (run_dir / "drift-report.md").write_text(
        "**drift: 1 total , 0 blocker**",
        encoding="utf-8",
    )

    assert _check_verifier(run_dir).passed
    assert _check_critic(run_dir).passed
    assert _check_drift(run_dir).passed


def test_check_tests_passes_vacuously_when_manifest_forbids_test_dirs(tmp_path) -> None:
    """v1.2.2: docs-only / tests-out-of-scope runs should not block on
    implementation-report.md absence when the manifest explicitly bars
    the executor from touching tests."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "manifest.yaml").write_text(
        'pipeline_run:\n'
        '  goal: "narrate the docs-only change"\n'
        '  allowed_paths:\n'
        '    - "docs/"\n'
        '  forbidden_paths:\n'
        '    - "tests/"\n'
        '    - ".github/workflows/"\n',
        encoding="utf-8",
    )

    result = _check_tests(run_dir)

    assert result.passed
    assert "vacuous" in result.evidence
    assert "tests/" in result.evidence


def test_check_tests_still_fails_when_no_manifest_and_no_implementation_report(
    tmp_path,
) -> None:
    """Default behavior unchanged: missing implementation-report with no
    manifest still fails, so a real implementation gap is not silently
    promoted."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    result = _check_tests(run_dir)

    assert not result.passed
    assert "missing" in result.evidence


def test_check_tests_still_fails_when_manifest_does_not_forbid_tests(tmp_path) -> None:
    """If the manifest does not forbid test dirs, the condition still
    requires a real test-pass signal."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "manifest.yaml").write_text(
        'pipeline_run:\n'
        '  goal: "make a code change"\n'
        '  allowed_paths:\n'
        '    - "src/"\n'
        '  forbidden_paths:\n'
        '    - ".github/workflows/"\n',
        encoding="utf-8",
    )

    result = _check_tests(run_dir)

    assert not result.passed
    assert "missing" in result.evidence


def test_malformed_or_missing_count_lines_block_auto_promote(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "verifier-report.md").write_text(
        "**Criteria: 2 total, 2 MET**",
        encoding="utf-8",
    )
    (run_dir / "critic-report.md").write_text(
        "No findings today.",
        encoding="utf-8",
    )
    (run_dir / "drift-report.md").write_text(
        "**Drift: 1 total, 1 blocker**",
        encoding="utf-8",
    )

    verifier = _check_verifier(run_dir)
    critic = _check_critic(run_dir)
    drift = _check_drift(run_dir)

    assert not verifier.passed
    assert "malformed" in verifier.evidence
    assert not critic.passed
    assert "malformed" in critic.evidence
    assert not drift.passed
    assert "1 blocker" in drift.evidence
