# Architecture — agent-pipeline-claude v2.0

The plugin orchestrates autonomous sprint runs across three layers. v2.0 is a ground-up rewrite from v1.3.x; the design follows SWE-agent, OpenHands, Aider, Reflexion, and GitHub release-please patterns.

---

## 1. The three layers

1. **Plugin layer** (`agent-pipeline-claude/`) — slash command surface, the autonomous procedure (`skills/run/references/run.md`), the worker role file, the bundled payload for `pipeline-init`. Versioned, shared across all your projects.
2. **Project layer** (`<your-project>/`) — files `pipeline-init` scaffolded: `.pipelines/sprint.yaml`, `.pipelines/sprint-task.yaml`, `.pipelines/roles/worker.md`, `scripts/policy/run_status.py`, `scripts/policy/validate_scope.py`. Yours to customize.
3. **Run layer** (`<your-project>/.agent-runs/<run-id>/`) — one directory per pipeline run, containing scope.md, tasks.md, per-task worker outputs, integration.log, run.log. Gitignored by default.

```
┌──────────────────────────────────────────────────────────────┐
│ Plugin layer (one install per machine)                        │
│   .claude-plugin/plugin.json    (v2.0.0)                      │
│   skills/run/SKILL.md           (/agent-pipeline-claude:run)  │
│   skills/run/references/run.md  ← the autonomous procedure    │
│   skills/pipeline-init/         (/agent-pipeline-claude:pipeline-init)
│   pipelines/sprint.yaml         (outer sprint pipeline contract)
│   pipelines/sprint-task.yaml    (per-task contract)           │
│   pipelines/roles/worker.md     (the ONE role file)           │
│   scripts/scaffold_pipeline.py  (used by pipeline-init)       │
│   scripts/run_status.py         (used by `/run status`)       │
│   scripts/validate_scope.py     (lightweight scope.md check)  │
└──────────────────────────────────────────────────────────────┘
                          │
                          │ /pipeline-init copies the payload into
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ Project layer (per repo, after `pipeline-init`)              │
│   .pipelines/sprint.yaml                                      │
│   .pipelines/sprint-task.yaml                                 │
│   .pipelines/roles/worker.md                                  │
│   scripts/policy/run_status.py                                │
│   scripts/policy/validate_scope.py                            │
│   .gitignore                    (should include .agent-runs/) │
└──────────────────────────────────────────────────────────────┘
                          │
                          │ /agent-pipeline-claude:run produces
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ Run layer (per invocation)                                    │
│   .agent-runs/<run-id>/                                       │
│     scope.md                  (the locked scope contract)     │
│     tasks.md                  (per-task state: pending/passed/…│
│     task-<id>-attempt-<N>.md  (worker output per attempt)     │
│     integration.log           (final integration suite output)│
│     run.log                   (append-only event stream)      │
│     HANDOFF.md                (only on hard halt)             │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. The autonomous loop

The procedure in `skills/run/references/run.md` is the only orchestrator. It runs in the operator's Claude Code session — there is no separate orchestrator subagent.

```
1. /agent-pipeline-claude:run "<goal>"
   ↓
2. Orient: read control plane, spec, CLAUDE.md, recent commits
   ↓
3. Generate run_id; classify goal (task vs sprint mode)
   ↓
4. Draft scope.md in the main session (no subagent)
   ↓
5. ONE AskUserQuestion modal: GO / REVISE / BLOCK
   ↓ GO
   ↓
6. Initialize tasks.md from scope.tasks
   ↓
7. For each task in order:
     7a. Mark task in_progress; log TASK_STARTED
     7b. Spawn worker subagent with task + scope context + (if retry) PRIOR_FAILURE_OBSERVATION
     7c. Read worker's status from output file's first line
     7d. passes → auto-commit (allowed_paths only) → log TASK_PASSED → next
     7e. fails  → if attempt < 3: re-spawn with observation prepended (Reflexion)
                 if attempt = 3: log TASK_RETRY_EXHAUSTED → escalate
     7f. blocked → escalate (≥50% passed: SHIP_PARTIAL; <50%: HARD_HALT)
   ↓
