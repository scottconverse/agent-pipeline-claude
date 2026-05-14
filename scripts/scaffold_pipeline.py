"""Deterministic scaffold for v2.0 pipeline-init.

Copies the bundled pipeline payload (`skills/pipeline-init/references/pipeline-payload/`)
into a target project's working tree:

  <project>/.pipelines/
      sprint.yaml
      sprint-task.yaml
      roles/worker.md

  <project>/scripts/policy/
      run_status.py          # status helper (for `/run status` path)
      validate_scope.py      # scope.md structure validator
      __init__.py

Per the v2.0 design: NO drift-detector, NO critic, NO manager, NO manifest schema,
NO action classifier, NO 18-script policy stack. The autonomous loop in
`skills/run/references/run.md` does its own light validation; the worker subagent
self-verifies.

Run via the pipeline-init skill or directly:

    python scripts/scaffold_pipeline.py --target <project-root>

Exits non-zero on conflicts (existing .pipelines/ or scripts/policy/ in target).
Pass --force to overwrite.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAYLOAD = REPO_ROOT / "skills" / "pipeline-init" / "references" / "pipeline-payload"


class ScaffoldError(RuntimeError):
    """Raised on conflicts or missing-payload errors."""


def _expected_payload_files() -> list[Path]:
    """The bundled files we MUST copy into the target project."""
    return [
        Path("pipelines/sprint.yaml"),
        Path("pipelines/sprint-task.yaml"),
        Path("pipelines/roles/worker.md"),
    ]


def _expected_policy_files() -> list[Path]:
    """Policy scripts copied into <target>/scripts/policy/."""
    return [
        Path("run_status.py"),
        Path("validate_scope.py"),
    ]


def scaffold(target: Path, *, payload: Path = DEFAULT_PAYLOAD, force: bool = False) -> None:
    """Scaffold v2.0 pipeline payload into ``target``.

    Raises:
        ScaffoldError: target has existing .pipelines/ and force is False,
                       or payload directory missing.
    """
    if not payload.is_dir():
        raise ScaffoldError(f"payload directory not found: {payload}")

    target_pipelines = target / ".pipelines"
    target_policy = target / "scripts" / "policy"

    if not force:
        if target_pipelines.exists():
            raise ScaffoldError(
                f"target already has .pipelines/ — pass --force to overwrite: {target_pipelines}"
            )

    # Copy bundled pipeline payload (sprint*.yaml + roles/worker.md).
    # The _expected_payload_files() paths are relative to the payload root
    # AND mirror the .pipelines/ layout. So src = payload / rel; dst strips
    # the leading "pipelines/" and prepends target/.pipelines/.
    for rel in _expected_payload_files():
        src = payload / rel
        if not src.is_file():
            raise ScaffoldError(f"payload missing required file: {rel}")
        # rel is like "pipelines/sprint.yaml"; we want target/.pipelines/sprint.yaml
        rel_under_pipelines = Path(*rel.parts[1:])  # drop the leading "pipelines"
        dst = target / ".pipelines" / rel_under_pipelines
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # Copy policy scripts (run_status.py + validate_scope.py)
    for rel in _expected_policy_files():
        src = REPO_ROOT / "scripts" / rel
        if not src.is_file():
            raise ScaffoldError(f"policy script missing in plugin: {rel}")
        dst = target_policy / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # Write a minimal __init__.py so policy is importable as a package
    init_path = target_policy / "__init__.py"
    if not init_path.exists():
        init_path.write_text(
            '"""Policy scripts for agent-pipeline-claude v2.0 runs."""\n',
            encoding="utf-8",
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="scaffold_pipeline", description=__doc__)
    p.add_argument("--target", type=Path, required=True, help="Project root to scaffold into.")
    p.add_argument("--payload", type=Path, default=DEFAULT_PAYLOAD,
                   help="Payload directory (default: plugin's bundled payload).")
    p.add_argument("--force", action="store_true",
                   help="Overwrite existing .pipelines/ in target.")
    args = p.parse_args(argv)

    try:
        scaffold(args.target.resolve(), payload=args.payload.resolve(), force=args.force)
    except ScaffoldError as e:
        print(f"scaffold_pipeline: {e}", file=sys.stderr)
        return 1

    print(
        f"scaffold_pipeline: scaffolded v2.0 payload into {args.target}\n"
        f"  .pipelines/sprint.yaml\n"
        f"  .pipelines/sprint-task.yaml\n"
        f"  .pipelines/roles/worker.md\n"
        f"  scripts/policy/run_status.py\n"
        f"  scripts/policy/validate_scope.py"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
