# agentic-pipeline

A Claude Code plugin that orchestrates multi-stage agentic work: **research → plan → test-write → execute → policy → verify → manager**, with three human-approval gates (manifest, plan, manager-decision). Built from real lessons across CivicCast and other projects where autonomous agent runs go wrong silently and "manager-PROMOTE" failures slip past CI.

## Why this plugin exists

Agentic work fails in predictable ways:

- The agent doesn't understand the project's conventions, so it improvises and the work silently diverges from the spec.
- The agent claims tests pass without running them against a fresh dependency set.
- The agent merges in-flight work while a scope question is open.
- The agent picks architectural decisions silently rather than surfacing them.

This plugin enforces a structural pattern that catches every one of those:

1. **Manifest gate** — every run starts with an explicit, human-approved manifest naming the goal, allowed paths, forbidden paths, non-goals, expected outputs, and definition-of-done.
2. **Director-decisions gate** — the researcher surfaces open questions; the human picks; choices are recorded as binding constraints before the planner runs.
3. **Plan gate** — the planner produces a plan; the human approves or sends back.
4. **Policy stage** — automated checks block the run if any change falls outside `allowed_paths`, contains TODO/FIXME/HACK markers, or modifies an existing ADR.
5. **Verifier stage** — independent fresh-context check against every manifest exit criterion.
6. **Manager gate** — final PROMOTE/BLOCK/REPLAN decision, must cite verifier evidence verbatim.

## Install

```bash
# As a Claude Code plugin (one-time install across all projects)
/plugin install scottconverse/agentic-pipeline
```

Or clone the repo and add to your Claude Code plugins config manually.

## First use in a new project

Drop into the project root (or a fresh empty directory) and run:

```
/pipeline-init
```

The plugin asks one question — what do you have? — and accepts one of three inputs:

1. **A PRD or spec document.** Paste the path or contents. The plugin reads it, derives the project's conventions, scaffolds `CLAUDE.md` + `.pipelines/` + `scripts/policy/` + a `.gitignore` entry, and produces a project-orientation summary.
2. **A repo URL** (or a local path to an existing repo). The plugin clones (or reads), inspects `README`, `CLAUDE.md`, `pyproject.toml` / `package.json`, `.github/workflows/`, `docs/adr/`, and recent commits. Produces a project-orientation summary, flags missing pieces, installs `.pipelines/` + `scripts/policy/`.
3. **A project description paragraph or two.** Plugin reads it, asks "scaffold a new project from this, or use as context for an existing repo?" and routes to (1) or (2) accordingly.

After init, your project has:

```
.pipelines/
├── feature.yaml                  # stage sequence for new functionality
├── bugfix.yaml                   # stage sequence for bug fixes
├── manifest-template.yaml        # blank template with field docs
└── roles/
    ├── researcher.md
    ├── planner.md
    ├── test-writer.md
    ├── executor.md
    ├── verifier.md
    └── manager.md
scripts/policy/
├── check_allowed_paths.py        # generic, manifest-driven
├── check_no_todos.py             # generic, configurable scan dirs
├── check_adr_gate.py             # generic, ADRs are append-only
└── run_all.py                    # runner
.agent-runs/                      # gitignored — pipeline run artifacts
```

## Running a pipeline

Once a project is initialized:

```
/new-run feature my-task-slug      # initialize a manifest skeleton
                                   # (you fill in the manifest, then:)
/run-pipeline feature 2026-05-09-my-task-slug
                                   # orchestrates the full sequence,
                                   # stops at human gates and on failure,
                                   # resumable from .agent-runs/<run-id>/run.log
```

Three human-approval gates per run: manifest, plan, manager-decision. Each is a one-question prompt: APPROVE or describe what should change.

## v0.2: The `module-release` pipeline

For work whose end-state is a published release artifact (module version bump, dependency migration), use `module-release` instead of `feature`. It adds two stages that prevent the most expensive class of failure: cascading discovery of pre-existing CI infrastructure bugs during the remote release run.

```
/new-run module-release my-module-v1.2.0-migration
/run-pipeline module-release 2026-05-11-my-module-v1.2.0-migration
```

