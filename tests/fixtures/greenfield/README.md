# Fixture: greenfield project

An empty project (just this README). Used to exercise the manifest-drafter's "no-spec-found" fallback path.

## Expected drafter behavior

When `/run "<any description>"` is invoked at this fixture's root:

1. The drafter walks the project root and finds no spec / release-plan / scope-lock / design-note / CLAUDE.md / ledgers.
2. The drafter returns `"NO_SPEC_FOUND"` to the orchestrator.
3. The orchestrator presents State-2 of the manifest-review prompt: *"No spec or release-plan found at the project root or under docs/. (a) Synthesize a minimal spec + draft the manifest from a description you paste; (b) Fill the manifest by hand."*
4. If the user replies with a description (a-path), the drafter takes the description, synthesizes a minimal spec, and produces a manifest.yaml + draft-provenance.md from that synthesis.
5. If the user picks (b), the orchestrator writes a blank-template manifest.yaml and waits for `READY`.

This fixture is intentionally empty. Adding any files would change the test behavior.