8. Run integration suite (project-defined: pytest / npm test / cargo test / etc.)
   ↓ pass
   git push -u origin <branch>
   gh pr create
   ↓
9. Final chat report → done
```

**Hard rules baked in:**

- Steps 1–6 + 9 happen in the operator's session. Step 7 spawns subagents but the orchestrator stays in the operator's session.
- ONE `AskUserQuestion` (Step 5). The loop is silent.
- Bounded retries: max 3 per task.
- Auto-commit per task. Never `git add -A`. Stage allowed_paths.
- Always exit with something: WIP commit + HANDOFF.md even on hard halt.
- Never admin-merge a PR. Never push tags. Never create releases.

---

## 3. The worker role

`pipelines/roles/worker.md` is the only subagent role v2.0 ships. The worker:

1. **Reads context efficiently.** scope.md, tasks.md, CLAUDE.md, the specific files the current task touches. Uses Grep for symbol lookup; doesn't read the world.
2. **Plans internally.** No `plan.md` artifact. Just decides the approach in its head.
3. **Implements.** Edit/Write inside `allowed_paths`. Never touches `forbidden_paths`.
4. **Self-verifies.** Bash to run tests, lint, type-check. Real commands, real output.
5. **Reports.** Writes ONE file: `task-<task-id>-attempt-<N>.md`. **First line is the status**: `**Status: passes**` / `**Status: fails**` / `**Status: blocked**`. Below that: what was done, the verbatim verification output, a diagnosis paragraph if non-passes.

The worker is a leaf node. It does not spawn other agents. It writes one file and stops.

**Fix mode (when `PRIOR_FAILURE_OBSERVATION` is populated):** the worker reads the prior attempt's failure observation FIRST, diagnoses the actual cause, picks a different approach than the prior attempt, addresses the cause directly in its `## Diagnosis` section.

---

## 4. Reflexion-style recovery

When the worker reports `fails`, the orchestrator:

1. Reads the worker's full output file.
2. Extracts the verbatim verification output (test stderr, lint output, build error).
3. Re-spawns the worker with that output prepended to the prompt as `PRIOR_FAILURE_OBSERVATION`.

The next worker reads its tutor (the failure) before touching code. It can pick a different approach because the cause is in front of it. This is the Reflexion + SWE-agent pattern collapsed into a single role.

After 3 failed attempts, the task is `blocked`. No more retries. The orchestrator escalates.

```
Attempt 1: worker → fails (test_jwt_expiry: expected 14d, got 24h)
            ↓ observation prepended
Attempt 2: worker → fails (test_jwt_expiry: expected 14d, got 7d  ← partial fix)
            ↓ observation prepended
Attempt 3: worker → passes (test_jwt_expiry green)
            ↓ commit
            next task
```

Or:

```
Attempt 1: worker → fails (test_jwt_expiry: import error in jwt.py)
Attempt 2: worker → fails (test_jwt_expiry: same import error — wrong fix shape)
Attempt 3: worker → fails (test_jwt_expiry: yet a different error)
            ↓ retry exhausted
            ↓ task marked blocked in tasks.md
            ↓ escalate
```

---

## 5. Escalation policy

When a task is blocked (3 failures OR worker self-reports blocked):

```
passed_count / total_count
       ≥ 50% → SHIP_PARTIAL
              - Commit any in-flight WIP work as `wip(scope): partial on <task>`
              - Run integration suite
              - Push branch
              - Open PR with title prefixed [WIP] + body naming the blocked task
              - log PR_OPENED
              - Operator can resume the run later, or merge the partial PR

       < 50% → HARD_HALT
              - Commit any WIP work
              - Write HANDOFF.md with: what's done, what's blocked, the cause,
                the exact resume command (`/agent-pipeline-claude:run resume <id>`)
              - Display HANDOFF.md content in chat
              - Do NOT push the branch
              - Operator inspects HANDOFF.md, fixes the underlying issue,
                and either resumes or starts a new run
```

