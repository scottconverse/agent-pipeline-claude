# Fixture: CivicCast-shaped project

A stripped-down replica of the CivicCast project structure. Used to exercise the manifest-drafter against a realistic spec / release-plan / scope-lock / design-note / CLAUDE.md / HANDOFF.md layout without requiring access to the actual CivicCast repo.

## Layout

```
civiccast-shaped/
├── README.md                                        (this file)
├── CivicCastUnifiedSpec-v2.md                       (1-paragraph project spec)
├── CivicCast-ReleasePlan-0.1-to-1.0.md              (release ladder summary)
├── CLAUDE.md                                        (project conventions)
├── HANDOFF.md                                       (session handoff style)
└── docs/
    ├── releases/
    │   └── v0.4-scope-lock.md                       (per-rung scope contract)
    └── research/
        └── v04-slice1-broadcast-spine-design.md     (design note)
```

## Expected drafter behavior

When `/run "close QA-005 conflict-409 race"` is invoked at this fixture's root:

1. The drafter walks the project root and detects:
   - `CivicCastUnifiedSpec-v2.md` (project spec)
   - `CivicCast-ReleasePlan-0.1-to-1.0.md` (release ladder)
   - `docs/releases/v0.4-scope-lock.md` (per-rung scope)
   - `docs/research/v04-slice1-broadcast-spine-design.md` (design note)
   - `CLAUDE.md` (conventions)
   - `HANDOFF.md` (handoff style)

2. The drafter writes `.agent-runs/<run-id>/manifest.yaml` with:
   - `goal` derived from the scope-lock and quoting QA-005's section.
   - `allowed_paths` derived from the scope-lock §1 + test path inference.
   - `forbidden_paths` derived from the scope-lock §4 + the project's "ADRs append-only" convention.
   - `non_goals` derived from the scope-lock §4 + the release-plan's remaining-commit list.
   - `expected_outputs` derived from the design note's QA-005 section.
   - `definition_of_done` quoting the design note's exit-criteria + CLAUDE.md CI-gate convention.
   - `director_notes` referencing the design note's TOCTOU note.

3. The drafter writes `.agent-runs/<run-id>/draft-provenance.md` listing each field's source.

4. The drafter returns a one-line summary citing the scope-lock + design note as sources.

## Not in the fixture

- ADRs (`docs/adr/*`) — the ADR-gate policy script will be disabled for this fixture.
- A `.github/workflows/` directory — the CI-gate inference will default to "unknown" in the manifest.
- A live test suite — the manifest's `expected_outputs` test-file references are paths that don't exist in the fixture.

These omissions are intentional. The fixture exercises the drafter's spec-walking logic, not the downstream pipeline stages.
