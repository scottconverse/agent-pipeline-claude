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