The 50% threshold is the SHIP_PARTIAL vs HARD_HALT decision boundary. The intent: if most of the sprint landed, the operator probably wants the PR to review; if barely anything landed, the partial isn't worth a PR yet.

---

## 6. State + resumability

`run.log` is append-only. Resume reads it backward:

- Last line `RUN_DONE` → already shipped; display PR URL, exit.
- Last line `TASK_RETRY_EXHAUSTED <id>` → that task is blocked. Resume at the NEXT task.
- Last line `TASK_PASSED <id>` → that task is done. Resume at the NEXT task.
- Last line `TASK_STARTED <id>` without paired `TASK_PASSED` → that task was in flight when the run died. Resume from it as attempt 1.

Resumability comes from durable per-task commits + the append-only log. No checkpointer infrastructure needed.

---

## 7. The single human gate

`AskUserQuestion` at Step 5 is the only modal. It surfaces:

- The goal (one sentence)
- Mode (task / sprint)
- Branch
- N tasks (numbered list, name only)
- Top-level allowed paths
- Estimated complexity

Options: `GO` / `REVISE` / `BLOCK`.

- **GO** → log `SCOPE_APPROVED`, enter the loop. The loop is silent until done.
- **REVISE** → ask what to change in chat, re-draft scope.md, re-fire the modal. Max 3 revise cycles per run; on the 4th the orchestrator halts and suggests running `pipeline-init` to fix project metadata.
- **BLOCK** → log `RUN_BLOCKED at scope gate`, exit.

**Nothing else triggers a modal.** Not failed verification (handled by Reflexion retry). Not blocked task (handled by escalation policy). Not push failure (handled by clean halt + resume instruction).

---

## 8. Comparison with v1.3.x

| Concept | v1.3.x | v2.0 |
|---|---|---|
| Pipeline stages | 11 (research, plan, test-write, execute, policy, verify, drift-detect, critique, auto-promote, manager + manifest gate) | 2 (worker + commit per task) + 1 outer (integration + push + PR) |
| Role files | 14 (researcher, planner, executor, verifier, drift-detector, critic, manager, manifest-drafter, judge, preflight-auditor, local-rehearsal, test-writer, implementer-pre-push, cross-agent-auditor) | 1 (worker) |
| Human gates | 3 mandatory (manifest, plan, manager — manager auto-promotable) | 1 mandatory (scope) |
| Policy scripts | 18 (manifest schema, paths, immutable, allowed_paths, no-todos, adr-gate, active-target, autonomous-mode, autonomous-compliance, manager-evidence, critic-evidence, stage-done, skill-packaging, run-all, run-preflight, auto-promote, preflight-infrastructure, scaffold) | 3 (scaffold, status, scope-validate) |
| Artifacts per run | 11+ (manifest, draft-provenance, research, plan, failing-tests, implementation, policy, verifier, drift, critic, auto-promote, manager-decision) | 3-4 (scope, tasks, task-attempt-N, run.log, optional handoff) |
| Retry mechanism | No retry — failure surfaces manager BLOCK | Bounded 3 attempts with Reflexion observation passing |
| Failed-run state | Halted with artifacts but no commit | WIP commit + HANDOFF.md, resumable |

---

## 9. What stays from v1.x

- **Cowork-first slash-command surface.** v2.0 ships the same `/agent-pipeline-claude:*` namespace.
- **Pipeline-init skill** for project scaffolding (now scaffolds the v2.0 minimal payload, not the v1.3 behemoth).
- **Audit-init skill** for dual-AI audit-handoff infrastructure. Unchanged from v1.x.
- **Append-only run.log.** Same audit-trail pattern.
- **Never admin-merge / push tags / create releases.** Operator-only.
- **`.agent-runs/<run-id>/`** as the per-run state directory.
- **Auto-promote concept** (in v1.3 a stage that ran at end; in v2.0 it's the default behavior of every stage that isn't the scope gate).
