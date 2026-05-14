# agent-pipeline-claude

**v2.0.0 — autonomous sprint driver for Claude Code.**

Type one goal. Click GO once. Walk away. The agent decomposes the goal into ordered tasks, executes each end-to-end (plan → implement → verify → auto-fix on failure with bounded Reflexion-style retries), auto-commits per task with semantic messages, opens a PR at sprint end.

**Zero mid-run gates.** Bounded retries (max 3 per task) instead of human escalation. Always exits with something — partial PR if a hard blocker was hit, full PR if it shipped.

```
/agent-pipeline-claude:run "ship slice 1 commits 1-5 of v0.4"
                ↓
        scope drafted → ONE AskUserQuestion → GO
                ↓
   for each task in scope.tasks:
      worker → plan + implement + self-verify
        ↓ passes      ↓ fails           ↓ blocked
       commit ↻      retry (max 3)     escalate
                       w/ failure obs
                       (Reflexion)
                ↓
   integration suite → push branch → PR opened
```

---

## Why v2.0

v1.0–v1.3 were variations on the same idea: an 11-stage feature pipeline with three mandatory human gates and 14 role files. Even after v1.3.0's modal-gate fix, the structure forced ceremony on every shape of work. A 6-step verification cleanroom and a single bug fix both ran the same 11 stages. Operators spent more time clicking gates and reading artifact ceremony than seeing the agent ship product.

v2.0 collapses the entire pipeline shape to a single autonomous loop. **One review gate at the start. After GO, the loop runs until success, hard blocker, or bounded-retry exhaustion. No mid-run modal dialogs. No "view plan" detours.**

Design informed by:
- **SWE-agent** (`max_requeries=3` + autosubmit on any error path)
- **Aider** (`max_reflections=3` + auto-commit per successful edit)
- **OpenHands** (stuck-detector at 3-4 repeats + graceful ERROR state)
- **Reflexion** (Yao et al., 2023 — failure-as-observation tutoring)
- **GitHub release-please** (gate once at detect, fan out many publish jobs)
- **LangGraph** (checkpointed resumable state per thread)

---

## Install

```bash
# Through Cowork / Claude Code marketplace (recommended):
#   Open the plugin marketplace, search "agent-pipeline-claude", install.

# Or git-clone for development:
git clone https://github.com/scottconverse/agent-pipeline-claude.git
# Then point Claude Code at the local plugin dir.
```

After install, in any project:

```bash
/agent-pipeline-claude:pipeline-init       # scaffold .pipelines/ + scripts/policy/
/agent-pipeline-claude:run "<your goal>"   # start an autonomous run
/agent-pipeline-claude:run status          # list runs in .agent-runs/
/agent-pipeline-claude:run resume <id>     # pick up a halted run
```

---

## The run shape

Three goal types, one pipeline:

| Goal style | Example | What v2.0 does |
|---|---|---|
| **Single task** | `"fix the auth-timeout bug"` | One task, one commit, one PR. |
| **Explicit sprint** | `"ship slice 1 commits 1-5"` | Read existing sprint plan; loop over its tasks; one PR at the end. |
| **Open-ended** | `"get the cleanroom passing"` | Decompose into 3-7 tasks at draft time; loop; one PR. |

In every case: ONE `AskUserQuestion` modal at the scope-gate step. Click GO once. The autonomous loop runs from there.

---

## The autonomous loop

For each task in scope:

1. **Worker subagent** spawns with the task description, scope contract, allowed_paths, success criteria. It plans internally (no `plan.md` artifact), implements via Edit/Write, self-verifies via Bash (runs tests/lint/build).
2. **Worker reports status** as the first line of its output file: `**Status: passes**` / `**Status: fails**` / `**Status: blocked**`.
3. **Orchestrator decides**:
   - `passes` → auto-commit on the run's branch with a semantic message → next task.
   - `fails` → spawn worker again with `PRIOR_FAILURE_OBSERVATION` populated from the failure output. Max 3 attempts. After 3 failures, the task is blocked.
   - `blocked` → escalate. If ≥50% of tasks have passed, SHIP_PARTIAL (commit WIP + run integration + push + open WIP PR). If <50%, HARD_HALT (commit WIP + write HANDOFF.md + exit).
4. **After all tasks**: run integration suite, push branch, `gh pr create`, done.

**That's the whole pipeline.** No separate research, plan, test-write, drift, critique, manager stages. No 11 artifacts. Just scope + worker outputs + run.log.

---

## Hard rules (baked in)

- **ONE `AskUserQuestion` per run.** Period. The scope gate is the only modal. The loop is silent.
- **Auto-commit per task.** Never `git add -A`. Stage allowed_paths only. Never batch commits.
- **Always exit with something.** Hard blocker → WIP commit + HANDOFF.md + clean exit. Resumable.
- **Never admin-merge a PR.** Never push tags. Never create releases. Operator-only.
- **Self-feedback is the recovery loop.** Failure output goes verbatim into the next worker's prompt. No separate critique stage.

---

## What's in this plugin

```
.claude-plugin/
  plugin.json                v2.0.0 manifest

skills/
  run/                       /agent-pipeline-claude:run
    SKILL.md
    references/run.md        ← the autonomous procedure (heart of v2.0)

  pipeline-init/             /agent-pipeline-claude:pipeline-init
    SKILL.md
    references/pipeline-init.md
    references/pipeline-payload/   ← scaffolded into target projects

  audit-init/                /agent-pipeline-claude:audit-init
    SKILL.md                 (unchanged from v1.x; dual-AI audit-handoff infra)
    references/

pipelines/
  sprint.yaml                outer pipeline (scope → ONE gate → loop → ship)
  sprint-task.yaml           per-task pipeline (worker + retry + commit)
  roles/
    worker.md                THE role file. plan + implement + verify, single subagent.

scripts/
  scaffold_pipeline.py       deterministic scaffold (used by pipeline-init)
  run_status.py              list runs (used by /run status path)
  validate_scope.py          lightweight scope.md structure check

tests/
  test_v2_plugin_layout.py   pins the v2.0 contract
  test_scaffold_pipeline.py
  test_run_status.py
  test_validate_scope.py

README.md / USER-MANUAL.md / ARCHITECTURE.md / CHANGELOG.md / LICENSE
```

When `pipeline-init` runs in a project, it scaffolds:

```
<your-project>/
  .pipelines/
    sprint.yaml
    sprint-task.yaml
    roles/worker.md
  scripts/policy/
    run_status.py
    validate_scope.py
    __init__.py
```

---

## Migration from v1.3.x

v2.0 is a deliberate scope reduction. The 14 role files, 11-stage feature pipeline, 18 policy scripts, and grant-based autonomous mode are GONE. See `CHANGELOG.md` for the full list.

**For existing v1.3 projects:**

- Run `pipeline-init` in the project. It detects the v1.3 `.pipelines/` and offers to back it up to `.pipelines.v1.3.bak/` before scaffolding v2.0 fresh.
- In-flight v1.3 runs under `.agent-runs/` — finish them on v1.3 before upgrading (v2.0's run.md doesn't read v1.3 manifest format).

---

## License

Apache-2.0. See `LICENSE`.

## Contributing

See `CONTRIBUTING.md`. Pull requests welcome; v2.0 is a brand-new surface and there's room for hardening, especially around the integration-suite handling and `gh pr create` body formatting.
