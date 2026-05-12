# agent-pipeline-claude — User Manual

Ship multi-step Claude Code work that doesn't drift. The plugin reads your project's spec, drafts a per-run scope contract, and asks you to APPROVE in chat. Then it runs research → plan → execute → verify → critique end-to-end with three human gates, an opt-in real-time judge, and machine-checkable auto-promote.

**Version:** 1.1.0
**License:** Apache 2.0

---

## What's new in v1.1 (read first if you used v1.0.x)

v1.1 fixes the install/runtime adapter that v1.0.0–v1.0.2 got wrong. Plugin behavior, manifest schema, role files, and policy scripts are unchanged.

- **Namespaced invocation is now the documented form.** Plugin skills in Claude Code are always invoked as `/<plugin-name>:<skill-name>` per the [official Claude Code plugin docs](https://code.claude.com/docs/en/plugins). The bare `/run` form documented in v1.0 was never reachable for marketplace-installed plugins. Use `/agent-pipeline-claude:run`.
- **Single layout (`skills/`).** v1.0.1 added a `skills/` mirror alongside `commands/`, causing every skill to register twice and Cowork's resolver to fail on bare names. v1.1 removes `commands/` entirely. Three skills, one layout, no collisions.
- **Skills are self-contained per Codex's pattern.** Each `skills/<name>/SKILL.md` is a thin shim with frontmatter + tool-mapping notes; the canonical procedure lives in `skills/<name>/references/<name>.md`. Enforced by `scripts/check_skill_packaging.py` ported from `agent-pipeline-codex`.
- **Marketplace manifest validates.** `marketplace.json` no longer carries an unrecognized root `description`; it lives under `metadata` per the marketplace schema.
- **Deprecated shims are gone.** `/new-run` and `/run-pipeline` were marked deprecated in v1.0 and scheduled for v1.1 removal. They are now removed (they never functioned as shims in Cowork because v1.0.0–v1.0.2 never loaded; the deprecation theater is over).

If you used v0.5.x and skipped v1.0, see the migration notes at the bottom of this manual.

---

## Table of contents

1. [Who this is for](#who-this-is-for)
2. [What you get](#what-you-get)
3. [Installation](#installation)
4. [Onboarding a project — `/agent-pipeline-claude:pipeline-init`](#onboarding-a-project)
5. [Running a pipeline](#running-a-pipeline)
6. [The three human gates](#the-three-human-gates)
7. [Customizing for your project](#customizing-for-your-project)
8. [Resuming a halted run](#resuming-a-halted-run)
9. [The judge layer](#the-judge-layer)
10. [Single-AI hardening](#single-ai-hardening)
11. [Troubleshooting](#troubleshooting)
12. [Glossary](#glossary)
13. [Migration from v0.5.x](#migration-from-v05x)

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

If you don't have those yet, `/agent-pipeline-claude:pipeline-init` helps you scaffold them.

## What you get

Three skills:

| Invocation | Purpose |
| :--- | :--- |
| `/agent-pipeline-claude:pipeline-init` | Onboard a project. Accepts a PRD path, a repo URL, or a description paragraph. Scaffolds `.pipelines/`, `scripts/policy/`, and `CLAUDE.md` if missing. |
| `/agent-pipeline-claude:run "<short description>"` | Start a pipeline run. Drafts the manifest from your spec, gates on APPROVE, orchestrates end-to-end. Also: `resume <run-id>` and `status`. |
| `/agent-pipeline-claude:audit-init` | Scaffold dual-AI audit-handoff infrastructure for projects where one AI implements and another audits. |

Three default pipeline definitions:

- **`feature`** — 11 stages: manifest → research → plan → test-write → execute → policy → verify → drift-detect → critique → auto-promote → manager
- **`bugfix`** — 10 stages: manifest → research → reproduce → patch → policy → verify → drift-detect → critique → auto-promote → manager
- **`module-release`** — six-phase release pipeline with Phase 0 preflight + Phase 2 local rehearsal

Fourteen self-contained role files (markdown) — each tells a fresh Claude session exactly what to do and what is forbidden: `manifest-drafter`, `researcher`, `planner`, `test-writer`, `executor` (with pre-edit fact-forcing), `verifier`, `drift-detector`, `critic`, `manager` (auto-promote-aware), `judge` (opt-in), `preflight-auditor`, `local-rehearsal`, `cross-agent-auditor`, `implementer-pre-push`.

Six generic policy checks (Python, stdlib only):

- `check_manifest_schema.py` — strict manifest contract validator
- `check_allowed_paths.py` — manifest-driven path enforcement
- `check_no_todos.py` — no TODO/FIXME/HACK in source
- `check_adr_gate.py` — ADRs are append-only
- `auto_promote.py` — six-condition machine-checkable promote
- `run_all.py` — combined runner

Plus `check_skill_packaging.py` at the plugin level to verify skills are self-contained before any release.

## Installation

The plugin works in **Cowork** (the chat-first Claude Code surface) and in **Claude Code CLI**. Cowork is the primary supported path because many Claude Code users don't have a CLI.

### Recommended: marketplace install

If your client supports `/plugin marketplace add`:

```
/plugin marketplace add scottconverse/agent-pipeline-claude
/plugin install agent-pipeline-claude@agent-pipeline-claude
```

Then **fully quit and reopen** Cowork (or restart your CLI session). Plugin metadata loads at app startup, not at conversation start.

### Cowork file-level install (no marketplace UI)

Paste this prompt into any Claude session:

```
Install the agent-pipeline-claude plugin for me.

Method: clone https://github.com/scottconverse/agent-pipeline-claude
into ~/.claude/plugins/marketplaces/agent-pipeline-claude. Add an
agent-pipeline-claude marketplace entry to ~/.claude/plugins/known_marketplaces.json
pointing at that path. Add agent-pipeline-claude@agent-pipeline-claude to
~/.claude/plugins/installed_plugins.json with the cloned commit SHA.
In ~/.claude/settings.json, set
enabledPlugins["agent-pipeline-claude@agent-pipeline-claude"] = true and add
the marketplace to extraKnownMarketplaces. If an older
agentic-pipeline@agentic-pipeline entry exists, set it to false.

Back up settings.json + known_marketplaces.json + installed_plugins.json
before patching. After install, tell me to fully quit Cowork
to load the new skills.
```

After the agent finishes, **fully quit Cowork** (Quit/Exit, not just close the conversation window). After restart, `/agent-pipeline-claude:pipeline-init` and `/agent-pipeline-claude:run` appear in the slash-command palette.

### Local development install

```
claude --plugin-dir /path/to/agent-pipeline-claude
```

Loads the plugin for one session without touching `installed_plugins.json`. Run `claude plugin list` to confirm `Status: ✔ loaded`.

### Verifying the install

Three commands worth running after install:

```
claude plugin validate /path/to/agent-pipeline-claude
claude plugin list
python scripts/check_skill_packaging.py     # from the plugin dir
```

All three should pass / show `✔ enabled` (or `✔ loaded` for `--plugin-dir` sessions). If `claude plugin list` shows `✘ failed to load`, read the error message — it identifies the manifest field that broke the loader.

### What if my skills don't appear in the command palette after install?

In order:

1. **Did you fully quit and restart your client?** Cowork loads plugin metadata at app startup, not conversation start. "New conversation" is not enough.
2. **Is the plugin enabled?** `~/.claude/settings.json` should have `enabledPlugins["agent-pipeline-claude@agent-pipeline-claude"]: true`. If you also have `"agentic-pipeline@agentic-pipeline"`, set the old one to `false`.
3. **Did the install actually clone the repo?** Check `~/.claude/plugins/marketplaces/agent-pipeline-claude/` exists and contains `skills/run/SKILL.md`. If not, re-run the bootstrap prompt.
4. **Does the manifest validate?** Run `claude plugin validate ~/.claude/plugins/marketplaces/agent-pipeline-claude`. If it fails, the loader rejected the plugin entirely — fix the manifest field it complains about.
5. **Are you typing the namespaced form?** Plugin skills are always `/agent-pipeline-claude:run`, never bare `/run`. The bare form is reserved for standalone `.claude/commands/` files.

## Onboarding a project

Drop into your project root (or a fresh empty directory) and run:

```
/agent-pipeline-claude:pipeline-init
```

The skill walks the cwd, summarizes what it finds, and asks for APPROVE before writing anything. Optionally pass an argument:

| Argument | Behavior |
| :--- | :--- |
| _(none)_ | Inspect cwd. The common case. |
| `<file path>` | Read as a PRD / spec / requirements doc. |
| `<repo URL>` | `git clone` into cwd (must be empty), then init. |
| `"<description paragraph>"` | Greenfield mode: synthesize a minimal spec from the description, then init. |

After APPROVE, the skill scaffolds `.pipelines/`, `scripts/policy/`, and (if missing) a starter `CLAUDE.md` whose `## Pipeline drafter notes` section tells the manifest-drafter where this project keeps its spec, release plan, design notes, and ledgers. Edit that section before your first run for best results.

## Running a pipeline

```
/agent-pipeline-claude:run "short description of the work"
```

That's the whole command. The skill:

1. Verifies `.pipelines/manifest-template.yaml` exists (otherwise prompts you to run `/agent-pipeline-claude:pipeline-init` first).
2. Picks the pipeline type (`feature` by default; `bugfix` if your description contains "bug" / "fix" / "regression"; `module-release` if it contains "release" / "ship" / "tag").
3. Generates a run id: `YYYY-MM-DD-<slug>` from your description.
4. Spawns the manifest-drafter subagent against your project's spec / release-plan / scope-lock / design notes.
5. Pastes the drafted manifest in chat with a one-line summary like `"Drafted from docs/releases/v0.4-scope-lock.md §1 + docs/research/v04-slice1-design.md. 8/11 fields auto-derived, 3 hand-required."`
6. Waits for `APPROVE`, `READY`, or revision instructions.
7. On APPROVE, orchestrates the rest of the pipeline.

### Other shapes

```
/agent-pipeline-claude:run resume 2026-05-12-my-task-slug   # pick up a halted run
/agent-pipeline-claude:run status                            # list runs in this project
/agent-pipeline-claude:run                                   # same as `status`
```

## The three human gates

Each is a chat-message decision moment. Three universal verbs: `APPROVE` to accept, `REPLAN <description>` (or `<description>`) to revise, or — at the manager gate — `BLOCK` to halt.

1. **Manifest gate** (after the drafter). You review YAML in chat and APPROVE or describe changes. The drafter loops on revision (max 5 cycles before falling back to a hand-edit prompt).
2. **Plan gate** (after research → plan). You see the planner's plan summary inline + a count of files in the blast radius + a list of open questions. APPROVE or REPLAN.
3. **Manager gate** (after auto-promote, only when auto-promote did NOT fire). The manager produces a PROMOTE / BLOCK / REPLAN recommendation citing the verifier, drift-detector, and critic findings verbatim. APPROVE / BLOCK / REPLAN.

When the auto-promote stage's six conditions all pass, the manager gate auto-fires (PROMOTE) and no human prompt appears. The run reports DONE-PROMOTED in its final summary.

## Customizing for your project

The manifest-drafter walks these patterns from the project root:

| Category | Filename patterns |
| :--- | :--- |
| Project spec | `*UnifiedSpec*.md`, `SPEC.md`, `PRD.md`, `REQUIREMENTS.md`, `docs/spec/*.md` |
| Release ladder | `*ReleasePlan*.md`, `RELEASE-PLAN.md`, `ROADMAP.md`, `docs/spec/release-plan.md` |
| Per-rung scope contract | `docs/releases/v*-scope-lock.md`, `docs/releases/<rung>-scope.md` |
| Design notes | `docs/research/<version>-<feature>-design.md`, `docs/design/*.md` |
| ADRs | `docs/adr/*.md` |
| Conventions | `CLAUDE.md` at root |
| Findings | `audit-*/`, `findings/*.md`, `next-cleanup.md` |

You can override the search list in your `CLAUDE.md` under a `## Pipeline drafter notes` section. The `pipeline-init` scaffolder writes that section for you.

### Add a new pipeline type

Create `.pipelines/<your-type>.yaml` with a list of stages. The orchestrator picks it up automatically. Use the existing `feature.yaml` and `bugfix.yaml` as templates.

After adding, `/agent-pipeline-claude:run "..."` will route to your new type if its description matches a heuristic in `skills/run/references/run.md` Step 2 — or you can override by including the type name in the description.

## Resuming a halted run

```
/agent-pipeline-claude:run resume 2026-05-12-my-task-slug
```

The orchestrator reads the run's `run.log`, finds the last completed stage, and picks up at the next stage. The `run.log` is append-only — every stage transition writes one line.

## The judge layer

The judge layer is opt-in via file presence: when `.pipelines/action-classification.yaml` exists, every executor tool call is classified by risk, and high-risk / external-facing calls spawn an independent judge subagent that returns `allow` / `block` / `revise` / `escalate`. Verdicts are appended to `judge-log.yaml`; metrics aggregate to `judge-metrics.yaml`.

To enable: copy the plugin's `pipelines/action-classification.yaml` into your project's `.pipelines/`. To disable: delete the file. No other config required.

## Single-AI hardening

v0.5 added these (all preserved through v1.1):

- **Critic stage** — adversarial cold read of every artifact in fresh context. Walks six lenses (engineering, UX, tests, docs, QA, scope). Emits `**Findings:**` count line for the auto-promote check.
- **Drift-detector stage** — compares manifest contract against assembled final state. Catches durable doc drift, status-word abuse, cross-file inconsistency. Emits `**Drift:**` count line.
- **Pre-edit fact-forcing in executor** — before the first edit per file, the executor must produce importers/callers, public API affected, schema, and the manifest goal quoted verbatim.
- **Machine-checkable auto-promote** — six conditions from the artifact stack: verifier-clean, critic-clean, drift-clean, policy-passed, judge-clean, tests-passed.
- **Strict manifest schema validation** — minimum-length `goal` and `definition_of_done`, non-empty `expected_outputs` / `non_goals` / `rollback_plan`, forbidden status words banned. Failure messages include remediation pointers.

## Troubleshooting

### `/agent-pipeline-claude:run` returns "Unknown command"

Check, in order:

1. `claude plugin list` — does the plugin show `Status: ✔ enabled`? If not, the loader rejected it. The error message identifies which field broke validation.
2. Did you fully restart your client after install? Cowork reads plugin metadata at app startup.
3. Is the plugin path correct? Check `installed_plugins.json` points at the marketplace clone you actually have.

### Bare `/run` returns "Unknown command" but autocomplete shows it

That's expected. Plugin skills are always namespaced. The autocomplete may surface the bare name as shorthand, but the resolver requires `/agent-pipeline-claude:run`. This is a Claude Code platform convention, not a plugin bug.

### `claude plugin validate` reports an unrecognized key

The validator is the source of truth even when the docs disagree. Remove or relocate the field per the error message. Common gotchas in past versions of this plugin:

- `repository` as an object — must be a plain string.
- `description` at the marketplace root — moved under `metadata`.

### A pipeline run halts mid-stage with a STAGE_FAILED entry

Read the artifact named in the log line. Most failures cite the policy check that failed (`policy-report.md`) or the verifier's open items (`verifier-report.md`). Resume with `/agent-pipeline-claude:run resume <run-id>` after fixing the underlying issue — the append-only log picks up at the failing stage.

### `auto-promote` reports NOT_ELIGIBLE

Read `auto-promote-report.md`. It cites the failing condition(s). Common: critic findings > 0, verifier open items > 0, tests didn't run, judge log shows blocked actions. Address the cited condition(s) and re-run.

## Glossary

- **Manifest** — the per-run scope contract. YAML at `.agent-runs/<run-id>/manifest.yaml`. Drafted from your project's spec, gated on chat APPROVE.
- **Pipeline** — the ordered list of stages for a run type, defined in `.pipelines/<type>.yaml`. Default types: `feature`, `bugfix`, `module-release`.
- **Stage** — one step in a pipeline. Each writes a named artifact to `.agent-runs/<run-id>/`.
- **Role** — the markdown file at `.pipelines/roles/<role>.md` that tells a subagent how to perform one stage. Self-contained — a fresh Claude session can execute the stage from the role file alone.
- **Gate** — a halt-and-prompt point. Three universal verbs: APPROVE, REPLAN, BLOCK.
- **Auto-promote** — the six-condition machine check that bypasses the manager gate when all conditions pass. Conditions: verifier-clean, critic-clean, drift-clean, policy-passed, judge-clean, tests-passed.
- **Judge layer** — opt-in real-time action supervision. Activated by the presence of `.pipelines/action-classification.yaml`.
- **Drift-detector** — adversarial stage that compares manifest contract against the assembled final state. Catches doc drift, status-word abuse, cross-file inconsistency.
- **Critic** — adversarial cold-read of every artifact in fresh context across six lenses.
- **Run** — one execution of a pipeline. Identified by a run-id like `2026-05-12-add-search-endpoint`. State at `.agent-runs/<run-id>/`.

## Migration from v0.5.x

If you're upgrading directly from v0.5.x and skipped v1.0:

- The two-step `/new-run` + `/run-pipeline` is gone. Use `/agent-pipeline-claude:run "<description>"`.
- The manifest is drafted from your project's spec; you no longer hand-author 11 fields from blank.
- All three human gates are chat messages (APPROVE / REPLAN / BLOCK), not modal popups.
- All slash invocations are namespaced: `/agent-pipeline-claude:<skill>` instead of `/<skill>`.

The manifest schema, role files, policy scripts, and pipeline definitions are unchanged. Existing `.agent-runs/<run-id>/` directories from v0.5.x runs work as resumable runs in v1.1.

To upgrade:

```
cd ~/.claude/plugins/marketplaces/agent-pipeline-claude
git pull
git checkout v1.1.0
```

Then fully quit and reopen Cowork.
