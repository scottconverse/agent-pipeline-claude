# agentic-pipeline — User Manual

A Claude Code plugin that orchestrates multi-stage agentic work with three human-approval gates. Built from real lessons across multi-week agent projects where autonomous runs go wrong silently and "manager-PROMOTE" failures slip past CI.

**Version:** 0.5.1
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
9. [The judge layer (v0.4)](#the-judge-layer-v04)
10. [Single-AI hardening (v0.5)](#single-ai-hardening-v05)
11. [Troubleshooting](#troubleshooting)
12. [Glossary](#glossary)

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

Four slash commands:

| Command | Purpose |
| :--- | :--- |
| `/pipeline-init` | Onboard a project. Accepts a PRD path, a repo URL, or a description paragraph. Scaffolds `.pipelines/`, `scripts/policy/`, and `CLAUDE.md` if missing. |
| `/new-run <type> <slug>` | Initialize a new pipeline run. Creates `.agent-runs/<run-id>/manifest.yaml` from the template and asks you to fill it in. |
| `/run-pipeline <type> <run-id>` | Orchestrate a pipeline run end-to-end. Stops at human gates and on failure. Resumable. |
| `/audit-init` | (v0.3) Scaffold dual-AI audit-handoff infrastructure for projects where one AI implements and another audits. |

Three default pipeline definitions:

- **`feature`** — 11 stages: manifest → research → plan → test-write → execute → policy → verify → drift-detect → critique → auto-promote → manager
- **`bugfix`** — 10 stages: manifest → research → reproduce → patch → policy → verify → drift-detect → critique → auto-promote → manager
- **`module-release`** — six-phase release pipeline with Phase 0 preflight + Phase 2 local rehearsal (v0.2+)

Thirteen self-contained role files (markdown) — each tells a fresh Claude session exactly what to do and what is forbidden: `researcher`, `planner`, `test-writer`, `executor` (with v0.5 pre-edit fact-forcing), `verifier`, `drift-detector` (v0.5), `critic` (v0.5), `manager` (auto-promote-aware at v0.5), `judge` (v0.4 opt-in), `preflight-auditor` (v0.2), `local-rehearsal` (v0.2), `cross-agent-auditor` (v0.3), `implementer-pre-push` (v0.3).

Six generic policy checks (Python, stdlib only):

- `check_manifest_schema.py` — v0.5 strict manifest contract validator
- `check_allowed_paths.py` — manifest-driven path enforcement
- `check_no_todos.py` — no TODO/FIXME/HACK in source
- `check_adr_gate.py` — ADRs are append-only
- `auto_promote.py` — v0.5 six-condition machine-checkable promote
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

### Verifying which release is installed

Two of the v0.5 policy scripts ship a `--version` flag for sanity-checking the install:

```bash
python scripts/policy/auto_promote.py --version
python scripts/policy/check_manifest_schema.py --version
```

Each prints `agentic-pipeline 0.5.1` and exits 0. The flag fires before any other argument validation, so it works on `auto_promote.py` without supplying `--run`. Use it to confirm a project actually has the v0.5 scripts and not stale copies from an earlier `/pipeline-init`.

If the script doesn't recognize `--version` (argparse prints a usage error and exits 2), the install is pre-v0.5. Re-run `/pipeline-init` to refresh the scripts from the plugin source.

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

## The judge layer (v0.4)

The judge layer is **real-time action-level supervision inside the executor stage**. It is opt-in: if `.pipelines/action-classification.yaml` exists in your project, the orchestrator detects it at run start and uses Handler 3a (classify → judge → execute) instead of Handler 3 for the executor stage. If the file is absent, the executor stage runs unchanged from v0.3.

The judge catches a failure mode the other gates can't: unauthorized actions that execute before the policy or verifier can see them. Destructive commands (`rm -rf`, `DROP TABLE`), external writes (`gh pr create`, `docker push`), force pushes, and credential-touching operations are intercepted at the action boundary and evaluated against the manifest.

### Enabling it

Two ways:

**Via `/pipeline-init` (recommended).** When `/pipeline-init` runs on a new or existing project, it offers to scaffold `.pipelines/action-classification.yaml` along with the rest of the pipeline files. If you accept, the judge layer is enabled. If you decline, you can enable it later by copying the file from the plugin: `cp <plugin-path>/pipelines/action-classification.yaml .pipelines/`.

**Manually.** Copy `pipelines/action-classification.yaml` from the plugin install into your project's `.pipelines/` directory. The next run after the copy lands will use the judge layer.

Disable by deleting the file. The next run reverts to v0.3 executor behavior.

### Customizing the classification rules

The shipped `action-classification.yaml` covers the common dangerous and external-facing patterns: `rm -rf`, `git push --force`, `npm publish`, `kubectl apply`, etc. Your project will have its own:

- Your project's deploy command — add it under `high_risk`.
- Your project's local preview server — add it under `reversible_write` (it's a side-effect-free local process).
- Your project's specific API endpoints accessed via `curl` — already caught by the generic `curl -X POST` rule, but you can add narrower rules for specific endpoints that you want named for clearer judge reasoning.

Edit order matters: rules are evaluated top-to-bottom **within each class**, and class priority is `high_risk` → `external_facing` → `reversible_write` → `read_only`. If you want a particular `gh release create` to be `high_risk` (because publishing a release is irreversible in your project), move that rule into the `high_risk` block.

When in doubt: classify conservatively. The cost of a false `high_risk` classification is one extra human confirm; the cost of a missed `high_risk` is the Lindy 14-email case.

### Reading judge-log.yaml

Every action — auto-allowed or judged — gets one entry in `.agent-runs/<run-id>/judge-log.yaml`:

```yaml
actions:
  - action_id: "exec-001"
    tool: bash
    arguments: "cat src/auth/models.py"
    class: read_only
    disposition: auto_allow
    timestamp: "2026-05-11T14:30:00Z"
  - action_id: "exec-007"
    tool: bash
    arguments: "git push origin main"
    class: high_risk
    disposition: judged_revise
    judge_verdict: revise
    judge_reason: "Manifest authorizes implementation on feature branch; main push is not in scope."
    revision_instruction: "Push to feature/judge-layer-v0.4 instead of main."
    timestamp: "2026-05-11T14:35:12Z"
```

The seven possible `disposition` values:

- `auto_allow` — action was `read_only` or `reversible_write`; executed without judge invocation.
- `judged_allow` — `external_facing` action; judge said ALLOW; executed.
- `judged_revise` — judge said REVISE; revision sent back to executor; executor produced a corrected proposal.
- `judged_block` — judge said BLOCK; action did not execute; pipeline halted.
- `judged_escalate` — judge said ESCALATE; pipeline paused for human input.
- `human_confirmed` — judge said ALLOW on `high_risk`, OR judge said ESCALATE and human approved; action executed.
- `human_blocked` — judge said ALLOW on `high_risk` but human refused, OR judge said ESCALATE and human refused; action did not execute; pipeline halted.

When reading the log, focus on the `judged_*` and `human_*` entries first — those are the moments the judge or you actually exercised judgment. The `auto_allow` entries are the audit trail; you typically only read them when investigating a specific incident.

### Reading judge-metrics.yaml

Aggregate counts and the tuning signal:

```yaml
total_actions: 23
by_class:
  read_only: 12
  reversible_write: 7
  external_facing: 3
  high_risk: 1
by_disposition:
  auto_allow: 19
  judged_allow: 2
  judged_revise: 1
  judged_block: 0
  judged_escalate: 1
  human_confirmed: 1
  human_blocked: 0
escalation_rate: 0.087
judge_invocations: 4
revision_cycles: 1
```

`escalation_rate` is `(judged_escalate + human_blocked) / total_actions`. It's the operator's tuning signal:

- **Too low (e.g., 0.00)** — the classification rules may be too permissive. The judge is allowing things you would have wanted to confirm. Tighten by moving borderline rules from `external_facing` to `high_risk`, or by adding project-specific rules under stricter classes.
- **Too high (e.g., >0.20)** — every other action is paging you. This is the **cookie-banner effect** the judge layer exists to prevent: humans flooded with confirmation prompts learn to click APPROVE reflexively, defeating the gate. Loosen by moving over-strict rules to a less-strict class, or by adding more specific patterns that catch the truly dangerous cases without sweeping in routine ones.
- **Healthy range (rough guide, project-dependent)** — `0.02 – 0.10`. Most actions auto-allowed; a few external/high-risk actions per run; one or two genuine human checks. Treat the rate as a moving average over many runs, not a single-run target.

`revision_cycles` is the cumulative count of judge-REVISE → executor-retry pairs across all actions. High revision_cycles with low judge_block suggests the executor is converging on correct actions after a couple of nudges — generally healthy. High revision_cycles **with** a final auto-escalate on the same action means the executor and judge disagree fundamentally on what the manifest authorizes — that's a manifest clarity bug, not an agent bug.

### Adding project-specific rules

Two common cases:

**Your deploy command is high-risk.** If `make deploy-prod` (or whatever) is your push-to-production trigger, add it under `high_risk`:

```yaml
high_risk:
  # ... existing entries ...
  - pattern: '\bmake\s+deploy-prod\b'
    tool: bash
    note: "Production deploy. Externally visible; requires explicit manifest authorization."
```

**Your API has a specific destructive endpoint.** If `curl -X DELETE https://api.example.com/v1/customers` is something you never want auto-allowed, add a more specific rule **above** the generic `curl -X DELETE` entry under `external_facing`, OR promote it to `high_risk`:

```yaml
high_risk:
  - pattern: 'curl.*example\.com/v1/customers'
    tool: bash
    note: "Customer-data DELETE. Irreversible and PII-touching."
```

Rules are first-match-wins within each class, and the four classes are evaluated in priority order (`high_risk` first). Putting the specific rule in a higher-priority class means it wins regardless of the generic rule's position.

### When the judge ESCALATEs and you aren't sure

The judge's `escalation_question` is designed to be answerable without reading other artifacts. If you find yourself unable to answer, the manifest is probably ambiguous — the right move is to halt, edit the manifest to remove the ambiguity, and re-run. The escalation question itself often tells you exactly which manifest field is unclear.

Do NOT routinely click APPROVE on escalations you don't fully understand. That's the cookie-banner effect arriving in slow motion. If escalations are happening on the same kind of question repeatedly, that's a manifest-template improvement to make for your project.

---

## Single-AI hardening (v0.5)

v0.5 adds three stages between `verify` and `manager` plus a strict manifest schema validator. The pipeline now looks like:

```
manifest → research → plan → test-write → execute → policy → verify →
drift-detect → critique → auto-promote → manager
```

You don't opt into v0.5 — every new run on a project initialized with v0.5 plumbing gets the three stages automatically. The point of v0.5 is making the pipeline credible when one AI runs the whole thing.

### What each new stage does

**drift-detect.** A read-only role that compares the manifest's contract (`goal`, `expected_outputs`, `definition_of_done`, `non_goals`) against the assembled final state — durable docs included (`CHANGELOG.md`, `README.md`, `USER-MANUAL.md`, ADRs, any project HANDOFF). It catches the gap class neither the judge (per-action) nor the verifier (per-criterion) sees: documents that say one thing while code says another, version strings out of sync, status-word abuse, "Closed" without evidence. Emits a parseable count line:

```
**Drift: <total> total, <blocker> blocker**
```

**critique.** A hostile cold read of every artifact in a fresh context. The critic role contract forbids encouragement, severity softening, "no findings" without per-lens evidence, and trusting the verifier or executor at face value. Walks six lenses — engineering, UX, tests, docs, QA, scope — and emits a parseable count line:

```
**Findings: <total> total, <blocker> blocker, <critical> critical, <major> major, <minor> minor**
```

**auto-promote.** A pipeline (script) stage, not an agent. Runs `scripts/policy/auto_promote.py`, which reads the count lines from verifier/critic/drift/policy/judge artifacts and checks six conditions:

1. Verifier-clean: zero `NOT MET` and zero `PARTIAL` criteria.
2. Critic-clean: zero blocker findings and zero critical findings.
3. Drift-clean: zero blocker drift items.
4. Policy-passed: `POLICY: ALL CHECKS PASSED`.
5. Judge-clean: zero `judged_block` and zero `human_blocked` (vacuous when judge layer is off).
6. Tests-passed: a recognizable `N passed[, 0 failed]` in `implementation-report.md`.

When all six pass, the script writes `manager-decision.md` with `**Decision: PROMOTE**` and a citation block. The manager stage detects the preset and short-circuits the human gate — you only see the manager gate when something needs your attention. When any condition fails, the script writes `auto-promote-report.md` naming the failing conditions and the manager stage runs normally with the human gate active.

### Pre-edit fact-forcing in executor

Before the executor's first edit/write to any file in a run, it must produce a fact block (importers/callers, public API affected, data schema touched, manifest goal quoted verbatim) — either inline in `implementation-report.md` or in `.agent-runs/<run-id>/notes/pre-edit-<filename>.md`. The drift-detector and critic check for the block; a missing block on any touched file is a finding.

This is the v0.5 substitute for "tell the agent to read carefully." Asking is useless; demanding a written artifact forces the investigation.

### Strict manifest schema validation

`scripts/policy/check_manifest_schema.py` enforces:

- `goal` ≥ 30 chars, no forbidden status words (`done`, `complete`, `ready`, `shippable`, `taggable`)
- `definition_of_done` ≥ 80 chars, same word ban
- `expected_outputs` non-empty
- `non_goals` non-empty
- `rollback_plan` non-empty
- Broad `allowed_paths` (top-level directory like `src/`) requires non-empty `forbidden_paths`

The check fires both at run-start (Phase A2 in `/run-pipeline`) AND inside the policy stage (defense in depth). Fuzzy manifests fail at the gate before they cascade into downstream work.

### Honest limit

Single-model-family blind spots correlate. If both the executor and the critic share a wrong assumption that fits the manifest, both sign off and auto-promote fires green. Dual-AI (v0.3 `/audit-init`) is the only structural defense against this. **Recommended mitigation:** periodic sample audit by a different model family on a weekly cadence. The v0.5 single-AI release does not replace v0.3; it provides single-AI projects a credible alternative when a second model family is not available.

### When auto-promote refuses

`auto-promote-report.md` names exactly which condition(s) failed. Typical fixes:

- **Verifier-clean fails:** open `verifier-report.md`, address every NOT MET / PARTIAL criterion. Then re-run the verifier stage.
- **Critic-clean fails:** open `critic-report.md`. Blocker or critical findings need to be addressed in code or in the manifest before the run promotes. Minor findings don't block.
- **Drift-clean fails:** open `drift-report.md`. Blocker drift typically means a durable doc lies about the change — fix the doc.
- **Policy fails:** open `policy-report.md`. Same as pre-v0.5 — fix the violation.
- **Tests-passed fails:** the implementation-report.md doesn't have a recognizable test-passing signal. Re-run tests, paste output, re-run executor stage with the fix.

Re-running `/run-pipeline <type> <run-id>` after fixing the underlying issue picks up at the failing stage thanks to the append-only `run.log`.

---

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
- **Judge** (v0.4) — a fresh-context subagent invoked by the orchestrator inside the executor stage to evaluate individual proposed tool calls against the manifest. Returns `allow`, `block`, `revise`, or `escalate`. Activated by the presence of `.pipelines/action-classification.yaml`.
- **Action class** (v0.4) — the risk category for an executor tool call: `read_only`, `reversible_write`, `external_facing`, or `high_risk`. Determines routing (auto-execute, judge, or judge-plus-human-confirm).
- **Escalation rate** (v0.4) — `(judged_escalate + human_blocked) / total_actions` in `judge-metrics.yaml`. Operator's tuning signal; high values indicate cookie-banner fatigue.

---

## Source of truth

This manual is the user-facing reference. The architecture and design rationale live in `ARCHITECTURE.md`. Plugin metadata is in `.claude-plugin/plugin.json`. Bug reports and feature requests: GitHub Discussions on the plugin repo.
