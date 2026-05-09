# agentic-pipeline — User Manual

A Claude Code plugin that orchestrates multi-stage agentic work with three human-approval gates. Built from real lessons across multi-week agent projects where autonomous runs go wrong silently and "manager-PROMOTE" failures slip past CI.

**Version:** 0.1.0-beta
**License:** Apache 2.0

---

## Table of contents

1. [Who this is for](#who-this-is-for)
2. [What you get](#what-you-get)
3. [Installation](#installation)
4. [Onboarding a project — `/pipeline-init`](#onboarding-a-project)
5. [Running a pipeline](#running-a-pipeline)
6. [The three human gates](#the-three-human-gates)
7. [Customizing for your project](#customizing-for-your-project)
8. [Resuming a halted run](#resuming-a-halted-run)
9. [Troubleshooting](#troubleshooting)
10. [Glossary](#glossary)

---

## Who this is for

Developers using Claude Code (or compatible agentic AI tooling) who want a structural pattern for getting multi-step agent work done correctly the first time. The plugin is most useful when:

- You work on a project across multiple Claude Code sessions
- Single-shot agent prompts produce work that drifts from your project's conventions
- You've been burned by "manager said PROMOTE but CI was red" failures
- You want explicit human-approval points without managing the workflow yourself

The plugin assumes you have:

- A repo (or are about to create one)
- A test framework configured
- A lint/format toolchain
- (Optional but recommended) A `CLAUDE.md` capturing your project's conventions
- (Optional) ADRs in `docs/adr/`

If you don't have those yet, `/pipeline-init` helps you scaffold them.

## What you get

Three slash commands:

| Command | Purpose |
| :--- | :--- |
| `/pipeline-init` | Onboard a project. Accepts a PRD path, a repo URL, or a description paragraph. Scaffolds `.pipelines/`, `scripts/policy/`, and `CLAUDE.md` if missing. |
| `/new-run <type> <slug>` | Initialize a new pipeline run. Creates `.agent-runs/<run-id>/manifest.yaml` from the template and asks you to fill it in. |
| `/run-pipeline <type> <run-id>` | Orchestrate a pipeline run end-to-end. Stops at human gates and on failure. Resumable. |

Two default pipeline definitions:

- **`feature`** — 8 stages: manifest → research → plan → test-write → execute → policy → verify → manager
- **`bugfix`** — 7 stages: manifest → research → reproduce → patch → policy → verify → manager

Six self-contained role files (markdown) — each tells a fresh Claude session exactly what to do and what is forbidden.

Four generic policy checks (Python, stdlib only):

- `check_allowed_paths.py` — manifest-driven path enforcement
- `check_no_todos.py` — no TODO/FIXME/HACK in source
- `check_adr_gate.py` — ADRs are append-only
- `run_all.py` — combined runner

## Installation

### As a Claude Code plugin (recommended)

```bash
# One-time install — available across all projects
/plugin install scottconverse/agentic-pipeline
```

### Manual install (local clone)

If your Claude Code setup uses a plugins config in `~/.claude/settings.json` or `.claude/settings.json`:

```bash
git clone https://github.com/scottconverse/agentic-pipeline.git ~/agentic-pipeline-plugin
```

Then add the path to your settings (consult the Claude Code docs for the current plugin-registration syntax — varies by version).

## Onboarding a project

Drop into your project root (or a fresh empty directory) and run:

```
/pipeline-init
```

The plugin asks: **what do you have?**

You answer with one of three things:

### Path 1 — A PRD or spec document

You have a written specification (markdown, PDF text, or pasted contents). The plugin reads it and:

1. Extracts project name, purpose, target audience, primary capabilities, technical constraints
2. Determines a working directory (current dir if non-empty, or scaffolds a subdirectory)
3. Scaffolds `CLAUDE.md` derived from the PRD (if you don't already have one)
4. Installs `.pipelines/` and `scripts/policy/`
5. Adds `.agent-runs/` to `.gitignore`
6. Hands off to `/new-run feature <slug>` with a slug suggestion derived from the PRD

### Path 2 — An existing repo (URL or local path)

You have a project somewhere — a GitHub URL, a local clone, anywhere. The plugin:

1. Clones the repo (or reads from the local path)
2. Inspects `README`, `CLAUDE.md`, `pyproject.toml` / `package.json` / etc., `.github/workflows/`, `docs/adr/`, and recent commits
3. Produces a **project orientation summary** — what it found, what's missing, what the gaps mean for downstream pipeline behavior
4. Asks you to confirm or correct the summary
5. Installs `.pipelines/` and `scripts/policy/` (preserves your existing `CLAUDE.md` and other config)

### Path 3 — A description paragraph

You have an idea — a paragraph or two describing what you want to build. The plugin asks:

- **New project to scaffold from scratch?** It synthesizes a minimal PRD from the description and treats it as Path 1.
- **Context for an existing repo?** It asks for the repo URL/path and treats it as Path 2 (your description goes into the orientation summary as user-provided context).

## Running a pipeline

Once onboarded, every piece of agent work follows the same shape: define what you're doing, let the pipeline orchestrate it, approve or reject at three checkpoints.

### Step 1 — Initialize a run

```
/new-run feature add-search-endpoint
```

This creates `.agent-runs/2026-05-09-add-search-endpoint/manifest.yaml` from the template. The manifest is the **contract for the entire run** — every downstream agent reads it.

### Step 2 — Fill in the manifest

Open `.agent-runs/2026-05-09-add-search-endpoint/manifest.yaml` in your editor. The fields you fill in:

| Field | What goes here |
| :--- | :--- |
| `goal` | One sentence, user-facing. The thing release notes will say. |
| `branch` | Git branch the run will commit to. |
| `allowed_paths` | Path prefixes this run may modify. Be specific. |
| `forbidden_paths` | Paths this run must NOT touch. Common: `docs/adr/`, version files, CI configs. |
| `non_goals` | What's out of scope. Keep the agent honest. |
| `expected_outputs` | Testable artifacts and behaviors that must exist when done. |
| `risk` | low / medium / high. |
| `rollback_plan` | What to do if this gets reverted. |
| `definition_of_done` | One paragraph: the precise bar the work clears. |
| `director_notes` | Optional. Things you want the researcher to surface explicitly (e.g., "check tests/ for sync vs async assumptions"). |

The manifest template has inline comments explaining every field.

### Step 3 — Run the pipeline

```
/run-pipeline feature 2026-05-09-add-search-endpoint
```

The orchestrator reads `.pipelines/feature.yaml` and walks each stage:

```
manifest        → human gate (you approve)
research        → researcher subagent → research.md
plan            → planner subagent → plan.md
                → human gate (you approve plan)
test-write      → test-writer subagent → failing-tests-report.md
execute         → executor subagent → implementation-report.md (commits made)
policy          → bash → policy-report.md
verify          → verifier subagent → verifier-report.md
manager         → manager subagent → manager-decision.md
                → human gate (you approve PROMOTE / BLOCK / REPLAN)
```

Each stage outcome appends to `.agent-runs/<run-id>/run.log`.

### Step 4 — Approve or send back at each gate

Three explicit human-approval moments:

1. **Manifest gate** (before any agent runs) — you confirm the manifest captures the work correctly.
2. **Plan gate** (after researcher + planner) — you confirm the planner's approach.
3. **Manager gate** (after the manager produces a verdict) — you confirm PROMOTE or reject.

Each gate is a one-question prompt: type **APPROVE** or describe what should change. Describing changes halts the pipeline.

## The three human gates

The gates exist because every project this pattern was tested on had at least one stage where the agent silently picked an architectural decision that should have been a human call. The gates force the conversation.

| Gate | Catches |
| :--- | :--- |
| **Manifest** | Wrong scope, missing constraints, fuzzy DoD, missing director_notes |
| **Plan** | Wrong pattern choice, scope expansion in §2/§3, missing risk mitigation, untestable contracts |
| **Manager** | "PROMOTE" on incomplete work, missing verifier evidence, ignored CLAUDE.md non-negotiables |

The manager gate is the most load-bearing. The manager role's hard rules forbid soft-promotion, encouragement, and summarization — every PROMOTE must cite verbatim verifier evidence.

## Customizing for your project

After `/pipeline-init`, the files in your project (`.pipelines/`, `scripts/policy/`, `CLAUDE.md`) are **yours**. The plugin's slash commands work against whatever's in those directories.

### Common customizations

- **Edit role files** to reference your project's specific ADR conventions, test patterns, lint rules.
- **Add project-specific policy checks** alongside the generic ones (e.g., a `check_my_module_boundaries.py`). Add the new check name to the `CHECKS` list in `scripts/policy/run_all.py`.
- **Add new pipeline types** by creating `.pipelines/<your-type>.yaml`. The orchestrator picks them up automatically — `/run-pipeline <your-type> <run-id>` works.
- **Customize the manifest template** to add project-specific fields. The agents will see them in the manifest.

### Adding a new pipeline type

To add (for example) a `refactor` pipeline:

```yaml
# .pipelines/refactor.yaml
pipeline: refactor

stages:
  - name: manifest
    role: human
    artifact: manifest.yaml
    gate: human_approval

  - name: research
    role: researcher
    artifact: research.md
    # researcher gets a researcher.md role file with refactor-specific focus

  - name: plan
    role: planner
    artifact: plan.md
    gate: human_approval

  - name: behavior-snapshot
    role: test-writer
    artifact: behavior-snapshot.md
    # captures EXISTING behavior as tests before any refactor

  - name: refactor
    role: executor
    artifact: implementation-report.md

  - name: policy
    role: pipeline
    command: python scripts/policy/run_all.py --run {run_id}
    artifact: policy-report.md

  - name: verify
    role: verifier
    artifact: verifier-report.md

  - name: manager
    role: manager
    artifact: manager-decision.md
    gate: human_approval
```

Then use it: `/new-run refactor extract-auth-module` → fill manifest → `/run-pipeline refactor 2026-05-09-extract-auth-module`.

## Resuming a halted run

The pipeline writes append-only progress to `.agent-runs/<run-id>/run.log`. Re-invoking `/run-pipeline <type> <run-id>` with the same arguments:

1. Reads the log
2. Identifies the first stage WITHOUT a `COMPLETE` entry
3. Resumes from there

`FAILED` and `BLOCKED` stages count as incomplete, so they re-run.

This means:

- After a policy failure → fix the violation, re-run, policy re-executes.
- After a verifier marks a criterion `NOT MET` → manager will likely return BLOCK or REPLAN; address and re-run; pipeline redoes execute → policy → verify → manager.
- After a human gate `BLOCKED` → address the requested change in commits, then re-run; the gate question fires again.

## Troubleshooting

### `manager-decision.md` says PROMOTE but CI fails

This was a real failure mode in early projects. Cause: local executor's pytest run passed because of stale dependencies in the local venv (e.g., a leftover `psycopg2-binary` install that wasn't a project dep). CI's fresh dep install exposed the gap.

**Fix:** the executor role file now requires verification against a fresh dep set (`pip install -e ".[dev]"` or your project's equivalent fresh-install command) before claiming COMPLETE. If the issue recurs, your project's careful-coding template should reinforce this.

### Manifest amendment needed mid-run

If the planner or test-writer needs a path that wasn't in `allowed_paths`, the policy stage will block. Two paths:

1. **Genuine correction** (the manifest's path enumeration was incomplete, not the scope) — amend the manifest in place, document the amendment in `.agent-runs/<run-id>/director-decisions.md`, re-run from the failed stage.
2. **Genuine scope expansion** — the manager should return REPLAN; you re-issue `/new-run` with a corrected manifest.

If you find yourself amending manifests frequently, consider using directory-level granularity for path lists (e.g., `tests/schedule/` instead of three individual test files) in your manifest template default.

### Pipeline halts on a director-decisions question

The researcher surfaces open questions in `research.md` §5. The orchestrator may pause for you to record decisions before the planner runs (depending on your pipeline YAML — the default `feature.yaml` does NOT have an explicit director-decisions stage; it's an implicit "planner reads research, you can intervene before approving the plan"). To make it explicit, you can add a stage like:

```yaml
  - name: director-decisions
    role: human
    artifact: director-decisions.md
    gate: human_approval
```

The researcher will write recommendations; you write the binding decisions; the planner reads both.

### Cleanroom CI catches "works on my machine"

If your project has CI but no Docker cleanroom, the executor's local pytest can pass while CI fails. This was the failure mode that surfaced multiple bugs in CivicCast. Recommended addition to your project: a `ci-cleanroom-e2e.yml` workflow that runs the full test suite inside a Docker container with all dependencies fresh-installed.

## Glossary

- **Run** — one execution of a pipeline. Has a unique id (e.g., `2026-05-09-add-search-endpoint`). All artifacts live under `.agent-runs/<run-id>/`.
- **Manifest** — the contract for a run. Lives at `.agent-runs/<run-id>/manifest.yaml`. Read by every stage.
- **Role file** — markdown file describing what one type of agent does. Lives at `.pipelines/roles/<role>.md`. Used as the prompt header when the orchestrator spawns a subagent for that role.
- **Stage** — one step in a pipeline. Each stage produces one named artifact and either advances or halts.
- **Gate** — a stop point requiring human approval before the pipeline advances. Three by default: manifest, plan, manager.
- **PROMOTE / BLOCK / REPLAN** — the three possible manager decisions. PROMOTE = ready for human merge approval. BLOCK = unfixable in current state, fix and re-run. REPLAN = manifest itself was wrong, redraft and start over.
- **Run log** — append-only `run.log` in the run dir. Records each stage outcome with timestamp. Drives resume.
- **Director-decisions file** — optional `.agent-runs/<run-id>/director-decisions.md` capturing human answers to questions the researcher surfaced. When present, binding for the planner.

---

## Source of truth

This manual is the user-facing reference. The architecture and design rationale live in `ARCHITECTURE.md`. Plugin metadata is in `.claude-plugin/plugin.json`. Bug reports and feature requests: GitHub Discussions on the plugin repo.
