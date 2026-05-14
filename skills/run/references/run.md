# Run procedure — autonomous sprint driver (v2.0.0)

You are the autonomous sprint driver. Replaces v1.3.x's 11-stage feature pipeline + 3 mandatory human gates with a single review gate followed by an autonomous loop.

**Design principles** (synthesized from SWE-agent, OpenHands, Aider, AutoGen, CrewAI, LangGraph, GitHub release-please, Reflexion):

1. **One review gate, then go.** Single initial scope-contract acknowledgment via `AskUserQuestion`. No mid-run gates. No plan gate. No manager gate.
2. **Observation-as-feedback recovery.** When verification fails, prepend the failure output to the fixer subagent's prompt verbatim. No separate "critique" stage. Reflexion + SWE-agent pattern.
3. **Bounded retries beat human escalation.** Up to 3 fix attempts per task. After exhaustion, halt with partial work committed + a one-paragraph blocker description. SWE-agent / Aider / OpenHands stuck-detector pattern.
4. **Auto-commit per task.** Progress is durable per task. Tasks 1..N-1 stay committed even if task N hits the retry ceiling.
5. **Always-exit-with-something.** Hard blocker → commit in-flight work as WIP, write handoff, exit cleanly. Resumable via `/agent-pipeline-claude:run resume <run-id>`. SWE-agent autosubmit pattern.
6. **Single role file.** One subagent role (`worker.md`) handles plan + implement + verify per task. Fixer reuses the same role with `prior_failure_observation` injected. Massive simplification from v1.3's 14 roles.
7. **State is lightweight.** `.agent-runs/<run-id>/scope.md`, `tasks.md`, `run.log`. No 11-artifact ceremony.

---

## Argument shapes

`$ARGUMENTS` is one of:

1. **A goal string** (common path). E.g.:
   - `"fix the auth-timeout bug"`
   - `"ship slice 1 commits 1-5 of v0.4"`
   - `"get the civicrecords-ai cleanroom passing on Linux WSL"`
2. **`resume <run-id>`** — pick up a halted run.
3. **`status`** (or empty) — list runs in `.agent-runs/` read-only.

Decide by checking the first whitespace-separated token.

---

## Path 1 — start a new run

### Step 1 — drop into the project root

If `$PWD` does not have a `.pipelines/` directory, this project hasn't been initialized for pipeline runs. Tell the user:

> This project hasn't been pipeline-initialized. Run `/agent-pipeline-claude:pipeline-init` first, or just say "init it" — that scaffolds `.pipelines/` and `scripts/policy/` from the plugin's bundled defaults. Comes back in <30 seconds.

Stop. Do not improvise scaffolding from here.

### Step 2 — orient against project state

Read in this order, stopping at the first match per category:

- **Control plane** (if present): `.agent-workflows/PROJECT_CONTROL_PLANE.md`, `.agent-workflows/ACTIVE_WORK_QUEUE.md`, `docs/RELEASE_PLAN.md`, `docs/PROJECT_CONTROL_PLANE.md`. Note the "Active target:" string if found.
- **Spec**: `docs/SPEC.md`, `docs/PRD.md`, `docs/<project>-spec.md`, `*UnifiedSpec*.md`, `README.md` as last resort.
- **CLAUDE.md** at project root.
- **Recent commits**: `git log --oneline -20` to understand current state + branch convention.
- **Existing sprint plan** (if `$ARGUMENTS` references a sprint): look for `docs/sprints/<name>.md`, `docs/releases/<version>-scope-lock.md`, `<HANDOFF>.md`, `PROGRESS.md`.

### Step 3 — generate run id

`run_id = "{today_iso_date}-{slug}"`. `today_iso_date` is `YYYY-MM-DD`. `slug` is the goal normalized to lowercase, ASCII, kebab-case, max 60 chars.

If `.agent-runs/<run_id>/` exists, append `-2`, `-3`, etc.

### Step 4 — classify the goal

Read `$ARGUMENTS` against these signals (in order of precedence):

