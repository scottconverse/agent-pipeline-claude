"""Tests for scripts/check_critic_evidence.py + check_manager_evidence.py.

v1.2.0 C4 + E1 evidence enforcement.
"""

from __future__ import annotations

from pathlib import Path

import sys
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_critic_evidence as cce  # type: ignore  # noqa: E402
import check_manager_evidence as cme  # type: ignore  # noqa: E402


# ---------- critic ----------


def test_critic_with_findings_passes(tmp_path: Path) -> None:
    report = tmp_path / "critic-report.md"
    report.write_text(
        "# Critic Report\n"
        "### UX\n"
        "- C-1: missing loading state in `src/Auth.tsx:42`\n"
        "### Tests\n"
        "- C-2: no assertion in `tests/test_auth.py:7`\n"
        "### Engineering\n"
        "- C-3: N+1 query in `src/db.py:88`\n"
        "### Docs\n"
        "- C-4: CHANGELOG missing entry\n"
        "### QA\n"
        "- C-5: ledger contradiction\n"
        "### Performance\n"
        "- C-6: bundle size up 30%\n",
        encoding="utf-8",
    )
    findings, sections = cce.evaluate(report)
    assert findings == [], f"got findings: {findings}"
    assert len(sections) >= 6


def test_critic_with_citations_only_passes(tmp_path: Path) -> None:
    """A lens with 'no findings' is acceptable IF citation evidence is present."""
    report = tmp_path / "critic-report.md"
    report.write_text(
        "### UX\n"
        "No findings — work doesn't touch UI.\n"
        "**Evidence:** `git diff --stat` shows no changes under `src/components/Button.tsx`.\n"
        "### Tests\n"
        "- C-1: missing edge case\n"
        "### Engineering\n"
        "No findings. Evidence: `grep -r 'except:' src/` returned nothing.\n"
        "### Docs\n"
        "- C-2: CHANGELOG stale\n"
        "### QA\n"
        "- C-3: ledger lag\n"
        "### Performance\n"
        "- C-4: hot path regression in `src/main.py:120`\n",
        encoding="utf-8",
    )
    findings, _ = cce.evaluate(report)
    assert findings == [], f"got findings: {findings}"


def test_critic_rubber_stamp_fails(tmp_path: Path) -> None:
    """A lens with neither findings nor citations fails the gate."""
    report = tmp_path / "critic-report.md"
    report.write_text(
        "### UX\n"
        "no findings.\n"  # no citations, no bullets
        "### Tests\n"
        "- C-1: ok\n"
        "### Engineering\n"
        "- C-2: ok\n"
        "### Docs\n"
        "- C-3: ok\n"
        "### QA\n"
        "- C-4: ok\n"
        "### Performance\n"
        "- C-5: ok\n",
        encoding="utf-8",
    )
    findings, _ = cce.evaluate(report)
    assert any("UX" in f for f in findings)


def test_critic_missing_lens_fails(tmp_path: Path) -> None:
    """A required lens entirely absent fails the gate."""
    report = tmp_path / "critic-report.md"
    report.write_text(
        "### UX\n- C-1\n"
        "### Tests\n- C-2\n"
        "### Engineering\n- C-3\n"
        "### Docs\n- C-4\n"
        "### QA\n- C-5\n"
        # Performance missing
        ,
        encoding="utf-8",
    )
    findings, _ = cce.evaluate(report)
    assert any("Performance" in f for f in findings)


# ---------- manager ----------


def _setup_manager_run(
    tmp_path: Path,
    decision_md: str,
    critic_md: str | None = None,
    drift_md: str | None = None,
) -> Path:
    run_dir = tmp_path / ".agent-runs" / "test-run"
    run_dir.mkdir(parents=True)
    (run_dir / "manager-decision.md").write_text(decision_md, encoding="utf-8")
    if critic_md is not None:
        (run_dir / "critic-report.md").write_text(critic_md, encoding="utf-8")
    if drift_md is not None:
        (run_dir / "drift-report.md").write_text(drift_md, encoding="utf-8")
    return tmp_path


def test_manager_well_formed_passes(tmp_path: Path) -> None:
    repo = _setup_manager_run(
        tmp_path,
        decision_md=(
            "**Decision: PROMOTE**\n\n"
            "## Resolution per finding\n\n"
            "| ID | Severity | Disposition | Rationale |\n"
            "|---|---|---|---|\n"
            "| C-1 | Minor | accepted | per overflow rule |\n"
            "| D-1 | Minor | accepted | doc-currency lag |\n"
        ),
        critic_md="### UX\n- C-1: minor finding\n",
        drift_md="- D-1: tiny drift\n",
    )
    findings, info = cme.evaluate("test-run", repo)
    assert findings == [], findings
    assert info["verdict"] == "PROMOTE"


def test_manager_missing_resolution_fails(tmp_path: Path) -> None:
    repo = _setup_manager_run(
        tmp_path,
        decision_md="**Decision: PROMOTE**\n\n(no resolution section)\n",
        critic_md="- C-1: thing\n",
    )
    findings, _ = cme.evaluate("test-run", repo)
    assert any("Resolution" in f for f in findings)


def test_manager_unresolved_finding_fails(tmp_path: Path) -> None:
    repo = _setup_manager_run(
        tmp_path,
        decision_md=(
            "**Decision: PROMOTE**\n\n"
            "## Resolution per finding\n\n"
            "| C-1 | Minor | accepted | foo |\n"
            # C-2 is in critic but missing here
        ),
        critic_md="- C-1: foo\n- C-2: bar\n",
    )
    findings, _ = cme.evaluate("test-run", repo)
    assert any("C-2" in f for f in findings)


def test_manager_promote_with_blocked_disposition_fails(tmp_path: Path) -> None:
    repo = _setup_manager_run(
        tmp_path,
        decision_md=(
            "**Decision: PROMOTE**\n\n"
            "## Resolution per finding\n\n"
            "| C-1 | Blocker | blocked | the thing | \n"
        ),
        critic_md="- C-1: real blocker\n",
    )
    findings, _ = cme.evaluate("test-run", repo)
    assert any("blocked" in f.lower() for f in findings)
