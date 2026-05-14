"""Unit tests for scripts/scaffold_pipeline.py.

Deterministic + $0 — these run in CI without an API key.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.scaffold_pipeline import DEFAULT_PAYLOAD, ScaffoldError, scaffold


def test_default_payload_exists():
    """The bundled payload must exist under skills/pipeline-init/references/."""
    assert DEFAULT_PAYLOAD.is_dir(), f"bundled payload missing: {DEFAULT_PAYLOAD}"
    assert (DEFAULT_PAYLOAD / "pipelines" / "sprint.yaml").is_file()
    assert (DEFAULT_PAYLOAD / "pipelines" / "sprint-task.yaml").is_file()
    assert (DEFAULT_PAYLOAD / "pipelines" / "roles" / "worker.md").is_file()


def test_scaffold_fresh_project(tmp_path: Path):
    """Scaffolding into a fresh target writes the expected v2.0 payload."""
    target = tmp_path / "fresh-project"
    target.mkdir()

    scaffold(target)

    # Pipeline payload landed
    assert (target / ".pipelines" / "sprint.yaml").is_file()
    assert (target / ".pipelines" / "sprint-task.yaml").is_file()
    assert (target / ".pipelines" / "roles" / "worker.md").is_file()

    # Policy scripts landed
    assert (target / "scripts" / "policy" / "run_status.py").is_file()
    assert (target / "scripts" / "policy" / "validate_scope.py").is_file()
    assert (target / "scripts" / "policy" / "__init__.py").is_file()


def test_scaffold_rejects_existing_pipelines(tmp_path: Path):
    """Scaffolding into a target that already has .pipelines/ fails without --force."""
    target = tmp_path / "existing-project"
    (target / ".pipelines").mkdir(parents=True)
    (target / ".pipelines" / "sprint.yaml").write_text("# pre-existing", encoding="utf-8")

    with pytest.raises(ScaffoldError) as exc:
        scaffold(target)
    assert ".pipelines/" in str(exc.value)


def test_scaffold_force_overwrites(tmp_path: Path):
    """With --force, scaffold overwrites the existing .pipelines/."""
    target = tmp_path / "force-overwrite"
    (target / ".pipelines").mkdir(parents=True)
    pre_existing = target / ".pipelines" / "sprint.yaml"
    pre_existing.write_text("# OLD CONTENT", encoding="utf-8")

    scaffold(target, force=True)

    # File is now the bundled payload content, not "# OLD CONTENT"
    new_content = pre_existing.read_text(encoding="utf-8")
    assert "# OLD CONTENT" not in new_content
    assert "pipeline: sprint" in new_content  # from bundled sprint.yaml


def test_scaffold_payload_missing(tmp_path: Path):
    """Scaffolding from a non-existent payload raises ScaffoldError."""
    target = tmp_path / "target"
    target.mkdir()

    with pytest.raises(ScaffoldError):
        scaffold(target, payload=tmp_path / "nonexistent-payload")
