"""Deterministic $0 verification of the pipeline-init scaffold.

This is the unit-tier sibling of `test_cleanroom_smoke.py`. The smoke
test exercises the full LLM-driven path (model invokes Skill, claude
CLI executes tool calls, scaffold materializes) at ~$0.05/run and
~60s wall. This test exercises just the deterministic copy step at
$0 and sub-second wall.

Both tests assert the same load-bearing post-conditions: a `.pipelines/`
tree with the expected role files + pipeline yamls + a `scripts/policy/`
tree with the expected validators. If the payload drifts, BOTH tests
fail — but this one fails first, fast, in CI, without an API key.

Coverage gap vs cleanroom-smoke: this test does NOT prove that the LLM
correctly invokes the skill, that claude CLI's Skill tool dispatch
works, or that the markdown step 3 instructions are followed. Those
remain covered by `test_skill_packaging.py`, the `claude plugin list`
load check, and manual Cowork-app verification.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.scaffold_pipeline import (
    DEFAULT_PAYLOAD,
    ScaffoldError,
    scaffold,
)


def test_payload_exists_at_expected_location() -> None:
    """The bundled payload must live where the skill's SKILL.md says it does."""
    assert DEFAULT_PAYLOAD.is_dir(), (
        f"Bundled payload missing at {DEFAULT_PAYLOAD}. "
        "SKILL.md step 3 references this path as the source of truth."
    )
    assert (DEFAULT_PAYLOAD / "pipelines").is_dir()
    assert (DEFAULT_PAYLOAD / "scripts").is_dir()


def test_scaffold_into_fresh_project_writes_expected_tree(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    result = scaffold(project)

    pipelines = project / ".pipelines"
    policy = project / "scripts" / "policy"
    assert pipelines.is_dir()
    assert policy.is_dir()

    # Same expected files asserted by tests/test_cleanroom_smoke.py.
    # If you change one, change both.
    expected_pipeline_files = [
        pipelines / "roles" / "manifest-drafter.md",
        pipelines / "roles" / "researcher.md",
        pipelines / "roles" / "planner.md",
        pipelines / "roles" / "executor.md",
        pipelines / "roles" / "verifier.md",
        pipelines / "roles" / "drift-detector.md",
        pipelines / "roles" / "critic.md",
        pipelines / "roles" / "manager.md",
        pipelines / "roles" / "judge.md",
        pipelines / "feature.yaml",
        pipelines / "bugfix.yaml",
        pipelines / "module-release.yaml",
        pipelines / "manifest-template.yaml",
        pipelines / "action-classification.yaml",
        pipelines / "self-classification-rules.md",
    ]
    missing = [str(p.relative_to(project)) for p in expected_pipeline_files if not p.is_file()]
    assert not missing, f"missing scaffold files: {missing}"

    expected_policy_files = [
        policy / "check_manifest_schema.py",
        policy / "check_allowed_paths.py",
        policy / "check_no_todos.py",
        policy / "check_adr_gate.py",
        policy / "auto_promote.py",
    ]
    missing_policy = [str(p.relative_to(project)) for p in expected_policy_files if not p.is_file()]
    assert not missing_policy, f"missing policy files: {missing_policy}"


def test_scaffold_updates_gitignore(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    result = scaffold(project)

    assert result.gitignore_updated is True
    assert ".agent-runs/" in (project / ".gitignore").read_text(encoding="utf-8")


def test_scaffold_preserves_existing_gitignore_entries(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".gitignore").write_text("node_modules/\n.env\n", encoding="utf-8")

    scaffold(project)

    content = (project / ".gitignore").read_text(encoding="utf-8")
    assert "node_modules/" in content
    assert ".env" in content
    assert ".agent-runs/" in content


def test_scaffold_idempotent_when_gitignore_already_has_entry(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".gitignore").write_text(".agent-runs/\n", encoding="utf-8")

    result = scaffold(project)

    assert result.gitignore_updated is False


def test_scaffold_refuses_to_overwrite_existing_pipelines(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".pipelines").mkdir()
    (project / ".pipelines" / "stale.txt").write_text("old", encoding="utf-8")

    with pytest.raises(ScaffoldError, match=".pipelines/ already exists"):
        scaffold(project)

    # Existing content must be untouched on refusal.
    assert (project / ".pipelines" / "stale.txt").read_text(encoding="utf-8") == "old"


def test_scaffold_overwrite_replaces_pipelines(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".pipelines").mkdir()
    (project / ".pipelines" / "stale.txt").write_text("old", encoding="utf-8")
    (project / "scripts").mkdir()
    (project / "scripts" / "policy").mkdir()
    (project / "scripts" / "policy" / "stale.py").write_text("old", encoding="utf-8")

    scaffold(project, overwrite=True)

    assert not (project / ".pipelines" / "stale.txt").exists()
    assert not (project / "scripts" / "policy" / "stale.py").exists()
    assert (project / ".pipelines" / "roles" / "manifest-drafter.md").is_file()


def test_scaffold_rejects_missing_project_root(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ScaffoldError, match="does not exist"):
        scaffold(missing)


def test_scaffold_rejects_missing_payload(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with pytest.raises(ScaffoldError, match="payload not found"):
        scaffold(project, payload_root=tmp_path / "no-payload")