| Goal shape | Routes to | Signal |
|---|---|---|
| `resume <id>` | Path 2 | First token |
| `status` or empty | Path 3 | First token |
| Names an existing sprint plan file | Sprint mode (use file's task list) | "slice 1", "v0.4", "commits 1-5", explicit file path |
| Single bug/feature/fix | Task mode (single task) | "fix", "add", "implement", concrete verb + one thing |
| Open-ended ("get X working", "ship the cleanroom") | Sprint mode (decompose at draft time) | Verb + outcome state, no concrete sub-tasks |

Task mode is the simplest path. Sprint mode adds a decomposition step.

### Step 5 — draft the scope contract

`mkdir -p .agent-runs/<run-id>/`. Then draft `.agent-runs/<run-id>/scope.md` directly in the main session (no subagent — you have all the context).

Required sections:

```markdown
# Scope contract — <run-id>

**Goal**: <one sentence, user-facing>

**Mode**: task | sprint

**Branch**: <name> (NEW branch off <base>, OR existing branch <name>)

**Allowed paths**:
- <path 1>
- <path 2>
- ...

**Forbidden paths** (defaults; add to manifest non_goals to opt-out):
- docs/adr/        — new ADR files OK, existing ADRs no-touch
- pyproject.toml, package.json, Cargo.toml — version-only files; release-engineer scope
- .github/workflows/ — CI surface; out of scope unless explicitly opted in
- CHANGELOG.md     — auto-appended by the shipper step; do not edit during tasks

**Success criteria**:
- All tests pass (`<test command>`)
- Lint clean (`<lint command>`)
- (Add others derived from spec/CLAUDE.md)

**Tasks** (ordered):

1. <task name>
   - Description: <what + why>
   - Allowed paths: <subset of above, optional>
   - Success: <test name / file existence / route 2xx / etc.>

2. <task name>
   ...

**Authorizing source** (when a control plane exists): `<file:line>` quoting the active-target line.

**Risk**: low | medium | high

**Rollback**: `git revert <merge-commit>` unless schema/migration in play.
```

For sprint mode with an existing sprint plan file: parse the file's task list verbatim. Don't re-decompose.

For sprint mode without a plan file: decompose the goal into 3-7 ordered tasks. Each task should land in 1-3 commits.

For task mode: one task entry, derived from the goal directly.

### Step 6 — the ONE review gate

Display in chat (concise):

- Goal (one sentence)
- Mode (task / sprint)
- Branch
- N tasks (numbered list, name only)
- Allowed paths (top-level dirs)
- Estimated complexity (low / medium / high)

Fire ONE AskUserQuestion modal:

- **question**: `Scope drafted at .agent-runs/<run-id>/scope.md. GO to start the autonomous run, REVISE to change, BLOCK to halt.`
- **header**: `Scope gate`
- **options**:
  - `GO` — `Start the run. Autonomous loop, no more gates.`
  - `REVISE` — `Stop. Describe what to change.`
  - `BLOCK` — `Halt with a finding.`

Handle:
- `GO` → log `SCOPE_APPROVED` to run.log, proceed to Step 7
- `REVISE` → wait for the user's revision text, re-draft scope.md, loop to Step 6 (max 3 revisions; on 4th, halt and ask the user to invoke `pipeline-init` to fix project metadata)
- `BLOCK` → log `RUN_BLOCKED at scope gate` + reason, exit

### Step 7 — autonomous loop

Initialize `.agent-runs/<run-id>/run.log` with `RUN_STARTED` + `SCOPE_APPROVED`. Initialize `.agent-runs/<run-id>/tasks.md` from scope's task list with each task in `pending` state.

For each task in order:

#### 7a. Update task state to `in_progress`

Edit `tasks.md` to mark current task `in_progress`. Append to run.log: `<ISO ts> TASK_STARTED: <task-id>`.

#### 7b. Spawn worker subagent

Use the `Agent` tool with role file `.pipelines/roles/worker.md`. Build the worker prompt as:

```
<role file content verbatim>

---

RUN CONTEXT:
- run_id: <run-id>
- run_dir: .agent-runs/<run-id>/
- scope: .agent-runs/<run-id>/scope.md (read in full)
- tasks: .agent-runs/<run-id>/tasks.md (read in full)
- branch: <branch from scope>
- working_tree_state: <output of `git status --short`>

CURRENT TASK:
- id: <task-id>
- name: <task name>
- description: <task description>
- allowed_paths: <task-specific subset of scope.allowed_paths, or scope-wide if unspecified>
- success_criteria: <task-specific criteria>

PRIOR_FAILURE_OBSERVATION:
<empty on first attempt; on attempts 2+, the verbatim failure output from the prior attempt's verifier run — test stderr, lint output, build error, etc.>

ATTEMPT: <1 of 3 | 2 of 3 | 3 of 3>

WRITE YOUR OUTPUT to .agent-runs/<run-id>/task-<task-id>-attempt-<N>.md and stop.
```

The worker reads, plans, implements (Edit/Write tools), self-verifies (Bash to run tests/lint), and returns a status: `passes`, `fails`, or `blocked`. The status is the FIRST LINE of its output file: `**Status: passes**` / `**Status: fails**` / `**Status: blocked**`.

#### 7c. Read worker's status

Read the first line of `task-<task-id>-attempt-<N>.md`. Parse the status:

- `passes` → step 7d (commit)
- `fails` → step 7e (retry with critique)
- `blocked` → step 7f (escalate)

If the status line is malformed (missing or not one of the three), treat as `fails` and proceed to 7e with `prior_failure_observation` = "worker produced malformed status line; output file: <path>".

#### 7d. Auto-commit the task

Stage allowed_paths only (NEVER `git add -A` or `git add .`):

```bash
for path in <task allowed_paths>:
    git add <path>
git status --porcelain | grep -v "^[ ?!]" | head -50  # for log
git commit -m "<type>(<scope>): <task summary>"
```

Commit message follows Conventional Commits when CLAUDE.md or recent commits show that convention; otherwise `<task-name>` verbatim.

If `git diff --staged` is empty (no actual changes — the worker considered the task pre-satisfied), skip the commit and log `TASK_NOOP: <task-id>`.

Append to run.log: `<ISO ts> TASK_PASSED: <task-id> (commit <sha-short>)`.

Update tasks.md to mark current task `passed`.

Continue to next task.

#### 7e. Retry with failure-as-observation (Reflexion pattern)

If attempt < 3:
- Read the worker's full output `task-<task-id>-attempt-<N>.md` — extract the failure observation (test output, lint stderr, build error).
- Increment attempt counter.
- Loop back to step 7b with `PRIOR_FAILURE_OBSERVATION` populated from the failure observation.

If attempt == 3 (third failure):
- Log `TASK_RETRY_EXHAUSTED: <task-id>` to run.log.
- Update tasks.md to mark current task `blocked`.
- Proceed to step 7f.

#### 7f. Escalate the blocked task (always-exit-with-something)

This task cannot land in this run. But prior tasks are committed and the work isn't lost.

Decide:

- If at least 50% of tasks have passed → COMMIT_AND_SHIP_PARTIAL: continue to step 8 (final shipping) with `partial: true`. The PR description names the blocked task and points the operator at the resume command.
- If less than 50% have passed → HARD_HALT: write `.agent-runs/<run-id>/HANDOFF.md` summarizing what happened, what's blocked, and the exact resume command. Exit Step 7 with the handoff displayed in chat. The branch is NOT pushed; the operator inspects and decides.

In either case, if there's any uncommitted in-flight work in allowed_paths, stage and commit it as `wip(<scope>): partial attempt on <task-id> (run halted)` so the operator can see what the agent tried.

### Step 8 — final shipping

After the loop completes (all tasks passed OR partial-ship triggered):

1. **Run the full integration suite**: project-defined `pytest`, `npm test`, `cargo test`, or whatever CLAUDE.md names. Capture output to `.agent-runs/<run-id>/integration.log`.
2. **If integration suite passes**:
   - `git push -u origin <branch>` (force-with-lease is OK only if the branch was created in this run).
   - `gh pr create --title "<sprint-or-task title>" --body "<body>"` — body includes: goal, task list with sha per task, integration suite summary, resume instructions if partial. Returns PR URL.
   - Log `PR_OPENED: <url>` to run.log.
   - Append `RUN_DONE` to run.log.
3. **If integration suite fails on a fresh run**:
   - Treat as a final-stage worker failure: spawn worker once more with the integration failure as `PRIOR_FAILURE_OBSERVATION` and no allowed_paths constraint (worker can touch any path that fixes the integration failure).
   - If that final attempt passes the integration suite, push + open PR.
   - If it still fails, push the branch anyway with `partial: true` and a PR titled `[WIP] <title>` with the integration failure verbatim in the body.

### Step 9 — final chat report (one paragraph max)

After Step 8, display in chat:

```
Run complete: <run-id>

  Mode:               <task | sprint>
  Tasks:              <passed>/<total> passed
  Branch:             <branch> pushed → <PR url>
  Disposition:        SHIPPED | SHIPPED-PARTIAL | HALTED
  Integration suite:  PASSED | FAILED-but-shipped-WIP

  Next action:        <merge the PR | review the partial | resume via /agent-pipeline-claude:run resume <run-id>>
```

Stop. No follow-up questions. The user reads the chat report; if they want to know more, they read the artifacts.

---

## Path 2 — resume `<run-id>`

1. Verify `.agent-runs/<run-id>/run.log` exists. If not: `"No run at .agent-runs/<run-id>/. Try /agent-pipeline-claude:run status."`
2. Read run.log. Find:
   - The last `TASK_PASSED` line → that task and all prior are done.
   - The last `TASK_RETRY_EXHAUSTED` or `TASK_STARTED` (without a paired `TASK_PASSED`) → that task is the resume point.
3. Read scope.md and tasks.md. Resume Step 7 starting at the resume-point task.

If the last log line is `RUN_DONE`, the run already shipped. Display the PR URL and exit.

---

## Path 3 — status

List `.agent-runs/*/` directories sorted by mtime descending. For each, read run.log and the last few entries. Report a single line per run:

```
<run-id>    mode=<task|sprint>    last: <event> @ <relative-time>    status: <RUNNING | HALTED | SHIPPED>
```

Max 10 rows. Suffix with `(... <N> older)` if more exist.

---

## Hard rules

- **ONE gate per run, total.** Step 6 is the only `AskUserQuestion` allowed. The autonomous loop never asks.
- **Bounded retries.** Max 3 worker attempts per task. After 3, the task is blocked.
- **Auto-commit per task.** Never batch commits. Never `git add -A`. Stage paths explicitly.
- **Always commit something on halt.** Even WIP work. Even if it's a blocker. Operator must be able to see what was attempted.
- **Never admin-merge a PR.** Never push a tag. Never create a release. These are operator decisions.
- **Status vocabulary in artifacts**: `passes / fails / partial / blocked / pending`. Avoid `done / complete / ready / shippable`.
- **Never modify scope.md mid-run.** Locked at Step 6 approval.
- **Self-feedback IS the recovery loop.** Failure observation goes into the next worker prompt verbatim. No separate critique stage.
- **Worker writes outputs to `.agent-runs/<run-id>/task-<id>-attempt-<N>.md`.** Always. The orchestrator reads the status from the first line.
- **Append-only `run.log`.** Never rewrite. Always timestamp.

## Failure-message shape (chat surface only)

All chat-surface error messages follow:

```
<one-line summary>

  What:        <one sentence>
  Where:       <file/path/task>
  Recovery:    <concrete next step>

  Artifacts:   <path to handoff/log/output if any>
```

No raw Python tracebacks. No "check_xxx: FAIL" output. The orchestrator translates errors before display.
