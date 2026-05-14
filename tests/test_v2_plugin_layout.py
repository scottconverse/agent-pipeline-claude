"""v2.0 plugin layout contract tests.

These tests pin the v2.0 surface so a future change can't silently
re-introduce the v1.3.x 11-stage + 14-role + 18-script bloat.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# plugin.json
# ---------------------------------------------------------------------------

def test_plugin_json_version_is_v2():
    plugin = json.loads(_read(REPO_ROOT / ".claude-plugin" / "plugin.json"))
    assert plugin["version"].startswith("2."), \
        f"plugin.json version must be 2.x for the v2.0 surface; got {plugin['version']}"


def test_plugin_json_description_emphasizes_autonomy():
    plugin = json.loads(_read(REPO_ROOT / ".claude-plugin" / "plugin.json"))
    desc = plugin["description"].lower()
    # Must mention autonomy (the headline feature)
    assert "autonomous" in desc, "description must name the autonomous mode"
    # Must mention the bounded-retry mechanism
    assert "retr" in desc, "description must mention retries (bounded)"


# ---------------------------------------------------------------------------
# Removed v1.3.x deadwood
# ---------------------------------------------------------------------------

V13_DELETED_ROLES = [
    "critic.md", "cross-agent-auditor.md", "drift-detector.md", "executor.md",
    "implementer-pre-push.md", "judge.md", "local-rehearsal.md", "manager.md",
    "manifest-drafter.md", "planner.md", "preflight-auditor.md", "researcher.md",
    "test-writer.md", "verifier.md",
]

V13_DELETED_YAMLS = [
    "feature.yaml", "bugfix.yaml", "module-release.yaml",
    "action-classification.yaml", "manifest-template.yaml",
]

V13_DELETED_SKILLS = ["grant-autonomous", "run-autonomous"]


def test_no_v13_roles_remain():
    """v1.3 roles are deleted; v2 has exactly one role: worker.md."""
    roles_dir = REPO_ROOT / "pipelines" / "roles"
    for name in V13_DELETED_ROLES:
        assert not (roles_dir / name).exists(), f"deleted v1.3 role still present: {name}"


def test_no_v13_yamls_remain():
    """v1.3 multi-pipeline yamls are deleted; v2 has sprint.yaml + sprint-task.yaml only."""
    pipelines_dir = REPO_ROOT / "pipelines"
    for name in V13_DELETED_YAMLS:
        assert not (pipelines_dir / name).exists(), f"deleted v1.3 yaml still present: {name}"


def test_no_v13_skills_remain():
    """grant-autonomous and run-autonomous were v1.2.x deprecation shims; v2.0 removes them."""
    skills_dir = REPO_ROOT / "skills"
    for name in V13_DELETED_SKILLS:
        assert not (skills_dir / name).exists(), f"deleted v1.2/v1.3 skill still present: {name}"


# ---------------------------------------------------------------------------
# v2.0 mandatory shape
# ---------------------------------------------------------------------------

def test_worker_role_exists():
    worker = REPO_ROOT / "pipelines" / "roles" / "worker.md"
    assert worker.is_file(), "v2.0 must ship pipelines/roles/worker.md"
    content = _read(worker)
    # Worker must declare its status vocabulary
    assert "**Status: passes**" in content
    assert "**Status: fails**" in content
    assert "**Status: blocked**" in content
    # Worker must reference the Reflexion pattern
    assert "PRIOR_FAILURE_OBSERVATION" in content
    # Worker must NOT spawn other agents (leaf rule)
    assert "leaf node" in content.lower() or "invoke another agent" in content.lower()


def test_sprint_yamls_exist():
    for name in ("sprint.yaml", "sprint-task.yaml"):
        p = REPO_ROOT / "pipelines" / name
        assert p.is_file(), f"v2.0 must ship pipelines/{name}"


def test_sprint_yaml_declares_one_gate():
    """sprint.yaml has exactly ONE gate (scope-gate)."""
    content = _read(REPO_ROOT / "pipelines" / "sprint.yaml")
    gate_lines = [ln for ln in content.splitlines() if "gate:" in ln and not ln.lstrip().startswith("#")]
    assert len(gate_lines) == 1, f"sprint.yaml must declare exactly ONE gate; got {len(gate_lines)}: {gate_lines}"


def test_sprint_task_yaml_has_bounded_retries():
    """sprint-task.yaml must specify max_attempts: 3 (SWE-agent/Aider pattern)."""
    content = _read(REPO_ROOT / "pipelines" / "sprint-task.yaml")
    assert re.search(r"max_attempts:\s*3", content), \
        "sprint-task.yaml must declare max_attempts: 3 for bounded retries"


def test_sprint_task_yaml_carries_observation():
    """sprint-task.yaml retry must carry prior_failure_observation forward (Reflexion)."""
    content = _read(REPO_ROOT / "pipelines" / "sprint-task.yaml")
    assert "prior_failure_observation" in content.lower(), \
        "sprint-task.yaml must declare observation_carryover: prior_failure_observation"


def test_run_skill_invokes_one_modal():
    """skills/run/references/run.md must declare ONE AskUserQuestion gate, total."""
    content = _read(REPO_ROOT / "skills" / "run" / "references" / "run.md")
    lower = content.lower()
    # Procedure must explicitly say "fire ONE" (case-insensitive) — that's the one gate
    assert "fire one" in lower, \
        "run.md must explicitly say 'Fire ONE AskUserQuestion' (the scope gate)"
    # Anti-patterns: no separate plan gate or manager gate. If those terms appear,
    # they must appear in a negation context ("no plan gate", "no manager gate").
    if "plan gate" in lower:
        # Allowed only if accompanied by "no plan gate" — the principle statement
        assert "no plan gate" in lower, \
            "run.md mentions 'plan gate' but doesn't say 'no plan gate'"
    if "manager gate" in lower:
        assert "no manager gate" in lower, \
            "run.md mentions 'manager gate' but doesn't say 'no manager gate'"


# ---------------------------------------------------------------------------
# v2.0 minimal scripts
# ---------------------------------------------------------------------------

V2_REQUIRED_SCRIPTS = [
    "scaffold_pipeline.py",
    "run_status.py",
    "validate_scope.py",
]


def test_v2_scripts_exist():
    scripts_dir = REPO_ROOT / "scripts"
    for name in V2_REQUIRED_SCRIPTS:
        assert (scripts_dir / name).is_file(), f"v2.0 must ship scripts/{name}"


def test_no_deprecated_check_scripts():
    """v1.3 had 18 check_*.py + run_*.py scripts. v2.0 has 3 minimal scripts."""
    scripts = list((REPO_ROOT / "scripts").glob("*.py"))
    # Allow __init__.py and the 3 v2.0 scripts; flag any other check_*/run_* names
    allowed_names = {"__init__.py"} | set(V2_REQUIRED_SCRIPTS)
    extras = [s.name for s in scripts if s.name not in allowed_names]
    assert not extras, f"unexpected scripts in scripts/ (v2.0 is minimal): {extras}"
