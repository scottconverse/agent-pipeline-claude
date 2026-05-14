---
name: run
description: Autonomous sprint driver for Claude Code. Type ONE goal, click GO once, walk away — the agent decomposes the goal into tasks, executes each end-to-end (plan → implement → verify → auto-fix on failure with bounded Reflexion-style retries), auto-commits per task with semantic messages, opens a PR at sprint end. Zero mid-run gates. Bounded retries (max 3 per task) instead of human escalation. Always exits with something — partial PR if a hard blocker was hit, full PR if it shipped. Invoked as /agent-pipeline-claude:run "<goal>". Goal may be a single task ("fix the auth timeout"), an explicit sprint ("ship slice 1 commits 1-5"), or open-ended ("get the cleanroom passing"). For status of in-flight runs use /agent-pipeline-claude:run status. To resume a halted run use /agent-pipeline-claude:run resume <run-id>.
---

# Run

Follow the canonical procedure in `references/run.md`. That file is the single source of truth for the autonomous loop, the one initial gate, the bounded retry mechanism, sprint decomposition, task execution, the auto-commit cadence, and the always-exit-with-something semantics.

Tool mapping:

- **`Agent`** → spawn a subagent using a role file from `<project>/.pipelines/roles/` (or the plugin's bundled defaults). The procedure names which role per stage.
- **`Bash`** → shell ops from the project root (git, tests, lint, build).
- **`AskUserQuestion`** → fires EXACTLY ONCE per run, for the initial scope-contract acknowledgment. Never inside the autonomous loop.

`$ARGUMENTS` is one of:

- A goal string — common path. The procedure auto-classifies it (single-task vs sprint vs verification) and routes to the appropriate shape.
- `status` (or empty) — list runs in `.agent-runs/` with last-stage status. Read-only.
- `resume <run-id>` — pick up a halted run from its last completed stage.

Hard rules:

- **ONE gate per run, period.** Initial scope-contract acknowledgment is the only modal `AskUserQuestion`. After GO, the loop runs autonomously until success, hard blocker, or bounded-retry exhaustion. No plan gate. No manager gate. No "view plan" detour. No "would you like me to continue?"
- **Bounded retries beat human gates.** On verifier failure, the fixer subagent runs with the failure observation prepended (Reflexion pattern). Up to 3 fix cycles per task. After 3, stop the run and exit with a partial-PR + handoff describing the blocker.
- **Auto-commit per task.** Every task that passes verification gets committed on the run's branch with a semantic message (`type(scope): summary`). No batch commits at the end. Progress is durable per task — if the run halts at task N, tasks 1..N-1 are committed and resumable.
- **Always-exit-with-something.** Even on hard blocker: write a one-paragraph blocker description, commit any in-flight work as a WIP commit if non-empty, surface the resume instruction. Never crash silently.
- **Never admin-merge a PR, push a tag, or create a release.** These are operator decisions. The pipeline pushes the branch and opens the PR (auto), but the human merges.
- **Never modify the scope contract mid-run.** The contract is locked at GO. If a task surfaces work outside the contract, mark it `out-of-scope` in the run log and skip it.
- **Self-feedback is the recovery loop.** When tests fail, the failure output IS the next agent's input. No separate "critique" stage. Errors get stuffed back into the prompt for the next attempt (SWE-agent / Aider pattern).
- **Status vocabulary in artifacts is binary or quantitative — no "done / complete / ready / shippable" status words.** Use `passes / fails / partial / blocked / pending` for human-readable state.
- **Never write outside `.agent-runs/<run-id>/` and the project working tree** that the run is authorized to modify per its scope contract.
- **`free -g`, `df -h`, dependency presence checks BEFORE infrastructure work.** Verification-shape runs that depend on Docker / GPU / specific RAM check those pre-conditions BEFORE the long-running stage. Don't burn a 30-minute install just to fail at minute 31.
