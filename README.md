# agent-pipeline-claude

**Ship multi-step Claude Code work that doesn't drift.**

The plugin reads your project's spec, drafts a per-run scope contract from it, and asks you to APPROVE in chat. Then it runs research → plan → execute → verify → critique end-to-end with three human gates, an opt-in real-time judge, and machine-checkable auto-promote.

One slash command. No YAML for you to hand-author.

**Current release: v1.0.0** · [CHANGELOG](CHANGELOG.md) · [User Manual](USER-MANUAL.md) · [Architecture](ARCHITECTURE.md) · [Landing page](https://scottconverse.github.io/agent-pipeline-claude/) · [Discussions](https://github.com/scottconverse/agent-pipeline-claude/discussions)

---

## What a typical run looks like

You're in your project. The plugin is installed. You type:

```
/run "close QA-005 conflict-409 race"
```

Claude reads your project's spec / release plan / scope-lock / design notes, drafts a manifest, and pastes it in chat:

```
Drafted from docs/releases/v0.4-scope-lock.md §1 + docs/research/v04-slice1-design.md.
8/11 fields auto-derived, 3 require your confirmation.

```yaml
pipeline_run:
  id: "2026-05-11-qa-005-conflict-race"
  type: feature
  branch: rung/0.4
  goal: "Close audit-team v0.3.0 QA-005 ..."   # drafted from scope-lock §1
  allowed_paths:
    - civiccast/schedule/store.py              # drafted from scope-lock §1
    - civiccast/schedule/router.py             # drafted from scope-lock §1
    - tests/schedule/                          # drafted from scope-lock §1
  forbidden_paths:
    - civiccast/live/                          # drafted from scope-lock §4
    - docs/adr/                                # drafted from append-only convention
  ...
```

Reply APPROVE to start, or describe what to change.
```

You read it, reply `APPROVE`, and the pipeline runs. Three human gates along the way (manifest, plan, manager-decision), each in chat. The last one auto-fires when six machine-checkable conditions pass. Final result lands in `.agent-runs/<run-id>/` as a structured paper trail.

That's it. No `/new-run` + `/run-pipeline` two-step. No blank YAML to fill in. No CLI commands you don't have.

## Why this plugin exists

Agentic work fails in predictable ways:

- The agent doesn't understand the project's conventions, so it improvises and the work silently diverges from the spec.
- The agent claims tests pass without running them against a fresh dependency set.
- The agent merges in-flight work while a scope question is open.
- The agent picks architectural decisions silently rather than surfacing them.
- The manifest the agent's working from doesn't match what the human actually wanted.

The plugin enforces a structural pattern that catches every one of those:

1. **Drafted scope contract.** The manifest is drafted from your project's existing docs and presented for one-click APPROVE. You review what the agent thinks the run is; you don't author it from blank.
2. **Plan gate.** The planner produces a plan; you approve or send back.
3. **Policy stage.** Automated checks block the run if the manifest fails strict schema validation, any change falls outside `allowed_paths`, the diff contains TODO/FIXME/HACK markers, or an existing ADR was modified.
4. **Verifier stage.** Independent fresh-context check against every manifest exit criterion.
5. **Drift-detector + critic stages.** Adversarial cold-read of every artifact across six lenses; comparison of assembled state against the manifest contract.
6. **Judge layer (opt-in).** Real-time action-level supervision inside the executor stage. Every tool call is classified; dangerous ones spawn an independent judge subagent that allows / blocks / revises / escalates.
7. **Auto-promote.** Six conditions checked from the artifact stack: verifier-clean, critic-clean, drift-clean, policy-passed, judge-clean, tests-passed. When all six pass, the manager gate auto-fires. When any fails, the human gate remains.

## Install

The plugin works in **Cowork** (the chat-first Claude Code surface) and in **Claude Code CLI** if your build has `/plugin` available.

### Cowork (and any environment without `/plugin install`)

Paste this prompt into any Claude session in any project:

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
before patching. After install, tell me to restart Cowork (or my CLI)
to load the new slash commands.
```

Claude will do the work. **Then restart your Cowork session** — slash commands register at session start. After restart, `/pipeline-init` and `/run` appear in the command palette.

### Claude Code CLI (if `/plugin install` is available)

```
/plugin install scottconverse/agent-pipeline-claude
```

Then restart your terminal session.

## First use in a new project

Drop into the project root and run:

```
/pipeline-init
```

The plugin inspects what your project has — spec, release plan, CLAUDE.md, tests, CI workflows — produces a one-message orientation summary, and asks you to APPROVE before scaffolding. After APPROVE, you get:

```
.pipelines/
├── feature.yaml                    # stage sequence for new functionality
├── bugfix.yaml                     # stage sequence for bug fixes
├── module-release.yaml             # six-phase release pipeline
├── manifest-template.yaml          # blank template with field docs
├── action-classification.yaml      # opt-in: enables the v0.4 judge layer
├── self-classification-rules.md    # pre-authorized cases the executor handles solo
└── roles/
    ├── manifest-drafter.md         # v1.0 -- reads your spec, drafts the manifest
    ├── researcher.md
    ├── planner.md
    ├── test-writer.md
    ├── executor.md                 # has the pre-edit fact-forcing gate
    ├── verifier.md
    ├── drift-detector.md           # manifest contract vs assembled state
    ├── critic.md                   # adversarial cold read, six lenses
    ├── manager.md                  # auto-promote-aware
    ├── judge.md                    # opt-in real-time action supervision
    ├── preflight-auditor.md        # module-release Phase 0
    ├── local-rehearsal.md          # module-release Phase 2
    ├── cross-agent-auditor.md      # v0.3 audit-handoff
    └── implementer-pre-push.md     # v0.3 audit-handoff
scripts/policy/
├── check_manifest_schema.py
├── check_allowed_paths.py
├── check_no_todos.py
├── check_adr_gate.py
├── auto_promote.py
└── run_all.py
CLAUDE.md                           # only created if you don't already have one
.agent-runs/                        # gitignored -- pipeline run artifacts land here
```

The `CLAUDE.md` starter is short and includes a `## Pipeline drafter notes` section telling the manifest-drafter where this project keeps its spec, release plan, design notes, and ledgers. Edit it before your first `/run` for best results.

## Running a pipeline

```
/run "short description of the work"
```

That's the whole command. The drafter reads your project, drafts the manifest, shows it in chat. You reply `APPROVE` to start, or describe changes.

### Other `/run` shapes

```
/run resume 2026-05-11-my-task-slug      # pick up a halted run from its last completed stage
/run status                              # list runs in this project with last-stage status
/run                                     # same as /run status
```

The old v0.5.2 commands `/new-run` and `/run-pipeline` are deprecated shims in v1.0 — they print a deprecation notice and offer to delegate to `/run`. They will be removed at v1.1.

## The three human gates

Each is a chat-message decision moment. Three universal verbs: `APPROVE` to accept, `REPLAN <description>` (or `<description>`) to revise, or — at the manager gate — `BLOCK` to halt.

1. **Manifest gate.** The drafted scope contract. You review YAML in chat and APPROVE or describe changes. The drafter loops on revision (max 5 cycles before falling back to a hand-edit prompt).
2. **Plan gate.** After research → plan, you see the planner's plan summary inline + a count of files in the blast radius + a list of open questions. APPROVE or REPLAN.
3. **Manager gate.** After everything else completes, the manager produces a PROMOTE / BLOCK / REPLAN recommendation citing the verifier, drift-detector, and critic findings verbatim. APPROVE / BLOCK / REPLAN.

When the auto-promote stage's six conditions all pass, the manager gate auto-fires (PROMOTE) and no human prompt appears. The run reports DONE-PROMOTED in its final summary.

## What about specs and release plans?

The drafter reads these patterns at the project root (or under `docs/`):

| Category | Filename patterns it walks |
| :--- | :--- |
| Project spec | `*UnifiedSpec*.md`, `SPEC.md`, `PRD.md`, `REQUIREMENTS.md`, `docs/spec/*.md` |
| Release ladder | `*ReleasePlan*.md`, `RELEASE-PLAN.md`, `ROADMAP.md`, `docs/spec/release-plan.md` |
| Per-rung scope contract | `docs/releases/v*-scope-lock.md`, `docs/releases/<rung>-scope.md` |
| Design notes | `docs/research/<version>-<feature>-design.md`, `docs/design/*.md` |
| ADRs | `docs/adr/*.md` (closed architectural decisions) |
| Conventions | `CLAUDE.md` at root |
| Findings | `audit-*/`, `findings/*.md`, `next-cleanup.md` |

If your project has none of these, the drafter falls back to a greenfield mode: it asks you to paste a 1-3 paragraph description and synthesizes a minimal spec + draft from it.

**You can also tell the drafter where to look** in your `CLAUDE.md` under a `## Pipeline drafter notes` section. The `/pipeline-init` scaffolder writes that section for you.

## v0.5 hardening (preserved in v1.0)

v1.0 keeps every safety mechanism from v0.5 — only the surface around them changed.

- **Critic stage** — adversarial cold read of every artifact in fresh context. Walks six lenses (engineering, UX, tests, docs, QA, scope). Emits `**Findings:**` count line for the auto-promote check.
- **Drift-detector stage** — compares manifest contract against assembled final state. Catches durable doc drift, status-word abuse, cross-file inconsistency. Emits `**Drift:**` count line.
- **Pre-edit fact-forcing in executor** — before the first edit per file, the executor must produce importers/callers, public API affected, schema, and the manifest goal quoted verbatim.
- **Judge layer (opt-in via file presence)** — every executor tool call classified by risk; high-risk and external-facing calls spawn an independent judge subagent with verdict allow / block / revise / escalate.
- **Machine-checkable auto-promote** — six conditions from the artifact stack: verifier-clean, critic-clean, drift-clean, policy-passed, judge-clean, tests-passed.
- **Strict manifest schema validation** — minimum-length `goal` and `definition_of_done`, non-empty `expected_outputs` / `non_goals` / `rollback_plan`, forbidden status words banned. Failure messages include remediation pointers (new in v1.0).

## v0.2 module-release pipeline (preserved)

For work whose end-state is a published release artifact, use `module-release` instead of `feature`:

```
/run "v1.2.0 release"
```

Six-phase pipeline: Phase 0 preflight (audit the release workflow before touching product code), Phase 1 scoped product work, Phase 2 local rehearsal on fresh state, Phase 3 remote release + umbrella reconciliation, Phase 4 verifier, Phase 5 manager. See `docs/module-release-handbook.md` for the full operator reference.

## v0.3 dual-AI audit-handoff (preserved)

For projects where one AI implements and a second AI audits, `/audit-init` scaffolds the shared discipline (the in-repo 5-lens self-audit doc + the out-of-repo audit gate + audit protocol). See `docs/audit-handoff-handbook.md`.

## Resuming a halted run

```
/run resume 2026-05-11-my-task-slug
```

The orchestrator reads the run's `run.log`, finds the last completed stage, and picks up at the next stage.

## Where things live

```
.agent-runs/<run-id>/
├── manifest.yaml              # the run's scope contract (drafted, then APPROVE'd)
├── draft-provenance.md        # which manifest fields came from which sources
├── research.md                # researcher's findings
├── plan.md                    # planner's plan (after human APPROVE)
├── failing-tests-report.md    # test-writer's output (feature pipeline only)
├── implementation-report.md   # executor's output
├── policy-report.md           # auto-policy checks results
├── verifier-report.md         # independent verifier's report
├── drift-report.md            # drift-detector findings
├── critic-report.md           # critic's adversarial review
├── auto-promote-report.md     # six-condition check (only when NOT_ELIGIBLE)
├── manager-decision.md        # final PROMOTE/BLOCK/REPLAN
├── judge-log.yaml             # action-level decisions (only when judge layer active)
├── judge-metrics.yaml         # action-level metrics (only when judge layer active)
└── run.log                    # chronological STAGE_DONE / STAGE_FAILED entries
```

## Migration from v0.5.x

v0.5.x users upgrading to v1.0 see no breaking changes in artifact shapes. The manifest schema is unchanged; the slash commands `/new-run` and `/run-pipeline` survive as deprecated shims (removed at v1.1). Run `cd ~/.claude/plugins/marketplaces/agent-pipeline-claude && git pull && git checkout v1.0.0` to upgrade, then restart your session. See [CHANGELOG.md](CHANGELOG.md) v1.0.0 entry for the full migration story.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues and discussions welcome.

## License

Apache-2.0. See [LICENSE](LICENSE).
