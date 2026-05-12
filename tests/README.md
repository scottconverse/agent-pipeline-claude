# tests/

Test surface for `agent-pipeline-claude` v1.0.0+.

## What's testable

### Unit-testable (Python policy scripts)

- `scripts/check_manifest_schema.py` — the schema validator. Tested at `tests/test_check_manifest_schema.py`.
- `scripts/check_allowed_paths.py` — the path-enforcement check. (Tests TODO; v1.0 ships without.)
- `scripts/check_no_todos.py` — the TODO/FIXME/HACK scan. (Tests TODO; v1.0 ships without.)
- `scripts/check_adr_gate.py` — the ADR append-only check. (Tests TODO; v1.0 ships without.)
- `scripts/auto_promote.py` — the six-condition machine-checkable promote. (Tests TODO; v1.0 ships without.)

The schema validator is the highest-leverage test target — it's the gate every run's manifest hits, and a regression here breaks every downstream stage. v1.0 ships with that one well-tested; the other policy scripts get tests in follow-up commits as needed.

### Integration-testable (the manifest-drafter role)

The manifest-drafter is a markdown role file, not Python. It can't be unit-tested, but it CAN be exercised against fixture projects.

`tests/fixtures/civiccast-shaped/` is a stripped-down replica of a CivicCast-style project structure: it has a one-line spec file, a release-plan file, a per-rung scope-lock, a design note, a CLAUDE.md, and a sample HANDOFF.md. The drafter run against this fixture should produce a populated `manifest.yaml` with ≥8 of 11 fields auto-derived.

`tests/fixtures/greenfield/` is an empty directory. The drafter run here should return `"NO_SPEC_FOUND"` and write a minimal-skeleton manifest.

To exercise the drafter manually:

```bash
cd tests/fixtures/civiccast-shaped/
# Open Claude Code (Cowork or CLI) in this directory.
# Once the plugin loads:
/pipeline-init       # confirms the fixture's documents are detected
/run "close QA-005 conflict-409 race"   # drafter runs; produces manifest in chat
```

You should see the drafter's one-line summary mention `docs/releases/v0.4-scope-lock.md` and `docs/research/v04-slice1-design.md` as sources.

A fully-automated integration test that spawns a real Claude session is out of scope for v1.0 — the plugin would have to invoke itself recursively, which CI can't currently provide. This is documented as a v1.x follow-up.

### Not testable (the role files themselves)

`pipelines/roles/researcher.md`, `planner.md`, `executor.md`, `verifier.md`, `drift-detector.md`, `critic.md`, `manager.md`, `judge.md`, `manifest-drafter.md` etc. are spec-style documents. The "test" for these is: a fresh Claude session given just the role file + run context produces the right artifact. That's an integration test against a live Claude API, not a unit test.

The review process for changes to these files is:
1. Manual review of the markdown (does it match the role-file shape?).
2. Exercise the role in a real pipeline run against a fixture project.
3. Inspect the produced artifact for shape + content.

## Running

```bash
pip install pytest  # if not already installed
python -m pytest tests/ -v
```

From the repo root. Tests don't require any external services; `tests/fixtures/` contains everything needed.

## Adding tests

For a new policy script:
1. Drop `tests/test_check_<name>.py` mirroring the schema-test pattern.
2. Each test has a setup fixture writing a synthetic manifest, runs the script via subprocess or import, asserts exit code + key output strings.
3. Cover at least one pass case + one fail case + one edge case.

For a new fixture project:
1. Drop a directory under `tests/fixtures/<name>/`.
2. Include a `README.md` at the fixture root explaining what shape the fixture represents.
3. Document the expected drafter behavior in `tests/README.md`.