The pipeline runs six phases:
- **Phase 0 — Preflight auditor.** Audits the module's release workflow before any product code is touched. YAML parse, workflow run health, referenced scripts exist, local `verify-release.sh` on fresh state, cross-platform reality check, diagnostic instrumentation, audit-punchlist correlation. Bugs found are bundled into ONE PR. See `pipelines/roles/preflight-auditor.md`.
- **Phase 1 — Scoped product work.** The executor role with pre-authorized self-classification rules (LIVE-STATE / FROZEN-EVIDENCE / SHAPE-GUARD / OWN-MODULE-VERSION for grep hits; MECHANICAL-CI-BUG / CONTRACT-CHANGE / ENVIRONMENTAL / NOVEL for failures) so the agent doesn't halt-and-ask on routine cases. See `pipelines/self-classification-rules.md`.
- **Phase 2 — Local release rehearsal.** Mirrors the CI environment and runs the release sequence locally on fresh state before tag push. The workflow becomes the *execution* mechanism, not the *discovery* mechanism. See `pipelines/roles/local-rehearsal.md`.
- **Phase 3 — Remote release + umbrella reconciliation.** Tag push, release workflow watch, umbrella PR through the project's release-lockstep gate.
- **Phase 4 — Verifier.** Independent fresh-context check of all release artifacts and durable docs.
- **Phase 5 — Manager.** Final PROMOTE/BLOCK/REPLAN with verifier evidence cited verbatim.

Human gates at Phase 0 results review, Phase 2 rehearsal-ok, and Phase 5 release-ok.

**Operator reference:** `docs/module-release-handbook.md` covers initial setup, expected timing per sprint type, and an honest "what this pipeline does NOT prevent" section. Originating failure receipts are documented in the handbook so future operators understand why each stage exists.

## v0.3: Dual-AI audit-handoff discipline

For projects where one AI implements and a different AI audits (e.g., Claude implements while Codex audits, or vice versa), v0.3 adds a complementary discipline that catches drift the pipeline doesn't:

```
/audit-init
```

This scaffolds three artifacts:
1. `<PROJECT>_AUDIT_GATE.md` (out-of-repo) — short mandatory gate the auditing agent reads every verification turn.
2. `<PROJECT>_AUDIT_PROTOCOL.md` (out-of-repo) — long reference protocol with the 10-section output shape, status-word rules, and a known drift patterns catalog.
3. `<project>/docs/process/5-lens-self-audit.md` (in-repo, via PR) — shared discipline both agents read. The implementer runs a hostile 5-lens self-audit before every push (Engineering / UX / Tests / Docs / QA), plus a post-push SHA-propagation step.

Plus per-agent wiring (Claude memory file or Codex skill addition) so each agent reads the right artifact on session start.

The discipline is symmetric — any agent can play either role:
- CivicCast uses Claude=implementer / Codex=auditor.
- CivicSuite uses Codex=implementer / Claude=auditor.

**Stacking with v0.2:**
- Pipeline (v0.2) catches execution-cascade failures: pre-existing CI bugs, tag-move dances, halt-and-ask loops.
- Audit-handoff (v0.3) catches drift failures: wrong endpoint, stale CHANGELOG, "Closed" without evidence, status-word abuse.

The two address different failure modes. Use both for projects with two AI systems.

**Operator reference:** `docs/audit-handoff-handbook.md`.

## What this plugin will NOT do

- It will not propose autonomous mode. Every gate is explicit.
- It will not silently expand scope. The policy stage blocks any change outside `allowed_paths`.
- It will not skip tests. CLAUDE.md hard-rule "never skip tests" is enforced as a project default.
- It will not promote a run if the verifier marked any criterion NOT MET. Manager hard rule.

## Project-specific customization

After `/pipeline-init`, the files installed in your repo are yours to edit. Add project-specific policy checks alongside the generic ones (e.g., a CivicCast-style `check_ffmpeg_wrapper.py`). Customize the role files to reference your project's specific ADRs, CLAUDE.md sections, test patterns. The plugin's slash commands work against whatever's in your repo's `.pipelines/` and `scripts/policy/` directories.

## Documentation

- `commands/pipeline-init.md` — the full onboarding command logic
- `commands/new-run.md` — the run-init command logic
- `commands/run-pipeline.md` — the orchestrator command logic
- `pipelines/roles/*.md` — what each role does, what's forbidden
- `pipelines/manifest-template.yaml` — every manifest field with inline docs

## Lessons baked in

This plugin's defaults reflect failures from prior projects. Notably:

- Halts apply to ALL repo state changes, including in-flight cleanup work
- Auto mode never overrides explicit stops
- "Tests pass locally" is not evidence; CI on a fresh dep set is
- Manifest amendments are corrections, not expansions, and the pattern of needing them means the manifest template should use directory-level path granularity for same-module test paths
- The manager must cite verifier evidence verbatim; encouragement and summarization are forbidden in the role file

## License

Apache 2.0.
